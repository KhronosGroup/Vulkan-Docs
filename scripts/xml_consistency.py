#!/usr/bin/python3
#
# Copyright (c) 2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>
#
# Purpose:      This script checks some "business logic" in the XML registry.

import re
import sys
from pathlib import Path
from collections import defaultdict, deque, namedtuple

from check_spec_links import VulkanEntityDatabase as OrigEntityDatabase
from reg import Registry
from spec_tools.consistency_tools import XMLChecker
from spec_tools.util import findNamedElem, getElemName, getElemType
from apiconventions import APIConventions

# These are extensions which do not follow the usual naming conventions,
# specifying the alternate convention they follow
EXTENSION_ENUM_NAME_SPELLING_CHANGE = {
    'VK_EXT_swapchain_colorspace': 'VK_EXT_SWAPCHAIN_COLOR_SPACE',
}

# These are extensions whose names *look* like they end in version numbers,
# but do not
EXTENSION_NAME_VERSION_EXCEPTIONS = (
    'VK_AMD_gpu_shader_int16',
    'VK_EXT_index_type_uint8',
    'VK_EXT_shader_image_atomic_int64',
    'VK_KHR_video_decode_h264',
    'VK_KHR_video_decode_h265',
    'VK_EXT_video_encode_h264',
    'VK_EXT_video_encode_h265',
    'VK_KHR_external_fence_win32',
    'VK_KHR_external_memory_win32',
    'VK_KHR_external_semaphore_win32',
    'VK_KHR_shader_atomic_int64',
    'VK_KHR_shader_float16_int8',
    'VK_KHR_spirv_1_4',
    'VK_NV_external_memory_win32',
    'VK_RESERVED_do_not_use_146',
    'VK_RESERVED_do_not_use_94',
)

# Exceptions to pointer parameter naming rules
# Keyed by (entity name, type, name).
CHECK_PARAM_POINTER_NAME_EXCEPTIONS = {
    ('vkGetDrmDisplayEXT', 'VkDisplayKHR', 'display') : None,
}

# Exceptions to pNext member requiring an optional attribute
CHECK_MEMBER_PNEXT_OPTIONAL_EXCEPTIONS = (
    'VkVideoEncodeInfoKHR',
    'VkVideoEncodeRateControlLayerInfoKHR',
)

# Exceptions to VK_INCOMPLETE being required for, and only applicable to, array
# enumeration functions
CHECK_ARRAY_ENUMERATION_RETURN_CODE_EXCEPTIONS = (
    'vkGetDeviceFaultInfoEXT',
    'vkEnumerateDeviceLayerProperties',
)

# Exceptions to unknown structure type constants.
# This is most likely an error in this script, not the XML.
# It does not understand Vulkan SC (alternate 'api') types.
CHECK_TYPE_STYPE_EXCEPTIONS = (
    'VK_STRUCTURE_TYPE_PERFORMANCE_QUERY_RESERVATION_INFO_KHR',
    'VK_STRUCTURE_TYPE_PIPELINE_POOL_SIZE',
    'VK_STRUCTURE_TYPE_FAULT_DATA',
    'VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_SC_1_0_FEATURES',
    'VK_STRUCTURE_TYPE_DEVICE_OBJECT_RESERVATION_CREATE_INFO',
    'VK_STRUCTURE_TYPE_PIPELINE_OFFLINE_CREATE_INFO',
    'VK_STRUCTURE_TYPE_FAULT_CALLBACK_INFO',
    'VK_STRUCTURE_TYPE_COMMAND_POOL_MEMORY_RESERVATION_CREATE_INFO',
    'VK_STRUCTURE_TYPE_DEVICE_SEMAPHORE_SCI_SYNC_POOL_RESERVATION_CREATE_INFO_NV',
    'VK_STRUCTURE_TYPE_COMMAND_POOL_MEMORY_CONSUMPTION',
    'VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_SC_1_0_PROPERTIES',
)

def get_extension_commands(reg):
    extension_cmds = set()
    for ext in reg.extensions:
        for cmd in ext.findall('./require/command[@name]'):
            extension_cmds.add(cmd.get('name'))
    return extension_cmds


def get_enum_value_names(reg, enum_type):
    names = set()
    result_elem = reg.groupdict[enum_type].elem
    for val in result_elem.findall('./enum[@name]'):
        names.add(val.get('name'))
    return names


# Regular expression matching an extension name ending in a (possible) version number
EXTNAME_RE = re.compile(r'(?P<base>(\w+[A-Za-z]))(?P<version>\d+)')

DESTROY_PREFIX = 'vkDestroy'
TYPEENUM = 'VkStructureType'

SPECIFICATION_DIR = Path(__file__).parent.parent
REVISION_RE = re.compile(r' *[*] Revision (?P<num>[1-9][0-9]*),.*')


def get_extension_source(extname):
    fn = f'{extname}.adoc'
    return str(SPECIFICATION_DIR / 'appendices' / fn)


class EntityDatabase(OrigEntityDatabase):

    # Override base class method to not exclude 'disabled' extensions
    def getExclusionSet(self):
        """Return a set of "support=" attribute strings that should not be included in the database.

        Called only during construction."""

        return set(())

    def makeRegistry(self):
        try:
            import lxml.etree as etree
            HAS_LXML = True
        except ImportError:
            HAS_LXML = False
        if not HAS_LXML:
            return super().makeRegistry()

        registryFile = str(SPECIFICATION_DIR / 'xml/vk.xml')
        registry = Registry()
        registry.filename = registryFile
        registry.loadElementTree(etree.parse(registryFile))
        return registry


class Checker(XMLChecker):
    def __init__(self):
        manual_types_to_codes = {
            # These are hard-coded "manual" return codes:
            # the codes of the value (string, list, or tuple)
            # are available for a command if-and-only-if
            # the key type is passed as an input.
            'VkFormat': 'VK_ERROR_FORMAT_NOT_SUPPORTED'
        }
        forward_only = {
            # Like the above, but these are only valid in the
            # "type implies return code" direction
        }
        reverse_only = {
            # like the above, but these are only valid in the
            # "return code implies type or its descendant" direction
            # "XrDuration": "XR_TIMEOUT_EXPIRED"
        }
        # Some return codes are related in that only one of a set
        # may be returned by a command
        # (eg. XR_ERROR_SESSION_RUNNING and XR_ERROR_SESSION_NOT_RUNNING)
        self.exclusive_return_code_sets = tuple(
            # set(("XR_ERROR_SESSION_NOT_RUNNING", "XR_ERROR_SESSION_RUNNING")),
        )

        # This is used to report collisions.
        conventions = APIConventions()
        db = EntityDatabase()

        self.extension_cmds = get_extension_commands(db.registry)
        self.return_codes = get_enum_value_names(db.registry, 'VkResult')
        self.structure_types = get_enum_value_names(db.registry, TYPEENUM)

        # Dict of entity name to a list of messages to suppress. (Exclude any context data and "Warning:"/"Error:")
        # Keys are entity names, values are tuples or lists of message text to suppress.
        suppressions = {}

        # Structures explicitly allowed to have 'limittype' attributes
        self.allowedStructs = set((
            'VkFormatProperties',
            'VkFormatProperties2',
            'VkPhysicalDeviceProperties',
            'VkPhysicalDeviceProperties2',
            'VkPhysicalDeviceLimits',
            'VkQueueFamilyProperties',
            'VkQueueFamilyProperties2',
            'VkSparseImageFormatProperties',
            'VkSparseImageFormatProperties2',
        ))

        # Substructures of allowed structures. This can be found by looking
        # at tags, but there are so few cases that it is hardwired for now.
        self.nestedStructs = set((
            'VkPhysicalDeviceLimits',
            'VkPhysicalDeviceSparseProperties',
            'VkPhysicalDeviceProperties',
            'VkQueueFamilyProperties',
            'VkSparseImageFormatProperties',
        ))

        # Structures all of whose (non pNext/sType) members are required to
        # have 'limittype' attributes, as are their descendants
        self.requiredStructs = set((
            'VkPhysicalDeviceProperties',
            'VkPhysicalDeviceProperties2',
            'VkPhysicalDeviceLimits',
            'VkSparseImageFormatProperties',
            'VkSparseImageFormatProperties2',
        ))

        # Structures which have already have their limittype attributes validated
        self.validatedLimittype = set()

        # Initialize superclass
        super().__init__(entity_db=db, conventions=conventions,
                         manual_types_to_codes=manual_types_to_codes,
                         forward_only_types_to_codes=forward_only,
                         reverse_only_types_to_codes=reverse_only,
                         suppressions=suppressions)

    def check(self):
        """Extends base class behavior with additional checks"""

        # This test is not run on a per-structure basis, but loops over
        # specific structures
        self.check_type_required_limittype()

        super().check()

    def check_command(self, name, info):
        """Extends base class behavior with additional checks"""

        if name[0:5] == 'vkCmd':
            if info.elem.get('tasks') is None:
                self.record_error(f'{name} is a vkCmd* command, but is missing a "tasks" attribute')

        super().check_command(name, info)

    def check_command_return_codes_basic(self, name, info,
                                         successcodes, errorcodes):
        """Check a command's return codes for consistency.

        Called on every command."""
        # Check that all extension commands can return the code associated
        # with trying to use an extension that was not enabled.
        # if name in self.extension_cmds and UNSUPPORTED not in errorcodes:
        #     self.record_error('Missing expected return code',
        #                       UNSUPPORTED,
        #                       'implied due to being an extension command')

        codes = successcodes.union(errorcodes)

        # Check that all return codes are recognized.
        unrecognized = codes - self.return_codes
        if unrecognized:
            self.record_error('Unrecognized return code(s):',
                              unrecognized)

        elem = info.elem
        params = [(getElemName(elt), elt) for elt in elem.findall('param')]

        def is_count_output(name, elt):
            # Must end with Count or Size,
            # not be const,
            # and be a pointer (detected by naming convention)
            return (name.endswith('Count') or name.endswith('Size')) \
                and (elt.tail is None or 'const' not in elt.tail) \
                and (name.startswith('p'))

        countParams = [elt
                       for name, elt in params
                       if is_count_output(name, elt)]
        if countParams:
            assert(len(countParams) == 1)
            if 'VK_INCOMPLETE' not in successcodes:
                message = "Apparent enumeration of an array without VK_INCOMPLETE in successcodes for command {}.".format(name)
                if name in CHECK_ARRAY_ENUMERATION_RETURN_CODE_EXCEPTIONS:
                    self.record_warning('(Allowed exception)', message)
                else:
                    self.record_error(message)

        elif 'VK_INCOMPLETE' in successcodes:
            message = "VK_INCOMPLETE in successcodes of command {} that is apparently not an array enumeration.".format(name)
            if name in CHECK_ARRAY_ENUMERATION_RETURN_CODE_EXCEPTIONS:
                self.record_warning('(Allowed exception)', message)
            else:
                self.record_error(message)

    def check_param(self, param):
        """Check a member of a struct or a param of a function.

        Called from check_params."""
        super().check_param(param)

        if not self.is_api_type(param):
            return

        param_text = ''.join(param.itertext())
        param_name = getElemName(param)

        # Make sure the number of leading 'p' matches the pointer count.
        pointercount = param.find('type').tail
        if pointercount:
            pointercount = pointercount.count('*')
        if pointercount:
            prefix = 'p' * pointercount
            if not param_name.startswith(prefix):
                param_type = param.find('type').text
                message = "Apparently incorrect pointer-related name prefix for {} - expected it to start with '{}'".format(
                    param_text, prefix)
                if (self.entity, param_type, param_name) in CHECK_PARAM_POINTER_NAME_EXCEPTIONS:
                    self.record_warning('(Allowed exception)', message, elem=param)
                else:
                    self.record_error(message, elem=param)

        # Make sure no members have optional="false" attributes
        optional = param.get('optional')
        if optional == 'false':
            message = f'{self.entity}.{param_name} member has disallowed \'optional="false"\' attribute (remove this attribute)'
            self.record_error(message, elem=param)

        # Make sure pNext members have optional="true" attributes
        if param_name == self.conventions.nextpointer_member_name:
            optional = param.get('optional')
            if optional is None or optional != 'true':
                message = f'{self.entity}.pNext member is missing \'optional="true"\' attribute'
                if self.entity in CHECK_MEMBER_PNEXT_OPTIONAL_EXCEPTIONS:
                    self.record_warning('(Allowed exception)', message, elem=param)
                else:
                    self.record_error(message, elem=param)

    def check_type_stype(self, name, info, type_elts):
        """Check a struct type's sType member"""
        if len(type_elts) > 1:
            self.record_error(
                'Have more than one member of type', TYPEENUM)
        else:
            type_elt = type_elts[0]
            val = type_elt.get('values')
            if val and val not in self.structure_types:
                message = f'{self.entity} has unknown structure type constant {val}'
                if val in CHECK_TYPE_STYPE_EXCEPTIONS:
                    self.record_warning('(Allowed exception)', message)
                else:
                    self.record_error(message)

    def check_type_pnext(self, name, info):
        """Check a struct type's pNext member, if present"""

        next_name = self.conventions.nextpointer_member_name
        next_member = findNamedElem(info.elem.findall('member'), next_name)
        if next_member is not None:
            # Ensure that the 'optional' attribute is set to 'true'
            optional = next_member.get('optional')
            if optional is None or optional != 'true':
                message = f'{name}.{next_name} member is missing \'optional="true"\' attribute'
                if name in CHECK_MEMBER_PNEXT_OPTIONAL_EXCEPTIONS:
                    self.record_warning('(Allowed exception)', message)
                else:
                    self.record_error(message)

    def __isLimittypeStruct(self, name, info, allowedStructs):
        """Check if a type element is a structure allowed to have 'limittype' attributes
           name - name of a structure
           info - corresponding TypeInfo object
           allowedStructs - set of struct names explicitly allowed"""

        # Is this an explicitly allowed struct?
        if name in allowedStructs:
            return True

        # Is this a struct extending an explicitly allowed struct?
        extends = info.elem.get('structextends')
        if extends is not None:
            # See if any name in the structextends attribute is an allowed
            # struct
            if len(set(extends.split(',')) & allowedStructs) > 0:
                return True

        return False

    def __validateStructLimittypes(self, name, info, requiredLimittype):
        """Validate 'limittype' attributes for a single struct.
           info - TypeInfo for a struct <type>
           requiredLimittype - True if members *must* have a limittype"""

        # Do not re-check structures
        if name in self.validatedLimittype:
            return {}
        self.validatedLimittype.add(name)

        limittypeDiags = namedtuple('limittypeDiags', ['missing', 'invalid'])
        badFields = defaultdict(lambda : limittypeDiags(missing=[], invalid=[]))
        validLimittypes = { 'min', 'max', 'pot', 'mul', 'bits', 'bitmask', 'range', 'struct', 'exact', 'noauto' }
        for member in info.getMembers():
            memberName = member.findtext('name')
            if memberName in ['sType', 'pNext']:
                continue
            limittype = member.get('limittype')
            if limittype is None:
                # Do not tag this as missing if it is not required
                if requiredLimittype:
                    badFields[info.elem.get('name')].missing.append(memberName)
            elif limittype == 'struct':
                typeName = member.findtext('type')
                memberType = self.reg.typedict[typeName]
                badFields.update(self.__validateStructLimittypes(typeName, memberType, requiredLimittype))
            else:
                for value in limittype.split(','):
                    if value not in validLimittypes:
                        badFields[info.elem.get('name')].invalid.append(memberName)

        return badFields

    def check_type_disallowed_limittype(self, name, info):
        """Check if a struct type's members cannot have the 'limittype' attribute"""

        # If not allowed to have limittypes, verify this for each member
        if not self.__isLimittypeStruct(name, info, self.allowedStructs.union(self.nestedStructs)):
            for member in info.getMembers():
                if member.get('limittype') is not None:
                    memname = member.findtext('name')
                    self.record_error(f'{name} member {memname} has disallowed limittype attribute')

    def check_type_optional_value(self, name, info):
        """Check if a struct type's members have disallowed 'optional' attribute values"""

        for member in info.getMembers():
            # Make sure no members have optional="false" attributes
            optional = member.get('optional')
            if optional == 'false':
                memname = member.findtext('name')
                message = f'{name} member {memname} has disallowed \'optional="false"\' attribute (remove this attribute)'
                self.record_error(message, elem=member)

    def check_type_required_limittype(self):
        """Check struct type members which must have the 'limittype' attribute

        Called from check."""

        for name in self.allowedStructs:
            # Assume that only extending structs of structs explicitly
            # requiring limittypes also require them
            requiredLimittype = (name in self.requiredStructs)

            info = self.reg.typedict[name]

            self.set_error_context(entity=name, elem=info.elem)

            badFields = self.__validateStructLimittypes(name, info, requiredLimittype)
            for extendingStructName in self.reg.validextensionstructs[name]:
                extendingStruct = self.reg.typedict[extendingStructName]
                badFields.update(self.__validateStructLimittypes(extendingStructName, extendingStruct, requiredLimittype))

            if badFields:
                for key in sorted(badFields.keys()):
                    diags = badFields[key]
                    if diags.missing:
                        self.record_error(f'{name} missing limittype for members {", ".join(badFields[key].missing)}')
                    if diags.invalid:
                        self.record_error(f'{name} has invalid limittype for members {", ".join(badFields[key].invalid)}')

    def check_type(self, name, info, category):
        """Check a type's XML data for consistency.

        Called from check."""

        if category == 'struct':
            type_elts = [elt
                         for elt in info.elem.findall('member')
                         if getElemType(elt) == TYPEENUM]

            if type_elts:
                self.check_type_stype(name, info, type_elts)
                self.check_type_pnext(name, info)

            # Check for disallowed limittypes on all structures
            self.check_type_disallowed_limittype(name, info)

            # Check for disallowed 'optional' values
            self.check_type_optional_value(name, info)
        elif category == 'bitmask':
            if 'Flags' in name:
                expected_require = name.replace('Flags', 'FlagBits')
                require = info.elem.get('require')
                if require is not None and expected_require != require:
                    self.record_error('Unexpected require attribute value:',
                                      'got', require,
                                      'but expected', expected_require)
        super().check_type(name, info, category)

    def check_extension(self, name, info, supported):
        """Check an extension's XML data for consistency.

        Called from check."""

        elem = info.elem
        enums = elem.findall('./require/enum[@name]')

        # If extension name is not on the exception list and matches the
        # versioned-extension pattern, map the extension name to the version
        # name with the version as a separate word. Otherwise just map it to
        # the upper-case version of the extension name.

        matches = EXTNAME_RE.fullmatch(name)
        ext_versioned_name = False
        if name in EXTENSION_ENUM_NAME_SPELLING_CHANGE:
            ext_enum_name = EXTENSION_ENUM_NAME_SPELLING_CHANGE.get(name)
        elif matches is None or name in EXTENSION_NAME_VERSION_EXCEPTIONS:
            # This is the usual case, either a name that does not look
            # versioned, or one that does but is on the exception list.
            ext_enum_name = name.upper()
        else:
            # This is a versioned extension name.
            # Treat the version number as a separate word.
            base = matches.group('base')
            version = matches.group('version')
            ext_enum_name = base.upper() + '_' + version
            # Keep track of this case
            ext_versioned_name = True

        # Look for the expected SPEC_VERSION token name
        version_name = f'{ext_enum_name}_SPEC_VERSION'
        version_elem = findNamedElem(enums, version_name)

        if version_elem is None:
            # Did not find a SPEC_VERSION enum matching the extension name
            if ext_versioned_name:
                suffix = '\n\
    Make sure that trailing version numbers in extension names are treated\n\
    as separate words in extension enumerant names. If this is an extension\n\
    whose name ends in a number which is not a version, such as "...h264"\n\
    or "...int16", add it to EXTENSION_NAME_VERSION_EXCEPTIONS in\n\
    scripts/xml_consistency.py.'
            else:
                suffix = ''
            self.record_error(f'Missing version enum {version_name}{suffix}')
        elif supported:
            # Skip unsupported / disabled extensions for these checks

            fn = get_extension_source(name)
            revisions = []
            with open(fn, 'r', encoding='utf-8') as fp:
                for line in fp:
                    line = line.rstrip()
                    match = REVISION_RE.match(line)
                    if match:
                        revisions.append(int(match.group('num')))
            ver_from_xml = version_elem.get('value')
            if revisions:
                ver_from_text = str(max(revisions))
                if ver_from_xml != ver_from_text:
                    self.record_error('Version enum mismatch: spec text indicates', ver_from_text,
                                      'but XML says', ver_from_xml)
            else:
                if ver_from_xml == '1':
                    self.record_warning(
                        "Cannot find version history in spec text - make sure it has lines starting exactly like '* Revision 1, ....'",
                        filename=fn)
                else:
                    self.record_warning("Cannot find version history in spec text, but XML reports a non-1 version number", ver_from_xml,
                                        " - make sure the spec text has lines starting exactly like '* Revision 1, ....'",
                                        filename=fn)

        name_define = f'{ext_enum_name}_EXTENSION_NAME'
        name_elem = findNamedElem(enums, name_define)
        if name_elem is None:
            self.record_error('Missing name enum', name_define)
        else:
            # Note: etree handles the XML entities here and turns &quot; back into "
            expected_name = f'"{name}"'
            name_val = name_elem.get('value')
            if name_val != expected_name:
                self.record_error('Incorrect name enum: expected', expected_name,
                                  'got', name_val)

        super().check_extension(name, info, supported)

    def check_format(self):
        """Check an extension's XML data for consistency.

        Called from check."""

        astc3d_formats = [
                'VK_FORMAT_ASTC_3x3x3_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_3x3x3_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_3x3x3_SFLOAT_BLOCK_EXT',
                'VK_FORMAT_ASTC_4x3x3_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_4x3x3_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_4x3x3_SFLOAT_BLOCK_EXT',
                'VK_FORMAT_ASTC_4x4x3_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_4x4x3_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_4x4x3_SFLOAT_BLOCK_EXT',
                'VK_FORMAT_ASTC_4x4x4_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_4x4x4_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_4x4x4_SFLOAT_BLOCK_EXT',
                'VK_FORMAT_ASTC_5x4x4_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_5x4x4_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_5x4x4_SFLOAT_BLOCK_EXT',
                'VK_FORMAT_ASTC_5x5x4_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_5x5x4_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_5x5x4_SFLOAT_BLOCK_EXT',
                'VK_FORMAT_ASTC_5x5x5_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_5x5x5_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_5x5x5_SFLOAT_BLOCK_EXT',
                'VK_FORMAT_ASTC_6x5x5_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_6x5x5_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_6x5x5_SFLOAT_BLOCK_EXT',
                'VK_FORMAT_ASTC_6x6x5_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_6x6x5_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_6x6x5_SFLOAT_BLOCK_EXT',
                'VK_FORMAT_ASTC_6x6x6_UNORM_BLOCK_EXT',
                'VK_FORMAT_ASTC_6x6x6_SRGB_BLOCK_EXT',
                'VK_FORMAT_ASTC_6x6x6_SFLOAT_BLOCK_EXT'
        ]

        # Need to build list of formats from rest of <enums>
        enum_formats = []
        for enum in self.reg.groupdict['VkFormat'].elem:
            if enum.get('alias') is None and enum.get('name') != 'VK_FORMAT_UNDEFINED':
                enum_formats.append(enum.get('name'))

        found_formats = []
        for name, info in self.reg.formatsdict.items():
            found_formats.append(name)
            self.set_error_context(entity=name, elem=info.elem)

            if name not in enum_formats:
                self.record_error('The <format> has no matching <enum> for', name)

            # Check never just 1 plane
            plane_elems = info.elem.findall('plane')
            if len(plane_elems) == 1:
                self.record_error('The <format> has only 1 <plane> for', name)

            valid_chroma = ['420', '422', '444']
            if info.elem.get('chroma') and info.elem.get('chroma') not in valid_chroma:
                self.record_error('The <format> has chroma is not a valid value for', name)

            # The formatsgenerator.py assumes only 1 <spirvimageformat> tag.
            # If this changes in the future, remove this warning and update generator script
            spirv_image_format = info.elem.findall('spirvimageformat')
            if len(spirv_image_format) > 1:
                self.record_error('More than 1 <spirvimageformat> but formatsgenerator.py is not updated, for format', name)

        # Re-loop to check the other way if the <format> is missing
        for enum in self.reg.groupdict['VkFormat'].elem:
            name = enum.get('name')
            if enum.get('alias') is None and name != 'VK_FORMAT_UNDEFINED':
                if name not in found_formats and name not in astc3d_formats:
                    self.set_error_context(entity=name, elem=enum)
                    self.record_error('The <enum> has no matching <format> for ', name)

        super().check_format()


if __name__ == '__main__':

    ckr = Checker()
    ckr.check()

    if ckr.fail:
        sys.exit(1)
