#!/usr/bin/python3
#
# Copyright (c) 2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Script to create symbolic links for aliases in reference pages
   Usage: makemanaliases.py -refdir refpage-output-directory"""

import argparse
import os
import sys

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-genpath', action='store',
                        default=None,
                        help='Path to directory containing generated *api.py module')
    parser.add_argument('-refdir', action='store',
                        required=True,
                        help='Path to directory containing reference pages to symlink')

    args = parser.parse_args()

    # Look for api.py in the specified directory
    if args.genpath is not None:
        sys.path.insert(0, args.genpath)
    import api

    # Change to refpage directory
    try:
        os.chdir(args.refdir)
    except:
        print('Cannot chdir to', args.refdir, file=sys.stderr)
        sys.exit(1)

    # For each alias in the API alias map, create a symlink if it
    # doesn't exist - and warn if it does exist.

    for key in api.alias:
        alias = key + '.html'
        src = api.alias[key] + '.html'

        if not os.access(src, os.R_OK):
            # This shouldn't happen, but is possible if the api module isn't
            # generated for the same set of APIs as were the refpages.
            print('No source file', src, file=sys.stderr)
            continue

        if os.access(alias, os.R_OK):
            # If the link already exists, that's not necc. a problem, so
            # don't fail, but it should be checked out
            print('Unexpected alias file "' + alias + '" exists, skipping',
                  file=sys.stderr)
        else:
            # Create link from alias refpage to page for what it's aliasing
            os.symlink(src, alias)
