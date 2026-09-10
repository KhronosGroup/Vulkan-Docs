#!/usr/bin/env python3
# Copyright 2026 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# normalize_xml.py - normalize excess whitespace in XML attribute lists by
# reading vk.xml into xml.etree and writing it back.
# Such whitespace is not part of XML data and is removed.

# Usage: normalize_xml.py [-o output.xml] [-xml inputfile]
#   -xml specifies the file to be normalized, defaulting to 'xml/vk.xml'
#        in the specification repository.
#   -o specifies the output file to write.
#      If not specified, the input XML file is overwritten in place.

import argparse
import os
import sys
import xml.etree.ElementTree as etree

if __name__ == '__main__':
    default_xml = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'xml', 'vk.xml'))

    parser = argparse.ArgumentParser(description='Normalize whitespace in XML by reading and re-writing it')

    parser.add_argument('-o', help='XML file to write to', dest='output')
    parser.add_argument('-xml', default=default_xml, help='path to XML registry file (default: xml/vk.xml)')

    args = parser.parse_args(sys.argv[1:])

    if args.output is None:
        args.output = args.xml
        print(f'Will overwrite input file {args.xml}')

    if not os.path.exists(args.xml):
        print(f'Input file {args.xml} does not exist')
        sys.exit(1)

    tree = etree.parse(args.xml)
    tree.write(args.output, encoding='UTF-8', xml_declaration=True)
    fp = open(args.output, mode='a', encoding='UTF-8')
    fp.write('\n')
