#!/usr/bin/python3 -i
#
# Copyright 2013-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import os
import re
import sys
from functools import total_ordering
from generator import GeneratorOptions, OutputGenerator, regSortFeatures, write
from parse_dependency import dependencyMarkup, dependencyNames

class ExtensionMetaDocGeneratorOptions(GeneratorOptions):
    """ExtensionMetaDocGeneratorOptions - subclass of GeneratorOptions.

    Represents options during extension metainformation generation for Asciidoc"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

@total_ordering
class Extension:
    def __init__(self,
                 generator, # needed for logging and API conventions
                 filename,
                 interface,
                 name,
                 number,
                 ext_type,
                 depends,
                 contact,
                 promotedTo,
                 deprecatedBy,
                 obsoletedBy,
                 provisional,
                 revision,
                 specialuse,
                 ratified
                ):
        """Object encapsulating information from an XML <extension> tag.
           Most of the parameters / members are XML tag values.
           'interface' is the actual XML <extension> element."""

        self.generator = generator
        self.conventions = generator.genOpts.conventions
        self.filename = filename
        self.interface = interface
        self.name = name
        self.number = number
        self.ext_type = ext_type
        self.depends = depends
        self.contact = contact
        self.promotedTo = promotedTo
        self.deprecatedBy = deprecatedBy
        self.obsoletedBy = obsoletedBy
        self.provisional = provisional
        self.revision = revision
        self.specialuse = specialuse
        self.ratified = ratified

        self.deprecationType = None
        self.supercedingAPIVersion = None
        self.supercedingExtension = None
        # This is a set containing names of extensions (if any) promoted
        # *to* this extension.
        # It is filled in after all the Extension objects are created,
        # since it requires a reverse mapping step.
        self.promotedFrom = set()

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
            elif supercededBy.startswith(self.conventions.extension_name_prefix):
                self.supercedingExtension = supercededBy
            else:
                self.generator.logMsg('error', 'Unrecognized ' + self.deprecationType + ' attribute value \'' + supercededBy + '\'!')

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

    def resolveDeprecationChain(self, extensions, succeededBy, isRefpage, file):
        if succeededBy not in extensions:
            write(f'  ** *NOTE* The extension `{succeededBy}` is not supported for the API specification being generated', file=file)
            self.generator.logMsg('warn', f'resolveDeprecationChain: {self.name} defines a superseding interface {succeededBy} which is not in the supported extensions list')
            return

        ext = extensions[succeededBy]

        if ext.deprecationType:
            if ext.deprecationType == 'promotion':
                if ext.supercedingAPIVersion:
                    write('  ** Which in turn was _promoted_ to\n' + ext.conditionalLinkCoreAPI(ext.supercedingAPIVersion, '-promotions', isRefpage), file=file)
                else: # ext.supercedingExtension
                    write('  ** Which in turn was _promoted_ to extension\n' + ext.conditionalLinkExt(ext.supercedingExtension), file=file)
                    ext.resolveDeprecationChain(extensions, ext.supercedingExtension, file)
            elif ext.deprecationType == 'deprecation':
                if ext.supercedingAPIVersion:
                    write('  ** Which in turn was _deprecated_ by\n' + ext.conditionalLinkCoreAPI(ext.supercedingAPIVersion, '-new-feature', isRefpage), file=file)
                elif ext.supercedingExtension:
                    write('  ** Which in turn was _deprecated_ by\n' + ext.conditionalLinkExt(ext.supercedingExtension) + '    extension', file=file)
                    ext.resolveDeprecationChain(extensions, ext.supercedingExtension, file)
                else:
                    write('  ** Which in turn was _deprecated_ without replacement', file=file)
            elif ext.deprecationType == 'obsoletion':
                if ext.supercedingAPIVersion:
                    write('  ** Which in turn was _obsoleted_ by\n' + ext.conditionalLinkCoreAPI(ext.supercedingAPIVersion, '-new-feature', isRefpage), file=file)
                elif ext.supercedingExtension:
                    write('  ** Which in turn was _obsoleted_ by\n' + ext.conditionalLinkExt(ext.supercedingExtension) + '    extension', file=file)
                    ext.resolveDeprecationChain(extensions, ext.supercedingExtension, file)
                else:
                    write('  ** Which in turn was _obsoleted_ without replacement', file=file)
            else: # should be unreachable
                self.generator.logMsg('error', 'Logic error in resolveDeprecationChain(): deprecationType is neither \'promotion\', \'deprecation\' nor \'obsoletion\'!')


    def writeTag(self, tag, value, isRefpage, fp):
        """Write a tag and (if non-None) a tag value to a file.

           If the value is None, just write the tag.

           If the tag is None, just write the value (used for adding a value
           to a just-written tag).

        - tag - string tag name
        - value - tag value, or None
        - isRefpage - controls style in which the tag is marked up
        - fp - open file pointer to write to"""

        if isRefpage:
            # Use subsection headers for the tag name
            # Because we do not know what preceded this, add whitespace
            tagPrefix = '\n== '
            tagSuffix = ''
        else:
            # Use a bolded item list for the tag name
            tagPrefix = '*'
            tagSuffix = '*::'

        if tag is not None:
            write(tagPrefix + tag + tagSuffix, file=fp)
        if value is not None:
            write(value, file=fp)

        if isRefpage:
            write('', file=fp)

    def makeMetafile(self, extensions, SPV_deps, isRefpage = False):
        """Generate a file containing extension metainformation in
           asciidoctor markup form.

        - extensions - dictionary of Extension objects for extensions spec
          is being generated against
        - SPV_deps - dictionary of SPIR-V extension names required for each
          extension and version name
        - isRefpage - True if generating a refpage include, False if
          generating a specification extension appendix include"""

        if isRefpage:
            filename = self.filename.replace('meta/', 'meta/refpage.')
        else:
            filename = self.filename

        fp = self.generator.newFile(filename)

        if not isRefpage:
            write('[[' + self.name + ']]', file=fp)
            write('== ' + self.name, file=fp)
            write('', file=fp)

            self.writeTag('Name String', '`' + self.name + '`', isRefpage, fp)
            if self.conventions.write_extension_type:
                self.writeTag('Extension Type', self.typeToStr(), isRefpage, fp)

        if self.conventions.write_extension_number:
            self.writeTag('Registered Extension Number', self.number, isRefpage, fp)
        if self.conventions.write_extension_revision:
            self.writeTag('Revision', self.revision, isRefpage, fp)

        if self.conventions.xml_api_name in self.ratified.split(','):
            ratstatus = 'Ratified'
        else:
            ratstatus = 'Not ratified'
        self.writeTag('Ratification Status', ratstatus, isRefpage, fp)

        # Only API extension dependencies are coded in XML, others are explicit
        self.writeTag('Extension and Version Dependencies', None, isRefpage, fp)

        # Transform the boolean 'depends' expression into equivalent
        # human-readable asciidoc markup.
        if self.depends is not None:
            if isRefpage:
                separator = ''
            else:
                separator = '+'
            write(separator + '\n--\n' +
                  dependencyMarkup(self.depends) +
                  '--', file=fp)
        else:
            # Do not specify the base API redundantly, but put something
            # here to avoid formatting trouble.
            self.writeTag(None, 'None', isRefpage, fp)

        if self.provisional == 'true' and self.conventions.provisional_extension_warning:
            write('  * *This is a _provisional_ extension and must: be used with caution.', file=fp)
            write('    See the ' +
                  self.specLink(xrefName = 'boilerplate-provisional-header',
                                xrefText = 'description',
                                isRefpage = isRefpage) +
                  ' of provisional header files for enablement and stability details.*', file=fp)
        write('', file=fp)

        # Determine version and extension interactions from 'depends'
        # attributes of <require> tags.
        interacts = set()
        for elem in self.interface.findall('require[@depends]'):
            names = dependencyNames(elem.get('depends'))
            interacts |= names

        if len(interacts) > 0:
            self.writeTag('API Interactions', None, isRefpage, fp)

            def versionKey(name):
                """Sort _VERSION_ names before extension names"""
                return '_VERSION_' not in name

            names = sorted(sorted(interacts), key=versionKey)
            for name in names:
                write(f'* Interacts with {name}', file=fp)

            write('', file=fp)

        if self.name in SPV_deps:
            self.writeTag('SPIR-V Dependencies', None, isRefpage, fp)

            for spvname in sorted(SPV_deps[self.name]):
                write(f'  * {self.conventions.formatSPIRVlink(spvname)}', file=fp)

            write('', file=fp)

        if self.deprecationType:
            self.writeTag('Deprecation State', None, isRefpage, fp)

            if self.deprecationType == 'promotion':
                if self.supercedingAPIVersion:
                    write('  * _Promoted_ to\n' + self.conditionalLinkCoreAPI(self.supercedingAPIVersion, '-promotions', isRefpage), file=fp)
                else: # ext.supercedingExtension
                    write('  * _Promoted_ to\n' + self.conditionalLinkExt(self.supercedingExtension) + '    extension', file=fp)
                    self.resolveDeprecationChain(extensions, self.supercedingExtension, isRefpage, fp)
            elif self.deprecationType == 'deprecation':
                if self.supercedingAPIVersion:
                    write('  * _Deprecated_ by\n' + self.conditionalLinkCoreAPI(self.supercedingAPIVersion, '-new-features', isRefpage), file=fp)
                elif self.supercedingExtension:
                    write('  * _Deprecated_ by\n' + self.conditionalLinkExt(self.supercedingExtension) + '    extension' , file=fp)
                    self.resolveDeprecationChain(extensions, self.supercedingExtension, isRefpage, fp)
                else:
                    write('  * _Deprecated_ without replacement' , file=fp)
            elif self.deprecationType == 'obsoletion':
                if self.supercedingAPIVersion:
                    write('  * _Obsoleted_ by\n' + self.conditionalLinkCoreAPI(self.supercedingAPIVersion, '-new-features', isRefpage), file=fp)
                elif self.supercedingExtension:
                    write('  * _Obsoleted_ by\n' + self.conditionalLinkExt(self.supercedingExtension) + '    extension' , file=fp)
                    self.resolveDeprecationChain(extensions, self.supercedingExtension, isRefpage, fp)
                else:
                    # TODO: Does not make sense to retroactively ban use of extensions from 1.0.
                    #       Needs some tweaks to the semantics and this message, when such extension(s) occur.
                    write('  * _Obsoleted_ without replacement' , file=fp)
            else: # should be unreachable
                self.generator.logMsg('error', 'Logic error in makeMetafile(): deprecationType is neither \'promotion\', \'deprecation\' nor \'obsoletion\'!')
            write('', file=fp)

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
            write('', file=fp)

        if self.conventions.write_contacts:
            self.writeTag('Contact', None, isRefpage, fp)

            contacts = self.contact.split(',')
            for contact in contacts:
                contactWords = contact.strip().split()
                name = ' '.join(contactWords[:-1])
                handle = contactWords[-1]
                if handle.startswith('gitlab:'):
                    prettyHandle = 'icon:gitlab[alt=GitLab, role="red"]' + handle.replace('gitlab:@', '')
                elif handle.startswith('@'):
                    issuePlaceholderText = f'[{self.name}] {handle}'
                    issuePlaceholderText += f'%0A*Here describe the issue or question you have about the {self.name} extension*'
                    trackerLink = f'link:++https://github.com/KhronosGroup/Vulkan-Docs/issues/new?body={issuePlaceholderText}++'
                    prettyHandle = f'{trackerLink}[icon:github[alt=GitHub,role="black"]{handle[1:]},window=_blank,opts=nofollow]'
                else:
                    prettyHandle = handle

                write('  * ' + name + ' ' + prettyHandle, file=fp)
            write('', file=fp)

        # Check if a proposal document for this extension exists in the
        # current repository, and link to the same document (parameterized
        # by a URL prefix attribute) if it does.
        # The assumption is that a proposal document for an extension
        # VK_name will be located in 'proposals/VK_name.adoc' relative
        # to the repository root, and that this script will be invoked from
        # the repository root.
        # If a proposal for this extension does not exist, look for
        # proposals for the extensions it is promoted from.

        def checkProposal(extname):
            """Check if a proposal document for an extension exists,
               returning the path to that proposal or None otherwise."""

            path = 'proposals/{}.adoc'.format(extname)
            if os.path.exists(path) and os.access(path, os.R_OK):
                return path
            else:
                return None

        # List of [ extname, proposal link ]
        proposals = []

        path = checkProposal(self.name)
        if path is not None:
            proposals.append([self.name, path])
        else:
            for name in self.promotedFrom:
                path = checkProposal(name)
                if path is not None:
                    proposals.append([name, path])

        if len(proposals) > 0:
            tag = 'Extension Proposal'
            for (name, path) in sorted(proposals):
                self.writeTag(tag,
                    f'{{proposalRefPath}}{path}[{name}]',
                    isRefpage, fp)
                # Setting tag = None so additional values will not get
                # additional tag headers.
                tag = None

        # If this is metadata to be included in a refpage, adjust the
        # leveloffset to account for the relative structure of the extension
        # appendices vs. refpages.
        if isRefpage and self.conventions.include_extension_appendix_in_refpage:
            write(':leveloffset: -1', file=fp)

        fp.close()

class ExtensionMetaDocOutputGenerator(OutputGenerator):
    """ExtensionMetaDocOutputGenerator - subclass of OutputGenerator.

    Generates AsciiDoc includes with metainformation for the API extension
    appendices. The fields used from <extension> tags in the API XML are:

    - name          extension name string
    - number        extension number (optional)
    - contact       name and GitHub login or email address (optional)
    - type          'instance' | 'device' (optional)
    - depends       boolean expression of core version and extension names this depends on (optional)
    - promotedTo    extension or API version it was promoted to
    - deprecatedBy  extension or API version which deprecated this extension,
                    or empty string if deprecated without replacement
    - obsoletedBy   extension or API version which obsoleted this extension,
                    or empty string if obsoleted without replacement
    - provisional   'true' if this extension is released provisionally"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extensions = {}
        # List of strings containing all vendor tags
        self.vendor_tags = []
        self.file_suffix = ''
        # SPIR-V dependencies, generated in beginFile()
        self.SPV_deps = {}

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

        # If there are <spirvextension> elements in the XML, generate a
        # reverse map from API version and extension names to the SPV
        # extensions they depend on.

        def add_dep(SPV_deps, name, spvname):
            """Add spvname as a dependency of name.
               name may be an API or extension name."""

            if name not in SPV_deps:
                SPV_deps[name] = set()
            SPV_deps[name].add(spvname)

        for spvext in root.findall('spirvextensions/spirvextension'):
            spvname = spvext.get('name')
            for elem in spvext.findall('enable'):
                if elem.get('version'):
                    version_name = elem.get('version')
                    add_dep(self.SPV_deps, version_name, spvname)
                elif elem.get('extension'):
                    ext_name = elem.get('extension')
                    add_dep(self.SPV_deps, ext_name, spvname)

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

    def makeExtensionInclude(self, extname):
        return self.conventions.extension_include_string(extname)

    def endFile(self):
        # Determine the extension an extension is promoted from, if any.
        # This is used when attempting to locate a proposal document in
        # makeMetafile() below.
        for (extname, ext) in self.extensions.items():
            promotedTo = ext.promotedTo
            if promotedTo is not None:
                if promotedTo in self.extensions:
                    #print(f'{promotedTo} is promoted from {extname}')
                    self.extensions[promotedTo].promotedFrom.add(extname)
                    #print(f'setting self.extensions[{promotedTo}].promotedFrom = {self.extensions[promotedTo].promotedFrom}')
                elif not self.conventions.is_api_version_name(promotedTo):
                    self.logMsg('warn', f'{extname} is promoted to {promotedTo} which is not in the extension map')

        # Generate metadoc extension files, in refpage and non-refpage form
        for ext in self.extensions.values():
            ext.makeMetafile(self.extensions, self.SPV_deps, isRefpage = False)
            if self.conventions.write_refpage_include:
                ext.makeMetafile(self.extensions, self.SPV_deps, isRefpage = True)

        # Key to sort extensions alphabetically within 'KHR', 'EXT', vendor
        # extension prefixes.
        def makeSortKey(extname):
            name = extname.lower()
            prefixes = self.conventions.extension_index_prefixes
            for i, prefix in enumerate(prefixes):
                if extname.startswith(prefix):
                    return (i, name)
            return (len(prefixes), name)

        # Generate list of promoted extensions
        promotedExtensions = {}
        for ext in self.extensions.values():
            if ext.deprecationType == 'promotion' and ext.supercedingAPIVersion:
                promotedExtensions.setdefault(ext.supercedingAPIVersion, []).append(ext.name)

        for coreVersion, extensions in promotedExtensions.items():
            promoted_extensions_fp = self.newFile(self.directory + '/promoted_extensions_' + coreVersion + self.file_suffix)

            for extname in sorted(extensions, key=makeSortKey):
                indent = ''
                write('  * {blank}\n+\n' + ext.conditionalLinkExt(extname, indent), file=promoted_extensions_fp)

            promoted_extensions_fp.close()

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

            # Note: there is a hardwired assumption in creating the
            # include:: directives below that all of these files are located
            # in the 'meta/' subdirectory of the generated files directory.
            # This is difficult to change, and it is very unlikely changing
            # it will be needed.

            # Do not include the lengthy '*extension_appendices_toc' indices
            # in the Antora site build, since all the extensions are already
            # indexed on the right navigation sidebar.

            write('', file=current_extensions_appendix_fp)
            write('include::{generated}/meta/deprecated_extensions_guard_macro' + self.file_suffix + '[]', file=current_extensions_appendix_fp)
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
            write('ifndef::site-gen-antora[]', file=current_extensions_appendix_fp)
            write('include::{generated}/meta/current_extension_appendices_toc' + self.file_suffix + '[]', file=current_extensions_appendix_fp)
            write('endif::site-gen-antora[]', file=current_extensions_appendix_fp)
            write('\n<<<\n', file=current_extensions_appendix_fp)
            write('include::{generated}/meta/current_extension_appendices' + self.file_suffix + '[]', file=current_extensions_appendix_fp)

            write('', file=deprecated_extensions_appendix_fp)
            write('include::{generated}/meta/deprecated_extensions_guard_macro' + self.file_suffix + '[]', file=deprecated_extensions_appendix_fp)
            write('', file=deprecated_extensions_appendix_fp)
            write('ifdef::HAS_DEPRECATED_EXTENSIONS[]', file=deprecated_extensions_appendix_fp)
            write('[[deprecated-extension-appendices-list]]', file=deprecated_extensions_appendix_fp)
            write('== List of Deprecated Extensions', file=deprecated_extensions_appendix_fp)
            write('ifndef::site-gen-antora[]', file=deprecated_extensions_appendix_fp)
            write('include::{generated}/meta/deprecated_extension_appendices_toc' + self.file_suffix + '[]', file=deprecated_extensions_appendix_fp)
            write('endif::site-gen-antora[]', file=deprecated_extensions_appendix_fp)
            write('\n<<<\n', file=deprecated_extensions_appendix_fp)
            write('include::{generated}/meta/deprecated_extension_appendices' + self.file_suffix + '[]', file=deprecated_extensions_appendix_fp)
            write('endif::HAS_DEPRECATED_EXTENSIONS[]', file=deprecated_extensions_appendix_fp)

            # add include guards to allow multiple includes
            write('ifndef::DEPRECATED_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD[]', file=deprecated_extensions_guard_macro_fp)
            write(':DEPRECATED_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD:\n', file=deprecated_extensions_guard_macro_fp)
            write('ifndef::PROVISIONAL_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD[]', file=provisional_extensions_guard_macro_fp)
            write(':PROVISIONAL_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD:\n', file=provisional_extensions_guard_macro_fp)

            write('', file=provisional_extensions_appendix_fp)
            write('include::{generated}/meta/provisional_extensions_guard_macro' + self.file_suffix + '[]', file=provisional_extensions_appendix_fp)
            write('', file=provisional_extensions_appendix_fp)
            write('ifdef::HAS_PROVISIONAL_EXTENSIONS[]', file=provisional_extensions_appendix_fp)
            write('[[provisional-extension-appendices-list]]', file=provisional_extensions_appendix_fp)
            write('== List of Provisional Extensions', file=provisional_extensions_appendix_fp)
            write('ifndef::site-gen-antora[]', file=provisional_extensions_appendix_fp)
            write('include::{generated}/meta/provisional_extension_appendices_toc' + self.file_suffix + '[]', file=provisional_extensions_appendix_fp)
            write('endif::site-gen-antora[]', file=provisional_extensions_appendix_fp)
            write('\n<<<\n', file=provisional_extensions_appendix_fp)
            write('include::{generated}/meta/provisional_extension_appendices' + self.file_suffix + '[]', file=provisional_extensions_appendix_fp)
            write('endif::HAS_PROVISIONAL_EXTENSIONS[]', file=provisional_extensions_appendix_fp)

            # Emit extensions in author ID order
            sorted_keys = sorted(self.extensions.keys(), key=makeSortKey)
            for name in sorted_keys:
                ext = self.extensions[name]

                # Increase the leveloffset of the extension include so it is
                # lower than the subsection (extension name) it belongs to
                include =  ':leveloffset: +1\n'
                include += '\n' + self.makeExtensionInclude(ext.name) + '\n\n'
                include += ':leveloffset: -1\n'

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
            write('endif::PROVISIONAL_EXTENSIONS_GUARD_MACRO_INCLUDE_GUARD[]', file=provisional_extensions_guard_macro_fp)

        OutputGenerator.endFile(self)

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)

        if interface.tag != 'extension':
            self.logMsg('diag', 'beginFeature: ignoring non-extension feature', self.featureName)
            return

        name = self.featureName

        # These attributes may be required to exist, depending on the API
        number = self.getAttrib(interface, 'number',
                    self.conventions.write_extension_number)
        ext_type = self.getAttrib(interface, 'type',
                    self.conventions.write_extension_type)
        if self.conventions.write_extension_revision:
            revision = self.getSpecVersion(interface, name)
        else:
            revision = None

        # These attributes are optional
        OPTIONAL = False
        depends = self.getAttrib(interface, 'depends', OPTIONAL)    # TODO should default to base API version 1.0?
        contact = self.getAttrib(interface, 'contact', OPTIONAL)
        promotedTo = self.getAttrib(interface, 'promotedto', OPTIONAL)
        deprecatedBy = self.getAttrib(interface, 'deprecatedby', OPTIONAL)
        obsoletedBy = self.getAttrib(interface, 'obsoletedby', OPTIONAL)
        provisional = self.getAttrib(interface, 'provisional', OPTIONAL, 'false')
        specialuse = self.getAttrib(interface, 'specialuse', OPTIONAL)
        ratified = self.getAttrib(interface, 'ratified', OPTIONAL, '')

        filename = self.directory + '/' + name + self.file_suffix

        extdata = Extension(
            generator = self,
            filename = filename,
            interface = interface,
            name = name,
            number = number,
            ext_type = ext_type,
            depends = depends,
            contact = contact,
            promotedTo = promotedTo,
            deprecatedBy = deprecatedBy,
            obsoletedBy = obsoletedBy,
            provisional = provisional,
            revision = revision,
            specialuse = specialuse,
            ratified = ratified)
        self.extensions[name] = extdata

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
        This only makes sense for Vulkan.

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
