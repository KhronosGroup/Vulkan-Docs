#!/usr/bin/python3
#
# Copyright 2017-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# testSpecVersion - check if SPEC_VERSION values for an unpublished
# extension branch meet the requirement of being 1.
#
# Usage: textSpecVersion.py [-branch branchname] [-registry file]
#
# Checks for an XML <extension> matching the branch name specified
# on the command line, or the current branch if not specified.
#
# If not found, the branch is not an extension staging branch; succeed.
# If found, but extension is disabled, don't run the test; succeed.
# If found, and extension SPEC_VERSION has a value of '1', succeed.
# Otherwise, fail.

import argparse
import sys
import xml.etree.ElementTree as etree
from reflib import getBranch

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-branch', action='store',
                        default=None,
                        help='Specify branch to check against')
    parser.add_argument('-registry', action='store',
                        default='xml/vk.xml',
                        help='Use specified registry file instead of vk.xml')
    args = parser.parse_args()

    try:
        tree = etree.parse(args.registry)
    except:
        print('ERROR - cannot open registry XML file', args.registry)
        sys.exit(1)

    errors = ''
    if args.branch is None:
        (args.branch, errors) = getBranch()
    if args.branch is None:
        print('ERROR - Cannot determine current git branch:', errors)
        sys.exit(1)

    elem = tree.find('extensions/extension[@name="' + args.branch + '"]')

    if elem == None:
        print('Success - assuming', args.branch, 'is not an extension branch')
        sys.exit(0)

    supported = elem.get('supported')
    if supported == 'disabled':
        print('Success - branch name', args.branch, 'matches, but extension is disabled')
        sys.exit(0)

    for enum in elem.findall('require/enum'):
        name = enum.get('name')

        if name is not None and name[-13:] == '_SPEC_VERSION':
            value = enum.get('value')
            if value == '1':
                print('Success - {} = 1 for branch {}'.format(
                      name, args.branch))
                sys.exit(0)
            else:
                print('ERROR - {} = {} for branch {}, but must be 1'.format(
                      name, value, args.branch))
                sys.exit(1)

    print('ERROR - no SPEC_VERSION token found for branch', args.branch)
    sys.exit(1)
