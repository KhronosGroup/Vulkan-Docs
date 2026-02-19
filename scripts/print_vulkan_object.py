#!/usr/bin/env python3 -i
#
# Copyright 2026 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0 OR MIT
import os
import sys
from xml.etree import ElementTree
import pprint
import tempfile
import argparse

registry_path = os.path.abspath((os.path.dirname(__file__)))
sys.path.insert(0, registry_path)
from reg import Registry
from base_generator import *
from vulkan_object import *

global output_file

class MyGenerator(BaseGenerator):
    def __init__(self):
        BaseGenerator.__init__(self)

    def generate(self):
        with open(output_file, "w") as f:
            pprint.pprint(self.vk, stream=f, indent=2, width=1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Print VulkanObject contents to be compared')
    # Require because it will be about 70MB of text, no reason to print to stdout
    parser.add_argument('-o', required=True, help='file to print to', dest='output_file')
    args = parser.parse_args(sys.argv[1:])
    output_file = args.output_file

    with tempfile.TemporaryDirectory() as tmp_dir:
        SetOutputDirectory(tmp_dir)
        SetOutputFileName("workaround.txt") # to allow use to invoke VulkanObject
        SetTargetApiName('vulkan')
        SetMergedApiNames(None)

        generator = MyGenerator()
        base_options = BaseGeneratorOptions()
        reg = Registry(generator, base_options)

        xml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'xml', 'vk.xml'))
        tree = ElementTree.parse(xml_path)
        reg.loadElementTree(tree)
        reg.apiGen()
