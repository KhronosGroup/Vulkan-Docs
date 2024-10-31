#!/usr/bin/env python3
#
# Copyright 2024 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

"""add_validusage_pages.py - adds 'page' key content to validusage.json
   based on the generated xrefMap and pageMap files.

Usage: add_validusage_pages.py -xrefmap path -pagemap path -validusage path

- -xrefmap is the path to xrefMap.py, an externally generated dictionary
  containing a map of asciidoc anchors in the spec markup to anchors of the
  pages (spec chapters and appendices) they appear in.
- -pagemap is the path to pageMap.py, an externally generated dictionary
  containing a map of page anchors to paths in the Antora document source
  tree they correspond to.
- -validusage is the path to a validusage.json file. The file is overwritten
  by adding a path to the 'page' key for each VU statement, allowing
  converting a Vulkan VUID into a link to the docs.vulkan.org page where
  that VUID is defined.

NOTE: the validusage file is always overwritten, in a non-destructive
fashion since the 'page' key is otherwise empty.
If you do not want this behavior, make a copy before running this script and
specify that copy.
"""

# For error and file-loading interfaces only
import argparse
import importlib
import json
import os
import re
import sys
from generator import enquote
from reflib import loadFile, logDiag, logWarn, logErr, setLogFile, getBranch
from pathlib import Path

titleAnchorPat = re.compile(r'^\[\[(?P<anchor>[^,]+).*\]\]$')
titlePat = re.compile(r'^[=#] (?P<title>[A-Z].*)')
subtitlePat = re.compile(r'^[=#]{2,} (?P<title>[A-Z].*)')

Pages = 'pages'
Partials = 'partials'
Images = 'images'

def undefquote(s, default='undefined'):
    """Quote a string, or return a default value if the string is None."""

    if s is not None:
        return enquote(s)
    else:
        return 'undefined'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-xrefmap', action='store', dest='xrefmap',
                        default=None, required=True,
                        help='Specify path to xrefMap.py containing map of anchors to chapter anchors')
    parser.add_argument('-pagemap', action='store', dest='pagemap',
                        default=None, required=True,
                        help='Specify path to pageMap.py containing map of chapter anchors to Antora filenames')
    parser.add_argument('-validusage', action='store',
                        default=None, required=True,
                        help='Specify path to validusage.json file to rewrite in place')

    args = parser.parse_args()

    # Import the xrefmap and pagemap
    def importFileModule(file):
        """importFileModule - import file as a module and return that module"""

        (path, file) = os.path.split(file)
        (module, extension) = os.path.splitext(file)
        sys.path.append(path)

        return importlib.import_module(module)

    try:
        xrefMap = importFileModule(args.xrefmap).xrefMap
    except:
        print(f'WARNING: Cannot load {args.xrefmap} containing xrefMap dictionary', file=sys.stderr)
        sys.exit(1)

    try:
        pageMap = importFileModule(args.pagemap).pageMap
    except:
        print(f'WARNING: Cannot load {args.pagemap} containing pageMap dictionary', file=sys.stderr)
        sys.exit(1)

    try:
        fp = open(args.validusage, 'r', encoding='utf-8')
        vufile = json.load(fp)
        fp.close()
    except:
        print(f'WARNING: Cannot load {args.validusage} containing valid usage statements', file=sys.stderr)
        sys.exit(1)

    # Iterate over top-level dictionary of command names
    rewrittenLinks = 0
    vuidErrors = 0
    pageErrors = 0
    allvus = vufile['validation']
    for (command, commandvus) in allvus.items():

        # Iterate over dictionary of profile? names
        for (profile, profilevus) in commandvus.items():

            # Iterate over individual VUs, updating their 'page' information
            for vu in profilevus:
                vuid = vu['vuid']

                if vuid in xrefMap:
                    pageAnchor = xrefMap[vuid][0]

                    if pageAnchor in pageMap:
                        # Replace .adoc suffix with .html
                        (page, suffix) = os.path.splitext(pageMap[pageAnchor])

                        vu['page'] = f'{page}.html'
                        rewrittenLinks += 1
                    else:
                        print(f'Cannot map page anchor {pageAnchor} for VU {vuid}')
                        pageErrors += 1
                else:
                    print(f'Cannot map VUID {vuid}')
                    vuidErrors += 1

    print(f'Added page keys to {args.validusage} for {rewrittenLinks} VUIDs', file=sys.stderr)

    # Report errors but proceed with updating validusage.json, anyway
    if vuidErrors > 0 or pageErrors > 0:
        print(f'WARNING: {vuidErrors} unmapped VUIDs in {args.xrefmap}, {pageErrors} unmapped page anchors in {args.pagemap}', file=sys.stderr)

    try:
        fp = open(args.validusage, 'w', encoding='utf-8')
        json.dump(vufile, fp, ensure_ascii=False, indent=2)
    except:
        print(f'WARNING: Cannot write updated {args.validusage} containing valid usage statements', file=sys.stderr)
        sys.exit(1)
