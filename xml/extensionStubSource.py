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

doc = """
/*
** This target is no longer maintained and supported.
** See README.adoc for discussion.
**
** This is a simple extension loader which provides the implementations for the
** extension prototypes declared in vulkan header. It supports loading extensions either
** for a single instance or a single device. Multiple instances are not yet supported.
**
** To use the loader add vulkan_ext.c to your solution and include <vulkan/vulkan_ext.h>.
**
** If your application is using a single instance, but multiple devices callParam
**
** vkExtInitInstance(instance);
**
** after initializing the instance. This way the extension loader will use the loaders
** trampoline functions to call the correct driver for each call. This method is safe
** if your application might use more than one device at the cost of one additional
** indirection, the dispatch table of each dispatchable object.
**
** If your application uses only a single device it's better to use
**
** vkExtInitDevice(device);
**
** once the device has been initialized. This will resolve the function pointers
** upfront and thus removes one indirection for each call into the driver. This *can*
** result in slightly more performance for calling overhead limited cases.
*/
"""

# StubExtGeneratorOptions - subclass of GeneratorOptions.
#
# Adds options used by COutputGenerator objects during C language header
# generation.
#
# Additional members
#   prefixText - list of strings to prefix generated header with
#     (usually a copyright statement + calling convention macros).
#   alignFuncParam - if nonzero and parameters are being put on a
#     separate line, align parameter names at the specified column
class StubExtGeneratorOptions(GeneratorOptions):
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
                 emitExtensions = None,
                 sortProcedure = regSortFeatures,
                 prefixText = "",
                 alignFuncParam = 0):
        GeneratorOptions.__init__(self, filename, directory, apiname, profile,
                                  versions, emitversions, defaultExtensions,
                                  addExtensions, removeExtensions,
                                  emitExtensions, sortProcedure)
        self.prefixText      = prefixText
        self.alignFuncParam  = alignFuncParam

# ExtensionStubSourceOutputGenerator - subclass of OutputGenerator.
# Generates C-language extension wrapper interface sources.
#
# ---- methods ----
# ExtensionStubSourceOutputGenerator(errFile, warnFile, diagFile) - args as for
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
class ExtensionStubSourceOutputGenerator(OutputGenerator):
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
    #
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
        # C-specific
        #
        # Multiple inclusion protection & C++ wrappers.

        # Internal state - accumulators for function pointers and function
        # pointer initializatoin
        self.pointers = [];
        self.pointerInitializersInstance = [];
        self.pointerInitializersDevice = [];

        #
        # Write header protection
        filename = self.genOpts.directory + '/' + 'vulkan_ext.h'
        self.outFileHeader = open(filename, 'w', encoding='utf-8')

        write('#ifndef VULKAN_EXT_H', file=self.outFileHeader)
        write('#define VULKAN_EXT_H', file=self.outFileHeader)
        write('', file=self.outFileHeader)
        write('#ifdef __cplusplus', file=self.outFileHeader)
        write('extern "C" {', file=self.outFileHeader)
        write('#endif', file=self.outFileHeader)

        #
        # User-supplied prefix text, if any (list of strings)
        if (genOpts.prefixText):
            for s in genOpts.prefixText:
                write(s, file=self.outFile)
                write(s, file=self.outFileHeader)

        write(doc, file=self.outFileHeader)

        write('#include <vulkan/vulkan.h>', file=self.outFile)
        self.newline()

        write('#include <vulkan/vulkan_core.h>', file=self.outFileHeader)
        write('', file=self.outFileHeader)

        write('void vkExtInitInstance(VkInstance instance);', file=self.outFileHeader)
        write('void vkExtInitDevice(VkDevice device);', file=self.outFileHeader)
        write('', file=self.outFileHeader)

    def endFile(self):
        for pointer in self.pointers:
          write(pointer, file=self.outFile)

        self.newline()

        write('void vkExtInitInstance(VkInstance instance)\n{', file=self.outFile)
        for pointerInitializer in self.pointerInitializersInstance:
          write(pointerInitializer, file=self.outFile)
        write('}', file=self.outFile)

        self.newline()

        write('void vkExtInitDevice(VkDevice device)\n{', file=self.outFile)
        for pointerInitializer in self.pointerInitializersDevice:
          write(pointerInitializer, file=self.outFile)
        write('}', file=self.outFile)

        self.newline()

        #Finish header file
        write('#ifdef __cplusplus', file=self.outFileHeader)
        write('}', file=self.outFileHeader)
        write('#endif', file=self.outFileHeader)
        write('', file=self.outFileHeader)
        write('#endif', file=self.outFileHeader)
        self.outFileHeader.close()

        # Finish processing in superclass
        OutputGenerator.endFile(self)

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)

        # Accumulate function pointers and function pointer initialization
        self.featurePointers = []
        self.featurePointerInitializersInstance = []
        self.featurePointerInitializersDevice = []

    def endFeature(self):
        # Add feature to global list with protectFeature
        if (self.emit and self.featurePointers):
          if (self.genOpts.protectFeature):
              self.pointers.append('#ifdef ' + self.featureName)
              self.pointerInitializersInstance.append('#ifdef ' + self.featureName)
              self.pointerInitializersDevice.append('#ifdef ' + self.featureName)

          if (self.featureExtraProtect != None):
              self.pointers.append('#ifdef ' + self.featureExtraProtect)
              self.pointerInitializersInstance.append('#ifndef ' + self.featureName)
              self.pointerInitializersDevice.append('#ifndef ' + self.featureName)

          self.pointers += self.featurePointers;
          self.pointerInitializersInstance += self.featurePointerInitializersInstance;
          self.pointerInitializersDevice += self.featurePointerInitializersDevice;

          if (self.featureExtraProtect != None):
              self.pointers.append('#endif /* ' + self.featureExtraProtect + ' */')
              self.pointerInitializersInstance.append('#endif /* ' + self.featureExtraProtect + ' */')
              self.pointerInitializersDevice.append('#endif /* ' + self.featureExtraProtect + ' */')
          if (self.genOpts.protectFeature):
              self.pointers.append('#endif /* ' + self.featureName + ' */')
              self.pointerInitializersInstance.append('#endif /* ' + self.featureName + ' */')
              self.pointerInitializersDevice.append('#endif /* ' + self.featureName + ' */')

        # Finish processing in superclass
        OutputGenerator.endFeature(self)
    #
    # Type generation
    def genType(self, typeinfo, name, alias):
      pass

    def genStruct(self, typeinfo, typeName, alias):
      pass

    def genGroup(self, groupinfo, groupName, alias):
      pass

    def genEnum(self, enuminfo, name, alias):
      pass

      #
    # Command generation
    def genCmd(self, cmdinfo, name, alias):
        OutputGenerator.genCmd(self, cmdinfo, name, alias)

        #
        decls = self.makeStub(cmdinfo.elem)
        self.featurePointerInitializersInstance.append(decls[0])
        self.featurePointerInitializersDevice.append(decls[1])
        self.featurePointers.append(decls[2])

    #
    # makeStub - return static declaration for function pointer and initialization of function pointer
    # as a two-element list of strings.
    # cmd - Element containing a <command> tag
    def makeStub(self, cmd):
        """Generate a stub function pointer <command> Element"""
        proto = cmd.find('proto')
        params = cmd.findall('param')
        name = cmd.find('name')

        # Begin accumulating prototype and typedef strings
        pfnDecl = 'static '
        pfnDecl += noneStr(proto.text)

        # Find the name tag and generate the function pointer and function pointer initialization code
        nameTag = proto.find('name')
        tail = noneStr(nameTag.tail)
        returnType = noneStr(proto.find('type').text)

        type = self.makeFunctionPointerType(nameTag.text, tail)

        # For each child element, if it's a <name> wrap in appropriate
        # declaration. Otherwise append its contents and tail con#tents.
        stubDecl = ''
        for elem in proto:
            text = noneStr(elem.text)
            tail = noneStr(elem.tail)
            if (elem.tag == 'name'):
                name = self.makeProtoName(text, tail)
                stubDecl += name
            else:
                stubDecl += text + tail

        pfnName = self.makeFunctionPointerName(nameTag.text, noneStr(tail));
        pfnDecl += type + ' ' + pfnName + ';'

        # Now generate the stub function
        pfnDecl += '\n'

        # Now add the parameter declaration list, which is identical
        # for prototypes and typedefs. Concatenate all the text from
        # a <param> node without the tags. No tree walking required
        # since all tags are ignored.
        n = len(params)
        paramdecl = '(\n'

        pfnCall = '\n{\n    ' + ('return ', '')[returnType == 'void'] + pfnName + '(\n'
        # Indented parameters
        if n > 0:
            indentCallParam = '(\n'
            indentdecl = '(\n'
            for i in range(0,n):
                callParam = ''

                paramdecl += self.makeCParamDecl(params[i], self.genOpts.alignFuncParam)
                pfnCall += self.makeCCallParam(params[i], self.genOpts.alignFuncParam)
                if (i < n - 1):
                    paramdecl += ',\n'
                    pfnCall += ',\n'
                else:
                    paramdecl += ')'
                    pfnCall += '\n    );\n'
                indentdecl += paramdecl
                indentCallParam += pfnCall
        else:
            indentdecl = '(void);'

        pfnCall += '}\n'

        featureInstance = '    '  + pfnName + ' = ('+type+')vkGetInstanceProcAddr(instance, "' + name + '");'
        featureDevice = '    '  + pfnName + ' = ('+type+')vkGetDeviceProcAddr(device, "' + name + '");'
        return [featureInstance, featureDevice , pfnDecl  + stubDecl + paramdecl + pfnCall]

    # Return function pointer type for given function
    def makeFunctionPointerType(self, name, tail):
       return 'PFN_' + name + tail

    # Return name of static variable which stores the function pointer for the given function
    def makeFunctionPointerName(self, name, tail):
       return 'pfn_' + name + tail

    #
    # makeCParamDecl - return a string which is an indented, formatted
    # declaration for a <param> or <member> block (e.g. function parameter
    # or structure/union member).
    # param - Element (<param> or <member>) to format
    # aligncol - if non-zero, attempt to align the nested <name> element
    #   at this column
    def makeCCallParam(self, param, aligncol):
        return '        ' + param.find('name').text

