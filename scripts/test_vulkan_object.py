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