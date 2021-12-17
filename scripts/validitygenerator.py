#!/usr/bin/python3 -i
#
# Copyright 2013-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import re
from collections import OrderedDict, namedtuple
from functools import reduce
from pathlib import Path

from conventions import ProseListFormats as plf
from generator import OutputGenerator, write
from spec_tools.attributes import ExternSyncEntry, LengthEntry
from spec_tools.util import (findNamedElem, findNamedObject, findTypedElem,
                             getElemName, getElemType)
from spec_tools.validity import ValidityCollection, ValidityEntry


# For parsing/splitting queue bit names - Vulkan only
QUEUE_BITS_RE = re.compile(r'([^,]+)')


class UnhandledCaseError(RuntimeError):
    def __init__(self, msg=None):
        if msg:
            super().__init__('Got a case in the validity generator that we have not explicitly handled: ' + msg)
        else:
            super().__init__('Got a case in the validity generator that we have not explicitly handled.')


def _genericIterateIntersection(a, b):
    """Iterate through all elements in a that are also in b.

    Somewhat like a set's intersection(),
    but not type-specific so it can work with OrderedDicts, etc.
    It also returns a generator instead of a set,
    so you can pick what container type you'd like,
    if any.
    """
    return (x for x in a if x in b)


def _make_ordered_dict(gen):
    """Make an ordered dict (with None as the values) from a generator."""
    return OrderedDict(((x, None) for x in gen))


def _orderedDictIntersection(a, b):
    return _make_ordered_dict(_genericIterateIntersection(a, b))


def _genericIsDisjoint(a, b):
    """Return true if nothing in a is also in b.

    Like a set's is_disjoint(),
    but not type-specific so it can work with OrderedDicts, etc.
    """
    for _ in _genericIterateIntersection(a, b):
        return False
    # if we never enter the loop...
    return True


def _parse_queue_bits(cmd):
    """Return a generator of queue bits, with underscores turned to spaces.

    Vulkan-only.

    Return None if the queues attribute is not specified."""
    queuetypes = cmd.get('queues')
    if not queuetypes:
        return None
    return (qt.replace('_', ' ')
            for qt in QUEUE_BITS_RE.findall(queuetypes))


class ValidityOutputGenerator(OutputGenerator):
    """ValidityOutputGenerator - subclass of OutputGenerator.

    Generates AsciiDoc includes of valid usage information, for reference
    pages and the specification. Similar to DocOutputGenerator.

    ---- methods ----
    ValidityOutputGenerator(errFile, warnFile, diagFile) - args as for
    OutputGenerator. Defines additional internal state.
    ---- methods overriding base class ----
    beginFile(genOpts)
    endFile()
    beginFeature(interface, emit)
    endFeature()
    genCmd(cmdinfo)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.currentExtension = ''

    @property
    def null(self):
        """Preferred spelling of NULL.

        Delegates to the object implementing ConventionsBase.
        """
        return self.conventions.null

    @property
    def structtype_member_name(self):
        """Return name of the structure type member.

        Delegates to the object implementing ConventionsBase.
        """
        return self.conventions.structtype_member_name

    @property
    def nextpointer_member_name(self):
        """Return name of the structure pointer chain member.

        Delegates to the object implementing ConventionsBase.
        """
        return self.conventions.nextpointer_member_name

    def makeProseList(self, elements, fmt=plf.AND,
                      comma_for_two_elts=False, *args, **kwargs):
        """Make a (comma-separated) list for use in prose.

        Adds a connective (by default, 'and')
        before the last element if there are more than 1.

        Optionally adds a quantifier (like 'any') before a list of 2 or more,
        if specified by fmt.

        Delegates to the object implementing ConventionsBase.
        """
        if not elements:
            raise ValueError(
                'Cannot pass an empty list if you are trying to make a prose list.')
        return self.conventions.makeProseList(elements,
                                              fmt,
                                              with_verb=False,
                                              comma_for_two_elts=comma_for_two_elts,
                                              *args, **kwargs)

    def makeProseListIs(self, elements, fmt=plf.AND,
                        comma_for_two_elts=False, *args, **kwargs):
        """Make a (comma-separated) list for use in prose, followed by either 'is' or 'are' as appropriate.

        Adds a connective (by default, 'and')
        before the last element if there are more than 1.

        Optionally adds a quantifier (like 'any') before a list of 2 or more,
        if specified by fmt.

        Delegates to the object implementing ConventionsBase.
        """
        if not elements:
            raise ValueError(
                'Cannot pass an empty list if you are trying to make a prose list.')
        return self.conventions.makeProseList(elements,
                                              fmt,
                                              with_verb=True,
                                              comma_for_two_elts=comma_for_two_elts,
                                              *args, **kwargs)

    def makeValidityCollection(self, entity_name):
        """Create a ValidityCollection object, passing along our Conventions."""
        return ValidityCollection(entity_name, self.conventions)

    def beginFile(self, genOpts):
        if not genOpts.conventions:
            raise RuntimeError(
                'Must specify conventions object to generator options')
        self.conventions = genOpts.conventions
        # Vulkan says 'must: be a valid pointer' a lot, OpenXR just says
        # 'must: be a pointer'.
        self.valid_pointer_text = ' '.join(
            (x for x in (self.conventions.valid_pointer_prefix, 'pointer') if x))
        OutputGenerator.beginFile(self, genOpts)

    def endFile(self):
        OutputGenerator.endFile(self)

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)
        self.currentExtension = interface.get('name')

    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    @property
    def struct_macro(self):
        """Get the appropriate format macro for a structure."""
        # delegate to conventions
        return self.conventions.struct_macro

    def makeStructName(self, name):
        """Prepend the appropriate format macro for a structure to a structure type name."""
        # delegate to conventions
        return self.conventions.makeStructName(name)

    def makeParameterName(self, name):
        """Prepend the appropriate format macro for a parameter/member to a parameter name."""
        return 'pname:' + name

    def makeBaseTypeName(self, name):
        """Prepend the appropriate format macro for a 'base type' to a type name."""
        return 'basetype:' + name

    def makeEnumerationName(self, name):
        """Prepend the appropriate format macro for an enumeration type to a enum type name."""
        return 'elink:' + name

    def makeFlagsName(self, name):
        """Prepend the appropriate format macro for a flags type to a flags type name."""
        return 'tlink:' + name

    def makeFuncPointerName(self, name):
        """Prepend the appropriate format macro for a function pointer type to a type name."""
        return 'tlink:' + name

    def makeExternalTypeName(self, name):
        """Prepend the appropriate format macro for an external type like uint32_t to a type name."""
        # delegate to conventions
        return self.conventions.makeExternalTypeName(name)

    def makeEnumerantName(self, name):
        """Prepend the appropriate format macro for an enumerate (value) to a enum value name."""
        return 'ename:' + name

    def writeInclude(self, directory, basename, validity: ValidityCollection,
                     threadsafety, commandpropertiesentry=None,
                     successcodes=None, errorcodes=None):
        """Generate an include file.

        directory - subdirectory to put file in (absolute or relative pathname)
        basename - base name of the file
        validity - ValidityCollection to write.
        threadsafety - List (may be empty) of thread safety statements to write.
        successcodes - Optional success codes to document.
        errorcodes - Optional error codes to document.
        """
        # Create subdirectory, if needed
        directory = Path(directory)
        if not directory.is_absolute():
            directory = Path(self.genOpts.directory) / directory
        self.makeDir(str(directory))

        # Create validity file
        filename = str(directory / (basename + '.txt'))
        self.logMsg('diag', '# Generating include file:', filename)

        with open(filename, 'w', encoding='utf-8') as fp:
            write(self.conventions.warning_comment, file=fp)

            # Valid Usage
            if validity:
                write('.Valid Usage (Implicit)', file=fp)
                write('****', file=fp)
                write(validity, file=fp, end='')
                write('****', file=fp)
                write('', file=fp)

            # Host Synchronization
            if threadsafety:
                # The heading of this block differs between projects, so an Asciidoc attribute is used.
                write('.{externsynctitle}', file=fp)
                write('****', file=fp)
                write(threadsafety, file=fp, end='')
                write('****', file=fp)
                write('', file=fp)

            # Command Properties - contained within a block, to avoid table numbering
            if commandpropertiesentry:
                write('.Command Properties', file=fp)
                write('****', file=fp)
                write('[options="header", width="100%"]', file=fp)
                write('|====', file=fp)
                write('|<<VkCommandBufferLevel,Command Buffer Levels>>|<<vkCmdBeginRenderPass,Render Pass Scope>>|<<VkQueueFlagBits,Supported Queue Types>>', file=fp)
                write(commandpropertiesentry, file=fp)
                write('|====', file=fp)
                write('****', file=fp)
                write('', file=fp)

            # Success Codes - contained within a block, to avoid table numbering
            if successcodes or errorcodes:
                write('.Return Codes', file=fp)
                write('****', file=fp)
                if successcodes:
                    write('ifndef::doctype-manpage[]', file=fp)
                    write('<<fundamentals-successcodes,Success>>::', file=fp)
                    write('endif::doctype-manpage[]', file=fp)
                    write('ifdef::doctype-manpage[]', file=fp)
                    write('On success, this command returns::', file=fp)
                    write('endif::doctype-manpage[]', file=fp)
                    write(successcodes, file=fp)
                if errorcodes:
                    write('ifndef::doctype-manpage[]', file=fp)
                    write('<<fundamentals-errorcodes,Failure>>::', file=fp)
                    write('endif::doctype-manpage[]', file=fp)
                    write('ifdef::doctype-manpage[]', file=fp)
                    write('On failure, this command returns::', file=fp)
                    write('endif::doctype-manpage[]', file=fp)
                    write(errorcodes, file=fp)
                write('****', file=fp)
                write('', file=fp)

    def paramIsPointer(self, param):
        """Check if the parameter passed in is a pointer."""
        tail = param.find('type').tail
        return tail is not None and '*' in tail

    def paramIsStaticArray(self, param):
        """Check if the parameter passed in is a static array."""
        tail = param.find('name').tail
        return tail and tail[0] == '['

    def paramIsConst(self, param):
        """Check if the parameter passed in has a type that mentions const."""
        return param.text is not None and 'const' in param.text

    def staticArrayLength(self, param):
        """Get the length of a parameter that's been identified as a static array."""
        paramenumsize = param.find('enum')
        if paramenumsize is not None:
            return paramenumsize.text
            # TODO switch to below when cosmetic changes OK
            # return self.makeEnumerantName(paramenumsize.text)

        return param.find('name').tail[1:-1]

    def paramIsArray(self, param):
        """Check if the parameter passed in is a pointer to an array."""
        return param.get('len') is not None

    def getHandleDispatchableAncestors(self, typename):
        """Get the ancestors of a handle object."""
        ancestors = []
        current = typename
        while True:
            current = self.getHandleParent(current)
            if current is None:
                return ancestors
            if self.isHandleTypeDispatchable(current):
                ancestors.append(current)

    def isHandleTypeDispatchable(self, handlename):
        """Check if a parent object is dispatchable or not."""
        handle = self.registry.tree.find(
            "types/type/[name='" + handlename + "'][@category='handle']")
        if handle is not None and getElemType(handle) == 'VK_DEFINE_HANDLE':
            return True
        else:
            return False

    def isHandleOptional(self, param, params):
        # Simple, if it's optional, return true
        if param.get('optional') is not None:
            return True

        # If no validity is being generated, it usually means that validity is complex and not absolute, so let's say yes.
        if param.get('noautovalidity') is not None:
            return True

        # If the parameter is an array and we haven't already returned, find out if any of the len parameters are optional
        if self.paramIsArray(param):
            for length in LengthEntry.parse_len_from_param(param):
                if not length.other_param_name:
                    # don't care about constants or "null-terminated"
                    continue

                other_param = findNamedElem(params, length.other_param_name)
                if other_param is None:
                    self.logMsg('warn', length.other_param_name,
                                'is listed as a length for parameter', param, 'but no such parameter exists')
                if other_param and other_param.get('optional'):
                    return True

        return False

    def makeOptionalPre(self, param):
        # Don't generate this stub for bitflags
        param_name = getElemName(param)
        paramtype = getElemType(param)
        type_category = self.getTypeCategory(paramtype)
        is_optional = param.get('optional').split(',')[0] == 'true'
        if type_category != 'bitmask' and is_optional:
            if self.paramIsArray(param) or self.paramIsPointer(param):
                optional_val = self.null
            elif type_category == 'handle':
                if self.isHandleTypeDispatchable(paramtype):
                    optional_val = self.null
                else:
                    optional_val = 'dlink:' + self.conventions.api_prefix + 'NULL_HANDLE'
            else:
                optional_val = self.conventions.zero
            return 'If {} is not {}, '.format(
                self.makeParameterName(param_name),
                optional_val)

        return ""

    def makeParamValidityPre(self, param, params, selector):
        """Make the start of an entry for a parameter's validity, including a chunk of text if it is an array."""
        param_name = getElemName(param)
        paramtype = getElemType(param)

        # General pre-amble. Check optionality and add stuff.
        entry = ValidityEntry(anchor=(param_name, 'parameter'))
        is_optional = param.get('optional') is not None and param.get('optional').split(',')[0] == 'true'

        # This is for a union member, and the valid member is chosen by an enum selection
        if selector:
            selection = param.get('selection')

            entry += 'If {} is {}, '.format(
                self.makeParameterName(selector),
                self.makeEnumerantName(selection))

            if is_optional:
                entry += "and "
                optionalpre = self.makeOptionalPre(param)
                entry += optionalpre[0].lower() + optionalpre[1:]

            return entry

        if self.paramIsStaticArray(param):
            if paramtype != 'char':
                entry += 'Any given element of '
            return entry

        if self.paramIsArray(param) and param.get('len') != LengthEntry.NULL_TERMINATED_STRING:
            # Find all the parameters that are called out as optional,
            # so we can document that they might be zero, and the array may be ignored
            optionallengths = []
            for length in LengthEntry.parse_len_from_param(param):
                if not length.other_param_name:
                    # Only care about length entries that are parameter names
                    continue

                other_param = findNamedElem(params, length.other_param_name)
                other_param_optional = (other_param is not None) and (
                    other_param.get('optional') is not None)

                if other_param is None or not other_param_optional:
                    # Don't care about not-found params or non-optional params
                    continue

                if self.paramIsPointer(other_param):
                    optionallengths.append(
                        'the value referenced by ' + self.makeParameterName(length.other_param_name))
                else:
                    optionallengths.append(
                        self.makeParameterName(length.other_param_name))

            # Document that these arrays may be ignored if any of the length values are 0
            if optionallengths or is_optional:
                entry += 'If '
            if optionallengths:
                entry += self.makeProseListIs(optionallengths, fmt=plf.OR)
                entry += ' not %s, ' % self.conventions.zero
            # TODO enabling this in OpenXR, as used in Vulkan, causes nonsensical things like
            # "If pname:propertyCapacityInput is not `0`, and pname:properties is not `NULL`, pname:properties must: be a pointer to an array of pname:propertyCapacityInput slink:XrApiLayerProperties structures"
            if optionallengths and is_optional:
                entry += 'and '
            if is_optional:
                entry += self.makeParameterName(param_name)
                # TODO switch when cosmetic changes OK
                # entry += ' is not {}, '.format(self.null)
                entry += ' is not `NULL`, '
            return entry

        if param.get('optional'):
            entry += self.makeOptionalPre(param)
            return entry

        # If none of the early returns happened, we at least return an empty
        # entry with an anchor.
        return entry

    def createValidationLineForParameterImpl(self, blockname, param, params, typetext, selector, parentname):
        """Make the generic validity portion used for all parameters.

        May return None if nothing to validate.
        """
        if param.get('noautovalidity') is not None:
            return None

        validity = self.makeValidityCollection(blockname)
        param_name = getElemName(param)
        paramtype = getElemType(param)

        entry = self.makeParamValidityPre(param, params, selector)

        # This is for a child member of a union
        if selector:
            entry += 'the {} member of {} must: be '.format(self.makeParameterName(param_name), self.makeParameterName(parentname))
        else:
            entry += '{} must: be '.format(self.makeParameterName(param_name))

        if self.paramIsStaticArray(param) and paramtype == 'char':
            # TODO this is a minor hack to determine if this is a command parameter or a struct member
            if self.paramIsConst(param) or blockname.startswith(self.conventions.type_prefix):
                entry += 'a null-terminated UTF-8 string whose length is less than or equal to '
                entry += self.staticArrayLength(param)
            else:
                # This is a command's output parameter
                entry += 'a character array of length %s ' % self.staticArrayLength(param)
            validity += entry
            return validity

        elif self.paramIsArray(param):
            # Arrays. These are hard to get right, apparently

            lengths = LengthEntry.parse_len_from_param(param)

            for i, length in enumerate(LengthEntry.parse_len_from_param(param)):
                if i == 0:
                    # If the first index, make it singular.
                    entry += 'a '
                    array_text = 'an array'
                    pointer_text = self.valid_pointer_text
                else:
                    array_text = 'arrays'
                    pointer_text = self.valid_pointer_text + 's'

                if length.null_terminated:
                    # This should always be the last thing.
                    # If it ever isn't for some bizarre reason, then this will need some massaging.
                    entry += 'null-terminated '
                elif length.number == 1:
                    entry += pointer_text
                    entry += ' to '
                else:
                    entry += pointer_text
                    entry += ' to '
                    entry += array_text
                    entry += ' of '
                    # Handle equations, which are currently denoted with latex
                    if length.math:
                        # Handle equations, which are currently denoted with latex
                        entry += str(length)
                    else:
                        entry += self.makeParameterName(str(length))
                    entry += ' '

            # Void pointers don't actually point at anything - remove the word "to"
            if paramtype == 'void':
                if lengths[-1].number == 1:
                    if len(lengths) > 1:
                        # Take care of the extra s added by the post array chunk function. #HACK#
                        entry.drop_end(5)
                    else:
                        entry.drop_end(4)

                    # This hasn't been hit, so this hasn't been tested recently.
                    raise UnhandledCaseError(
                        "Got void pointer param/member with last length 1")
                else:
                    # An array of void values is a byte array.
                    entry += 'byte'

            elif paramtype == 'char':
                # A null terminated array of chars is a string
                if lengths[-1].null_terminated:
                    entry += 'UTF-8 string'
                else:
                    # Else it's just a bunch of chars
                    entry += 'char value'

            elif self.paramIsConst(param):
                # If a value is "const" that means it won't get modified, so it must be valid going into the function.
                if 'const' in param.text:

                    if not self.isStructAlwaysValid(paramtype):
                        entry += 'valid '

            # Check if the array elements are optional
            array_element_optional = param.get('optional') is not None    \
                      and len(param.get('optional').split(',')) == len(LengthEntry.parse_len_from_param(param)) + 1 \
                      and param.get('optional').split(',')[-1] == 'true'
            if array_element_optional and self.getTypeCategory(paramtype) != 'bitmask': # bitmask is handled later
                entry += 'or dlink:' + self.conventions.api_prefix + 'NULL_HANDLE '

            entry += typetext

            # pluralize
            if len(lengths) > 1 or (lengths[0] != 1 and not lengths[0].null_terminated):
                entry += 's'

            return self.handleRequiredBitmask(blockname, param, paramtype, entry, 'true' if array_element_optional else None)

        if self.paramIsPointer(param):
            # Handle pointers - which are really special case arrays (i.e. they don't have a length)
            # TODO  should do something here if someone ever uses some intricate comma-separated `optional`
            pointercount = param.find('type').tail.count('*')

            # Treat void* as an int
            if paramtype == 'void':
                optional = param.get('optional')
                # If there is only void*, it is just optional int - we don't need any language.
                if pointercount == 1 and optional is not None:
                    return None  # early return
                # Treat the inner-most void* as an int
                pointercount -= 1

            # Could be multi-level pointers (e.g. ppData - pointer to a pointer). Handle that.
            entry += 'a '
            entry += (self.valid_pointer_text + ' to a ') * pointercount

            # Handle void* and pointers to it
            if paramtype == 'void':
                if optional is None or optional.split(',')[pointercount]:
                    # The last void* is just optional int (e.g. to be filled by the impl.)
                    typetext = 'pointer value'

            # If a value is "const" that means it won't get modified, so it must be valid going into the function.
            elif self.paramIsConst(param) and paramtype != 'void':
                entry += 'valid '

            entry += typetext
            return self.handleRequiredBitmask(blockname, param, paramtype, entry, param.get('optional'))

        # Add additional line for non-optional bitmasks
        if self.getTypeCategory(paramtype) == 'bitmask':
            # TODO does not really handle if someone tries something like optional="true,false"
            # TODO OpenXR has 0 or a valid combination of flags, for optional things.
            # Vulkan doesn't...
            # isMandatory = param.get('optional') is None
            # if not isMandatory:
            #     entry += self.conventions.zero
            #     entry += ' or '
            # Non-pointer, non-optional things must be valid
            entry += 'a valid {}'.format(typetext)

            return self.handleRequiredBitmask(blockname, param, paramtype, entry, param.get('optional'))

        # Non-pointer, non-optional things must be valid
        entry += 'a valid {}'.format(typetext)
        return entry

    def handleRequiredBitmask(self, blockname, param, paramtype, entry, optional):
        # TODO does not really handle if someone tries something like optional="true,false"
        if self.getTypeCategory(paramtype) != 'bitmask' or optional == 'true':
            return entry
        if self.paramIsPointer(param) and not self.paramIsArray(param):
            # This is presumably an output parameter
            return entry

        param_name = getElemName(param)
        # If mandatory, then we need two entries instead of just one.
        validity = self.makeValidityCollection(blockname)
        validity += entry

        entry2 = ValidityEntry(anchor=(param_name, 'requiredbitmask'))
        if self.paramIsArray(param):
            entry2 += 'Each element of '
        entry2 += '{} must: not be {}'.format(
            self.makeParameterName(param_name), self.conventions.zero)
        validity += entry2
        return validity

    def createValidationLineForParameter(self, blockname, param, params, typecategory, selector, parentname):
        """Make an entire validation entry for a given parameter."""
        param_name = getElemName(param)
        paramtype = getElemType(param)

        is_array = self.paramIsArray(param)
        is_pointer = self.paramIsPointer(param)
        needs_recursive_validity = (is_array
                                    or is_pointer
                                    or not self.isStructAlwaysValid(paramtype))
        typetext = None
        if paramtype in ('void', 'char'):
            # Chars and void are special cases - we call the impl function,
            # but don't use the typetext.
            # A null-terminated char array is a string, else it's chars.
            # An array of void values is a byte array, a void pointer is just a pointer to nothing in particular
            typetext = ''

        elif typecategory == 'bitmask':
            bitsname = paramtype.replace('Flags', 'FlagBits')
            bitselem = self.registry.tree.find("enums[@name='" + bitsname + "']")

            # If bitsname is an alias, then use the alias to get bitselem.
            typeElem = self.registry.lookupElementInfo(bitsname, self.registry.typedict)
            if typeElem is not None:
                alias = self.registry.getAlias(typeElem.elem, self.registry.typedict)
                if alias is not None:
                    bitselem = self.registry.tree.find("enums[@name='" + alias + "']")

            if bitselem is None or len(bitselem.findall('enum[@required="true"]')) == 0:
                # Empty bit mask: presumably just a placeholder (or only in
                # an extension not enabled for this build)
                entry = ValidityEntry(
                    anchor=(param_name, 'zerobitmask'))
                entry += self.makeParameterName(param_name)
                entry += ' must: be '
                entry += self.conventions.zero
                # Early return
                return entry

            is_const = self.paramIsConst(param)

            if is_array:
                if is_const:
                    # input an array of bitmask values
                    template = 'combinations of {bitsname} value'
                else:
                    template = '{paramtype} value'
            elif is_pointer:
                if is_const:
                    template = 'combination of {bitsname} values'
                else:
                    template = '{paramtype} value'
            else:
                template = 'combination of {bitsname} values'

            # The above few cases all use makeEnumerationName, just with different context.
            typetext = template.format(
                bitsname=self.makeEnumerationName(bitsname),
                paramtype=self.makeFlagsName(paramtype))

        elif typecategory == 'handle':
            typetext = '{} handle'.format(self.makeStructName(paramtype))

        elif typecategory == 'enum':
            typetext = '{} value'.format(self.makeEnumerationName(paramtype))

        elif typecategory == 'funcpointer':
            typetext = '{} value'.format(self.makeFuncPointerName(paramtype))

        elif typecategory == 'struct':
            if needs_recursive_validity:
                typetext = '{} structure'.format(
                    self.makeStructName(paramtype))

        elif typecategory == 'union':
            if needs_recursive_validity:
                typetext = '{} union'.format(self.makeStructName(paramtype))

        elif self.paramIsArray(param) or self.paramIsPointer(param):
            # TODO sync cosmetic changes from OpenXR?
            typetext = '{} value'.format(self.makeBaseTypeName(paramtype))

        elif typecategory is None:
            if not self.isStructAlwaysValid(paramtype):
                typetext = '{} value'.format(
                    self.makeExternalTypeName(paramtype))

            # "a valid uint32_t value" doesn't make much sense.
            pass

        # If any of the above conditions matched and set typetext,
        # we call using it.
        if typetext is not None:
            return self.createValidationLineForParameterImpl(
                blockname, param, params, typetext, selector, parentname)
        return None

    def makeHandleValidityParent(self, param, params):
        """Make a validity entry for a handle's parent object.

        Creates 'parent' VUID.
        """
        param_name = getElemName(param)
        paramtype = getElemType(param)

        # Deal with handle parents
        handleparent = self.getHandleParent(paramtype)
        if handleparent is None:
            return None

        otherparam = findTypedElem(params, handleparent)
        if otherparam is None:
            return None

        parent_name = getElemName(otherparam)
        entry = ValidityEntry(anchor=(param_name, 'parent'))

        is_optional = self.isHandleOptional(param, params)

        if self.paramIsArray(param):
            template = 'Each element of {}'
            if is_optional:
                template += ' that is a valid handle'
        elif is_optional:
            template = 'If {} is a valid handle, it'
        else:
            # not optional, not an array. Just say the parameter name.
            template = '{}'

        entry += template.format(self.makeParameterName(param_name))

        entry += ' must: have been created, allocated, or retrieved from {}'.format(
            self.makeParameterName(parent_name))

        return entry

    def makeAsciiDocHandlesCommonAncestor(self, blockname, handles, params):
        """Make an asciidoc validity entry for a common ancestors between handles.

        Only handles parent validity for signatures taking multiple handles
        any ancestors also being supplied to this function.
        (e.g. "Each of x, y, and z must: come from the same slink:ParentHandle")
        See self.makeAsciiDocHandleParent() for instances where the parent
        handle is named and also passed.

        Creates 'commonparent' VUID.
        """
        # TODO Replace with refactored code from OpenXR
        entry = None

        if len(handles) > 1:
            ancestormap = {}
            anyoptional = False
            # Find all the ancestors
            for param in handles:
                paramtype = getElemType(param)

                if not self.paramIsPointer(param) or (param.text and 'const' in param.text):
                    ancestors = self.getHandleDispatchableAncestors(paramtype)

                    ancestormap[param] = ancestors

                    anyoptional |= self.isHandleOptional(param, params)

            # Remove redundant ancestor lists
            for param in handles:
                paramtype = getElemType(param)

                removals = []
                for ancestors in ancestormap.items():
                    if paramtype in ancestors[1]:
                        removals.append(ancestors[0])

                if removals != []:
                    for removal in removals:
                        del(ancestormap[removal])

            # Intersect

            if len(ancestormap.values()) > 1:
                current = list(ancestormap.values())[0]
                for ancestors in list(ancestormap.values())[1:]:
                    current = [val for val in current if val in ancestors]

                if len(current) > 0:
                    commonancestor = current[0]

                    if len(ancestormap.keys()) > 1:

                        entry = ValidityEntry(anchor=('commonparent',))

                        parametertexts = []
                        for param in ancestormap.keys():
                            param_name = getElemName(param)
                            parametertext = self.makeParameterName(param_name)
                            if self.paramIsArray(param):
                                parametertext = 'the elements of ' + parametertext
                            parametertexts.append(parametertext)

                        parametertexts.sort()

                        if len(parametertexts) > 2:
                            entry += 'Each of '
                        else:
                            entry += 'Both of '

                        entry += self.makeProseList(parametertexts,
                                                    comma_for_two_elts=True)
                        if anyoptional is True:
                            entry += ' that are valid handles of non-ignored parameters'
                        entry += ' must: have been created, allocated, or retrieved from the same '
                        entry += self.makeStructName(commonancestor)

        return entry

    def makeStructureTypeFromName(self, structname):
        """Create text for a structure type name, like ename:VK_STRUCTURE_TYPE_CREATE_INSTANCE_INFO"""
        return self.makeEnumerantName(self.conventions.generate_structure_type_from_name(structname))

    def makeStructureTypeValidity(self, structname):
        """Generate an validity line for the type value of a struct.

        Creates VUID named like the member name.
        """
        info = self.registry.typedict.get(structname)
        assert(info is not None)

        # If this fails (meaning we have something other than a struct in here),
        # then the caller is wrong:
        # probably passing the wrong value for structname.
        members = info.getMembers()
        assert(members)

        # If this fails, see caller: this should only get called for a struct type with a type value.
        param = findNamedElem(members, self.structtype_member_name)
        # OpenXR gets some structs without a type field in here, so can't assert
        assert(param is not None)
        # if param is None:
        #     return None

        entry = ValidityEntry(
            anchor=(self.structtype_member_name, self.structtype_member_name))
        entry += self.makeParameterName(self.structtype_member_name)
        entry += ' must: be '

        values = param.get('values', '').split(',')
        if values:
            # Extract each enumerant value. They could be validated in the
            # same fashion as validextensionstructs in
            # makeStructureExtensionPointer, although that's not relevant in
            # the current extension struct model.
            entry += self.makeProseList((self.makeEnumerantName(v)
                                         for v in values), 'or')
            return entry

        if 'Base' in structname:
            # This type doesn't even have any values for its type,
            # and it seems like it might be a base struct that we'd expect to lack its own type,
            # so omit the entire statement
            return None

        self.logMsg('warn', 'No values were marked-up for the structure type member of',
                    structname, 'so making one up!')
        entry += self.makeStructureTypeFromName(structname)

        return entry

    def makeStructureExtensionPointer(self, blockname, param):
        """Generate an validity line for the pointer chain member value of a struct."""
        param_name = getElemName(param)

        if param.get('validextensionstructs') is not None:
            self.logMsg('warn', blockname,
                        'validextensionstructs is deprecated/removed', '\n')

        entry = ValidityEntry(
            anchor=(param_name, self.nextpointer_member_name))
        validextensionstructs = self.registry.validextensionstructs.get(
            blockname)
        extensionstructs = []
        duplicatestructs = []

        if validextensionstructs is not None:
            # Check each structure name and skip it if not required by the
            # generator. This allows tagging extension structs in the XML
            # that are only included in validity when needed for the spec
            # being targeted.
            # Track the required structures, and of the required structures,
            # those that allow duplicates in the pNext chain.
            for struct in validextensionstructs:
                # Unpleasantly breaks encapsulation. Should be a method in the registry class
                t = self.registry.lookupElementInfo(
                    struct, self.registry.typedict)
                if t is None:
                    self.logMsg('warn', 'makeStructureExtensionPointer: struct', struct,
                                'is in a validextensionstructs= attribute but is not in the registry')
                elif t.required:
                    extensionstructs.append('slink:' + struct)
                    if t.elem.get('allowduplicate') == 'true':
                        duplicatestructs.append('slink:' + struct)
                else:
                    self.logMsg(
                        'diag', 'makeStructureExtensionPointer: struct', struct, 'IS NOT required')

        if not extensionstructs:
            entry += '{} must: be {}'.format(
                self.makeParameterName(param_name), self.null)
            return entry

        if len(extensionstructs) == 1:
            entry += '{} must: be {} or a pointer to a valid instance of {}'.format(self.makeParameterName(param_name), self.null,
                                                                                    extensionstructs[0])
        else:
            # More than one extension struct.
            entry += 'Each {} member of any structure (including this one) in the pname:{} chain '.format(
                self.makeParameterName(param_name), self.nextpointer_member_name)
            entry += 'must: be either {} or a pointer to a valid instance of '.format(
                self.null)

            entry += self.makeProseList(extensionstructs, fmt=plf.OR)

        validity = self.makeValidityCollection(blockname)
        validity += entry

        # Generate VU statement requiring unique structures in the pNext
        # chain.
        # NOTE: OpenXR always allows non-unique type values. Instances other
        # than the first are just ignored

        vu = ('The pname:' +
              self.structtype_member_name +
              ' value of each struct in the pname:' +
              self.nextpointer_member_name +
              ' chain must: be unique')
        anchor = (self.conventions.member_used_for_unique_vuid, 'unique')

        # If duplicates of some structures are allowed, they are called out
        # explicitly.
        num = len(duplicatestructs)
        if num > 0:
            vu = (vu +
                  ', with the exception of structures of type ' +
                  self.makeProseList(duplicatestructs, fmt=plf.OR))

        validity.addValidityEntry(vu, anchor = anchor )

        return validity

    def addSharedStructMemberValidity(self, struct, blockname, param, validity):
        """Generate language to independently validate a parameter, for those validated even in output.

        Return value indicates whether it was handled internally (True) or if it may need more validity (False)."""
        param_name = getElemName(param)
        paramtype = getElemType(param)
        if param.get('noautovalidity') is None:

            if self.conventions.is_structure_type_member(paramtype, param_name):
                validity += self.makeStructureTypeValidity(blockname)
                return True

            if self.conventions.is_nextpointer_member(paramtype, param_name):
                # Vulkan: the addition of validity here is conditional unlike OpenXR.
                if struct.get('structextends') is None:
                    validity += self.makeStructureExtensionPointer(
                        blockname, param)
                return True
        return False

    def makeOutputOnlyStructValidity(self, cmd, blockname, params):
        """Generate all the valid usage information for a struct that's entirely output.

        That is, it is only ever filled out by the implementation other than
        the structure type and pointer chain members.
        Thus, we only create validity for the pointer chain member.
        """
        # Start the validity collection for this struct
        validity = self.makeValidityCollection(blockname)

        for param in params:
            self.addSharedStructMemberValidity(
                cmd, blockname, param, validity)

        return validity

    def isVKVersion11(self):
        """Returns true if VK_VERSION_1_1 is being emitted."""
        vk11 = re.match(self.registry.genOpts.emitversions, 'VK_VERSION_1_1') is not None
        return vk11

    def makeStructOrCommandValidity(self, cmd, blockname, params):
        """Generate all the valid usage information for a given struct or command."""
        validity = self.makeValidityCollection(blockname)
        handles = []
        arraylengths = dict()
        for param in params:
            param_name = getElemName(param)
            paramtype = getElemType(param)

            # Valid usage ID tags (VUID) are generated for various
            # conditions based on the name of the block (structure or
            # command), name of the element (member or parameter), and type
            # of VU statement.

            # Get the type's category
            typecategory = self.getTypeCategory(paramtype)

            if not self.addSharedStructMemberValidity(
                    cmd, blockname, param, validity):
                if not param.get('selector'):
                    validity += self.createValidationLineForParameter(
                        blockname, param, params, typecategory, None, None)
                else:
                    selector = param.get('selector')
                    if typecategory != 'union':
                        self.logMsg('warn', 'selector attribute set on non-union parameter', param_name, 'in', blockname)

                    paraminfo = self.registry.lookupElementInfo(paramtype, self.registry.typedict)

                    for member in paraminfo.getMembers():
                        membertype = getElemType(member)
                        membertypecategory = self.getTypeCategory(membertype)

                        validity += self.createValidationLineForParameter(
                            blockname, member, paraminfo.getMembers(), membertypecategory, selector, param_name)

            # Ensure that any parenting is properly validated, and list that a handle was found
            if typecategory == 'handle':
                handles.append(param)

            # Get the array length for this parameter
            lengths = LengthEntry.parse_len_from_param(param)
            if lengths:
                arraylengths.update({length.other_param_name: length
                                     for length in lengths
                                     if length.other_param_name})

        # For any vkQueue* functions, there might be queue type data
        if 'vkQueue' in blockname:
            # The queue type must be valid
            queuebits = _parse_queue_bits(cmd)
            if queuebits:
                entry = ValidityEntry(anchor=('queuetype',))
                entry += 'The pname:queue must: support '
                entry += self.makeProseList(queuebits,
                                            fmt=plf.OR, comma_for_two_elts=True)
                entry += ' operations'
                validity += entry

        if 'vkCmd' in blockname:
            # The commandBuffer parameter must be being recorded
            entry = ValidityEntry(anchor=('commandBuffer', 'recording'))
            entry += 'pname:commandBuffer must: be in the <<commandbuffers-lifecycle, recording state>>'
            validity += entry

            #
            # Start of valid queue type validation - command pool must have been
            # allocated against a queue with at least one of the valid queue types
            entry = ValidityEntry(anchor=('commandBuffer', 'cmdpool'))

            #
            # This test for vkCmdFillBuffer is a hack, since we have no path
            # to conditionally have queues enabled or disabled by an extension.
            # As the VU stuff is all moving out (hopefully soon), this hack solves the issue for now
            if blockname == 'vkCmdFillBuffer':
                entry += 'The sname:VkCommandPool that pname:commandBuffer was allocated from must: support '
                if self.isVKVersion11() or 'VK_KHR_maintenance1' in self.registry.requiredextensions:
                    entry += 'transfer, graphics or compute operations'
                else:
                    entry += 'graphics or compute operations'
            else:
                # The queue type must be valid
                queuebits = _parse_queue_bits(cmd)
                assert(queuebits)
                entry += 'The sname:VkCommandPool that pname:commandBuffer was allocated from must: support '
                entry += self.makeProseList(queuebits,
                                            fmt=plf.OR, comma_for_two_elts=True)
                entry += ' operations'
            validity += entry

            # Must be called inside/outside a render pass appropriately
            renderpass = cmd.get('renderpass')

            if renderpass != 'both':
                entry = ValidityEntry(anchor=('renderpass',))
                entry += 'This command must: only be called '
                entry += renderpass
                entry += ' of a render pass instance'
                validity += entry

            # Must be in the right level command buffer
            cmdbufferlevel = cmd.get('cmdbufferlevel')

            if cmdbufferlevel != 'primary,secondary':
                entry = ValidityEntry(anchor=('bufferlevel',))
                entry += 'pname:commandBuffer must: be a '
                entry += cmdbufferlevel
                entry += ' sname:VkCommandBuffer'
                validity += entry

        # Any non-optional arraylengths should specify they must be greater than 0
        array_length_params = ((param, getElemName(param))
                               for param in params
                               if getElemName(param) in arraylengths)

        for param, param_name in array_length_params:
            if param.get('optional') is not None:
                continue

            length = arraylengths[param_name]
            full_length = length.full_reference

            # Is this just a name of a param? If false, then it's some kind of qualified name (a member of a param for instance)
            simple_param_reference = (len(length.param_ref_parts) == 1)
            if not simple_param_reference:
                # Loop through to see if any parameters in the chain are optional
                array_length_parent = cmd
                array_length_optional = False
                for part in length.param_ref_parts:
                    # Overwrite the param so it ends up as the bottom level parameter for later checks
                    param = array_length_parent.find("*/[name='{}']".format(part))

                    # If any parameter in the chain is optional, skip the implicit length requirement
                    array_length_optional |= (param.get('optional') is not None)

                    # Lookup the type of the parameter for the next loop iteration
                    type = param.findtext('type')
                    array_length_parent = self.registry.tree.find("./types/type/[@name='{}']".format(type))

                if array_length_optional:
                    continue

            # Get all the array dependencies
            arrays = cmd.findall(
                "param/[@len='{}'][@optional='true']".format(full_length))

            # Get all the optional array dependencies, including those not generating validity for some reason
            optionalarrays = arrays + \
                cmd.findall(
                    "param/[@len='{}'][@noautovalidity='true']".format(full_length))

            entry = ValidityEntry(anchor=(full_length, 'arraylength'))
            # Allow lengths to be arbitrary if all their dependents are optional
            if optionalarrays and len(optionalarrays) == len(arrays):
                entry += 'If '
                # TODO sync this section from OpenXR once cosmetic changes OK

                optional_array_names = (self.makeParameterName(getElemName(array))
                                        for array in optionalarrays)
                entry += self.makeProseListIs(optional_array_names,
                                              plf.ANY_OR, comma_for_two_elts=True)

                entry += ' not {}, '.format(self.null)

            # TODO end needs sync cosmetic
            if self.paramIsPointer(param):
                entry += 'the value referenced by '

            # Split and re-join here to insert pname: around ::
            entry += '::'.join(self.makeParameterName(part)
                               for part in full_length.split('::'))
            # TODO replace the previous statement with the following when cosmetic changes OK
            # entry += length.get_human_readable(make_param_name=self.makeParameterName)

            entry += ' must: be greater than '
            entry += self.conventions.zero
            validity += entry

        # Find the parents of all objects referenced in this command
        for param in handles:
            # Don't detect a parent for return values!
            if not self.paramIsPointer(param) or self.paramIsConst(param):
                validity += self.makeHandleValidityParent(param, params)

        # Find the common ancestor of all objects referenced in this command
        validity += self.makeAsciiDocHandlesCommonAncestor(
            blockname, handles, params)

        return validity

    def makeThreadSafetyBlock(self, cmd, paramtext):
        """Generate thread-safety validity entries for cmd/structure"""
        # See also makeThreadSafetyBlock in validitygenerator.py
        validity = self.makeValidityCollection(getElemName(cmd))

        # This text varies between projects, so an Asciidoctor attribute is used.
        extsync_prefix = "{externsyncprefix} "

        # Find and add any parameters that are thread unsafe
        explicitexternsyncparams = cmd.findall(paramtext + "[@externsync]")
        if explicitexternsyncparams is not None:
            for param in explicitexternsyncparams:
                externsyncattribs = ExternSyncEntry.parse_externsync_from_param(
                    param)
                param_name = getElemName(param)

                for attrib in externsyncattribs:
                    entry = ValidityEntry()
                    entry += extsync_prefix
                    if attrib.entirely_extern_sync:
                        if self.paramIsArray(param):
                            entry += 'each member of '
                        elif self.paramIsPointer(param):
                            entry += 'the object referenced by '

                        entry += self.makeParameterName(param_name)

                        if attrib.children_extern_sync:
                            entry += ', and any child handles,'

                    else:
                        entry += 'pname:'
                        entry += str(attrib.full_reference)
                        # TODO switch to the following when cosmetic changes OK
                        # entry += attrib.get_human_readable(make_param_name=self.makeParameterName)
                    entry += ' must: be externally synchronized'
                    validity += entry

        # Vulkan-specific
        # For any vkCmd* functions, the command pool is externally synchronized
        if cmd.find('proto/name') is not None and 'vkCmd' in cmd.find('proto/name').text:
            entry = ValidityEntry()
            entry += extsync_prefix
            entry += 'the sname:VkCommandPool that pname:commandBuffer was allocated from must: be externally synchronized'
            validity += entry

        # Find and add any "implicit" parameters that are thread unsafe
        implicitexternsyncparams = cmd.find('implicitexternsyncparams')
        if implicitexternsyncparams is not None:
            for elem in implicitexternsyncparams:
                entry = ValidityEntry()
                entry += extsync_prefix
                entry += elem.text
                entry += ' must: be externally synchronized'
                validity += entry

        return validity

    def makeCommandPropertiesTableEntry(self, cmd, name):

        if 'vkCmd' in name:
            # Must be called inside/outside a render pass appropriately
            cmdbufferlevel = cmd.get('cmdbufferlevel')
            cmdbufferlevel = (' + \n').join(cmdbufferlevel.title().split(','))

            renderpass = cmd.get('renderpass')
            renderpass = renderpass.capitalize()

            #
            # This test for vkCmdFillBuffer is a hack, since we have no path
            # to conditionally have queues enabled or disabled by an extension.
            # As the VU stuff is all moving out (hopefully soon), this hack solves the issue for now
            if name == 'vkCmdFillBuffer':
                if self.isVKVersion11() or 'VK_KHR_maintenance1' in self.registry.requiredextensions:
                    queues = 'Transfer + \nGraphics + \nCompute'
                else:
                    queues = 'Graphics + \nCompute'
            else:
                queues = cmd.get('queues')
                queues = (' + \n').join(queues.title().split(','))

            return '|' + cmdbufferlevel + '|' + renderpass + '|' + queues
        elif 'vkQueue' in name:
            # Must be called inside/outside a render pass appropriately

            queues = cmd.get('queues')
            if queues is None:
                queues = 'Any'
            else:
                queues = (' + \n').join(queues.upper().split(','))

            return '|-|-|' + queues

        return None


    def findRequiredEnums(self, enums):
        """Check each enumerant name in the enums list and remove it if not
        required by the generator. This allows specifying success and error
        codes for extensions that are only included in validity when needed
        for the spec being targeted."""
        return self.keepOnlyRequired(enums, self.registry.enumdict)

    def findRequiredCommands(self, commands):
        """Check each command name in the commands list and remove it if not
        required by the generator.

        This will allow some state operations to take place before endFile."""
        return self.keepOnlyRequired(commands, self.registry.cmddict)

    def keepOnlyRequired(self, names, info_dict):
        """Check each element name in the supplied dictionary and remove it if not
        required by the generator.

        This will allow some operations to take place before endFile no matter the order of generation."""
        # TODO Unpleasantly breaks encapsulation. Should be a method in the registry class

        def is_required(name):
            info = self.registry.lookupElementInfo(name, info_dict)
            if info is None:
                return False
            if not info.required:
                self.logMsg('diag', 'keepOnlyRequired: element',
                            name, 'IS NOT required, skipping')
            return info.required

        return [name
                for name in names
                if is_required(name)]

    def makeReturnCodeList(self, attrib, cmd, name):
        """Return a list of possible return codes for a function.

        attrib is either 'successcodes' or 'errorcodes'.
        """
        return_lines = []
        RETURN_CODE_FORMAT = '* ename:{}'

        codes_attr = cmd.get(attrib)
        if codes_attr:
            codes = self.findRequiredEnums(codes_attr.split(','))
            if codes:
                return_lines.extend((RETURN_CODE_FORMAT.format(code)
                                     for code in codes))

        applicable_ext_codes = (ext_code
                                for ext_code in self.registry.commandextensionsuccesses
                                if ext_code.command == name)
        for ext_code in applicable_ext_codes:
            line = RETURN_CODE_FORMAT.format(ext_code.value)
            if ext_code.extension:
                line += ' [only if {} is enabled]'.format(
                    self.conventions.formatExtension(ext_code.extension))

            return_lines.append(line)
        if return_lines:
            return '\n'.join(return_lines)

        return None

    def makeSuccessCodes(self, cmd, name):
        return self.makeReturnCodeList('successcodes', cmd, name)

    def makeErrorCodes(self, cmd, name):
        return self.makeReturnCodeList('errorcodes', cmd, name)

    def genCmd(self, cmdinfo, name, alias):
        """Command generation."""
        OutputGenerator.genCmd(self, cmdinfo, name, alias)

        # @@@ (Jon) something needs to be done here to handle aliases, probably

        validity = self.makeValidityCollection(name)

        # OpenXR-only: make sure extension is enabled
        # validity.possiblyAddExtensionRequirement(self.currentExtension, 'calling flink:')

        validity += self.makeStructOrCommandValidity(
            cmdinfo.elem, name, cmdinfo.getParams())

        threadsafety = self.makeThreadSafetyBlock(cmdinfo.elem, 'param')
        commandpropertiesentry = None

        # Vulkan-specific
        commandpropertiesentry = self.makeCommandPropertiesTableEntry(
            cmdinfo.elem, name)
        successcodes = self.makeSuccessCodes(cmdinfo.elem, name)
        errorcodes = self.makeErrorCodes(cmdinfo.elem, name)

        # OpenXR-specific
        # self.generateStateValidity(validity, name)

        self.writeInclude('protos', name, validity, threadsafety,
                          commandpropertiesentry, successcodes, errorcodes)

    def genStruct(self, typeinfo, typeName, alias):
        """Struct Generation."""
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)

        # @@@ (Jon) something needs to be done here to handle aliases, probably

        # Anything that's only ever returned can't be set by the user, so shouldn't have any validity information.
        validity = self.makeValidityCollection(typeName)
        threadsafety = []

        # OpenXR-only: make sure extension is enabled
        # validity.possiblyAddExtensionRequirement(self.currentExtension, 'using slink:')

        if typeinfo.elem.get('category') != 'union':
            if typeinfo.elem.get('returnedonly') is None:
                validity += self.makeStructOrCommandValidity(
                    typeinfo.elem, typeName, typeinfo.getMembers())
                threadsafety = self.makeThreadSafetyBlock(typeinfo.elem, 'member')

            else:
                # Need to generate structure type and next pointer chain member validation
                validity += self.makeOutputOnlyStructValidity(
                    typeinfo.elem, typeName, typeinfo.getMembers())

        self.writeInclude('structs', typeName, validity,
                          threadsafety, None, None, None)

    def genGroup(self, groupinfo, groupName, alias):
        """Group (e.g. C "enum" type) generation.
        For the validity generator, this just tags individual enumerants
        as required or not.
        """
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)

        # @@@ (Jon) something needs to be done here to handle aliases, probably

        groupElem = groupinfo.elem

        # Loop over the nested 'enum' tags. Keep track of the minimum and
        # maximum numeric values, if they can be determined; but only for
        # core API enumerants, not extension enumerants. This is inferred
        # by looking for 'extends' attributes.
        for elem in groupElem.findall('enum'):
            name = elem.get('name')
            ei = self.registry.lookupElementInfo(name, self.registry.enumdict)

            # Tag enumerant as required or not
            ei.required = self.isEnumRequired(elem)

    def genType(self, typeinfo, name, alias):
        """Type Generation."""
        OutputGenerator.genType(self, typeinfo, name, alias)

        # @@@ (Jon) something needs to be done here to handle aliases, probably

        category = typeinfo.elem.get('category')
        if category in ('struct', 'union'):
            self.genStruct(typeinfo, name, alias)
