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

import os,re,sys
from generator import *

# DocGeneratorOptions - subclass of GeneratorOptions.
#
# Shares many members with CGeneratorOptions, since
# both are writing C-style declarations:
#
#   prefixText - list of strings to prefix generated header with
#     (usually a copyright statement + calling convention macros).
#   apicall - string to use for the function declaration prefix,
#     such as APICALL on Windows.
#   apientry - string to use for the calling convention macro,
#     in typedefs, such as APIENTRY.
#   apientryp - string to use for the calling convention macro
#     in function pointer typedefs, such as APIENTRYP.
#   directory - directory into which to generate include files
#   indentFuncProto - True if prototype declarations should put each
#     parameter on a separate line
#   indentFuncPointer - True if typedefed function pointers should put each
#     parameter on a separate line
#   alignFuncParam - if nonzero and parameters are being put on a
#     separate line, align parameter names at the specified column
#
# Additional members:
#   expandEnumerants - if True, add BEGIN/END_RANGE macros in enumerated
#     type declarations
#
class DocGeneratorOptions(GeneratorOptions):
    """Represents options during C interface generation for Asciidoc"""
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
                 sortProcedure = regSortFeatures,
                 prefixText = "",
                 apicall = '',
                 apientry = '',
                 apientryp = '',
                 indentFuncProto = True,
                 indentFuncPointer = False,
                 alignFuncParam = 0,
                 expandEnumerants = True):
        GeneratorOptions.__init__(self, filename, directory, apiname, profile,
                                  versions, emitversions, defaultExtensions,
                                  addExtensions, removeExtensions,
                                  emitExtensions, sortProcedure)
        self.prefixText      = prefixText
        self.apicall         = apicall
        self.apientry        = apientry
        self.apientryp       = apientryp
        self.indentFuncProto = indentFuncProto
        self.indentFuncPointer = indentFuncPointer
        self.alignFuncParam  = alignFuncParam
        self.expandEnumerants = expandEnumerants

# DocOutputGenerator - subclass of OutputGenerator.
# Generates AsciiDoc includes with C-language API interfaces, for reference
# pages and the Vulkan specification. Similar to COutputGenerator, but
# each interface is written into a different file as determined by the
# options, only actual C types are emitted, and none of the boilerplate
# preprocessor code is emitted.
#
# ---- methods ----
# DocOutputGenerator(errFile, warnFile, diagFile) - args as for
#   OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# beginFile(genOpts)
# endFile()
# beginFeature(interface, emit)
# endFeature()
# genType(typeinfo,name)
# genStruct(typeinfo,name)
# genGroup(groupinfo,name)
# genEnum(enuminfo, name)
# genCmd(cmdinfo)
class DocOutputGenerator(OutputGenerator):
    """Generate specified API interfaces in a specific style, such as a C header"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
    #
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
    def endFile(self):
        OutputGenerator.endFile(self)
    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)
    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)
    #
    # Generate an include file
    #
    # directory - subdirectory to put file in
    # basename - base name of the file
    # contents - contents of the file (Asciidoc boilerplate aside)
    def writeInclude(self, directory, basename, contents):
        # Create subdirectory, if needed
        directory = self.genOpts.directory + '/' + directory
        self.makeDir(directory)

        # Create file
        filename = directory + '/' + basename + '.txt'
        self.logMsg('diag', '# Generating include file:', filename)
        fp = open(filename, 'w', encoding='utf-8')

        # Asciidoc anchor
        write('// WARNING: DO NOT MODIFY! This file is automatically generated from the vk.xml registry', file=fp)
        write('[[{0},{0}]]'.format(basename), file=fp)
        write('[source,c++]', file=fp)
        write('----', file=fp)
        write(contents, file=fp)
        write('----', file=fp)
        fp.close()
    #
    # Type generation
    def genType(self, typeinfo, name, alias):
        OutputGenerator.genType(self, typeinfo, name, alias)
        typeElem = typeinfo.elem
        # If the type is a struct type, traverse the imbedded <member> tags
        # generating a structure. Otherwise, emit the tag text.
        category = typeElem.get('category')

        body = ''
        if category == 'struct' or category == 'union':
            # If the type is a struct type, generate it using the
            # special-purpose generator.
            self.genStruct(typeinfo, name, alias)
        else:
            if alias:
                # If the type is an alias, just emit a typedef declaration
                body = 'typedef ' + alias + ' ' + name + ';\n'
                self.writeInclude(OutputGenerator.categoryToPath[category],
                    name, body)
            else:
                # Replace <apientry /> tags with an APIENTRY-style string
                # (from self.genOpts). Copy other text through unchanged.
                # If the resulting text is an empty string, don't emit it.
                body = noneStr(typeElem.text)
                for elem in typeElem:
                    if (elem.tag == 'apientry'):
                        body += self.genOpts.apientry + noneStr(elem.tail)
                    else:
                        body += noneStr(elem.text) + noneStr(elem.tail)

                if body:
                    if (category in OutputGenerator.categoryToPath.keys()):
                        self.writeInclude(OutputGenerator.categoryToPath[category],
                            name, body + '\n')
                    else:
                        self.logMsg('diag', '# NOT writing include file for type:',
                            name, '- bad category: ', category)
                else:
                    self.logMsg('diag', '# NOT writing empty include file for type', name)
    #
    # Struct (e.g. C "struct" type) generation.
    # This is a special case of the <type> tag where the contents are
    # interpreted as a set of <member> tags instead of freeform C
    # C type declarations. The <member> tags are just like <param>
    # tags - they are a declaration of a struct or union member.
    # Only simple member declarations are supported (no nested
    # structs etc.)
    # If alias != None, then this struct aliases another; just
    #   generate a typedef of that alias.
    def genStruct(self, typeinfo, typeName, alias):
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)

        typeElem = typeinfo.elem

        if alias:
            body = 'typedef ' + alias + ' ' + typeName + ';\n'
        else:
            body = 'typedef ' + typeElem.get('category') + ' ' + typeName + ' {\n'

            targetLen = 0;
            for member in typeinfo.elem.findall('.//member'):
                targetLen = max(targetLen, self.getCParamTypeLength(member))
            for member in typeElem.findall('.//member'):
                body += self.makeCParamDecl(member, targetLen + 4)
                body += ';\n'
            body += '} ' + typeName + ';'

        self.writeInclude('structs', typeName, body)
    #
    # Group (e.g. C "enum" type) generation.
    # These are concatenated together with other types.
    # If alias != None, it is the name of another group type
    #   which aliases this type; just generate that alias.
    def genGroup(self, groupinfo, groupName, alias):
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)
        groupElem = groupinfo.elem

        if alias:
            filename = groupName

            # If the group name is aliased, just emit a typedef declaration
            # for the alias.
            body = 'typedef ' + alias + ' ' + groupName + ';\n'
        else:
            filename = groupName

            # See if we need min/max/num/padding at end
            expand = self.genOpts.expandEnumerants

            if expand:
                expandName = re.sub(r'([0-9a-z_])([A-Z0-9][^A-Z0-9]?)',r'\1_\2',groupName).upper()
                isEnum = ('FLAG_BITS' not in expandName)

                expandPrefix = expandName
                expandSuffix = ''

                # Look for a suffix
                expandSuffixMatch = re.search(r'[A-Z][A-Z]+$',groupName)
                if expandSuffixMatch:
                    expandSuffix = '_' + expandSuffixMatch.group()
                    # Strip off the suffix from the prefix
                    expandPrefix = expandName.rsplit(expandSuffix, 1)[0]

            # Prefix
            body = "typedef enum " + groupName + " {\n"

            # Get a list of nested 'enum' tags.
            enums = groupElem.findall('enum')

            # Check for and report duplicates, and return a list with them
            # removed.
            enums = self.checkDuplicateEnums(enums)

            # Loop over the nested 'enum' tags. Keep track of the minimum and
            # maximum numeric values, if they can be determined.
            minName = None

            # Accumulate non-numeric enumerant values separately and append
            # them following the numeric values, to allow for aliases.
            # NOTE: this doesn't do a topological sort yet, so aliases of
            # aliases can still get in the wrong order.
            aliasText = ""

            for elem in enums:
                # Convert the value to an integer and use that to track min/max.
                (numVal,strVal) = self.enumToValue(elem, True)
                name = elem.get('name')

                # Extension enumerants are only included if they are required
                if self.isEnumRequired(elem):
                    decl = "    " + name + " = " + strVal + ",\n"
                    if numVal != None:
                        body += decl
                    else:
                        aliasText += decl

                # Don't track min/max for non-numbers (numVal == None)
                if expand and isEnum and numVal != None and elem.get('extends') is None:
                    if (minName == None):
                        minName = maxName = name
                        minValue = maxValue = numVal
                    elif (numVal < minValue):
                        minName = name
                        minValue = numVal
                    elif (numVal > maxValue):
                        maxName = name
                        maxValue = numVal

            # Now append the non-numeric enumerant values
            body += aliasText

            # Generate min/max value tokens and a range-padding enum. Need some
            # additional padding to generate correct names...
            if expand:
                #@ body += "\n"
                if isEnum:
                    body += "    " + expandPrefix + "_BEGIN_RANGE" + expandSuffix + " = " + minName + ",\n"
                    body += "    " + expandPrefix + "_END_RANGE" + expandSuffix + " = " + maxName + ",\n"
                    body += "    " + expandPrefix + "_RANGE_SIZE" + expandSuffix + " = (" + maxName + " - " + minName + " + 1),\n"

                body += "    " + expandPrefix + "_MAX_ENUM" + expandSuffix + " = 0x7FFFFFFF\n"
            # Postfix
            body += "} " + groupName + ";"

        self.writeInclude('enums', filename, body)

    # Enumerant generation
    # <enum> tags may specify their values in several ways, but are usually
    # just integers.
    def genEnum(self, enuminfo, name, alias):
        OutputGenerator.genEnum(self, enuminfo, name, alias)
        (numVal,strVal) = self.enumToValue(enuminfo.elem, False)
        body = '#define ' + name.ljust(33) + ' ' + strVal
        self.logMsg('diag', '# NOT writing compile-time constant', name)
        # self.writeInclude('consts', name, body)
    #
    # Command generation
    def genCmd(self, cmdinfo, name, alias):
        OutputGenerator.genCmd(self, cmdinfo, name, alias)
        #
        decls = self.makeCDecls(cmdinfo.elem)
        self.writeInclude('protos', name, decls[0])
