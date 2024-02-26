#!/usr/bin/python3
#
# Copyright 2022-2024 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

"""Used to generate the Antora `nav.adoc` for the Vulkan spec proposals module.

Usage: `antora-nav-proposals.py [-root path] -component path [-roadmap path] [-template path] files`

- `-root` is the root path (repository root, usually) relative to which spec
  files are processed. Defaults to current directory if not specified.
- `-component` is the path to the module and component in which converted
  files are written (e.g. the component directory under which pages/,
  partials/, images/, etc. are located).
- `-navfile` is the filename (not path) of the navigation file, and defaults
  to `nav.adoc` if not present
- `-roadmappath` is the path to the Vulkan Roadmap, which is grouped
  separately from the individual extension proposals.
- `-templatepath` is the path to the proposal template, which is grouped
  separately from the individual extension proposals.
- Remaining arguments are paths to individual proposals.

The only file generated is `component`/nav.adoc, which is the top-level
navigation file for the module.
All the input paths are turned into links within nav.adoc.
"""

import argparse
import importlib
import os
import sys
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-root', action='store', dest='root',
                        default=os.getcwd(),
                        help='Specify root directory under which files are located (default current directory)')
    parser.add_argument('-component', action='store', dest='component',
                        required=True,
                        help='Specify module / component directory in which the proposal navigation file "nav.adoc" is written')
    parser.add_argument('-navfile', action='store', dest='navfile',
                        default='nav.adoc', required=False,
                        help='Specify filename of proposal module navigation file (default nav.adoc)')
    parser.add_argument('-roadmappath', action='store', dest='roadmappath',
                        default=None, required=False,
                        help='Specify path to Roadmap.adoc containing the Vulkan 2022 Roadmap')
    parser.add_argument('-templatepath', action='store', dest='templatepath',
                        default=None, required=False,
                        help='Specify path to the template.adoc used to create new proposals')
    parser.add_argument('files', metavar='filename', nargs='*',
                        help='Specify name of a single extension proposal to index')

    args = parser.parse_args()

    args.root = os.path.abspath(args.root)
    args.component = os.path.abspath(args.component)

    # Write the navigation file
    path = Path(args.component) / args.navfile

    try:
        fp = open(path, 'w', encoding='utf8')
    except:
        raise RuntimeError(f'Cannot write navigation file {path}')

    # Boilerplate

    print('// Copyright 2024 The Khronos Group Inc.', file=fp)
    print('// {}-License-Identifier: CC-BY-4.0\n'.format('SPDX'), file=fp)
    print(':chapters:\n', file=fp)
    print('* xref:index.adoc[Vulkan Proposals]', file=fp)

    # Roadmap
    if args.roadmappath is not None:
        print('* Vulkan Roadmap', file=fp)
        relpath = os.path.relpath(os.path.abspath(args.roadmappath), args.root)
        print(f'** xref:{relpath}[]', file=fp)

    # Individual extension proposals
    print('* Extension Proposals', file=fp)
    proposals = set()
    for filename in args.files:
        relpath = os.path.relpath(os.path.abspath(filename), args.root)
        proposals.add(relpath)
    for relpath in sorted(proposals):
        print(f'** xref:{relpath}[]', file=fp)

    # Template
    if args.templatepath is not None:
        print('* Extension Proposal Template', file=fp)
        relpath = os.path.relpath(os.path.abspath(args.templatepath), args.root)
        print(f'** xref:{relpath}[]', file=fp)

    fp.close()

