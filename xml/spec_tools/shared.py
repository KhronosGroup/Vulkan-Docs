"""Types, constants, and utility functions used by multiple sub-modules in spec_tools."""

# Copyright (c) 2018-2019 Collabora, Ltd.
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
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>

from collections import namedtuple
from enum import Enum
from inspect import currentframe, getframeinfo
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
CATEGORIES_WITH_VALIDITY = set(['protos', 'structs'])
NON_EXISTENT_MACROS = set(['plink', 'ttext', 'dtext'])

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
        if self == MessageId.MISSING_TEXT:
            return "a *text: macro is expected but not found"
        elif self == MessageId.LEGACY:
            return "legacy usage of *name: macro when *link: is applicable"
        elif self == MessageId.WRONG_MACRO:
            return "wrong macro used for an entity"
        elif self == MessageId.MISSING_MACRO:
            return "a macro might be missing"
        elif self == MessageId.BAD_ENTITY:
            return "entity not recognized, etc."
        elif self == MessageId.BAD_ENUMERANT:
            return "unrecognized enumerant value used in ename:"
        elif self == MessageId.BAD_MACRO:
            return "unrecognized macro used"
        elif self == MessageId.UNRECOGNIZED_CONTEXT:
            return "pname used with an unrecognized context"
        elif self == MessageId.UNKNOWN_MEMBER:
            return "pname used but member/argument by that name not found"
        elif self == MessageId.DUPLICATE_INCLUDE:
            return "duplicated include line"
        elif self == MessageId.UNKNOWN_INCLUDE:
            return "include line specified file we wouldn't expect to exists"
        elif self == MessageId.API_VALIDITY_ORDER:
            return "saw API include after validity include"
        elif self == MessageId.UNDOCUMENTED_MEMBER:
            return "saw an apparent struct/function documentation, but missing a member"
        elif self == MessageId.MEMBER_PNAME_MISSING:
            return "pname: missing from a 'scope' operator"
        elif self == MessageId.MISSING_VALIDITY_INCLUDE:
            return "missing validity include"
        elif self == MessageId.MISSING_API_INCLUDE:
            return "missing API include"
        elif self == MessageId.MISUSED_TEXT:
            return "a *text: macro is found but not expected"
        elif self == MessageId.EXTENSION:
            return "an extension name is incorrectly marked"
        elif self == MessageId.REFPAGE_TAG:
            return "a refpage tag is missing an expected field"
        elif self == MessageId.REFPAGE_MISSING_DESC:
            return "a refpage tag has an empty description"
        elif self == MessageId.REFPAGE_XREFS:
            return "an unrecognized entity is mentioned in xrefs of a refpage tag"
        elif self == MessageId.REFPAGE_XREFS_COMMA:
            return "a comma was founds in xrefs of a refpage tag, which is space-delimited"
        elif self == MessageId.REFPAGE_TYPE:
            return "a refpage tag has an incorrect type field"
        elif self == MessageId.REFPAGE_NAME:
            return "a refpage tag has an unrecognized entity name in its refpage field"
        elif self == MessageId.REFPAGE_BLOCK:
            return "a refpage block is not correctly opened or closed."
        elif self == MessageId.REFPAGE_MISSING:
            return "an API include was found outside of a refpage block."
        elif self == MessageId.REFPAGE_MISMATCH:
            return "an API or validity include was found in a non-matching refpage block."
        elif self == MessageId.REFPAGE_UNKNOWN_ATTRIB:
            return "a refpage tag has an unrecognized attribute"
        elif self == MessageId.REFPAGE_SELF_XREF:
            return "a refpage tag has itself in the list of cross-references"
        elif self == MessageId.REFPAGE_XREF_DUPE:
            return "a refpage cross-references list has at least one duplicate"
        elif self == MessageId.REFPAGE_WHITESPACE:
            return "a refpage cross-references list has non-minimal whitespace"
        elif self == MessageId.REFPAGE_DUPLICATE:
            return "a refpage tag has been seen for a single entity for a second time"
        elif self == MessageId.UNCLOSED_BLOCK:
            return "one or more blocks remain unclosed at the end of a file"


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
