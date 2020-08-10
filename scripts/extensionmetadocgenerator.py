#!/usr/bin/python3 -i
#
# Copyright (c) 2013-2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import re
import sys
from functools import total_ordering
from generator import GeneratorOptions, OutputGenerator, regSortFeatures, write

class ExtensionMetaDocGeneratorOptions(GeneratorOptions):
    """ExtensionMetaDocGeneratorOptions - subclass of GeneratorOptions.

    Represents options during extension metainformation generation for Asciidoc"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


EXT_NAME_DECOMPOSE_RE = re.compile(r'[A-Z]+_(?P<tag>[A-Z]+)_(?P<name>[\w_]+)')


@total_ordering
class Extension:
    def __init__(self,
                 generator, # needed for logging and API conventions
                 filename,
                 name,
                 number,
                 ext_type,
                 requires,
                 requiresCore,
                 contact,
                 promotedTo,
                 deprecatedBy,
                 obsoletedBy,
                 provisional,
                 revision,
                 specialuse ):
        self.generator = generator
        self.conventions = generator.genOpts.conventions
        self.filename = filename
        self.name = name
        self.number = number
        self.ext_type = ext_type
        self.requires = requires
        self.requiresCore = requiresCore
        self.contact = contact
        self.promotedTo = promotedTo
        self.deprecatedBy = deprecatedBy
        self.obsoletedBy = obsoletedBy
        self.provisional = provisional
        self.revision = revision
        self.specialuse = specialuse

        self.deprecationType = None
        self.supercedingAPIVersion = None
        self.supercedingExtension = None

        if self.promotedTo is not None and self.deprecatedBy is not None and self.obsoletedBy is not None:
            self.generator.logMsg('warn', 'All \'promotedto\', \'deprecatedby\' and \'obsoletedby\' attributes used on extension ' + self.name + '! Ignoring \'promotedto\' and \'deprecatedby\'.')
        elif self.promotedTo is not None and self.deprecatedBy is not None:
            self.generator.logMsg('warn', 'Both \'promotedto\' and \'deprecatedby\' attributes used on extension ' + self.name + '! Ignoring \'deprecatedby\'.')
        elif self.promotedTo is not None and self.obsoletedBy is not None:
            self.generator.logMsg('warn', 'Both \'promotedto\' and \'obsoletedby\' attributes used on extension ' + self.name + '! Ignoring \'promotedto\'.')
        elif self.deprecatedBy is not None and self.obsoletedBy is not None:
            self.generator.logMsg('warn', 'Both \'deprecatedby\' and \'obsoletedby\' attributes used on extension ' + self.name + '! Ignoring \'deprecatedby\'.')

        supercededBy = None
        if self.promotedTo is not None:
            self.deprecationType = 'promotion'
            supercededBy = promotedTo
        elif self.deprecatedBy is not None:
            self.deprecationType = 'deprecation'
            supercededBy = deprecatedBy
        elif self.obsoletedBy is not None:
            self.deprecationType = 'obsoletion'
            supercededBy = obsoletedBy

        if supercededBy is not None:
            if supercededBy == '' and not self.deprecationType == 'promotion':
                pass # supercedingAPIVersion, supercedingExtension is None
            elif supercededBy.startswith(self.conventions.api_version_prefix):
                self.supercedingAPIVersion = supercededBy
            elif supercededBy.startswith(self.conventions.api_prefix):
                self.supercedingExtension = supercededBy
            else:
                self.generator.logMsg('error', 'Unrecognized ' + self.deprecationType + ' attribute value \'' + supercededBy + '\'!')

        match = EXT_NAME_DECOMPOSE_RE.match(self.name)
        self.vendor = match.group('tag')
        self.bare_name = match.group('name')

    def __str__(self):
        return self.name
    def __eq__(self, other):
        return self.name == other.name
    def __ne__(self, other):
        return self.name != other.name

    def __lt__(self, other):
        self_is_KHR = self.name.startswith(self.conventions.KHR_prefix)
        self_is_EXT = self.name.startswith(self.conventions.EXT_prefix)
        other_is_KHR = other.name.startswith(self.conventions.KHR_prefix)
        other_is_EXT = other.name.startswith(self.conventions.EXT_prefix)

        swap = False
        if self_is_KHR and not other_is_KHR:
            return not swap
        if other_is_KHR and not self_is_KHR:
            return swap
        if self_is_EXT and not other_is_EXT:
            return not swap
        if other_is_EXT and not self_is_EXT:
            return swap

        return self.name < other.name

    def typeToStr(self):
        if self.ext_type == 'instance':
            return 'Instance extension'
        if self.ext_type == 'device':
            return 'Device extension'

        if self.ext_type is not None:
            self.generator.logMsg('warn', 'The type attribute of ' + self.name + ' extension is neither \'instance\' nor \'device\'. That is invalid (at the time this script was written).')
        else: # should be unreachable
            self.generator.logMsg('error', 'Logic error in typeToStr(): Missing type attribute!')
        return None

    def specLink(self, xrefName, xrefText, isRefpage = False):
        """Generate a string containing a link to a specification anchor in
           asciidoctor markup form.

        - xrefName - anchor name in the spec
        - xrefText - text to show for the link, or None
        - isRefpage = True if generating a refpage include, False if
          generating a specification extension appendix include"""

        if isRefpage:
            # Always link into API spec
            specURL = self.conventions.specURL('api')
            return 'link:{}#{}[{}^]'.format(specURL, xrefName, xrefText)
        else:
            return '<<' + xrefName + ', ' + xrefText + '>>'

    def conditionalLinkCoreAPI(self, apiVersion, linkSuffix, isRefpage):
        versionMatch = re.match(self.conventions.api_version_prefix + r'(\d+)_(\d+)', apiVersion)
        major = versionMatch.group(1)
        minor = versionMatch.group(2)

        dottedVersion = major + '.' + minor

        xrefName = 'versions-' + dottedVersion + linkSuffix
        xrefText = self.conventions.api_name() + ' ' + dottedVersion

        doc  = 'ifdef::' + apiVersion + '[]\n'
        doc += '    ' + self.specLink(xrefName, xrefText, isRefpage) + '\n'
        doc += 'endif::' + apiVersion + '[]\n'
        doc += 'ifndef::' + apiVersion + '[]\n'
        doc += '    ' + self.conventions.api_name() + ' ' + dottedVersion + '\n'
        doc += 'endif::' + apiVersion + '[]\n'

        return doc

    def conditionalLinkExt(self, extName, indent = '    '):
        doc  = 'ifdef::' + extName + '[]\n'
        doc +=  indent + self.conventions.formatExtension(extName) + '\n'
        doc += 'endif::' + extName + '[]\n'
        doc += 'ifndef::' + extName + '[]\n'
        doc += indent + '`' + extName + '`\n'
        doc += 'endif::' + extName + '[]\n'

        return doc

    def resolveDeprecationChain(self, extensionsList, succeededBy, isRefpage, file):
        ext = next(x for x in extensionsList if x.name == succeededBy)

        if ext.deprecationType:
            if ext.deprecationType == 'promotion':
                if ext.supercedingAPIVersion:
                    write('  ** Which in turn was _promoted_ to\n' + ext.conditionalLinkCoreAPI(ext.supercedingAPIVersion, '-promotions', isRefpage), file=file)
                else: # ext.supercedingExtension
                    write('  ** Which in turn was _promoted_ to extension\n' + ext.conditionalLinkExt(ext.supercedingExtension), file=file)
                    ext.resolveDeprecationChain(extensionsList, ext.supercedingExtension, file)
            elif ext.deprecationType == 'deprecation':
                if ext.supercedingAPIVersion:
                    write('  ** Which in turn was _deprecated_ by\n' + ext.conditionalLinkCoreAPI(ext.supercedingAPIVersion, '-new-feature', isRefpage), file=file)
                elif ext.supercedingExtension:
                    write('  ** Which in turn was _deprecated_ by\n' + ext.conditionalLinkExt(ext.supercedingExtension) + '    extension', file=file)
                    ext.resolveDeprecationChain(extensionsList, ext.supercedingExtension, file)
                else:
                    write('  ** Which in turn was _deprecated_ without replacement', file=file)
            elif ext.deprecationType == 'obsoletion':
                if ext.supercedingAPIVersion:
                    write('  ** Which in turn was _obsoleted_ by\n' + ext.conditionalLinkCoreAPI(ext.supercedingAPIVersion, '-new-feature', isRefpage), file=file)
                elif ext.supercedingExtension:
                    write('  ** Which in turn was _obsoleted_ by\n' + ext.conditionalLinkExt(ext.supercedingExtension) + '    extension', file=file)
                    ext.resolveDeprecationChain(extensionsList, ext.supercedingExtension, file)
                else:
                    write('  ** Which in turn was _obsoleted_ without replacement', file=file)
            else: # should be unreachable
                self.generator.logMsg('error', 'Logic error in resolveDeprecationChain(): deprecationType is neither \'promotion\', \'deprecation\' nor \'obsoletion\'!')


    def writeTag(self, tag, value, isRefpage, fp):
        """Write a tag and (if non-None) a tag value to a file.

        - tag - string tag name
        - value - tag value, or None
        - isRefpage - controls style in which the tag is marked up
        - fp - open file pointer to write to"""

        if isRefpage:
            # Use subsection headers for the tag name
            tagPrefix = '== '
            tagSuffix = ''
        else:
            # Use an bolded item list for the tag name
            tagPrefix = '*'
            tagSuffix = '*::'

        write(tagPrefix + tag + tagSuffix, file=fp)
        if value is not None:
            write(value, file=fp)

        if isRefpage:
            write('', file=fp)

    def makeMetafile(self, extensionsList, isRefpage = False):
        """Generate a file containing extension metainformation in
           asciidoctor markup form.

        - extensionsList - list of extensions spec is being generated against
        - isRefpage - True if generating a refpage include, False if
          generating a specification extension appendix include"""

        if isRefpage:
            filename = self.filename.replace('meta/', 'meta/refpage.')
        else:
            filename = self.filename

        fp = self.generator.newFile(filename)

        if not isRefpage:
            write('[[' + self.name + ']]', file=fp)
            write('=== ' + self.name, file=fp)
            write('', file=fp)

            self.writeTag('Name String', '`' + self.name + '`', isRefpage, fp)
            self.writeTag('Extension Type', self.typeToStr(), isRefpage, fp)

        self.writeTag('Registered Extension Number', self.number, isRefpage, fp)
        self.writeTag('Revision', self.revision, isRefpage, fp)

        # Only API extension dependencies are coded in XML, others are explicit
        self.writeTag('Extension and Version Dependencies', None, isRefpage, fp)

        write('  * Requires ' + self.conventions.api_name() + ' ' + self.requiresCore, file=fp)
        if self.requires:
            for dep in self.requires.split(','):
                write('  * Requires', self.conventions.formatExtension(dep),
                      file=fp)
        if self.provisional == 'true':
            write('  * *This is a _provisional_ extension and must: be used with caution.', file=fp)
            write('    See the ' +
                  self.specLink(xrefName = 'boilerplate-provisional-header',
                                xrefText = 'description',
                                isRefpage = isRefpage) +
                  ' of provisional header files for enablement and stability details.*', file=fp)
        write('', file=fp)

        if self.deprecationType:
            self.writeTag('Deprecation state', None, isRefpage, fp)

            if self.deprecationType == 'promotion':
                if self.supercedingAPIVersion:
                    write('  * _Promoted_ to\n' + self.conditionalLinkCoreAPI(self.supercedingAPIVersion, '-promotions', isRefpage), file=fp)
                else: # ext.supercedingExtension
                    write('  * _Promoted_ to\n' + self.conditionalLinkExt(self.supercedingExtension) + '    extension', file=fp)
                    self.resolveDeprecationChain(extensionsList, self.supercedingExtension, isRefpage, fp)
            elif self.deprecationType == 'deprecation':
                if self.supercedingAPIVersion:
                    write('  * _Deprecated_ by\n' + self.conditionalLinkCoreAPI(self.supercedingAPIVersion, '-new-features', isRefpage), file=fp)
                elif self.supercedingExtension:
                    write('  * _Deprecated_ by\n' + self.conditionalLinkExt(self.supercedingExtension) + '    extension' , file=fp)
                    self.resolveDeprecationChain(extensionsList, self.supercedingExtension, isRefpage, fp)
                else:
                    write('  * _Deprecated_ without replacement' , file=fp)
            elif self.deprecationType == 'obsoletion':
                if self.supercedingAPIVersion:
                    write('  * _Obsoleted_ by\n' + self.conditionalLinkCoreAPI(self.supercedingAPIVersion, '-new-features', isRefpage), file=fp)
                elif self.supercedingExtension:
                    write('  * _Obsoleted_ by\n' + self.conditionalLinkExt(self.supercedingExtension) + '    extension' , file=fp)
                    self.resolveDeprecationChain(extensionsList, self.supercedingExtension, isRefpage, fp)
                else:
                    # TODO: Does not make sense to retroactively ban use of extensions from 1.0.
                    #       Needs some tweaks to the semantics and this message, when such extension(s) occur.
                    write('  * _Obsoleted_ without replacement' , file=fp)
            else: # should be unreachable
                self.generator.logMsg('error', 'Logic error in makeMetafile(): deprecationType is neither \'promotion\', \'deprecation\' nor \'obsoletion\'!')

        if self.specialuse is not None:
            specialuses = self.specialuse.split(',')
            if len(specialuses) > 1:
                header = 'Special Uses'
            else:
                header = 'Special Use'
            self.writeTag(header, None, isRefpage, fp)

            for use in specialuses:
                # Each specialuse attribute value expands an asciidoctor
                # attribute of the same name, instead of using the shorter,
                # and harder to understand attribute
                write('* {}'.format(
                      self.specLink(
                           xrefName = self.conventions.special_use_section_anchor,
                           xrefText = '{' + use + '}',
                           isRefpage = isRefpage)), file=fp)

        if self.conventions.write_contacts and not isRefpage:
            write('*Contact*::', file=fp)
            contacts = self.contact.split(',')
            for contact in contacts:
                contactWords = contact.strip().split()
                name = ' '.join(contactWords[:-1])
                handle = contactWords[-1]
                if handle.startswith('gitlab:'):
                    prettyHandle = 'icon:gitlab[alt=GitLab, role="red"]' + handle.replace('gitlab:@', '')
                elif handle.startswith('@'):
                    trackerLink = 'link:++https://github.com/KhronosGroup/Vulkan-Docs/issues/new?title=' + self.name + ':%20&body=' + handle + '%20++'
                    prettyHandle = trackerLink + '[icon:github[alt=GitHub, role="black"]' + handle[1:] + ']'
                else:
                    prettyHandle = handle

                write('  * ' + name + ' ' + prettyHandle, file=fp)

        fp.close()

class ExtensionMetaDocOutputGenerator(OutputGenerator):
    """ExtensionMetaDocOutputGenerator - subclass of OutputGenerator.

    Generates AsciiDoc includes with metainformation for the API extension
    appendices. The fields used from <extension> tags in the API XML are:

    - name          extension name string
    - number        extension number (optional)
    - contact       name and github login or email address (optional)
    - type          'instance' | 'device' (optional)
    - requires      list of comma-separated required API extensions (optional)
    - requiresCore  required core version of API (optional)
    - promotedTo    extension or API version it was promoted to
    - deprecatedBy  extension or API version which deprecated this extension,
                    or empty string if deprecated without replacement
    - obsoletedBy   extension or API version which obsoleted this extension,
                    or empty string if obsoleted without replacement
    - provisional   'true' if this extension is released provisionally"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extensions = []
        # List of strings containing all vendor tags
        self.vendor_tags = []
        self.file_suffix = ''

    def newFile(self, filename):
        self.logMsg('diag', '# Generating include file:', filename)
        fp = open(filename, 'w', encoding='utf-8')
        write(self.genOpts.conventions.warning_comment, file=fp)
        return fp

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        self.directory = self.genOpts.directory
        self.file_suffix = self.genOpts.conventions.file_suffix

        # Iterate over all 'tag' Elements and add the names of all the valid vendor
        # tags to the list
        root = self.registry.tree.getroot()
        for tag in root.findall('tags/tag'):
            self.vendor_tags.append(tag.get('name'))

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
                raise RuntimeError('Should be unreachable: ifdef is neither \'ifdef \' nor \'ifndef\'!')
        else:
            doc += innerdoc

        return doc

    def makeExtensionInclude(self, ext):
        return self.conventions.extension_include_string(ext)

    def endFile(self):
        self.extensions.sort()

        # Generate metadoc extension files, in refpage and non-refpage form
        for ext in self.extensions:
            ext.makeMetafile(self.extensions, isRefpage = False)
            if self.conventions.write_refpage_include:
                ext.makeMetafile(self.extensions, isRefpage = True)

        # Generate list of promoted extensions
        promotedExtensions = {}
        for ext in self.extensions:
            if ext.deprecationType == 'promotion' and ext.supercedingAPIVersion:
                promotedExtensions.setdefault(ext.supercedingAPIVersion, []).append(ext)

        for coreVersion, extensions in promotedExtensions.items():
            promoted_extensions_fp = self.newFile(self.directory + '/promoted_extensions_' + coreVersion + self.file_suffix)

            for ext in extensions:
                indent = ''
                write('  * {blank}\n+\n' + ext.conditionalLinkExt(ext.name, indent), file=promoted_extensions_fp)

            promoted_extensions_fp.close()

        # Re-sort to match earlier behavior
        # TODO: Remove this extra sort when re-arranging section order OK.

        def makeSortKey(ext):
            name = ext.name.lower()
            prefixes = self.conventions.extension_index_prefixes
            for i, prefix in enumerate(prefixes):
                if ext.name.startswith(prefix):
                    return (i, name)
            return (len(prefixes), name)

        self.extensions.sort(key=makeSortKey)

        # Generate include directives for the extensions appendix, grouping
        # extensions by status (current, deprecated, provisional, etc.)
        with self.newFile(self.directory + '/current_extensions_appendix' + self.file_suffix) as current_extensions_appendix_fp, \
                self.newFile(self.directory + '/deprecated_extensions_appendix' + self.file_suffix) as deprecated_extensions_appendix_fp, \
                self.newFile(self.directory + '/current_extension_appendices' + self.file_suffix) as current_extension_appendices_fp, \
                self.newFile(self.directory + '/current_extension_appendices_toc' + self.file_suffix) as current_extension_appendices_toc_fp, \
                self.newFile(self.directory + '/deprecated_extension_appendices' + self.file_suffix) as deprecated_extension_appendices_fp, \
                self.newFile(self.directory + '/deprecated_extension_appendices_toc' + self.file_suffix) as deprecated_extension_appendices_toc_fp, \
                self.newFile(self.directory + '/deprecated_extensions_guard_macro' + self.file_suffix) as deprecated_extensions_guard_macro_fp, \
                self.newFile(self.directory + '/provisional_extensions_appendix' + self.file_suffix) as provisional_extensions_appendix_fp, \
                self.newFile(self.directory + '/provisional_extension_appendices' + self.file_suffix) as provisional_extension_appendices_fp, \
                self.newFile(self.directory + '/provisional_extension_appendices_toc' + self.file_suffix) as provisional_extension_appendices_toc_fp, \
                self.newFile(self.directory + '/provisional_extensions_guard_macro' + self.file_suffix) as provisional_extensions_guard_macro_fp:

            write('include::deprecated_extensions_guard_macro' + self.file_suffix + '[]', file=current_extensions_appendix_fp)
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
            write('include::current_extension_appendices_toc' + self.file_suffix + '[]', file=current_extensions_appendix_fp)
            write('<<<', file=current_extensions_appendix_fp)
            write('include::current_extension_appendices' + self.file_suffix + '[]', file=current_extensions_appendix_fp)

            write('include::deprecated_extensions_guard_macro' + self.file_suffix + '[]', file=deprecated_extensions_appendix_fp)
            write('', file=deprecated_extensions_appendix_fp)
            write('ifdef::HAS_DEPRECATED_EXTENSIONS[]', file=deprecated_extensions_appendix_fp)
            write('[[deprecated-extension-appendices-list]]', file=deprecated_extensions_appendix_fp)
            write('== List of Deprecated Extensions', file=deprecated_extensions_appendix_fp)
            write('include::deprecated_extension_appendices_toc' + self.file_suffix + '[]', file=deprecated_extensions_appendix_fp)
            write('<<<', file=deprecated_extensions_appendix_fp)
            write('include::deprecated_extension_appendices' + self.file_suffix + '[]', file=deprecated_extensions_appendix_fp)
            write('endif::HAS_DEPRECATED_EXTENSIONS[]', file=deprecated_extensions_appendix_fp)

            # add include guard to allow multiple includes
            write('ifndef::DEPRECATED_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD[]', file=deprecated_extensions_guard_macro_fp)
            write(':DEPRECATED_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD:\n', file=deprecated_extensions_guard_macro_fp)
            write('ifndef::PROVISIONAL_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD[]', file=provisional_extensions_guard_macro_fp)
            write(':PROVISIONAL_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD:\n', file=provisional_extensions_guard_macro_fp)

            write('include::provisional_extensions_guard_macro' + self.file_suffix + '[]', file=provisional_extensions_appendix_fp)
            write('', file=provisional_extensions_appendix_fp)
            write('ifdef::HAS_PROVISIONAL_EXTENSIONS[]', file=provisional_extensions_appendix_fp)
            write('[[provisional-extension-appendices-list]]', file=provisional_extensions_appendix_fp)
            write('== List of Provisional Extensions', file=provisional_extensions_appendix_fp)
            write('include::provisional_extension_appendices_toc' + self.file_suffix + '[]', file=provisional_extensions_appendix_fp)
            write('<<<', file=provisional_extensions_appendix_fp)
            write('include::provisional_extension_appendices' + self.file_suffix + '[]', file=provisional_extensions_appendix_fp)
            write('endif::HAS_PROVISIONAL_EXTENSIONS[]', file=provisional_extensions_appendix_fp)

            for ext in self.extensions:
                include = self.makeExtensionInclude(ext)
                link = '  * ' + self.conventions.formatExtension(ext.name)
                if ext.provisional == 'true':
                    write(self.conditionalExt(ext.name, include), file=provisional_extension_appendices_fp)
                    write(self.conditionalExt(ext.name, link), file=provisional_extension_appendices_toc_fp)
                    write(self.conditionalExt(ext.name, ':HAS_PROVISIONAL_EXTENSIONS:'), file=provisional_extensions_guard_macro_fp)
                elif ext.deprecationType is None:
                    write(self.conditionalExt(ext.name, include), file=current_extension_appendices_fp)
                    write(self.conditionalExt(ext.name, link), file=current_extension_appendices_toc_fp)
                else:
                    condition = ext.supercedingAPIVersion if ext.supercedingAPIVersion else ext.supercedingExtension  # potentially None too

                    write(self.conditionalExt(ext.name, include, 'ifndef', condition), file=current_extension_appendices_fp)
                    write(self.conditionalExt(ext.name, link, 'ifndef', condition), file=current_extension_appendices_toc_fp)

                    write(self.conditionalExt(ext.name, include, 'ifdef', condition), file=deprecated_extension_appendices_fp)
                    write(self.conditionalExt(ext.name, link, 'ifdef', condition), file=deprecated_extension_appendices_toc_fp)

                    write(self.conditionalExt(ext.name, ':HAS_DEPRECATED_EXTENSIONS:', 'ifdef', condition), file=deprecated_extensions_guard_macro_fp)

            write('endif::DEPRECATED_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD[]', file=deprecated_extensions_guard_macro_fp)

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
        ext_type = self.getAttrib(interface, 'type')
        revision = self.getSpecVersion(interface, name)

        # These attributes are optional
        OPTIONAL = False
        requires = self.getAttrib(interface, 'requires', OPTIONAL)
        requiresCore = self.getAttrib(interface, 'requiresCore', OPTIONAL, '1.0') # TODO update this line with update_version.py
        contact = self.getAttrib(interface, 'contact', OPTIONAL)
        promotedTo = self.getAttrib(interface, 'promotedto', OPTIONAL)
        deprecatedBy = self.getAttrib(interface, 'deprecatedby', OPTIONAL)
        obsoletedBy = self.getAttrib(interface, 'obsoletedby', OPTIONAL)
        provisional = self.getAttrib(interface, 'provisional', OPTIONAL, 'false')
        specialuse = self.getAttrib(interface, 'specialuse', OPTIONAL)

        filename = self.directory + '/' + name + self.file_suffix

        extdata = Extension(
            generator = self,
            filename = filename,
            name = name,
            number = number,
            ext_type = ext_type,
            requires = requires,
            requiresCore = requiresCore,
            contact = contact,
            promotedTo = promotedTo,
            deprecatedBy = deprecatedBy,
            obsoletedBy = obsoletedBy,
            provisional = provisional,
            revision = revision,
            specialuse = specialuse)
        self.extensions.append(extdata)


    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    def getAttrib(self, elem, attribute, required=True, default=None):
        """Query an attribute from an element, or return a default value

        - elem - element to query
        - attribute - attribute name
        - required - whether attribute must exist
        - default - default value if attribute not present"""
        attrib = elem.get(attribute, default)
        if required and (attrib is None):
            name = elem.get('name', 'UNKNOWN')
            self.logMsg('error', 'While processing \'' + self.featureName + ', <' + elem.tag + '> \'' + name + '\' does not contain required attribute \'' + attribute + '\'')
        return attrib

    def numbersToWords(self, name):
        allowlist = ['WIN32', 'INT16', 'D3D1']

        # temporarily replace allowlist items
        for i, w in enumerate(allowlist):
            name = re.sub(w, '{' + str(i) + '}', name)

        name = re.sub(r'(?<=[A-Z])(\d+)(?![A-Z])', r'_\g<1>', name)

        # undo allowlist substitution
        for i, w in enumerate(allowlist):
            name = re.sub('\\{' + str(i) + '}', w, name)

        return name

    def getSpecVersion(self, elem, extname, default=None):
        """Determine the extension revision from the EXTENSION_NAME_SPEC_VERSION
        enumerant.

        - elem - <extension> element to query
        - extname - extension name from the <extension> 'name' attribute
        - default - default value if SPEC_VERSION token not present"""
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
        return default
