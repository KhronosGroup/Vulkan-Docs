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

# fixupRef.py - replace old // refBegin .. // refEnd syntax with new
# open block syntax
#
# Usage: fixupRef.py [-outdir path] [-overwrite] files

from reflib import *
import argparse, copy, io, os, pdb, re, string, sys

def prefix(depth):
    return '  ' * depth

openPat   = re.compile('^\[open,(?P<attribs>refpage=.*)\]')
ifdefPat = re.compile('^if(n|)def::(?P<condition>.*)\[(?P<text>.*)\]')
endifPat = re.compile('^endif::(?P<condition>.*)\[\]')

# Look for imbalanced block delimiters and conditionals
#   specFile - filename to examine
def findBalance(specFile):
    file = loadFile(specFile)
    if file == None:
        return

    # blocks[] is a stack of nesting constructs, each of which is
    # [ '--', line, None ] for a -- delimiter on line
    # [ 'ifdef', line, condition] for an ifdef or ifndef on line
    blocks = []

    line = 1

    for str in file:
        blockDepth = len(blocks)
        if blockDepth > 0:
            thisBlock = blocks[blockDepth-1]
            blockType = thisBlock[0]
            blockLine = thisBlock[1]
            blockCondition = thisBlock[2]
        else:
            thisBlock = None
            blockType = None
            blockLine = None
            blockCondition = None

        if str.rstrip() == '--':
            if (blockDepth > 0 and blockType == '--'):
                print(prefix(blockDepth - 1) +
                      'Closing -- block opened @', blockLine,
                      '-> new block depth =', blockDepth - 1)
                blocks.pop()
            else:
                print(prefix(blockDepth) +
                      'Opening -- block @', line,
                      '-> new block depth:', blockDepth + 1)
                blocks.append([ '--', line, None ])
            line = line + 1
            continue

        matches = beginPat.search(str)
        if matches != None:
            # print('Matched [open pattern @', line, ':', str.rstrip())
            line = line + 1
            continue

        matches = ifdefPat.search(str)
        if matches != None:
            condition = matches.group('condition')
            text = matches.group('text')

            if text != '':
                print('Matched self-closing if(n)def pattern @', line,
                      'condition:', condition, 'text:', text)
            else:
                print(prefix(blockDepth) +
                      'Opening if(n)def block @', line,
                      '-> new block depth =', blockDepth + 1,
                      'condition:', condition)
                blocks.append([ 'ifdef', line, condition ])

            line = line + 1
            continue

        matches = endifPat.search(str)
        if matches != None:
            condition = matches.group('condition')

            if (blockDepth > 0):
                if blockType == 'ifdef':
                    # Try closing an ifdef/ifndef block
                    if blockCondition != condition:
                        print('** WARNING:', specFile,
                              'endif @', blockLine,
                              'block depth:', blockDepth,
                              'condition', condition,
                              'does not match ifdef/ifndef @',
                              blockLine, 'condition', blockCondition)

                    print(prefix(blockDepth - 1) +
                          'Closing endif block @', line,
                          '-> new block depth =', blockDepth - 1)
                    blocks.pop()
                elif blockType == '--':
                    # An overlap!
                    print('** ERROR:', specFile, 'endif @', line,
                          'block depth:', blockDepth,
                          'overlaps -- block start @', blockLine)
                else:
                    # Should never get here
                    print('** ERROR:', specFile,
                          'block depth:', blockDepth,
                          'unknown open block type:', blockType)
            else:
                # Unlikely error condition from bad markup
                print('** ERROR:', specFile,
                      'block depth:', blockDepth,
                      'endif @', line, 'with no matching open block')

            line = line + 1
            continue

        line = line + 1

    blockDepth = len(blocks)
    if blockDepth > 0:
        print('** ERROR:', specFile, 'still in open block at EOF:',
              'block depth =', blockDepth,
              'block type:', blocks[blockDepth-1][0])

if __name__ == '__main__':
    global genDict
    genDict = {}

    parser = argparse.ArgumentParser()

    parser.add_argument('-diag', action='store', dest='diagFile',
                        help='Set the diagnostic file')
    parser.add_argument('-warn', action='store', dest='warnFile',
                        help='Set the warning file')
    parser.add_argument('-log', action='store', dest='logFile',
                        help='Set the log file for both diagnostics and warnings')
    parser.add_argument('files', metavar='filename', nargs='*',
                        help='a filename to extract ref pages from')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')

    results = parser.parse_args()

    setLogFile(True,  True, results.logFile)
    setLogFile(True, False, results.diagFile)
    setLogFile(False, True, results.warnFile)

    skipped = set()
    for file in results.files:
        findBalance(file)

    if len(skipped) > 0:
        print('Files containing skipped feature blocks:')
        for file in sorted(skipped):
            print('\t' + file)
