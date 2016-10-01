#!/usr/bin/python3
#
# Copyright (c) 2016 The Khronos Group Inc.
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

# Used for automatic reflow of Vulkan spec to satisfy the agreed layout to
# minimize git churn. Most of the logic has to to with detecting asciidoc
# markup or block types that *shouldn't* be reflowed (tables, code) and
# ignoring them. It's very likely there are many asciidoc constructs not yet
# accounted for in the script, our usage of asciidoc markup is intentionally
# somewhat limited.

# Usage: reflow.py [-overwrite] [-out dir] [-suffix str] files
#   -overwrite updates in place (usually not desired, and risky)
#   -out specifies directory to create output file in, default 'out'
#   -suffix specifies suffix to add to output files, default ''
#   files are asciidoc source files from the Vulkan spec to reflow.

# For error and file-loading interfaces only
from reflib import *

import argparse, copy, os, pdb, re, string, sys

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
endPara = re.compile('^( *|\[.*\]|//.*|<<<<|:.*|[a-z]+::.*|\+|.*::)$')

# Markup that's OK in a contiguous paragraph but otherwise passed through
#   .anything
#   === Section Titles
endParaContinue = re.compile('^(\..*|=+ .*)$')

# Markup for block delimiters whose contents *should* be reformatted
#   --   (exactly two)  (open block)
#   **** (4 or more)    (sidebar block - why do we have these?!)
#   ==== (4 or more)    (example block)
#   ____ (4 or more)    (quote block)
blockReflow = re.compile('^(--|[*=_]{4,})$')

# Markup for block delimiters whose contents should *not* be reformatted
#   |=== (3 or more)  (table)
#   ++++ (4 or more)  (passthrough block)
#   .... (4 or more)  (literal block)
#   //// (4 or more)  (comment block)
#   ---- (4 or more)  (listing block)
#   **** (4 or more)  (sidebar block)
blockPassthrough = re.compile('^(\|={3,}|[-+./]{4,})$')

# Markup for introducing bullet points (hanging paragraphs)
#   * bullet
#     ** bullet
#     -- bullet
#   . bullet
#   :: bullet
beginBullet = re.compile('^ *([*-]+|\.|::) ')

# Text that (may) not end sentences

# A single letter followed by a period, typically a middle initial.
endInitial = re.compile('^[[:upper:]]\.$')
# An abbreviation, which doesn't (usually) end a line.
endAbbrev = re.compile('(e\.g|i\.e|c\.f)\.$', re.IGNORECASE)

# State machine for reflowing.
#
# blockStack - The last element is a line with the asciidoc block delimiter
#   that's currently in effect, such as
#     '--', '----', '****', '======', or '+++++++++'.
#   This affects whether or not the block contents should be formatted.
# reflowStack - The last element is True or False if the current blockStack
#   contents should be reflowed
# margin - margin to reflow text to
# para - list of lines in the paragraph being accumulated. When this is
#   non-empty, there is a current paragraph.
# leadIndent - indent level (in spaces) of the first line of a paragraph.
# hangIndent - indent level of the remaining lines of a paragraph.
# file - file pointer to write to
# filename - base name of file being read from
# lineNumber - line number being read from the input file
# breakPeriod - True if justification should break to a new line after
#   the end of a sentence
# breakInitial - True if justification should break to a new
class ReflowState:
    """Represents the state of the reflow operation"""
    def __init__(self, filename, margin = 76, file = sys.stdout, breakPeriod = True):
        self.blockStack = [ None ]
        self.reflowStack = [ True ]
        self.margin = margin
        self.para = []
        self.leadIndent = 0
        self.hangIndent = 0
        self.file = file
        self.filename = filename
        self.lineNumber = 0
        self.breakPeriod = breakPeriod
        self.breakInitial = True

    def incrLineNumber(self):
        self.lineNumber = self.lineNumber + 1

    # Print an array of lines with newlines already present
    def printLines(self, lines):
        logDiag(':: printLines:', len(lines), 'lines: ', lines[0], end='')
        for line in lines:
            print(line, file=self.file, end='')

    # Returns True if word ends with a sentence-period, False otherwise. Allows
    # for contraction cases which won't end a line:
    #  - A single letter (if breakInitial is True)
    #  - Abbreviations: 'c.f.', 'e.g.', 'i.e.' (or mixed-case versions)
    def endSentence(self,word):
        if (word[-1:] != '.' or
            endAbbrev.search(word) or
            (self.breakInitial and endInitial.match(word))):
            return False
        else:
            return True

    # Reflow the current paragraph, respecting the paragraph lead and
    # hanging indentation levels. The algorithm also respects trailing '+'
    # signs that indicate imbedded newlines, and will not reflow a very long
    # word immediately after a bullet point.
    def reflowPara(self):
        logDiag('reflowPara lead indent = ', self.leadIndent,
                'hangIndent =', self.hangIndent,
                'para:', self.para[0], end='')

        # Total words processed (we care about the *first* word vs. others)
        wordCount = 0

        # Tracks the *previous* word processed. It must not be empty.
        prevWord = ' '

        #import pdb; pdb.set_trace()

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
                if (i == numWords and word == '+'):
                    # Trailing ' +' must stay on the same line
                    endEscape = word
                    # logDiag('reflowPara last word of line =', word, 'prevWord =', prevWord, 'endEscape =', endEscape)
                else:
                    True
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

                    if (endEscape):
                        # If the new word ends the input line with ' +',
                        # add it to the current line.

                        (addWord, closeLine, startLine) = (True, True, False)
                    elif newLen > self.margin:
                        if firstBullet:
                            # If the word follows a bullet point, add it to
                            # the current line no matter its length.

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
        if (outLine):
            outPara.append(outLine + '\n')

        return outPara

    # Emit a paragraph, possibly reflowing it depending on the block
    # context. Reset the paragraph accumulator.
    def emitPara(self):
        if self.para != []:
            if self.reflowStack[-1]:
                self.printLines(self.reflowPara())
            else:
                self.printLines(self.para)

        # Reset the paragraph, including its indentation level
        self.para = []
        self.leadIndent = 0
        self.hangIndent = 0

    # 'line' ends a paragraph and should itself be emitted.
    # line may be None to indicate EOF or other exception.
    def endPara(self, line):
        logDiag('endPara line', self.lineNumber, ': emitting paragraph')

        # Emit current paragraph, this line, and reset tracker
        self.emitPara()

        if line:
            self.printLines( [ line ] )

    # 'line' ends a paragraph (unless there's already a paragraph being
    # accumulated, e.g. len(para) > 0 - currently not implemented)
    def endParaContinue(self, line):
        self.endPara(line)

    # 'line' begins or ends a block. If beginning a block, tag whether or
    # not to reflow the contents.
    def endBlock(self, line, reflow = False):
        self.endPara(line)

        if self.blockStack[-1] == line:
            logDiag('endBlock line', self.lineNumber,
                    ': popping block end depth:', len(self.blockStack),
                    ':', line, end='')
            self.blockStack.pop()
            self.reflowStack.pop()
        else:
            # Start a block
            self.blockStack.append(line)
            self.reflowStack.append(reflow)

            logDiag('endBlock reflow =', reflow, ' line', self.lineNumber,
                    ': pushing block start depth', len(self.blockStack),
                    ':', line, end='')

    # 'line' begins or ends a block. The paragraphs in the block *should* be
    # reformatted (e.g. a NOTE).
    def endParaBlockReflow(self, line):
        self.endBlock(line, reflow = True)

    # 'line' begins or ends a block. The paragraphs in the block should
    # *not* be reformatted (e.g. a NOTE).
    def endParaBlockPassthrough(self, line):
        self.endBlock(line, reflow = False)

    # 'line' starts or continues a paragraph.
    # Paragraphs may have "hanging indent", e.g.
    #   * Bullet point...
    #     ... continued
    # In this case, when the higher indentation level ends, so does the
    # paragraph.
    def addLine(self, line):
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

def reflowFile(filename, overwrite, outDir, suffix):
    logDiag('reflow: filename', filename)

    lines = loadFile(filename)
    if (lines == None):
        return

    # Output file handle and reflow object for this file. There are no race
    # conditions on overwriting the input, but it's not recommended unless
    # you have backing store such as git.

    if overwrite:
        outFilename = filename
    else:
        outFilename = outDir + '/' + os.path.basename(filename) + suffix

    try:
        fp = open(outFilename, 'w')
    except:
        logWarn('Cannot open output file', filename, ':', sys.exc_info()[0])
        return None

    state = ReflowState(filename, file = fp)

    for line in lines:
        state.incrLineNumber()

        # The logic here is broken. If we're in a non-reflowable block and
        # this line *doesn't* end the block, it should always be
        # accumulated.

        if endPara.match(line):
            # Ending a paragraph. Emit the current paragraph, if any, and
            # prepare to begin a new paragraph.

            state.endPara(line)
        elif endParaContinue.match(line):
            # For now, always just end the paragraph.
            # Could check see if len(para) > 0 to accumulate.

            state.endParaContinue(line)
        elif blockReflow.match(line):
            # Starting or ending a block whose contents may be reflowed.
            # Blocks cannot be nested.

            state.endParaBlockReflow(line)
        elif blockPassthrough.match(line):
            # Starting or ending a block whose contents must not be reflowed.
            # These are tables, etc. Blocks cannot be nested.

            state.endParaBlockPassthrough(line)
        else:
            # Just accumulate a line to the current paragraph. Watch out for
            # hanging indents / bullet-points and track that indent level.

            state.addLine(line)

    # Cleanup at end of file
    state.endPara(None)

    # Sanity check on block nesting
    if len(state.blockStack) > 1:
        logWarn('file', filename,
                'mismatched asciidoc block delimiters at EOF:',
                state.blockStack[-1])

    fp.close()

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
                        help='a filename to reflow text in')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')

    results = parser.parse_args()

    setLogFile(True,  True, results.logFile)
    setLogFile(True, False, results.diagFile)
    setLogFile(False, True, results.warnFile)

    if (results.overwrite):
        logWarn('reflow.py: will overwrite all input files')

    for file in results.files:
        reflowFile(file, results.overwrite, results.outDir, results.suffix)
