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
global verbose

# Top-level named entity types: when encountered as embedded references inside
# another entity, print only the class name and .name instead of full contents.
_ENTITY_TYPES = (
    Version, Extension, Handle, Command, Struct,
    Enum, Bitmask, Flags, Constant, Format, FuncPointer,
    SyncStage, SyncAccess, SyncPipeline, Spirv,
)

class _CompactPrinter(pprint.PrettyPrinter):
    """PrettyPrinter that collapses embedded entity references to a one-liner.

    Top-level entity objects (depth == 0 when first encountered) are printed in
    full.  The same entity types appearing as fields inside another entity are
    printed as e.g. Version('VK_VERSION_1_1') to avoid repeating their contents
    throughout the file.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._entity_depth = 0  # >0 means we are currently inside an entity

    def _pprint_dataclass(self, object, stream, indent, allowance, context, level):
        if isinstance(object, _ENTITY_TYPES):
            if self._entity_depth > 0:
                # Compact reference: just print the type and name
                name = getattr(object, 'name', None)
                label = repr(name) if name is not None else '?'
                stream.write(f'{object.__class__.__name__}({label})')
                return
            self._entity_depth += 1
            try:
                super()._pprint_dataclass(object, stream, indent, allowance, context, level)
            finally:
                self._entity_depth -= 1
        else:
            super()._pprint_dataclass(object, stream, indent, allowance, context, level)


class MyGenerator(BaseGenerator):
    def __init__(self):
        BaseGenerator.__init__(self)

    def generate(self):
        # Sort things here to ensure moving things around the XML do not change things
        self.vk.extensions = sorted(self.vk.extensions)
        self.vk.versions = sorted(self.vk.versions)
        self.vk.handles = sorted(self.vk.handles)
        self.vk.commands = sorted(self.vk.commands)
        self.vk.structs = sorted(self.vk.structs)
        self.vk.enums = sorted(self.vk.enums)
        self.vk.bitmasks = sorted(self.vk.bitmasks)
        self.vk.flags = sorted(self.vk.flags)
        self.vk.constants = sorted(self.vk.constants)
        self.vk.formats = sorted(self.vk.formats)
        self.vk.funcPointers = sorted(self.vk.funcPointers)
        self.vk.aliasTypeRequirements = sorted(self.vk.aliasTypeRequirements)
        self.vk.aliasFieldRequirements = sorted(self.vk.aliasFieldRequirements)
        self.vk.aliasFlagRequirements = sorted(self.vk.aliasFlagRequirements)

        with open(output_file, "w") as f:
            if verbose:
                pprint.pprint(self.vk, stream=f, indent=2, width=1)
            else:
                printer = _CompactPrinter(stream=f, indent=2, width=120)
                printer.pprint(self.vk)

if __name__ == '__main__':
    default_xml = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'xml', 'vk.xml'))

    parser = argparse.ArgumentParser(description='Print VulkanObject contents to be compared')
    # Require because it will be about 70MB of text, no reason to print to stdout
    parser.add_argument('-o', required=True, help='file to print to', dest='output_file')
    parser.add_argument('-verbose', action='store_true', default=False,
                        help='use verbose output (full expansion of all embedded objects)',
                        dest='verbose')
    parser.add_argument('-api', default='vulkan', choices=['vulkan', 'vulkansc', 'vulkanbase'],
                        help='target API (default: vulkan)', dest='api')
    parser.add_argument('-xml', default=default_xml, help='path to XML registry (default: xml/vk.xml)',
                        dest='xml')
    args = parser.parse_args(sys.argv[1:])
    output_file = args.output_file
    verbose = args.verbose

    with tempfile.TemporaryDirectory() as tmp_dir:
        SetOutputDirectory(tmp_dir)
        SetOutputFileName("workaround.txt") # to allow use to invoke VulkanObject
        SetTargetApiName(args.api)
        SetMergedApiNames(None)

        generator = MyGenerator()
        base_options = BaseGeneratorOptions()
        reg = Registry(generator, base_options)

        tree = ElementTree.parse(args.xml)
        reg.loadElementTree(tree)
        reg.apiGen()
