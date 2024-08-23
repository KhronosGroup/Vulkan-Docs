#!/usr/bin/env python3
#
# Copyright 2017-2024 The Khronos Group Inc.
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
# extension name' requirement, to a real extension name.
# If you have such a branch, you can add an entry for it below.
# This example treats branch name '3955-ci' as enabled extension
# VK_KHR_xlib_surface, and the spec_extension_branch_check stage should
# succeed.
remapBranchName = {
    '3955-ci' : 'VK_KHR_xlib_surface'
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-branch', action='store',
                        default=None,
                        help='Specify branch to check against (defaults to current branch name)')
    parser.add_argument('-canonicalize', action='store_true',
                        help='Return canonical extension name corresponding to branch name, or empty string if extension does not exist.')
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

    # Determine canonical extension name corresponding to the branch name
    if args.branch in remapBranchName:
        extension = remapBranchName[args.branch]
        print(f'Remapping branch {args.branch} to extension {extension}', file=sys.stderr)
    else:
        extension = args.branch

    # Look up the extension name in XML
    try:
        tree = etree.parse(args.registry)
    except:
        print(f'ERROR - cannot open registry XML file {args.registry}')
        sys.exit(1)

    elem = tree.find(f'extensions/extension[@name="{extension}"]')

    # Just print the extension name, if it is supported
    if args.canonicalize:
        if elem != None:
            print(extension)
        sys.exit(0)

    if elem == None:
        print(f'Success - branch "{extension}" is not an extension name, not running SPEC_VERSION test')
        sys.exit(0)

    if elem.get('supported') == 'disabled':
        print(f'Success - branch "{extension}" is a disabled extension, not running SPEC_VERSION test')
        sys.exit(0)

    for enum in elem.findall('require/enum'):
        name = enum.get('name')

        if name is not None and name[-13:] == '_SPEC_VERSION':
            value = int(enum.get('value'))
            if value >= 1:
                print(f'Success - {name} = {value} for {extension}')
                sys.exit(0)
            else:
                print(f"ERROR - {name} = {enum.get('value')} for {extension}, but must be >= 1")
                sys.exit(1)

    print(f'ERROR - no SPEC_VERSION token found for {extension}')
    sys.exit(1)
