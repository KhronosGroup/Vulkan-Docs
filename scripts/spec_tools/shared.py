"""Types, constants, and utility functions used by multiple sub-modules in spec_tools."""

# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>

import platform
from collections import namedtuple
from enum import Enum
from inspect import getframeinfo
from pathlib import Path
from sys import stdout

# if we have termcolor and we know our stdout is a TTY,
# pull it in and use it.
if hasattr(stdout, 'isatty') and stdout.isatty():
    try:
        from termcolor import colored as colored_impl
        HAVE_COLOR = True
    except ImportError:
        HAVE_COLOR = False
elif platform.system() == 'Windows':
    try:
        from termcolor import colored as colored_impl
        import colorama
        colorama.init()
        HAVE_COLOR = True
    except ImportError:
        HAVE_COLOR = False

else:
    HAVE_COLOR = False


def colored(s, color=None, attrs=None):
    """Call termcolor.colored with same arguments if this is a tty and it is available."""
    if HAVE_COLOR:
        return colored_impl(s, color, attrs=attrs)
    return s


###
# Constants used in multiple places.
AUTO_FIX_STRING = 'Note: Auto-fix available.'
EXTENSION_CATEGORY = 'extension'
CATEGORIES_WITH_VALIDITY = set(('protos', 'structs'))
NON_EXISTENT_MACROS = set(('plink', 'ttext', 'dtext'))

###
# MessageContext: All the information about where a message relates to.
MessageContext = namedtuple('MessageContext',
                            ['filename', 'lineNum', 'line',
                             'match', 'group'])


def getInterestedRange(message_context):
    """Return a (start, end) pair of character index for the match in a MessageContext."""
    if not message_context.match:
        # whole line
        return (0, len(message_context.line))
    return (message_context.match.start(), message_context.match.end())


def getHighlightedRange(message_context):
    """Return a (start, end) pair of character index for the highlighted range in a MessageContext."""
    if message_context.group is not None and message_context.match is not None:
        return (message_context.match.start(message_context.group),
                message_context.match.end(message_context.group))
    # no group (whole match) or no match (whole line)
    return getInterestedRange(message_context)


def toNameAndLine(context, root_path=None):
    """Convert MessageContext into a simple filename:line string."""
    my_fn = Path(context.filename)
    if root_path:
        my_fn = my_fn.relative_to(root_path)
    return '{}:{}'.format(str(my_fn), context.lineNum)


def generateInclude(dir_traverse, generated_type, category, entity):
    """Create an include:: directive for geneated api or validity from the various pieces."""
    return 'include::{directory_traverse}{generated_type}/{category}/{entity_name}.txt[]'.format(
        directory_traverse=dir_traverse,
        generated_type=generated_type,
        category=category,
        entity_name=entity)


# Data stored per entity (function, struct, enumerant type, enumerant, extension, etc.)
EntityData = namedtuple(
    'EntityData', ['entity', 'macro', 'elem', 'filename', 'category', 'directory'])


class MessageType(Enum):
    """Type of a message."""

    WARNING = 1
    ERROR = 2
    NOTE = 3

    def __str__(self):
        """Format a MessageType as a lowercase string."""
        return str(self.name).lower()

    def formattedWithColon(self):
        """Format a MessageType as a colored, lowercase string followed by a colon."""
        if self == MessageType.WARNING:
            return colored(str(self) + ':', 'magenta', attrs=['bold'])
        if self == MessageType.ERROR:
            return colored(str(self) + ':', 'red', attrs=['bold'])
        return str(self) + ':'


class MessageId(Enum):
    """Enumerates the varieties of messages that can be generated.

    Control over enabled messages with -Wbla or -Wno_bla is per-MessageId.
    """

    MISSING_TEXT = 1
    LEGACY = 2
    WRONG_MACRO = 3
    MISSING_MACRO = 4
    BAD_ENTITY = 5
    BAD_ENUMERANT = 6
    BAD_MACRO = 7
    UNRECOGNIZED_CONTEXT = 8
    UNKNOWN_MEMBER = 9
    DUPLICATE_INCLUDE = 10
    UNKNOWN_INCLUDE = 11
    API_VALIDITY_ORDER = 12
    UNDOCUMENTED_MEMBER = 13
    MEMBER_PNAME_MISSING = 14
    MISSING_VALIDITY_INCLUDE = 15
    MISSING_API_INCLUDE = 16
    MISUSED_TEXT = 17
    EXTENSION = 18
    REFPAGE_TAG = 19
    REFPAGE_MISSING_DESC = 20
    REFPAGE_XREFS = 21
    REFPAGE_XREFS_COMMA = 22
    REFPAGE_TYPE = 23
    REFPAGE_NAME = 24
    REFPAGE_BLOCK = 25
    REFPAGE_MISSING = 26
    REFPAGE_MISMATCH = 27
    REFPAGE_UNKNOWN_ATTRIB = 28
    REFPAGE_SELF_XREF = 29
    REFPAGE_XREF_DUPE = 30
    REFPAGE_WHITESPACE = 31
    REFPAGE_DUPLICATE = 32
    UNCLOSED_BLOCK = 33

    def __str__(self):
        """Format as a lowercase string."""
        return self.name.lower()

    def enable_arg(self):
        """Return the corresponding Wbla string to make the 'enable this message' argument."""
        return 'W{}'.format(self.name.lower())

    def disable_arg(self):
        """Return the corresponding Wno_bla string to make the 'enable this message' argument."""
        return 'Wno_{}'.format(self.name.lower())

    def desc(self):
        """Return a brief description of the MessageId suitable for use in --help."""
        return MessageId.DESCRIPTIONS[self]


MessageId.DESCRIPTIONS = {
    MessageId.MISSING_TEXT: "a *text: macro is expected but not found",
    MessageId.LEGACY: "legacy usage of *name: macro when *link: is applicable",
    MessageId.WRONG_MACRO: "wrong macro used for an entity",
    MessageId.MISSING_MACRO: "a macro might be missing",
    MessageId.BAD_ENTITY: "entity not recognized, etc.",
    MessageId.BAD_ENUMERANT: "unrecognized enumerant value used in ename:",
    MessageId.BAD_MACRO: "unrecognized macro used",
    MessageId.UNRECOGNIZED_CONTEXT: "pname used with an unrecognized context",
    MessageId.UNKNOWN_MEMBER: "pname used but member/argument by that name not found",
    MessageId.DUPLICATE_INCLUDE: "duplicated include line",
    MessageId.UNKNOWN_INCLUDE: "include line specified file we wouldn't expect to exists",
    MessageId.API_VALIDITY_ORDER: "saw API include after validity include",
    MessageId.UNDOCUMENTED_MEMBER: "saw an apparent struct/function documentation, but missing a member",
    MessageId.MEMBER_PNAME_MISSING: "pname: missing from a 'scope' operator",
    MessageId.MISSING_VALIDITY_INCLUDE: "missing validity include",
    MessageId.MISSING_API_INCLUDE: "missing API include",
    MessageId.MISUSED_TEXT: "a *text: macro is found but not expected",
    MessageId.EXTENSION: "an extension name is incorrectly marked",
    MessageId.REFPAGE_TAG: "a refpage tag is missing an expected field",
    MessageId.REFPAGE_MISSING_DESC: "a refpage tag has an empty description",
    MessageId.REFPAGE_XREFS: "an unrecognized entity is mentioned in xrefs of a refpage tag",
    MessageId.REFPAGE_XREFS_COMMA: "a comma was founds in xrefs of a refpage tag, which is space-delimited",
    MessageId.REFPAGE_TYPE: "a refpage tag has an incorrect type field",
    MessageId.REFPAGE_NAME: "a refpage tag has an unrecognized entity name in its refpage field",
    MessageId.REFPAGE_BLOCK: "a refpage block is not correctly opened or closed.",
    MessageId.REFPAGE_MISSING: "an API include was found outside of a refpage block.",
    MessageId.REFPAGE_MISMATCH: "an API or validity include was found in a non-matching refpage block.",
    MessageId.REFPAGE_UNKNOWN_ATTRIB: "a refpage tag has an unrecognized attribute",
    MessageId.REFPAGE_SELF_XREF: "a refpage tag has itself in the list of cross-references",
    MessageId.REFPAGE_XREF_DUPE: "a refpage cross-references list has at least one duplicate",
    MessageId.REFPAGE_WHITESPACE: "a refpage cross-references list has non-minimal whitespace",
    MessageId.REFPAGE_DUPLICATE: "a refpage tag has been seen for a single entity for a second time",
    MessageId.UNCLOSED_BLOCK: "one or more blocks remain unclosed at the end of a file"
}


class Message(object):
    """An Error, Warning, or Note with a MessageContext, MessageId, and message text.

    May optionally have a replacement, a see_also array, an auto-fix,
    and a stack frame where the message was created.
    """

    def __init__(self, message_id, message_type, message, context,
                 replacement=None, see_also=None, fix=None, frame=None):
        """Construct a Message.

        Typically called by MacroCheckerFile.diag().
        """
        self.message_id = message_id

        self.message_type = message_type

        if isinstance(message, str):
            self.message = [message]
        else:
            self.message = message

        self.context = context
        if context is not None and context.match is not None and context.group is not None:
            if context.group not in context.match.groupdict():
                raise RuntimeError(
                    'Group "{}" does not exist in the match'.format(context.group))

        self.replacement = replacement

        self.fix = fix

        if see_also is None:
            self.see_also = None
        elif isinstance(see_also, MessageContext):
            self.see_also = [see_also]
        else:
            self.see_also = see_also

        self.script_location = None
        if frame:
            try:
                frameinfo = getframeinfo(frame)
                self.script_location = "{}:{}".format(
                    frameinfo.filename, frameinfo.lineno)
            finally:
                del frame
