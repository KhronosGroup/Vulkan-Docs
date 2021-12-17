#!/usr/bin/env python3
#
# Copyright 2016-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Build Promoter submission package for a specified extension or extensions.
# This consists of one spec with the extension(s) and all dependencies,
# one with just the dependencies, and an htmldiff of them.
#
# This script lives in config/, but is executed from the parent directory.
#
# Usage: makeSubmit extension targets

import argparse, copy, io, os, pdb, re, string, subprocess, sys

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
          'IMAGEOPTS=',
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
    print('cd scripts/htmldiff')
    print('./htmldiff',
          enQuote('../../' + baseSpec),
          enQuote('../../' + newSpec),
          '>',
           enQuote('../../submit/html/diff-' + submitName + '.html'))
    print('cd ../../')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-extension', action='append',
                        default=[],
                        help='Specify a required extension or extensions to add to targets')
    parser.add_argument('-genpath', action='store',
                        default='gen',
                        help='Path to directory containing generated extDependency.py module')
    parser.add_argument('-title', action='store',
                        default='vkspec',
                        help='Set the document title')

    results = parser.parse_args()

    # Look for extDependency.py in the specified directory
    sys.path.insert(0, results.genpath)

    # Ensure gen/extDependency.py is up-to-date before we import it.
    subprocess.check_call(['make', 'GENERATED=' + results.genpath, 'extDependency'])

    from extDependency import *

    makeSubmit(results.title, results.extension)
