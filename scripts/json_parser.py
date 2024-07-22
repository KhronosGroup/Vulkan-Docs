#!/usr/bin/env python3 -i
#
# Copyright 2020-2024 The Khronos Group Inc.
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
 * Copyright 2024 The Khronos Group Inc.
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
#include <cassert>
#include <limits>
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

        void* result = static_cast<uint8_t *>(m_vec.back()) + m_pointer;
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

static thread_local GlobalMem<uint32_t, uint8_t> s_globalMem(32768U);

// To make sure the generated data is consistent across platforms,
// we typecast to 32-bit.
static void parse_size_t(const Json::Value& obj, size_t& o)
{
    uint32_t _res = static_cast<uint32_t>(obj.asUInt());
    o = _res;
}

static void parse_char(const Json::Value& obj, char o[])
{
    const std::string& _res = obj.asString();
    memcpy((void*)o, _res.c_str(), static_cast<uint32_t>(_res.size()));
    o[_res.size()] = \'\\0\';
}
static void parse_char(const Json::Value& obj, const char* const*)
{
}
static void parse_char(const Json::Value& obj, const char** o)
{
    const std::string& _res = obj.asString();
    char *writePtr = (char *)s_globalMem.allocate(static_cast<uint32_t>(_res.size()) + 1);
    memcpy((void*)writePtr, _res.c_str(), _res.size());
    writePtr[_res.size()] = \'\\0\';
    *o = writePtr;
}

"""

base64DecodeCodeCTS = """
// base64 encoder taken from executor/xeTestResultParser.cpp

static
std::vector<uint8_t> base64decode(const std::string& encoded)
{
	int base64DecodeOffset = 0;
	std::vector<uint8_t> result;

	for (std::size_t inNdx = 0; inNdx < encoded.size(); inNdx++)
	{
		uint8_t	byte = encoded[inNdx];
		uint8_t	decodedBits = 0;

		if (de::inRange<uint8_t>(byte, 'A', 'Z'))
			decodedBits = (uint8_t)(byte - 'A');
		else if (de::inRange<uint8_t>(byte, 'a', 'z'))
			decodedBits = (uint8_t)(('Z' - 'A' + 1) + (byte - 'a'));
		else if (de::inRange<uint8_t>(byte, '0', '9'))
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
			DE_ASSERT(false);
		}

		base64DecodeOffset++;
	}
	return result;
}

static void parse_void_data(const Json::Value& obj, void* o, int oSize)
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
			parse_uint8_t(obj[i], const_cast<uint8_t&>(data[i]));
		}
	}
	memcpy(o, data.data(), oSize);
}

"""

base64DecodeCode = """
// base64 encoder taken from executor/xeTestResultParser.cpp

static
std::vector<uint8_t> base64decode(const std::string& encoded)
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

static void parse_void_data(const Json::Value& obj, void* o, int oSize)
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
			parse_uint8_t(obj[i], const_cast<uint8_t&>(data[i]));
		}
	}
	memcpy(o, data.data(), oSize);
}

"""

headerGuardTop = """#ifndef _VULKAN_JSON_PARSER_HPP
#define _VULKAN_JSON_PARSER_HPP
"""

headerGuardBottom = """#endif // _VULKAN_JSON_PARSER_HPP\n"""

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
                 versions='',
                 defaultExtensions='',
                 addExtensions='',
                 **kwargs
                 ):

        GeneratorOptions.__init__(self, **kwargs)
        self.isCTS = isCTS
        self.versions = versions
        self.defaultExtensions = defaultExtensions
        self.addExtensions = addExtensions


class JSONParserGenerator(OutputGenerator):
    # This is an ordered list of sections in the header file.
    TYPE_SECTIONS = ['basetype', 'handle', 'enum',
                     'group', 'bitmask', 'struct',
                     'pNext']
    ALL_SECTIONS = TYPE_SECTIONS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Internal state - accumulators for different inner block text
        self.sections = {section: [] for section in self.ALL_SECTIONS}
        self.feature_not_empty = False
        self.may_alias         = None
        self.pNextCases        = ""
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
                                  "uint16_t" : "obj.asUInt()"
                                  }
        self.nvSciTypeDict     = {
                                  "NvSciBufAttrList"  : "obj.asInt()",
                                  "NvSciBufObj"       : "obj.asInt()",
                                  "NvSciSyncAttrList" : "obj.asInt()",
                                  "NvSciSyncObj"      : "obj.asInt()"
                                  }

    def parseBaseTypes(self, dict):
        for baseType in dict:
            printStr = dict[baseType]
            if baseType == "uint8_t" or baseType == "uint16_t":
                write("static void parse_%s(const Json::Value& obj, %s& o)\n" %(baseType, baseType) +
                    "{\n"
                    "     o = static_cast<%s>(%s);\n" %(baseType,printStr)                                                                                   +
                    "}\n"
                    , file=self.outFile
                )
            elif baseType.startswith('NvSci'):
                write("static void parse_%s(const Json::Value& obj, %s& o)\n" %(baseType, self.nvSciTypeListMap[baseType]) +
                    "{\n"
                    "     o = static_cast<%s>(%s);\n" %(self.nvSciTypeListMap[baseType],printStr)                                                                                   +
                    "}\n"
                    , file=self.outFile
                )
            else:
                code = ""
                code += "static void parse_%s(const Json::Value& obj, %s& o)\n" %(baseType, baseType)
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

    def createConstDict(self):
        # This dictionary is used to convert string constants like 'VK_TRUE' and 'VK_WHOLE_SIZE' when reading integer base types
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

    def genStructExtensionCode(self):
       code  = "static void* parsePNextChain(const Json::Value& obj) {\n"
       code += "    VkBaseInStructure o;\n"
       code += "    const Json::Value& pNextObj = obj[\"pNext\"];\n"
       code += "    if (pNextObj.empty() || (pNextObj.isString() && pNextObj.asString() == \"NULL\")) return nullptr;\n\n"
       code += "    parse_VkStructureType(pNextObj[\"sType\"], (o.sType));\n"
       code += "    void* p = nullptr;\n"
       code += "    switch (o.sType) {\n"
       code += self.pNextCases
       code += "        default:\n"
       code += "            break;\n"
       code += "    }\n"
       code += "    return p;\n"
       code += "}\n"
       return code

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        self.isCTS = genOpts.isCTS
        self.versions = genOpts.versions
        self.defaultExtensions = genOpts.defaultExtensions
        self.addExtensions = genOpts.addExtensions
        self.createConstDict()

        self.nvSciTypeListMap = {
                                  "NvSciBufAttrList"  : "vk::pt::NvSciBufAttrList" if self.isCTS else "NvSciBufAttrList",
                                  "NvSciBufObj"       : "vk::pt::NvSciBufObj" if self.isCTS else "NvSciBufObj",
                                  "NvSciSyncAttrList" : "vk::pt::NvSciSyncAttrList" if self.isCTS else "NvSciSyncAttrList",
                                  "NvSciSyncObj"      : "vk::pt::NvSciSyncObj" if self.isCTS else "NvSciSyncObj"
                                }

        write(headerGuardTop, file=self.outFile, end='')
        write(copyright, file=self.outFile)
        write(predefinedCode, file=self.outFile)

        self.parseBaseTypes(self.baseTypeDict)
        nvSciExtensions = ('VK_NV_external_sci_sync', 'VK_NV_external_sci_sync2', 'VK_NV_external_memory_sci_buf')
        if any(item in self.addExtensions for item in nvSciExtensions) or (self.defaultExtensions == 'vulkansc'):
            self.parseBaseTypes(self.nvSciTypeDict)

        write("static void* parsePNextChain(const Json::Value& obj);\n", file=self.outFile)

        if self.isCTS:
            write(base64DecodeCodeCTS, file=self.outFile)
        else:
            write(base64DecodeCode, file=self.outFile)

    def endFile(self):
        write(self.genStructExtensionCode(), file=self.outFile)
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
                if self.genOpts.conventions.writeFeature(self.featureName, self.featureExtraProtect, self.genOpts.filename):
                    for section in self.TYPE_SECTIONS:
                        contents = self.sections[section]
                        if contents:
                            if section == 'pNext':
                                self.pNextCases += ''.join(contents)
                            else:
                                write('\n'.join(contents), file=self.outFile)

        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    def appendSection(self, section, text):
        self.sections[section].append(text)
        self.feature_not_empty = True

    def genEnumCode(self, name):
        code = ""
        code += "static void parse_%s(const Json::Value& obj, %s& o) {\n" %(name, name)
        code += "    const std::string& _res = obj.asString();\n"
        code += "    o = (%s)%s_map[std::string(_res)];\n" %(name, name)
        code += "}\n"

        return code

    def genBasetypeCode(self, str1, str2, name):
        code  = "static void parse_%s(const Json::Value& obj, %s& o) {\n" %(name, name)
        code += "    const std::string& _res = obj.asString();\n"
        if name == "VkBool32":
            code += "    //VkBool is represented as VK_TRUE and VK_FALSE in the json\n"
            code += "    o = (_res == \"VK_TRUE\") ? (1) : (0);\n"
        elif name == "VkDeviceAddress":
            code += "    sscanf(_res.c_str(), \"%\" SCNu64, &o);\n"
        elif name == "VkDeviceSize":
            code += "    if (_res == \"VK_WHOLE_SIZE\")\n"
            code += "        o = (~0ULL);\n"
            code += "    else\n"
            code += "        sscanf(_res.c_str(), \"%\" SCNu64, &o);\n"
        elif name == "VkFlags64":
            code += "    sscanf(_res.c_str(), \"%\" SCNd64, &o);\n"
        else:
            code += "    sscanf(_res.c_str(), \"%u\", &o);\n"
        code += "}\n"
        return code

    def genHandleCode(self, str1, str2, name):
        code  = "static void parse_%s(const Json::Value& obj, %s& o) {\n" %(name, name)
        code += "//    const std::string& _res = obj.asString();\n"
        code += "}\n"
        return code

    def genBitmaskCode(self, str1, str2, name, mapName, baseType):
        code = ""

        if mapName is not None:
            code += "static void parse_%s(const Json::Value& obj, %s& o) {\n" %(name, name)
            code += "    o = (%s)0;\n" %(name)
            code += "    const std::string& _res = obj.asString();\n"
            code += "    std::vector<std::string> bitmasks;\n"
            code += "    std::istringstream inputStream(_res);\n"
            code += "    std::string tempStr;\n"
            code += "    while (getline(inputStream, tempStr, '|')) {\n"
            code += "        tempStr.erase(std::remove_if(tempStr.begin(), tempStr.end(), isspace), tempStr.end());\n"
            code += "        bitmasks.push_back(tempStr);\n"
            code += "    }\n"
            code += "    for (auto& it : bitmasks) {\n"
            code += "        o |= (%s)%s_map[it];\n" %(mapName, mapName)
            code += "    }\n"
            code += "}\n"
        else:
            code += "static void parse_%s(const Json::Value& obj, %s& o) {\n" %(name, name)
            code += "    if (obj.isString()) {\n"
            code += "        const std::string& _res = obj.asString();\n"
            if baseType == "VkFlags64":
                code += "        sscanf(_res.c_str(), \"%\" SCNd64, &o);\n"
            else:
                code += "        sscanf(_res.c_str(), \"%u\", &o);\n"
            code += "    }\n"
            code += "    else {\n"
            code += "        o = obj.asUInt();\n"
            code += "    }\n"

            code += "}\n"
            
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
                baseType = ''
                typeName = ''
                for elem in typeElem:
                    if elem.tag == 'type':
                        baseType = elem.text
                    elif elem.tag == 'name':
                        typeName = elem.text
                if typeName != '':
                    body += self.genBitmaskCode("(", " obj,", typeName, typeElem.get('requires'), baseType)

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
            code += "    %s%s) = (%s*)s_globalMem.allocate(%s, sizeof(%s));\n" %(str2, memberName, typeName, length, typeName)
            code += "    const Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
            code += "    if (obj_%s.size() == 0) %s%s) = nullptr;\n" %(memberName, str2, memberName)
            code += "    else {\n"
            code += "        for (unsigned int i = 0; i < %s; i++) {\n" %(length)
            code += "            parse_%s(obj_%s[i], const_cast<%s&>(%s%s[i])));\n" %(typeName, memberName, typeName, str2, memberName)
            code += "        }\n"
            code += "    }\n"
            return code
        elif self.paramIsPointer(param) is True:
            code += "    {\n"
            code += "        const Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
            code += "        if (obj_%s.size() == 0) {\n" %(memberName)
            code += "            %s%s) = nullptr;\n"%(str2, memberName)
            code += "        } else {\n"
            code += "            %s%s) = (%s*)s_globalMem.allocate(1, sizeof(%s));\n" %(str2, memberName, typeName, typeName)
            code += "            parse_%s(obj_%s, const_cast<%s&>(*%s%s)));\n" %(typeName, memberName, typeName, str2, memberName)
            code += "        }\n"
            code += "    }\n"
            return code

        # TODO: With some tweak, we can use the genArrayCode() here.
        if isArr is True:
            code += "    const Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
            code += "    for (unsigned int i = 0; i < obj_%s.size(); i++) {\n" %(memberName)
            code += "        parse_%s(obj_%s[i], const_cast<%s&>(%s%s[i])));\n" %(typeName, memberName, typeName, str2, memberName)
            code += "    }\n"
        else:
            code += "    parse_%s(obj[\"%s\"], %s%s));\n" %(typeName, memberName, str2, memberName)

        return code

    def genArrayCode(self, structName, name, typeName, str2, arraySize, needStrPrint, isMallocNeeded):
        code = ""
        if structName == "VkPipelineLayoutCreateInfo" and self.isCTS:
            if isMallocNeeded:
                code += "    %s* %sTab = (%s*)s_globalMem.allocate(%s, sizeof(%s));\n" %(typeName, name, typeName, arraySize, typeName)
            code += "    const Json::Value& obj_%s_arr = obj[\"%s\"];\n" %(name, name)
            code += "    for (unsigned int i = 0; i < obj_%s_arr.size(); i++) {\n" %(name)
            code += "        uint64_t %sInternal = 0;\n" %(name)
            code += "        parse_uint64_t(obj_%s_arr[i], %sInternal);\n" %(name, name)
            code += "        %sTab[i] = %s(%sInternal);\n" %(name, typeName, name)
            code += "    }\n"
            code += "    %s%s = %sTab;\n" %(str2[1:], name, name)
        else:
            if isMallocNeeded:
                code += "    %s%s) = (%s*)s_globalMem.allocate(%s, sizeof(%s));\n" %(str2, name, typeName, arraySize, typeName)
            code += "    const Json::Value& obj_%s_arr = obj[\"%s\"];\n" %(name, name)
            code += "    for (unsigned int i = 0; i < obj_%s_arr.size(); i++) {\n" %(name)
            code += "        parse_%s(obj_%s_arr[i], const_cast<%s&>(%s%s[i])));\n" %(typeName, name, typeName, str2, name)
            code += "    }\n"

        return code

    # Prints out member name followed by empty string.
    def genEmptyCode(self, memberName, isCommaNeeded):
        code = ""
        return code

    def genCTSHandleCode(self, memberName, typeName):
        code = ""
        code += "    uint64_t %sInternal = 0;\n" %(memberName)
        code += "    parse_uint64_t(obj[\"%s\"], %sInternal);\n" %(memberName, memberName)
        code += "    o.%s = %s(%sInternal);\n" %(memberName, typeName, memberName)
        return code

    def genStructCode(self, param, str1, str2, str3, str4, structName, isCommaNeeded):
        code = ""
        memberName = ""
        typeName = ""

        for elem in param:
            if elem.text.find('PFN_') != -1:
                return "    /** Note: Ignoring function pointer (%s). **/\n" %(elem.text)

            if elem.text == 'pNext':
                return "    o.pNext = (%s*)parsePNextChain(obj);\n" %(structName)

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
                code += "    if (o.dataSize > 0U)\n"
                code += "    {\n"
                code += "        void* data = s_globalMem.allocate(uint32_t(%sdataSize));\n" %(str2[1:])
                code += "        parse_void_data(obj[\"%s\"], data, int(%sdataSize));\n" %(memberName, str2[1:])
                code += "        %s%s = data;\n" %(str2[1:], memberName)
                code += "    }\n"
                code += "    else\n"
                code += "        %s%s = NULL;\n" %(str2[1:], memberName)
                return code
            if self.isCTS:
                if structName == "VkPipelineCacheCreateInfo":
                    code += "    if (o.initialDataSize > 0U)\n"
                    code += "    {\n"
                    code += "        void* data = s_globalMem.allocate(uint32_t(%sinitialDataSize));\n" %(str2[1:])
                    code += "        parse_void_data(obj[\"%s\"], data, int(%sinitialDataSize));\n" %(memberName, str2[1:])
                    code += "        %s%s = data;\n" %(str2[1:], memberName)
                    code += "    }\n"
                    code += "    else\n"
                    code += "        %s%s = NULL;\n" %(str2[1:], memberName)
                return code
            return "    /** Note: Ignoring void* data. **/\n"

        # For pointers where we have the 'len' field, dump them as arrays.
        elif self.paramIsPointer(param) and param.get('len') is not None and param.get('len').find('null-terminated') == -1 and param.get('len').find('latexmath') == -1:
            # TODO: Check what the optional means here. In some cases, the pointer isn't populated, but the count gets set.
            if param.get('optional') != 'true':
                return self.genArrayCode(structName, memberName, typeName, str2, str2+param.get('len')+")", False, True)
            else:
                if structName == "VkDescriptorSetLayoutBinding" and self.isCTS:
                    code  = "    const Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
                    code += "    if (obj_%s.empty() || (obj_%s.isString() && obj_%s.asString() == \"NULL\"))\n" %(memberName, memberName, memberName)
                    code += "        o.%s = nullptr;\n" %(memberName)
                    code += "    else\n"
                    code += "    {\n"
                    code += "        %s* samplers = (%s*)s_globalMem.allocate((o.descriptorCount), sizeof(%s));\n" %(typeName, typeName, typeName)
                    code += "        for (unsigned int i = 0; i < obj_%s.size(); i++)\n" %(memberName)
                    code += "        {\n"
                    code += "            uint64_t sInternal = 0;\n"
                    code += "            parse_uint64_t(obj_%s[i], sInternal);\n" %(memberName)
                    code += "            samplers[i] = %s(sInternal);\n" %(typeName)
                    code += "        }\n"
                    code += "        o.%s = samplers;\n" %(memberName)
                    code += "    }"
                    return code
                return self.genEmptyCode(memberName, isCommaNeeded)

        # Special handling for VkPipelineMultisampleStateCreateInfo::pSampleMask
        elif typeName in "VkSampleMask":
            arraySize = "(uint32_t(o.rasterizationSamples + 31) / 32)"
            code += "    %s%s) = (%s*)s_globalMem.allocate(%s, sizeof(%s));\n" %(str2, memberName, typeName, arraySize, typeName)
            code += "    const Json::Value& obj_%s = obj[\"%s\"];\n" %(memberName, memberName)
            code += "    if (o.rasterizationSamples == 0 || obj_%s.size() == 0) {\n" %(memberName)
            code += "        %s%s) = nullptr;\n" %(str2, memberName)
            code += "    } else {\n"
            code += "        for (uint32_t i = 0; i < %s; i++) {\n" %(arraySize)
            code += "            parse_uint32_t(obj_%s[i], const_cast<%s&>(%s%s[i])));\n" %(memberName, typeName, str2, memberName)
            code += "        }\n"
            code += "    }\n"

        # If a struct member is just a handle.
        elif str(self.getTypeCategory(typeName)) == 'handle':
            if self.isCTS and (memberName == "module" or memberName == "layout" or memberName == "renderPass" or memberName == "conversion"):
                return self.genCTSHandleCode(memberName, typeName)
            return self.genEmptyCode(memberName, isCommaNeeded)

        elif typeName in "char":
            if self.paramIsCharStaticArrayWithMacroSize(param) == 0:
                code += "    %s%s) = (const char*)s_globalMem.allocate(255);\n" %(str2, memberName)
                code += "    parse_%s(obj[\"%s\"], &%s%s));\n" %(typeName, memberName, str2, memberName)
            else:
                code += "    /** TODO: Handle this - %s **/\n" %(memberName)

        elif typeName in "NvSciSyncFence":
            code += "    /** TODO: Handle this - %s **/\n" %(memberName)

        # Ignore other pointer data members
        elif self.paramIsPointer(param):
            code += "    /** Note: Ignoring %s* data from %s **/\n" %(typeName, memberName)
        
        else:
            code += "    parse_%s(obj[\"%s\"], %s%s));\n" %(typeName, memberName, str2, memberName)

        return code

    def genStruct(self, typeinfo, typeName, alias):
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)
        body = ""
        typeElem = typeinfo.elem

        if alias is None:
            genStr1 = ["("]
            genStr2 = ["(o."]
            genStr3 = [" o, const const char* s, bool commaNeeded) {"]
            genStr4 = ["    if (obj."]

            index = 0
            body += "static void parse_%s(const Json::Value& obj, %s& o) {\n\n" %(typeName, typeName)

            for member in typeElem.findall('.//member'):
                body += self.genStructCode(member, genStr1[index], genStr2[index], genStr3[index], genStr4[index], typeName, 0)
                body += "\n"

            body += "}\n"

            self.appendSection('struct', body)

            if typeElem.get('category') == 'struct' and typeElem.get('structextends') is not None:
                members = typeElem.findall('member')
                for m in members:
                    n = typeElem.get('name')
                    if m.get('values'):
                        pNext  = "        case %s:\n" %(m.get('values'))
                        pNext += "            p = s_globalMem.allocate(sizeof(%s));\n" %(n)
                        pNext += "            parse_%s(pNextObj, *((%s*)p));\n" %(n, n)
                        pNext += "            break;\n\n"
                        self.appendSection('pNext', pNext)

    def genGroup(self, groupinfo, groupName, alias=None):
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)
        groupElem = groupinfo.elem
        body = ""
        section = 'enum'
        if (groupElem.get('bitwidth')):
            bitwidth = int(groupElem.get('bitwidth'))
        else:
            bitwidth = 32
 
        if bitwidth == 64:
            body += "static std::map<std::string, uint64_t> %s_map = {\n" %(groupName)
        else:
            body += "static std::map<std::string, int> %s_map = {\n" %(groupName)
        enums = groupElem.findall('enum')

        for enum in enums:
            enumName = enum.get('name')
            enumValue = enum.get('value')
            enumBit = enum.get('bitpos')
            enumExtends = enum.get('extends')
            enumExtension = enum.get('extnumber')
            enumOffset = enum.get('offset')

            # Handle aliases by looking up their aliased type
            if enum.get('alias'):
                for allEnums in self.registry.reg.findall('enums'):
                    if allEnums.get("name") == groupName:
                        for baseEnum in allEnums.findall('enum'):
                            if (enum.get('alias') == baseEnum.get('name')):
                                enumBit = baseEnum.get('bitpos')
                                enumValue = baseEnum.get('value')
                                enumExtends = baseEnum.get('extends')
                                enumExtension = baseEnum.get('extnumber')
                                enumOffset = baseEnum.get('offset')

            if enumValue:
                body += "    std::make_pair(\"%s\", %s),\n" %(enumName, enumValue)

            elif enumBit:
                if bitwidth == 64:
                    body += "    std::make_pair(\"%s\", 1ULL << %s),\n" %(enumName, enumBit)
                else:
                    body += "    std::make_pair(\"%s\", 1UL << %s),\n" %(enumName, enumBit)

            elif enumExtends and enumExtension and enumOffset:
                extNumber = int(enumExtension)
                offset = int(enumOffset)
                enumVal = self.extBase + (extNumber - 1) * self.extBlockSize + offset
                body += "    std::make_pair(\"%s\", %s),\n" %(enumName, str(enumVal))

        body += "};\n"
        body += self.genEnumCode(groupName)

        self.appendSection(section, body)
