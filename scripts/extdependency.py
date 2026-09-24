#!/usr/bin/env python3
#
# Copyright 2017-2026 The Khronos Group Inc.
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

        self.conventions = APIConventions()
        if registry_path is None:
            registry_path = self.conventions.registry_path
        if api_name is None:
            api_name = self.conventions.xml_api_name

        # Sets of all, KHR, and ratified extensions
        self.allExts = set()
        self.khrExts = set()
        self.ratifiedExts = set()
        # Sets of extensions for each platform, keyed by platform name.
        self.platformExts = {}
        self.versions = set()
        self.graph = DiGraph()
        self.extensions = {}
        self.tree = etree.parse(registry_path)

        # Loop over all supported features (versions)
        for elem in self.tree.findall('feature'):
            name = elem.get('name')
            api = elem.get('api')

            if api_name in api.split(','):
                self.versions.add(name)

                self.graph.add_node(name)
                depends = elem.get('depends')
                if depends:
                    for dep in dependencyNames(depends):
                        self.graph.add_edge(name, dep)

        # All <platform> tags are included, although the sets are empty if
        # no extensions are tagged for that platform.
        # This is needed so that we continue to generate (empty) headers for
        # VulkanSC.
        for elem in self.tree.findall('platforms/platform'):
            name = elem.get('name')
            protect = elem.get('protect')
            self.platformExts[name] = set()

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
            platform = elem.get('platform', None)

            if api_name in supported.split(','):
                self.allExts.add(name)

                if self.conventions.KHR_prefix in name:
                    self.khrExts.add(name)

                if api_name in ratified.split(','):
                    self.ratifiedExts.add(name)

                # Track names of extensions in each platform separately
                if platform is not None:
                    if platform not in self.platformExts:
                        raise Exception(f'Extension {name} is tagged for platform {platform}, which is not in the XML')
                    self.platformExts[platform].add(name)

                self.graph.add_node(name)

                depends = elem.get('depends')
                if depends:
                    # Walk a list of the leaf nodes (version and extension
                    # names) in the boolean expression.
                    for dep in dependencyNames(depends):
                        # Filter out version names, which are explicitly
                        # specified when building a specification.
                        if not self.conventions.is_api_version_name(dep):
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

    def allVersions(self):
        """Returns a set of all versions in the graph"""
        return self.versions

    def children(self, extension):
        """Returns a set of the direct and indirect dependencies of an
           extension.
           Throws an exception if the extension is not in the dependency
           graph."""

        if extension not in self.allExts:
            raise Exception(f'Extension {extension} not found in XML!')

        return set(self.graph.descendants(extension))

    def interactions(self, extension):
        """Returns a set of the direct interactions of an extension.
           These are from depends attributes of the <extension> and its
           <require> tags.
           Throws an exception if the extension is not in the graph."""

        if extension not in self.allExts:
            raise Exception(f'Extension {extension} not found in XML!')

        interactions = set()

        ext_elem = self.tree.find(f"extensions/extension[@name='{extension}']")
        if ext_elem is None:
            return interactions

        def add_depends(dependset, dependexpr):
            if dependexpr is not None:
                for depname in dependencyNames(dependexpr):
                    # Filter out version names, which are explicitly
                    # specified when building a specification.
                    if not self.conventions.is_api_version_name(depname):
                        dependset.add(depname)

        # <extension depends=>
        add_depends(interactions, ext_elem.get('depends'))
        # <require depends=>
        for elem in ext_elem.findall('require'):
            add_depends(interactions, elem.get('depends'))

        return interactions

    def versionChildren(self, version):
        """Returns a set of the dependencies of a version.
           Throws an exception if the version is not in the graph."""

        if version not in self.versions:
            raise Exception(f'Version {version} not found in XML!')

        return set(self.graph.descendants(version))


# Test script
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-registry', action='store',
                        default=APIConventions().registry_path,
                        help=f'Use specified registry file instead of {APIConventions().registry_path}')
    parser.add_argument('-loops', action='store',
                        default=0, type=int,
                        help='Number of timing loops to run')

    args = parser.parse_args()

    deps = ApiDependencies(args.registry)
    print('KHR exts =', sorted(deps.khrExtensions()))
    print('Ratified exts =', sorted(deps.ratifiedExtensions()))
    print('Platforms =', sorted(deps.platformExts.keys()))

    print('platforms = [')

    for platform in sorted(deps.platformExts):
        alldeps = set()
        exts = set(deps.platformExts[platform])

        # print(f'Platform {platform} has direct interactions:')
        for ext in sorted(exts):
            interactions = deps.interactions(ext)
            if len(interactions) > 0:
                alldeps |= interactions
                # print(f'    {ext} -> {interactions}')

        # Remove interactions which are in the set of platform extensions
        alldeps -= exts

        # print(f'    All platform interactions = {sorted(alldeps)}')

        if platform == 'provisional':
            filename = 'vulkan_beta.h'
        else:
            filename = f'vulkan_{platform}.h'

        print(f"    [ '{filename}',")
        print(f"      {exts},")
        print(f"      {alldeps - exts} ],")

    if args.loops > 0:
        import time
        startTime = time.process_time()

        for loop in range(args.loops):
            deps = ApiDependencies(args.registry)

        endTime = time.process_time()

        deltaT = endTime - startTime
        print(f'Total time = {deltaT} time/loop = {deltaT / args.loops}')
