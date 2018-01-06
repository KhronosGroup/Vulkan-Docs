#!/usr/bin/python3
#
# Copyright (c) 2013-2018 The Khronos Group Inc.
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
