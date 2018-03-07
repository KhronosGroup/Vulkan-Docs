#!/usr/bin/python3
#
# Copyright (c) 2017-2018 The Khronos Group Inc.
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

    fmtString = '    <li> <a href="specs/1.1-extensions/html/vkspec.html#{0}"> {0} </a> </li>'

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

        if (supported == 'vulkan'):
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
