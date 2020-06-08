"""Provides the BasePrinter base class for MacroChecker/Message output techniques."""

# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>

from abc import ABC, abstractmethod
from pathlib import Path

from .macro_checker import MacroChecker
from .macro_checker_file import MacroCheckerFile
from .shared import EntityData, Message, MessageContext, MessageType


def getColumn(message_context):
    """Return the (zero-based) column number of the message context.

    If a group is specified: returns the column of the start of the group.
    If no group, but a match is specified: returns the column of the start of
    the match.
    If no match: returns column 0 (whole line).
    """
    if not message_context.match:
        # whole line
        return 0
    if message_context.group is not None:
        return message_context.match.start(message_context.group)
    return message_context.match.start()


class BasePrinter(ABC):
    """Base class for a way of outputting results of a checker execution."""

    def __init__(self):
        """Constructor."""
        self._cwd = None

    def close(self):
        """Write the tail end of the output and close it, if applicable.

        Override if you want to print a summary or are writing to a file.
        """
        pass

    ###
    # Output methods: these should all print/output directly.
    def output(self, obj):
        """Output any object.

        Delegates to other output* methods, if type known,
        otherwise uses self.outputFallback().
        """
        if isinstance(obj, Message):
            self.outputMessage(obj)
        elif isinstance(obj, MacroCheckerFile):
            self.outputCheckerFile(obj)
        elif isinstance(obj, MacroChecker):
            self.outputChecker(obj)
        else:
            self.outputFallback(self.formatBrief(obj))

    @abstractmethod
    def outputResults(self, checker, broken_links=True,
                      missing_includes=False):
        """Output the full results of a checker run.

        Must be implemented.

        Typically will call self.output() on the MacroChecker,
        as well as calling self.outputBrokenAndMissing()
        """
        raise NotImplementedError

    @abstractmethod
    def outputBrokenLinks(self, checker, broken):
        """Output the collection of broken links.

        `broken` is a dictionary of entity names: usage contexts.

        Must be implemented.

        Called by self.outputBrokenAndMissing() if requested.
        """
        raise NotImplementedError

    @abstractmethod
    def outputMissingIncludes(self, checker, missing):
        """Output a table of missing includes.

        `missing` is a iterable entity names.

        Must be implemented.

        Called by self.outputBrokenAndMissing() if requested.
        """
        raise NotImplementedError

    def outputChecker(self, checker):
        """Output the contents of a MacroChecker object.

        Default implementation calls self.output() on every MacroCheckerFile.
        """
        for f in checker.files:
            self.output(f)

    def outputCheckerFile(self, fileChecker):
        """Output the contents of a MacroCheckerFile object.

        Default implementation calls self.output() on every Message.
        """
        for m in fileChecker.messages:
            self.output(m)

    def outputBrokenAndMissing(self, checker, broken_links=True,
                               missing_includes=False):
        """Outputs broken links and missing includes, if desired.

        Delegates to self.outputBrokenLinks() (if broken_links==True)
        and self.outputMissingIncludes() (if missing_includes==True).
        """
        if broken_links:
            broken = checker.getBrokenLinks()
            if broken:
                self.outputBrokenLinks(checker, broken)
        if missing_includes:
            missing = checker.getMissingUnreferencedApiIncludes()
            if missing:
                self.outputMissingIncludes(checker, missing)

    @abstractmethod
    def outputMessage(self, msg):
        """Output a Message.

        Must be implemented.
        """
        raise NotImplementedError

    @abstractmethod
    def outputFallback(self, msg):
        """Output some text in a general way.

        Must be implemented.
        """
        raise NotImplementedError

    ###
    # Format methods: these should all return a string.
    def formatContext(self, context, _message_type=None):
        """Format a message context in a verbose way, if applicable.

        May override, default implementation delegates to
        self.formatContextBrief().
        """
        return self.formatContextBrief(context)

    def formatContextBrief(self, context, _with_color=True):
        """Format a message context in a brief way.

        May override, default is relativeFilename:line:column
        """
        return '{}:{}:{}'.format(self.getRelativeFilename(context.filename),
                                 context.lineNum, getColumn(context))

    def formatMessageTypeBrief(self, message_type, _with_color=True):
        """Format a message type in a brief way.

        May override, default is message_type:
        """
        return '{}:'.format(message_type)

    def formatEntityBrief(self, entity_data, _with_color=True):
        """Format an entity in a brief way.

        May override, default is macro:entity.
        """
        return '{}:{}'.format(entity_data.macro, entity_data.entity)

    def formatBrief(self, obj, with_color=True):
        """Format any object in a brief way.

        Delegates to other format*Brief methods, if known,
        otherwise uses str().
        """
        if isinstance(obj, MessageContext):
            return self.formatContextBrief(obj, with_color)
        if isinstance(obj, MessageType):
            return self.formatMessageTypeBrief(obj, with_color)
        if isinstance(obj, EntityData):
            return self.formatEntityBrief(obj, with_color)
        return str(obj)

    @property
    def cwd(self):
        """Get the current working directory, fully resolved.

        Lazy initialized.
        """
        if not self._cwd:
            self._cwd = Path('.').resolve()
        return self._cwd

    ###
    # Helper function
    def getRelativeFilename(self, fn):
        """Return the given filename relative to the current directory,
        if possible.
        """
        try:
            return str(Path(fn).relative_to(self.cwd))
        except ValueError:
            return str(Path(fn))
