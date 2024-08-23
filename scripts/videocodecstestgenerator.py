#!/usr/bin/env python3
#
# Copyright 2024 The Khronos Group Inc.
# Copyright 2024 RasterGrid Kft.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Daniel Rakos <daniel.rakos@rastergrid.com>
#
# Purpose:      This script generates code based on the <videocodecs> block
#               in the vk.xml to verify the descripted relationships at the
#               actual source code level the tags are expected to used in.

from typing import OrderedDict
import xml.etree.ElementTree as etree
import argparse
import copy

class VulkanVideoRequiredCapabilities():
    def __init__(self, struct, member, value):
        self.struct = struct
        self.member = member
        self.value = value


class VulkanVideoFormat():
    def __init__(self, name, usage):
        self.name = name
        self.usage = usage
        self.requiredCaps = list()
        self.properties = OrderedDict()


class VulkanVideoProfileStructMember():
    def __init__(self, name):
        self.name = name
        self.values = OrderedDict()


class VulkanVideoProfileStruct():
    def __init__(self, struct):
        self.struct = struct
        self.members = OrderedDict()


class VulkanVideoCodec():
    def __init__(self, name, extend = None, value = None):
        self.name = name
        self.value = value
        self.profileStructs = OrderedDict()
        self.capabilities = OrderedDict()
        self.formats = OrderedDict()
        if extend is not None:
            self.profileStructs = copy.deepcopy(extend.profileStructs)
            self.capabilities = copy.deepcopy(extend.capabilities)
            self.formats = copy.deepcopy(extend.formats)

    def is_specific_codec(self):
        # If no video codec operation flag bit is associated with the codec description
        # then it is a codec category (e.g. decode, encode), not a specific codec
        return self.value is not None


def varNameFromTypeName(name):
    return f'{name[2:]}'


def cBoolExpFromXmlBoolExp(exp):
    return exp.replace('+', ' && ').replace(',', ' || ')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--registry', action='store',
                        default='xml/vk.xml',
                        help='Use specified registry file instead of vk.xml')
    parser.add_argument('--output', action='store',
                        required=True,
                        help='Output source file')
    args = parser.parse_args()

    xml = etree.parse(args.registry)

    baseProfileStruct = 'VkVideoProfileInfoKHR'
    baseCapabilitiesStruct = 'VkVideoCapabilitiesKHR'
    baseFormatPropertiesStruct = 'VkVideoFormatPropertiesKHR'

    with open(args.output, 'w') as out:
        out.write('#include <vulkan/vulkan.h>\n')

        videoCodecs = dict()
        xmlVideoCodecs = xml.find("./videocodecs")
        for xmlVideoCodec in xmlVideoCodecs.findall("./videocodec"):
            name = xmlVideoCodec.get('name')
            extend = xmlVideoCodec.get('extend')
            value = xmlVideoCodec.get('value')

            if name in videoCodecs:
                print(f'ERROR: Duplicate videocodec name="{name}"')
                exit(1)

            if value is None:
                # Video codec category
                videoCodecs[name] = VulkanVideoCodec(name)
            else:
                # Specific video codec
                videoCodecs[name] = VulkanVideoCodec(name, videoCodecs[extend], value)
            videoCodec = videoCodecs[name]

            for xmlVideoProfiles in xmlVideoCodec.findall("./videoprofiles"):
                videoProfileStructName = xmlVideoProfiles.get('struct')

                if videoProfileStructName in videoCodec.profileStructs:
                    print(f'ERROR: Duplicate videoprofiles struct="{memberName}" for videocodec name="{name}"')
                    exit(1)

                videoCodec.profileStructs[videoProfileStructName] = VulkanVideoProfileStruct(videoProfileStructName)
                videoProfileStruct = videoCodec.profileStructs[videoProfileStructName]

                for xmlVideoProfileMember in xmlVideoProfiles.findall("./videoprofilemember"):
                    memberName = xmlVideoProfileMember.get('name')

                    if memberName in videoProfileStruct.members:
                        print(f'ERROR: Duplicate videoprofilemember name="{memberName}" for videoprofiles struct="{videoProfileStructName}", videocodec name="{name}"')
                        exit(1)

                    videoProfileStruct.members[memberName] = VulkanVideoProfileStructMember(memberName)
                    videoProfileStructMember = videoProfileStruct.members[memberName]

                    for xmlVideoProfile in xmlVideoProfileMember.findall("./videoprofile"):
                        if xmlVideoProfile.get('value') in videoProfileStructMember.values:
                            print(f'ERROR: Duplicate videoprofile value="{xmlVideoProfile.get("value")}" for videoprofilemember name="{memberName}", videoprofiles struct="{videoProfileStructName}", videocodec name="{name}"')
                            exit(1)

                        videoProfileStructMember.values[xmlVideoProfile.get('value')] = xmlVideoProfile.get('name')

            for xmlVideoCapabilities in xmlVideoCodec.findall("./videocapabilities"):
                capabilityStructName = xmlVideoCapabilities.get('struct')
                videoCodec.capabilities[capabilityStructName] = capabilityStructName

            for xmlVideoFormat in xmlVideoCodec.findall("./videoformat"):
                videoFormatName = xmlVideoFormat.get('name')
                videoFormatUsage = xmlVideoFormat.get('usage')

                if videoFormatName in videoCodec.formats:
                    print(f'ERROR: Duplicate videoformat name="{videoFormatName}" for videocodec name="{name}"')
                    exit(1)

                videoCodec.formats[videoFormatName] = VulkanVideoFormat(videoFormatName, videoFormatUsage)
                videoFormat = videoCodec.formats[videoFormatName]

                for xmlVideoFormatProperties in xmlVideoFormat.findall("./videoformatproperties"):
                    propertiesStructName = xmlVideoFormatProperties.get('struct')

                    if propertiesStructName in videoFormat.properties:
                        print(f'ERROR: Duplicate videoformatproperties struct="{propertiesStructName}" for videoformat name="{videoFormatName}", videocodec name="{name}"')
                        exit(1)

                    videoFormat.properties[propertiesStructName] = propertiesStructName

                for xmlVideoFormatRequiredCap in xmlVideoFormat.findall("./videorequirecapabilities"):
                    requiredCapStruct = xmlVideoFormatRequiredCap.get('struct')
                    requiredCapMember = xmlVideoFormatRequiredCap.get('member')
                    requiredCapValue = xmlVideoFormatRequiredCap.get('value')
                    videoFormat.requiredCaps.append(VulkanVideoRequiredCapabilities(requiredCapStruct, requiredCapMember, requiredCapValue))

        out.write('int main() {\n')

        for videoCodec in videoCodecs.values():
            if videoCodec.is_specific_codec():
                out.write(f'    // {videoCodec.name}\n')
                out.write('    {\n')
                out.write(f'        VkVideoCodecOperationFlagBitsKHR codecOp = {videoCodec.value};\n')
                out.write('        (void)codecOp;\n')

                for profileStruct in videoCodec.profileStructs.values():
                    xmlProfileStruct = xml.find(f"./types/type[@name='{profileStruct.struct}']")
                    if xmlProfileStruct is None:
                        print(f'ERROR: Video profile struct "{profileStruct.struct}" not found')
                        exit(1)
                    if not baseProfileStruct in xmlProfileStruct.get('structextends').split(','):
                        print(f'ERROR: Video profile struct "{profileStruct.struct}" does not extend {baseProfileStruct}')
                        exit(1)

                    profileStructVarName = varNameFromTypeName(profileStruct.struct)
                    out.write(f'        {profileStruct.struct} {profileStructVarName};\n')
                    for profileStructMember in profileStruct.members.values():
                        for value, name in profileStructMember.values.items():
                            out.write(f'        {profileStructVarName}.{profileStructMember.name} = {value}; // {name}\n')
                    out.write(f'        (void){profileStructVarName};\n')

                for capabilitiesStruct in videoCodec.capabilities:
                    xmlCapabilitiesStruct = xml.find(f"./types/type[@name='{capabilitiesStruct}']")
                    if xmlCapabilitiesStruct is None:
                        print(f'ERROR: Video capabilities struct "{capabilitiesStruct}" not found')
                        exit(1)
                    if not baseCapabilitiesStruct in xmlCapabilitiesStruct.get('structextends').split(','):
                        print(f'ERROR: Video capabilities struct "{capabilitiesStruct}" does not extend {baseCapabilitiesStruct}')
                        exit(1)
                    out.write(f'        {capabilitiesStruct} {varNameFromTypeName(capabilitiesStruct)} = {{}};\n')
                    out.write(f'        (void){varNameFromTypeName(capabilitiesStruct)};\n')

                for format in videoCodec.formats.values():
                    out.write(f'        // {format.name}\n')
                    out.write('        {\n')
                    out.write(f'            VkImageUsageFlags formatUsage = {cBoolExpFromXmlBoolExp(format.usage)};')
                    out.write('            (void)formatUsage;\n')
                    for i, requiredCap in enumerate(format.requiredCaps):
                        out.write(f'            VkBool32 requirement{i} = ({varNameFromTypeName(requiredCap.struct)}.{requiredCap.member} == {cBoolExpFromXmlBoolExp(requiredCap.value)});\n')
                        out.write(f'            (void)requirement{i};\n')
                    for properties in format.properties:
                        xmlPropertiesStruct = xml.find(f"./types/type[@name='{properties}']")
                        if xmlPropertiesStruct is None:
                            print(f'ERROR: Video format properties struct "{properties}" not found')
                            exit(1)
                        if not baseFormatPropertiesStruct in xmlPropertiesStruct.get('structextends').split(','):
                            print(f'ERROR: Video format properties struct "{properties}" does not extend {baseFormatPropertiesStruct}')
                            exit(1)
                        out.write(f'            {properties} {varNameFromTypeName(properties)};\n')
                        out.write(f'            (void){varNameFromTypeName(properties)} = {{}};\n')
                    out.write('        }\n')

                out.write('    }\n')

        out.write('    return 0;\n')
        out.write('}\n')
