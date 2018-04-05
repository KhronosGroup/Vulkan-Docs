#!/usr/bin/env python3
#
# Copyright (c) 2017-2018 The Khronos Group Inc.
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
# This updates config/extDependency.sh from the spec Makefile.
# It also defines lists of KHR extensions and all extensions for use in
# make frontend scripts such as 'makeAllExts'.

import argparse
import xml.etree.ElementTree as etree

def enQuote(key):
    return "'" + str(key) + "'"

# Return a sortable (list or set) of names as a string encoding
# of a Bash or Python list, sorted on the names.

def shList(names):
    s = ('"' +
         ' '.join([str(key) for key in sorted(names)]) +
         '"')
    return s

def pyList(names):
    s = ('[ ' +
         ', '.join([enQuote(key) for key in sorted(names)]) +
         ' ]')
    return s

class DiGraph:
    """A directed graph.

    The implementation and API mimic that of networkx.DiGraph in networkx-1.11.
    networkx implements graphs as nested dicts; it's dicts all the way down, no
    lists.

    Some major differences between this implementation and that of
    networkx-1.11 are:

        * This omits edge and node attribute data, because we never use them
          yet they add additional code complexity.

        * This returns iterator objects when possible instead of collection
          objects, because it simplifies the implementation and should provide
          better performance.
    """

    def __init__(self):
        self.__nodes = {}

    def add_node(self, node):
        if node not in self.__nodes:
            self.__nodes[node] = DiGraphNode()

    def add_edge(self, src, dest):
        self.add_node(src)
        self.add_node(dest)
        self.__nodes[src].adj.add(dest)

    def nodes(self):
        """Iterate over the nodes in the graph."""
        return self.__nodes.keys()

    def descendants(self, node):
        """
        Iterate over the nodes reachable from the given start node, excluding
        the start node itself. Each node in the graph is yielded at most once.
        """

        # Implementation detail: Do a breadth-first traversal because it's
        # easier than depth-first.

        # All nodes seen during traversal.
        seen = set()

        # The stack of nodes that need visiting.
        visit_me = []

        # Boostrap the traversal.
        seen.add(node)
        for x in self.__nodes[node].adj:
            if x not in seen:
                seen.add(x)
                visit_me.append(x)

        while visit_me:
            x = visit_me.pop()
            assert x in seen
            yield x

            for y in self.__nodes[x].adj:
                if y not in seen:
                    seen.add(y)
                    visit_me.append(y)

class DiGraphNode:

    def __init__(self):
        # Set of adjacent of nodes.
        self.adj = set()

# -extension name - may be a single extension name, a space-separated list
# of names, or a regular expression.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-registry', action='store',
                        default='vk.xml',
                        help='Use specified registry file instead of vk.xml')
    parser.add_argument('-outscript', action='store',
                        default=None,
                        help='Shell script to create')
    parser.add_argument('-outpy', action='store',
                        default=None,
                        help='Python script to create')
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
    g = DiGraph()

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
                    g.add_edge(name, dep)
            else:
                g.add_node(name)
        else:
            # Skip unsupported extensions
            True

    if args.outscript:
        fp = open(args.outscript, 'w', encoding='utf-8')

        print('#!/bin/bash', file=fp)
        print('# Generated from xml/extDependency.py', file=fp)
        print('# Specify maps of all extensions required by an enabled extension', file=fp)
        print('', file=fp)
        print('declare -A extensions', file=fp)

        # When printing lists of extensions, sort them sort the output script
        # remains as stable as possible as extensions are added to vk.xml.

        for ext in sorted(g.nodes()):
            children = list(g.descendants(ext))

            # Only emit an ifdef block if an extension has dependencies
            if len(children) > 0:
                print('extensions[' + ext + ']=' + shList(children), file=fp)

        print('', file=fp)
        print('# Define lists of all extensions and KHR extensions', file=fp)
        print('allExts=' + shList(allExts), file=fp)
        print('khrExts=' + shList(khrExts), file=fp)

        fp.close()

    if args.outpy:
        fp = open(args.outpy, 'w', encoding='utf-8')

        print('#!/usr/bin/env python', file=fp)
        print('# Generated from xml/extDependency.py', file=fp)
        print('# Specify maps of all extensions required by an enabled extension', file=fp)
        print('', file=fp)
        print('extensions = {}', file=fp)

        # When printing lists of extensions, sort them sort the output script
        # remains as stable as possible as extensions are added to vk.xml.

        for ext in sorted(g.nodes()):
            children = list(g.descendants(ext))

            # Only emit an ifdef block if an extension has dependencies
            if len(children) > 0:
                print("extensions['" + ext + "'] = " + pyList(children), file=fp)

        print('', file=fp)
        print('# Define lists of all extensions and KHR extensions', file=fp)
        print('allExts = ' + pyList(allExts), file=fp)
        print('khrExts = ' + pyList(khrExts), file=fp)

        fp.close()
