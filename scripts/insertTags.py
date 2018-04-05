#!/usr/bin/python3
#
# Copyright (c) 2016-2018 The Khronos Group Inc.
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

# insertTags.py - insert // refBegin and // refEnd tags in Vulkan
# spec source files.
#
# Usage: insertTags.py output-dir files

# Short descriptions of ref pages, if not found
from refDesc import *

# Utility functions
from reflib import *
import copy, os, pdb, re, string, sys

# Insert informative tags in a spec asciidoc source file
#   specFile - filename to add tags to
#   baseDir - output directory to generate page in
def insertTags(specFile, baseDir):
    file = loadFile(specFile)
    if (file == None):
        return
    pageMap = findRefs(file)
    logDiag(specFile + ': found', len(pageMap.keys()), 'potential pages')

    # Fix up references in pageMap
    fixupRefs(pageMap, specFile, file)

    # Proceed backwards through the file, inserting
    # // refBegin name desc
    # lines where they're meaningful

    logDiag('Table of pages found:')
    logDiag('---------------------')
    for name in pageMap.keys():
        printPageInfo(pageMap[name], file)

    line = len(file) - 1
    while (line >= 0):
        # If this is a valid begin line without a description, and a
        # description exists in refDesc, add it.
        for name in pageMap.keys():
            pi = pageMap[name]
            if (pi.begin == line):
                if (not name in refDesc.keys()):
                    if (pi.desc != None):
                        logDiag('Description already exists, but no refDesc found for', name, 'at', specFile + ':' + str(line))
                    else:
                        if (pi.embed):
                            logDiag('No refDesc found (this is OK) for embedded', name, 'at', specFile + ':' + str(line))
                        else:
                            logWarn('No refDesc found for', name, 'at', specFile + ':' + str(line))
                    continue

                # New or replacement refBegin line, with short description
                newLine = '// refBegin ' + name + ' - ' + refDesc[name] + '\n'

                if (pi.desc == None):
                    logDiag('Adding description for', name, 'at', specFile + ':' + str(line))

                    # If there's already a refBegin on this line, replace it.
                    # Otherwise, insert one.
                    if (file[line].find('// refBegin') == 0):
                        logDiag('Replacing existing refBegin without description for', name, 'at', specFile + ':' + str(line))
                        file[line] = newLine
                    else:
                        logDiag('Inserting new refBegin at', specFile + ':' + str(line))
                        # Add a blank line after the comment if it's new
                        file.insert(line, newLine)
                        file.insert(line, '\n')
                else:
                    if (pi.desc[-1] == '.'):
                        pi.desc = pi.desc[0:-1]
                    if (pi.desc == refDesc[name]):
                        logDiag('Not replacing description for', name, 'at', specFile + ':' + str(line), '- MATCHES existing one')
                    else:
                        logWarn('Replacing existing refBegin WITH description for', name, 'at', specFile + ':' + str(line))
                        file[line] = newLine
                        # logWarn('\t  refDesc: ', refDesc[name])
                        # logWarn('\tfile desc: ', pi.desc)

        line = line - 1

    pageName = baseDir + '/' + os.path.basename(specFile)
    logDiag('Creating output file', pageName)
    fp = open(pageName, 'w', encoding='utf-8')
    fp.writelines(file)
    fp.close()


if __name__ == '__main__':
    logDiag('In main!')

    baseDir = 'man'
    follow = False
    if (len(sys.argv) > 2):
        baseDir = sys.argv[1]
        for file in sys.argv[2:]:
            insertTags(file, baseDir)
