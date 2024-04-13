#!/usr/bin/python3 -i
#
# Copyright 2013-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from generator import GeneratorOptions, OutputGenerator, noneStr, write
from parse_dependency import dependencyLanguageComment

_ENUM_TABLE_PREFIX = """
[cols=",",options="header",]
|====
|Enum |Description"""

_TABLE_SUFFIX = """|===="""

_ENUM_BLOCK_PREFIX = """.Enumerant Descriptions
****"""

_FLAG_BLOCK_PREFIX = """.Flag Descriptions
****"""

_BLOCK_SUFFIX = """****"""

def orgLevelKey(name):
    # Sort key for organization levels of features / extensions
    # From highest to lowest, core versions, KHR extensions, EXT extensions,
    # and vendor extensions

    prefixes = (
        'VK_VERSION_',
        'VKSC_VERSION_',
        'VK_KHR_',
        'VK_EXT_')

    i = 0
    for prefix in prefixes:
        if name.startswith(prefix):
            return i
        i += 1

    # Everything else (e.g. vendor extensions) is least important
    return i


class DocGeneratorOptions(GeneratorOptions):
    """DocGeneratorOptions - subclass of GeneratorOptions for
    generating declaration snippets for the spec.

    Shares many members with CGeneratorOptions, since
    both are writing C-style declarations."""

    def __init__(self,
                 prefixText="",
                 apicall='',
                 apientry='',
                 apientryp='',
                 indentFuncProto=True,
                 indentFuncPointer=False,
                 alignFuncParam=0,
                 secondaryInclude=False,
                 expandEnumerants=True,
                 extEnumerantAdditions=False,
                 extEnumerantFormatString=" (Added by the {} extension)",
                 **kwargs):
        """Constructor.

        Since this generator outputs multiple files at once,
        the filename is just a "stamp" to indicate last generation time.

        Shares many parameters/members with CGeneratorOptions, since
        both are writing C-style declarations:

        - prefixText - list of strings to prefix generated header with
        (usually a copyright statement + calling convention macros).
        - apicall - string to use for the function declaration prefix,
        such as APICALL on Windows.
        - apientry - string to use for the calling convention macro,
        in typedefs, such as APIENTRY.
        - apientryp - string to use for the calling convention macro
        in function pointer typedefs, such as APIENTRYP.
        - indentFuncProto - True if prototype declarations should put each
        parameter on a separate line
        - indentFuncPointer - True if typedefed function pointers should put each
        parameter on a separate line
        - alignFuncParam - if nonzero and parameters are being put on a
        separate line, align parameter names at the specified column

        Additional parameters/members:

        - expandEnumerants - if True, add BEGIN/END_RANGE macros in enumerated
        type declarations
        - secondaryInclude - if True, add secondary (no xref anchor) versions
        of generated files
        - extEnumerantAdditions - if True, include enumerants added by extensions
        in comment tables for core enumeration types.
        - extEnumerantFormatString - A format string for any additional message for
        enumerants from extensions if extEnumerantAdditions is True. The correctly-
        marked-up extension name will be passed.
        """
        GeneratorOptions.__init__(self, **kwargs)
        self.prefixText = prefixText
        """list of strings to prefix generated header with (usually a copyright statement + calling convention macros)."""

        self.apicall = apicall
        """string to use for the function declaration prefix, such as APICALL on Windows."""

        self.apientry = apientry
        """string to use for the calling convention macro, in typedefs, such as APIENTRY."""

        self.apientryp = apientryp
        """string to use for the calling convention macro in function pointer typedefs, such as APIENTRYP."""

        self.indentFuncProto = indentFuncProto
        """True if prototype declarations should put each parameter on a separate line"""

        self.indentFuncPointer = indentFuncPointer
        """True if typedefed function pointers should put each parameter on a separate line"""

        self.alignFuncParam = alignFuncParam
        """if nonzero and parameters are being put on a separate line, align parameter names at the specified column"""

        self.secondaryInclude = secondaryInclude
        """if True, add secondary (no xref anchor) versions of generated files"""

        self.expandEnumerants = expandEnumerants
        """if True, add BEGIN/END_RANGE macros in enumerated type declarations"""

        self.extEnumerantAdditions = extEnumerantAdditions
        """if True, include enumerants added by extensions in comment tables for core enumeration types."""

        self.extEnumerantFormatString = extEnumerantFormatString
        """A format string for any additional message for
        enumerants from extensions if extEnumerantAdditions is True. The correctly-
        marked-up extension name will be passed."""


class DocOutputGenerator(OutputGenerator):
    """DocOutputGenerator - subclass of OutputGenerator.

    Generates AsciiDoc includes with C-language API interfaces, for reference
    pages and the corresponding specification. Similar to COutputGenerator,
    but each interface is written into a different file as determined by the
    options, only actual C types are emitted, and none of the boilerplate
    preprocessor code is emitted."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        # This should be a separate conventions property rather than an
        # inferred type name pattern for different APIs.
        self.result_type = genOpts.conventions.type_prefix + "Result"

    def endFile(self):
        OutputGenerator.endFile(self)

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)

        # Decide if we are in a core <feature> or an <extension>
        self.in_core = (interface.tag == 'feature')

    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    def genRequirements(self, name, mustBeFound = True):
        """Generate text showing what core versions and extensions introduce
        an API. This relies on the map in apimap.py, which may be loaded at
        runtime into self.apidict. If not present, no message is
        generated.

        - name - name of the API
        - mustBeFound - If True, when requirements for 'name' cannot be
          determined, a warning comment is generated.
        """

        if self.apidict:
            if name in self.apidict.requiredBy:
                # It is possible to get both 'A with B' and 'B with A' for
                # the same API.
                # To simplify this, sort the (base,dependency) requirements
                # and put them in a set to ensure they are unique.
                features = set()
                # 'dependency' may be a boolean expression of extension names
                for (base,dependency) in self.apidict.requiredBy[name]:
                    if dependency is not None:
                        # 'dependency' may be a boolean expression of extension
                        # names, in which case the sorting will not work well.

                        # First, convert it from asciidoctor markup to language.
                        depLanguage = dependencyLanguageComment(dependency)

                        # If they are the same, the dependency is only a
                        # single extension, and sorting them works.
                        # Otherwise, skip it.
                        if depLanguage == dependency:
                            deps = sorted(
                                    sorted((base, dependency)),
                                    key=orgLevelKey)
                            depString = ' with '.join(deps)
                        else:
                            # An expression with multiple extensions
                            depString = f'{base} with {depLanguage}'

                        features.add(depString)
                    else:
                        features.add(base)
                # Sort the overall dependencies so core versions are first
                provider = ', '.join(sorted(
                                        sorted(features),
                                        key=orgLevelKey))
                return f'// Provided by {provider}\n'
            else:
                if mustBeFound:
                    self.logMsg('warn', 'genRequirements: API {} not found'.format(name))
                return ''
        else:
            # No API dictionary available, return nothing
            return ''

    def writeInclude(self, directory, basename, contents):
        """Generate an include file.

        - directory - subdirectory to put file in
        - basename - base name of the file
        - contents - contents of the file (Asciidoc boilerplate aside)"""
        # Create subdirectory, if needed
        directory = self.genOpts.directory + '/' + directory
        self.makeDir(directory)

        # Create file
        filename = directory + '/' + basename + self.file_suffix
        self.logMsg('diag', '# Generating include file:', filename)
        fp = open(filename, 'w', encoding='utf-8')

        # Asciidoc anchor
        write(self.genOpts.conventions.warning_comment, file=fp)
        write('[[{0}]]'.format(basename), file=fp)

        if self.genOpts.conventions.generate_index_terms:
            if basename.startswith(self.conventions.command_prefix):
                index_term = basename + " (function)"
            elif basename.startswith(self.conventions.type_prefix):
                index_term = basename + " (type)"
            elif basename.startswith(self.conventions.api_prefix):
                index_term = basename + " (define)"
            else:
                index_term = basename
            write('indexterm:[{}]'.format(index_term), file=fp)

        source_options = self.conventions.docgen_source_options
        source_language = self.conventions.docgen_language
        source_directive = f'[source{source_options},{source_language}]'

        write(source_directive, file=fp)
        write('----', file=fp)
        write(contents, file=fp)
        write('----', file=fp)
        fp.close()

        if self.genOpts.secondaryInclude:
            # Create secondary no cross-reference include file
            filename = f'{directory}/{basename}.no-xref{self.file_suffix}'
            self.logMsg('diag', '# Generating include file:', filename)
            fp = open(filename, 'w', encoding='utf-8')

            # Asciidoc anchor
            write(self.genOpts.conventions.warning_comment, file=fp)
            write('// Include this no-xref version without cross reference id for multiple includes of same file', file=fp)
            write(source_directive, file=fp)
            write('----', file=fp)
            write(contents, file=fp)
            write('----', file=fp)
            fp.close()

    def writeEnumTable(self, basename, values):
        """Output a table of enumerants."""
        directory = Path(self.genOpts.directory) / 'enums'
        self.makeDir(str(directory))

        filename = str(directory / f'{basename}.comments{self.file_suffix}')
        self.logMsg('diag', '# Generating include file:', filename)

        with open(filename, 'w', encoding='utf-8') as fp:
            write(self.conventions.warning_comment, file=fp)
            write(_ENUM_TABLE_PREFIX, file=fp)

            for data in values:
                write("|ename:{}".format(data['name']), file=fp)
                write("|{}".format(data['comment']), file=fp)

            write(_TABLE_SUFFIX, file=fp)

    def writeBox(self, filename, prefix, items):
        """Write a generalized block/box for some values."""
        self.logMsg('diag', '# Generating include file:', filename)

        with open(filename, 'w', encoding='utf-8') as fp:
            write(self.conventions.warning_comment, file=fp)
            write(prefix, file=fp)

            for item in items:
                write("* {}".format(item), file=fp)

            write(_BLOCK_SUFFIX, file=fp)

    def writeEnumBox(self, basename, values):
        """Output a box of enumerants."""
        directory = Path(self.genOpts.directory) / 'enums'
        self.makeDir(str(directory))

        filename = str(directory / f'{basename}.comments-box{self.file_suffix}')
        self.writeBox(filename, _ENUM_BLOCK_PREFIX,
                      ("ename:{} -- {}".format(data['name'], data['comment'])
                       for data in values))

    def writeFlagBox(self, basename, values):
        """Output a box of flag bit comments."""
        directory = Path(self.genOpts.directory) / 'enums'
        self.makeDir(str(directory))

        filename = str(directory / f'{basename}.comments{self.file_suffix}')
        self.writeBox(filename, _FLAG_BLOCK_PREFIX,
                      ("ename:{} -- {}".format(data['name'], data['comment'])
                       for data in values))

    def genType(self, typeinfo, name, alias):
        """Generate type."""
        OutputGenerator.genType(self, typeinfo, name, alias)
        typeElem = typeinfo.elem
        # If the type is a struct type, traverse the embedded <member> tags
        # generating a structure. Otherwise, emit the tag text.
        category = typeElem.get('category')

        if category in ('struct', 'union'):
            # If the type is a struct type, generate it using the
            # special-purpose generator.
            self.genStruct(typeinfo, name, alias)
        elif category not in OutputGenerator.categoryToPath:
            # If there is no path, do not write output
            self.logMsg('diag', 'NOT writing include for {} category {}'.format(
                        name, category))
        else:
            body = self.genRequirements(name)
            if alias:
                # If the type is an alias, just emit a typedef declaration
                body += 'typedef ' + alias + ' ' + name + ';\n'
                self.writeInclude(OutputGenerator.categoryToPath[category],
                                  name, body)
            else:
                # Replace <apientry /> tags with an APIENTRY-style string
                # (from self.genOpts). Copy other text through unchanged.
                # If the resulting text is an empty string, do not emit it.
                body += noneStr(typeElem.text)
                for elem in typeElem:
                    if elem.tag == 'apientry':
                        body += self.genOpts.apientry + noneStr(elem.tail)
                    else:
                        body += noneStr(elem.text) + noneStr(elem.tail)

                if body:
                    self.writeInclude(OutputGenerator.categoryToPath[category],
                                      name, body + '\n')
                else:
                    self.logMsg('diag', 'NOT writing empty include file for type', name)

    def genStructBody(self, typeinfo, typeName):
        """
        Returns the body generated for a struct.

        Factored out to allow aliased types to also generate the original type.
        """
        typeElem = typeinfo.elem
        body = 'typedef ' + typeElem.get('category') + ' ' + typeName + ' {\n'

        targetLen = self.getMaxCParamTypeLength(typeinfo)
        for member in typeElem.findall('.//member'):
            body += self.makeCParamDecl(member, targetLen + 4)
            body += ';\n'
        body += '} ' + typeName + ';'
        return body

    def genStruct(self, typeinfo, typeName, alias):
        """Generate struct."""
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)

        body = self.genRequirements(typeName)
        if alias:
            if self.conventions.duplicate_aliased_structs:
                # TODO maybe move this outside the conditional? This would be a visual change.
                body += '// {} is an alias for {}\n'.format(typeName, alias)
                alias_info = self.registry.typedict[alias]
                body += self.genStructBody(alias_info, alias)
                body += '\n\n'
            body += 'typedef ' + alias + ' ' + typeName + ';\n'
        else:
            body += self.genStructBody(typeinfo, typeName)

        self.writeInclude('structs', typeName, body)

    def genEnumTable(self, groupinfo, groupName):
        """Generate tables of enumerant values and short descriptions from
        the XML."""

        values = []
        got_comment = False
        missing_comments = []
        for elem in groupinfo.elem.findall('enum'):
            if not elem.get('required'):
                continue
            name = elem.get('name')

            data = {
                'name': name,
            }

            (numVal, _) = self.enumToValue(elem, True)
            data['value'] = numVal

            extname = elem.get('extname')

            added_by_extension_to_core = (extname is not None and self.in_core)
            if added_by_extension_to_core and not self.genOpts.extEnumerantAdditions:
                # We are skipping such values
                continue

            comment = elem.get('comment')
            if comment:
                got_comment = True
            elif name.endswith('_UNKNOWN') and numVal == 0:
                # This is a placeholder for 0-initialization to be clearly invalid.
                # Just skip this silently
                continue
            else:
                # Skip but record this in case it is an odd-one-out missing
                # a comment.
                missing_comments.append(name)
                continue

            if added_by_extension_to_core and self.genOpts.extEnumerantFormatString:
                # Add a note to the comment
                comment += self.genOpts.extEnumerantFormatString.format(
                    self.conventions.formatExtension(extname))

            data['comment'] = comment
            values.append(data)

        if got_comment:
            # If any had a comment, output it.

            if missing_comments:
                self.logMsg('warn', 'The following values for', groupName,
                            'were omitted from the table due to missing comment attributes:',
                            ', '.join(missing_comments))

            group_type = groupinfo.elem.get('type')
            if groupName == self.result_type:
                # Split this into success and failure
                self.writeEnumTable(groupName + '.success',
                                (data for data in values
                                 if data['value'] >= 0))
                self.writeEnumTable(groupName + '.error',
                                (data for data in values
                                 if data['value'] < 0))
            elif group_type == 'bitmask':
                self.writeFlagBox(groupName, values)
            elif group_type == 'enum':
                self.writeEnumTable(groupName, values)
                self.writeEnumBox(groupName, values)
            else:
                raise RuntimeError("Unrecognized enums type: " + str(group_type))

    def genGroup(self, groupinfo, groupName, alias):
        """Generate group (e.g. C "enum" type)."""
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)

        body = self.genRequirements(groupName)
        if alias:
            # If the group name is aliased, just emit a typedef declaration
            # for the alias.
            body += 'typedef ' + alias + ' ' + groupName + ';\n'
        else:
            expand = self.genOpts.expandEnumerants
            (_, enumbody) = self.buildEnumCDecl(expand, groupinfo, groupName)
            body += enumbody
            if self.genOpts.conventions.generate_enum_table:
                self.genEnumTable(groupinfo, groupName)

        self.writeInclude('enums', groupName, body)

    def genEnum(self, enuminfo, name, alias):
        """Generate the C declaration for a constant (a single <enum> value)."""

        OutputGenerator.genEnum(self, enuminfo, name, alias)

        body = self.buildConstantCDecl(enuminfo, name, alias)

        self.writeInclude('enums', name, body)

    def genCmd(self, cmdinfo, name, alias):
        "Generate command."
        OutputGenerator.genCmd(self, cmdinfo, name, alias)

        body = self.genRequirements(name)
        decls = self.makeCDecls(cmdinfo.elem)
        body += decls[0]
        self.writeInclude('protos', name, body)
