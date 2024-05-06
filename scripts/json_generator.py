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
from generator import (GeneratorOptions, OutputGenerator, noneStr,
                       regSortFeatures, write)

copyright = """
/*
 * Copyright 2021-2024 The Khronos Group Inc.
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

#include <iostream>
#include <map>
#include <bitset>
#include <functional>
#include <sstream>
#include <cassert>
#include <cmath>
#ifndef VULKAN_JSON_CTS
    #include <vulkan/vulkan.h>
#endif

#ifdef _WIN32
	#ifndef WIN32_LEAN_AND_MEAN
	#define WIN32_LEAN_AND_MEAN
	#endif
	#define VC_EXTRALEAN
	#define NOMINMAX
	#include <windows.h>
#endif

namespace vk_json {

static thread_local int s_num_spaces    = 0;
static thread_local std::stringstream _string_stream;

static void dumpPNextChain(const void* pNext);

// By default, redirect to std::cout. Can stream it to a stringstream if needed.
//#define   _OUT std::cout
#define _OUT _string_stream

// Helper utility to do indentation in the generated json file.
#define PRINT_SPACE for (int k = 0; k < s_num_spaces; k++) _OUT << \" \";

#define INDENT(sz) s_num_spaces += (sz);

#define PRINT_VAL(c) PRINT_SPACE \\
    if (s != "") {\\
        _OUT << \"\\\"\" << s << \"\\\"\" << \" : \" << o << (c ? \",\" : \"\") << std::endl; \\
    } else {\\
        _OUT << o << (c ? \",\" : \"\") << std::endl; \\
    }

#define PRINT_STR(c) PRINT_SPACE \\
    if (s != "") {\\
        _OUT << \"\\\"\" << s << \"\\\"\" << \" : " << \"\\\"\" << o << \"\\\"\" << (c ? \",\" : \"\") << std::endl; \\
    } else {\\
        _OUT << \"\\\"\" << o << \"\\\"\" << (c ? \",\" : \"\") << std::endl; \\
    }

// To make sure the generated data is consistent across platforms,
// we typecast to 32-bit and dump the data.
// The value is not expected to exceed the range.
static void print_size_t(const size_t* o, const std::string& s, bool commaNeeded=true)
{
    PRINT_SPACE
    _OUT << \"\\\"\" << s << \"\\\"\" << \" : \" << static_cast<%s>(*o) << (commaNeeded ? \",\" : \"\") << std::endl;\\
}
static void print_size_t(size_t o, const std::string& s, bool commaNeeded=true)
{
    PRINT_SPACE
    _OUT << \"\\\"\" << s << \"\\\"\" << \" : \" << static_cast<%s>(o) << (commaNeeded ? \",\" : \"\") << std::endl;\\
}
"""

headerGuardTop = """#ifndef _VULKAN_JSON_DATA_HPP
#define _VULKAN_JSON_DATA_HPP
"""

headerGuardBottom = """#endif // _VULKAN_JSON_DATA_HPP"""

encodeBase64CodeCTS = """
// Base 64 formatter class from executor/xeTestLogWriter.cpp

class Base64Formatter
{
public:
	const deUint8*	data;
	int				numBytes;

	Base64Formatter(const deUint8* data_, int numBytes_) : data(data_), numBytes(numBytes_) {}
};

std::ostream& operator<< (std::ostream& str, const Base64Formatter& fmt)
{
	static const char s_base64Table[64] =
	{
		'A','B','C','D','E','F','G','H','I','J','K','L','M',
		'N','O','P','Q','R','S','T','U','V','W','X','Y','Z',
		'a','b','c','d','e','f','g','h','i','j','k','l','m',
		'n','o','p','q','r','s','t','u','v','w','x','y','z',
		'0','1','2','3','4','5','6','7','8','9','+','/'
	};

	const deUint8*	data = fmt.data;
	int				numBytes = fmt.numBytes;
	int				srcNdx = 0;

	DE_ASSERT(data && (numBytes > 0));

	/* Loop all input chars. */
	while (srcNdx < numBytes)
	{
		int		numRead = de::min(3, numBytes - srcNdx);
		deUint8	s0 = data[srcNdx];
		deUint8	s1 = (numRead >= 2) ? data[srcNdx + 1] : 0;
		deUint8	s2 = (numRead >= 3) ? data[srcNdx + 2] : 0;
		char	d[4];

		srcNdx += numRead;

		d[0] = s_base64Table[s0 >> 2];
		d[1] = s_base64Table[((s0 & 0x3) << 4) | (s1 >> 4)];
		d[2] = s_base64Table[((s1 & 0xF) << 2) | (s2 >> 6)];
		d[3] = s_base64Table[s2 & 0x3F];

		if (numRead < 3) d[3] = '=';
		if (numRead < 2) d[2] = '=';

		/* Write data. */
		str.write(&d[0], sizeof(d));
	}

	return str;
}

inline Base64Formatter toBase64(const deUint8* bytes, int numBytes) {return Base64Formatter(bytes, numBytes); }

static void print_void_data(const void * o, int oSize, const std::string& s, bool commaNeeded=true)
{
	if (o != NULL && oSize != 0)
	{
		PRINT_SPACE _OUT << "\\\"" << s << "\\\"" << " : " << "\\\"" << toBase64((deUint8*)o, oSize) << "\\\"" << (commaNeeded ? "," : "") << std::endl;
	}
	else
	{
		PRINT_SPACE _OUT << "\\\"" << s << "\\\"" << " : " << "\\\"NULL\\\"" << (commaNeeded ? "," : "") << std::endl;
	}
}
"""
encodeBase64Code = """
// Base 64 formatter class from executor/xeTestLogWriter.cpp

class Base64Formatter
{
public:
	const uint8_t*	data;
	int				numBytes;

	Base64Formatter(const uint8_t* data_, int numBytes_) : data(data_), numBytes(numBytes_) {}
};

std::ostream& operator<< (std::ostream& str, const Base64Formatter& fmt)
{
	static const char s_base64Table[64] =
	{
		'A','B','C','D','E','F','G','H','I','J','K','L','M',
		'N','O','P','Q','R','S','T','U','V','W','X','Y','Z',
		'a','b','c','d','e','f','g','h','i','j','k','l','m',
		'n','o','p','q','r','s','t','u','v','w','x','y','z',
		'0','1','2','3','4','5','6','7','8','9','+','/'
	};

	const uint8_t*	data = fmt.data;
	int				numBytes = fmt.numBytes;
	int				srcNdx = 0;

	assert(data && (numBytes > 0));

	/* Loop all input chars. */
	while (srcNdx < numBytes)
	{
        #undef min
		int		numRead = std::min(3, numBytes - srcNdx);
		uint8_t	s0 = data[srcNdx];
		uint8_t	s1 = (numRead >= 2) ? data[srcNdx + 1] : 0;
		uint8_t	s2 = (numRead >= 3) ? data[srcNdx + 2] : 0;
		char	d[4];

		srcNdx += numRead;

		d[0] = s_base64Table[s0 >> 2];
		d[1] = s_base64Table[((s0 & 0x3) << 4) | (s1 >> 4)];
		d[2] = s_base64Table[((s1 & 0xF) << 2) | (s2 >> 6)];
		d[3] = s_base64Table[s2 & 0x3F];

		if (numRead < 3) d[3] = '=';
		if (numRead < 2) d[2] = '=';

		/* Write data. */
		str.write(&d[0], sizeof(d));
	}

	return str;
}

inline Base64Formatter toBase64(const uint8_t* bytes, int numBytes) {return Base64Formatter(bytes, numBytes); }

static void print_void_data(const void * o, int oSize, const std::string& s, bool commaNeeded=true)
{
	if (o != NULL && oSize != 0)
	{
		PRINT_SPACE _OUT << "\\\"" << s << "\\\"" << " : " << "\\\"" << toBase64((uint8_t*)o, oSize) << "\\\"" << (commaNeeded ? "," : "") << std::endl;
	}
	else
	{
		PRINT_SPACE _OUT << "\\\"" << s << "\\\"" << " : " << "\\\"NULL\\\"" << (commaNeeded ? "," : "") << std::endl;
	}
}
"""

class JSONGeneratorOptions(GeneratorOptions):
    """JSONGeneratorOptions - subclass of GeneratorOptions.

    Adds options used by JSONOutputGenerator objects during C language header
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
                 vulkanLayer=False,
                 **kwargs
                 ):

        GeneratorOptions.__init__(self, **kwargs)
        self.isCTS = isCTS

        self.vulkanLayer = vulkanLayer

class JSONOutputGenerator(OutputGenerator):
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
        self.vkscFeatureList   = []
        self.vkFeatureLayerList = []

        # Fills in some extensions for exclusion while generating code for layer.
        self.vkLayerNotReqList = set([""])

        self.platformList      = ["xlib",
                                  "xlib_xrandr",
                                  "xcb",
                                  "wayland",
                                  "directfb",
                                  "android",
                                  "win32",
                                  "vi",
                                  "ios",
                                  "macos",
                                  "metal",
                                  "fuchsia",
                                  "ggp",
                                  "QNX",
                                  "provisional"]
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

    def printBaseTypes(self):
        for baseType in self.baseTypeList:
            printStr = "    PRINT_VAL(commaNeeded)\n"

            # Some special handling needed here.
            if baseType == 'char':
                write("static void print_%s(const %s * const* o, const std::string& s, bool commaNeeded=true)\n" %(baseType, self.baseTypeListMap[baseType]) +
                  "{\n"                                                                                                           						+
                  "    PRINT_STR(commaNeeded)\n"                                                                                  						+
                  "}\n"
                  , file=self.outFile
                 )

            if self.isCTS and baseType == "float":
                printStr = "	if (std::isnan(o))\n"
                printStr +="	{\n"
                printStr +="		PRINT_SPACE\n"
                printStr +="		if (s != \"\")\n"
                printStr +="			_OUT << \"\\\"\" << s << \"\\\"\" << \" : \\\"NaN\\\"\" << (commaNeeded ? \",\" : \"\") << std::endl;\n"
                printStr +="		else\n"
                printStr +="			_OUT << \"\\\"NaN\\\"\" << (commaNeeded ? \",\" : \"\") << std::endl;\n"
                printStr +="	}\n"
                printStr +="	else\n"
                printStr +="	{\n"
                printStr +="		PRINT_VAL(commaNeeded)\n"
                printStr +="	}\n"

            write("static void print_%s(%s o, const std::string& s, bool commaNeeded=true)\n" %(baseType, self.baseTypeListMap[baseType]) +
                  "{\n"                                                                                        						 +
                  printStr                                                                                     						 +
                  "}\n"
                  , file=self.outFile
                  )

            if baseType == 'char':
                printStr = "    PRINT_STR(commaNeeded)\n"

            if self.isCTS and baseType == "float":
                printStr = "	if (std::isnan(*o))\n"
                printStr +="	{\n"
                printStr +="		PRINT_SPACE\n"
                printStr +="		if (s != \"\")\n"
                printStr +="			_OUT << \"\\\"\" << s << \"\\\"\" << \" : \\\"NaN\\\"\" << (commaNeeded ? \",\" : \"\") << std::endl;\n"
                printStr +="		else\n"
                printStr +="			_OUT << \"\\\"NaN\\\"\" << (commaNeeded ? \",\" : \"\") << std::endl;\n"
                printStr +="	}\n"
                printStr +="	else\n"
                printStr +="	{\n"
                printStr +="		PRINT_VAL(commaNeeded)\n"
                printStr +="	}\n"

            write("static void print_%s(const %s * o, const std::string& s, bool commaNeeded=true)\n" %(baseType, self.baseTypeListMap[baseType]) +
                  "{\n"                                                                                                						 +
                  printStr                                                                                             						 +
                  "}\n"
                  , file=self.outFile
                 )

    def createLayerUnusedList(self):
        allExtensions = self.registry.reg.findall('extensions')
        for extensions in allExtensions:
            extensionList = extensions.findall("extension")
            for extension in extensionList:
                for platform in self.platformList:
                    if re.search(platform, extension.get("name"), re.IGNORECASE):
                        requiredList = extension.findall("require")
                        for requiredItem in requiredList:
                            typeList = requiredItem.findall("type")
                            for typeName in typeList:
                                if platform == "vi":
                                    if re.search("NN", extension.get("name")):
                                        self.vkLayerNotReqList.add(typeName.get("name"))
                                else:
                                    self.vkLayerNotReqList.add(typeName.get("name"))
                        break

        typesList = self.registry.reg.findall('types')
        for types in typesList:
            typeList = types.findall("type")
            for type in typeList:
                if type.get("name") != "":
                    cat  = type.get("category")
                    name = type.get("name")
                    if cat in {"handle", "bitmask", "basetype", "enum", "struct"}:
                        for platform in self.platformList:
                            if re.search(platform, name, re.IGNORECASE):
                                if platform == "vi":
                                    if re.search("NN", name):
                                        self.vkLayerNotReqList.add(name)
                                else:
                                    self.vkLayerNotReqList.add(name)
                                break


    def createvkscFeatureList(self):
        for feature in self.registry.reg.findall('feature'):
            if feature.get('api').find('vulkansc') != -1:
                # Remove entries that are removed in features in VKSC profile.
                requiredList = feature.findall("require")

                for requiredItem in requiredList:
                    typeList = requiredItem.findall("type")
                    for typeName in typeList:
                        if typeName.get("name") != "":
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
                            self.vkscFeatureList.append(typeName.get("name"))

    def printPrototypesAndExtensionDump(self):
        code = ""

        code += "/*************************************** Begin prototypes ***********************************/\n"
        if self.vulkanLayer:
            typesList = self.registry.reg.findall('types')
            for types in typesList:
                typeList = types.findall("type")
                for type in typeList:
                    if type.get("name") != "":
                        cat  = type.get("category")
                        name = type.get("name")

            enumList = self.registry.reg.findall('enums')
            for enums in enumList:
                name = enums.get("name")
        else:
            typesList = self.registry.reg.findall('types')
            for types in typesList:
                typeList = types.findall("type")
                for type in typeList:
                    if type.get("name") != "":
                        cat  = type.get("category")
                        name = type.get("name")

        code += "/*************************************** End prototypes ***********************************/\n\n"
        code += "static void dumpPNextChain(const void* pNext) {\n"
        code += "      VkBaseInStructure *pBase = (VkBaseInStructure*)pNext;\n"
        code += "      if (pNext) {\n"
        code += "           PRINT_SPACE\n"
        code += "           _OUT << \"\\\"pNext\\\":\"<< std::endl;\n\n"
        code += "          switch (pBase->sType) {\n"

        for type in typeList:
            if type.get('category') == 'struct' and type.get('structextends') is not None:
                if (self.vulkanLayer and (type.get('name') not in self.vkLayerNotReqList)) or (not self.vulkanLayer):
                    members = type.findall('member')
                    for m in members:
                            n = type.get('name')
                            if m.get('values') and (n in self.vkFeatureLayerList):
                                code += "             case %s:" %(m.get('values'))
                                code += "print_%s((%s *) pNext, \"%s\", true);\n" %(n, n, n)
                                code += "             break;\n"

        code += "             default: assert(false); // No structure type matching\n"
        code += "         }\n"
        code += "     }\n"
        code += "  }\n"

        return code


    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        self.vulkanLayer = genOpts.vulkanLayer
        if self.vulkanLayer:
            self.createLayerUnusedList()

        self.createvkscFeatureList()

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
                                  "char"      : "char"
                                }

        write(headerGuardTop, file=self.outFile, end='')
        write(copyright, file=self.outFile)
        if self.isCTS:
            write(predefinedCode % ("deUint32", "deUint32"), file=self.outFile)
        else:
            write(predefinedCode % ("uint32_t", "uint32_t"), file=self.outFile)
        self.printBaseTypes()
        if self.isCTS:
            write(encodeBase64CodeCTS, file=self.outFile)
        else:
            write(encodeBase64Code, file=self.outFile)

    def endFile(self):
        write(self.printPrototypesAndExtensionDump(), file=self.outFile)
        write("}//End of namespace vk_json\n", file=self.outFile) # end of namespace
        write(headerGuardBottom, file=self.outFile, end='') # end of _VULKAN_JSON_DATA_HPP
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

    def appendSection(self, section, text):
        self.sections[section].append(text)
        self.feature_not_empty = True

    def genEnumData(self, name, obj):
        code = ""
        code += "     if (str != \"\") _OUT << \"\\\"\" << str << \"\\\"\" << \" : \";\n"
        code += "     if (commaNeeded)\n"
        code += "         _OUT << \"\\\"\" <<  %s_map[%sobj] << \"\\\",\" << std::endl;\n" %(name, obj)
        code += "     else\n"
        code += "         _OUT << \"\\\"\" << %s_map[%sobj] << \"\\\"\" << std::endl;\n" %(name, obj)
        return code

    def genEnumCode(self, name):
        code = ""
        code += "static void print_%s(%s obj, const std::string& str, bool commaNeeded=true) {\n" %(name, name)
        code += "     PRINT_SPACE\n"
        code += self.genEnumData(name, "")
        code += "}\n"

        code += "static void print_%s(const %s * obj, const std::string& str, bool commaNeeded=true) {\n" %(name, name)
        code += "     PRINT_SPACE\n"
        code += self.genEnumData(name, "*")
        code += "}\n"

        return code

    def genBasetypeCode(self, str1, str2, name):
        code = ""
        code += "static void print_" + name + "(" + str1 + name + str2 + " const std::string& str, bool commaNeeded=true) {\n"
        code += "     PRINT_SPACE\n"
        if name == "VkBool32":
            code += "     _OUT << \"\\\"\" << str << \"\\\"\" << \" : \" << \"\\\"\" << ((obj == 0) ? (\"VK_FALSE\") : (\"VK_TRUE\")) << \"\\\"\" << (commaNeeded ? \",\" : \"\") << std::endl;\n"
        else:
            code += "     _OUT << \"\\\"\" << str << \"\\\"\" << \" : \" << \"\\\"\" << obj << \"\\\"\" << (commaNeeded ? \",\" : \"\") << std::endl;\n"
        code += "}\n"
        return code

    def genHandleCode(self, str1, str2, name):
        code = ""
        code += "static void print_%s(%s%s%s const std::string& str, bool commaNeeded=true) {\n" %(name, str1, name, str2)
        code += "     PRINT_SPACE\n"
        code += "     if (commaNeeded)\n"
        code += "         _OUT << \"\\\"\" << str << \"\\\"\" << \",\" << std::endl;\n"
        code += "     else\n"
        code += "         _OUT << \"\\\"\" << str << \"\\\"\" << std::endl;\n"
        code += "}\n"
        return code

    def genBitmaskCode(self, str1, str2, name, mapName):
        if mapName is not None:
            code = ""
            code += "static void print_%s(%s%s%s const std::string& str, bool commaNeeded=true) {\n" %(name, str1, name, str2)
            code += "     PRINT_SPACE\n"
            code += "     if (str != \"\") _OUT << \"\\\"\" << str << \"\\\"\" << \" : \";\n"
            code += "     const int max_bits = 64; // We don't expect the number to be larger.\n"
            code += "     std::bitset<max_bits> b(obj);\n"
            code += "     _OUT << " + "\"\\\"\"" + ";\n"
            code += "     if (obj == 0) _OUT << \"0\";\n"
            code += "     for (unsigned int i = 0, bitCount = 0; i < b.size(); i++) {\n"
            code += "         if (b[i] == 1) {\n"
            code += "             bitCount++;\n"
            code += "             if (bitCount < b.count())\n"
            code += "                 _OUT << %s_map[1ULL<<i] << \" | \";\n" %(mapName)
            code += "             else\n"
            code += "                 _OUT << %s_map[1ULL<<i];\n" %(mapName)
            code += "         }\n"
            code += "     }\n"
            code += "     if (commaNeeded)\n"
            code += "       _OUT << \"\\\"\" << \",\";\n"
            code += "     else\n"
            code += "       _OUT << \"\\\"\"<< \"\";\n"
            code += "     _OUT << std::endl;\n"
            code += "}\n"

        else:
            code = ""
            code += "static void print_%s(%s%s%s const std::string& str, bool commaNeeded=true) {\n" %(name, str1, name, str2)
            code += "     PRINT_SPACE\n"
            code += "     if (commaNeeded)\n"
            code += "         _OUT << \"\\\"\" << str << \"\\\"\" << \" : \" << obj << \",\" << std::endl;\n"
            code += "     else\n"
            code += "         _OUT << \"\\\"\" << str << \"\\\"\" << \" : \" << obj << std::endl;\n"
            code += "}\n"

        return code

    def genType(self, typeinfo, name, alias):
        OutputGenerator.genType(self, typeinfo, name, alias)
        typeElem = typeinfo.elem
        body = ""
        
        self.vkFeatureLayerList.append(name);

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
                        body += self.genBitmaskCode("", " obj,", elem.text, typeElem.get('requires'))
                        body += self.genBitmaskCode("const ", " * obj,", elem.text, typeElem.get('requires'))

            elif typeElem.get('category') == 'basetype':
                    for elem in typeElem:
                        if elem.tag == 'name':
                            body += self.genBasetypeCode("", " obj,", elem.text)
                            body += self.genBasetypeCode("const ", " * obj,", elem.text)

            elif typeElem.get('category') == 'handle':
                    for elem in typeElem:
                        if elem.tag == 'name':
                            body += self.genHandleCode("", " obj,", elem.text)
                            body += self.genHandleCode("const ", " * obj,", elem.text)
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

    def generateStructMembercode(self, param, str1, str2, str3, str4, memberName, typeName, isCommaNeeded):
        length = ""
        code = ""
        isArr = param.get('len') is not None

        if param.get('len') is not None:
            length = str2 + param.get('len') + ")"
        length = length.replace(')', '')
        length = length.replace(',1', '')

        code += "     PRINT_SPACE\n"
        code += "     _OUT << \"\\\"%s\\\": \" << std::endl;\n" %(memberName)

        if self.paramIsPointer(param): code += str4 + memberName + ") {\n"
        else:                          code += "     {\n"

        # TODO: With some tweak, we can use the genArrayCode() here.
        if isArr is True:
            code += "         PRINT_SPACE\n"
            code += "         _OUT << \"[\" << std::endl;\n"
            code += "         for (unsigned int i = 0; i < %s; i++) {\n" %(length)
            code += "           if (i+1 == %s)\n" %(length)
            code += "               print_%s(%s%s[i], \"%s\", 0);\n" %(typeName, str2, memberName, memberName)
            code += "           else\n"
            code += "               print_%s(%s%s[i], \"%s\", 1);\n" %(typeName, str2, memberName, memberName)
            code += "         }\n"
            code += "         PRINT_SPACE\n"
            if isCommaNeeded:
                code += "         _OUT << \"],\" << std::endl;\n"
            else:
                code += "         _OUT << \"]\" << std::endl;\n"
            code += "    }\n"
        else:
            if (typeName == "VkAccelerationStructureGeometryKHR"):
                code += "           print_%s(*%s%s, \"%s\", %s);\n" %(typeName, str2, memberName, memberName, str(isCommaNeeded))
            else:
                code += "           print_%s(%s%s, \"%s\", %s);\n" %(typeName, str2, memberName, memberName, str(isCommaNeeded))
            code += "     }\n"

        if self.paramIsPointer(param):
            code += "     else\n"
            code += "     {\n"
            if isCommaNeeded:
                code += "         PRINT_SPACE _OUT << \"\\\"NULL\\\"\"<< \",\"<< std::endl;\n"
            else:
                code += "         PRINT_SPACE _OUT << \"\\\"NULL\\\"\"<< \"\"<< std::endl;\n"
            code += "     }\n"

        return code

    def genPNextCode(self, str2):
        code  = ""
        code += "      if (%spNext) {\n" %(str2)
        code += "         dumpPNextChain(%spNext);\n" %(str2)
        code += "      } else {\n"
        code += "         PRINT_SPACE\n"
        code += "         _OUT << \"\\\"pNext\\\":\" << \"\\\"NULL\\\"\"<< \",\"<< std::endl;\n"
        code += "     }\n"

        return code

    # Prints out member name followed by empty string.
    def genEmptyCode(self, memberName, str2, isCommaNeeded):
        code = ""
        if not self.isCTS:
            code +=  "     /** Note: printing just an empty entry here **/\n"
        else:
            code +=  "     // CTS : required value\n"
        code +=  "     PRINT_SPACE"
        if isCommaNeeded:
            if self.isCTS and (memberName == "module" or memberName == "layout" or memberName == "renderPass" or memberName == "conversion"):
                code +=  "    _OUT << \"\\\"\" << \"%s\" << \"\\\"\" << \" : \" << %s%s.getInternal() << \",\" << std::endl;\n" %(memberName, str2, memberName)
            else:
                code +=  "    _OUT << \"\\\"\" << \"%s\" << \"\\\"\" << \" : \" << \"\\\"\" << \"\\\",\" << std::endl;\n" %(memberName)
        else:
            if self.isCTS and (memberName == "module" or memberName == "layout" or memberName == "renderPass" or memberName == "conversion"):
                code +=  "    _OUT << \"\\\"\" << \"%s\" << \"\\\"\" << \" : \" << %s%s.getInternal() << std::endl;\n" %(memberName, str2, memberName)
            else:
                code +=  "    _OUT << \"\\\"\" << \"%s\" << \"\\\"\" << \" : \" << \"\\\"\" << \"\\\"\" << std::endl;\n" %(memberName)
        return code

    def genArrayCode(self, structName, name, typeName, str2, arraySize, needStrPrint, isArrayType, isCommaNeeded):
            comma = "," if isCommaNeeded else ""
            code = ""
            arraySize = arraySize.replace(')', '')
            needsTmp = needStrPrint or (str(self.getTypeCategory(typeName)) == 'handle')
            
            if needStrPrint: printStr = "tmp.str()"
            else:            printStr = "\"\""

            code += "     PRINT_SPACE\n"
            code += "     _OUT << \"\\\"%s\\\":\" << std::endl;\n" %(name)
            code += "     PRINT_SPACE\n"
            if not isArrayType:
                code += "     if (%s%s) {\n" %(str2, name)
            code += "       _OUT << \"[\" << std::endl;\n"
            code += "       for (unsigned int i = 0; i < %s; i++) {\n" %(arraySize)
            if self.isCTS and (structName == "VkPipelineLayoutCreateInfo" or structName == "VkDescriptorSetLayoutBinding"):
                code += "           bool isCommaNeeded = (i+1) != %s;\n" %(arraySize)
                code += "           if (isCommaNeeded)\n"
                code += "           {\n"
                code += "               PRINT_SPACE\n"
                code += "               _OUT << %s%s[i].getInternal() << \",\" << std::endl;\n" %(str2, name)
                code += "           }\n"
                code += "           else\n"
                code += "           {\n"
                code += "               PRINT_SPACE\n"
                code += "               _OUT << %s%s[i].getInternal() << std::endl;\n" %(str2, name)
                code += "           }\n"
            else:
                if needsTmp:
                    code += "           std:: stringstream tmp;\n"

                    # Special case handling for giving unique names for pImmutableSamplers if there are multiple
                    # bindings in the same Descriptor set layout.
                    if name == "pImmutableSamplers":
                        code += "           tmp << \"%s\" << \"_\" << (%sbinding) << \"_\" << i;\n" %(name, str2)
                    else:
                        code += "           tmp << \"%s\" << \"_\" << i;\n" %(name)

                code += "           bool isCommaNeeded = (i+1) != %s;\n" %(arraySize)

                if str(self.getTypeCategory(typeName)) == 'handle':
                    code += "           print_%s(%s%s[i], tmp.str(), isCommaNeeded);\n" %(typeName, str2, name)
                else:
                    if self.isCTS and name == "pipelineIdentifier":
                        code += "           print_uint32_t((%s)%s%s[i], %s, isCommaNeeded);\n" %(self.baseTypeListMap["uint32_t"], str2, name, printStr)
                    else:
                        code += "           print_%s(%s%s[i], %s, isCommaNeeded);\n" %(typeName, str2, name, printStr)
            code += "       }\n"
            code += "       PRINT_SPACE\n"
            code += "       _OUT << \"]\" << \"%s\" << std::endl;\n" %(comma)
            if not isArrayType == True:
                code += "     } else {\n"
                code += "       _OUT << \"\\\"NULL\\\"\" << \"%s\" << std::endl;\n" %(comma)
                code += "     }\n"
            return code

    def genStructCode(self, param, str1, str2, str3, str4, structName, isCommaNeeded):
        code = ""
        memberName = ""
        typeName = ""

        for elem in param:
            if elem.text.find('PFN_') != -1:
                return "     /** Note: Ignoring function pointer (%s). **/\n" %(elem.text)

            if elem.text == 'pNext':
                return self.genPNextCode(str2)

            if elem.tag == 'name':
                memberName = elem.text

            if elem.tag == 'type':
                typeName = elem.text

            # Some arrays have constant sizes.
            if elem.text.find("VK_") != -1:
                return self.genArrayCode(structName, memberName, typeName, str2, elem.text, False, True, isCommaNeeded)

        if self.paramIsStaticArray(param):
            return self.genArrayCode(structName, memberName, typeName, str2, self.paramIsStaticArray(param), False, True, isCommaNeeded)

        # If the struct's member is another struct, we need a different way to handle.
        elif self.paramIsStruct(typeName) == 1:
            code += self.generateStructMembercode(param, str1, str2, str3, str4, memberName, typeName, isCommaNeeded)

        # Ignore void* data members
        elif self.paramIsPointer(param) and typeName == 'void':
            if structName == "VkSpecializationInfo":
                    return "     print_void_data(%s%s, int(%sdataSize), \"%s\", 0);\n" %(str2, memberName, str2, memberName)
            if self.isCTS:
                if structName == "VkPipelineCacheCreateInfo":
                    return "     print_void_data(%s%s, int(%sinitialDataSize), \"%s\", 0);\n" %(str2, memberName, str2, memberName)
            return "     /** Note: Ignoring void* data. **/\n"

        # For pointers where we have the 'len' field, dump them as arrays.
        elif self.paramIsPointer(param) and param.get('len') is not None and param.get('len').find('null-terminated') == -1 and param.get('len').find('latexmath') == -1:
            if memberName == "versionData":
                return self.genArrayCode(structName, memberName, typeName, str2, param.get('len')+")", False, False, isCommaNeeded)
            else:
                return self.genArrayCode(structName, memberName, typeName, str2, str2+param.get('len')+")", False, False, isCommaNeeded)

        # Special handling for VkPipelineMultisampleStateCreateInfo::pSampleMask
        elif typeName in "VkSampleMask":
            code += "     %s sampleMaskSize = ((%srasterizationSamples + 31) / 32);\n" % (self.baseTypeListMap["uint32_t"], str2)
            code += self.genArrayCode(structName, memberName, "uint32_t", str2, "sampleMaskSize", False, False, isCommaNeeded)
            return code

        # If a struct member is just a handle.
        elif str(self.getTypeCategory(typeName)) == 'handle':
            return self.genEmptyCode(memberName, str2, isCommaNeeded)

        else:
            code += "     print_%s(%s%s, \"%s\", %s);\n" %(typeName, str2, memberName, memberName, str(isCommaNeeded))

        return code

    def genStruct(self, typeinfo, typeName, alias):
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)
        body = ""
        typeElem = typeinfo.elem

        if alias:
            body = 'typedef ' + alias + ' ' + typeName + ';\n'
        else:
            genStr1 = [""   , "const "]
            genStr2 = ["obj.", "obj->" ]
            genStr3 = [" obj, const std::string& s, bool commaNeeded=true) {" , " * obj, const std::string& s, bool commaNeeded=true) {"]
            genStr4 = ["     if (obj.", "     if (obj->"]

            for index in range(len(genStr1)):
                body += "static void print_%s(%s%s%s\n" %(typeName, genStr1[index], typeName, genStr3[index])
                body += "     PRINT_SPACE\n"
                body += "     _OUT << \"{\" << std::endl;\n"
                body += "     INDENT(4);\n"
                body += "\n"
                count = 0
                numMembers = len(typeElem.findall('.//member'))

                isCommaNeeded = 1
                for member in typeElem.findall('.//member'):
                    count = count + 1
                    if count == numMembers:
                        isCommaNeeded = 0

                    body += self.genStructCode(member, genStr1[index], genStr2[index], genStr3[index], genStr4[index], typeName, isCommaNeeded)
                    body += "\n"

                body += "     INDENT(-4);\n"
                body += "     PRINT_SPACE\n"
                body += "     if (commaNeeded)\n"
                body += "         _OUT << \"},\" << std::endl;\n"
                body += "     else\n"
                body += "         _OUT << \"}\" << std::endl;\n"
                body += "}\n"

        self.appendSection('struct', body)

    def genGroup(self, groupinfo, groupName, alias=None):
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)
        groupElem = groupinfo.elem
        body = ""
        section = 'enum'

        body += "static std::map<%s, std::string> %s_map = {\n" %(self.baseTypeListMap["uint64_t"], groupName)
        enums = groupElem.findall('enum')

        for enum in enums:
            if enum.get('value'):
                body += "    std::make_pair(%s, \"%s\"),\n" %(enum.get('value'), enum.get('name'))

            elif enum.get('bitpos'):
                body += "    std::make_pair(1ULL << %s, \"%s\"),\n" %(enum.get('bitpos'), enum.get('name'))

            #TODO: Some enums have no offset. How to handle those?
            elif enum.get('extends') and enum.get("extnumber") and enum.get("offset"):
                extNumber = int(enum.get("extnumber"))
                offset = int(enum.get("offset"))
                enumVal = self.extBase + (extNumber - 1) * self.extBlockSize + offset
                body += "    std::make_pair(%s, \"%s\"),\n" %(str(enumVal), enum.get('name'))

        body += "};\n"
        body += self.genEnumCode(groupName)

        self.appendSection(section, body)
