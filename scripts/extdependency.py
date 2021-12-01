#!/usr/bin/env python3
#
# Copyright 2017-2021 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

"""Generate a mapping of extension name -> all required extension names for
   that extension, from dependencies in the API XML."""

import argparse
import errno
import xml.etree.ElementTree as etree
from pathlib import Path

from apiconventions import APIConventions

class DiGraph:
    """A directed graph.

    The implementation and API mimic that of networkx.DiGraph in networkx-1.11.
    networkx implements graphs as nested dicts; it uses dicts all the way
    down, no lists.

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

        # Implementation detail: Do a breadth-first traversal because it is
        # easier than depth-first.

        # All nodes seen during traversal.
        seen = set()

        # The stack of nodes that need visiting.
        visit_me = []

        # Bootstrap the traversal.
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

class ApiDependencies:
    def __init__(self,
                 registry_path = None,
                 api_name = None):
        """Load an API registry and generate extension dependencies

        registry_path - relative filename of XML registry. If not specified,
        uses the API default.

        api_name - API name for which to generate dependencies. Only
        extensions supported for that API are considered.
        """

        if registry_path is None:
            registry_path = APIConventions().registry_path
        if api_name is None:
            api_name = APIConventions().xml_api_name

        self.allExts = set()
        self.khrExts = set()
        self.graph = DiGraph()
        self.extensions = {}
        self.tree = etree.parse(registry_path)

        # Loop over all supported extensions, creating a digraph of the
        # extension dependencies in the 'requires' attribute, which is a
        # comma-separated list of extension names. Also track lists of
        # all extensions and all KHR extensions.
        for elem in self.tree.findall('extensions/extension'):
            name = elem.get('name')
            supported = elem.get('supported')

            # This works for the present form of the 'supported' attribute,
            # which is a comma-separate list of XML API names
            if api_name in supported.split(','):
                self.allExts.add(name)

                if 'KHR' in name:
                    self.khrExts.add(name)

                deps = elem.get('requires')
                if deps:
                    for dep in deps.split(','):
                        self.graph.add_edge(name, dep)
                else:
                    self.graph.add_node(name)
            else:
                # Skip unsupported extensions
                pass

    def allExtensions(self):
        """Returns a set of all extensions in the graph"""
        return self.allExts

    def khrExtensions(self):
        """Returns a set of all KHR extensions in the graph"""
        return self.khrExts

    def children(self, extension):
        """Returns a set of the dependencies of an extension.
           Throws an exception if the extension is not in the graph."""

        if extension not in self.allExts:
            raise Exception(f'Extension {extension} not found in XML!')

        return set(self.graph.descendants(extension))


# Test script - takes about 0.05 seconds to load & process vk.xml
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-registry', action='store',
                        default=APIConventions().registry_path,
                        help='Use specified registry file instead of ' + APIConventions().registry_path)
    parser.add_argument('-loops', action='store',
                        default=20, type=int,
                        help='Number of timing loops to run')
    parser.add_argument('-test', action='store',
                        default=None,
                        help='Specify extension to find dependencies of')

    args = parser.parse_args()

    import time
    startTime = time.process_time()

    for loop in range(args.loops):
        deps = ApiDependencies(args.registry)

    endTime = time.process_time()

    deltaT = endTime - startTime
    print('Total time = {} time/loop = {}'.format(deltaT, deltaT / args.loops))
