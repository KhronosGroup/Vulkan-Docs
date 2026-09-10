#!/usr/bin/env python3 -i
#
# Copyright 2025-2026 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0 OR MIT
import os
import sys
import pytest
from xml.etree import ElementTree

registry_path = os.path.abspath((os.path.dirname(__file__)))
sys.path.insert(0, registry_path)
from reg import Registry
from base_generator import *
from vulkan_object import *

class MyGenerator(BaseGenerator):
    def __init__(self):
        BaseGenerator.__init__(self)

    def generate(self):
        print(f'VulkanObject generated for {self.targetApiName}')

        version = self.vk.headerVersionComplete.split('.')
        assert len(version) == 3
        # These asserts are just here until we have a more robust way to get these values
        if self.targetApiName == 'vulkan':
            assert version[0] == '1'
            assert version[1] == '4'
        elif self.targetApiName == 'vulkansc':
            assert version[0] == '1'
            assert version[1] == '0'

        # isinstance() will make sure we are reporting valid types exposed in the
        # VulkanObject interface for each .
        # Note - it will not recursively inspect each member class
        assert isinstance(self.vk.headerVersion, str)
        for handle in self.vk.handles.values():
            assert isinstance(handle, Handle)
        for command in self.vk.commands.values():
            assert isinstance(command, Command)
            for param in command.params:
                assert isinstance(param, Param)
            for extension in command.extensions:
                assert isinstance(extension, str)
            for task in command.tasks:
                assert isinstance(task, str)
            for code in command.successCodes:
                assert isinstance(code, str)
            for code in command.errorCodes:
                assert isinstance(code, str)
        for struct in self.vk.structs.values():
            assert isinstance(struct, Struct)
            for member in struct.members:
                assert isinstance(member, Member)
            for extension in struct.extensions:
                assert isinstance(extension, str)
            for alias in struct.aliases:
                assert isinstance(alias, str)
            for e in struct.extends:
                assert isinstance(e, str)
            for e in struct.extendedBy:
                assert isinstance(e, str)
        for enum in self.vk.enums.values():
            assert isinstance(enum, Enum)
            for alias in enum.aliases:
                assert isinstance(alias, str)
            for e in enum.extensions:
                assert isinstance(e, str)
            for e in enum.fieldExtensions:
                assert isinstance(e, str)
            for field in enum.fields:
                assert isinstance(field, EnumField)
                for alias in field.aliases:
                    assert isinstance(alias, str)
                for e in field.extensions:
                    assert isinstance(e, str)
        for bitmask in self.vk.bitmasks.values():
            assert isinstance(bitmask, Bitmask)
            for alias in bitmask.aliases:
                assert isinstance(alias, str)
            for e in bitmask.extensions:
                assert isinstance(e, str)
            for e in bitmask.flagExtensions:
                assert isinstance(e, str)
            for flag in bitmask.flags:
                assert isinstance(flag, Flag)
                for e in flag.extensions:
                    assert isinstance(e, str)
        for flag in self.vk.flags.values():
            assert isinstance(flag, Flags)
            for e in flag.extensions:
                assert isinstance(e, str)
        for constant in self.vk.constants.values():
            assert isinstance(constant, Constant)
        for format in self.vk.formats.values():
            assert isinstance(format, Format)
            for component in format.components:
                assert isinstance(component, FormatComponent)
            for plane in format.planes:
                assert isinstance(plane, FormatPlane)
            for extent in format.blockExtent:
                assert isinstance(extent, str)
        for funcPointer in self.vk.funcPointers.values():
            assert isinstance(funcPointer, FuncPointer)
            for param in funcPointer.params:
                assert isinstance(param, FuncPointerParam)
        for extension in self.vk.extensions.values():
            assert isinstance(extension, Extension)
            for special in extension.specialUse:
                assert isinstance(special, str)
            for handle in extension.handles:
                assert isinstance(handle, Handle)
            for command in extension.commands:
                assert isinstance(command, Command)
            for struct in extension.structs:
                assert isinstance(struct, Struct)
            for enum in extension.enums:
                assert isinstance(enum, Enum)
            for bitmask in extension.bitmasks:
                assert isinstance(bitmask, Bitmask)
            for flag in extension.flags:
                assert isinstance(flag, Flags)
            for enumFields in extension.enumFields.values():
                for enum in enumFields:
                    assert isinstance(enum, EnumField)
            for flagBits in extension.flagBits.values():
                for flag in flagBits:
                    assert isinstance(flag, Flag)
            for feature in extension.featureRequirement:
                assert isinstance(feature, FeatureRequirement)
            assert(extension.vendorTag in self.vk.vendorTags)
        for version in self.vk.versions.values():
            assert isinstance(version, Version)
            for feature in version.featureRequirement:
                assert isinstance(feature, FeatureRequirement)
        for videoCodec in self.vk.videoCodecs.values():
            for videoProfiles in videoCodec.profiles.values():
                assert isinstance(videoProfiles, VideoProfiles)
                for member in videoProfiles.members.values():
                    assert isinstance(member, VideoProfileMember)
                    for value in member.values.values():
                        assert isinstance(value, str)
            for videoCaps in videoCodec.capabilities.values():
                assert isinstance(videoCaps, str)
            for videoFormat in videoCodec.formats.values():
                assert isinstance(videoFormat, VideoFormat)
                for requiredCaps in videoFormat.requiredCaps:
                    assert isinstance(requiredCaps, VideoRequiredCapabilities)
                for props in videoFormat.properties.values():
                    assert isinstance(props, str)
        if self.vk.videoStd is not None:
            for header in self.vk.videoStd.headers.values():
                assert isinstance(header, VideoStdHeader)
            for enum in self.vk.videoStd.enums.values():
                assert isinstance(enum, Enum)
                assert isinstance(enum.videoStdHeader, str)
            for struct in self.vk.videoStd.structs.values():
                assert isinstance(struct, Struct)
                assert isinstance(struct.videoStdHeader, str)
                for member in struct.members:
                    assert isinstance(member, Member)
            for constant in self.vk.videoStd.constants.values():
                assert isinstance(constant, Constant)

def initVulkanObject(output_dir: str, output_file: str, target_api: str, merged_api: str|None):
    SetOutputDirectory(output_dir)
    SetOutputFileName(output_file)
    SetTargetApiName(target_api)
    SetMergedApiNames(merged_api)

    generator = MyGenerator()
    base_options = BaseGeneratorOptions()
    reg = Registry(generator, base_options)

    xml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'xml', 'vk.xml'))
    tree = ElementTree.parse(xml_path)
    reg.loadElementTree(tree)
    reg.apiGen()
    
    return generator.vk

# Test VulkanObject initialization
def testVulkanObject(tmp_path):
    initVulkanObject(tmp_path, "test_vulkan_object_out.txt", 'vulkan', None)

# Check class Member.alias is stored correctly when Member is from a feature structure
def testVulkanObjectStructFeatureAliasStore(tmp_path):
    vk = initVulkanObject(tmp_path, "test_vulkan_object_struct_member_aliases_store.txt", 'vulkan', None)

    struct1 = vk.structs["VkPhysicalDeviceShaderSubgroupRotateFeatures"]
    member1 = next(m for m in struct1.members if m.name == "shaderSubgroupRotate")
    assert member1.capabilityAlias is None

    struct2 = vk.structs["VkPhysicalDeviceVulkan14Features"]
    member2 = next(m for m in struct2.members if m.name == "shaderSubgroupRotate")
    assert member2.capabilityAlias == StructCapabilityAlias("VkPhysicalDeviceShaderSubgroupRotateFeatures", "shaderSubgroupRotate")

    struct3 = vk.structs["VkPhysicalDeviceVulkan12Features"]
    member3 = next(m for m in struct3.members if m.name == "subgroupBroadcastDynamicId")
    assert member3.capabilityAlias is None

    struct4 = vk.structs["VkPhysicalDeviceVulkan12Features"]
    member4 = next(m for m in struct4.members if m.name == "samplerMirrorClampToEdge")
    assert member4.capabilityAlias == ExtensionCapabilityAlias("VK_KHR_sampler_mirror_clamp_to_edge")

# Check class Member.alias is stored correctly when Member is from a property structure
def testVulkanObjectStructPropertyAliasStore(tmp_path):
    vk = initVulkanObject(tmp_path, "test_vulkan_object_feature_aliases.txt", 'vulkan', None)

    struct1 = vk.structs["VkPhysicalDeviceVertexAttributeDivisorProperties"]
    member1 = next(m for m in struct1.members if m.name == "maxVertexAttribDivisor")
    assert member1.capabilityAlias is None

    struct2 = vk.structs["VkPhysicalDeviceVulkan14Properties"]
    member2 = next(m for m in struct2.members if m.name == "maxVertexAttribDivisor")
    assert member2.capabilityAlias == StructCapabilityAlias("VkPhysicalDeviceVertexAttributeDivisorProperties", "maxVertexAttribDivisor")

    struct3 = vk.structs["VkPhysicalDeviceVulkan11Properties"]
    member3 = next(m for m in struct3.members if m.name == "subgroupQuadOperationsInAllStages")
    assert member3.capabilityAlias == StructCapabilityAlias("VkPhysicalDeviceSubgroupProperties", "quadOperationsInAllStages")

    struct4 = vk.structs["VkPhysicalDeviceSubgroupProperties"]
    member4 = next(m for m in struct4.members if m.name == "quadOperationsInAllStages")
    assert member4.capabilityAlias is None

    struct5 = vk.structs["VkPhysicalDeviceVulkan12Properties"]
    member5 = next(m for m in struct5.members if m.name == "framebufferIntegerColorSampleCounts")
    assert member5.capabilityAlias is None

def testVulkanObjectWithVideo(tmp_path):
    SetOutputDirectory(tmp_path)
    SetOutputFileName("test_vulkan_object_with_video_out.txt")
    SetTargetApiName('vulkan')
    SetMergedApiNames(None)

    generator = MyGenerator()
    base_options = BaseGeneratorOptions(
        videoXmlPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'xml', 'video.xml')))
    reg = Registry(generator, base_options)

    xml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'xml', 'vk.xml'))
    tree = ElementTree.parse(xml_path)
    reg.loadElementTree(tree)

    reg.apiGen()

def testVulkanObjectSC(tmp_path):
    SetOutputDirectory(tmp_path)
    SetOutputFileName("test_vulkan_object_sc_out.txt")
    SetTargetApiName('vulkansc')
    SetMergedApiNames('vulkan')

    generator = MyGenerator()
    base_options = BaseGeneratorOptions()
    reg = Registry(generator, base_options)

    xml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'xml', 'vk.xml'))
    tree = ElementTree.parse(xml_path)
    reg.loadElementTree(tree)
    reg.apiGen()

def testVulkanObjectWithVideoSC(tmp_path):
    SetOutputDirectory(tmp_path)
    SetOutputFileName("test_vulkan_object_with_video_sc_out.txt")
    SetTargetApiName('vulkansc')
    SetMergedApiNames('vulkan')

    generator = MyGenerator()
    base_options = BaseGeneratorOptions(
        videoXmlPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'xml', 'video.xml')))
    reg = Registry(generator, base_options)

    xml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'xml', 'vk.xml'))
    tree = ElementTree.parse(xml_path)
    reg.loadElementTree(tree)
    reg.apiGen()
