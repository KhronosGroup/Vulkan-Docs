#!/usr/bin/env python3 -i
#
# Copyright 2025 The Khronos Group Inc.
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
        for extension in self.vk.extensions.values():
            assert isinstance(extension, Extension)
            for special in extension.specialUse:
                assert isinstance(special, str)
            for handle in extension.handles:
                assert isinstance(handle, Handle)
            for command in extension.commands:
                assert isinstance(command, Command)
            for enum in extension.enums:
                assert isinstance(enum, Enum)
            for bitmask in extension.bitmasks:
                assert isinstance(bitmask, Bitmask)
            for flags in extension.flags.values():
                for flag in flags:
                    assert isinstance(flag, Flags)
            for enumFields in extension.enumFields.values():
                for enum in enumFields:
                    assert isinstance(enum, EnumField)
            for flagBits in extension.flagBits.values():
                for flag in flagBits:
                    assert isinstance(flag, Flag)

def testVulkanObject(tmp_path):
    SetOutputDirectory(tmp_path)
    SetOutputFileName("test_vulkan_object_out.txt")
    SetTargetApiName('vulkan')
    SetMergedApiNames(None)

    generator = MyGenerator()
    base_options = BaseGeneratorOptions()
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