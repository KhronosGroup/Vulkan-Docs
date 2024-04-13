#!/usr/bin/env python3
#
# Copyright 2017-2024 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

"""Generate a mapping of extension name -> all required extension names for
   that extension, from dependencies in the API XML."""

import argparse
import errno
import xml.etree.ElementTree as etree
from pathlib import Path

from apiconventions import APIConventions
from parse_dependency import dependencyNames

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

        conventions = APIConventions()
        if registry_path is None:
            registry_path = conventions.registry_path
        if api_name is None:
            api_name = conventions.xml_api_name

        self.allExts = set()
        self.khrExts = set()
        self.ratifiedExts = set()
        self.graph = DiGraph()
        self.extensions = {}
        self.tree = etree.parse(registry_path)

        # Loop over all supported extensions, creating a digraph of the
        # extension dependencies in the 'depends' attribute, which is a
        # boolean expression of core version and extension names.
        # A static dependency tree can be constructed only by treating all
        # extension names in the expression as dependencies, even though
        # that may not be true if it is of form (ext OR ext).
        # For the purpose these dependencies are used for - generating
        # specifications with required dependencies included automatically -
        # this will suffice.
        # Separately tracks lists of all extensions and all KHR extensions,
        # which are common specification targets.
        for elem in self.tree.findall('extensions/extension'):
            name = elem.get('name')
            supported = elem.get('supported')
            ratified = elem.get('ratified', '')

            if api_name in supported.split(','):
                self.allExts.add(name)

                if conventions.KHR_prefix in name:
                    self.khrExts.add(name)

                if api_name in ratified.split(','):
                    self.ratifiedExts.add(name)

                self.graph.add_node(name)

                depends = elem.get('depends')
                if depends:
                    # Walk a list of the leaf nodes (version and extension
                    # names) in the boolean expression.
                    for dep in dependencyNames(depends):
                        # Filter out version names, which are explicitly
                        # specified when building a specification.
                        if not conventions.is_api_version_name(dep):
                            self.graph.add_edge(name, dep)
            else:
                # Skip unsupported extensions
                pass

    def allExtensions(self):
        """Returns a set of all extensions in the graph"""
        return self.allExts

    def khrExtensions(self):
        """Returns a set of all KHR extensions in the graph"""
        return self.khrExts

    def ratifiedExtensions(self):
        """Returns a set of all ratified extensions in the graph"""
        return self.ratifiedExts

    def children(self, extension):
        """Returns a set of the dependencies of an extension.
           Throws an exception if the extension is not in the graph."""

        if extension not in self.allExts:
            raise Exception(f'Extension {extension} not found in XML!')

        return set(self.graph.descendants(extension))


# Test script
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-registry', action='store',
                        default=APIConventions().registry_path,
                        help='Use specified registry file instead of ' + APIConventions().registry_path)
    parser.add_argument('-loops', action='store',
                        default=10, type=int,
                        help='Number of timing loops to run')
    parser.add_argument('-test', action='store',
                        default=None,
                        help='Specify extension to find dependencies of')

    args = parser.parse_args()

    deps = ApiDependencies(args.registry)
    print('KHR exts =', sorted(deps.khrExtensions()))
    print('Ratified exts =', sorted(deps.ratifiedExtensions()))

    import time
    startTime = time.process_time()

    for loop in range(args.loops):
        deps = ApiDependencies(args.registry)

    endTime = time.process_time()

    deltaT = endTime - startTime
    print('Total time = {} time/loop = {}'.format(deltaT, deltaT / args.loops))
