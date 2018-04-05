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

# Retroactively insert markup in show both 1.1 core features and KHR
# extensions they were promoted from.

# Usage: promote.py [-overwrite] [-out dir] [-suffix str] files
#   -overwrite updates in place (can be risky, make sure there are backups)
#   -out specifies directory to create output file in, default 'out'
#   -suffix specifies suffix to add to output files, default ''
#   files are asciidoc source files from the Vulkan spec to reflow.

# For error and file-loading interfaces only
import argparse, copy, os, pdb, re, string, sys
from reflib import *
from promoted import *

global anchor
anchor = 0

def anchorname(anchor):
    return 'promoted-' + str(anchor)

def printanchor(fp):
    # Anchor index for navigation
    global anchor

    print('[[' + anchorname(anchor) + ']]', file=fp)
    print('This anchor:', anchorname(anchor), file=fp)
    print('<<' + anchorname(anchor+1) + ', OINK>>', file=fp)
    anchor = anchor + 1

# promote a core interface and include the extension it was promoted from
#   line - matching line with 1.1 interface
#   type - 'protos', 'structs', 'flags', 'enums'
#   name - interface name
#   extension - name of extension interface was promoted from
#   fp - output filename
def promote(line, type, name, extension, fp):
    if type == 'protos':
        # printanchor(fp)
        print('ifdef::VK_VERSION_1_1[]', file=fp)
        print(line, file=fp, end='')
        print('endif::VK_VERSION_1_1[]', file=fp)
        print('', file=fp)
        print('ifdef::VK_VERSION_1_1+' + extension +
              '[or the equivalent command]', file=fp)
        print('', file=fp)
        print('ifdef::' + extension + '[]', file=fp)
        print('include::../api/' + type + '/' + name + 'KHR.txt[]', file=fp)
        print('endif::' + extension + '[]', file=fp)
        del promoted[name]
    elif type == 'structs' or type == 'enums' or type == 'flags' or type == 'handles':
        # printanchor(fp)
        print(line, file=fp, end='')
        print('', file=fp)
        print('ifdef::' + extension + '[]', file=fp)
        print('or the equivalent', file=fp)
        print('', file=fp)
        print('include::../api/' + type + '/' + name + 'KHR.txt[]', file=fp)
        print('endif::' + extension + '[]', file=fp)
        del promoted[name]
    else:
        logWarn('Unrecognized promoted type', type, 'for interface', name)
        print(line, file=fp, end='')


def promoteFile(filename, args):
    logDiag('promote: filename', filename)

    lines = loadFile(filename)
    if (lines == None):
        return

    # Output file handle and promote object for this file. There are no race
    # conditions on overwriting the input, but it's not recommended unless
    # you have backing store such as git.

    if args.overwrite:
        outFilename = filename
    else:
        outFilename = args.outDir + '/' + os.path.basename(filename) + args.suffix

    try:
        fp = open(outFilename, 'w', encoding='utf8')
        True
    except:
        logWarn('Cannot open output file', filename, ':', sys.exc_info()[0])
        return None

    lineno = 0
    for line in lines:
        lineno = lineno + 1

        matches = includePat.search(line)
        if matches != None:
            type = matches.group('type')
            name = matches.group('name')
            if name in promoted:
                extension = promoted[name]['extension']
                if extension:
                    # Promote core interface
                    promote(line, type, name, promoted[name]['extension'], fp)
                    continue
        # Fallthrough
        print(line, file=fp, end='')

    fp.close()

def promoteAllAdocFiles(folder_to_promote, args):
    for root, subdirs, files in os.walk(folder_to_promote):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                promoteFile(file_path, args)
        for subdir in subdirs:
            sub_folder = os.path.join(root, subdir)
            print('Sub-folder = %s' % sub_folder)
            if not (subdir.lower() == "scripts") and not (subdir.lower() == "style"):
                print('   Parsing = %s' % sub_folder)
                promoteAllAdocFiles(sub_folder, args)
            else:
                print('   Skipping = %s' % sub_folder)

# Patterns used to recognize interesting lines in an asciidoc source file.
# These patterns are only compiled once.

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-diag', action='store', dest='diagFile',
                        help='Set the diagnostic file')
    parser.add_argument('-warn', action='store', dest='warnFile',
                        help='Set the warning file')
    parser.add_argument('-log', action='store', dest='logFile',
                        help='Set the log file for both diagnostics and warnings')
    parser.add_argument('-overwrite', action='store_true',
                        help='Overwrite input filenames instead of writing different output filenames')
    parser.add_argument('-out', action='store', dest='outDir',
                        default='out',
                        help='Set the output directory in which updated files are generated (default: out)')
    parser.add_argument('-suffix', action='store', dest='suffix',
                        default='',
                        help='Set the suffix added to updated file names (default: none)')
    parser.add_argument('files', metavar='filename', nargs='*',
                        help='a filename to promote text in')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')

    args = parser.parse_args()

    setLogFile(True,  True, args.logFile)
    setLogFile(True, False, args.diagFile)
    setLogFile(False, True, args.warnFile)

    if args.overwrite:
        logWarn('promote.py: will overwrite all input files')

    # If no files are specified, promote the entire specification chapters folder
    if len(args.files) == 0:
        folder_to_promote = os.getcwd()
        folder_to_promote += '/chapters'
        promoteAllAdocFiles(folder_to_promote, args)
    else:
        for file in args.files:
            promoteFile(file, args)

    print('At end, promoted interfaces remaining:')
    for key in promoted:
        if promoted[key]['extension'] != None:
            print('\t' + key)
