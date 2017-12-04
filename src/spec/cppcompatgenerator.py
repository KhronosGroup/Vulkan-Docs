#!/usr/bin/python3 -i
#
# Copyright (c) 2013-2017 The Khronos Group Inc.
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

# CppcompatGeneratorOptions - subclass of GeneratorOptions.
#
# Adds options used by CppcompatOutputGenerator objects during C++
# compatibility header generation.
#
# Additional members
#   vulkanHeaderFile - Filename of the Vulkan header
class CppcompatGeneratorOptions(GeneratorOptions):
    """Represents options during C interface generation for headers"""
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
                 sortProcedure = regSortFeatures,
                 vulkanHeaderFile = ""):
        GeneratorOptions.__init__(self, filename, directory, apiname, profile,
                                  versions, emitversions, defaultExtensions,
                                  addExtensions, removeExtensions, sortProcedure)
        self.vulkanHeaderFile = vulkanHeaderFile

# CppcompatOutputGenerator - subclass of OutputGenerator.
# Generates C++ compatibility wrapper for Vulkan header
#
# ---- methods ----
# COutputGenerator(errFile, warnFile, diagFile) - args as for
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
class CppcompatOutputGenerator(OutputGenerator):
    """Generate specified API interfaces in a specific style, such as a C header"""
    # This is an ordered list of sections in the header file.
    TYPE_SECTIONS = ['include', 'define', 'basetype', 'handle', 'enum',
                     'group', 'bitmask', 'funcpointer', 'struct']
    ALL_SECTIONS = TYPE_SECTIONS + ['commandPointer', 'command']
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
        # Internal state - accumulators for different inner block text
        self.sections = dict([(section, []) for section in self.ALL_SECTIONS])
    #
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        headerSym = re.sub('\.h', '_h_', os.path.basename(self.genOpts.vulkanHeaderFile)).upper()
        cppCompatHeaderSym = os.path.basename(self.genOpts.filename).upper().replace('.', '_') + '_'
        write('#ifndef', cppCompatHeaderSym, file=self.outFile)
        write('#define', cppCompatHeaderSym, '1', file=self.outFile)
        self.newline()
        write('#ifdef', headerSym, file=self.outFile)
        write('    #error vulkan.h included before vulkan.cppcompat.h! Do not mix use of '
            + self.genOpts.vulkanHeaderFile + ' and ' + self.genOpts.filename + '!',
            file=self.outFile)
        write('#endif', file=self.outFile)
        self.newline()
    #
    def endFile(self):
        write('#include "' + self.genOpts.vulkanHeaderFile + '"', file=self.outFile)
        self.newline()
        write('#endif', file=self.outFile)

        # Finish processing in superclass
        OutputGenerator.endFile(self)
    #
    # Type generation
    def genType(self, typeinfo, name):
        OutputGenerator.genType(self, typeinfo, name)
        typeElem = typeinfo.elem
        # If the type is a struct type, traverse the imbedded <member> tags
        # generating a structure. Otherwise, emit the tag text.
        category = typeElem.get('category')
        if (category == 'struct' or category == 'union'):
            self.genStruct(typeinfo, name)
    #
    # Struct (e.g. C "struct" type) generation.
    # This is a special case of the <type> tag where the contents are
    # interpreted as a set of <member> tags instead of freeform C
    # C type declarations. The <member> tags are just like <param>
    # tags - they are a declaration of a struct or union member.
    # Only simple member declarations are supported (no nested
    # structs etc.)
    def genStruct(self, typeinfo, typeName):
        OutputGenerator.genStruct(self, typeinfo, typeName)
        placeholderDef = ''

        for member in typeinfo.elem.findall('.//member'):
            for elem in member:
                if (elem.tag == 'name' and elem.attrib.get('cppcompatname') is not None):
                    placeholderMacro = self.toPlaceholderMacro(typeName, elem.text)
                    compatName = elem.attrib.get('cppcompatname')
                    placeholderDef += '#define ' + placeholderMacro + ' ' + compatName + '\n'
        if placeholderDef:
            write(placeholderDef, file=self.outFile)
