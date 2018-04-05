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

# PyOutputGenerator - subclass of OutputGenerator.
# Generates Python data structures describing API names and relationships.
# Similar to DocOutputGenerator, but writes a single file.
#
# ---- methods ----
# PyOutputGenerator(errFile, warnFile, diagFile) - args as for
#   OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# beginFile(genOpts)
# endFile()
# genType(typeinfo,name)
# genStruct(typeinfo,name)
# genGroup(groupinfo,name)
# genEnum(enuminfo, name)
# genCmd(cmdinfo)
class PyOutputGenerator(OutputGenerator):
    """Generate specified API interfaces in a specific style, such as a C header"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
    #
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
        #
        # Dictionaries are keyed by the name of the entity (e.g.
        # self.structs is keyed by structure names). Values are
        # the names of related entities (e.g. structs contain
        # a list of type names of members, enums contain a list
        # of enumerants belong to the enumerated type, etc.), or
        # just None if there are no directly related entities.
        #
        # Collect the mappings, then emit the Python script in endFile
        self.basetypes = {}
        self.consts = {}
        self.enums = {}
        self.flags = {}
        self.funcpointers = {}
        self.protos = {}
        self.structs = {}
        self.handles = {}
        self.defines = {}
        # Dictionary containing the type of a type name
        # (e.g. the string name of the dictionary with its contents).
        self.typeCategory = {}
        self.mapDict = {}
    def endFile(self):
        # Print out all the dictionaries as Python strings.
        # Could just print(dict) but that's not human-readable
        dicts = [ [ self.basetypes,     'basetypes' ],
                  [ self.consts,        'consts' ],
                  [ self.enums,         'enums' ],
                  [ self.flags,         'flags' ],
                  [ self.funcpointers,  'funcpointers' ],
                  [ self.protos,        'protos' ],
                  [ self.structs,       'structs' ],
                  [ self.handles,       'handles' ],
                  [ self.defines,       'defines' ],
                  [ self.typeCategory,  'typeCategory' ] ]
        for (dict, name) in dicts:
            write(name + ' = {}', file=self.outFile)
            for key in sorted(dict.keys()):
                write(name + '[' + enquote(key) + '] = ', dict[key], file=self.outFile)

        # Dictionary containing the relationships of a type
        # (e.g. a dictionary with each related type as keys).
        write('mapDict = {}', file=self.outFile)

        # Could just print(self.mapDict), but prefer something human-readable
        for baseType in sorted(self.mapDict.keys()):
            write('mapDict[' + enquote(baseType) + '] = ', self.mapDict[baseType], file=self.outFile)

        OutputGenerator.endFile(self)
    # Add a string entry to the dictionary, quoting it so it gets printed
    # out correctly in self.endFile()
    def addName(self, dict, name, value):
        dict[name] = enquote(value)
    # Add a mapping between types to mapDict. Only include Vulkan types,
    # so we don't end up with a lot of useless uint32_t and void types.
    def addMapping(self, baseType, refType):
        if (not apiName(baseType) or not apiName(refType)):
            self.logMsg('diag', 'PyOutputGenerator::addMapping: IGNORE map from', baseType, '<->', refType)
            return
        else:
            self.logMsg('diag', 'PyOutputGenerator::addMapping: map from', baseType, '<->', refType)

        if (not baseType in self.mapDict.keys()):
            baseDict = {}
            self.mapDict[baseType] = baseDict
        else:
            baseDict = self.mapDict[baseType]
        if (not refType in self.mapDict.keys()):
            refDict = {}
            self.mapDict[refType] = refDict
        else:
            refDict = self.mapDict[refType]

        baseDict[refType] = None
        refDict[baseType] = None
    #
    # Type generation
    # For 'struct' or 'union' types, defer to genStruct() to
    #   add to the dictionary.
    # For 'bitmask' types, add the type name to the 'flags' dictionary,
    #   with the value being the corresponding 'enums' name defining
    #   the acceptable flag bits.
    # For 'enum' types, add the type name to the 'enums' dictionary,
    #   with the value being '@STOPHERE@' (because this case seems
    #   never to happen).
    # For 'funcpointer' types, add the type name to the 'funcpointers'
    #   dictionary.
    # For 'handle' and 'define' types, add the handle or #define name
    #   to the 'struct' dictionary, because that's how the spec sources
    #   tag these types even though they aren't structs.
    def genType(self, typeinfo, name, alias):
        OutputGenerator.genType(self, typeinfo, name, alias)
        typeElem = typeinfo.elem
        # If the type is a struct type, traverse the imbedded <member> tags
        # generating a structure. Otherwise, emit the tag text.
        category = typeElem.get('category')

        # Add a typeCategory{} entry for the category of this type.
        self.addName(self.typeCategory, name, category)

        if (category == 'struct' or category == 'union'):
            self.genStruct(typeinfo, name, alias)
        else:
            # Extract the type name
            # (from self.genOpts). Copy other text through unchanged.
            # If the resulting text is an empty string, don't emit it.
            count = len(noneStr(typeElem.text))
            for elem in typeElem:
                count += len(noneStr(elem.text)) + len(noneStr(elem.tail))
            if (count > 0):
                if (category == 'bitmask'):
                    requiredEnum = typeElem.get('requires')
                    self.addName(self.flags, name, requiredEnum)

                    # This happens when the Flags type is defined, but no
                    # FlagBits are defined yet.
                    if (requiredEnum != None):
                        self.addMapping(name, requiredEnum)
                elif (category == 'enum'):
                    # This case does not seem to come up. It nominally would
                    # result from
                    #   <type name="VkSomething" category="enum"/>,
                    # but the output generator doesn't emit them directly.
                    self.logMsg('warn', 'PyOutputGenerator::genType: invalid \'enum\' category for name:', name)
                elif (category == 'funcpointer'):
                    self.funcpointers[name] = None
                elif (category == 'handle'):
                    self.handles[name] = None
                elif (category == 'define'):
                    self.defines[name] = None
                elif (category == 'basetype'):
                    # Don't add an entry for base types that aren't Vulkan types
                    # e.g. VkBool32 gets one, uint32_t does not
                    if (apiName(name)):
                        self.basetypes[name] = None
                        self.addName(self.typeCategory, name, 'basetype')
                    else:
                        self.logMsg('diag', 'PyOutputGenerator::genType: unprocessed type:', name, 'category:', category)
            else:
                self.logMsg('diag', 'PyOutputGenerator::genType: unprocessed type:', name)
    #
    # Struct (e.g. C "struct" type) generation.
    #
    # Add the struct name to the 'structs' dictionary, with the
    # value being an ordered list of the struct member names.
    def genStruct(self, typeinfo, typeName, alias):
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)

        members = [member.text for member in typeinfo.elem.findall('.//member/name')]
        self.structs[typeName] = members
        memberTypes = [member.text for member in typeinfo.elem.findall('.//member/type')]
        for type in memberTypes:
            self.addMapping(typeName, type)
    #
    # Group (e.g. C "enum" type) generation.
    # These are concatenated together with other types.
    #
    # Add the enum type name to the 'enums' dictionary, with
    #   the value being an ordered list of the enumerant names.
    # Add each enumerant name to the 'consts' dictionary, with
    #   the value being the enum type the enumerant is part of.
    def genGroup(self, groupinfo, groupName, alias):
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)
        groupElem = groupinfo.elem

        # Loop over the nested 'enum' tags.
        enumerants = [elem.get('name') for elem in groupElem.findall('enum')]
        for name in enumerants:
            self.addName(self.consts, name, groupName)
        self.enums[groupName] = enumerants
    # Enumerant generation (compile-time constants)
    #
    # Add the constant name to the 'consts' dictionary, with the
    #   value being None to indicate that the constant isn't
    #   an enumeration value.
    def genEnum(self, enuminfo, name, alias):
        OutputGenerator.genEnum(self, enuminfo, name, alias)

        # Add a typeCategory{} entry for the category of this type.
        self.addName(self.typeCategory, name, 'consts')

        self.consts[name] = None
    #
    # Command generation
    #
    # Add the command name to the 'protos' dictionary, with the
    #   value being an ordered list of the parameter names.
    def genCmd(self, cmdinfo, name, alias):
        OutputGenerator.genCmd(self, cmdinfo, name, alias)

        # Add a typeCategory{} entry for the category of this type.
        self.addName(self.typeCategory, name, 'protos')

        params = [param.text for param in cmdinfo.elem.findall('param/name')]
        self.protos[name] = params
        paramTypes = [param.text for param in cmdinfo.elem.findall('param/type')]
        for type in paramTypes:
            self.addMapping(name, type)
