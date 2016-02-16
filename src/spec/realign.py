#!/usr/bin/python3
#
# Copyright (c) 2013-2016 The Khronos Group Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and/or associated documentation files (the
# "Materials"), to deal in the Materials without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Materials, and to
# permit persons to whom the Materials are furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Materials.
#
# THE MATERIALS ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.

# Usage: realign [infile] > outfile
# Used to realign XML tags in the Vulkan registry after it's operated on by
# some other filter, since whitespace inside a tag isn't part of the
# internal representation.

import copy, sys, string, re

def realignXML(fp):
    patterns = [
        [ '(^ *\<type .*)(category=[\'"]bitmask[\'"].*)', 58 ],
        [ '(^ *\<enum [bv].*)(name=.*)',     28 ],
        [ '(^ *\<enum [bv].*)(comment=.*)',  85 ]
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
                    #print("# While processing line: " + line, end='')
                    emitted = True
                #print("# matched expression: " + patterns[i][0])
                #print("# clause 1 = " + match.group(1))
                #print("# clause 2 = " + match.group(2))
                line = match.group(1).ljust(column[i]) + match.group(2)
        if (emitted):
            print(line)
        else:
            print(line, end='')

if __name__ == '__main__':
    if (len(sys.argv) > 1):
        realignXML(open(sys.argv[1],"r"))
    else:
        realignXML(sys.stdin)
