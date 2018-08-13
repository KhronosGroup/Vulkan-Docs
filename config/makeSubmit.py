#!/usr/bin/env python3
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

# Build Promoter submission package for a specified extension or extensions.
# This consists of one spec with the extension(s) and all dependencies,
# one with just the dependencies, and an htmldiff of them.
#
# This script lives in config/, but is executed from the parent directory.
#
# Usage: makeSubmit extension targets

import argparse, copy, io, os, pdb, re, string, subprocess, sys

# Ensure config/extDependency.py is up-to-date before we import it.
subprocess.check_call(['make', 'config/extDependency.py'])

from extDependency import *

def enQuote(str):
    return '"' + str + '"'

# Make a single submission target. Several are needed per document.
#
# outDir - where to generate intermediate and final documents
# extensionList - list of extensions to include
# submitName - base name of final HTML file
# title - document title
# target - default 'html'
def makeTarget(outDir, extensionList, submitName, title, target):
    print('make clean_generated')
    print('make OUTDIR=' + outDir,
          'EXTENSIONS="' + ' '.join(extensionList) + '"',
          'APITITLE="' + title + '"', target)
    # Rename into submission directory
    outFile = outDir + '/html/' + submitName + '.html'
    print('mv', outDir + '/html/vkspec.html', enQuote(outFile))
    # No longer needed
    # print('mv -n', outDir + '/katex', 'out/submit/')

    return outFile

# Make submission for a list of required extension names
def makeSubmit(submitName, required, target='html'):
    global extensions

    deps = []
    for name in required:
        if name in extensions.keys():
            for depname in extensions[name]:
                if (depname not in required and depname not in deps):
                    deps.append(depname)

    print('echo Required extensions:', ' '.join(required))
    print('echo Dependent extensions:', ' '.join(deps))
    print('')

    # Generate shell commands to build the specs
    outDir = 'submit'
    print('mkdir -p', outDir)

    # Generate spec with required extensions + dependencies
    newSpec = makeTarget(outDir, required + deps, submitName,
                         submitName, target)

    # Generate base spec with just dependencies
    baseSpec = makeTarget(outDir, deps, 'deps-' + submitName,
                          '(with only dependencies of ' + submitName + ')',
                          target)

    # # Reorganize and rename them, and generate the diff spec
    print('')
    print('cd scripts')
    print('./htmldiff',
          enQuote('../' + baseSpec),
          enQuote('../' + newSpec),
          '>',
           enQuote('../submit/html/diff-' + submitName + '.html'))
    print('cd ..')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-title', action='store',
                        default='vkspec',
                        help='Set the document title')
    parser.add_argument('-extension', action='append',
                        default=[],
                        help='Specify a required extension or extensions to add to targets')

    results = parser.parse_args()

    makeSubmit(results.title, results.extension)
