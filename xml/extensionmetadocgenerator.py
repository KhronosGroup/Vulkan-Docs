#!/usr/bin/python3 -i
#
# Copyright (c) 2013-2018 The Khronos Group Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os,re,sys,functools
from generator import *
from functools import total_ordering

# ExtensionMetaDocGeneratorOptions - subclass of GeneratorOptions.
class ExtensionMetaDocGeneratorOptions(GeneratorOptions):
    """Represents options during extension metainformation generation for Asciidoc"""
    def __init__(self,
                 filename = None,
                 directory = '.',
                 apiname = None,
                 profile = None,
                 versions = '.*',
                 emitversions = '.*',
                 defaultExtensions = None,
                 addExtensions = None,
                 removeExtensions = None,
                 emitExtensions = None,
                 sortProcedure = regSortFeatures):
        GeneratorOptions.__init__(self, filename, directory, apiname, profile,
                                  versions, emitversions, defaultExtensions,
                                  addExtensions, removeExtensions,
                                  emitExtensions, sortProcedure)

@total_ordering
class Extension:
    def __init__(self,
                 generator, # needed for logging
                 filename,
                 name,
                 number,
                 type,
                 requires,
                 requiresCore,
                 contact,
                 promotedTo,
                 deprecatedBy,
                 obsoletedBy,
                 revision ):
        self.generator = generator
        self.filename = filename
        self.name = name
        self.number = number
        self.type = type
        self.requires = requires
        self.requiresCore = requiresCore
        self.contact = contact
        self.promotedTo = promotedTo
        self.deprecatedBy = deprecatedBy
        self.obsoletedBy = obsoletedBy
        self.revision = revision

        self.deprecationType = None
        self.supercedingVkVersion = None
        self.supercedingExtension = None

        if self.promotedTo is not None and self.deprecatedBy is not None and self.obsoletedBy is not None:
            self.generator.logMsg('warn', 'All \'promotedto\', \'deprecatedby\' and \'obsoletedby\' attributes used on extension ' + self.name + '! Ignoring \'promotedto\' and \'deprecatedby\'.')
        elif self.promotedTo is not None and self.deprecatedBy is not None:
            self.generator.logMsg('warn', 'Both \'promotedto\' and \'deprecatedby\' attributes used on extension ' + self.name + '! Ignoring \'deprecatedby\'.')
        elif self.promotedTo is not None and self.obsoletedBy is not None:
            self.generator.logMsg('warn', 'Both \'promotedto\' and \'obsoletedby\' attributes used on extension ' + self.name + '! Ignoring \'promotedto\'.')
        elif self.deprecatedBy is not None and self.obsoletedBy is not None:
            self.generator.logMsg('warn', 'Both \'deprecatedby\' and \'obsoletedby\' attributes used on extension ' + self.name + '! Ignoring \'deprecatedby\'.')

        superceededBy = None
        if self.promotedTo is not None:
            self.deprecationType = 'promotion'
            superceededBy = promotedTo
        elif self.deprecatedBy is not None:
            self.deprecationType = 'deprecation'
            superceededBy = deprecatedBy
        elif self.obsoletedBy is not None:
            self.deprecationType = 'obsoletion'
            superceededBy = obsoletedBy

        if superceededBy is not None:
            if superceededBy == '' and not self.deprecationType == 'promotion':
                pass # supercedingVkVersion, supercedingExtension == None
            elif superceededBy.startswith('VK_VERSION_'):
                self.supercedingVkVersion = superceededBy
            elif superceededBy.startswith('VK_'):
                self.supercedingExtension = superceededBy
            else:
                self.generator.logMsg('error', 'Unrecognized ' + self.deprecationType + ' attribute value \'' + superceededBy + '\'!')

    def __str__(self): return self.name

    def __eq__(self, other): return self.name == other.name
    def __ne__(self, other): return self.name != other.name
    def __lt__(self, other):
        me_is_KHR = self.name.startswith( 'VK_KHR' )
        me_is_EXT = self.name.startswith( 'VK_EXT' )
        he_is_KHR = other.name.startswith( 'VK_KHR' )
        he_is_EXT = other.name.startswith( 'VK_EXT' )

        swap = False
        if me_is_KHR and not he_is_KHR:
            return not swap
        elif he_is_KHR and not me_is_KHR:
            return swap
        elif me_is_EXT and not he_is_EXT:
            return not swap
        elif he_is_EXT and not me_is_EXT:
            return swap
        else:
            return self.name < other.name

    def typeToStr(self):
        if self.type == 'instance':
            return 'Instance extension'
        elif self.type == 'device':
            return 'Device extension'
        elif self.type != None:
            self.generator.logMsg('warn', 'The type attribute of ' + self.name + ' extension is neither \'instance\' nor \'device\'. That is invalid (at the time this script was written).')
            write('    ' + type.capitalize(), file=fp)
        else: # should be unreachable
            self.generator.logMsg('error', 'Logic error in typeToStr(): Missing type attribute!')

    def conditionalLinkCoreVk(self, vulkanVersion, linkSuffix):
        versionMatch = re.match(r'VK_VERSION_(\d+)_(\d+)', vulkanVersion)
        major = versionMatch.group(1)
        minor = versionMatch.group(2)

        dottedVersion = major + '.' + minor

        doc  = 'ifdef::' + vulkanVersion + '[]\n'
        doc += '    <<versions-' + dottedVersion + linkSuffix + ', Vulkan ' + dottedVersion + '>>\n'
        doc += 'endif::' + vulkanVersion + '[]\n'
        doc += 'ifndef::' + vulkanVersion + '[]\n'
        doc += '    Vulkan ' + dottedVersion + '\n'
        doc += 'endif::' + vulkanVersion + '[]\n'

        return doc

    def conditionalLinkExt(self, extName, indent = '    '):
        doc  = 'ifdef::' + extName + '[]\n'
        doc +=  indent + '<<' + extName + '>>\n'
        doc += 'endif::' + extName + '[]\n'
        doc += 'ifndef::' + extName + '[]\n'
        doc += indent + '`' + extName + '`\n'
        doc += 'endif::' + extName + '[]\n'

        return doc

    def resolveDeprecationChain(self, extensionsList, succeededBy, file):
        ext = next(x for x in extensionsList if x.name == succeededBy)

        if ext.deprecationType:
            if ext.deprecationType == 'promotion':
                if ext.supercedingVkVersion:
                    write('  ** Which in turn was _promoted_ to\n' + ext.conditionalLinkCoreVk(ext.supercedingVkVersion, '-promotions'), file=file)
                else: # ext.supercedingExtension
                    write('  ** Which in turn was _promoted_ to extension\n' + ext.conditionalLinkExt(ext.supercedingExtension), file=file)
                    ext.resolveDeprecationChain(extensionsList, ext.supercedingExtension, file)
            elif ext.deprecationType == 'deprecation':
                if ext.supercedingVkVersion:
                    write('  ** Which in turn was _deprecated_ by\n' + ext.conditionalLinkCoreVk(ext.supercedingVkVersion, '-new-feature'), file=file)
                elif ext.supercedingExtension:
                    write('  ** Which in turn was _deprecated_ by\n' + ext.conditionalLinkExt(ext.supercedingExtension) + '    extension', file=file)
                    ext.resolveDeprecationChain(extensionsList, ext.supercedingExtension, file)
                else:
                    write('  ** Which in turn was _deprecated_ without replacement', file=file)
            elif ext.deprecationType == 'obsoletion':
                if ext.supercedingVkVersion:
                    write('  ** Which in turn was _obsoleted_ by\n' + ext.conditionalLinkCoreVk(ext.supercedingVkVersion, '-new-feature'), file=file)
                elif ext.supercedingExtension:
                    write('  ** Which in turn was _obsoleted_ by\n' + ext.conditionalLinkExt(ext.supercedingExtension) + '    extension', file=file)
                    ext.resolveDeprecationChain(extensionsList, ext.supercedingExtension, file)
                else:
                    write('  ** Which in turn was _obsoleted_ without replacement', file=file)
            else: # should be unreachable
                self.generator.logMsg('error', 'Logic error in resolveDeprecationChain(): deprecationType is neither \'promotion\', \'deprecation\' nor \'obsoletion\'!')


    def makeMetafile(self, extensionsList):
        fp = self.generator.newFile(self.filename)

        write('[[' + self.name + ']]', file=fp)
        write('=== ' + self.name, file=fp)
        write('', file=fp)

        write('*Name String*::', file=fp)
        write('    `' + self.name + '`', file=fp)

        write('*Extension Type*::', file=fp)
        write('    ' + self.typeToStr(), file=fp)

        write('*Registered Extension Number*::', file=fp)
        write('    ' + self.number, file=fp)

        write('*Revision*::', file=fp)
        write('    ' + self.revision, file=fp)

        # Only Vulkan extension dependencies are coded in XML, others are explicit
        write('*Extension and Version Dependencies*::', file=fp)
        write('  * Requires Vulkan ' + self.requiresCore, file=fp)
        if self.requires:
            for dep in self.requires.split(','):
                write('  * Requires `<<' + dep + '>>`', file=fp)

        if self.deprecationType:
            write('*Deprecation state*::', file=fp)

            if self.deprecationType == 'promotion':
                if self.supercedingVkVersion:
                    write('  * _Promoted_ to\n' + self.conditionalLinkCoreVk(self.supercedingVkVersion, '-promotions'), file=fp)
                else: # ext.supercedingExtension
                    write('  * _Promoted_ to\n' + self.conditionalLinkExt(self.supercedingExtension) + '    extension', file=fp)
                    self.resolveDeprecationChain(extensionsList, self.supercedingExtension, fp)
            elif self.deprecationType == 'deprecation':
                if self.supercedingVkVersion:
                    write('  * _Deprecated_ by\n' + self.conditionalLinkCoreVk(self.supercedingVkVersion, '-new-features'), file=fp)
                elif self.supercedingExtension:
                    write('  * _Deprecated_ by\n' + self.conditionalLinkExt(self.supercedingExtension) + '    extension' , file=fp)
                    self.resolveDeprecationChain(extensionsList, self.supercedingExtension, fp)
                else:
                    write('  * _Deprecated_ without replacement' , file=fp)
            elif self.deprecationType == 'obsoletion':
                if self.supercedingVkVersion:
                    write('  * _Obsoleted_ by\n' + self.conditionalLinkCoreVk(self.supercedingVkVersion, '-new-features'), file=fp)
                elif self.supercedingExtension:
                    write('  * _Obsoleted_ by\n' + self.conditionalLinkExt(self.supercedingExtension) + '    extension' , file=fp)
                    self.resolveDeprecationChain(extensionsList, self.supercedingExtension, fp)
                else:
                    # TODO: Does not make sense to retroactively ban use of extensions from 1.0.
                    #       Needs some tweaks to the semantics and this message, when such extension(s) occur.
                    write('  * _Obsoleted_ without replacement' , file=fp)
            else: # should be unreachable
                self.generator.logMsg('error', 'Logic error in makeMetafile(): deprecationType is neither \'promotion\', \'deprecation\' nor \'obsoletion\'!')

        write('*Contact*::', file=fp)
        contacts = self.contact.split(',')
        for c in contacts:
            write('  * ' + c, file=fp)

        fp.close()


# ExtensionMetaDocOutputGenerator - subclass of OutputGenerator.
# Generates AsciiDoc includes with metainformation for the Vulkan extension
# appendices. The fields used from <extension> tags in vk.xml are:
#
# name          extension name string
# number        extension number (optional)
# contact       name and github login or email address (optional)
# type          'instance' | 'device' (optional)
# requires      list of comma-separate requires Vulkan extensions (optional)
# requiresCore  required core version of Vulkan (optional)
# promotedTo    extension or Vulkan version it was promoted to
# deprecatedBy   extension or Vulkan version which deprecated this extension,
#                or empty string if deprecated without replacement
# obsoletedBy   extension or Vulkan version which obsoleted this extension,
#                or empty string if obsoleted without replacement
#
# ---- methods ----
# ExtensionMetaDocOutputGenerator(errFile, warnFile, diagFile) - args as for
#   OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# beginFile(genOpts)
# endFile()
# beginFeature(interface, emit)
# endFeature()
class ExtensionMetaDocOutputGenerator(OutputGenerator):
    """Generate specified API interfaces in a specific style, such as a C header"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
        self.extensions = []

    def newFile(self, filename):
        self.logMsg('diag', '# Generating include file:', filename)
        fp = open(filename, 'w', encoding='utf-8')
        write('// WARNING: DO NOT MODIFY! This file is automatically generated from the vk.xml registry', file=fp)
        return fp

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        self.directory = self.genOpts.directory

        # Create subdirectory, if needed
        self.makeDir(self.directory)

    def conditionalExt(self, extName, content, ifdef = None, condition = None):
        doc = ''

        innerdoc  = 'ifdef::' + extName + '[]\n'
        innerdoc += content + '\n'
        innerdoc += 'endif::' + extName + '[]\n'

        if ifdef:
            if ifdef == 'ifndef':
                if condition:
                    doc += 'ifndef::' + condition + '[]\n'
                    doc += innerdoc
                    doc += 'endif::' + condition + '[]\n'
                else: # no condition is as if condition is defined; "nothing" is always defined :p
                    pass # so no output
            elif ifdef == 'ifdef':
                if condition:
                    doc += 'ifdef::' + condition + '+' + extName + '[]\n'
                    doc += content + '\n' # does not include innerdoc; the ifdef was merged with the one above
                    doc += 'endif::' + condition + '+' + extName + '[]\n'
                else: # no condition is as if condition is defined; "nothing" is always defined :p
                    doc += innerdoc
            else: # should be unreachable
                self.generator.logMsg('error', 'Logic error in conditionalExt(): ifdef is neither \'ifdef \' nor \'ifndef\'!')
        else:
            doc += innerdoc

        return doc

    def endFile(self):
        self.extensions.sort()

        for ext in self.extensions:
            ext.makeMetafile(self.extensions)

        promotedExtensions = {}
        for ext in self.extensions:
            if ext.deprecationType == 'promotion' and ext.supercedingVkVersion:
                promotedExtensions.setdefault(ext.supercedingVkVersion, []).append(ext)

        for coreVersion, extensions in promotedExtensions.items():
            promoted_extensions_fp = self.newFile(self.directory + '/promoted_extensions_' + coreVersion + '.txt')

            for ext in extensions:
                indent = ''
                write('  * {blank}\n+\n' + ext.conditionalLinkExt(ext.name, indent), file=promoted_extensions_fp)

            promoted_extensions_fp.close()

        current_extensions_appendix_fp = self.newFile(self.directory + '/current_extensions_appendix.txt')
        deprecated_extensions_appendix_fp = self.newFile(self.directory + '/deprecated_extensions_appendix.txt')
        current_extension_appendices_fp = self.newFile(self.directory + '/current_extension_appendices.txt')
        current_extension_appendices_toc_fp = self.newFile(self.directory + '/current_extension_appendices_toc.txt')
        deprecated_extension_appendices_fp = self.newFile(self.directory + '/deprecated_extension_appendices.txt')
        deprecated_extension_appendices_toc_fp = self.newFile(self.directory + '/deprecated_extension_appendices_toc.txt')
        deprecated_extensions_guard_macro_fp = self.newFile(self.directory + '/deprecated_extensions_guard_macro.txt')

        write('include::deprecated_extensions_guard_macro.txt[]', file=current_extensions_appendix_fp)
        write('', file=current_extensions_appendix_fp)
        write('ifndef::HAS_DEPRECATED_EXTENSIONS[]', file=current_extensions_appendix_fp)
        write('[[extension-appendices-list]]', file=current_extensions_appendix_fp)
        write('== List of Extensions', file=current_extensions_appendix_fp)
        write('endif::HAS_DEPRECATED_EXTENSIONS[]', file=current_extensions_appendix_fp)
        write('ifdef::HAS_DEPRECATED_EXTENSIONS[]', file=current_extensions_appendix_fp)
        write('[[extension-appendices-list]]', file=current_extensions_appendix_fp)
        write('== List of Current Extensions', file=current_extensions_appendix_fp)
        write('endif::HAS_DEPRECATED_EXTENSIONS[]', file=current_extensions_appendix_fp)
        write('', file=current_extensions_appendix_fp)
        write('include::current_extension_appendices_toc.txt[]', file=current_extensions_appendix_fp)
        write('<<<', file=current_extensions_appendix_fp)
        write('include::current_extension_appendices.txt[]', file=current_extensions_appendix_fp)

        write('include::deprecated_extensions_guard_macro.txt[]', file=deprecated_extensions_appendix_fp)
        write('', file=deprecated_extensions_appendix_fp)
        write('ifdef::HAS_DEPRECATED_EXTENSIONS[]', file=deprecated_extensions_appendix_fp)
        write('[[deprecated-extension-appendices-list]]', file=deprecated_extensions_appendix_fp)
        write('== List of Deprecated Extensions', file=deprecated_extensions_appendix_fp)
        write('include::deprecated_extension_appendices_toc.txt[]', file=deprecated_extensions_appendix_fp)
        write('<<<', file=deprecated_extensions_appendix_fp)
        write('include::deprecated_extension_appendices.txt[]', file=deprecated_extensions_appendix_fp)
        write('endif::HAS_DEPRECATED_EXTENSIONS[]', file=deprecated_extensions_appendix_fp)

        # add include guard to allow multiple includes
        write('ifndef::DEPRECATED_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD[]', file=deprecated_extensions_guard_macro_fp)
        write(':DEPRECATED_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD:\n', file=deprecated_extensions_guard_macro_fp)

        for ext in self.extensions:
            include = 'include::../' + ext.name  + '.txt[]'
            link = '  * <<' + ext.name + '>>'

            if ext.deprecationType is None:
                write(self.conditionalExt(ext.name, include), file=current_extension_appendices_fp)
                write(self.conditionalExt(ext.name, link), file=current_extension_appendices_toc_fp)
            else:
                condition = ext.supercedingVkVersion if ext.supercedingVkVersion else ext.supercedingExtension # potentially None too

                write(self.conditionalExt(ext.name, include, 'ifndef', condition), file=current_extension_appendices_fp)
                write(self.conditionalExt(ext.name, link, 'ifndef', condition), file=current_extension_appendices_toc_fp)

                write(self.conditionalExt(ext.name, include, 'ifdef', condition), file=deprecated_extension_appendices_fp)
                write(self.conditionalExt(ext.name, link, 'ifdef', condition), file=deprecated_extension_appendices_toc_fp)

                write(self.conditionalExt(ext.name, ':HAS_DEPRECATED_EXTENSIONS:', 'ifdef', condition), file=deprecated_extensions_guard_macro_fp)

        current_extensions_appendix_fp.close()
        deprecated_extensions_appendix_fp.close()
        current_extension_appendices_fp.close()
        current_extension_appendices_toc_fp.close()
        deprecated_extension_appendices_fp.close()
        deprecated_extension_appendices_toc_fp.close()

        write('endif::DEPRECATED_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD[]', file=deprecated_extensions_guard_macro_fp)
        deprecated_extensions_guard_macro_fp.close()

        OutputGenerator.endFile(self)

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)

        if interface.tag != 'extension':
            self.logMsg('diag', 'beginFeature: ignoring non-extension feature', self.featureName)
            return

        # These attributes must exist
        name = self.featureName
        number = self.getAttrib(interface, 'number')
        type = self.getAttrib(interface, 'type')
        revision = self.getSpecVersion(interface, name)

        # These attributes are optional
        OPTIONAL = False
        requires = self.getAttrib(interface, 'requires', OPTIONAL)
        requiresCore = self.getAttrib(interface, 'requiresCore', OPTIONAL, '1.0')
        contact = self.getAttrib(interface, 'contact', OPTIONAL)
        promotedTo = self.getAttrib(interface, 'promotedto', OPTIONAL)
        deprecatedBy = self.getAttrib(interface, 'deprecatedby', OPTIONAL)
        obsoletedBy = self.getAttrib(interface, 'obsoletedby', OPTIONAL)

        filename = self.directory + '/' + name + '.txt'

        self.extensions.append( Extension(self, filename, name, number, type, requires, requiresCore, contact, promotedTo, deprecatedBy, obsoletedBy, revision) )

    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    # Query an attribute from an element, or return a default value
    #   elem - element to query
    #   attribute - attribute name
    #   required - whether attribute must exist
    #   default - default value if attribute not present
    def getAttrib(self, elem, attribute, required=True, default=None):
            attrib = elem.get(attribute, default)
            if required and (attrib is None):
                name = elem.get('name', 'UNKNOWN')
                self.logMsg('error', 'While processing \'' + self.featureName + ', <' + elem.tag + '> \'' + name + '\' does not contain required attribute \'' + attribute + '\'')
            return attrib

    def content(tag, ET):
        return tag.text + ''.join(ET.tostring(e) for e in tag)

    def numbersToWords(self, name):
        whitelist = ['WIN32', 'INT16']

        # temporarily replace whitelist items
        for i, w in enumerate(whitelist):
            name = re.sub(w, '{' + str(i) + '}', name)

        name = re.sub(r'(?<=[A-Z])(\d+)(?![A-Z])', '_\g<1>', name)

        # undo whitelist substitution
        for i, w in enumerate(whitelist):
            name = re.sub('\\{' + str(i) + '}', w, name)

        return name

    #
    # Determine the extension revision from the EXTENSION_NAME_SPEC_VERSION
    # enumerant.
    #
    #   elem - <extension> element to query
    #   extname - extension name from the <extension> 'name' attribute
    #   default - default value if SPEC_VERSION token not present
    def getSpecVersion(self, elem, extname, default=None):
        # The literal enumerant name to match
        versioningEnumName = self.numbersToWords(extname.upper()) + '_SPEC_VERSION'

        for enum in elem.findall('./require/enum'):
            enumName = self.getAttrib(enum, 'name')
            if enumName == versioningEnumName:
                return self.getAttrib(enum, 'value')

        #if not found:
        for enum in elem.findall('./require/enum'):
            enumName = self.getAttrib(enum, 'name')
            if enumName.find('SPEC_VERSION') != -1:
                self.logMsg('diag', 'Missing ' + versioningEnumName + '! Potential misnamed candidate ' + enumName + '.')
                return self.getAttrib(enum, 'value')

        self.logMsg('error', 'Missing ' + versioningEnumName + '!')
