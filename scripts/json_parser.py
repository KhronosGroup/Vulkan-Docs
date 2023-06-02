#!/usr/bin/python3 -i
#
# Copyright 2020-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Description:
# -----------
# This script generates a .hpp file that creates VK structures from a
# json file.

import os
import re
import xml.dom.minidom
from generator import (GeneratorOptions, OutputGenerator, noneStr,
                       regSortFeatures, write)

copyright = """
/*
 * Copyright (c) 2021 The Khronos Group Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 *//*!
 * \\file
 * \\brief Defines JSON generators for Vulkan structures
 */
"""

predefinedCode = """
/********************************************************************************************/
/** This code is generated. To make changes, please modify the scripts or the relevant xml **/
/********************************************************************************************/

#pragma once
#include <iostream>
#include <map>
#include <cinttypes>
#include <algorithm>
#include <bitset>
#include <functional>
#include <sstream>
#include <cinttypes>
#include <json/json.h>

namespace vk_json_parser {

template <typename T1, typename T2>
class GlobalMem {
    static constexpr size_t MAX_ALIGNMENT = alignof(std::max_align_t);

    void grow(T1 size = 0) {
        //push_back new single vector of size m_tabSize onto vec
        void * p = calloc(size > m_tabSize ? size : m_tabSize, sizeof(T2));
        assert(p);
        m_vec.push_back(p);
        m_pointer = 0U;
    }
    void * alloc(T1 size) {
        // Align to the next multiple of MAX_ALIGNMENT.
        size = (size + static_cast<T1>(MAX_ALIGNMENT) - 1) & ~(static_cast<T1>(MAX_ALIGNMENT) - 1);

        void* result = static_cast<%s *>(m_vec.back()) + m_pointer;
        m_pointer += size;
        return result;
    }
public:

    GlobalMem(T1 tabSize_ = 32768U)
      : m_tabSize(tabSize_), m_pointer(0U)
    {
    }

    void* allocate (T1 size)
    {
        if (m_vec.empty() || m_pointer+size >= m_tabSize) {
            grow();
        }
        return alloc(size);
    }

    void* allocate (T1 count, T1 size)
    {
        T1 totalSize = count * size;
        if (m_vec.empty() || m_pointer+totalSize >= m_tabSize)
        {
            grow(totalSize);
        }
        return alloc(totalSize);
    }
    // deallocates all memory. Any use of earlier allocated elements is forbidden
    void clear()
    {
        // remove all vectors from vec excluding the one with index 0
        for (size_t i=1 ; i<m_vec.size(); i++) {
            free(m_vec[i]);
        }
        if (!m_vec.empty()) {
            m_vec.resize(1);
        }
        m_pointer = 0;
    }

    ~GlobalMem()
    {
        clear();
        if (!m_vec.empty()) {
            free(m_vec[0]);
        }
    }

private:
    std::vector< void * > m_vec;
    T1 m_tabSize;
    T1 m_pointer;
};

static thread_local GlobalMem<%s, %s> s_globalMem(32768U);

// To make sure the generated data is consistent across platforms,
// we typecast to 32-bit.
static void parse_size_t(const char* s, Json::Value& obj, size_t& o)
{
    %s _res = static_cast<%s>(obj.asUInt());
    o = _res;
}

static void parse_char(const char* s, Json::Value& obj, char o[])
{
    std::string _res = obj.asString();
    memcpy((void*)o, _res.c_str(), static_cast<%s>(_res.size()));
    o[_res.size()] = \'\\0\';
}
static void parse_char(const char* s, Json::Value& obj, const char* const*)
{
}
static void parse_char(const char* s, Json::Value& obj, const char** o)
{
    std::string _res = obj.asString();
    char *writePtr = (char *)s_globalMem.allocate(static_cast<%s>(_res.size()) + 1);
    memcpy((void*)writePtr, _res.c_str(), _res.size());
    writePtr[_res.size()] = \'\\0\';
    *o = writePtr;
}

"""

base64DecodeCodeCTS = """
// base64 encoder taken from executor/xeTestResultParser.cpp

static
std::vector<deUint8> base64decode(const std::string encoded)
{
	int base64DecodeOffset = 0;
	std::vector<deUint8> result;

	for (std::size_t inNdx = 0; inNdx < encoded.size(); inNdx++)
	{
		deUint8	byte = encoded[inNdx];
		deUint8	decodedBits = 0;

		if (de::inRange<deUint8>(byte, 'A', 'Z'))
			decodedBits = (deUint8)(byte - 'A');
		else if (de::inRange<deUint8>(byte, 'a', 'z'))
			decodedBits = (deUint8)(('Z' - 'A' + 1) + (byte - 'a'));
		else if (de::inRange<deUint8>(byte, '0', '9'))
			decodedBits = (deUint8)(('Z' - 'A' + 1) + ('z' - 'a' + 1) + (byte - '0'));
		else if (byte == '+')
			decodedBits = ('Z' - 'A' + 1) + ('z' - 'a' + 1) + ('9' - '0' + 1);
		else if (byte == '/')
			decodedBits = ('Z' - 'A' + 1) + ('z' - 'a' + 1) + ('9' - '0' + 2);
		else
			continue; // Not an B64 input character.

		int phase = base64DecodeOffset % 4;

		if (phase == 0)
			result.resize(result.size() + 3, 0);

		//		if ((int)image->data.size() < (base64DecodeOffset >> 2) * 3 + 3)
		//			throw TestResultParseError("Malformed base64 data");
		deUint8* outPtr = result.data() + (base64DecodeOffset >> 2) * 3;

		switch (phase)
		{
		case 0: outPtr[0] |= (deUint8)(decodedBits << 2);																								break;
		case 1: outPtr[0] = (deUint8)(outPtr[0] | (deUint8)(decodedBits >> 4));	outPtr[1] = (deUint8)(outPtr[1] | (deUint8)((decodedBits & 0xF) << 4));	break;
		case 2: outPtr[1] = (deUint8)(outPtr[1] | (deUint8)(decodedBits >> 2));	outPtr[2] = (deUint8)(outPtr[2] | (deUint8)((decodedBits & 0x3) << 6));	break;
		case 3: outPtr[2] |= decodedBits;																												break;
		default:
			DE_ASSERT(false);
		}

		base64DecodeOffset++;
	}
	return result;
}

static void parse_void_data(const void* s, Json::Value& obj, void* o, int oSize)
{
	std::vector<deUint8> data;
	if (obj.isString())
	{
		data = base64decode(obj.asString());
	}
	else
	{
		data.resize(oSize);
		for (int i = 0; i < std::min(oSize, (int)obj.size()); i++)
		{
			parse_uint8_t("pData", obj[i], const_cast<deUint8&>(data[i]));
		}
	}
	memcpy(o, data.data(), oSize);
}

"""

base64DecodeCode = """
// base64 encoder taken from executor/xeTestResultParser.cpp

static
std::vector<uint8_t> base64decode(const std::string encoded)
{
	int base64DecodeOffset = 0;
	std::vector<uint8_t> result;

	for (std::size_t inNdx = 0; inNdx < encoded.size(); inNdx++)
	{
		uint8_t	byte = encoded[inNdx];
		uint8_t	decodedBits = 0;

        if ('A' <= byte && byte <= 'Z')
			decodedBits = (uint8_t)(byte - 'A');
        else if ('a' <= byte && byte <= 'z')
			decodedBits = (uint8_t)(('Z' - 'A' + 1) + (byte - 'a'));
        else if ('0' <= byte && byte <= '9')
			decodedBits = (uint8_t)(('Z' - 'A' + 1) + ('z' - 'a' + 1) + (byte - '0'));
		else if (byte == '+')
			decodedBits = ('Z' - 'A' + 1) + ('z' - 'a' + 1) + ('9' - '0' + 1);
		else if (byte == '/')
			decodedBits = ('Z' - 'A' + 1) + ('z' - 'a' + 1) + ('9' - '0' + 2);
		else
			continue; // Not an B64 input character.

		int phase = base64DecodeOffset % 4;

		if (phase == 0)
			result.resize(result.size() + 3, 0);

		//		if ((int)image->data.size() < (base64DecodeOffset >> 2) * 3 + 3)
		//			throw TestResultParseError("Malformed base64 data");
		uint8_t* outPtr = result.data() + (base64DecodeOffset >> 2) * 3;

		switch (phase)
		{
		case 0: outPtr[0] |= (uint8_t)(decodedBits << 2);																								break;
		case 1: outPtr[0] = (uint8_t)(outPtr[0] | (uint8_t)(decodedBits >> 4));	outPtr[1] = (uint8_t)(outPtr[1] | (uint8_t)((decodedBits & 0xF) << 4));	break;
		case 2: outPtr[1] = (uint8_t)(outPtr[1] | (uint8_t)(decodedBits >> 2));	outPtr[2] = (uint8_t)(outPtr[2] | (uint8_t)((decodedBits & 0x3) << 6));	break;
		case 3: outPtr[2] |= decodedBits;																												break;
		default:
			assert(false);
		}

		base64DecodeOffset++;
	}
	return result;
}

static void parse_void_data(const void* s, Json::Value& obj, void* o, int oSize)
{
	std::vector<uint8_t> data;
	if (obj.isString())
	{
		data = base64decode(obj.asString());
	}
	else
	{
		data.resize(oSize);
		for (int i = 0; i < std::min(oSize, (int)obj.size()); i++)
		{
			parse_uint8_t("pData", obj[i], const_cast<uint8_t&>(data[i]));
		}
	}
	memcpy(o, data.data(), oSize);
}

"""

headerGuardTop = """#ifndef _VULKAN_JSON_PARSER_HPP
#define _VULKAN_JSON_PARSER_HPP
"""

headerGuardBottom = """#endif // _VULKAN_JSON_PARSER_HPP"""

class JSONParserOptions(GeneratorOptions):
    """JSONParserOptions - subclass of GeneratorOptions.

    Adds options used by JSONParserGenerator objects during C language header
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
                 isCTS = False,
                 indentFuncProto=True,
                 indentFuncPointer=False,
                 alignFuncParam=0,
                 genEnumBeginEndRange=False,
                 genAliasMacro=False,
                 aliasMacro='',
                 **kwargs
                 ):

        GeneratorOptions.__init__(self, **kwargs)
        self.isCTS = isCTS


class JSONParserGenerator(OutputGenerator):
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
        self.constDict         = {}
        self.baseTypeDict      = {
                                  "int32_t"  : "obj.asInt()",
                                  "uint32_t" : "obj.asUInt()",
                                  "uint8_t"  : "obj.asUInt()",
                                  "uint64_t" : "obj.asUInt64()",
                                  "float"    : "obj.asFloat()",
                                  "int"      : "obj.asInt()",
                                  "double"   : "obj.asDouble()",
                                  "int64_t"  : "obj.asInt64()",
                                  "uint16_t" : "obj.asUInt()",
                                  "NvSciBufAttrList"  : "obj.asInt()",
                                  "NvSciBufObj"       : "obj.asInt()",
                                  "NvSciSyncAttrList" : "obj.asInt()",
                                  "NvSciSyncObj"      : "obj.asInt()"
                                  }

    def parseBaseTypes(self):
        for baseType in self.baseTypeDict:
            printStr = self.baseTypeDict[baseType]
            if baseType == "uint8_t" or baseType == "uint16_t" or baseType.startswith('NvSci'):
                write("static void parse_%s(const char* s, Json::Value& obj, %s& o)\n" %(baseType, self.baseTypeListMap[baseType]) +
                    "{\n"
                    "     o = static_cast<%s>(%s);\n" %(self.baseTypeListMap[baseType],printStr)                                                                                   +
                    "}\n"
                    , file=self.outFile
                )
            else:
                code = ""
                code += "static void parse_%s(const char* s, Json::Value& obj, %s& o)\n" %(baseType, self.baseTypeListMap[baseType])
                code += "{\n"
                if baseType in self.constDict:
                    code += "     if (obj.isString())\n"
                    for index, enumValue in enumerate(self.constDict[baseType]):
                        code += "          %sif (obj.asString() == \"%s\")\n" %("else " if index > 0 else "", enumValue[0])
                        code += "               o = %s;\n" %(enumValue[1])
                    if baseType == "float":
                        code += "          else if (obj.asString() == \"NaN\")\n"
                        code += "               o = std::numeric_limits<float>::quiet_NaN();\n"
                    code += "          else\n"
                    code += "               assert(false);\n"
                    code += "     else\n"
                    code += "          o = %s;\n" %(printStr)
                else:
                    code += "     o = %s;\n" %(printStr)
                code += "}\n"
                write(code, file=self.outFile)

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

    def createConstDict(self):
        for enums in self.registry.reg.findall('enums'):
            if enums.get("name") == "API Constants":
                for enum in enums.findall('enum'):
                    type = enum.get("type");
                    if (type):
                        name = enum.get("name")
                        value = enum.get("value")
                        if type not in self.constDict:
                            self.constDict[type] = [(name, value)]
                        else:
                            self.constDict[type].append((name, value))

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
                            if not self.isCTS and currentExtension != "VK_VERSION_1_0":
                                code += "#endif\n"
                            currentExtension = self.featureDict[name]
                            if self.featureDict[name] != "VK_VERSION_1_0":
                                if not self.isCTS:
                                    code += "#ifdef %s\n" %(currentExtension)
                        code += "static void parse_%s(const char* s, Json::Value& obj, %s& o);\n" %(name, name)

       if currentExtension != "VK_VERSION_1_0":   
            if not self.isCTS:
                code += "#endif\n"
       code += "/*************************************** End prototypes ***********************************/\n\n"

       return code

    def genStructExtensionCode(self):
       code  = ""
       code += "static\n"
       code += "void* parsePNextChain(Json::Value& obj) {\n"
       code += "      VkBaseInStructure o;\n"
       code += "      Json::Value& pNextObj = obj[\"pNext\"];\n"
       code += "      if (pNextObj.empty() || (pNextObj.isString() && pNextObj.asString() == \"NULL\")) return nullptr;\n\n"
       code += "      parse_VkStructureType(\"sType\", pNextObj[\"sType\"], (o.sType));\n"
       code += "      void* p = nullptr;\n"
       code += "      switch (o.sType) {\n"

       typesList = self.registry.reg.findall('types')
       currentExtension = "VK_VERSION_1_0"
       for types in typesList:
           typeList = types.findall("type")
           for type in typeList:
               if type.get('category') == 'struct' and type.get('structextends') is not None and type.get('name') in self.vkscFeatureList:
                   members = type.findall('member')
                   for m in members:
                       n = type.get('name')
                       if m.get('values'):
                           if n in self.featureDict and currentExtension != self.featureDict[n]:
                               if not self.isCTS and currentExtension != "VK_VERSION_1_0":
                                   code += "#endif\n"
                               currentExtension = self.featureDict[n]
                               if self.featureDict[n] != "VK_VERSION_1_0":
                                    if not self.isCTS:
                                        code += "#ifdef %s\n" %(currentExtension)
                           code += "             case %s:\n" %(m.get('values'))
                           code += "             {\n"
                           code += "                p = s_globalMem.allocate(sizeof(%s));\n" %(n)
                           code += "                parse_%s(\"\", pNextObj, *((%s*)p));\n" %(n, n)
                           code += "             }\n"
                           #code += "print_%s(((%s *)pNext), \"%s\", 1);\n" %(n, n, n)
                           code += "             break;\n"

       if currentExtension != "VK_VERSION_1_0":
            if not self.isCTS:
                code += "#endif\n"
       code += "             default: {/** **/}\n"
       code += "     }\n"
       code += "     return p;\n"
       code += "  }\n"

       return code

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        self.createvkscFeatureList()
        self.createConstDict()

        self.isCTS = genOpts.isCTS

        self.baseTypeListMap  = {
                                  "int32_t"   : "deInt32" if self.isCTS else "int32_t",
                                  "uint32_t"  : "deUint32" if self.isCTS else "uint32_t",
                                  "uint8_t"   : "deUint8" if self.isCTS else "uint8_t",
                                  "uint64_t"  : "deUint64" if self.isCTS else "uint64_t",
                                  "float"     : "float",
                                  "int"       : "int",
                                  "double"    : "double",
                                  "int64_t"   : "deInt64" if self.isCTS else "int64_t",
                                  "uint16_t"  : "deUint16" if self.isCTS else "uint16_t",
                                  "NvSciBufAttrList"  : "vk::pt::NvSciBufAttrList" if self.isCTS else "NvSciBufAttrList",
                                  "NvSciBufObj"       : "vk::pt::NvSciBufObj" if self.isCTS else "NvSciBufObj",
                                  "NvSciSyncAttrList" : "vk::pt::NvSciSyncAttrList" if self.isCTS else "NvSciSyncAttrList",
                                  "NvSciSyncObj"      : "vk::pt::NvSciSyncObj" if self.isCTS else "NvSciSyncObj"
                                }

        write(headerGuardTop, file=self.outFile, end='')
        write(copyright, file=self.outFile)
        write(predefinedCode % (self.baseTypeListMap["uint8_t"],
                                self.baseTypeListMap["uint32_t"],
                                self.baseTypeListMap["uint8_t"],
                                self.baseTypeListMap["uint32_t"],
                                self.baseTypeListMap["uint32_t"],
                                self.baseTypeListMap["uint32_t"],
                                self.baseTypeListMap["uint32_t"]), file=self.outFile)

        self.parseBaseTypes()
        if self.isCTS:
            write(base64DecodeCodeCTS, file=self.outFile)
        else:
            write(base64DecodeCode, file=self.outFile)

        write(self.printPrototypes(), file=self.outFile)

        write(self.genStructExtensionCode(), file=self.outFile)

    def endFile(self):
        write("}//End of namespace vk_json_parser\n", file=self.outFile) # end of namespace
        write(headerGuardBottom, file=self.outFile, end='') # end of _VULKAN_JSON_PARSER_HPP
        OutputGenerator.endFile(self)

    def beginFeature(self, interface, emit):
        OutputGenerator.beginFeature(self, interface, emit)
        self.sections = {section: [] for section in self.ALL_SECTIONS}
        self.feature_not_empty = False

    def endFeature(self):
        if self.emit:
            if self.feature_not_empty:
                if self.genOpts.conventions.writeFeature(self.featureExtraProtect, self.genOpts.filename):

                    for section in self.TYPE_SECTIONS:
                        contents = self.sections[section]
                        if contents:
                            write('\n'.join(contents), file=self.outFile)

        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    def appendSection(self, section, text):
        self.sections[section].append(text)
        self.feature_not_empty = True

    def genEnumCode(self, name, endIfdef):
        code = ""
        code += "static void parse_%s(const char* s, Json::Value& obj, %s& o) {\n" %(name, name)
        code += "     std::string _res = obj.asString();\n"
        code += "     o = (%s)%s_map[std::string(_res)];\n" %(name, name)
        code += "}\n"
        if not self.isCTS and endIfdef:
            code += "#endif\n"

        return code

    def genBasetypeCode(self, str1, str2, name):
        code = ""
        code += "static void parse_%s(const char* s, Json::Value& obj, %s& o) {\n" %(name, name)
        code += "     std::string _res = obj.asString();\n"
        if name == "VkBool32":
            code += "     //VkBool is represented as VK_TRUE and VK_FALSE in the json\n"
            code += "     o = (_res == \"VK_TRUE\") ? (1) : (0);\n"
        elif name == "VkDeviceAddress":
            code += "     sscanf(_res.c_str(), \"%\" SCNu64, &o);\n"
        elif name == "VkDeviceSize":
            code += "     if (_res == \"VK_WHOLE_SIZE\")\n"
            code += "          o = (~0ULL);\n"
            code += "     else\n"
            code += "          sscanf(_res.c_str(), \"%\" SCNu64, &o);\n"
        elif name in ["VkFlags64", "VkPipelineStageFlags2KHR", "VkAccessFlags2KHR", "VkFormatFeatureFlags2KHR"]:
            code += "     sscanf(_res.c_str(), \"%\" SCNd64, &o);\n"
        else:
            code += "     sscanf(_res.c_str(), \"%u\", &o);\n"
        code += "}\n"
        return code

    def genHandleCode(self, str1, str2, name):
        code = ""
        ifdefName = ""
        if name in self.featureDict and self.featureDict[name] != "VK_VERSION_1_0":
            ifdefName = self.featureDict[name]
        if not self.isCTS and ifdefName != "":
            code += "#ifdef %s\n" %(ifdefName)
        code += "static void parse_%s(const char* s, Json::Value& obj, %s& o) {\n" %(name, name)
        code += "//     std::string _res = obj.asString();\n"
        code += "}\n"
        if not self.isCTS and ifdefName != "":
            code += "#endif\n"
        return code

    def genBitmaskCode(self, str1, str2, name, mapName):
        code = ""
        ifdefName = ""
        if mapName in self.featureDict and self.featureDict[mapName] != "VK_VERSION_1_0":
            ifdefName = self.featureDict[mapName]
        elif name in self.featureDict and self.featureDict[name] != "VK_VERSION_1_0":
            ifdefName = self.featureDict[name]
        if ifdefName != "":
            if not self.isCTS:
                code += "#ifdef %s\n" %(ifdefName)

        if mapName is not None:
            code += "static void parse_%s(const char* s, Json::Value& obj, %s& o) {\n" %(name, name)
            code += "     o = (%s)0;\n" %(name)
            code += "     std::string _res = obj.asString();\n"
            code += "     std::vector<std::string> bitmasks;\n"
            code += "     std::istringstream inputStream(_res);\n"
            code += "     std::string tempStr;\n"
            code += "     while (getline(inputStream, tempStr, '|')) {\n"
            code += "         tempStr.erase(std::remove_if(tempStr.begin(), tempStr.end(), isspace), tempStr.end());\n"
            code += "         bitmasks.push_back(tempStr);\n"
            code += "     }\n"
            code += "     for (auto& it : bitmasks) {\n"
            code += "       o |= (%s)%s_map[it];\n" %(mapName, mapName)
            code += "     }\n"
            code += "}\n"
        else:
            code += "static void parse_%s(const char* s, Json::Value& obj, %s& o) {\n" %(name, name)
            code += "     if (obj.isString()) {\n"
            code += "          std::string _res = obj.asString();\n"
            if name in ["VkFlags64", "VkPipelineStageFlags2KHR", "VkAccessFlags2KHR", "VkFormatFeatureFlags2KHR"]:
                code += "          sscanf(_res.c_str(), \"%\" SCNd64, &o);\n"
            else:
                code += "          sscanf(_res.c_str(), \"%u\", &o);\n"
            code += "     }\n"
            code += "     else {\n"
            code += "          o = obj.asUInt();\n"
            code += "     }\n"

            code += "}\n"
            
        if not self.isCTS and ifdefName != "":
            code += "#endif\n"

        return code

    def genType(self, typeinfo, name, alias):
        OutputGenerator.genType(self, typeinfo, name, alias)
        typeElem = typeinfo.elem
        body = ""

        category = typeElem.get('category')
        if category == 'funcpointer':
            section = 'struct'
        else:
            section = category

        if category in ('struct', 'union'):
            self.genStruct(typeinfo, name, alias)
        else:
            if typeElem.get('category') == 'bitmask':
                for elem in typeElem:
                    if elem.tag == 'name':
                        body += self.genBitmaskCode("(", " obj,", elem.text, typeElem.get('requires'))

            elif typeElem.get('category') == 'basetype':
                    for elem in typeElem:
                        if elem.tag == 'name':
                            body += self.genBasetypeCode("(", " obj,", elem.text)

            elif typeElem.get('category') == 'handle':
                    for elem in typeElem:
                        if elem.tag == 'name':
                            body += self.genHandleCode("(", " obj,", elem.text)

            if body:
                self.appendSection(section, body)

    def paramIsStruct(self, memberType):
        if str(self.getTypeCategory(memberType)) == 'struct':
            return 1
        return 0

    # Helper taken from the validation layers code.
    def paramIsPointer(self, param):
        ispointer = False
        for elem in param:
            if elem.tag == 'type' and elem.tail is not None and '*' in elem.tail:
                ispointer = True
        return ispointer

    # Helper taken from the validation layers code.
    def paramIsStaticArray(self, param):
        isstaticarray = 0
        paramname = param.find('name')
        if (paramname.tail is not None) and ('[' in paramname.tail) and (']' in paramname.tail):
            isstaticarray = paramname.tail.count('[')
            if isstaticarray:
                arraySize = paramname.tail[1]

        if isstaticarray:
            return arraySize
        else:
            return 0

    def paramIsStaticArrayWithMacroSize(self, param):
        paramname = param.find('name')
        isCharArray = param.find('type') is not None and 'char' in param.find('type').text
        hasMacroSize = paramname.tail is not None and '[' in paramname.tail and param.find('enum') is not None
        if hasMacroSize and not isCharArray:
            return 1
        else:
            return 0

    def paramIsCharStaticArrayWithMacroSize(self, param):
        paramname = param.find('name')
        if paramname.tail is None and paramname.text == "pName":
            return 0
        else:
            return 1

    def generateStructMembercode(self, param, str1, str2, str3, str4, memberName, typeName, isCommaNeeded):
        length = ""
        code = ""
        isArr = param.get('len') is not None

        if param.get('len') is not None:
            length = str2 + param.get('len') + ")"

        if self.paramIsPointer(param) is True and isArr is True:
            code += "     %s%s) = (%s*)s_globalMem.allocate(%s, sizeof(%s));\n" %(str2, memberName, typeName, length, typeName)
            code += "     Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
            code += "     if (obj_%s.size() == 0) %s%s) = nullptr;\n" %(memberName, str2, memberName)
            code += "     else {\n"
            code += "       for (unsigned int i = 0; i < %s; i++) {\n" %(length)
            code += "           parse_%s(\"%s\", obj_%s[i], const_cast<%s&>(%s%s[i])));\n" %(typeName, memberName, memberName, typeName, str2, memberName)
            code += "       }\n"
            code += "     }\n"
            return code
        elif self.paramIsPointer(param) is True:
            code += "     {\n"
            code += "         Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
            code += "         const int sz = obj_%s.size();\n" %(memberName)
            code += "         if (obj_%s.size() == 0) {\n" %(memberName)
            code += "             %s%s) = nullptr;\n"%(str2, memberName)
            code += "         } else {\n"
            code += "             %s%s) = (%s*)s_globalMem.allocate(1, sizeof(%s));\n" %(str2, memberName, typeName, typeName)
            code += "             parse_%s(\"%s\", obj_%s, const_cast<%s&>(*%s%s)));\n" %(typeName, memberName, memberName, typeName, str2, memberName)
            code += "         }\n"
            code += "     }\n"
            return code

        # TODO: With some tweak, we can use the genArrayCode() here.
        if isArr is True:
            code += "     Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
            code += "     for (unsigned int i = 0; i < obj_%s.size(); i++) {\n" %(memberName)
            code += "           parse_%s(\"%s\", obj_%s[i], const_cast<%s&>(%s%s[i])));\n" %(typeName, memberName, memberName, typeName, str2, memberName)
            code += "     }\n"
        else:
            code += "     parse_%s(\"%s\", obj[\"%s\"], %s%s));\n" %(typeName, memberName, memberName, str2, memberName)

        return code

    def genArrayCode(self, structName, name, typeName, str2, arraySize, needStrPrint, isMallocNeeded):
        code = ""
        mappedType = self.baseTypeListMap[typeName] if self.baseTypeListMap.get(typeName) != None else typeName
        if structName == "VkPipelineLayoutCreateInfo" and self.isCTS:
            if isMallocNeeded:
                code += "     %s* %sTab = (%s*)s_globalMem.allocate(%s, sizeof(%s));\n" %(mappedType, name, mappedType, arraySize, mappedType)
            code += "     Json::Value& obj_%s_arr = obj[\"%s\"];\n" %(name, name)
            code += "     for (unsigned int i = 0; i < obj_%s_arr.size(); i++) {\n" %(name)
            code += "           deUint64 %sInternal = 0;\n" %(name)
            code += "           parse_uint64_t(\"%s\", obj_%s_arr[i], %sInternal);\n" %(name, name, name)
            code += "           %sTab[i] = %s(%sInternal);\n" %(name, mappedType, name)
            code += "     }\n"
            code += "     %s%s = %sTab;\n" %(str2[1:], name, name)
        else:
            if isMallocNeeded:
                code += "     %s%s) = (%s*)s_globalMem.allocate(%s, sizeof(%s));\n" %(str2, name, mappedType, arraySize, mappedType)
            code += "     Json::Value& obj_%s_arr = obj[\"%s\"];\n" %(name, name)
            code += "     for (unsigned int i = 0; i < obj_%s_arr.size(); i++) {\n" %(name)
            code += "           parse_%s(\"%s\", obj_%s_arr[i], const_cast<%s&>(%s%s[i])));\n" %(typeName, name, name, mappedType, str2, name)
            code += "     }\n"

        return code

    # Prints out member name followed by empty string.
    def genEmptyCode(self, memberName, isCommaNeeded):
        code = ""
        return code

    def genCTSHandleCode(self, memberName, typeName):
        code = ""
        code += "     deUint64 %sInternal = 0;\n" %(memberName)
        code += "     parse_uint64_t(\"%s\", obj[\"%s\"], %sInternal);\n" %(memberName, memberName, memberName)
        code += "     o.%s = %s(%sInternal);\n" %(memberName, typeName, memberName)
        return code

    def genStructCode(self, param, str1, str2, str3, str4, structName, isCommaNeeded):
        code = ""
        memberName = ""
        typeName = ""

        for elem in param:
            if elem.text.find('PFN_') != -1:
                return "     /** Note: Ignoring function pointer (%s). **/\n" %(elem.text)

            if elem.text == 'pNext':
                return  "     o.pNext = (%s*)parsePNextChain(obj);\n" %(structName)

            if elem.tag == 'name':
                memberName = elem.text

            if elem.tag == 'type':
                typeName = elem.text

        if self.paramIsStaticArray(param):
            return self.genArrayCode(structName, memberName, typeName, str2, self.paramIsStaticArray(param), False, isCommaNeeded)

        elif self.paramIsStaticArrayWithMacroSize(param):
            arraySize = param.find('enum').text
            return self.genArrayCode(structName, memberName, typeName, str2, arraySize, False, isCommaNeeded)

        # If the struct's member is another struct, we need a different way to handle.
        elif self.paramIsStruct(typeName) == 1:
            code += self.generateStructMembercode(param, str1, str2, str3, str4, memberName, typeName, isCommaNeeded)

        # Ignore void* data members
        elif self.paramIsPointer(param) and typeName == 'void':
            code = ""
            if structName == "VkSpecializationInfo":
                code += "     if (o.dataSize > 0U)\n"
                code += "     {\n"
                code += "         void* data = s_globalMem.allocate(%s(%sdataSize));\n" %(self.baseTypeListMap["uint32_t"] ,str2[1:])
                code += "         parse_void_data(\"%s\", obj[\"%s\"], data, int(%sdataSize));\n" %(memberName, memberName, str2[1:])
                code += "         %s%s = data;\n" %(str2[1:], memberName)
                code += "     }\n"
                code += "     else\n"
                code += "         %s%s = NULL;\n" %(str2[1:], memberName)
                return code
            if self.isCTS:
                if structName == "VkPipelineCacheCreateInfo":
                    code += "     if (o.initialDataSize > 0U)\n"
                    code += "     {\n"
                    code += "         void* data = s_globalMem.allocate(%s(%sinitialDataSize));\n" %(self.baseTypeListMap["uint32_t"], str2[1:])
                    code += "         parse_void_data(\"%s\", obj[\"%s\"], data, int(%sinitialDataSize));\n" %(memberName, memberName, str2[1:])
                    code += "         %s%s = data;\n" %(str2[1:], memberName)
                    code += "     }\n"
                    code += "     else\n"
                    code += "         %s%s = NULL;\n" %(str2[1:], memberName)
                return code
            return "     /** Note: Ignoring void* data. **/\n"

        # For pointers where we have the 'len' field, dump them as arrays.
        elif self.paramIsPointer(param) and param.get('len') is not None and param.get('len').find('null-terminated') == -1 and param.get('len').find('latexmath') == -1:
            # TODO: Check what the optional means here. In some cases, the pointer isn't populated, but the count gets set.
            if param.get('optional') != 'true':
                return self.genArrayCode(structName, memberName, typeName, str2, str2+param.get('len')+")", False, True)
            else:
                if structName == "VkDescriptorSetLayoutBinding" and self.isCTS:
                    code = ""
                    code += "     Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
                    code += "     if (obj_%s.empty() || (obj_%s.isString() && obj_%s.asString() == \"NULL\"))\n" %(memberName, memberName, memberName)
                    code += "         o.%s = nullptr;\n" %(memberName)
                    code += "     else\n"
                    code += "     {\n"
                    code += "         %s* samplers = (%s*)s_globalMem.allocate((o.descriptorCount), sizeof(%s));\n" %(typeName, typeName, typeName)
                    code += "         for (unsigned int i = 0; i < obj_%s.size(); i++)\n" %(memberName)
                    code += "         {\n"
                    code += "             deUint64 sInternal = 0;\n"
                    code += "             parse_uint64_t(\"%s\", obj_%s[i], sInternal);\n" %(memberName, memberName)
                    code += "             samplers[i] = %s(sInternal);\n" %(typeName)
                    code += "         }\n"
                    code += "         o.%s = samplers;\n" %(memberName)
                    code += "     }"
                    return code
                return self.genEmptyCode(memberName, isCommaNeeded)

        # Special handling for VkPipelineMultisampleStateCreateInfo::pSampleMask
        elif typeName in "VkSampleMask":
            arraySize = "(%s(o.rasterizationSamples + 31) / 32)" %(self.baseTypeListMap["uint32_t"])
            code += "     %s%s) = (%s*)s_globalMem.allocate(%s, sizeof(%s));\n" %(str2, memberName, typeName, arraySize, typeName)
            code += "     Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
            code += "     if (o.rasterizationSamples == 0 || obj_%s.size() == 0) {\n" %(memberName)
            code += "         %s%s) = nullptr;\n" %(str2, memberName)
            code += "     } else {\n"
            code += "         for (%s i = 0; i < %s; i++) {\n" %(self.baseTypeListMap["uint32_t"], arraySize)
            code += "             parse_uint32_t(\"%s\", obj_%s[i], const_cast<%s&>(%s%s[i])));\n" %(memberName, memberName, typeName, str2, memberName)
            code += "         }\n"
            code += "     }\n"

        # If a struct member is just a handle.
        elif str(self.getTypeCategory(typeName)) == 'handle':
            if self.isCTS and (memberName == "module" or memberName == "layout" or memberName == "renderPass" or memberName == "conversion"):
                return self.genCTSHandleCode(memberName, typeName)
            return self.genEmptyCode(memberName, isCommaNeeded)

        elif typeName in "char":
            if self.paramIsCharStaticArrayWithMacroSize(param) == 0:
                code += "     %s%s) = (const char*)s_globalMem.allocate(255);\n" %(str2, memberName)
                code += "     parse_%s(\"%s\", obj[\"%s\"], &%s%s));\n" %(typeName, memberName, memberName, str2, memberName)
            else:
                code += "     /** TODO: Handle this - %s **/\n" %(memberName)

        elif typeName in "NvSciSyncFence":
            code += "     /** TODO: Handle this - %s **/\n" %(memberName)

        else:
            code += "     parse_%s(\"%s\", obj[\"%s\"], %s%s));\n" %(typeName, memberName, memberName, str2, memberName)

        return code

    def genStruct(self, typeinfo, typeName, alias):
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)
        body = ""
        typeElem = typeinfo.elem
        ifdefNeeded = False

        if typeName in self.featureDict and self.featureDict[typeName] != "VK_VERSION_1_0":
            ifdefNeeded = True
            if not self.isCTS:
                body = "#ifdef %s\n" %(self.featureDict[typeName])

        if alias:
            body += 'typedef ' + alias + ' ' + typeName + ';\n'
        else:
            genStr1 = ["("]
            genStr2 = ["(o."]
            genStr3 = [" o, const const char* s, bool commaNeeded) {"]
            genStr4 = ["     if (obj."]

            index = 0
            body += "static void parse_%s(const char* s, Json::Value& obj, %s& o) {\n" %(typeName, typeName)
            body += "\n"

            for member in typeElem.findall('.//member'):
                body += self.genStructCode(member, genStr1[index], genStr2[index], genStr3[index], genStr4[index], typeName, 0)
                body += "\n"

            body += "}\n"

        if not self.isCTS and ifdefNeeded:
            body += "#endif\n"

        self.appendSection('struct', body)

    def genGroup(self, groupinfo, groupName, alias=None):
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)
        groupElem = groupinfo.elem
        body = ""
        section = 'enum'
        ifdefNeeded = False
 
        if groupName in self.featureDict and self.featureDict[groupName] != "VK_VERSION_1_0":
            ifdefNeeded = True
            if not self.isCTS:
                body += "#ifdef %s\n" %(self.featureDict[groupName])

        if groupName == "VkPipelineStageFlagBits2KHR" or groupName == "VkAccessFlagBits2KHR" or groupName == "VkFormatFeatureFlagBits2KHR":
            body += "static std::map<std::string, %s> %s_map = {\n" %(self.baseTypeListMap["uint64_t"],groupName)
        else:
            body += "static std::map<std::string, int> %s_map = {\n" %(groupName)
        enums = groupElem.findall('enum')

        for enum in enums:
            if enum.get('value'):
                body += "    std::make_pair(\"%s\", %s),\n" %(enum.get('name'), enum.get('value'))

            elif enum.get('bitpos'):
                if groupName == "VkPipelineStageFlagBits2KHR" or groupName == "VkAccessFlagBits2KHR" or groupName == "VkFormatFeatureFlagBits2KHR":
                    body += "    std::make_pair(\"%s\", 1ULL << %s),\n" %(enum.get('name'), enum.get('bitpos'))
                else:
                    body += "    std::make_pair(\"%s\", 1UL << %s),\n" %(enum.get('name'), enum.get('bitpos'))

            elif enum.get('extends') and enum.get("extnumber") and enum.get("offset"):
                extNumber = int(enum.get("extnumber"))
                offset = int(enum.get("offset"))
                enumVal = self.extBase + (extNumber - 1) * self.extBlockSize + offset
                body += "    std::make_pair(\"%s\", %s),\n" %(enum.get('name'), str(enumVal))

        body += "};\n"
        body += self.genEnumCode(groupName, ifdefNeeded)

        self.appendSection(section, body)
