#!/usr/bin/python3
#
# Copyright (c) 2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Script that adds href to <a> anchors

import os,sys,re

def genAnchorLinks(in_file, out_file):
        try:
                with open(in_file, 'r', encoding='utf8') as f: data = f.read()
        except FileNotFoundError:
                print('Error: File %s does not exist.' % in_file)
                sys.exit(2)

        data = re.sub( r'(<a )(id="(VUID\-[\w\-:]+)")(>)', '\g<1>\g<2> href="#\g<3>"\g<4>', data)
        with open(out_file, 'w', encoding='utf8') as f: data = f.write(data)

if __name__ == '__main__':
        if len(sys.argv) != 3:
                print('Error: genanchorlinks.py requires two arguments.')
                print('Usage: genanchorlinks.py infile.html outfile.html')
                sys.exit(1)
        genAnchorLinks(sys.argv[1], sys.argv[2])
