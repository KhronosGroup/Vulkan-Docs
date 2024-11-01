#!/usr/bin/env python3
#
# Copyright 2016-2024 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# Build Promoter submission package for a specified extension or extensions.
# Updated 2024-10-30 for the new package submission format:
#
#   - extended spec with the new extensions added
#   - HTML diff between extended spec and baseline spec without new extensions
#   - baseline spec with all ratified extensions (instead of core + dependencies)
# The baseline spec is removed after generating the diff unless overridden
# on the command line.
#
# This script generates a bash script as output, which must be executed
# in the spec repository root directory to build the submission.
#
# usage: makeSubmit.py [-h] [-extension EXTENSION] [-extradepend EXTRADEPEND]
#                      [-title TITLE] [-outdir OUTDIR] [-registry REGISTRY]
#                      [-apiname APINAME] [-basespec] [-diffspec]
#
# optional arguments:
#   -h, --help            show this help message and exit
#   -extension EXTENSION  Specify a required extension or extensions to add to
#                         targets
#   -extradepend EXTRADEPEND
#                         Specify an extension that is a dependency of the
#                         required extension(s), but not discovered
#                         automatically (currently ignored)
#   -title TITLE          Set the document title
#   -outdir OUTDIR        Path to generated specs
#   -registry REGISTRY    Path to API XML registry file specifying version and
#                         extension dependencies
#   -apiname APINAME      API name to generate
#   -basespec             Also generate a 'baseline' HTML specification
#   -diffspec             Also generate an HTML diff with the baseline specification

import argparse, os, string, subprocess, sys

# Make a single submission target. Several are needed per document.
#
# outDir - where to generate intermediate and final documents
# extensions - list of extensions to include
# submitFileName - base name of final HTML file
# title - document title
# target - default 'html'
def makeTarget(outDir, extensions, submitFileName, title, target):
    # Construct -extension NAME arguments
    if len(extensions) > 0:
        extopt = ' -extension '
        extargs = extopt + extopt.join(extensions)
    else:
        extargs=''

    # Clean any previous outputs and build the target specification.
    # This relies on OUTDIR *not* pointing to $(GENERATED)/out as it
    # defaults to.
    print(f'make clean_generated')
    print(f'echo DEBUG: ./makeSpec -spec ratified {extargs} OUTDIR="{outDir}" IMAGEOPTS= APITITLE="{title}" {target}')
    print(f'./makeSpec -spec ratified {extargs} OUTDIR="{outDir}" IMAGEOPTS= APITITLE="{title}" {target}')

    # Rename into submission directory
    outFile = f'{outDir}/html/{submitFileName}.html'
    print('mv', f'"{outDir}/html/vkspec.html"', f'"{outFile}"')

    return outFile

# Make submission for a list of required extension names
def makeSubmit(args, apideps = None, target='html'):
    """makeSubmit - make submission for a list of required extension names

        Uses arguments packaged by argparse:

        args.outdir - path to output directory for generated specs.
        args.title - the base document title, usually the name of the
            extension being submitted unless there is more than one of them.
        args.extension - a list of one or more extension names comprising
            the submission.
        args.extradepend - a list of zero or more extension names which are
            dependencies not derivable from the XML.
            Currently ignored.
        args.basespec - True if a baseline specification should be created
            (e.g. not deleted, since it is required for a diffspec).
        args.diffspec - True if an HTML diff between baseline and extended
            specifications should be created.
        apideps - extension dependencies from which to determine other
            extensions which must be included.
            Currently ignored.
        target - build target to generated, normally 'html'."""

    # Title may contain spaces, which are replaced by '_' in generated file
    # names.
    specFileName = args.title.replace(' ', '_')

    # Convert required and extradepend extension lists to sets
    requiredexts = set(args.extension)
    extraexts = set(args.extradepend)

    # We no longer add implicit dependencies, since all ratified
    # dependencies are already included.
    # If there were a non-ratified implicit dependency, this would have to
    # be revisited.

    # for name in requiredexts:
    #     for depname in apideps.children(name):
    #         if depname not in requiredexts:
    #             #print(f'Adding {depname} to extraexts')
    #             extraexts.add(depname)

    print('echo Required extensions:', ' '.join(sorted(requiredexts)))
    print('echo Dependent extensions:', ' '.join(sorted(extraexts)))
    print('')

    # Generate shell commands to build the specs
    print('mkdir -p', args.outdir)

    # Generate extended spec with required extensions + previously ratified
    # language.
    print(f'echo DEBUG: Making extended spec {specFileName}')
    extendedSpec = makeTarget(args.outdir,
                              extensions=requiredexts.union(extraexts),
                              submitFileName=specFileName,
                              title=args.title,
                              target=target)

    baseFileName = 'base-' + specFileName
    if args.basespec or args.diffspec:
        # Generate baseline spec with just previously ratified language
        print(f'echo DEBUG: Making base spec {baseFileName}')
        baseSpec = makeTarget(args.outdir,
                              extensions=extraexts,
                              submitFileName=baseFileName,
                              title='(with only ratified extensions)',
                              target=target)

    # Reorganize and rename them, and generate the diff spec
    diffFileName = 'diff-' + specFileName
    if args.diffspec:
        print(f'echo DEBUG: Making diff spec {diffFileName}')
        print('')
        print('cd scripts/htmldiff')
        print(f'./htmldiff "{baseSpec}" "{extendedSpec}" > "{args.outdir}/html/{diffFileName}.html"')
        print('cd ../../')

    if not args.basespec:
        print(f'echo DEBUG: Removing base spec {args.outdir}/html/{baseFileName}.html')
        print(f'rm -f {args.outdir}/html/{baseFileName}.html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-extension', action='append',
                        default=[],
                        help='Specify a required extension or extensions to add to targets')
    parser.add_argument('-extradepend', action='append',
                        default=[],
                        help='(Currently ignored) Specify an extension that is a dependency of the required extension(s), but not discovered automatically')
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
    parser.add_argument('-basespec', action='store_true',
                        default=False,
                        help='Retain baseline specification after build')
    parser.add_argument('-diffspec', action='store_true',
                        default=True,
                        help='Generate HTML diff between baseline and extended specifications')

    args = parser.parse_args()

    # Look for scripts/extdependency.py
    # This requires makeSpec to be invoked from the repository root, but we
    # could derive that path.
    sys.path.insert(0, 'scripts')
    from extdependency import ApiDependencies

    apideps = ApiDependencies(args.registry, args.apiname)

    args.outdir = os.path.abspath(args.outdir)
    makeSubmit(args, apideps)
