"""Defines ConsolePrinter, a BasePrinter subclass for appealing console output."""

# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>

from sys import stdout

from .base_printer import BasePrinter
from .shared import (colored, getHighlightedRange, getInterestedRange,
                     toNameAndLine)

try:
    from tabulate import tabulate_impl
    HAVE_TABULATE = True
except ImportError:
    HAVE_TABULATE = False


def colWidth(collection, columnNum):
    """Compute the required width of a column in a collection of row-tuples."""
    MIN_PADDING = 5
    return MIN_PADDING + max((len(row[columnNum]) for row in collection))


def alternateTabulate(collection, headers=None):
    """Minimal re-implementation of the tabulate module."""
    # We need a list, not a generator or anything else.
    if not isinstance(collection, list):
        collection = list(collection)

    # Empty collection means no table
    if not collection:
        return None

    if headers is None:
        fullTable = collection
    else:
        underline = ['-' * len(header) for header in headers]
        fullTable = [headers, underline] + collection
    widths = [colWidth(collection, colNum)
              for colNum in range(len(fullTable[0]))]
    widths[-1] = None

    lines = []
    for row in fullTable:
        fields = []
        for data, width in zip(row, widths):
            if width:
                spaces = ' ' * (width - len(data))
                fields.append(data + spaces)
            else:
                fields.append(data)
        lines.append(''.join(fields))
    return '\n'.join(lines)


def printTabulated(collection, headers=None):
    """Call either tabulate.tabulate(), or our internal alternateTabulate()."""
    if HAVE_TABULATE:
        tabulated = tabulate_impl(collection, headers=headers)
    else:
        tabulated = alternateTabulate(collection, headers=headers)
    if tabulated:
        print(tabulated)


def printLineSubsetWithHighlighting(
        line, start, end, highlightStart=None, highlightEnd=None, maxLen=120, replacement=None):
    """Print a (potential subset of a) line, with highlighting/underline and optional replacement.

    Will print at least the characters line[start:end], and potentially more if possible
    to do so without making the output too wide.
    Will highlight (underline) line[highlightStart:highlightEnd], where the default
    value for highlightStart is simply start, and the default value for highlightEnd is simply end.
    Replacment, if supplied, will be aligned with the highlighted range.

    Output is intended to look like part of a Clang compile error/warning message.
    """
    # Fill in missing start/end with start/end of range.
    if highlightStart is None:
        highlightStart = start
    if highlightEnd is None:
        highlightEnd = end

    # Expand interested range start/end.
    start = min(start, highlightStart)
    end = max(end, highlightEnd)

    tildeLength = highlightEnd - highlightStart - 1
    caretLoc = highlightStart
    continuation = '[...]'

    if len(line) > maxLen:
        # Too long

        # the max is to handle -1 from .find() (which indicates "not found")
        followingSpaceIndex = max(end, line.find(' ', min(len(line), end + 1)))

        # Maximum length has decreased by at least
        # the length of a single continuation we absolutely need.
        maxLen -= len(continuation)

        if followingSpaceIndex <= maxLen:
            # We can grab the whole beginning of the line,
            # and not adjust caretLoc
            line = line[:maxLen] + continuation

        elif (len(line) - followingSpaceIndex) < 5:
            # We need to truncate the beginning,
            # but we're close to the end of line.
            newBeginning = len(line) - maxLen

            caretLoc += len(continuation)
            caretLoc -= newBeginning
            line = continuation + line[newBeginning:]
        else:
            # Need to truncate the beginning of the string too.
            newEnd = followingSpaceIndex

            # Now we need two continuations
            # (and to adjust caret to the right accordingly)
            maxLen -= len(continuation)
            caretLoc += len(continuation)

            newBeginning = newEnd - maxLen
            caretLoc -= newBeginning

            line = continuation + line[newBeginning:newEnd] + continuation

    stdout.buffer.write(line.encode('utf-8'))
    print()

    spaces = ' ' * caretLoc
    tildes = '~' * tildeLength
    print(spaces + colored('^' + tildes, 'green'))
    if replacement is not None:
        print(spaces + colored(replacement, 'green'))


class ConsolePrinter(BasePrinter):
    """Implementation of BasePrinter for generating diagnostic reports in colored, helpful console output."""

    def __init__(self):
        self.show_script_location = False
        super().__init__()

    ###
    # Output methods: these all print directly.
    def outputResults(self, checker, broken_links=True,
                      missing_includes=False):
        """Output the full results of a checker run.

        Includes the diagnostics, broken links (if desired),
        and missing includes (if desired).
        """
        self.output(checker)
        if broken_links:
            broken = checker.getBrokenLinks()
            if broken:
                self.outputBrokenLinks(checker, broken)
        if missing_includes:
            missing = checker.getMissingUnreferencedApiIncludes()
            if missing:
                self.outputMissingIncludes(checker, missing)

    def outputBrokenLinks(self, checker, broken):
        """Output a table of broken links.

        Called by self.outputBrokenAndMissing() if requested.
        """
        print('Missing API includes that are referenced by a linking macro: these result in broken links in the spec!')

        def makeRowOfBroken(entity, uses):
            fn = checker.findEntity(entity).filename
            anchor = '[[{}]]'.format(entity)
            locations = ', '.join((toNameAndLine(context, root_path=checker.root_path)
                                   for context in uses))
            return (fn, anchor, locations)
        printTabulated((makeRowOfBroken(entity, uses)
                        for entity, uses in sorted(broken.items())),
                       headers=['Include File', 'Anchor in lieu of include', 'Links to this entity'])

    def outputMissingIncludes(self, checker, missing):
        """Output a table of missing includes.

        Called by self.outputBrokenAndMissing() if requested.
        """
        missing = list(sorted(missing))
        if not missing:
            # Exit if none
            return
        print(
            'Missing, but unreferenced, API includes/anchors - potentially not-documented entities:')

        def makeRowOfMissing(entity):
            fn = checker.findEntity(entity).filename
            anchor = '[[{}]]'.format(entity)
            return (fn, anchor)
        printTabulated((makeRowOfMissing(entity) for entity in missing),
                       headers=['Include File', 'Anchor in lieu of include'])

    def outputMessage(self, msg):
        """Output a Message, with highlighted range and replacement, if appropriate."""
        highlightStart, highlightEnd = getHighlightedRange(msg.context)

        if '\n' in msg.context.filename:
            # This is a multi-line string "filename".
            # Extra blank line and delimiter line for readability:
            print()
            print('--------------------------------------------------------------------')

        fileAndLine = colored('{}:'.format(
            self.formatBrief(msg.context)), attrs=['bold'])

        headingSize = len('{context}: {mtype}: '.format(
            context=self.formatBrief(msg.context),
            mtype=self.formatBrief(msg.message_type, False)))
        indent = ' ' * headingSize
        printedHeading = False

        lines = msg.message[:]
        if msg.see_also:
            lines.append('See also:')
            lines.extend(('  {}'.format(self.formatBrief(see))
                          for see in msg.see_also))

        if msg.fix:
            lines.append('Note: Auto-fix available')

        for line in msg.message:
            if not printedHeading:
                scriptloc = ''
                if msg.script_location and self.show_script_location:
                    scriptloc = ', ' + msg.script_location
                print('{fileLine} {mtype} {msg} (-{arg}{loc})'.format(
                    fileLine=fileAndLine, mtype=msg.message_type.formattedWithColon(),
                    msg=colored(line, attrs=['bold']), arg=msg.message_id.enable_arg(), loc=scriptloc))
                printedHeading = True
            else:
                print(colored(indent + line, attrs=['bold']))

        if len(msg.message) > 1:
            # extra blank line after multiline message
            print('')

        start, end = getInterestedRange(msg.context)
        printLineSubsetWithHighlighting(
            msg.context.line,
            start, end,
            highlightStart, highlightEnd,
            replacement=msg.replacement)

    def outputFallback(self, obj):
        """Output by calling print."""
        print(obj)

    ###
    # Format methods: these all return a string.
    def formatFilename(self, fn, _with_color=True):
        """Format a local filename, as a relative path if possible."""
        return self.getRelativeFilename(fn)

    def formatMessageTypeBrief(self, message_type, with_color=True):
        """Format a message type briefly, applying color if desired and possible.

        Delegates to the superclass if not formatting with color.
        """
        if with_color:
            return message_type.formattedWithColon()
        return super(ConsolePrinter, self).formatMessageTypeBrief(
            message_type, with_color)
