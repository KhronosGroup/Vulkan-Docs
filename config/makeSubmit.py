#!/usr/bin/env python3
#
# Copyright 2016-2023 The Khronos Group Inc.
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

# Make a single submission target. Several are needed per document.
#
# outDir - where to generate intermediate and final documents
# extensions - list of extensions to include
# submitName - base name of final HTML file
# title - document title
# target - default 'html'
def makeTarget(outDir, extensions, submitName, title, target):
    ws = ' '

    print('make clean_generated')
    print('make',
          f'OUTDIR="{outDir}"',
          'IMAGEOPTS=',
          f'EXTENSIONS="{ws.join(sorted(extensions))}"',
          f'APITITLE="{title}"',
          target)
    # Rename into submission directory
    outFile = f'{outDir}/html/{submitName}.html'.replace(' ', '_')
    print('mv', f'"{outDir}/html/vkspec.html"', f'"{outFile}"')

    return outFile

# Make submission for a list of required extension names
def makeSubmit(outDir, submitName, required, apideps, target='html'):
    """outDir - path to output directory for generated specs.
       submitName - the base document title, usually the name of the
            extension being submitted unless there is more than one of them.
       required - a list of one or more extension names comprising the
            submission.
       apideps - extension dependencies from which to determine other
            extensions which must be included."""

    # Convert required list to a set
    required = set(required)

    extraexts = set()
    for name in required:
        for depname in apideps.children(name):
            if depname not in required:
                #print(f'Adding {depname} to extraexts')
                extraexts.add(depname)

    print('echo Required extensions:', ' '.join(sorted(required)))
    print('echo Dependent extensions:', ' '.join(sorted(extraexts)))
    print('')

    # Generate shell commands to build the specs
    print('mkdir -p', outDir)

    # Generate spec with required extensions + dependencies
    newSpec = makeTarget(outDir, required.union(extraexts), submitName,
                         submitName, target)

    # Generate base spec with just dependencies
    baseSpec = makeTarget(outDir, extraexts, 'deps-' + submitName,
                          '(with only dependencies of ' + submitName + ')',
                          target)

    # # Reorganize and rename them, and generate the diff spec
    print('')
    print('cd scripts/htmldiff')
    print('./htmldiff',
          f'"{baseSpec}"',
          f'"{newSpec}"',
          '>',
          f'"{outDir}/html/diff-{submitName}.html"')
    print('cd ../../')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-extension', action='append',
                        default=[],
                        help='Specify a required extension or extensions to add to targets')
    parser.add_argument('-title', action='store',
                        default='vkspec-tmp',
                        help='Set the document title')
    parser.add_argument('-outdir', action='store',
                        default='submit',
                        help='Path to generated specs')
    parser.add_argument('-registry', action='store',
                        default=None,
                        help='Path to API XML registry file specifying version and extension dependencies')
    parser.add_argument('-apiname', action='store',
                        default=None,
                        help='API name to generate')

    results = parser.parse_args()

    # Look for scripts/extdependency.py
    # This requires makeSpec to be invoked from the repository root, but we
    # could derive that path.
    sys.path.insert(0, 'scripts')
    from extdependency import ApiDependencies

    apideps = ApiDependencies(results.registry, results.apiname)

    results.outdir = os.path.abspath(results.outdir)
    makeSubmit(results.outdir, results.title, results.extension, apideps)
