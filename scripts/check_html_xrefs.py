#!/usr/bin/python3
#
# Copyright 2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# check_html_xrefs - simple-minded check for internal xrefs in spec HTML
# that don't exist.

# Usage: check_html_xrefs file
# Just reports bad xrefs, not where they occur

import argparse, cProfile, pdb, string, sys, time
import io, os, re, string, sys, copy
from lxml import etree

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('files', metavar='filename', nargs='*',
                        help='Path to registry XML')
    args = parser.parse_args()

    if len(args.files) > 0:
        file = open(args.files[0], 'r')
        parser = etree.HTMLParser()
        tree = etree.parse(file, parser)

        # Find all 'id' elements
        id_elems = tree.findall('.//*[@id]')
        ids = set()
        for elem in id_elems:
            id = elem.get('id')
            if id in ids:
                True
                # print('Duplicate ID attribute:', id)
            else:
                ids.add(id)

        # Find all 'href' attributes
        ref_elems = tree.findall('.//a[@href]')
        refs = set()
        for elem in ref_elems:
            ref = elem.get('href')
            # If not a local ref, skip it
            if ref[0] == '#':
                ref = ref[1:]
                if ref in refs:
                    True
                    # print('Duplicate href:', ref)
                else:
                    refs.add(ref)
            else:
                True
                # print('Skipping ref:', ref)

        # Check for hrefs not found in ids
        for ref in refs:
            if ref not in ids:
                print('Reference not found in HTML: #' + ref)
