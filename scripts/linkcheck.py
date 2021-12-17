#!/usr/bin/python3
# Copyright 2013-2021 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# linkcheck - check internal links of the specified HTML file against
# internal anchors and report inconsistencies.
#
# Usage: linkcheck file.html

import argparse
from lxml import etree as et

def printSet(s):
    for key in sorted(s):
        print('    {}'.format(key))

def checkLinks(file, args):
    parser = et.HTMLParser()
    tree = et.parse(file, parser)

    # Remove all <svg> elements, which just add noise to the cross-referencing
    for svg in tree.findall('//svg'):
        svg.getparent().remove(svg)

    # Extract elements with href= and id= attributes
    hrefs = tree.findall('//*[@href]')
    ids = tree.findall('//*[@id]')

    # Extract xref name from each xref
    internals = set()
    externals = set()

    for e in hrefs:
        # Don't track '<link>' tags from HTML headers
        if e.tag != 'link':
            xref = e.get('href')

            if xref[0:1] == '#':
                # Internal anchor
                internals.add(xref[1:])
            else:
                externals.add(xref)

    # Extract anchor name from each id
    anchors = set()

    for e in ids:
        # Don't track SVG '<g>' tags
        if e.tag != 'g':
            anchors.add(e.get('id'))

    # Intersect them to find inconsistencies
    xrefsOnly = internals.difference(anchors)
    anchorsOnly = anchors.difference(internals)

    # print('External xrefs:', len(externals))
    # printSet(externals)
    #
    # print('Internal xrefs:', len(internals))
    # print('Anchors:       ', len(anchors))

    print('Internal xrefs not in anchors:', len(xrefsOnly))
    printSet(xrefsOnly)

    if args.anchors:
        print('Internal anchors not in xrefs:', len(anchorsOnly))
        printSet(anchorsOnly)

# Patterns used to recognize interesting lines in an asciidoc source file.
# These patterns are only compiled once.

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('files', metavar='filename', nargs='*',
                        help='a filename to promote text in')
    parser.add_argument('-anchors', action='store_true',
                        help='Report orphaned anchors')


    args = parser.parse_args()

    for file in args.files:
        checkLinks(file, args)
