#!/usr/bin/env python3 -i
#
# Copyright 2020-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Description:
# -----------
# This script generates a full schema definition from the vk.xml.

import os
import re
from generator import (GeneratorOptions, OutputGenerator, noneStr,
                       regSortFeatures, write)


headerString = "\
{\n\
\"$schema\": \"http://json-schema.org/draft-04/schema#\", \n\
\"id\": \"https://schema.khronos.org/vulkan/vk.json#\",\n\
\"title\": \"JSON schema for Vulkan SC\",\n\
\"description\": \"Schema for representing entire vk.xml as a schema.\",\n\
\"type\": \"object\",\n\
\"additionalProperties\": true,\n\
\"definitions\": {\
"

basetypeString = "\
    \"$schema\": {\"type\": \"string\", \"format\": \"uri\"},\n\
    \"uint8_t\": {\"type\": \"integer\", \"minimum\": 0, \"maximum\": 255},\n\
    \"int32_t\": {\"type\": \"integer\", \"minimum\": -2147483648, \"maximum\": 2147483647},\n\
    \"uint32_t\": {\"type\": \"integer\", \"minimum\": 0, \"maximum\": 4294967295},\n\
    \"uint64_t\": {\"oneOf\": [{\"enum\": [\"\"]},{\"type\": \"integer\"}]},\n\
    \"char\": {\"type\": \"string\"},\n\
    \"float\": {\"type\": \"number\"},\n\
    \"size_t\": {\"$ref\": \"#/definitions/uint32_t\"},\n\
    \"enum\": {\"type\": \"string\"},\n\
    \"void\": {\"enum\": [\"NULL\", \"\"]},\
"

class SchemaGeneratorOptions(GeneratorOptions):
    """SchemaGeneratorOptions - subclass of GeneratorOptions.

    Adds options used by SchemaOutputGenerator objects during C language header
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

        self.prefixText = prefixText
        """list of strings to prefix generated header with (usually a copyright statement + calling convention macros)."""

        self.genFuncPointers = genFuncPointers
        """True if function pointer typedefs should be generated"""

        self.protectFile = protectFile
        """True if multiple inclusion protection should be generated (based on the filename) around the entire header."""

        self.protectFeature = protectFeature
        """True if #ifndef..#endif protection should be generated around a feature interface in the header file."""

        self.protectProto = protectProto
        """If conditional protection should be generated around prototype declarations, set to either '#ifdef' to require opt-in (#ifdef protectProtoStr) or '#ifndef' to require opt-out (#ifndef protectProtoStr). Otherwise set to None."""

        self.protectProtoStr = protectProtoStr
        """#ifdef/#ifndef symbol to use around prototype declarations, if protectProto is set"""

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

        self.genEnumBeginEndRange = genEnumBeginEndRange
        """True if BEGIN_RANGE / END_RANGE macros should be generated for enumerated types"""

        self.genAliasMacro = genAliasMacro
        """True if the OpenXR alias macro should be generated for aliased types (unclear what other circumstances this is useful)"""

        self.aliasMacro = aliasMacro
        """alias macro to inject when genAliasMacro is True"""

        self.codeGenerator = True
        """True if this generator makes compilable code"""


class SchemaOutputGenerator(OutputGenerator):
    # This is an ordered list of sections in the header file.
    TYPE_SECTIONS = ['basetype', 'handle', 'enum', 'group', 'bitmask', 'struct']
    ALL_SECTIONS = TYPE_SECTIONS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Internal state - accumulators for different inner block text
        self.sections = {section: [] for section in self.ALL_SECTIONS}
        self.feature_not_empty = False
        self.may_alias = None

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        # Write schema header
        write(headerString, file=self.outFile)
        write(basetypeString, file=self.outFile)

    def endFile(self):
        write("    \"VkLastStructure\": {", file=self.outFile)
        write("    }", file=self.outFile)
        write("  }", file=self.outFile)
        write("}", file=self.outFile)

        # Finish processing in superclass
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

        elif category == 'handle':
            for elem in typeElem:
                if elem.tag == 'name':
                    body += "    \"" + elem.text + "\": {\"$ref\": \"#/definitions/uint64_t" + "\"},"

        elif category in ('bitmask','basetype'):
            storeType = ""
            section = 'bitmask'

            for elem in typeElem:
                if elem.tag == 'type':
                    storeType = elem.text

                if elem.tag == 'name':
                    if elem.text == "VkBool32":
                        body += "    \"" + elem.text + "\": {\"oneOf\": [{\"$ref\": \"#/definitions/" + storeType + "\"},{\"enum\": [\"VK_TRUE\", \"VK_FALSE\"]}]},"
                    elif elem.text == "VkFlags":
                        body += "    \"" + elem.text + "\": {\"oneOf\": [{\"$ref\": \"#/definitions/" + storeType + "\"},{\"$ref\": \"#/definitions/enum\"}]},"
                    else:
                        body += "    \"" + elem.text + "\": {\"$ref\": \"#/definitions/" + storeType + "\"},"

        if body:
            self.appendSection(section, body)

    def genMemberSchema(self, structure, param):
        paramdecl = ""
        storeType = ""
        isArr = param.get('len') not in (None, "null-terminated")
        isPtr = False

        for elem in param:
            text = noneStr(elem.text)
            tail = noneStr(elem.tail)

            #TODO: In the actual json data, we inline the pNext structs by checking what they point to, at runtime.
            #      This is however not possible to be represented in the schema. So, the plan is to not represent the
            #      pNext structs altogether or to indicate that these would be represented at runtime.
            #if elem.text != 'pNext' and elem.text != 'sType' and elem.text != 'VkStructureType' and elem.text != 'void' and elem.text != 'const':
            if 1:
                if elem.tag == 'type':
                    storeType = text
                    if '*' in tail:
                        isPtr = True

                if elem.tag == 'name':
                    paramdecl += "            \"" + text + "\": "
                    if isPtr and text != "pNext":
                        paramdecl += "{\"oneOf\": [{\"$ref\": \"#/definitions/void\"},"

                    if isArr or tail.startswith('['):
                        # TODO: How to get maxCount here?
                        paramdecl += " {\"type\": \"array\", \"minItems\": 0, \"maxItems\": 255, \"items\": {\"$ref\": \"#/definitions/"
                        if (structure == "VkPipelineLayoutCreateInfo" and text == "pSetLayouts") or \
                           (structure == "VkDescriptorSetLayoutBinding" and text == "pImmutableSamplers") or \
                           (structure == "VkSamplerYcbcrConversionInfo" and text == "conversion"):
                            paramdecl += "char\"}}"
                        elif (storeType == "void"):
                            # void* data can be NULL, an array of uint8_t data, or a Base64-encoded string
                            paramdecl += "uint8_t\"}}, {\"type\": \"string\"}"
                        else:
                            paramdecl += storeType + "\"}}"
                    else:
                        paramdecl += "{\"$ref\": \"#/definitions/"
                        paramdecl += storeType + "\"}"

                    if isPtr and text != "pNext":
                        paramdecl += "]}"
                    isPtr = False
            else:
                return ""

        return paramdecl

    def genStruct(self, typeinfo, typeName, alias):
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)
        body = ""
        typeElem = typeinfo.elem

        if alias:
            return
        else:
            body = ''
            body += "    \"" + typeName + "\": {\n"
            body += "        \"type\": \"object\",\n"
            body += "        \"additionalProperties\": false,\n"
            body += "        \"properties\": {\n"

            count = 0
            numMembers = len(typeElem.findall('.//member'))

            for member in typeElem.findall('.//member'):
                count = count + 1

                genText = self.genMemberSchema(typeName, member)
                body += genText

                if count < numMembers and genText != "":
                    body += ','
                    body += '\n'
            body += "\n        }\n"
        body += "    },\n"

        self.appendSection('struct', body)

    def genGroup(self, groupinfo, groupName, alias=None):
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)
        groupElem = groupinfo.elem
        body = ""

        section = 'enum'
        body += "    \"" + groupName + "\": {\"$ref\": \"#/definitions/enum"+ "\"},"

        self.appendSection(section, body)

