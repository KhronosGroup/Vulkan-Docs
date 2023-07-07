#!/usr/bin/python3
#
# Copyright 2016-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Used for automatic reflow of spec sources to satisfy the agreed layout to
minimize git churn.  Also used to insert identifying tags on explicit Valid
Usage statements.

Usage: `reflow.py [-noflow] [-tagvu] [-nextvu #] [-overwrite] [-out dir] [-suffix str] files`

- `-noflow` acts as a passthrough, instead of reflowing text. Other
  processing may occur.
- `-tagvu` generates explicit VUID tag for Valid Usage statements which
  do not already have them.
- `-nextvu #` starts VUID tag generation at the specified # instead of
  the value wired into the `reflow.py` script.
- `-overwrite` updates in place (can be risky, make sure there are backups)
- `-check FAIL|WARN` runs some consistency checks on markup. If the checks
  fail and the WARN option is given, the script will simply print a warning
  message. If the checks fail and the FAIL option is given, the script will
  exit with an error code. FAIL is for use with continuous integration
  scripts enforcing the checks.
- `-out` specifies directory to create output file in, default 'out'
- `-suffix` specifies suffix to add to output files, default ''
- `files` are asciidoc source files from the spec to reflow.
"""
# For error and file-loading interfaces only
import argparse
import os
import re
import sys
from reflib import loadFile, logDiag, logWarn, logErr, setLogFile, getBranch
from pathlib import Path
import doctransformer

# Vulkan-specific - will consolidate into scripts/ like OpenXR soon
sys.path.insert(0, 'xml')

from apiconventions import APIConventions
conventions = APIConventions()

# Patterns used to recognize interesting lines in an asciidoc source file.
# These patterns are only compiled once.

# Find the pname: or code: patterns in a Valid Usage statement
pnamePat = re.compile(r'pname:(?P<param>\{?\w+\}?)')
codePat = re.compile(r'code:(?P<param>\w+)')

# Text that (may) not end sentences

# A single letter followed by a period, typically a middle initial.
endInitial = re.compile(r'^[A-Z]\.$')
# An abbreviation, which does not (usually) end a line.
endAbbrev = re.compile(r'(e\.g|i\.e|c\.f|vs)\.$', re.IGNORECASE)

# Explicit Valid Usage list item with one or more leading asterisks
# The re.DOTALL is needed to prevent vuPat.search() from stripping
# the trailing newline.
vuPat = re.compile(r'^(?P<head>  [*]+)( *)(?P<tail>.*)', re.DOTALL)

# VUID with the numeric portion captured in the match object
vuidPat = re.compile(r'VUID-[^-]+-[^-]+-(?P<vuid>[0-9]+)')

# Pattern matching leading nested bullet points
global nestedVuPat
nestedVuPat = re.compile(r'^  \*\*')

class ReflowCallbacks:
    """State and arguments for reflowing.

    Used with DocTransformer to reflow a file."""
    def __init__(self,
                 filename,
                 vuidDict,
                 margin = 76,
                 breakPeriod = True,
                 reflow = True,
                 nextvu = None,
                 maxvu = None,
                 check = True):

        self.filename = filename
        """base name of file being read from."""

        self.check = check
        """Whether consistency checks must be performed."""

        self.margin = margin
        """margin to reflow text to."""

        self.breakPeriod = breakPeriod
        """True if justification should break to a new line after the end of a
        sentence."""

        self.breakInitial = True
        """True if justification should break to a new line after something
        that appears to be an initial in someone's name. **TBD**"""

        self.reflow = reflow
        """True if text should be reflowed, False to pass through unchanged."""

        self.vuPrefix = 'VUID'
        """Prefix of generated Valid Usage tags"""

        self.vuFormat = '{0}-{1}-{2}-{3:0>5d}'
        """Format string for generating Valid Usage tags.
        First argument is vuPrefix, second is command/struct name, third is
        parameter name, fourth is the tag number."""

        self.nextvu = nextvu
        """Integer to start tagging un-numbered Valid Usage statements with,
        or None if no tagging should be done."""

        self.maxvu = maxvu
        """Maximum tag to use for Valid Usage statements, or None if no
        tagging should be done."""

        self.vuidDict = vuidDict
        """Dictionary of VUID numbers found, containing a list of (file, VUID)
        on which that number was found.  This is used to warn on duplicate
        VUIDs."""

        self.warnCount = 0
        """Count of markup check warnings encountered."""

    def endSentence(self, word):
        """Return True if word ends with a sentence-period, False otherwise.

        Allows for contraction cases which will not end a line:

         - A single letter (if breakInitial is True)
         - Abbreviations: 'c.f.', 'e.g.', 'i.e.' (or mixed-case versions)"""
        if (word[-1:] != '.' or
            endAbbrev.search(word) or
                (self.breakInitial and endInitial.match(word))):
            return False

        return True

    def vuidAnchor(self, word):
        """Return True if word is a Valid Usage ID Tag anchor."""
        return (word[0:7] == '[[VUID-')

    def visitVUID(self, vuid, line):
        if vuid not in self.vuidDict:
            self.vuidDict[vuid] = []
        self.vuidDict[vuid].append([self.filename, line])

    def gatherVUIDs(self, para):
        """Gather VUID tags and add them to vuidDict.  Used to verify no-duplicate VUIDs"""
        for line in para:
            line = line.rstrip()

            matches = vuidPat.search(line)
            if matches is not None:
                vuid = matches.group('vuid')
                self.visitVUID(vuid, line)

    def addVUID(self, para, state):
        hangIndent = state.hangIndent

        """Generate and add VUID if necessary."""
        if not state.isVU or self.nextvu is None:
            return para, hangIndent

        # If:
        #   - this paragraph is in a Valid Usage block,
        #   - VUID tags are being assigned,
        # Try to assign VUIDs

        if nestedVuPat.search(para[0]):
            # Do not assign VUIDs to nested bullet points.
            # These are now allowed VU markup syntax, but will never
            # themselves be VUs, just subsidiary points.
            return para, hangIndent

        # Skip if there is already a VUID assigned
        if self.vuPrefix in para[0]:
            return para, hangIndent

        # If:
        #   - a tag is not already present, and
        #   - the paragraph is a properly marked-up list item
        # Then add a VUID tag starting with the next free ID.

        # Split the first line after the bullet point
        matches = vuPat.search(para[0])
        if matches is None:
            # There are only a few cases of this, and they are all
            # legitimate. Leave detecting this case to another tool
            # or hand inspection.
            # logWarn(self.filename + ': Unexpected non-bullet item in VU block (harmless if following an ifdef):',
            #         para[0])
            return para, hangIndent

        outPara = para

        logDiag('addVUID: Matched vuPat on line:', para[0], end='')
        head = matches.group('head')
        tail = matches.group('tail')

        # Find pname: or code: tags in the paragraph for the purposes of VUID
        # tag generation. pname:{attribute}s are prioritized to make sure
        # commonvalidity VUIDs end up being unique. Otherwise, the first pname:
        # or code: tag in the paragraph is used, which may not always be
        # correct, but should be highly reliable.
        pnameMatches = re.findall(pnamePat, ' '.join(para))
        codeMatches = re.findall(codePat, ' '.join(para))

        # Prioritize {attribute}s, but not the ones in the exception list
        # below.  These have complex expressions including ., ->, or [index]
        # which makes them unsuitable for VUID tags.  Ideally these would be
        # automatically discovered.
        attributeExceptionList = ['maxinstancecheck', 'regionsparam',
                                  'rayGenShaderBindingTableAddress',
                                  'rayGenShaderBindingTableStride',
                                  'missShaderBindingTableAddress',
                                  'missShaderBindingTableStride',
                                  'hitShaderBindingTableAddress',
                                  'hitShaderBindingTableStride',
                                  'callableShaderBindingTableAddress',
                                  'callableShaderBindingTableStride',
                                 ]
        attributeMatches = [match for match in pnameMatches if
                            match[0] == '{' and
                            match[1:-1] not in attributeExceptionList]
        nonattributeMatches = [match for match in pnameMatches if
                               match[0] != '{']

        if len(attributeMatches) > 0:
            paramName = attributeMatches[0]
        elif len(nonattributeMatches) > 0:
            paramName = nonattributeMatches[0]
        elif len(codeMatches) > 0:
            paramName = codeMatches[0]
        else:
            paramName = 'None'
            logWarn(self.filename,
                    'No param name found for VUID tag on line:',
                    para[0])

        # Transform:
        #
        #   * VU first line
        #
        # To:
        #
        #   * [[VUID]]
        #     VU first line
        #
        tagLine = (head + ' [[' +
                   self.vuFormat.format(self.vuPrefix,
                                        state.apiName,
                                        paramName,
                                        self.nextvu) + ']]\n')
        self.visitVUID(str(self.nextvu), tagLine)

        newLines = [tagLine]
        if tail.strip() != '':
            logDiag('transformParagraph first line matches bullet point -'
                    'single line, assuming hangIndent @ input line',
                    state.lineNumber)
            hangIndent = len(head) + 1
            newLines.append(''.ljust(hangIndent) + tail)

        logDiag('Assigning', self.vuPrefix, state.apiName, self.nextvu,
                ' on line:\n' + para[0], '->\n' + newLines[0] + 'END', '\n' + newLines[1] if len(newLines) > 1 else '')

        # Do not actually assign the VUID unless it is in the reserved range
        if self.nextvu <= self.maxvu:
            if self.nextvu == self.maxvu:
                logWarn('Skipping VUID assignment, no more VUIDs available')
            outPara = newLines + para[1:]
            self.nextvu = self.nextvu + 1

        return outPara, hangIndent

    def transformParagraph(self, para, state):
        """Reflow a given paragraph, respecting the paragraph lead and
        hanging indentation levels.

        The algorithm also respects trailing '+' signs that indicate embedded newlines,
        and will not reflow a very long word immediately after a bullet point.

        Just return the paragraph unchanged if the -noflow argument was
        given."""

        self.gatherVUIDs(para)

        # If this is a VU that is missing a VUID, add it to the paragraph now.
        para, hangIndent = self.addVUID(para, state)

        if not self.reflow:
            return para

        logDiag('transformParagraph lead indent = ', state.leadIndent,
                'hangIndent =', state.hangIndent,
                'para:', para[0], end='')

        # Total words processed (we care about the *first* word vs. others)
        wordCount = 0

        # Tracks the *previous* word processed. It must not be empty.
        prevWord = ' '

        # Track the previous line and paragraph being indented, if any
        outLine = None
        outPara = []

        for line in para:
            line = line.rstrip()
            words = line.split()

            # logDiag('transformParagraph: input line =', line)
            numWords = len(words) - 1

            for i in range(0, numWords + 1):
                word = words[i]
                wordLen = len(word)
                wordCount += 1

                endEscape = False
                if i == numWords and word in ('+', '-'):
                    # Trailing ' +' or ' -' must stay on the same line
                    endEscape = word
                    # logDiag('transformParagraph last word of line =', word,
                    #         'prevWord =', prevWord, 'endEscape =', endEscape)
                else:
                    # logDiag('transformParagraph wordCount =', wordCount,
                    #         'word =', word, 'prevWord =', prevWord)
                    pass

                if wordCount == 1:
                    # The first word of the paragraph is treated specially.
                    # The loop logic becomes trickier if all this code is
                    # done prior to looping over lines and words, so all the
                    # setup logic is done here.

                    outLine = ''.ljust(state.leadIndent) + word
                    outLineLen = state.leadIndent + wordLen

                    # If the paragraph begins with a bullet point, generate
                    # a hanging indent level if there is not one already.
                    if doctransformer.beginBullet.match(para[0]):
                        bulletPoint = True
                        if len(para) > 1:
                            logDiag('transformParagraph first line matches bullet point',
                                    'but indent already hanging @ input line',
                                    state.lineNumber)
                        else:
                            logDiag('transformParagraph first line matches bullet point -'
                                    'single line, assuming hangIndent @ input line',
                                    state.lineNumber)
                            hangIndent = outLineLen + 1
                    else:
                        bulletPoint = False
                else:
                    # Possible actions to take with this word
                    #
                    # addWord - add word to current line
                    # closeLine - append line and start a new (null) one
                    # startLine - add word to a new line

                    # Default behavior if all the tests below fail is to add
                    # this word to the current line, and keep accumulating
                    # that line.
                    (addWord, closeLine, startLine) = (True, False, False)

                    # How long would this line be if the word were added?
                    newLen = outLineLen + 1 + wordLen

                    # Are we on the first word following a bullet point?
                    firstBullet = (wordCount == 2 and bulletPoint)

                    if endEscape:
                        # If the new word ends the input line with ' +',
                        # add it to the current line.

                        (addWord, closeLine, startLine) = (True, True, False)
                    elif self.vuidAnchor(word):
                        # If the new word is a Valid Usage anchor, break the
                        # line afterwards. Note that this should only happen
                        # immediately after a bullet point, but we do not
                        # currently check for this.
                        (addWord, closeLine, startLine) = (True, True, False)

                    elif newLen > self.margin:
                        if firstBullet:
                            # If the word follows a bullet point, add it to
                            # the current line no matter its length.

                            (addWord, closeLine, startLine) = (True, True, False)
                        elif doctransformer.beginBullet.match(word + ' '):
                            # If the word *is* a bullet point, add it to
                            # the current line no matter its length.
                            # This avoids an innocent inline '-' or '*'
                            # turning into a bogus bullet point.

                            (addWord, closeLine, startLine) = (True, True, False)
                        else:
                            # The word overflows, so add it to a new line.

                            (addWord, closeLine, startLine) = (False, True, True)
                    elif (self.breakPeriod and
                          (wordCount > 2 or not firstBullet) and
                          self.endSentence(prevWord)):
                        # If the previous word ends a sentence and
                        # breakPeriod is set, start a new line.
                        # The complicated logic allows for leading bullet
                        # points which are periods (implicitly numbered lists).
                        # @@@ But not yet for explicitly numbered lists.

                        (addWord, closeLine, startLine) = (False, True, True)

                    # Add a word to the current line
                    if addWord:
                        if outLine:
                            outLine += ' ' + word
                            outLineLen = newLen
                        else:
                            # Fall through to startLine case if there is no
                            # current line yet.
                            startLine = True

                    # Add current line to the output paragraph. Force
                    # starting a new line, although we do not yet know if it
                    # will ever have contents.
                    if closeLine:
                        if outLine:
                            outPara.append(outLine + '\n')
                            outLine = None

                    # Start a new line and add a word to it
                    if startLine:
                        outLine = ''.ljust(hangIndent) + word
                        outLineLen = hangIndent + wordLen

                # Track the previous word, for use in breaking at end of
                # a sentence
                prevWord = word

        # Add last line to the output paragraph.
        if outLine:
            outPara.append(outLine + '\n')

        return outPara

    def onEmbeddedVUConditional(self, state):
        if self.check:
            logWarn('Detected embedded Valid Usage conditional: {}:{}'.format(
                    self.filename, state.lineNumber - 1))
            # Keep track of warning check count
            self.warnCount = self.warnCount + 1

def reflowFile(filename, args):
    logDiag('reflow: filename', filename)

    # Output file handle and reflow object for this file. There are no race
    # conditions on overwriting the input, but it is not recommended unless
    # you have backing store such as git.

    lines, newline_string = loadFile(filename)
    if lines is None:
        return

    if args.overwrite:
        outFilename = filename
    else:
        outDir = Path(args.outDir).resolve()
        outDir.mkdir(parents=True, exist_ok=True)

        outFilename = str(outDir / (os.path.basename(filename) + args.suffix))

    if args.nowrite:
        fp = None
    else:
        try:
            fp = open(outFilename, 'w', encoding='utf8', newline=newline_string)
        except:
            logWarn('Cannot open output file', outFilename, ':', sys.exc_info()[0])
            return

    callback = ReflowCallbacks(filename,
                               args.vuidDict,
                               margin = args.margin,
                               reflow = not args.noflow,
                               nextvu = args.nextvu,
                               maxvu = args.maxvu,
                               check = args.check)

    transformer = doctransformer.DocTransformer(filename,
                                                outfile = fp,
                                                callback = callback)

    transformer.transformFile(lines)

    if fp is not None:
        fp.close()

    # Update the 'nextvu' value
    if args.nextvu != callback.nextvu:
        logWarn('Updated nextvu to', callback.nextvu, 'after file', filename)
        args.nextvu = callback.nextvu

    args.warnCount += callback.warnCount

def reflowAllAdocFiles(folder_to_reflow, args):
    for root, subdirs, files in os.walk(folder_to_reflow):
        for file in files:
            if file.endswith(conventions.file_suffix):
                file_path = os.path.join(root, file)
                reflowFile(file_path, args)
        for subdir in subdirs:
            sub_folder = os.path.join(root, subdir)
            print('Sub-folder = %s' % sub_folder)
            if subdir.lower() not in conventions.spec_no_reflow_dirs:
                print('   Parsing = %s' % sub_folder)
                reflowAllAdocFiles(sub_folder, args)
            else:
                print('   Skipping = %s' % sub_folder)

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
    parser.add_argument('-nowrite', action='store_true',
                        help='Do not write output files, for use with -check')
    parser.add_argument('-check', action='store', dest='check',
                        help='Run markup checks and warn if WARN option is given, error exit if FAIL option is given')
    parser.add_argument('-checkVUID', action='store', dest='checkVUID',
                        help='Detect duplicated VUID numbers and warn if WARN option is given, error exit if FAIL option is given')
    parser.add_argument('-tagvu', action='store_true',
                        help='Tag un-tagged Valid Usage statements starting at the value wired into reflow.py')
    parser.add_argument('-nextvu', action='store', dest='nextvu', type=int,
                        default=None,
                        help='Tag un-tagged Valid Usage statements starting at the specified base VUID instead of the value wired into reflow.py')
    parser.add_argument('-maxvu', action='store', dest='maxvu', type=int,
                        default=None,
                        help='Specify maximum VUID instead of the value wired into vuidCounts.py')
    parser.add_argument('-branch', action='store', dest='branch',
                        help='Specify branch to assign VUIDs for')
    parser.add_argument('-noflow', action='store_true', dest='noflow',
                        help='Do not reflow text. Other actions may apply')
    parser.add_argument('-margin', action='store', type=int, dest='margin',
                        default='76',
                        help='Width to reflow text, defaults to 76 characters')
    parser.add_argument('-suffix', action='store', dest='suffix',
                        default='',
                        help='Set the suffix added to updated file names (default: none)')
    parser.add_argument('files', metavar='filename', nargs='*',
                        help='a filename to reflow text in')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')

    args = parser.parse_args()

    setLogFile(True,  True, args.logFile)
    setLogFile(True, False, args.diagFile)
    setLogFile(False, True, args.warnFile)

    if args.overwrite:
        logWarn("reflow.py: will overwrite all input files")

    errors = ''
    if args.branch is None:
        (args.branch, errors) = getBranch()
    if args.branch is None:
        # This is not fatal unless VUID assignment is required
        if args.tagvu:
            logErr('Cannot determine current git branch, so cannot assign VUIDs:', errors)

    if args.tagvu and args.nextvu is None:
        # Moved here since vuidCounts is only needed in the internal
        # repository
        from vuidCounts import vuidCounts

        if args.branch not in vuidCounts:
            logErr('Branch', args.branch, 'not in vuidCounts, cannot continue')
        maxVUID = vuidCounts[args.branch][1]
        startVUID = vuidCounts[args.branch][2]
        args.nextvu = startVUID
        args.maxvu = maxVUID

    if args.nextvu is not None:
        logWarn('Tagging untagged Valid Usage statements starting at', args.nextvu)

    # Count of markup check warnings encountered
    # This is added to the argparse structure
    args.warnCount = 0

    # Dictionary of VUID numbers found, containing a list of (file, VUID) on
    # which that number was found
    # This is added to the argparse structure
    args.vuidDict = {}

    # If no files are specified, reflow the entire specification chapters folder
    if not args.files:
        folder_to_reflow = conventions.spec_reflow_path
        logWarn('Reflowing all asciidoc files under', folder_to_reflow)
        reflowAllAdocFiles(folder_to_reflow, args)
    else:
        for file in args.files:
            reflowFile(file, args)

    if args.warnCount > 0:
        if args.check == 'FAIL':
            logErr('Failed with', args.warnCount, 'markup errors detected.\n' +
                   'To fix these, you can take actions such as:\n' +
                   '  * Moving conditionals outside VU start / end without changing VU meaning\n' +
                   '  * Refactor conditional text using terminology defined conditionally outside the VU itself\n' +
                   '  * Remove the conditional (allowable when this just affects command / structure / enum names)\n')
        else:
            logWarn('Total warning count for markup issues is', args.warnCount)

    # Look for duplicated VUID numbers
    if args.checkVUID:
        dupVUIDs = 0
        for vuid in sorted(args.vuidDict):
            found = args.vuidDict[vuid]
            if len(found) > 1:
                logWarn('Duplicate VUID number {} found in files:'.format(vuid))
                for (file, vuidLine) in found:
                    logWarn('    {}: {}'.format(file, vuidLine))
                dupVUIDs = dupVUIDs + 1

        if dupVUIDs > 0:
            if args.checkVUID == 'FAIL':
                logErr('Failed with', dupVUIDs, 'duplicated VUID numbers found.\n' +
                       'To fix this, either convert these to commonvalidity VUs if possible, or strip\n' +
                       'the VUIDs from all but one of the duplicates and regenerate new ones.')
            else:
                logWarn('Total number of duplicated VUID numbers is', dupVUIDs)

    if args.nextvu is not None and args.nextvu != startVUID:
        # Update next free VUID to assign
        vuidCounts[args.branch][2] = args.nextvu
        try:
            reflow_count_file_path = os.path.dirname(os.path.realpath(__file__))
            reflow_count_file_path += '/vuidCounts.py'
            reflow_count_file = open(reflow_count_file_path, 'w', encoding='utf8')
            print('# Do not edit this file, unless reserving a new VUID range', file=reflow_count_file)
            print('# VUID ranges reserved for branches', file=reflow_count_file)
            print('# Key is branch name, value is [ start, end, nextfree ]', file=reflow_count_file)
            print('# New reservations must be made by MR to main branch', file=reflow_count_file)
            print('vuidCounts = {', file=reflow_count_file)
            for key in sorted(vuidCounts.keys(), key=lambda k: vuidCounts[k][0]):
                counts = vuidCounts[key]
                print(f"    '{key}': [ {counts[0]}, {counts[1]}, {counts[2]} ],",
                    file=reflow_count_file)
            print('}', file=reflow_count_file)
            reflow_count_file.close()
        except:
            logWarn('Cannot open output count file vuidCounts.py', ':', sys.exc_info()[0])
