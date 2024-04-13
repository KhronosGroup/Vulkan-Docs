# Copyright 2023-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Utilities for automatic transformation of spec sources.  Most of the logic
has to do with detecting asciidoc markup or block types that should not be
transformed (tables, code) and ignoring them.  It is very likely there are many
asciidoc constructs not yet accounted for in the script, our usage of asciidoc
markup is intentionally somewhat limited.
"""

import re
import sys
from reflib import logDiag, logWarn

# Vulkan-specific - will consolidate into scripts/ like OpenXR soon
sys.path.insert(0, 'xml')

from apiconventions import APIConventions
conventions = APIConventions()

# Start of an asciidoctor conditional
#   ifdef::
#   ifndef::
conditionalStart = re.compile(r'^(ifdef|ifndef)::')

# Markup that always ends a paragraph
#   empty line or whitespace
#   [block options]
#   [[anchor]]
#   //                  comment
#   <<<<                page break
#   :attribute-setting
#   macro-directive::terms
#   +                   standalone list item continuation
#   label::             labeled list - label must be standalone
endPara = re.compile(r'^( *|\[.*\]|//.*|<<<<|:.*|[a-z]+::.*|\+|.*::)$')

# Special case of markup ending a paragraph, used to track the current
# command/structure. This allows for either OpenXR or Vulkan API path
# conventions. Nominally it should use the file suffix defined by the API
# conventions (conventions.file_suffix), except that XR uses '.txt' for
# generated API include files, not '.adoc' like its other includes.
includePat = re.compile(
        r'include::(?P<directory_traverse>((../){1,4}|\{generated\}/)(generated/)?)(?P<generated_type>[\w]+)/(?P<category>\w+)/(?P<entity_name>[^./]+).adoc[\[][\]]')

# Markup that is OK in a contiguous paragraph but otherwise passed through
#   .anything (except .., which indicates a literal block)
#   === Section Titles
#   image::path_to_image[attributes]  (apparently a single colon is OK but less idiomatic)
endParaContinue = re.compile(r'^(\.[^.].*|=+ .*|image:.*\[.*\])$')

# Markup for block delimiters whose contents *should* be reformatted
#   --   (exactly two)  (open block)
#   **** (4 or more)    (sidebar block)
#   ==== (4 or more)    (example block)
#   ____ (4 or more)    (quote block)
blockTransform = re.compile(r'^(--|[*=_]{4,})$')

# Fake block delimiters for "common" VU statements
blockCommonTransform = '// Common Valid Usage\n'

# Markup for block delimiters whose contents should *not* be transformed
#   |=== (3 or more)  (table)
#   ```  (3 or more)  (listing block)
#   //// (4 or more)  (comment block)
#   ---- (4 or more)  (listing block)
#   .... (4 or more)  (literal block)
#   ++++ (4 or more)  (passthrough block)
blockPassthrough = re.compile(r'^(\|={3,}|[`]{3}|[\-+./]{4,})$')

# Markup for introducing lists (hanging paragraphs)
#   * bullet
#     ** bullet
#     -- bullet
#   . bullet
#   :: bullet (no longer supported by asciidoctor 2)
#   {empty}:: bullet
#   1. list item
#   <1> source listing callout
beginBullet = re.compile(r'^ *([-*.]+|\{empty\}::|::|[0-9]+[.]|<([0-9]+)>) ')

class TransformState:
    """State machine for transforming documents.

    Represents the state of the transform operation"""
    def __init__(self):
        self.blockStack = [ None ]
        """The last element is a line with the asciidoc block delimiter that is
        currently in effect, such as '--', '----', '****', '====', or '++++'.
        This affects whether or not the block contents should be transformed."""
        self.transformStack = [ True ]
        """The last element is True or False if the current blockStack contents
        should be transformed."""
        self.vuStack = [ False ]
        """the last element is True or False if the current blockStack contents
        are an explicit Valid Usage block."""

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

        self.lineNumber = 0
        """line number being read from the input file."""

        self.defaultApiName = '{refpage}'
        self.apiName = self.defaultApiName
        """String name of an API structure or command for VUID tag generation,
        or {refpage} if one has not been included in this file yet."""

    def incrLineNumber(self):
        self.lineNumber = self.lineNumber + 1

    def isOpenBlockDelimiter(self, line):
        """Returns True if line is an open block delimiter.
           This does not and should not match the listing block delimiter,
           which is used inside refpage blocks both as a listing block and,
           via an extension, as a nested open block."""
        return line.rstrip() == '--'

    def resetPara(self):
        """Reset the paragraph, including its indentation level"""
        self.para = []
        self.leadIndent = 0
        self.hangIndent = 0

    def endBlock(self, line, transform, vuBlock):
        """If beginning a block, tag whether or not to transform the contents.

        vuBlock is True if the previous line indicates this is a Valid Usage
        block."""
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
                logDiag('NOT resetting apiName to default at line',
                        self.lineNumber)

            self.blockStack.pop()
            self.transformStack.pop()
            self.vuStack.pop()
        else:
            # Start a block
            self.blockStack.append(line)
            self.transformStack.append(transform)
            self.vuStack.append(vuBlock)

            logDiag('endBlock transform =', transform, ' line', self.lineNumber,
                    ': pushing block start depth', len(self.blockStack),
                    ':', line, end='')

    def addLine(self, line, indent):
        """Add a line to the current paragraph"""
        if self.para == []:
            # Begin a new paragraph
            self.para = [line]
            self.leadIndent = indent
            self.hangIndent = indent
        else:
            # Add a line to a paragraph. Increase the hanging indentation
            # level - once.
            if self.hangIndent == self.leadIndent:
                self.hangIndent = indent
            self.para.append(line)


class TransformCallbackState:
    """State given to the transformer callback object, derived from
    TransformState."""
    def __init__(self, state):
        self.isVU = state.vuStack[-1] if len(state.vuStack) > 0 else False
        """Whether this paragraph is a VU."""

        self.apiName = state.apiName
        """String name of an API structure or command this paragraph belongs
        to."""

        self.leadIndent = state.leadIndent
        """indent level (in spaces) of the first line of a paragraph."""

        self.hangIndent = state.hangIndent
        """indent level of the remaining lines of a paragraph."""

        self.lineNumber = state.lineNumber
        """line number being read from the input file."""


class DocTransformer:
    """A transformer that recursively goes over all spec files under a path.

    The transformer goes over all spec files under a path and does some basic
    parsing.  In particular, it tracks which section the current text belongs
    to, whether it references a VU, etc and processes them in 'paragraph'
    granularity.
    The transformer takes a callback object with the following methods:

    - transformParagraph: Called when a paragraph is parsed.  The paragraph
      along with some information (such as whether it is a VU) is passed.  The
      function may transform the paragraph as necessary.
    - onEmbeddedVUConditional: Called when an embedded VU conditional is
      encountered.
    """
    def __init__(self,
                 filename,
                 outfile,
                 callback):
        self.filename = filename
        """base name of file being read from."""

        self.outfile = outfile
        """file handle to write to."""

        self.state = TransformState()
        """State of transformation"""

        self.callback = callback
        """The transformation callback object"""

    def printLines(self, lines):
        """Print an array of lines with newlines already present"""
        if len(lines) > 0:
            logDiag(':: printLines:', len(lines), 'lines: ', lines[0], end='')

        if self.outfile is not None:
            for line in lines:
                print(line, file=self.outfile, end='')

    def emitPara(self):
        """Emit a paragraph, possibly transforming it depending on the block
        context.

        Resets the paragraph accumulator."""
        if self.state.para != []:
            transformedPara = self.state.para

            if self.state.transformStack[-1]:
                callbackState = TransformCallbackState(self.state)

                transformedPara = self.callback.transformParagraph(
                        self.state.para,
                        callbackState)

            self.printLines(transformedPara)

        self.state.resetPara()

    def endPara(self, line):
        """'line' ends a paragraph and should itself be emitted.
        line may be None to indicate EOF or other exception."""
        logDiag('endPara line', self.state.lineNumber, ': emitting paragraph')

        # Emit current paragraph, this line, and reset tracker
        self.emitPara()

        if line:
            self.printLines([line])

    def endParaContinue(self, line):
        """'line' ends a paragraph (unless there is already a paragraph being
        accumulated, e.g. len(para) > 0 - currently not implemented)"""
        self.endPara(line)

    def endBlock(self, line, transform = False, vuBlock = False):
        """'line' begins or ends a block.

        If beginning a block, tag whether or not to transform the contents.

        vuBlock is True if the previous line indicates this is a Valid Usage
        block."""
        self.endPara(line)
        self.state.endBlock(line, transform, vuBlock)

    def endParaBlockTransform(self, line, vuBlock):
        """'line' begins or ends a block. The paragraphs in the block *should* be
        reformatted (e.g. a NOTE)."""
        self.endBlock(line, transform = True, vuBlock = vuBlock)

    def endParaBlockPassthrough(self, line):
        """'line' begins or ends a block. The paragraphs in the block should
        *not* be reformatted (e.g. a code listing)."""
        self.endBlock(line, transform = False)

    def addLine(self, line):
        """'line' starts or continues a paragraph.

        Paragraphs may have "hanging indent", e.g.

        ```
          * Bullet point...
            ... continued
        ```

        In this case, when the higher indentation level ends, so does the
        paragraph."""
        logDiag('addLine line', self.state.lineNumber, ':', line, end='')

        # See https://stackoverflow.com/questions/13648813/what-is-the-pythonic-way-to-count-the-leading-spaces-in-a-string
        indent = len(line) - len(line.lstrip())

        # A hanging paragraph ends due to a less-indented line.
        if self.state.para != [] and indent < self.state.hangIndent:
            logDiag('addLine: line reduces indentation, emit paragraph')
            self.emitPara()

        # A bullet point (or something that looks like one) always ends the
        # current paragraph.
        if beginBullet.match(line):
            logDiag('addLine: line matches beginBullet, emit paragraph')
            self.emitPara()

        self.state.addLine(line, indent)

    def apiMatch(self, oldname, newname):
        """Returns whether oldname and newname match, up to an API suffix.
           This should use the API map instead of this heuristic, since aliases
           like VkPhysicalDeviceVariablePointerFeaturesKHR ->
           VkPhysicalDeviceVariablePointersFeatures are not recognized."""
        upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        return oldname.rstrip(upper) == newname.rstrip(upper)

    def transformFile(self, lines):
        """Transform lines, and possibly output to the given file."""

        for line in lines:
            self.state.incrLineNumber()

            # Is this a title line (leading '= ' followed by text)?
            thisTitle = False

            # The logic here is broken. If we are in a non-transformable block and
            # this line *does not* end the block, it should always be
            # accumulated.

            # Test for a blockCommonTransform delimiter comment first, to avoid
            # treating it solely as an end-Paragraph marker comment.
            if line == blockCommonTransform:
                # Starting or ending a pseudo-block for "common" VU statements.
                self.endParaBlockTransform(line, vuBlock = True)

            elif blockTransform.match(line):
                # Starting or ending a block whose contents may be transformed.
                # Blocks cannot be nested.

                # Is this is an explicit Valid Usage block?
                vuBlock = (self.state.lineNumber > 1 and
                           lines[self.state.lineNumber-2] == '.Valid Usage\n')

                self.endParaBlockTransform(line, vuBlock)

            elif endPara.match(line):
                # Ending a paragraph. Emit the current paragraph, if any, and
                # prepare to begin a new paragraph.

                self.endPara(line)

                # If this is an include:: line starting the definition of a
                # structure or command, track that for use in VUID generation.

                matches = includePat.search(line)
                if matches is not None:
                    generated_type = matches.group('generated_type')
                    include_type = matches.group('category')
                    if generated_type == 'api' and include_type in ('protos', 'structs', 'funcpointers'):
                        apiName = matches.group('entity_name')
                        if self.state.apiName != self.state.defaultApiName:
                            # This happens when there are multiple API include
                            # lines in a single block. The style guideline is to
                            # always place the API which others are promoted to
                            # first. In virtually all cases, the promoted API
                            # will differ solely in the vendor suffix (or
                            # absence of it), which is benign.
                            if not self.apiMatch(self.state.apiName, apiName):
                                logDiag(f'Promoted API name mismatch at line {self.state.lineNumber}: {apiName} does not match self.state.apiName (this is OK if it is just a spelling alias)')
                        else:
                            self.state.apiName = apiName

            elif endParaContinue.match(line):
                # For now, always just end the paragraph.
                # Could check see if len(para) > 0 to accumulate.

                self.endParaContinue(line)

                # If it is a title line, track that
                if line[0:2] == '= ':
                    thisTitle = True

            elif blockPassthrough.match(line):
                # Starting or ending a block whose contents must not be
                # transformed.  These are tables, etc. Blocks cannot be nested.
                # Note that the use of a listing block masquerading as an
                # open block, via an extension, will not be formatted even
                # though it should be.
                # Fixing this would require looking at the previous line
                # state for the '[open]' tag, and there are so few cases of
                # this in the spec markup that it is not worth the trouble.

                self.endParaBlockPassthrough(line)
            elif self.state.lastTitle:
                # The previous line was a document title line. This line
                # is the author / credits line and must not be transformed.

                self.endPara(line)
            else:
                # Just accumulate a line to the current paragraph. Watch out for
                # hanging indents / bullet-points and track that indent level.

                self.addLine(line)

                # Commented out now that VU extractor supports this, but may
                # need to refactor through a conventions object enable if
                # OpenXR still needs this.

                # This test looks for disallowed conditionals inside Valid Usage
                # blocks, by checking if (a) this line does not start a new VU
                # (bullet point) and (b) the previous line starts an asciidoctor
                # conditional (ifdef:: or ifndef::).
                # if (self.state.vuStack[-1]
                #     and not beginBullet.match(line)
                #     and conditionalStart.match(lines[self.state.lineNumber-2])):
                #        self.callback.onEmbeddedVUConditional(self.state)

            self.state.lastTitle = thisTitle

        # Cleanup at end of file
        self.endPara(None)

        # Check for sensible block nesting
        if len(self.state.blockStack) > 1:
            logWarn('file', self.filename,
                    'mismatched asciidoc block delimiters at EOF:',
                    self.state.blockStack[-1])

