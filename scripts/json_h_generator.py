#!/usr/bin/python3 -i
#
# Copyright 2020-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Description:
# -----------
# This script generates a .hpp file that can be included in an application
# to generate json data that can then be used to generate the pipeline cache.

import os
import re
import xml.dom.minidom
from generator import (GeneratorOptions, OutputGenerator, noneStr,
                       regSortFeatures, write)

copyright = """
/*
** Copyright 2020-2024 The Khronos Group Inc.
**
** SPDX-License-Identifier: Apache-2.0
*/
"""


predefinedCode = """
/********************************************************************************************/
/** This code is generated. To make changes, please modify the scripts or the relevant xml **/
/********************************************************************************************/

#pragma once

#include <stdio.h>
#include <vulkan/vulkan.h>

const char* getJSONOutput(void);
void resetJSONOutput(void);
"""

class JSONHeaderGeneratorOptions(GeneratorOptions):
    """JSONHeaderGeneratorOptions - subclass of GeneratorOptions.

    Adds options used by JSONHeaderOutputGenerator objects during C language header
    generation."""

    def __init__(self,
                 prefixText="",
                 genFuncPointers=True,
                 protectFile=True,
                 protectFeature=True,
                 protectProto=None,
                 protectProtoStr=None,
                 apicall='',
                 apientry='',
                 apientryp='',
                 indentFuncProto=True,
                 indentFuncPointer=False,
                 alignFuncParam=0,
                 genEnumBeginEndRange=False,
                 genAliasMacro=False,
                 aliasMacro='',
                 **kwargs
                 ):

        GeneratorOptions.__init__(self, **kwargs)


class JSONHeaderOutputGenerator(OutputGenerator):
    # This is an ordered list of sections in the header file.
    TYPE_SECTIONS = ['basetype', 'handle', 'enum',
                     'group', 'bitmask', 'struct']
    ALL_SECTIONS = TYPE_SECTIONS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Internal state - accumulators for different inner block text
        self.sections = {section: [] for section in self.ALL_SECTIONS}
        self.feature_not_empty = False
        self.may_alias         = None
        self.featureDict       = {}
        self.vkscFeatureList   = []
        self.baseTypeList      = ["int32_t",
                                  "uint32_t",
                                  "uint8_t",
                                  "uint64_t",
                                  "float",
                                  "int",
                                  "double",
                                  "int64_t",
                                  "uint16_t",
                                  "char"]


    def createvkscFeatureList(self):
        for feature in self.registry.reg.findall('feature'):
            if feature.get('api').find('vulkansc') != -1:
                # Remove entries that are removed in features in VKSC profile.
                requiredList = feature.findall("require")

                for requiredItem in requiredList:
                    typeList = requiredItem.findall("type")
                    for typeName in typeList:
                        if typeName.get("name") != "":
                            self.featureDict[typeName.get("name")] = feature.get("name")
                            self.vkscFeatureList.append(typeName.get("name"))

                removeItemList = feature.findall("remove")
                for removeItem in removeItemList:
                    removeTypes = removeItem.findall("type")
                    for item in removeTypes:
                        if self.vkscFeatureList.count(item.get("name")) > 0:
                            self.vkscFeatureList.remove(item.get("name"))

        allExtensions = self.registry.reg.findall('extensions')
        for extensions in allExtensions:
            extensionList = extensions.findall("extension")
            for extension in extensionList:
                if extension.get("supported").find("vulkansc") != -1:
                    requiredList = extension.findall("require")
                    for requiredItem in requiredList:
                        typeList = requiredItem.findall("type")
                        for typeName in typeList:
                            self.featureDict[typeName.get("name")] = extension.get("name")
                            self.vkscFeatureList.append(typeName.get("name"))

    def printPrototypes(self):
       code = ""

       code += "/*************************************** Begin prototypes ***********************************/\n"
       typesList = self.registry.reg.findall('types')
       currentExtension = "VK_VERSION_1_0"
       for types in typesList:
            typeList = types.findall("type")

            for type in typeList:
                if type.get("name") != "":
                    cat  = type.get("category")
                    name = type.get("name")

                    if cat in {"handle", "bitmask", "basetype", "enum", "struct"} and name in self.vkscFeatureList:
                        if name in self.featureDict and currentExtension != self.featureDict[name]:
                            if currentExtension != "VK_VERSION_1_0":
                                code += "#endif\n"
                            currentExtension = self.featureDict[name]
                            if self.featureDict[name] != "VK_VERSION_1_0":
                                code += "#ifdef %s\n" %(currentExtension)
                        code += "void print_%s(const %s* obj, const char* str, int commaNeeded);\n" %(name, name)

       if currentExtension != "VK_VERSION_1_0":
            code += "#endif\n"
       code += "/*************************************** End prototypes ***********************************/\n\n"

       return code

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        self.createvkscFeatureList()

        write(copyright, file=self.outFile)
        write(predefinedCode, file=self.outFile)

        write(self.printPrototypes(), file=self.outFile)
        write("void dumpPNextChain(const void* pNext);\n", file=self.outFile)

    def endFile(self):
        OutputGenerator.endFile(self)

    def beginFeature(self, interface, emit):
        OutputGenerator.beginFeature(self, interface, emit)
        self.sections = {section: [] for section in self.ALL_SECTIONS}
        self.feature_not_empty = False

    def endFeature(self):
        if self.emit:
            if self.feature_not_empty:
                if self.genOpts.conventions.writeFeature(self.featureName, self.featureExtraProtect, self.genOpts.filename):

                    for section in self.TYPE_SECTIONS:
                        contents = self.sections[section]
                        if contents:
                            write('\n'.join(contents), file=self.outFile)

        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    def genType(self, typeinfo, name, alias):
        OutputGenerator.genType(self, typeinfo, name, alias)

    def genStruct(self, typeinfo, typeName, alias):
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)

    def genGroup(self, groupinfo, groupName, alias=None):
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)

