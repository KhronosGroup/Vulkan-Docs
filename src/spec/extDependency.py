#!/usr/bin/python3
#
# Copyright (c) 2017 The Khronos Group Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# extDependency - generate a mapping of extension name -> all required
# extension names for that extension.
#
# This is run only rarely, when adding a new extension, and updates
# doc/specs/vulkan/config/extDependency.sh from the spec Makefile.
# It also defines lists of KHR extensions and all extensions for use in make
# frontend scripts in doc/specs/vulkan.

import argparse
import xml.etree.ElementTree as etree
import networkx as nx

# -extension name - may be a single extension name, a space-separated list
# of names, or a regular expression.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-registry', action='store',
                        default='vk.xml',
                        help='Use specified registry file instead of vk.xml')
    parser.add_argument('-test', action='store',
                        default=None,
                        help='Specify extension to find dependencies of')
    parser.add_argument('-quiet', action='store_true', default=False,
                        help='Suppress script output during normal execution.')

    args = parser.parse_args()

    tree = etree.parse(args.registry)

    # Loop over all supported extensions, creating a digraph of the
    # extension dependencies in the 'requires' attribute, which is a
    # comma-separated list of extension names. Also track lists of
    # all extensions and all KHR extensions.

    allExts = set()
    khrExts = set()
    g = nx.DiGraph()

    for elem in tree.findall('extensions/extension'):
        name = elem.get('name')
        supported = elem.get('supported')

        if (supported == 'vulkan'):
            allExts.add(name)
            if ('KHR' in name):
                khrExts.add(name)

            if ('requires' in elem.attrib):
                deps = elem.get('requires').split(',')

                for dep in deps:
                    g.add_path([name, dep])
            else:
                g.add_node(name)
        else:
            # Skip unsupported extensions
            True

    print('#!/bin/bash')
    print('# Generated from src/spec/extDependency.py')
    print('# Specify maps of all extensions required by an enabled extension')
    print('')
    print('declare -A extensions')

    # When printing lists of extensions, sort them sort the output script
    # remains as stable as possible as extensions are added to vk.xml.

    for ext in sorted(g.nodes()):
        children = nx.descendants(g, ext)

        # Only emit an ifdef block if an extension has dependencies
        if len(children) > 0:
            print('extensions[' + ext + ']="' + ' '.join(sorted(children)) + '"')

    print('')
    print('# Define lists of all extensions and all KHR extensions')
    print('allExts="' + ' '.join([str(k) for k in sorted(allExts)]) + '"')
    print('khrExts="' + ' '.join([str(k) for k in sorted(khrExts)]) + '"')
