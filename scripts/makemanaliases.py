#!/usr/bin/python3
#
# Copyright 2020-2023 The Khronos Group Inc.
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
                        help='Path to directory containing generated apimap.py module')
    parser.add_argument('-refdir', action='store',
                        required=True,
                        help='Path to directory containing reference pages to symlink')

    args = parser.parse_args()

    # Look for apimap.py in the specified directory
    if args.genpath is not None:
        sys.path.insert(0, args.genpath)
    import apimap as api

    # Change to refpage directory
    try:
        os.chdir(args.refdir)
    except:
        print('Cannot chdir to', args.refdir, file=sys.stderr)
        sys.exit(1)

    # For each alias in the API alias map, create a symlink if it
    # does not exist - and warn if it does exist.

    for key in api.alias:
        if key.endswith(('_EXTENSION_NAME', '_SPEC_VERSION')):
            # No reference pages are generated for these meta-tokens, so
            # attempts to alias them will fail. Silently skip them.
            continue

        alias = key + '.html'
        src = api.alias[key] + '.html'

        if not os.access(src, os.R_OK):
            # This should not happen, but is possible if the api module is
            # not generated for the same set of APIs as were the refpages.
            print('No source file', src, file=sys.stderr)
            continue

        if os.access(alias, os.R_OK):
            # If the link already exists, that is not necessarily a
            # problem, so do not fail, but it should be checked out.
            # The usual case for this is not cleaning the target directory
            # prior to generating refpages.
            print('Unexpected alias file "' + alias + '" exists, skipping',
                  file=sys.stderr)
        else:
            # Create link from alias refpage to page for what it is aliasing
            os.symlink(src, alias)
