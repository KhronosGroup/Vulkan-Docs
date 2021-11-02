#!/usr/bin/python3
#
# Copyright 2016-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Used for automatic reflow of spec sources to satisfy the agreed layout to
minimize git churn. Most of the logic has to do with detecting asciidoc
markup or block types that *shouldn't* be reflowed (tables, code) and
ignoring them. It's very likely there are many asciidoc constructs not yet
accounted for in the script, our usage of asciidoc markup is intentionally
somewhat limited.

Also used to insert identifying tags on explicit Valid Usage statements.

Usage: `reflow.py [-noflow] [-tagvu] [-nextvu #] [-overwrite] [-out dir] [-suffix str] files`

- `-noflow` acts as a passthrough, instead of reflowing text. Other
  processing may occur.
- `-tagvu` generates explicit VUID tag for Valid Usage statements which
  don't already have them.
- `-nextvu #` starts VUID tag generation at the specified # instead of
  the value wired into the `reflow.py` script.
- `-overwrite` updates in place (can be risky, make sure there are backups)
- `-check FAIL|WARN` runs some simple sanity checks on markup. If the checks
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

# Vulkan-specific - will consolidate into scripts/ like OpenXR soon
sys.path.insert(0, 'xml')

from vkconventions import VulkanConventions as APIConventions
conventions = APIConventions()

# Markup that always ends a paragraph
#   empty line or whitespace
#   [block options]
#   [[anchor]]
#   //                  comment
#   <<<<                page break
#   :attribute-setting
#   macro-directive::terms
#   +                   standalone list item continuation
#   label::             labelled list - label must be standalone
endPara = re.compile(r'^( *|\[.*\]|//.*|<<<<|:.*|[a-z]+::.*|\+|.*::)$')

# Special case of markup ending a paragraph, used to track the current
# command/structure. This allows for either OpenXR or Vulkan API path
# conventions. Nominally it should use the file suffix defined by the API
# conventions (conventions.file_suffix), except that XR uses '.txt' for
# generated API include files, not '.adoc' like its other includes.
includePat = re.compile(
        r'include::(?P<directory_traverse>((../){1,4}|\{INCS-VAR\}/|\{generated\}/)(generated/)?)(?P<generated_type>[\w]+)/(?P<category>\w+)/(?P<entity_name>[^./]+).txt[\[][\]]')

# Find the first pname: or code: pattern in a Valid Usage statement
pnamePat = re.compile(r'pname:(?P<param>\{?\w+\}?)')
codePat = re.compile(r'code:(?P<param>\w+)')

# Markup that's OK in a contiguous paragraph but otherwise passed through
#   .anything (except .., which indicates a literal block)
#   === Section Titles
endParaContinue = re.compile(r'^(\.[^.].*|=+ .*)$')

# Markup for block delimiters whose contents *should* be reformatted
#   --   (exactly two)  (open block)
#   **** (4 or more)    (sidebar block - why do we have these?!)
#   ==== (4 or more)    (example block)
#   ____ (4 or more)    (quote block)
blockReflow = re.compile(r'^(--|[*=_]{4,})$')

# Fake block delimiters for "common" VU statements
blockCommonReflow = '// Common Valid Usage\n'

# Markup for block delimiters whose contents should *not* be reformatted
#   |=== (3 or more)  (table)
#   ++++ (4 or more)  (passthrough block)
#   .... (4 or more)  (literal block)
#   //// (4 or more)  (comment block)
#   ---- (4 or more)  (listing block)
#   ```  (3 or more)  (listing block)
#   **** (4 or more)  (sidebar block)
blockPassthrough = re.compile(r'^(\|={3,}|[`]{3}|[\-+./~]{4,})$')

# Markup for introducing lists (hanging paragraphs)
#   * bullet
#     ** bullet
#     -- bullet
#   . bullet
#   :: bullet (no longer supported by asciidoctor 2)
#   {empty}:: bullet
#   1. list item
beginBullet = re.compile(r'^ *([*\-.]+|\{empty\}::|::|[0-9]+[.]) ')

# Start of an asciidoctor conditional
#   ifdef::
#   ifndef::
conditionalStart = re.compile(r'^(ifdef|ifndef)::')

# Text that (may) not end sentences

# A single letter followed by a period, typically a middle initial.
endInitial = re.compile(r'^[A-Z]\.$')
# An abbreviation, which doesn't (usually) end a line.
endAbbrev = re.compile(r'(e\.g|i\.e|c\.f|vs)\.$', re.IGNORECASE)

class ReflowState:
    """State machine for reflowing.

    Represents the state of the reflow operation"""
    def __init__(self,
                 filename,
                 margin = 76,
                 file = sys.stdout,
                 breakPeriod = True,
                 reflow = True,
                 nextvu = None,
                 maxvu = None):

        self.blockStack = [ None ]
        """The last element is a line with the asciidoc block delimiter that's currently in effect,
        such as '--', '----', '****', '======', or '+++++++++'.
        This affects whether or not the block contents should be formatted."""

        self.reflowStack = [ True ]
        """The last element is True or False if the current blockStack contents
        should be reflowed."""
        self.vuStack = [ False ]
        """the last element is True or False if the current blockStack contents
        are an explicit Valid Usage block."""

        self.margin = margin
        """margin to reflow text to."""

        self.para = []
        """list of lines in the paragraph being accumulated.
        When this is non-empty, there is a current paragraph."""

        self.lastTitle = False
        """true if the previous line was a document title line
        (e.g. :leveloffset: 0 - no attempt to track changes to this is made)."""

        self.leadIndent = 0
        """indent level (in spaces) of the first line of a paragraph."""

        self.hangIndent = 0
        """indent level of the remaining lines of a paragraph."""

        self.file = file
        """file handle to write to."""

        self.filename = filename
        """base name of file being read from."""

        self.lineNumber = 0
        """line number being read from the input file."""

        self.breakPeriod = breakPeriod
        """True if justification should break to a new line after the end of a sentence."""

        self.breakInitial = True
        """True if justification should break to a new line after
        something that appears to be an initial in someone's name. **TBD**"""

        self.reflow = reflow
        """True if text should be reflowed, False to pass through unchanged."""

        self.vuPrefix = 'VUID'
        """Prefix of generated Valid Usage tags"""

        self.vuFormat = '{0}-{1}-{2}-{3:0>5d}'
        """Format string for generating Valid Usage tags.
        First argument is vuPrefix, second is command/struct name, third is parameter name, fourth is the tag number."""

        self.nextvu = nextvu
        """Integer to start tagging un-numbered Valid Usage statements with,
        or None if no tagging should be done."""

        self.maxvu = maxvu
        """Maximum tag to use for Valid Usage statements, or None if no
        tagging should be done."""

        self.defaultApiName = '{refpage}'
        self.apiName = self.defaultApiName
        """String name of a Vulkan structure or command for VUID tag
        generation, or {refpage} if one hasn't been included in this file
        yet."""

    def incrLineNumber(self):
        self.lineNumber = self.lineNumber + 1

    def printLines(self, lines):
        """Print an array of lines with newlines already present"""
        if len(lines) > 0:
            logDiag(':: printLines:', len(lines), 'lines: ', lines[0], end='')

        if self.file is not None:
            for line in lines:
                print(line, file=self.file, end='')

    def endSentence(self, word):
        """Return True if word ends with a sentence-period, False otherwise.

        Allows for contraction cases which won't end a line:

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

    def isOpenBlockDelimiter(self, line):
        """Returns True if line is an open block delimiter."""
        return line[0:2] == '--'

    def reflowPara(self):
        """Reflow the current paragraph, respecting the paragraph lead and
        hanging indentation levels.

        The algorithm also respects trailing '+' signs that indicate embedded newlines,
        and will not reflow a very long word immediately after a bullet point.

        Just return the paragraph unchanged if the -noflow argument was
        given."""
        if not self.reflow:
            return self.para

        logDiag('reflowPara lead indent = ', self.leadIndent,
                'hangIndent =', self.hangIndent,
                'para:', self.para[0], end='')

        # Total words processed (we care about the *first* word vs. others)
        wordCount = 0

        # Tracks the *previous* word processed. It must not be empty.
        prevWord = ' '

        # Track the previous line and paragraph being indented, if any
        outLine = None
        outPara = []

        for line in self.para:
            line = line.rstrip()
            words = line.split()

            # logDiag('reflowPara: input line =', line)
            numWords = len(words) - 1

            for i in range(0, numWords + 1):
                word = words[i]
                wordLen = len(word)
                wordCount += 1

                endEscape = False
                if i == numWords and word == '+':
                    # Trailing ' +' must stay on the same line
                    endEscape = word
                    # logDiag('reflowPara last word of line =', word, 'prevWord =', prevWord, 'endEscape =', endEscape)
                else:
                    pass
                    # logDiag('reflowPara wordCount =', wordCount, 'word =', word, 'prevWord =', prevWord)

                if wordCount == 1:
                    # The first word of the paragraph is treated specially.
                    # The loop logic becomes trickier if all this code is
                    # done prior to looping over lines and words, so all the
                    # setup logic is done here.

                    outPara = []
                    outLine = ''.ljust(self.leadIndent) + word
                    outLineLen = self.leadIndent + wordLen

                    # If the paragraph begins with a bullet point, generate
                    # a hanging indent level if there isn't one already.
                    if beginBullet.match(self.para[0]):
                        bulletPoint = True
                        if len(self.para) > 1:
                            logDiag('reflowPara first line matches bullet point',
                                    'but indent already hanging @ input line',
                                    self.lineNumber)
                        else:
                            logDiag('reflowPara first line matches bullet point -'
                                    'single line, assuming hangIndent @ input line',
                                    self.lineNumber)
                            self.hangIndent = outLineLen + 1
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
                        # immediately after a bullet point, but we don't
                        # currently check for this.
                        (addWord, closeLine, startLine) = (True, True, False)
                    elif newLen > self.margin:
                        if firstBullet:
                            # If the word follows a bullet point, add it to
                            # the current line no matter its length.

                            (addWord, closeLine, startLine) = (True, True, False)
                        elif beginBullet.match(word + ' '):
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
                            # Fall through to startLine case if there's no
                            # current line yet.
                            startLine = True

                    # Add current line to the output paragraph. Force
                    # starting a new line, although we don't yet know if it
                    # will ever have contents.
                    if closeLine:
                        if outLine:
                            outPara.append(outLine + '\n')
                            outLine = None

                    # Start a new line and add a word to it
                    if startLine:
                        outLine = ''.ljust(self.hangIndent) + word
                        outLineLen = self.hangIndent + wordLen

                # Track the previous word, for use in breaking at end of
                # a sentence
                prevWord = word

        # Add this line to the output paragraph.
        if outLine:
            outPara.append(outLine + '\n')

        return outPara

    def emitPara(self):
        """Emit a paragraph, possibly reflowing it depending on the block context.

        Resets the paragraph accumulator."""
        if self.para != []:
            if self.vuStack[-1] and self.nextvu is not None:
                # If:
                #   - this paragraph is in a Valid Usage block,
                #   - VUID tags are being assigned,
                # Try to assign VUIDs

                if nestedVuPat.search(self.para[0]):
                    # Check for nested bullet points. These should not be
                    # assigned VUIDs, nor present at all, because they break
                    # the VU extractor.
                    logWarn(self.filename + ': Invalid nested bullet point in VU block:', self.para[0])
                elif self.vuPrefix not in self.para[0]:
                    # If:
                    #   - a tag is not already present, and
                    #   - the paragraph is a properly marked-up list item
                    # Then add a VUID tag starting with the next free ID.

                    # Split the first line after the bullet point
                    matches = vuPat.search(self.para[0])
                    if matches is not None:
                        logDiag('findRefs: Matched vuPat on line:', self.para[0], end='')
                        head = matches.group('head')
                        tail = matches.group('tail')

                        # Use the first pname: or code: tag in the paragraph as
                        # the parameter name in the VUID tag. This won't always
                        # be correct, but should be highly reliable.
                        for vuLine in self.para:
                            matches = pnamePat.search(vuLine)
                            if matches is not None:
                                break
                            matches = codePat.search(vuLine)
                            if matches is not None:
                                break

                        if matches is not None:
                            paramName = matches.group('param')
                        else:
                            paramName = 'None'
                            logWarn(self.filename,
                                    'No param name found for VUID tag on line:',
                                    self.para[0])

                        newline = (head + ' [[' +
                                   self.vuFormat.format(self.vuPrefix,
                                                        self.apiName,
                                                        paramName,
                                                        self.nextvu) + ']] ' + tail)

                        logDiag('Assigning', self.vuPrefix, self.apiName, self.nextvu,
                                ' on line:', self.para[0], '->', newline, 'END')

                        # Don't actually assign the VUID unless it's in the reserved range
                        if self.nextvu <= self.maxvu:
                            if self.nextvu == self.maxvu:
                                logWarn('Skipping VUID assignment, no more VUIDs available')
                            self.para[0] = newline
                            self.nextvu = self.nextvu + 1
                # else:
                #     There are only a few cases of this, and they're all
                #     legitimate. Leave detecting this case to another tool
                #     or hand inspection.
                #     logWarn(self.filename + ': Unexpected non-bullet item in VU block (harmless if following an ifdef):',
                #             self.para[0])

            if self.reflowStack[-1]:
                self.printLines(self.reflowPara())
            else:
                self.printLines(self.para)

        # Reset the paragraph, including its indentation level
        self.para = []
        self.leadIndent = 0
        self.hangIndent = 0

    def endPara(self, line):
        """'line' ends a paragraph and should itself be emitted.
        line may be None to indicate EOF or other exception."""
        logDiag('endPara line', self.lineNumber, ': emitting paragraph')

        # Emit current paragraph, this line, and reset tracker
        self.emitPara()

        if line:
            self.printLines( [ line ] )

    def endParaContinue(self, line):
        """'line' ends a paragraph (unless there's already a paragraph being
        accumulated, e.g. len(para) > 0 - currently not implemented)"""
        self.endPara(line)

    def endBlock(self, line, reflow = False, vuBlock = False):
        """'line' begins or ends a block.

        If beginning a block, tag whether or not to reflow the contents.

        vuBlock is True if the previous line indicates this is a Valid Usage block."""
        self.endPara(line)

        if self.blockStack[-1] == line:
            logDiag('endBlock line', self.lineNumber,
                    ': popping block end depth:', len(self.blockStack),
                    ':', line, end='')

            # Reset apiName at the end of an open block.
            # Open blocks cannot be nested (at present), so this is safe.
            if self.isOpenBlockDelimiter(line):
                logDiag('reset apiName to empty at line', self.lineNumber)
                self.apiName = self.defaultApiName
            else:
                logDiag('NOT resetting apiName to default at line', self.lineNumber)

            self.blockStack.pop()
            self.reflowStack.pop()
            self.vuStack.pop()
        else:
            # Start a block
            self.blockStack.append(line)
            self.reflowStack.append(reflow)
            self.vuStack.append(vuBlock)

            logDiag('endBlock reflow =', reflow, ' line', self.lineNumber,
                    ': pushing block start depth', len(self.blockStack),
                    ':', line, end='')

    def endParaBlockReflow(self, line, vuBlock):
        """'line' begins or ends a block. The paragraphs in the block *should* be
        reformatted (e.g. a NOTE)."""
        self.endBlock(line, reflow = True, vuBlock = vuBlock)

    def endParaBlockPassthrough(self, line):
        """'line' begins or ends a block. The paragraphs in the block should
        *not* be reformatted (e.g. a code listing)."""
        self.endBlock(line, reflow = False)

    def addLine(self, line):
        """'line' starts or continues a paragraph.

        Paragraphs may have "hanging indent", e.g.

        ```
          * Bullet point...
            ... continued
        ```

        In this case, when the higher indentation level ends, so does the
        paragraph."""
        logDiag('addLine line', self.lineNumber, ':', line, end='')

        # See https://stackoverflow.com/questions/13648813/what-is-the-pythonic-way-to-count-the-leading-spaces-in-a-string
        indent = len(line) - len(line.lstrip())

        # A hanging paragraph ends due to a less-indented line.
        if self.para != [] and indent < self.hangIndent:
            logDiag('addLine: line reduces indentation, emit paragraph')
            self.emitPara()

        # A bullet point (or something that looks like one) always ends the
        # current paragraph.
        if beginBullet.match(line):
            logDiag('addLine: line matches beginBullet, emit paragraph')
            self.emitPara()

        if self.para == []:
            # Begin a new paragraph
            self.para = [ line ]
            self.leadIndent = indent
            self.hangIndent = indent
        else:
            # Add a line to a paragraph. Increase the hanging indentation
            # level - once.
            if self.hangIndent == self.leadIndent:
                self.hangIndent = indent
            self.para.append(line)

def apiMatch(oldname, newname):
    """Returns whether oldname and newname match, up to an API suffix.
       This should use the API map instead of this heuristic, since aliases
       like VkPhysicalDeviceVariablePointerFeatures ->
       VkPhysicalDeviceVariablePointersFeatures are not recognized."""
    upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return oldname.rstrip(upper) == newname.rstrip(upper)

def reflowFile(filename, args):
    logDiag('reflow: filename', filename)

    lines = loadFile(filename)
    if lines is None:
        return

    # Output file handle and reflow object for this file. There are no race
    # conditions on overwriting the input, but it's not recommended unless
    # you have backing store such as git.

    if args.overwrite:
        outFilename = filename
    else:
        outFilename = args.outDir + '/' + os.path.basename(filename) + args.suffix

    if args.nowrite:
        fp = None
    else:
        try:
            fp = open(outFilename, 'w', encoding='utf8')
        except:
            logWarn('Cannot open output file', outFilename, ':', sys.exc_info()[0])
            return

    state = ReflowState(filename,
                        margin = args.margin,
                        file = fp,
                        reflow = not args.noflow,
                        nextvu = args.nextvu,
                        maxvu = args.maxvu)

    for line in lines:
        state.incrLineNumber()

        # Is this a title line (leading '= ' followed by text)?
        thisTitle = False

        matches = vuidPat.search(line)
        if matches is not None:
            # If we found a VUID pattern, add the (filename,line) it was
            # found at to a list for that VUID, to find duplicates.
            vuid = matches.group('vuid')
            if vuid not in args.vuidDict:
                args.vuidDict[vuid] = []
            args.vuidDict[vuid].append([filename, line])

        # The logic here is broken. If we're in a non-reflowable block and
        # this line *doesn't* end the block, it should always be
        # accumulated.

        # Test for a blockCommonReflow delimiter comment first, to avoid
        # treating it solely as a end-Paragraph marker comment.
        if line == blockCommonReflow:
            # Starting or ending a pseudo-block for "common" VU statements.
            state.endParaBlockReflow(line, vuBlock = True)

        elif blockReflow.match(line):
            # Starting or ending a block whose contents may be reflowed.
            # Blocks cannot be nested.

            # Is this is an explicit Valid Usage block?
            vuBlock = (state.lineNumber > 1 and
                       lines[state.lineNumber-2] == '.Valid Usage\n')

            state.endParaBlockReflow(line, vuBlock)

        elif endPara.match(line):
            # Ending a paragraph. Emit the current paragraph, if any, and
            # prepare to begin a new paragraph.

            state.endPara(line)

            # If this is an include:: line starting the definition of a
            # structure or command, track that for use in VUID generation.

            matches = includePat.search(line)
            if matches is not None:
                generated_type = matches.group('generated_type')
                include_type = matches.group('category')
                if generated_type == 'api' and include_type in ('protos', 'structs', 'funcpointers'):
                    apiName = matches.group('entity_name')
                    if state.apiName != state.defaultApiName:
                        # This happens when there are multiple API include
                        # lines in a single block. The style guideline is to
                        # always place the API which others are promoted to
                        # first. In virtually all cases, the promoted API
                        # will differ solely in the vendor suffix (or
                        # absence of it), which is benign.
                        if not apiMatch(state.apiName, apiName):
                            logDiag(f'Promoted API name mismatch at line {state.lineNumber}: {apiName} does not match state.apiName (this is OK if it is just a spelling alias)')
                    else:
                        state.apiName = apiName

        elif endParaContinue.match(line):
            # For now, always just end the paragraph.
            # Could check see if len(para) > 0 to accumulate.

            state.endParaContinue(line)

            # If it's a title line, track that
            if line[0:2] == '= ':
                thisTitle = True

        elif blockPassthrough.match(line):
            # Starting or ending a block whose contents must not be reflowed.
            # These are tables, etc. Blocks cannot be nested.

            state.endParaBlockPassthrough(line)
        elif state.lastTitle:
            # The previous line was a document title line. This line
            # is the author / credits line and must not be reflowed.

            state.endPara(line)
        else:
            # Just accumulate a line to the current paragraph. Watch out for
            # hanging indents / bullet-points and track that indent level.

            state.addLine(line)

            # This test looks for disallowed conditionals inside Valid Usage
            # blocks, by checking if (a) this line does not start a new VU
            # (bullet point) and (b) the previous line starts an asciidoctor
            # conditional (ifdef:: or ifndef::).

            if (args.check
                and state.vuStack[-1]
                and not beginBullet.match(line)
                and conditionalStart.match(lines[state.lineNumber-2])):

                logWarn('Detected embedded Valid Usage conditional: {}:{}'.format(
                        filename, state.lineNumber - 1))
                # Keep track of warning check count
                args.warnCount = args.warnCount + 1

        state.lastTitle = thisTitle

    # Cleanup at end of file
    state.endPara(None)

    # Check for sensible block nesting
    if len(state.blockStack) > 1:
        logWarn('file', filename,
                'mismatched asciidoc block delimiters at EOF:',
                state.blockStack[-1])

    if fp is not None:
        fp.close()

    # Update the 'nextvu' value
    if args.nextvu != state.nextvu:
        logWarn('Updated nextvu to', state.nextvu, 'after file', filename)
        args.nextvu = state.nextvu

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

# Patterns used to recognize interesting lines in an asciidoc source file.
# These patterns are only compiled once.

# Explicit Valid Usage list item with one or more leading asterisks
# The re.DOTALL is needed to prevent vuPat.search() from stripping
# the trailing newline.
vuPat = re.compile(r'^(?P<head>  [*]+)( *)(?P<tail>.*)', re.DOTALL)

# VUID with the numeric portion captured in the match object
vuidPat = re.compile(r'VUID-[^-]+-[^-]+-(?P<vuid>[0-9]+)')

# Pattern matching leading nested bullet points
global nestedVuPat
nestedVuPat = re.compile(r'^  \*\*')

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
                        help='Specify start VUID to use instead of the value wired into vuidCounts.py')
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

    print('args.margin = ', args.margin)

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

    # Dictionary of VUID numbers found, containing a list of (file, line) on
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
                for (file, line) in found:
                    logWarn('    {}: {}'.format(file, line))
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
            print('# Do not edit this file!', file=reflow_count_file)
            print('# VUID ranges reserved for branches', file=reflow_count_file)
            print('# Key is branch name, value is [ start, end, nextfree ]', file=reflow_count_file)
            print('vuidCounts = {', file=reflow_count_file)
            for key in sorted(vuidCounts):
                print("    '{}': [ {}, {}, {} ],".format(
                    key,
                    vuidCounts[key][0],
                    vuidCounts[key][1],
                    vuidCounts[key][2]),
                    file=reflow_count_file)
            print('}', file=reflow_count_file)
            reflow_count_file.close()
        except:
            logWarn('Cannot open output count file vuidCounts.py', ':', sys.exc_info()[0])
