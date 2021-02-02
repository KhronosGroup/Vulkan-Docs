#!/usr/bin/python3
#
# Copyright 2013-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Usage: realign [infile] > outfile
# Used to realign XML tags in the Vulkan registry after it's operated on by
# some other filter, since whitespace inside a tag isn't part of the
# internal representation.

import copy, sys, string, re

def realignXML(fp):
    patterns = [
        [ r'(^ *\<type .*)(category=[\'"]bitmask[\'"].*)', 58 ],
        [ r'(^ *\<enum [bv].*)(name=.*)',     28 ],
        [ r'(^ *\<enum [bv].*)(comment=.*)',  85 ]
    ]

    # Assemble compiled expressions to match and alignment columns
    numpat = len(patterns)
    regexp = [ re.compile(patterns[i][0]) for i in range(0,numpat)]
    column = [ patterns[i][1] for i in range(0,numpat)]

    lines = fp.readlines()
    for line in lines:
        emitted = False
        for i in range(0,len(patterns)):
            match = regexp[i].match(line)
            if (match):
                if (not emitted):
                    #print('# While processing line: ' + line, end='')
                    emitted = True
                #print('# matched expression: ' + patterns[i][0])
                #print('# clause 1 = ' + match.group(1))
                #print('# clause 2 = ' + match.group(2))
                line = match.group(1).ljust(column[i]) + match.group(2)
        if (emitted):
            print(line)
        else:
            print(line, end='')

if __name__ == '__main__':
    if (len(sys.argv) > 1):
        realignXML(open(sys.argv[1], 'r', encoding='utf-8'))
    else:
        realignXML(sys.stdin)
