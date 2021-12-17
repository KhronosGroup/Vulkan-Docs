#!/usr/bin/python3
#
# Copyright 2020-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# check_html_xrefs - simple-minded check for internal xrefs in spec HTML
# that don't exist.

# Usage: check_html_xrefs file
# Just reports bad xrefs, not where they occur

import argparse
import re
from lxml import etree

SECTNAME = re.compile(r'sect(?P<level>\d+)')

def find_parent_ids(elem, href):
    """Find section titles in parents, which are the 'id' elements of '<hN'
       children of '<div class="sectM"' tags, and N = M + 1. This may be
       specific to the Vulkan spec, though - hierarchy could be different in
       other asciidoctor documents. Returns a list of [ anchor, title ].

       elem - this node
       href - href link text of elem"""

    # Find parent <div> with class="sect#"
    parent = elem.getparent()
    while parent is not None:
        if parent.tag == 'div':
            cssclass = parent.get('class')
            matches = SECTNAME.match(cssclass)
            if matches is not None:
                level = int(matches.group('level'))
                # Look for corresponding header tag in this div
                helem = parent.find('./h{}'.format(level+1))
                if helem is not None:
                    return [ helem.get('id'), ''.join(helem.itertext()) ]
        parent = parent.getparent()
    return [ '** NO PARENT NODE IDENTIFIED **', '' ]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('files', metavar='filename', nargs='*',
                        help='Path to registry XML')
    args = parser.parse_args()

    for filename in args.files:
        parser = etree.HTMLParser()
        tree = etree.parse(filename, parser)

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

        # Find all internal 'href' attributes and see if they're valid
        # Keep an [element, href] list for tracking parents
        # Also keep a count of each href
        ref_elems = tree.findall('.//a[@href]')
        refs = []
        count = {}
        for elem in ref_elems:
            href = elem.get('href')
            # If not a local href, skip it
            if href[0] == '#':
                # If there's a corresponding id, skip it
                href = href[1:]
                if href not in ids:
                    if href in count:
                        refs.append((elem, href))
                        True
                        count[href] = count[href] + 1
                    else:
                        refs.append((elem, href))
                        count[href] = 1
            else:
                True
                # print('Skipping external href:', ref)

        # Check for hrefs not found in ids
        print('Bad links in {}:'.format(filename))
        for (elem, href) in refs:
            parents = find_parent_ids(elem, href)
            print('{:<40} in {:<28} ({})'.format(href, parents[0], parents[1]))
