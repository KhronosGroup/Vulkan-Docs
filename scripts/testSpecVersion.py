#!/usr/bin/env python3
#
# Copyright 2017-2026 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# testSpecVersion - check if SPEC_VERSION values for an unpublished
# extension branch meet the requirement of being >= 1.
#
# Usage: testSpecVersion.py [-branch branchname] [-canonicalize] [-check_spec_version] [-registry file]
#
# Checks for an XML <extension> tag corresponding to a branch name
# - If -branch is specified, use that branch name.
#   Otherwise, use the current git branch.
# - If -canonicalize is specified, prints the non-disabled extension name
#   corresponding to the branch name if it exists; otherwise print nothing.
# - If -registry is specified, use that XML registry.
#   Otherwise, use 'xml/vk.xml'
#
# If -canonicalize is not specified, tries to validate the SPEC_VERSION
# token of an extension development branch:
# - If there is no non-disabled extension corresponding to the branch name,
#   succeed.
# - If the extension has a SPEC_VERSION value >= 1, succeed.
# - Otherwise, fail.
#
# Note that the SPEC_VERSION requirement is deeply buried down in the
# "Required Extension Tokens" section of the style guide and actually says
# "This value begins at 1 when an extension specification is first
# published".
# This is a difficult ask since it is hard to determine "first published" in
# an un-merged and hence un-published branch, hence we only require it be a
# positive integer.

import argparse
import sys
import xml.etree.ElementTree as etree
from reflib import getBranch

# Dictionary mapping branch names not following the 'extension branch ==
# extension name' requirement, to a list containing one or more real
# extension names contained in the branch.
# If you have such a branch, you can add an entry for it below.
# This example treats branch name '3955-ci' as enabled extension
# VK_KHR_xlib_surface, and the spec_extension_branch_check stage should
# succeed.
remapBranchName = {
    '3955-ci' : [ 'VK_KHR_xlib_surface' ],
    'jbolz_coopmat2' : [ 'VK_NV_cooperative_matrix2' ],
    'VK_NV_vertex_attribute_robustness' : [ 'VK_EXT_vertex_attribute_robustness' ],
    'VK_NV_4_Extensions' : [
        'VK_NV_cooperative_vector',
        'VK_NV_cluster_acceleration_structure',
        'VK_NV_partitioned_acceleration_structure',
        'VK_NV_ray_tracing_linear_swept_spheres' ],
    'cooperative_vector' : [ 'VK_NV_cooperative_vector' ],
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-branch', action='store',
                        default=None,
                        help='Specify branch to check against (defaults to current branch name)')
    parser.add_argument('-build', action='store_true',
                        help='Build a test specification including extensions for this branch')
    parser.add_argument('-build_log', action='store_true',
                        help='Print output log from build test')
    parser.add_argument('-canonicalize', action='store_true',
                        help='Return canonical extension name corresponding to branch name, or empty string if extension does not exist.')
    parser.add_argument('-test', action='store_true',
                        help='Test SPEC_VERSION values for extensions for this branch')
    parser.add_argument('-registry', action='store',
                        default='xml/vk.xml',
                        help='Use specified registry file instead of vk.xml')
    args = parser.parse_args()

    # Determine current git branch name, if not specified in arguments
    errors = ''
    if args.branch is None:
        (args.branch, errors) = getBranch()

        if args.branch is None:
            print('ERROR - Cannot determine current git branch - please specify explicitly with the -branch option:', errors, file=sys.stderr)
            sys.exit(1)

    # Determine canonical extension name(s) corresponding to the branch name
    if args.branch in remapBranchName:
        extensions = remapBranchName[args.branch]
        print(f'Remapping branch {args.branch} to {extensions}', file=sys.stderr)
    else:
        extensions = [ args.branch ]

    # Look up the extension names in XML
    try:
        tree = etree.parse(args.registry)
    except:
        print(f'ERROR - cannot open registry XML file {args.registry}')
        sys.exit(1)

    success = True
    valid_extensions = True

    # Validate SPEC_VERSION values for the extension(s)
    if args.test:
        print(f'Checking SPEC_VERSION values for specified branch')

        for extension in extensions:
            elem = tree.find(f'extensions/extension[@name="{extension}"]')

            if elem == None:
                print(f'"{extension}" is not an extension name, not running SPEC_VERSION or build tests')
                valid_extensions = False
                continue

            if elem.get('supported') == 'disabled':
                print(f'"{extension}" is a disabled extension, not running SPEC_VERSION or build tests')
                valid_extensions = False
                continue

            found_spec_version = False

            for enum in elem.findall('require/enum'):
                name = enum.get('name')

                if name is not None and name[-13:] == '_SPEC_VERSION':
                    found_spec_version = True

                    value = int(enum.get('value'))
                    if value >= 1:
                        print(f'{name} = {value} for {extension}, as expected')
                        break
                    else:
                        print(f"ERROR: {name} = {enum.get('value')} for {extension}, but must be >= 1")
                        success = False
                        break

            if not found_spec_version:
                print(f'ERROR: no SPEC_VERSION token found for {extension}')
                success = False

    # Validate spec build
    if args.build and valid_extensions:
        import subprocess

        # Construct command string to execute for a spec build
        command = [ './makeSpec',
                    '-clean',
                    '-spec',
                    'core',
                    'html',
                  ]
        for extension in extensions:
            command.append('-extension')
            command.append(extension)

        print('Testing spec build with branch extension(s) included:')
        print(' '.join(command))

        # Execute it
        results = subprocess.run(command,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)

        # Only mark a failure if the return code was nonzero
        if results.returncode != 0:
            print(f'Test build failed with status {results.returncode}.')
            success = False

        if args.build_log:
            if len(results.stdout) > 0:
                print(f'Output from spec build:\n{results.stdout.decode()}')
            if len(results.stderr) > 0:
                print(f'stderr output from spec build:\n{results.stderr.decode()}')

    # Fail the script if some part of it failed
    if not success:
        print(f'testSpecVersion.py failed')
        sys.exit(1)
    else:
        print(f'testSpecVersion.py passed')
        sys.exit(0)
