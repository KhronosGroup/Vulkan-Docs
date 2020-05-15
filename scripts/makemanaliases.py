#!/usr/bin/python3
#
# Copyright (c) 2020 The Khronos Group Inc.
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
