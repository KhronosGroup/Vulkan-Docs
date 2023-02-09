#!/usr/bin/python3
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Used during build to preprocess VUs in chapter files.  In this process:

- Non-VU text is passed through without modification
- Current values of macros are recorded
- VUs in prose are passed through without modification
- Codified VUs are reformatted
- Includes of commonvalidity/ files are recursively processed, taking macros
  into account.  Each combination of macros produces a different output for the
  commonvalidity file and includes are modified to the generated output.  The
  include file is not inlined so build error lines meaningfully translate back
  to the source.

Usage: `vuprocessor.py -o outputpath [-stamp stampfile]`
"""

import argparse
import os
from pathlib import Path
import sys

from reflib import loadFile, resolveAndMkdir, logDiag, logWarn, logErr, setLogFile
import doctransformer
from check_spec_links import VulkanEntityDatabase
from vuAST import isCodifiedVU, VuAST, VuFormat, formatVU

from apiconventions import APIConventions
conventions = APIConventions()


class PreprocessCallbacks:
    """State and arguments for preprocessing.

    Used with DocTransformer to preprocess a file."""
    def __init__(self,
                 args,
                 entity_db,
                 filename,
                 macros,
                 commonvalidityDict):

        self.entity_db = entity_db
        self.args = args

        self.inCommonValidityPath = os.path.join(args.inpath, 'commonvalidity')
        """Base path to commonvalidity input."""

        self.outCommonValidityPath = resolveAndMkdir(os.path.join(args.outpath, 'commonvalidity'))
        """Base path to commonvalidity output."""

        self.filename = filename
        """Base name of file being read from."""

        self.vuPrefix = 'VUID'
        """Prefix of generated Valid Usage tags."""

        # Prime the macro dictionary from the input values if any, but do not
        # let it be modified out of the scope of this file.
        self.macros = dict(macros)
        """Dictionary of current macro values."""

        self.commonvalidityDict = commonvalidityDict
        """Common validity files need to be processed once per unique set of
        macros that may affect them.  Assuming

            ValidityOutputMap = map of macro -> unique id

        This is a map of commonvalidity filename -> ValidityOutputMap

        Common validity files are then processed after the chapters."""

        self.passed = True
        """Whether preprocessing was successful.  If codified VUs have errors,
        this will make sure the build fails."""

    def transformParagraph(self, para, state):
        # Pass through all non-VU paragraphs
        if not state.isVU:
            return para

        # Pass through all VUs written in prose
        if not isCodifiedVU(para[1:] if self.vuPrefix in para[0] else para):
            return para

        # Reformat the VU
        formatted, passed = formatVU(para, state.apiName, self.filename,
                                           state.lineNumber, self.vuPrefix,
                                           VuFormat.OUTPUT, self.entity_db,
                                           self.macros)
        if not passed:
            self.passed = False
            return para

        return formatted

    def getCommonValidityUniqueId(self, commonvalidityFilename):
        """Check if map[filename][macros] exists.  If so, return it and
        indicate that this combination is previously processed.  Otherwise, a
        new id is assigned to this combination and returned."""
        if commonvalidityFilename not in self.commonvalidityDict:
            self.commonvalidityDict[commonvalidityFilename] = {}

        macroDict = self.commonvalidityDict[commonvalidityFilename]
        macroKey = str(sorted(self.macros.items()))
        if macroKey in macroDict:
            return macroDict[macroKey], False

        # Note that due to `refpage` being different for every api token, this
        # is path is currently always hit.  `refpage` does affect VU
        # verification, so it should not be removed.
        uniqueId = len(macroDict)
        macroDict[macroKey] = uniqueId
        return uniqueId, True

    def transformInclude(self, line, state):
        # Check to see if this is in the form:
        #     include::{chapters}/commonvalidity/<foo>.adoc[]
        #
        # If so, extract foo, get an id from commonvalidityDict and if it is
        # new, recursively preprocess <foo>.adoc.
        commonvalidityInclude = 'include::{chapters}/commonvalidity/'
        commonvalidityIncludeEnd = '[]'
        if not line.startswith(commonvalidityInclude):
            return line

        assert(line.rstrip().endswith(commonvalidityIncludeEnd))
        inFilename = line.rstrip()[len(commonvalidityInclude):-len(commonvalidityIncludeEnd)]
        assert(inFilename.endswith(conventions.file_suffix))

        # Check whether this combination of file+macros was previously
        # processed.
        uniqueId, isNew = self.getCommonValidityUniqueId(inFilename)
        outFilename = (inFilename[:-len(conventions.file_suffix)] +
                       '_' + str(uniqueId) + conventions.file_suffix)

        # Change the line to include the id tag to make the processed file
        # unique for each set of macros.
        line = commonvalidityInclude + outFilename + commonvalidityIncludeEnd + '\n'

        # If new, recursively process the commonvalidity file
        if isNew:
            # Note: commonvalidity/ currently does not have subdirs
            infile = os.path.join(self.inCommonValidityPath, inFilename)
            outfile = os.path.join(self.outCommonValidityPath, outFilename)

            self.passed = preprocessFile(self.args, infile, outfile,
                                         self.entity_db, self.macros,
                                         self.commonvalidityDict) and self.passed

        return line

    def onMacro(self, line, state):
        # Parse the macro definition and record it
        assert(line[0] == ':')

        endingColon = line.find(':', 1)
        assert(endingColon != -1)

        macroName = line[1:endingColon]
        macroValue = line[endingColon + 1:].strip()

        self.macros[macroName] = macroValue

    def onEmbeddedVUConditional(self, state):
        # This is not supported.  reflow.py already complains about this.
        logErr('ifdef inside VU is disallowed')


def preprocessFile(args, infile, outfile, entity_db, macros, commonvalidityDict):
    print('Preprocessing: ' + infile)
    lines, _ = loadFile(infile)

    try:
        fp = open(outfile, 'w', encoding='utf8', newline='\n')
    except:
        logWarn('Cannot open output file', outfile, ':', sys.exc_info()[0])
        return

    passed = True

    if lines is not None:
        callback = PreprocessCallbacks(args, entity_db, infile, macros, commonvalidityDict)

        transformer = doctransformer.DocTransformer(infile,
                                                    outfile = fp,
                                                    callback = callback)

        transformer.transformFile(lines)
        passed = callback.passed

    fp.close()
    return passed


def preprocessFiles(args, entity_db, inpath, outpath):
    defaultMacros = {}
    commonvalidityDict = {}

    passed = True
    root, subdirs, files = next(os.walk(inpath))
    for file in files:
        if file.endswith(conventions.file_suffix):
            infile = os.path.join(root, file)
            outfile = os.path.join(outpath, file)
            passed = preprocessFile(args, infile, outfile, entity_db, defaultMacros, commonvalidityDict) and passed
    for subdir in subdirs:
        if os.path.basename(subdir) == 'commonvalidity':
            # Process commonvalidity files as they are encountered
            continue
        insubdir = os.path.join(root, subdir)
        outsubdir = resolveAndMkdir(os.path.join(outpath, subdir))
        passed = preprocessFiles(args, entity_db, insubdir, outsubdir) and passed

    return passed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-diag', action='store', dest='diagFile',
                        help='Set the diagnostic file')
    parser.add_argument('-warn', action='store', dest='warnFile',
                        help='Set the warning file')
    parser.add_argument('-log', action='store', dest='logFile',
                        help='Set the log file for both diagnostics and warnings')
    parser.add_argument('-o', action='store', dest='outpath',
                        help='Set the output path')
    parser.add_argument('-stamp', action='store', dest='stampfile',
                        help='File to touch on success')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')

    args = parser.parse_args()

    setLogFile(True,  True, args.logFile)
    setLogFile(True, False, args.diagFile)
    setLogFile(False, True, args.warnFile)

    args.inpath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'chapters'))
    args.outpath = resolveAndMkdir(args.outpath)

    entity_db = VulkanEntityDatabase()

    if not preprocessFiles(args, entity_db, args.inpath, args.outpath):
        # Fail build if there are errors
        sys.exit(1)

    # Touch the stamp file
    if args.stampfile is not None:
        Path(args.stampfile).touch()
