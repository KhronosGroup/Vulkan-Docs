#!/usr/bin/python3
#
# Copyright (c) 2017-2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Construct an HTML fragment indexing extension appendices in vkspec.html.
# This is run only when publishing an update spec, to update the Vulkan
# registry.

import argparse,io,os,re,string,sys,copy
import xml.etree.ElementTree as etree

def listExts(vendor, ext, tag):
    prefix = '    <li> <b> '
    suffix = ' </b> </li>'

    if vendor in tag:
        desc = vendor + ' Extensions (' + tag[vendor] + ')'
    else:
        desc = vendor + ' Extensions (full vendor description unavailable)'
    print(prefix, desc, suffix)

    # (OLD) Links to the extension appendix in the single-page HTML document.
    # This is very slow to load.
    # fmtString = '    <li> <a href="specs/1.2-extensions/html/vkspec.html#{0}"> {0} </a> </li>'

    # This links to the individual per-extension refpages, which are a
    # slightly modified version of the extension appendices, and far faster
    # to load.
    fmtString = '    <li> <a href="specs/1.2-extensions/man/html/{0}.html"> {0} </a> </li>'

    for name in sorted(ext[vendor]):
        print(fmtString.format(name))

# -extension name - may be a single extension name, a a space-separated list
# of names, or a regular expression.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-registry', action='store',
                        default='vk.xml',
                        help='Use specified registry file instead of vk.xml')
    parser.add_argument('-quiet', action='store_true', default=False,
                        help='Suppress script output during normal execution.')

    args = parser.parse_args()

    tree = etree.parse(args.registry)

    # Dictionary of vendor tags -> author name mappings
    tag = {}

    # Loop over all vendor tags, tracking the full corresponding author name
    for elem in tree.findall('tags/tag'):
        vendor = elem.get('name')
        author = elem.get('author')

        tag[vendor] = author

    # Dictionary of supported extensions, indexed by vendor prefix
    ext = {}

    # Loop over all extensions, add supported names to the dictionary
    for elem in tree.findall('extensions/extension'):
        name = elem.get('name')
        supported = elem.get('supported')

        if supported == 'vulkan':
            # Relies on name being in the form VK_<vendor>_stuff
            (vk, vendor) = name.split('_')[0:2]

            if not vendor in ext:
                ext[vendor] = []
            ext[vendor].append(name)

    # Emit HTML fragment indexing the extensions

    print('<ul>')

    for vendor in ['KHR', 'EXT']:
        if vendor in ext:
            listExts(vendor, ext, tag)
            del ext[vendor]

    for vendor in sorted(ext.keys()):
        listExts(vendor, ext, tag)
        del ext[vendor]

    print('</ul>')
