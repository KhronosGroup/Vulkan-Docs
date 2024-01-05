#!/usr/bin/env python3
#
# Copyright 2016-2024 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# Build Promoter submission package for a specified extension or extensions.
# This consists of one spec with the extension(s) and all dependencies,
# one with just the dependencies, and an htmldiff of them.
#
# This script generates a bash script as output, which must be executed
# in the spec repository root directory to build the submission.
#
# usage: makeSubmit.py [-h] [-extension EXTENSION] [-extradepend EXTRADEPEND]
#                      [-title TITLE] [-outdir OUTDIR] [-registry REGISTRY]
#                      [-apiname APINAME]
#
# optional arguments:
#   -h, --help            show this help message and exit
#   -extension EXTENSION  Specify a required extension or extensions to add to
#                         targets
#   -extradepend EXTRADEPEND
#                         Specify an extension that is a dependency of the
#                         required extension(s), but not discovered
#                         automatically
#   -title TITLE          Set the document title
#   -outdir OUTDIR        Path to generated specs
#   -registry REGISTRY    Path to API XML registry file specifying version and
#                         extension dependencies
#   -apiname APINAME      API name to generate

import argparse, copy, io, os, pdb, re, string, subprocess, sys

# Make a single submission target. Several are needed per document.
#
# outDir - where to generate intermediate and final documents
# extensions - list of extensions to include
# submitFileName - base name of final HTML file
# title - document title
# target - default 'html'
def makeTarget(outDir, extensions, submitFileName, title, target):
    ws = ' '

    print('make clean_generated')
    print('make',
          f'OUTDIR="{outDir}"',
          'IMAGEOPTS=',
          f'EXTENSIONS="{ws.join(sorted(extensions))}"',
          f'APITITLE="{title}"',
          target)
    # Rename into submission directory
    outFile = f'{outDir}/html/{submitFileName}.html'
    print('mv', f'"{outDir}/html/vkspec.html"', f'"{outFile}"')

    return outFile

# Make submission for a list of required extension names
def makeSubmit(outDir, submitName, required, extradepend, apideps, target='html'):
    """outDir - path to output directory for generated specs.
       submitName - the base document title, usually the name of the
            extension being submitted unless there is more than one of them.
       required - a list of one or more extension names comprising the
            submission.
       extradepend - a list of zero or more extension names which are
            dependencies not derivable from the XML
       apideps - extension dependencies from which to determine other
            extensions which must be included."""

    # submitName may contain spaces, which are replaced by '_' in generated
    # file names.
    submitFileName = submitName.replace(' ', '_')

    # Convert required list to a set
    required = set(required)

    extraexts = set(extradepend)
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
    newSpec = makeTarget(outDir, required.union(extraexts),
                         submitFileName=submitFileName,
                         title=submitName,
                         target=target)

    # Generate base spec with just dependencies
    baseSpec = makeTarget(outDir, extraexts,
                          submitFileName='deps-' + submitFileName,
                          title='(with only dependencies of ' + submitName + ')',
                          target=target)

    # # Reorganize and rename them, and generate the diff spec
    print('')
    print('cd scripts/htmldiff')
    print('./htmldiff',
          f'"{baseSpec}"',
          f'"{newSpec}"',
          '>',
          f'"{outDir}/html/diff-{submitFileName}.html"')
    print('cd ../../')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-extension', action='append',
                        default=[],
                        help='Specify a required extension or extensions to add to targets')
    parser.add_argument('-extradepend', action='append',
                        default=[],
                        help='Specify an extension that is a dependency of the required extension(s), but not discovered automatically')
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
    makeSubmit(results.outdir, results.title, results.extension, results.extradepend, apideps)
