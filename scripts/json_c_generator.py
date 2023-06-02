#!/usr/bin/python3 -i
#
# Copyright 2020-2023 The Khronos Group Inc.
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
** Copyright (c) 2020 The Khronos Group Inc.
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
#include <string.h>
#include <assert.h>
#include <inttypes.h>
#include <vulkan/vulkan.h>
#include "vulkan_json_gen.h"

#define MAX_SIZE 255 // We don't expect to write a bigger string at a time.
#define MAX_JSON_SIZE 1024*1024 // We don't expect the entire JSON file to be bigger than this.

static int s_num_spaces = 0;
static char s_tempBuf[MAX_SIZE];
static char s_outBuf[MAX_JSON_SIZE];
static char *s_writePtr = s_outBuf;

#define _OUT s_tempBuf

#define UPDATE_BUF strncpy(s_writePtr, s_tempBuf, strnlen(s_tempBuf, MAX_SIZE)); s_writePtr += strnlen(s_tempBuf, MAX_SIZE);

// Variadic macro for neat buffer update + print.
#define vk_json_printf(...) { sprintf(__VA_ARGS__); UPDATE_BUF }

// Helper utility to do indentation in the generated json file.
#define PRINT_SPACE \
{ \\
    int spaces; \\
    for (spaces = 0; spaces < s_num_spaces; spaces++) \\
        vk_json_printf(_OUT, " "); \\
}


#define INDENT(sz) s_num_spaces += (sz);

const char* getJSONOutput()
{
    return s_outBuf;
}

void resetJSONOutput(void)
{
    memset(s_outBuf, 0x00, MAX_JSON_SIZE);
    s_writePtr = s_outBuf;
}

"""

printVal = """
void print_@name(const @name * obj, const char* s, int commaNeeded) {
    PRINT_SPACE
    if (s[0] != 0) {
        vk_json_printf(_OUT, \"\\\"%s\\\" : FORMAT%s\\n\", s, *obj, commaNeeded ? \",\" : \"\");
    } else {
        vk_json_printf(_OUT, \"FORMAT%s\\n", *obj, commaNeeded ? \",\" : \"\");
    }
}
"""

class JSONCGeneratorOptions(GeneratorOptions):
    """JSONCGeneratorOptions - subclass of GeneratorOptions.

    Adds options used by JSONCOutputGenerator objects during C language header
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


class JSONCOutputGenerator(OutputGenerator):
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
        self.enumNames         = []
        self.baseTypeDict      = {
                                  "int32_t"  : "%d",
                                  "uint32_t" : "%u",
                                  "uint8_t"  : "%u",
                                  "uint64_t" : "%\" PRIu64 \"",
                                  "float"    : "%f",
                                  "int"      : "%d",
                                  "double"   : "%lf",
                                  "int64_t"  : "%\" PRId64 \"",
                                  "uint16_t" : "%u",
                                  "char"     : "%c",
                                  "size_t"   : "%zu"
                                  }

    def printBaseTypes(self):
        for baseType in self.baseTypeDict:
            temp = printVal
            temp = printVal.replace("@name", baseType)
            temp = temp.replace("FORMAT", self.baseTypeDict[baseType])
            write(temp, file=self.outFile)

    def genStructExtensionCode(self):
       code  = ""
       code += "void dumpPNextChain(const void* pNext) {\n"
       code += "      VkBaseInStructure *pBase = (VkBaseInStructure*)pNext;\n"
       code += "      if (pNext) {\n"
       code += "          PRINT_SPACE\n"
       code += "          vk_json_printf(_OUT, \"\\\"pNext\\\":\\n\");\n"
       code += "          switch (pBase->sType) {\n"

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
                               if currentExtension != "VK_VERSION_1_0":
                                   code += "#endif\n"
                               currentExtension = self.featureDict[n]
                               if self.featureDict[n] != "VK_VERSION_1_0":
                                   code += "#ifdef %s\n" %(currentExtension)
                           code += "             case %s:" %(m.get('values'))
                           code += "print_%s(((%s *)pNext), \"%s\", 1);\n" %(n, n, n)
                           code += "             break;\n"

       if currentExtension != "VK_VERSION_1_0":
            code += "#endif\n"
       code += "             default: assert(!\"No structure type matching!\");\n"
       code += "         }\n"
       code += "     }\n"
       code += "  }\n"

       return code

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

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
        self.createvkscFeatureList()

        write(copyright, file=self.outFile)
        write(predefinedCode, file=self.outFile)
        self.printBaseTypes()

        write(self.genStructExtensionCode(), file=self.outFile)

    def endFile(self):
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

    def appendSection(self, section, text, extension):
        if extension != "VK_VERSION_1_0":
            self.sections[section].append("#ifdef %s" %(extension))
        self.sections[section].append(text)
        self.feature_not_empty = True
        if extension != "VK_VERSION_1_0":
            self.sections[section].append("#endif")

    def genEnumData(self, name, obj):
        code = ""
        code += "     if (strncmp(str, \"\", 255)) vk_json_printf(_OUT, \"\\\"%s\\\" : \", str);\n"
        code += "     vk_json_printf(_OUT, \"\\\"%%s\\\"%%s\\n\", %s_map(*%sobj), commaNeeded ? \",\" : \"\");\n" %(name, obj)
        return code

    def genEnumCode(self, name):
        code = ""
        code += "void print_%s(const %s* obj, const char* str, int commaNeeded) {\n" %(name, name)
        code += "     PRINT_SPACE\n"
        code += self.genEnumData(name, "")
        code += "}\n"

        return code

    def genBasetypeCode(self, str1, str2, name, baseType):
        code = ""
        code += "void print_" + name + "(" + str1 + name + str2 + " const char* str, int commaNeeded) {\n"
        code += "     PRINT_SPACE\n"
        if name == "VkBool32":
            code += "     vk_json_printf(_OUT, \"\\\"%s\\\" : \\\"%s\\\"%s\\n\", str, (*obj == 0) ? (\"VK_FALSE\") : (\"VK_TRUE\"), commaNeeded ? \",\" : \"\");\n"
        else:
            code += "     vk_json_printf(_OUT, \"\\\"%s\\\" : \\\"" + self.baseTypeDict[baseType] + "\\\"%s\\n\", str, *obj, commaNeeded ? \",\" : \"\");\n"
        code += "}\n"
        return code

    def genHandleCode(self, str1, str2, name):
        code = ""
        code += "void print_%s(%s%s%s const char* str, int commaNeeded) {\n" %(name, str1, name, str2)
        code += "     (void)%s;\n" %(str2[:-1])
        code += "     PRINT_SPACE\n"
        code += "     vk_json_printf(_OUT, \"\\\"%s\\\"%s\\n\", str, commaNeeded ? \",\" : \"\");\n"
        code += "}\n"
        return code

    def genBitmaskCode(self, str1, str2, name, mapName):
        if mapName is not None:
            code = ""
            code += "void print_%s(%s%s%s const char* str, int commaNeeded) {\n" %(name, str1, name, str2)
            code += "     const unsigned int max_bits = 64; \n"
            code += "     unsigned int _count = 0;\n"
            code += "     unsigned int checkBit = 1;\n"
            code += "     unsigned int i = 0;\n"
            code += "     unsigned int bitCount = 0;\n"
            code += "     unsigned int n = *obj;\n"
            code += "     unsigned int b = *obj;\n"
            code += "     unsigned int res = 0;\n"
            code += "     PRINT_SPACE\n"
            code += "     vk_json_printf(_OUT, \"\\\"%s\\\" : \", str);\n"
            code += "     while (n) {\n"
            code += "        n &= (n-1);\n"
            code += "        _count++;\n"
            code += "     }\n"
            code += "     vk_json_printf(_OUT, \"\\\"\");\n"
            code += "     if (*obj == 0) vk_json_printf(_OUT, \"0\");\n"
            #We need bitpos here, so just iterate fully.
            code += "     for (i = 0, bitCount = 0; i < max_bits; i++, checkBit <<= 1) {\n"
            code += "         res = b & checkBit;\n"
            code += "         if (res) {\n"
            code += "             bitCount++;\n"
            code += "             if (bitCount < _count) {\n"
            code += "                 vk_json_printf(_OUT, \"%%s | \", %s_map(1<<i));\n" %(mapName)
            code += "             } else {\n"
            code += "                 vk_json_printf(_OUT, \"%%s\", %s_map(1<<i));\n" %(mapName)
            code += "             }\n"
            code += "         }\n"
            code += "     }\n"
            code += "     vk_json_printf(_OUT, \"\\\"%s\\n\", commaNeeded ? \",\" : \"\");\n"
            code += "}\n"

        else:
            code = ""
            code += "void print_%s(%s%s%s const char* str, int commaNeeded) {\n" %(name, str1, name, str2)
            code += "     PRINT_SPACE\n"
            code += "     vk_json_printf(_OUT, \"\\\"%s\\\" : \\\"%d\\\"%s\\n\", str, (int)(*obj), commaNeeded ? \",\" : \"\");\n"
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

        extension = "VK_VERSION_1_0"
        if (name in self.featureDict):
            extension = self.featureDict[name]

        if category in ('struct', 'union'):
            self.genStruct(typeinfo, name, alias)
        else:
            if typeElem.get('category') == 'bitmask':
                for elem in typeElem:
                    if elem.tag == 'name':
                        body += self.genBitmaskCode("const ", " * obj,", elem.text, typeElem.get('requires'))

            elif typeElem.get('category') == 'basetype':
                    body += self.genBasetypeCode("const ", " * obj,", typeElem.find('name').text, typeElem.find('type').text)

            elif typeElem.get('category') == 'handle':
                    for elem in typeElem:
                        if elem.tag == 'name':
                            body += self.genHandleCode("const ", "  * obj,", elem.text)
            if body:
                self.appendSection(section, body, extension)

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
        comma = "," if isCommaNeeded else ""
        isArr = param.get('len') is not None

        if param.get('len') is not None:
            length = str2 + param.get('len')

        if  re.search(r'\d', length) is None: derefPtr = "*"
        else:                                 derefPtr = ""

        code += "     PRINT_SPACE\n"
        code += "     vk_json_printf(_OUT, \"\\\"%s\\\" :\");\n" %(memberName)

        if self.paramIsPointer(param): code += str4 + memberName + ") {\n"
        else:                          code += "     {\n"
        if isArr:                      code += "         unsigned int i = 0;\n"
        code += "         vk_json_printf(_OUT, \"\\n\");\n"

        # TODO: With some tweak, we can use the genArrayCode() here.
        if isArr is True:
            code += "         PRINT_SPACE\n"
            code += "         vk_json_printf(_OUT, \"[\\n\");\n"
            code += "         for (i = 0; i < %s(%s); i++) {\n" %(derefPtr, length)
            code += "             if (i+1 == %s(%s))\n" %(derefPtr, length)
            code += "                 print_%s(%s%s[i], \"%s\", 0);\n" %(typeName, str2, memberName, memberName)
            code += "             else\n"
            code += "                 print_%s(%s%s[i], \"%s\", 1);\n" %(typeName, str2, memberName, memberName)
            code += "         }\n"
            code += "         PRINT_SPACE\n"
            code += "         vk_json_printf(_OUT, \"]%s\\n\");\n" % comma
            code += "     }\n"
        elif self.paramIsPointer(param):
            code += "         print_%s(*(%s%s), \"%s\", %s);\n" %(typeName, str2, memberName, memberName, str(isCommaNeeded))
            code += "     }\n"

        else:
            code += "         print_%s(%s%s, \"%s\", %s);\n" %(typeName, str2, memberName, memberName, str(isCommaNeeded))
            code += "     }\n"

        if self.paramIsPointer(param):
            code += "     else \n"
            code += "     {\n"
            code += "         vk_json_printf(_OUT, \" \\\"NULL\\\"%s\\n\");\n" % comma
            code += "     }\n"

        return code

    def genPNextCode(self, str2):
        code  = ""
        code += "     if (obj->pNext) {\n"
        code += "         dumpPNextChain(obj->pNext);\n"
        code += "     } else {\n"
        code += "         PRINT_SPACE\n"
        code += "         vk_json_printf(_OUT, \"\\\"pNext\\\" : \\\"NULL\\\",\\n\");\n"
        code += "     }\n"

        return code

    # TODO: This may need to be relaxed in the schema. The schema could say array of integers,
    # but we will print the extra strings to show them
    def genArrayCode(self, name, typeName, str2, arraySize, needStrPrint, isCommaNeeded):
            comma = "," if isCommaNeeded else ""
            code = ""
            printStr  = "\"\""
            arraySize = arraySize.replace(')', '')
            derefPtr = "*"
            if arraySize.find("VK") != -1 or re.search(r'\d', arraySize) is not None:
                derefPtr = ""

            code += "     PRINT_SPACE\n"
            code += "     vk_json_printf(_OUT, \"\\\"%s\\\" :\");\n" %(name)
            code += "     if (obj->%s) {\n" %(name)
            code += "        bool isCommaNeeded = false;\n"
            code += "        unsigned int i = 0;\n"
            code += "        vk_json_printf(_OUT, \"\\n\"); PRINT_SPACE\n"
            code += "        vk_json_printf(_OUT, \"[\\n\");\n"
            code += "        for (i = 0; i < %s(%s); i++) {\n" %(derefPtr, arraySize)
            code += "            char tmp[100];\n"
            
            # Special case handling for giving unique names for pImmutableSamplers if there are multiple
            # bindings in the same Descriptor set layout.
            if name == "pImmutableSamplers":
                code += "            sprintf(tmp, \"%s_%%u_%%u\", *(%sbinding), i);\n" %(name, str2)
            else:
                code += "            sprintf(tmp, \"%s_%%u\", i);\n" %(name)

            code += "            INDENT(4);\n"
            code += "            isCommaNeeded = (i+1) != %s(%s);\n" %(derefPtr, arraySize)
            if str(self.getTypeCategory(typeName)) == 'handle':
                code += "            print_%s(%s%s[i], tmp, isCommaNeeded);\n" %(typeName, str2, name)
            elif not typeName.startswith("Std"):
                code += "            print_%s(%s%s[i], %s, isCommaNeeded);\n" %(typeName, str2, name, printStr)
            code += "            INDENT(-4);\n"
            code += "        }\n"
            code += "        PRINT_SPACE\n"
            code += "        vk_json_printf(_OUT, \"]%s\\n\");\n" %(comma)
            code += "     } else {\n"
            code += "         vk_json_printf(_OUT, \" \\\"NULL\\\"%s\\n\");\n" %(comma)
            code += "     }\n"
            
            return code

    # Prints out member name followed by empty string.
    def genEmptyCode(self, memberName, isCommaNeeded):
        comma = "," if isCommaNeeded else ""
        code = ""
        code +=  "     /** Note: printing just an empty entry here **/\n"
        code +=  "     PRINT_SPACE"
        code +=  "    vk_json_printf(_OUT, \"\\\"%s\\\" : \\\"\\\"%s\\n\");\n" %(memberName, comma)

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
                return self.genArrayCode(memberName, typeName, str2, elem.text, False, isCommaNeeded)

        if self.paramIsStaticArray(param):
            return self.genArrayCode(memberName, typeName, str2, self.paramIsStaticArray(param), False, isCommaNeeded)

        # If the struct's member is another struct, we need a different way to handle.
        elif self.paramIsStruct(typeName) == 1:
            code += self.generateStructMembercode(param, str1, str2, str3, str4, memberName, typeName, isCommaNeeded)

        # Ignore void* data members
        elif self.paramIsPointer(param) and typeName == 'void':
            return "     /** Note: Ignoring void* data. **/\n"

        # Handle C style strings
        elif self.paramIsPointer(param) and param.get('len') is not None and param.get('len').find('null-terminated') != -1:
            code = "     /** Printing string inline. **/\n"
            code += "     PRINT_SPACE\n"
            code += "     vk_json_printf(_OUT, \"\\\"%s\\\" : \\\"%%s\\\",\\n\", (char*)obj->%s);\n" %(memberName, memberName)
            return code

        #TODO: Handle this path.
        elif self.paramIsPointer(param) and param.get('len') is not None and param.get('len').find('latexmath') != -1:
            code = "     /** Skipping %s. **/\n" %(typeName)

        # For pointers where we have the 'len' field, dump them as arrays.
        elif self.paramIsPointer(param) and param.get('len') is not None and param.get('len').find('null-terminated') == -1 and param.get('len').find('latexmath') == -1:
            return self.genArrayCode(memberName, typeName, str2, str2+param.get('len')+")", False, isCommaNeeded)

        # If a struct member is just a handle.
        elif str(self.getTypeCategory(typeName)) == 'handle':
            return self.genEmptyCode(memberName, isCommaNeeded)

        elif not typeName.startswith("Std"):
            code += "     print_%s(%s%s, \"%s\", %s);\n" %(typeName, str2, memberName, memberName, str(isCommaNeeded))

        return code

    def genStruct(self, typeinfo, typeName, alias):
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)
        body = ""
        typeElem = typeinfo.elem

        extension = "VK_VERSION_1_0"
        if (typeName in self.featureDict):
            extension = self.featureDict[typeName]

        if alias:
            body = 'typedef ' + alias + ' ' + typeName + ';\n'
        else:
            # The code here is similar to the hpp generator. Hence maintaining similar form.
            genStr1 = ["const "]
            genStr2 = ["&obj->" ]
            genStr3 = [" * obj, const char* s, int commaNeeded) {"]
            genStr4 = ["     if (obj->"]

            for index in range(len(genStr1)):
                body += "void print_%s(%s%s%s\n" %(typeName, genStr1[index], typeName, genStr3[index])
                body += "     (void)s;\n"
                body += "     PRINT_SPACE\n"
                body += "     vk_json_printf(_OUT, \"{\\n\");\n"
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
                body += "     vk_json_printf(_OUT, \"}%s\\n\", commaNeeded ? \",\" : \"\");\n"
                body += "}\n"

        self.appendSection('struct', body, extension)

    def genGroup(self, groupinfo, groupName, alias=None):
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)
        groupElem = groupinfo.elem
        body = ""
        section = 'enum'

        extension = "VK_VERSION_1_0"
        if (groupName in self.featureDict):
            extension = self.featureDict[groupName]
        enumType = "uint32_t"
        bitStr = "1u"
        if groupElem.get('bitwidth') and (int(groupElem.get('bitwidth')) == 64):
            enumType = "uint64_t"
            bitStr = "1ull"

        body += "static const char* %s_map(%s o) {\n" %(groupName, enumType)
        body += "switch (o) {\n"
        enums = groupElem.findall('enum')

        for enum in enums:
            # Avoid having duplicates.
            if enum.get('name') not in self.enumNames:
                self.enumNames.append(enum.get('name'))

                if enum.get('value'):
                    body += "    case %s: return \"%s\";\n" %(enum.get('value'), enum.get('name'))

                elif enum.get('bitpos'):
                    body += "    case (%s << %s): return \"%s\";\n" %(bitStr, enum.get('bitpos'), enum.get('name'))

                #TODO: Some enums have no offset. How to handle those?
                elif enum.get('extends') and enum.get("extnumber") and enum.get("offset"):
                    extNumber = int(enum.get("extnumber"))
                    offset = int(enum.get("offset"))
                    enumVal = self.extBase + (extNumber - 1) * self.extBlockSize + offset
                    body += "    case %s: return \"%s\";\n" %(str(enumVal), enum.get('name'))

        body += "   }\n"
        body += "   return NULL;\n";
        body += "}\n"
        body += self.genEnumCode(groupName)

        self.appendSection(section, body, extension)
