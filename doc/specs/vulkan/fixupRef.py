#!/usr/bin/python3
#
# Copyright (c) 2016-2017 The Khronos Group Inc.
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
from vkapi import *
import argparse, copy, io, os, pdb, re, string, sys

# Return True if name is a Vulkan extension name (ends with an upper-case
# author ID). This assumes that author IDs are at least two characters.
def isextension(name):
    return name[-2:].isalpha() and name[-2:].isupper()

# Return 'None' for None, the string otherwise
def noneStr(str):
    if str == None:
        return '(None)'
    else:
        return str

# Escape single quotes in a string for asciidoc
def escapeQuote(str):
    return str.replace("'", "\'")

# Start a refpage open block
def openBlock(name, desc, type, fp):
    print("[open,refpage='" + name +
          "',desc='" + desc +
          "',type='" + type + "']",
          file=fp)
    print('--', file=fp)

# Replace old // refBegin .. // refEnd references in an asciidoc
# file with open blocks, per # ??? .
#   specFile - filename to extract from
#   outDir - output directory to write updated file to, if not overwritten
#   overwrite - True if the file should be overwritten in place
#   skipped - set of filenames containing commands which weren't
#       rewritten with open blocks (e.g. enums). Updated in place.
def replaceRef(specFile, outDir, overwrite = False, skipped = set()):
    file = loadFile(specFile)
    if file == None:
        return

    # Save the path to this file for later use in rewriting relative includes
    specDir = os.path.dirname(os.path.abspath(specFile))

    pageMap = findRefs(file)
    logDiag(specFile + ': found', len(pageMap.keys()), 'potential pages')

    sys.stderr.flush()

    # Fix up references in pageMap
    fixupRefs(pageMap, specFile, file)

    # Map the page info dictionary into a dictionary of actions
    # keyed by line number they're performed on/after:
    #   { 'refBegin', name, description } -> replace refBegin line with block start
    #   { 'addBegin', name, description } -> add block start preceding this line
    #   { 'refEnd', name, description } -> replace refEnd line with block end
    #   { 'addEnd', name, description } -> add block end following this line

    actions = { }

    for name in pageMap.keys():
        pi = pageMap[name]

        # Leave refBegin/refEnd alone for enums, for now
        if pi.type != 'enums' and pi.extractPage:
            if (file[pi.begin][0:11] == '// refBegin'):
                # Replace line
                actions[pi.begin] = {
                    'action' : 'begin',
                    'replace': True,
                    'name'   : pi.name,
                    'desc'   : pi.desc,
                    'type'   : pi.type
                }
            else:
                # Insert line
                actions[pi.begin] = {
                    'action' : 'begin',
                    'replace': False,
                    'name'   : pi.name,
                    'desc'   : pi.desc,
                    'type'   : pi.type
                }

            if (file[pi.end][0:9] == '// refEnd'):
                # Replace line
                actions[pi.end] = {
                    'action' : 'end',
                    'replace': True,
                    'name'   : pi.name,
                    'desc'   : pi.desc,
                    'type'   : pi.type
                }
            else:
                # Insert line
                actions[pi.end] = {
                    'action' : 'end',
                    'replace': False,
                    'name'   : pi.name,
                    'desc'   : pi.desc,
                    'type'   : pi.type
                }
        else:
            print('Skipping replacement for', pi.name, 'at', specFile,
                  'line', pi.begin)
            skipped.add(specFile)

    if overwrite:
        pageName = specFile
    else:
        pageName = outDir + '/' + os.path.basename(specFile)

    fp = open(pageName, 'w', encoding='utf-8')

    line = 0
    for text in file:
        if line in actions.keys():
            action = actions[line]['action']
            replace = actions[line]['replace']
            name = noneStr(actions[line]['name'])
            desc = escapeQuote(noneStr(actions[line]['desc']))
            type = actions[line]['type']

            if action == 'begin':
                openBlock(name, desc, type, fp)
                if not replace:
                    print(text, file=fp, end='')
            elif action == 'end':
                if not replace:
                    print(text, file=fp, end='')
                print('--', file=fp)
            else:
                print('ERROR: unrecognized action:', action, 'in',
                      specFile, 'at line', line)
                print(text, file=fp, end='')
        else:
            print(text, file=fp, end='')
        line = line + 1

    fp.close()

    #for line in sorted(actions.keys()):
    #    action = actions[line]
    #    print('action at line', line, '\t',
    #          action[0], action[1], action[2])

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
    parser.add_argument('-outdir', action='store', dest='outDir',
                        default='man',
                        help='Set the base directory in which pages are generated')
    parser.add_argument('-overwrite', action='store_true',
                        help='Overwrite input filenames instead of writing different output filenames')
    parser.add_argument('files', metavar='filename', nargs='*',
                        help='a filename to extract ref pages from')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')

    results = parser.parse_args()

    setLogFile(True,  True, results.logFile)
    setLogFile(True, False, results.diagFile)
    setLogFile(False, True, results.warnFile)

    skipped = set()
    for file in results.files:
        replaceRef(file, results.outDir, results.overwrite, skipped)

    if len(skipped) > 0:
        print('Files containing skipped feature blocks:')
        for file in sorted(skipped):
            print('\t' + file)
