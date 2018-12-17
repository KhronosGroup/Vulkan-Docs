#!/usr/bin/python3
#
# Copyright (c) 2018 Collabora, Ltd.
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
#
# Purpose:      This file performs some basic checks of the custom macros
#               used in the AsciiDoctor source for the spec, especially
#               related to the validity of the entities linked-to.

import argparse
import html
import json
import re
from abc import ABC, abstractmethod
from collections import namedtuple
from enum import Enum
from io import StringIO
from pathlib import Path
from sys import exit, stdout
from xml.etree import ElementTree
from inspect import currentframe, getframeinfo

from reg import Registry

###
# "Configuration" constants
NAME_PREFIX = 'vk'

MISSING_VALIDITY_SUPPRESSIONS = set()
ENTITIES_WITHOUT_VALIDITY = set(
    ['VkBaseOutStructure', 'VkBaseInStructure', 'VkHdrMetadataEXT'])

# These are marked with the code: macro
SYSTEM_TYPES = set(['void', 'char', 'float', 'size_t', 'uintptr_t',
                    'int8_t', 'uint8_t',
                    'int32_t',  'uint32_t',
                    'int64_t', 'uint64_t', 'ANativeWindow', 'AHardwareBuffer'])


PLATFORM_REQUIRES = 'vk_platform'

EXTRA_DEFINES = []  # TODO - defines mentioned in spec but not needed in registry
ROOT = Path(__file__).resolve().parent.parent
REGISTRY_FILE = ROOT / 'xml/vk.xml'
ALL_DOCS = [str(fn)
            for fn in sorted((ROOT / 'chapters/').glob('**/*.txt'))]
ALL_DOCS.extend([str(fn)
                 for fn in sorted((ROOT / 'appendices/').glob('**/*.txt'))])

INCLUDE = re.compile(
    r'include::(?P<directory_traverse>((../){1,4}|\{INCS-VAR\}/))(?P<generated_type>[\w]+)/(?P<category>\w+)/(?P<entity_name>[^./]+).txt[[][]]')
ANCHOR = re.compile(r'\[\[(?P<entity_name>[^\]]+)\]\]')

MEMBER_REFERENCE = re.compile(
    r'\b(?P<first_part>(?P<scope_macro>[fs](text|link)):(?P<scope>[\w*]+))(?P<double_colons>::)(?P<second_part>(?P<member_macro>pname:?)(?P<entity_name>[\w]+))\b'
)

PRECEDING_MEMBER_REFERENCE = re.compile(
    r'\b(?P<macro>[fs](text|link)):(?P<entity_name>[\w*]+)::$')

HEADING_COMMAND = re.compile(
    r'=+ (?P<command>{}[\w]+)'.format(NAME_PREFIX)
)

SUSPECTED_MISSING_MACRO = re.compile(
    r'\b(?<![-=:/[\.`+,])(?P<entity_name>[vV][kK][\w*]+)\b(?!>>)'
)

OPEN_LINK = re.compile(
    r'.*(?<!`)<<[^>]*$'
)

CLOSE_LINK = re.compile(
    r'[^<]*>>.*$'
)

SKIP_LINE = re.compile(
    r'^(ifdef:)|(endif:).*'
)

INTERNAL_PLACEHOLDER = re.compile(
    r'(?P<delim>__+)([a-zA-Z]+)(?P=delim)'
)

CATEGORIES_WITH_VALIDITY = set(['protos', 'structs'])


LEADING_SPACES = re.compile(r'^(?P<spaces>\s*)(?P<content>.*)')

CWD = Path('.').resolve()

if hasattr(stdout, 'isatty') and stdout.isatty():
    try:
        from termcolor import colored as colored_impl
        HAVE_COLOR = True
    except ImportError:
        HAVE_COLOR = False
else:
    HAVE_COLOR = False

try:
    from tabulate import tabulate_impl
    HAVE_TABULATE = True
except ImportError:
    HAVE_TABULATE = False

AUTO_FIX_STRING = 'Note: Auto-fix available.'
EXTENSION_CATEGORY = 'extension'


def colored(s, color=None, attrs=None):
    if HAVE_COLOR:
        return colored_impl(s, color, attrs=attrs)
    return s


def colWidth(collection, columnNum):
    MIN_PADDING = 5
    return MIN_PADDING + max([len(row[columnNum]) for row in collection])


def alternateTabulate(collection, headers=None):
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
                spaces = ' ' * (width-len(data))
                fields.append(data + spaces)
            else:
                fields.append(data)
        lines.append(''.join(fields))
    return '\n'.join(lines)


def printTabulated(collection, headers=None):
    if HAVE_TABULATE:
        print(tabulate_impl(collection, headers=headers))
    else:
        print(alternateTabulate(collection, headers=headers))


def generateInclude(dir_traverse, generated_type, category, entity):
    return 'include::{directory_traverse}{generated_type}/{category}/{entity_name}.txt[]'.format(
        directory_traverse=dir_traverse,
        generated_type=generated_type,
        category=category,
        entity_name=entity)


def regenerateIncludeFromMatch(match, generated_type):
    return generateInclude(match.group('directory_traverse'), generated_type, match.group('category'),
                           match.group('entity_name'))


def shouldEntityBeText(entity, subscript):
    entity_only = entity
    if subscript:
        if subscript == '[]' or subscript == '[i]' or subscript.startswith('[_') or subscript.endswith('_]'):
            return True
        entity_only = entity[:-len(subscript)]

    if ('*' in entity) or entity.startswith('_') or entity_only.endswith('_'):
        return True

    if INTERNAL_PLACEHOLDER.search(entity):
        return True
    return False


EntityData = namedtuple(
    'EntityData', ['entity', 'macro', 'elem', 'filename', 'category'])


def entityToDict(data):
    return {
        'macro': data.macro,
        'filename': data.filename,
        'category': data.category
    }


class MessageType(Enum):
    WARNING = 1
    ERROR = 2
    NOTE = 3

    def __str__(self):
        return str(self.name).lower()

    def formattedWithColon(self):
        if self == MessageType.WARNING:
            return colored(str(self) + ':', 'magenta', attrs=['bold'])
        if self == MessageType.ERROR:
            return colored(str(self) + ':', 'red', attrs=['bold'])
        return str(self) + ':'


MessageContext = namedtuple('MessageContext',
                            ['filename', 'lineNum', 'line',
                             'match', 'group'])


class MessageId(Enum):
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

    def __str__(self):
        return self.name.lower()

    def enable_arg(self):
        return 'W{}'.format(self.name.lower())

    def disable_arg(self):
        return 'Wno_{}'.format(self.name.lower())

    def desc(self):

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

    @classmethod
    def default_set(self):
        return set([self.WRONG_MACRO,
                    self.BAD_ENTITY,
                    self.BAD_ENUMERANT,
                    self.BAD_MACRO,
                    self.UNKNOWN_MEMBER,
                    self.DUPLICATE_INCLUDE,
                    self.UNKNOWN_INCLUDE,
                    self.API_VALIDITY_ORDER,
                    self.UNDOCUMENTED_MEMBER,
                    self.MEMBER_PNAME_MISSING,
                    self.MISSING_VALIDITY_INCLUDE,
                    self.MISSING_API_INCLUDE
                    ])


def getInterestedRange(message_context):
    return (message_context.match.start(), message_context.match.end())


def getHighlightedRange(message_context):
    if message_context.group is not None:
        return (message_context.match.start(message_context.group),
                message_context.match.end(message_context.group))
    return getInterestedRange(message_context)


def getColumn(message_context):
    if message_context.group is not None:
        return message_context.match.start(message_context.group)
    return message_context.match.start()


def toNameAndLine(context):
    """Convert MessageContext into a simple filename:line string"""
    return '{}:{}'.format(str(Path(context.filename).relative_to(ROOT)), context.lineNum)


def likelyRecognizedEntity(entity_name):
    return entity_name.lower().startswith(NAME_PREFIX)


class Message(object):
    def __init__(self, message_id, message_type, message, context, replacement=None, see_also=None, fix=None, frame=None):
        self.message_id = message_id
        self.message_type = message_type
        if isinstance(message, str):
            self.message = [message]
        else:
            self.message = message
        self.context = context
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


def s_suffix(num):
    """Simplify pluralization."""
    if num > 1:
        return 's'
    return ''


def pluralize(word, num):
    if num == 1:
        return word
    if word.endswith('y'):
        return word[:-1]+'ies'
    return word + 's'


def printLineSubsetWithHighlighting(line, start, end, highlightStart=None, highlightEnd=None, maxLen=120, replacement=None):
    if highlightStart is None:
        highlightStart = start
    if highlightEnd is None:
        highlightEnd = end

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
            # We can grab the whole beginning of the line and not adjust caretLoc
            line = line[:maxLen] + continuation

        elif (len(line) - followingSpaceIndex) < 5:
            # We need to truncate the beginning, but we're close to the end of line.
            newBeginning = len(line) - maxLen

            caretLoc += len(continuation)
            caretLoc -= newBeginning
            line = continuation + line[newBeginning:]
        else:
            # Need to truncate the beginning of the string too.
            newEnd = followingSpaceIndex

            # Now we need two continuations (and to adjust caret to the right accordingly)
            maxLen -= len(continuation)
            caretLoc += len(continuation)

            newBeginning = newEnd - maxLen
            caretLoc -= newBeginning

            line = continuation + line[newBeginning:newEnd] + continuation
    print(line)

    spaces = ' ' * caretLoc
    tildes = '~' * tildeLength
    print(spaces + colored('^' + tildes, 'green'))
    if replacement is not None:
        print(spaces + colored(replacement, 'green'))


class MacroCheckerFile(object):
    def __init__(self, checker, filename, enabled_messages, stream_maker):
        self.checker = checker
        self.filename = filename
        self.stream_maker = stream_maker
        self.enabled_messages = enabled_messages
        self.fixes = set()
        self.messages = []

        self.pname_data = None
        self.pname_mentions = {}

        self.lines = []

        # For both of these:
        # keys: entity name
        # values: MessageContext
        self.fs_api_includes = {}
        self.validity_includes = {}

        self.in_code_block = False

    def numDiagnostics(self):
        return len(self.messages)

    def numErrors(self):
        return self.numMessagesOfType(MessageType.ERROR)

    def numMessagesOfType(self, message_type):
        return len([msg for msg in self.messages if msg.message_type == message_type])

    def hasFixes(self):
        return len(self.fixes) > 0

    def printMessageCounts(self):
        for message_type in [MessageType.ERROR, MessageType.WARNING]:
            count = len(
                [msg for msg in self.messages if msg.message_type == message_type])
            if count > 0:
                print('{num} {mtype}{s} generated.'.format(
                    num=count, mtype=message_type, s=s_suffix(count)))

    def diag(self, severity, message_id,  messageLines, group=None, replacement=None, context=None, fix=None, see_also=None, frame=None):
        if message_id not in self.enabled_messages:
            return

        if not frame:
            frame = currentframe().f_back
        if context is None:
            message = Message(message_id=message_id,
                              message_type=severity,
                              message=messageLines,
                              context=self.storeMessageContext(group=group),
                              replacement=replacement,
                              see_also=see_also,
                              fix=fix,
                              frame=frame)
        else:
            message = Message(message_id=message_id,
                              message_type=severity,
                              message=messageLines,
                              context=context,
                              replacement=replacement,
                              see_also=see_also,
                              fix=fix,
                              frame=frame)
        if fix is not None:
            self.fixes.add(fix)
        self.messages.append(message)

    def warning(self, message_id,  messageLines, group=None, replacement=None, context=None, fix=None, see_also=None, frame=None):
        if not frame:
            frame = currentframe().f_back
        self.diag(MessageType.WARNING, message_id, messageLines, group,
                  replacement, context, fix, see_also)

    def error(self, message_id, messageLines, group=None, replacement=None, context=None, fix=None, see_also=None, frame=None):
        if not frame:
            frame = currentframe().f_back
        self.diag(MessageType.ERROR, message_id, messageLines, group,
                  replacement, context, fix, see_also)

    def storeMessageContext(self, group=None):
        """Create message context from corresponding instance variables."""
        return MessageContext(filename=self.filename,
                              lineNum=self.lineNum,
                              line=self.line,
                              match=self.match,
                              group=group)

    def makeFix(self, newMacro=None, newEntity=None, data=None):
        return (self.makeSearch(), self.makeMacroMarkup(newMacro, newEntity, data))

    def makeSearch(self):
        return '{}:{}'.format(self.macro, self.entity)

    def makeMacroMarkup(self, newMacro=None, newEntity=None, data=None):
        if not newEntity:
            if data:
                newEntity = data.entity
            else:
                newEntity = self.entity
        if not newMacro:
            if data:
                newMacro = data.macro
            else:
                newMacro = self.macro
        if not data:
            data = self.checker.findEntity(newEntity)
        if data and data.category == EXTENSION_CATEGORY:
            return self.makeExtensionLink(newEntity)
        return '{}:{}'.format(newMacro, newEntity)

    def makeExtensionLink(self, newEntity=None):
        if not newEntity:
            newEntity = self.entity
        return '`<<{}>>`'.format(newEntity)

    def hasMember(self, elem, memberName):
        pass

    def checkRecognizedEntity(self):
        """Returns true if there is no need to perform further checks on this match.

        Helps avoid duplicate warnings/errors."""
        entity = self.entity
        macro = self.macro
        if self.checker.findMacroAndEntity(macro, entity) is not None:
            # We know this macro-entity combo
            return True

        # We don't know this macro-entity combo.
        possibleCats = self.checker.categoriesByMacro.get(macro)
        if possibleCats is None:
            possibleCats = ['???']
        msg = ['Definition of link target {} with macro {} (used for {} {}) does not exist.'.format(
            entity,
            macro,
            pluralize('category', len(possibleCats)),
            ', '.join(possibleCats))]

        data = self.checker.findEntity(entity)
        if data:
            # We found the goof: incorrect macro
            message_type = MessageType.WARNING
            message_id = MessageId.WRONG_MACRO
            group = 'macro'

            if data.category == EXTENSION_CATEGORY:
                # Ah, this is an extension
                msg.append(
                    'This is apparently an extension name, which should be marked up as a link.')
                message_id = MessageId.EXTENSION
                group = None  # replace the whole thing
            else:

                # Non-extension, we found the macro though.
                msg.append('Apparently matching entity in category {} found.'.format(
                    data.category))
                if data.macro[0] == macro[0] and data.macro[1:] == 'link' and macro[1:] == 'name':
                    # This is legacy markup
                    msg.append(
                        'This is legacy markup that has not been updated yet.')
                    message_id = MessageId.LEGACY
                else:
                    message_type = MessageType.ERROR

            msg.append(AUTO_FIX_STRING)
            self.diag(message_type, message_id, msg,
                      group=group, replacement=self.makeMacroMarkup(data=data), fix=self.makeFix(data=data))
            return True

        see_also = []
        dataArray = self.checker.findEntityCaseInsensitive(entity)
        if dataArray:
            # We might have found the goof...

            if len(dataArray) == 1:
                # Yep, found the goof - incorrect macro and entity capitalization
                data = dataArray[0]
                self.error(MessageId.WRONG_MACRO, msg + ['Apparently matching entity in category {} found by searching case-insensitively.'.format(data.category)],
                           replacement=self.makeMacroMarkup(data=data),
                           fix=self.makeFix(data=data))
                return True
            else:
                # Ugh, more than one resolution
                msg.append(
                    'More than one apparent match found by searching case-insensitively, cannot auto-fix.')
                see_also = dataArray[:]

        # OK, so we don't recognize this entity (and couldn't auto-fix it).

        if macro in self.checker.linkedMacros:
            # This should be linked, which means we should know the target.
            if not likelyRecognizedEntity(entity):
                newMacro = macro[0] + 'name'
                if newMacro in self.checker.categoriesByMacro:
                    self.error(MessageId.BAD_ENTITY, msg +
                               ['Entity name fits the pattern for this API, which would mean it should be a "name" macro instead of "link"'],
                               group='macro', replacement=newMacro, fix=self.makeFix(newMacro=newMacro), see_also=see_also)
                else:
                    self.error(MessageId.BAD_ENTITY, msg +
                               ['Entity name does not fit the pattern for this API, which would mean it should be a "name" macro',
                                'However, {} is not a known macro so cannot auto-fix.'.format(newMacro)], see_also=see_also)
            else:
                # no idea why it's missing, it just is. Human brains required.
                if not self.checkText():
                    self.error(MessageId.BAD_ENTITY, msg + ['Might be a misspelling or the wrong macro.'],
                               see_also=see_also)

        elif macro == 'ename':
            # TODO This might be an ambiguity in the style guide - ename might be a known enumerant value,
            # or it might be an enumerant value in an external library, etc. that we don't know about - so
            # hard to check this.
            if likelyRecognizedEntity(entity):
                if not self.checkText():
                    self.warning(MessageId.BAD_ENUMERANT, msg +
                                 ['Unrecognized ename:{} that we would expect to recognize since it fits the pattern for this API.'.format(entity)],  see_also=see_also)
        else:
            # This is fine - it doesn't need to be recognized since it's not linked.
            pass
        # Don't skip other tests.
        return False

    def checkText(self):
        ###
        # Wildcards (or leading or trailing underscore, or square brackets with nothing or a placeholder) if and only if a 'text' macro
        macro = self.macro
        entity = self.entity
        shouldBeText = shouldEntityBeText(entity, self.subscript)
        if shouldBeText and not self.macro.endswith('text') and not self.macro == 'code':
            newMacro = macro[0] + 'text'
            if newMacro in self.checker.categoriesByMacro:
                self.error(MessageId.MISSING_TEXT,
                           ['Asterisk/leading or trailing underscore/bracket found - macro should end with "text:", probably {}:'.format(newMacro),
                            AUTO_FIX_STRING],
                           group='macro', replacement=newMacro, fix=self.makeFix(newMacro=newMacro))
            else:
                self.error(MessageId.MISSING_TEXT,
                           ['Asterisk/leading or trailing underscore/bracket found, so macro should end with "text:".',
                            'However {}: is not a known macro so cannot auto-fix.'.format(newMacro)],
                           group='macro')
            return True
        elif macro.endswith('text') and not shouldBeText:
            msg = [
                "No asterisk/leading or trailing underscore/bracket in the entity, so this might be a mistaken use of the 'text' macro {}:".format(macro)]
            data = self.checker.findEntity(entity)
            if data:
                # We found the goof: incorrect macro
                msg.append('Apparently matching entity in category {} found.'.format(
                    data.category))
                msg.append(AUTO_FIX_STRING)
                replacement = self.makeFix(data=data)
                if data.category == EXTENSION_CATEGORY:
                    self.error(MessageId.EXTENSION, msg,
                               replacement=replacement, fix=replacement)
                else:
                    self.error(MessageId.WRONG_MACRO, msg,
                               group='macro', replacement=data.macro, fix=replacement)
            else:
                msg.append('Entity not found in spec, either.')
                if macro[0] != 'e':
                    # Only suggest a macro if we aren't in elink/ename/etext, since ename and elink are not related
                    # in an equivalent way to the relationship between flink and fname.
                    newMacro = macro[0] + 'name'
                    if newMacro in self.checker.categoriesByMacro:
                        msg.append(
                            'Consider if {}: might be the correct macro to use here.'.format(newMacro))
                    else:
                        msg.append(
                            'Cannot suggest a new macro because {}: is not a known macro.'.format(newMacro))
                self.warning(MessageId.MISUSED_TEXT, msg)
            return True
        return False

    def checkPname(self, pname_context):
        if '*' in pname_context:
            # This context has a placeholder, can't verify it.
            return

        entity = self.entity

        context_data = self.checker.findEntity(pname_context)
        members = self.checker.getMemberNames(pname_context)

        if context_data and not members:
            # This is a recognized parent entity that doesn't have detectable member names,
            # skip validation
            # TODO: Annotate parameters of function pointer types with <name> and <param>?
            return
        if not members:
            self.warning(MessageId.UNRECOGNIZED_CONTEXT,
                         'pname context entity was un-recognized {}'.format(pname_context))
            return

        if entity not in members:
            self.warning(MessageId.UNKNOWN_MEMBER, ["Could not find member/param named '{}' in {}".format(entity, pname_context),
                                                    'Known {} mamber/param names are: {}'.format(
                pname_context, ', '.join(members))], group='entity_name')

    def processMatch(self):
        match = self.match
        entity = self.entity
        macro = self.macro

        ###
        # Track entities that we're actually linking to.
        ###
        if macro in self.checker.linkedMacros:
            self.checker.addLinkToEntity(entity, self.storeMessageContext())

        ###
        # Link everything that should be, and nothing that shouldn't be
        ###
        if self.checkRecognizedEntity():
            # if this returns true, then there is no need to do the remaining checks on this match
            return

        ###
        # Non-existent macros
        if macro in self.checker.NON_EXISTENT_MACROS:
            self.error(MessageId.BAD_MACRO, '{} is not a macro provided in the specification, despite resembling other macros.'.format(
                macro), group='macro')

        ###
        # Wildcards (or leading underscore, or square brackets) if and only if a 'text' macro
        self.checkText()

        # Do some validation of pname references.
        if macro == 'pname':
            # See if there's an immediately-preceding entity
            preceding = self.line[:match.start()]
            scope = PRECEDING_MEMBER_REFERENCE.search(preceding)
            if scope:
                # Yes there is, check it out.
                self.checkPname(scope.group('entity_name'))
            elif self.pname_data is not None:
                # No, but there is a pname_context
                self.checkPname(self.pname_data.entity)
                if self.pname_data.entity in self.pname_mentions and self.pname_mentions[self.pname_data.entity] is not None:
                    # Record this mention, in case we're in the documentation block.
                    self.pname_mentions[self.pname_data.entity].add(entity)
            else:
                # no, and no existing pname_context from an include - can't check this.
                pass

    def recordInclude(self, include_dict, generated_type=None):
        entity = self.match.group('entity_name')
        if generated_type is None:
            generated_type = self.match.group('generated_type')

        if entity in include_dict:
            self.warning(MessageId.DUPLICATE_INCLUDE,
                         "Included {} docs for {} when they were already included.".format(generated_type,
                                                                                           entity), see_also=include_dict[entity])
            include_dict[entity].append(self.storeMessageContext())
        else:
            include_dict[entity] = [self.storeMessageContext()]

    def processLine(self, lineNum, line):
        self.lineNum = lineNum
        self.line = line
        self.match = None
        self.entity = None
        self.macro = None

        if line.startswith('----'):
            self.in_code_block = not self.in_code_block
            return

        if self.in_code_block:
            # We do no processing in a code block.
            return

        ###
        # Detect headings
        if line.startswith('=='):
            # Headings cause us to clear our pname_context
            self.pname_data = None

            command = HEADING_COMMAND.match(line)
            if command:
                data = self.checker.findEntity(command)
                if data:
                    self.pname_data = data
            return

        ###
        # Detect [open, lines for manpages
        # TODO: Verify these (and use for pname context) instead of skipping them.
        if line.startswith('[open,refpage='):
            return

        ###
        # Skip comments
        if line.lstrip().startswith('//'):
            return

        ###
        # Skip ifdef/endif
        if SKIP_LINE.match(line):
            return

        ###
        # Detect include:::....[] lines
        match = INCLUDE.match(line)
        if match:
            self.match = match
            entity = match.group('entity_name')

            if not entity in self.checker.byEntity:
                self.warning(MessageId.UNKNOWN_INCLUDE, ['Saw include for {}, but that entity is unknown.'.format(entity),
                                                         'This could be typo, or it could be a bug in check_spec_links.'])
                self.pname_data = None
                return

            self.pname_data = self.checker.byEntity[entity]

            if match.group('generated_type') == 'api':
                self.recordInclude(self.checker.apiIncludes)

                # Set mentions to None. The first time we see something like `* pname:paramHere`,
                # we will set it to an empty set
                self.pname_mentions[entity] = None

                if match.group('category') in CATEGORIES_WITH_VALIDITY:
                    self.fs_api_includes[entity] = self.storeMessageContext()

                if entity in self.validity_includes:
                    self.warning(MessageId.API_VALIDITY_ORDER,
                                 ['/api/ include found for {} after a corresponding /validity/ include'.format(entity),
                                  'Validity include located at {}'.format(toNameAndLine(self.validity_includes[entity]))])

            elif match.group('generated_type') == 'validity':
                self.recordInclude(self.checker.validityIncludes)
                self.validity_includes[entity] = self.storeMessageContext()

                if self.pname_mentions[entity] is not None:
                    # Got a validity include and we have seen at least one * pname: line since we got the API include
                    # so we can warn if we haven't seen a reference to every parameter/member.
                    members = self.checker.getMemberNames(entity)
                    missing = [member for member in members
                               if member not in self.pname_mentions[entity]]
                    if len(missing) > 0:
                        self.warning(MessageId.UNDOCUMENTED_MEMBER,
                                     ['Validity include found for {}, but not all members/params apparently documented'.format(entity),
                                      'Members/params not mentioned with pname: {}'.format(
                                         ', '.join(missing))])

            # If we found an include line, we're done with this line.
            return

        if self.pname_data is not None and '* pname:' in line:
            context_entity = self.pname_data.entity
            if self.pname_mentions[context_entity] is None:
                # First time seeting * pname: after an api include, prepare the set that
                # tracks
                self.pname_mentions[context_entity] = set()

        ###
        # Detect [[Entity]] anchors
        for match in ANCHOR.finditer(line):
            entity = match.group('entity_name')
            if self.checker.findEntity(entity):
                # We found an anchor with the same name as an entity - treat it like an API include
                self.match = match
                self.recordInclude(self.checker.apiIncludes,
                                   generated_type='api (manual anchor)')

        ###
        # Detect :: without pname
        for match in MEMBER_REFERENCE.finditer(line):
            if not match.group('member_macro'):
                self.match = match
                # Got :: but not followed by pname

                search = match.group()
                replacement = match.group(
                    'first_part') + '::pname:' + match.group('second_part')
                self.error(MessageId.MEMBER_PNAME_MISSING,
                           'Found a function parameter or struct member reference with :: but missing pname:',
                           group='double_colons',
                           replacement='::pname:',
                           fix=(search, replacement))

                # check pname here because it won't come up in normal iteration below
                # because of the missing macro
                self.entity = match.group('entity_name')
                self.checkPname(match.group('scope'))

        ###
        # Look for things that seem like a missing macro.
        for match in SUSPECTED_MISSING_MACRO.finditer(line):
            if OPEN_LINK.match(line, endpos=match.start()):
                # this is in a link, skip it.
                continue
            if CLOSE_LINK.match(line[match.end():]):
                # this is in a link, skip it.
                continue

            entity = match.group('entity_name')
            self.match = match
            self.entity = entity
            data = self.checker.findEntity(entity)
            if data:

                if data.category == EXTENSION_CATEGORY:
                    # Ah, this is an extension
                    self.warning(MessageId.EXTENSION, "Seems like this is an extension name that was not linked.",
                                 group='entity_name', replacement=self.makeExtensionLink())
                else:
                    self.warning(MessageId.MISSING_MACRO,
                                 ['Seems like a macro was omitted for this reference to a known entity in category "{}".'.format(data.category),
                                  'Wrap in ` ` to silence this if you do not want a verified macro here.'],
                                 group='entity_name',
                                 replacement=self.makeMacroMarkup(data.macro))
            else:

                dataArray = self.checker.findEntityCaseInsensitive(entity)
                # We might have found the goof...

                if dataArray:
                    if len(dataArray) == 1:
                        # Yep, found the goof - incorrect macro and entity capitalization
                        data = dataArray[0]
                        if data.category == EXTENSION_CATEGORY:
                            # Ah, this is an extension
                            self.warning(MessageId.EXTENSION,
                                         "Seems like this is an extension name that was not linked.",
                                         group='entity_name', replacement=self.makeExtensionLink(data.entity))
                        else:
                            self.warning(MessageId.MISSING_MACRO,
                                         'Seems like a macro was omitted for this reference to a known entity in category "{}", found by searching case-insensitively.'.format(
                                             data.category),
                                         replacement=self.makeMacroMarkup(data=data))

                    else:
                        # Ugh, more than one resolution

                        self.warning(MessageId.MISSING_MACRO,
                                     ['Seems like a macro was omitted for this reference to a known entity, found by searching case-insensitively.',
                                      'More than one apparent match.'],
                                     group='entity_name', see_also=dataArray[:])

        ###
        # Main operations: detect markup macros
        for match in self.checker.regex.finditer(line):
            self.match = match
            self.macro = match.group('macro')
            self.entity = match.group('entity_name')
            self.subscript = match.group('subscript')
            self.processMatch()

    def process(self):
        with self.stream_maker.make_stream() as f:
            for lineIndex, line in enumerate(f):
                trimmedLine = line.rstrip()
                self.lines.append(trimmedLine)
                self.processLine(lineIndex + 1, trimmedLine)

        # Check that every include of an /api/ file in the protos or structs category
        # had a matching /validity/ include
        for entity, includeContext in self.fs_api_includes.items():
            if not self.checker.entityHasValidity(entity):
                continue

            if entity in MISSING_VALIDITY_SUPPRESSIONS:
                continue

            if entity not in self.validity_includes:
                self.warning(MessageId.MISSING_VALIDITY_INCLUDE,
                             ['Saw /api/ include for {}, but no matching /validity/ include'.format(entity),
                              'Expected a line with ' + regenerateIncludeFromMatch(includeContext.match, 'validity')],
                             context=includeContext)

        # Check that we never include a /validity/ file without a matching /api/ include
        for entity, includeContext in self.validity_includes.items():
            if entity not in self.fs_api_includes:
                self.warning(MessageId.MISSING_API_INCLUDE,
                             ['Saw /validity/ include for {}, but no matching /api/ include'.format(entity),
                              'Expected a line with ' + regenerateIncludeFromMatch(includeContext.match, 'api')],
                             context=includeContext)

        if not self.numDiagnostics():
            # no problems, exit quietly
            return

        print('\nFor file {}:'.format(self.filename))

        self.printMessageCounts()
        numFixes = len(self.fixes)
        if numFixes > 0:
            fixes = ', '.join(['{} -> {}'.format(search, replace)
                               for search, replace in self.fixes])

            print('{} unique auto-fix {} recorded: {}'.format(numFixes,
                                                              pluralize(
                                                                  'pattern', numFixes),
                                                              fixes))


class MacroChecker(object):
    def __init__(self, enabled_messages):
        self.enabled_messages = enabled_messages

        self.files = []

        self.byEntity = {}
        self.byLowercaseEntity = {}
        self.byMacroAndEntity = {}

        self.categoriesByMacro = {}

        # keys: entity names. values: MessageContext
        self.links = {}
        self.apiIncludes = {}
        self.validityIncludes = {}
        self.headings = {}

        # Entities that get a generated/api/category/entity.txt file.
        self.generatingEntities = {}

        # The rest are added later inside addMacros

        self.linkedMacros = set(['basetype'])

        self.registryFile = str(REGISTRY_FILE)
        self.registry = Registry()
        self.registry.loadFile(self.registryFile)
        self.registry.parseTree()

        self.addMacro('basetype', ['basetypes'])
        self.addMacro('code', ['code'])
        self.addMacros('f', ['link', 'name', 'text'], ['protos'])
        self.addMacros('s', ['link', 'name', 'text'], ['structs', 'handles'])
        self.addMacros('e', ['link', 'name', 'text'], ['enums'])
        self.addMacros('p', ['name', 'text'], ['parameter', 'member'])
        self.addMacros('t', ['link', 'name'], ['funcpointers', 'flags'])
        self.addMacros('d', ['link', 'name'], ['defines', 'configdefines'])

        self.NON_EXISTENT_MACROS = set(['plink', 'ttext', 'dtext'])
        for macro in self.NON_EXISTENT_MACROS:
            # Still search for them
            self.addMacro(macro, None)

        # the "formatting" group is to strip matching */**/_/__ surrounding an entire macro.
        self.regex = re.compile(
            r'(?P<formatting>\**|_*)(?P<macro>{}):(?P<entity_name>[\w*]+((?P<subscript>[\[][^\]]*[\]]))?)(?P=formatting)'.format('|'.join([re.escape(macro) for macro in self.categoriesByMacro])))

        for t in SYSTEM_TYPES:
            self.addEntity(t, 'code', generates=False)

        for name, info in self.registry.typedict.items():
            if name in SYSTEM_TYPES:
                # We already added these.
                continue

            requires = info.elem.get('requires')
            if requires == PLATFORM_REQUIRES:
                # Ah, no, don't skip this, it's just in the platform header file.
                # TODO are these code or basetype?
                self.addEntity(name, 'code', elem=info.elem)
                continue

            if requires and not requires.lower().startswith(NAME_PREFIX):
                # This is an externally-defined type, will skip it.
                continue

            protect = info.elem.get('protect')
            if protect:
                self.addEntity(protect, 'dlink', category='configdefines')

            cat = info.elem.get('category')
            if cat == 'struct':
                self.addEntity(name, 'slink', elem=info.elem)

            elif cat == 'union':
                # TODO: is this right?
                self.addEntity(name, 'slink', elem=info.elem)

            elif cat == 'enum':
                self.addEntity(
                    name, 'elink', elem=info.elem)

            elif cat == 'handle':
                self.addEntity(name, 'slink', elem=info.elem,
                               category='handles')

            elif cat == 'bitmask':
                self.addEntity(
                    name, 'tlink', elem=info.elem, category='flags')

            elif cat == 'basetype':
                self.addEntity(name, 'basetype',
                               elem=info.elem)

            elif cat == 'define':
                self.addEntity(name, 'dlink', elem=info.elem)

            elif cat == 'funcpointer':
                self.addEntity(name, 'tlink', elem=info.elem)

            elif cat == 'include':
                # skip
                continue

            elif cat is None:
                self.addEntity(name, 'code', elem=info.elem)

            else:
                raise RuntimeError('unrecognized category {}'.format(cat))

        for name, info in self.registry.enumdict.items():
            self.addEntity(name, 'ename', elem=info.elem,
                           category='enumvalues')

        for name, info in self.registry.cmddict.items():
            self.addEntity(name, 'flink', elem=info.elem,
                           category='commands', directory='protos')

        for name, info in self.registry.extdict.items():
            # Only get the protect strings and name from extensions

            self.addEntity(name, None, category=EXTENSION_CATEGORY,
                           generates=False)
            protect = info.elem.get('protect')
            if protect:
                self.addEntity(protect, 'dlink', category='configdefines')

        # These are not mentioned in the XML
        for name in EXTRA_DEFINES:
            self.addEntity(name, 'dlink', category='configdefines')

    def addMacro(self, macro, categories):
        self.categoriesByMacro[macro] = categories

    def addMacros(self, letter, macroTypes, categories):
        for macroType in macroTypes:
            macro = letter + macroType
            self.addMacro(macro, categories)
            if macroType == 'link':
                self.linkedMacros.add(macro)

    def addEntity(self, entityName, macro, category=None, elem=None, filename=None,  directory=None, generates=True):
        if category is None:
            category = self.categoriesByMacro.get(macro)[0]
        if directory is None:
            directory = category

        # Don't generate a filename for ename or code, or configdefines because there are no files for those.
        if filename is None and macro not in ['ename', 'code'] and category != 'configdefines' and generates:
            filename = '{}/{}.txt'.format(directory, entityName)

        data = EntityData(
            entity=entityName,
            macro=macro,
            elem=elem,
            filename=filename,
            category=category
        )
        if entityName in self.byEntity:
            # skip
            return
        if entityName.lower() not in self.byLowercaseEntity:
            self.byLowercaseEntity[entityName.lower()] = []

        self.byEntity[entityName] = data
        self.byLowercaseEntity[entityName.lower()].append(data)
        self.byMacroAndEntity[(macro, entityName)] = data
        if generates and filename is not None:
            self.generatingEntities[entityName] = data

    def haveLinkTarget(self, entity):
        if not self.findEntity(entity):
            return None
        if entity in self.apiIncludes:
            return True
        return entity in self.headings

    def hasFixes(self):
        for f in self.files:
            if f.hasFixes():
                return True
        return False

    def addLinkToEntity(self, entity, context):
        if entity not in self.links:
            self.links[entity] = []
        self.links[entity].append(context)

    def findMacroAndEntity(self, macro, entity):
        return self.byMacroAndEntity.get((macro, entity))

    def findEntity(self, entity):
        return self.byEntity.get(entity)

    def findEntityCaseInsensitive(self, entity):
        return self.byLowercaseEntity.get(entity.lower())

    def getMemberElems(self, commandOrStruct):
        data = self.findEntity(commandOrStruct)

        if not data:
            return None
        if data.macro == 'slink':
            tag = 'member'
        else:
            tag = 'param'
        return data.elem.findall('.//{}'.format(tag))

    def getMemberNames(self, commandOrStruct):
        members = self.getMemberElems(commandOrStruct)
        if not members:
            return []
        ret = []
        for member in members:
            name_tag = member.find('name')
            if name_tag:
                ret.append(name_tag.text)
        return ret

    def entityHasValidity(self, entity):
        # Related to ValidityGenerator.isStructAlwaysValid
        data = self.findEntity(entity)
        if not data:
            return None

        if entity in ENTITIES_WITHOUT_VALIDITY:
            return False

        if data.category == 'protos':
            # All protos have validity
            return True

        if data.category not in CATEGORIES_WITH_VALIDITY:
            return False

        # Handle structs here.
        members = self.getMemberElems(entity)
        if not members:
            return None
        for member in members:

            if member.find('name').text in ['next', 'type']:
                return True

            if member.find('type').text in ['void', 'char']:
                return True

            if member.get('noautovalidity'):
                # Not generating validity for this member, skip it
                continue

            if member.get('len'):
                # Array
                return True

            typetail = member.find('type').tail
            if typetail and '*' in typetail:
                # Pointer
                return True

            if member.get('category') in ['handle', 'enum', 'bitmask'] == 'type':
                return True

            if member.get('category') in ['struct', 'union'] and self.entityHasValidity(member.find('type').text):
                # struct or union member - recurse
                return True

        # Got this far - no validity needed
        return False

    def processFile(self, filename):
        class FileStreamMaker(object):
            def __init__(self, filename):
                self.filename = filename

            def make_stream(self):
                return open(self.filename, 'r', encoding='utf-8')

        f = MacroCheckerFile(self, filename, self.enabled_messages,
                             FileStreamMaker(filename))
        f.process()
        self.files.append(f)

    def processString(self, s):
        """For testing purposes"""
        filename = "string{}".format(len(self.files))

        class StringStreamMaker(object):
            def __init__(self, string):
                self.string = string

            def make_stream(self):
                return StringIO(self.string)

        f = MacroCheckerFile(self, filename, self.enabled_messages,
                             StringStreamMaker(s))
        f.process()
        self.files.append(f)
        return f

    def numDiagnostics(self):
        return sum([f.numDiagnostics() for f in self.files])

    def numErrors(self):
        return sum([f.numErrors() for f in self.files])

    def getEntityJson(self):
        """Dump the internal entity dictionary to JSON for debugging"""
        d = {entity: entityToDict(data)
             for entity, data in self.byEntity.items()}
        return json.dumps(d, sort_keys=True, indent=4)

    def getMissingUnreferencedApiIncludes(self):
        return [entity for entity, data in self.generatingEntities.items()
                if (not self.haveLinkTarget(entity)) and entity not in self.links]

    def getBrokenLinks(self):
        return {entity: contexts for entity, contexts in self.links.items()
                if entity in self.generatingEntities and not self.haveLinkTarget(entity)}


class BasePrinter(ABC):
    def close(self):
        pass

    def getRelativeFilename(self, fn):
        try:
            return str(Path(fn).relative_to(CWD))
        except ValueError:
            return str(Path(fn))

    def formatContext(self, context, message_type=None):
        return self.formatContextBrief(context)

    def formatContextBrief(self, context, with_color=True):
        return '{}:{}:{}'.format(self.getRelativeFilename(context.filename),
                                 context.lineNum, getColumn(context))

    def formatMessageTypeBrief(self, message_type, with_color=True):
        return '{}:'.format(message_type)

    def formatEntityBrief(self, entity_data, with_color=True):
        return '{}:{}'.format(entity_data.macro, entity_data.entity)

    def formatBrief(self, obj, with_color=True):
        if isinstance(obj, MessageContext):
            return self.formatContextBrief(obj, with_color)
        if isinstance(obj, MessageType):
            return self.formatMessageTypeBrief(obj, with_color)
        if isinstance(obj, EntityData):
            return self.formatEntityBrief(obj, with_color)
        return str(obj)

    @abstractmethod
    def outputMessage(self, msg):
        raise NotImplementedError

    @abstractmethod
    def outputFallback(self, msg):
        raise NotImplementedError

    def outputCheckerFile(self, fileChecker):
        for m in fileChecker.messages:
            self.output(m)

    def outputChecker(self, checker):
        for f in checker.files:
            self.output(f)

    def output(self, obj):
        if isinstance(obj, Message):
            self.outputMessage(obj)
        elif isinstance(obj, MacroCheckerFile):
            self.outputCheckerFile(obj)
        elif isinstance(obj, MacroChecker):
            self.outputChecker(obj)
        else:
            self.outputFallback(self.formatBrief(obj))

    @abstractmethod
    def outputResults(self, checker, broken_links=True, missing_includes=False):
        raise NotImplementedError


class ConsolePrinter(BasePrinter):

    def formatFilename(self, fn, with_color=True):
        return self.getRelativeFilename(fn)

    def formatMessageTypeBrief(self, message_type, with_color=True):
        if with_color:
            return message_type.formattedWithColon()
        else:
            return super(ConsolePrinter, self).formatMessageTypeBrief(message_type, with_color)

    def outputFallback(self, obj):
        print(obj)

    def outputMessage(self, msg):
        highlightStart, highlightEnd = getHighlightedRange(msg.context)

        fileAndLine = colored('{}:'.format(
            self.formatBrief(msg.context)), attrs=['bold'])

        headingSize = len('{context}: {mtype}: '.format(
            context=self.formatBrief(msg.context),
            mtype=self.formatBrief(msg.message_type, False)))
        indent = ' ' * headingSize
        printedHeading = False

        lines = msg.message[:]
        if msg.see_also is not None and len(msg.see_also) != 0:
            lines.append('See also:')
            for see in msg.see_also:
                lines.append('  {}'.format(self.formatBrief(see)))

        if msg.fix is not None:
            lines.append('Note: Auto-fix available')

        for line in msg.message:
            if not printedHeading:
                scriptloc = ''
                if msg.script_location:
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

    def outputBrokenLinks(self, checker, broken):
        print('Missing API includes that are referenced by a linking macro: these result in broken links in the spec!')

        def makeRowOfBroken(entity, uses):
            fn = checker.findEntity(entity).filename
            anchor = '[[{}]]'.format(entity)
            locations = ', '.join([toNameAndLine(context)
                                   for context in uses])
            return (fn, anchor, locations)
        printTabulated(sorted([makeRowOfBroken(entity, uses)
                               for entity, uses in broken.items()]),
                       headers=['Include File', 'Anchor in lieu of include', 'Links to this entity'])

    def outputMissingIncludes(self, checker, missing):
        print(
            'Missing, but unreferenced, API includes/anchors - potentially not-documented entities:')

        def makeRowOfMissing(entity):
            fn = checker.findEntity(entity).filename
            anchor = '[[{}]]'.format(entity)
            return (fn, anchor)
        printTabulated(sorted([makeRowOfMissing(entity) for entity in missing]),
                       headers=['Include File', 'Anchor in lieu of include'])

    def outputResults(self, checker, broken_links=True, missing_includes=False):
        self.output(checker)
        if broken_links:
            broken = checker.getBrokenLinks()
            if len(broken) > 0:
                self.outputBrokenLinks(checker, broken)
        if missing_includes:
            missing = checker.getMissingUnreferencedApiIncludes()
            if len(missing) > 0:
                self.outputMissingIncludes(checker, missing)


MESSAGE_TYPE_STYLES = {
    MessageType.ERROR: 'danger',
    MessageType.WARNING: 'warning',
    MessageType.NOTE: 'secondary'
}


MESSAGE_TYPE_ICONS = {
    MessageType.ERROR: '&#x2297;',  # makeIcon('times-circle'),
    MessageType.WARNING: '&#9888;',  # makeIcon('exclamation-triangle'),
    MessageType.NOTE: '&#x2139;'  # makeIcon('info-circle')
}

LINK_ICON = '&#128279;'  # link icon


class HTMLPrinter(BasePrinter):
    def __init__(self, filename):
        self.f = open(filename, 'w', encoding='utf-8')
        self.f.write("""<!doctype html>
        <html lang="en"><head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/themes/prism.min.css" integrity="sha256-N1K43s+8twRa+tzzoF3V8EgssdDiZ6kd9r8Rfgg8kZU=" crossorigin="anonymous" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/line-numbers/prism-line-numbers.min.css" integrity="sha256-Afz2ZJtXw+OuaPX10lZHY7fN1+FuTE/KdCs+j7WZTGc=" crossorigin="anonymous" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/line-highlight/prism-line-highlight.min.css" integrity="sha256-FFGTaA49ZxFi2oUiWjxtTBqoda+t1Uw8GffYkdt9aco=" crossorigin="anonymous" />
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css" integrity="sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO" crossorigin="anonymous">
        <style>
        pre {
            overflow-x: scroll;
            white-space: nowrap;
        }
        </style>
        <title>check_spec_links results</title>
        </head>
        <body>
        <div class="container">
        <h1><code>check_spec_links.py</code> Scan Results</h1>
        """)
        #
        self.filenameTransformer = re.compile(r'[^\w]+')
        self.fileRange = {}
        self.fileLines = {}
        self.backLink = namedtuple(
            'BackLink', ['lineNum', 'col', 'end_col', 'target', 'tooltip', 'message_type'])
        self.fileBackLinks = {}

        self.nextAnchor = 0

    def close(self):
        self.f.write("""
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/prism.min.js" integrity="sha256-jc6y1s/Y+F+78EgCT/lI2lyU7ys+PFYrRSJ6q8/R8+o=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/keep-markup/prism-keep-markup.min.js" integrity="sha256-mP5i3m+wTxxOYkH+zXnKIG5oJhXLIPQYoiicCV1LpkM=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/components/prism-asciidoc.min.js" integrity="sha256-NHPE1p3VBIdXkmfbkf/S0hMA6b4Ar4TAAUlR+Rlogoc=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/line-numbers/prism-line-numbers.min.js" integrity="sha256-JfF9MVfGdRUxzT4pecjOZq6B+F5EylLQLwcQNg+6+Qk=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/line-highlight/prism-line-highlight.min.js" integrity="sha256-DEl9ZQE+lseY13oqm2+mlUr+sVI18LG813P+kzzIm8o=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.3.1/jquery.slim.min.js" integrity="sha256-3edrmyuQ0w65f8gfBsqowzjJe2iM6n0nKciPUp8y+7E=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.6/esm/popper.min.js" integrity="sha256-T0gPN+ySsI9ixTd/1ciLl2gjdLJLfECKvkQjJn98lOs=" crossorigin="anonymous"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js" integrity="sha384-ChfqqxuZUCnJSK3+MXmPNIyE6ZbWh2IMqE241rYiqJxyMiZ6OW/JmZQ5stwEULTy" crossorigin="anonymous"></script>
        <script>
        $(function () {
            $('[data-toggle="tooltip"]').tooltip();
            function autoExpand() {
                var hash = window.location.hash;
                if (!hash) {
                    return;
                }
                $(hash).parents().filter('.collapse').collapse('show');
            }
            window.addEventListener('hashchange', autoExpand);
            $(document).ready(autoExpand);
            $('.accordion').on('shown.bs.collapse', function(e) {
                e.target.parentNode.scrollIntoView();
            })
        })
        </script>
        </body></html>
        """)
        self.f.close()

    def recordUsage(self, context, linkBackTooltip=None, linkBackTarget=None, linkBackType=MessageType.NOTE):
        BEFORE_CONTEXT = 6
        AFTER_CONTEXT = 3
        # Clamp because we need accurate start line number to make line number display right
        start = max(1, context.lineNum - BEFORE_CONTEXT)
        stop = context.lineNum + AFTER_CONTEXT + 1
        if context.filename not in self.fileRange:
            self.fileRange[context.filename] = range(start, stop)
            self.fileBackLinks[context.filename] = []
        else:
            oldRange = self.fileRange[context.filename]
            self.fileRange[context.filename] = range(
                min(start, oldRange.start), max(stop, oldRange.stop))

        if linkBackTarget is not None:
            start_col, end_col = getHighlightedRange(context)
            self.fileBackLinks[context.filename].append(self.backLink(
                lineNum=context.lineNum, col=start_col, end_col=end_col,
                target=linkBackTarget, tooltip=linkBackTooltip,
                message_type=linkBackType))

    def formatFilename(self, fn):
        return '<a href="{href}">{relative}</a>'.format(
            href=fn,
            relative=self.getRelativeFilename(fn))

    def formatContext(self, context, message_type=None):
        if message_type is None:
            icon = LINK_ICON
        else:
            icon = MESSAGE_TYPE_ICONS[message_type]
        return 'In context: <a href="{href}">{icon}{relative}:{lineNum}:{col}</a>'.format(
            href=self.getAnchorLinkForContext(context),
            icon=icon,
            id=self.makeIdentifierFromFilename(context.filename),
            relative=self.getRelativeFilename(context.filename),
            lineNum=context.lineNum,
            col=getColumn(context))

    def makeIdentifierFromFilename(self, fn):
        return self.filenameTransformer.sub('_', self.getRelativeFilename(fn))

    def getAnchorLinkForContext(self, context):
        return '#excerpt-{}.{}'.format(self.makeIdentifierFromFilename(context.filename), context.lineNum)

    def outputFallback(self, obj):
        self.f.write(obj)

    def getUniqueAnchor(self):
        """Create and return a new unique string usable as a link anchor"""
        anchor = 'anchor-{}'.format(self.nextAnchor)
        self.nextAnchor += 1
        return anchor

    def outputMessage(self, msg):
        anchor = self.getUniqueAnchor()

        self.recordUsage(msg.context,
                         linkBackTarget=anchor,
                         linkBackTooltip='{}: {} [...]'.format(
                             msg.message_type, msg.message[0]),
                         linkBackType=msg.message_type)

        self.f.write("""
        <div class="card">
        <div class="card-body">
        <h5 class="card-header bg bg-{style}" id="{anchor}">{icon} {t} Line {lineNum}, Column {col} (-{arg})</h5>
        <p class="card-text">
        """.format(
            anchor=anchor,
            icon=MESSAGE_TYPE_ICONS[msg.message_type],
            style=MESSAGE_TYPE_STYLES[msg.message_type],
            t=self.formatBrief(msg.message_type),
            lineNum=msg.context.lineNum,
            col=getColumn(msg.context),
            arg=msg.message_id.enable_arg()))
        self.f.write(self.formatContext(msg.context))
        self.f.write('<br/>')
        for line in msg.message:
            self.f.write(html.escape(line))
            self.f.write('<br />\n')
        self.f.write('</p>\n')
        if msg.see_also is not None and len(msg.see_also) != 0:
            self.f.write('<p>See also:</p><ul>\n')
            for see in msg.see_also:
                if isinstance(see, MessageContext):
                    self.f.write(
                        '<li>{}</li>\n'.format(self.formatContext(see)))
                    self.recordUsage(see,
                                     linkBackTarget=anchor,
                                     linkBackType=MessageType.NOTE,
                                     linkBackTooltip='see-also associated with {} at {}'.format(msg.message_type, self.formatContextBrief(see)))
                else:
                    self.f.write('<li>{}</li>\n'.format(self.formatBrief(see)))
            self.f.write('</ul>')
        if msg.replacement is not None:
            self.f.write(
                '<div class="alert alert-primary">Hover the highlight text to view suggested replacement.</div>')
        if msg.fix is not None:
            self.f.write(
                '<div class="alert alert-info">Note: Auto-fix available.</div>')
        if msg.script_location:
            self.f.write(
                '<p>Message originated at <code>{}</code></p>'.format(msg.script_location))
        self.f.write('<pre class="line-numbers language-asciidoc" data-start="{}"><code>'.format(
            msg.context.lineNum))
        highlightStart, highlightEnd = getHighlightedRange(msg.context)
        self.f.write(html.escape(msg.context.line[:highlightStart]))
        self.f.write(
            '<span class="border border-{}"'.format(MESSAGE_TYPE_STYLES[msg.message_type]))
        if msg.replacement is not None:
            self.f.write(
                ' data-toggle="tooltip" title="{}"'.format(msg.replacement))
        self.f.write('>')
        self.f.write(html.escape(
            msg.context.line[highlightStart:highlightEnd]))
        self.f.write('</span>')
        self.f.write(html.escape(msg.context.line[highlightEnd:]))
        self.f.write('</code></pre></div></div>')

    def outputCheckerFile(self, fileChecker):
        # Save lines for later
        self.fileLines[fileChecker.filename] = fileChecker.lines

        if not fileChecker.numDiagnostics():
            return

        self.f.write("""
        <div class="card">
        <div class="card-header" id="{id}-file-heading">
        <div class="row">
        <div class="col">
        <button data-target="#collapse-{id}" class="btn btn-link btn-primary mb-0 collapsed" type="button" data-toggle="collapse" aria-expanded="false" aria-controls="collapse-{id}">
        {relativefn}
        </button>
        </div>
        """.format(id=self.makeIdentifierFromFilename(fileChecker.filename), relativefn=html.escape(self.getRelativeFilename(fileChecker.filename))))
        self.f.write('<div class="col-1">')
        warnings = fileChecker.numMessagesOfType(MessageType.WARNING)
        if warnings > 0:
            self.f.write("""<span class="badge badge-warning" data-toggle="tooltip" title="{num} warnings in this file">
                            {icon}
                            {num}<span class="sr-only"> warnings</span></span>""".format(num=warnings, icon=MESSAGE_TYPE_ICONS[MessageType.WARNING]))
        self.f.write('</div>\n<div class="col-1">')
        errors = fileChecker.numMessagesOfType(MessageType.ERROR)
        if errors > 0:
            self.f.write("""<span class="badge badge-danger" data-toggle="tooltip" title="{num} errors in this file">
                            {icon}
                            {num}<span class="sr-only"> errors</span></span>""".format(num=errors, icon=MESSAGE_TYPE_ICONS[MessageType.ERROR]))
        self.f.write("""
        </div><!-- .col-1 -->
        </div><!-- .row -->
        </div><!-- .card-header -->
        <div id="collapse-{id}" class="collapse" aria-labelledby="{id}-file-heading" data-parent="#fileAccordion">
        <div class="card-body">
        """.format(
            linkicon=LINK_ICON,
            id=self.makeIdentifierFromFilename(fileChecker.filename), fn=html.escape(fileChecker.filename)))
        super(HTMLPrinter, self).outputCheckerFile(fileChecker)

        self.f.write("""
        </div><!-- .card-body -->
        </div><!-- .collapse -->
        </div><!-- .card -->
        <!-- ..................................... -->
        """.format(id=self.makeIdentifierFromFilename(fileChecker.filename)))

    def outputChecker(self, checker):
        self.f.write(
            '<div class="container"><h2>Per-File Warnings and Errors</h2>\n')
        self.f.write('<div class="accordion" id="fileAccordion">\n')
        super(HTMLPrinter, self).outputChecker(checker)
        self.f.write("""</div><!-- #fileAccordion -->
        </div><!-- .container -->\n""")

    def outputBrokenLinks(self, checker, broken):

        self.f.write("""
        <div class="container">
        <h2>Missing Referenced API Includes</h2>
        <p>Items here have been referenced by a linking macro, so these are all broken links in the spec!</p>
        <table class="table table-striped">
        <thead>
        <th scope="col">Add line to include this file</th>
        <th scope="col">or add this macro instead</th>
        <th scope="col">Links to this entity</th></thead>
        """)

        for entity in sorted(broken):
            uses = broken[entity]
            category = checker.findEntity(entity).category
            anchor = self.getUniqueAnchor()
            asciidocAnchor = '[[{}]]'.format(entity)
            include = generateInclude(dir_traverse='../../generated/',
                                      generated_type='api',
                                      category=category,
                                      entity=entity)
            self.f.write("""
            <tr id={}>
            <td><code class="text-dark language-asciidoc">{}</code></td>
            <td><code class="text-dark">{}</code></td>
            <td><ul class="list-inline">
            """.format(anchor, include, asciidocAnchor))
            for context in uses:
                self.f.write(
                    '<li class="list-inline-item">{}</li>'.format(self.formatContext(context, MessageType.NOTE)))
                self.recordUsage(context,
                                 linkBackTooltip='Link broken in spec: {} not included'.format(
                                     fn),
                                 linkBackTarget=anchor,
                                 linkBackType=MessageType.NOTE)
            self.f.write("""</ul></td></tr>""")
        self.f.write("""</table></div>""")

    def outputMissingIncludes(self, checker, missing):
        self.f.write("""
        <div class="container">
        <h2>Missing Unreferenced API Includes</h2>
        <p>These items are expected to be generated in the spec build process, but aren't included.
        However, as they also are not referenced by any linking macros, they aren't broken links - at worst they are undocumented entities,
        at best they are errors in <code>check_spec_links.py</code> logic computing which entities get generated files.</p>
        <table class="table table-striped">
        <thead>
        <th scope="col">Add line to include this file</th>
        <th scope="col">or add this macro instead</th>
        """)

        for entity in sorted(missing):
            fn = checker.findEntity(entity).filename
            anchor = '[[{}]]'.format(entity)
            self.f.write("""
            <tr>
            <td><code class="text-dark">{filename}</code></td>
            <td><code class="text-dark">{anchor}</code></td>
            """.format(filename=fn, anchor=anchor))
        self.f.write("""</table></div>""")

    def outputFileExcerpt(self, filename):
        self.f.write("""<div class="card">
            <div class="card-header" id="heading-{id}"><h5 class="mb-0">
            <button class="btn btn-link" type="button">
            {fn}
            </button></h5></div><!-- #heading-{id} -->
            <div class="card-body">
            """.format(id=self.makeIdentifierFromFilename(filename), fn=self.getRelativeFilename(filename)))
        lines = self.fileLines[filename]
        r = self.fileRange[filename]
        self.f.write("""<pre class="line-numbers language-asciidoc line-highlight" id="excerpt-{id}" data-start="{start}"><code>""".format(
            id=self.makeIdentifierFromFilename(filename),
            start=r.start))
        for lineNum, line in enumerate(lines[(r.start - 1):(r.stop - 1)], r.start):
            # self.f.write(line)
            lineLinks = [x for x in self.fileBackLinks[filename]
                         if x.lineNum == lineNum]
            # opened_links = 0
            for col, char in enumerate(line):
                colLinks = [x for x in lineLinks if x.col == col]
                # opened_links += len(colLinks)
                for link in colLinks:
                    # TODO right now the syntax highlighting is interfering with the link! so the link-generation is commented out,
                    # only generating the emoji icon.

                    # self.f.write('<a href="#{target}" title="{title}" data-toggle="tooltip" data-container="body">{icon}'.format(
                    #     target=link.target, title=html.escape(link.tooltip), icon=MESSAGE_TYPE_ICONS[link.message_type]))
                    self.f.write(MESSAGE_TYPE_ICONS[link.message_type])
                    self.f.write('<span class="sr-only">Cross reference: {t} {title}</span>'.format(
                        title=html.escape(link.tooltip, False), t=link.message_type))

                    # If you uncomment the following line, don't uncomment anything related to opened_links
                    # self.f.write('</a>')

                # Write the actual character
                self.f.write(html.escape(char))
                # Close any applicable links
                # links_to_close = len([x for x in lineLinks if x.end_col == col])
                # self.f.write('</a>' * links_to_close)
                # opened_links -= links_to_close

            # Close any leftovers
            # self.f.write('</a>' * opened_links)
            self.f.write('\n')

        self.f.write('</code></pre>')
        self.f.write('</div><!-- .card-body -->\n')
        self.f.write('</div><!-- .card -->\n')

    def outputResults(self, checker, broken_links=True, missing_includes=False):
        self.output(checker)
        if broken_links:
            broken = checker.getBrokenLinks()
            if len(broken) > 0:
                self.outputBrokenLinks(checker, broken)
        if missing_includes:
            missing = checker.getMissingUnreferencedApiIncludes()
            if len(missing) > 0:
                self.outputMissingIncludes(checker, missing)

        self.f.write("""
        <div class="container">
        <h2>Excerpts of referenced files</h2>""")
        for fn in self.fileRange:
            self.outputFileExcerpt(fn)
        self.f.write('</div><!-- .container -->\n')


if __name__ == '__main__':
    enabled_messages = MessageId.default_set()

    disable_args = []
    enable_args = []

    parser = argparse.ArgumentParser()
    parser.add_argument("-Werror", "--warning_error",
                        help="Make warnings act as errors, exiting with non-zero error code",
                        action="store_true")
    parser.add_argument("--include_warn",
                        help="List all expected but unseen include files, not just those that are referenced.",
                        action='store_true')
    parser.add_argument("--include_error",
                        help="Make expected but unseen include files cause exiting with non-zero error code",
                        action='store_true')
    parser.add_argument("--broken_error",
                        help="Make missing include/anchor for linked-to entities cause exiting with non-zero error code. Weaker version of --include_error.",
                        action='store_true')
    parser.add_argument("--dump_entities",
                        help="Just dump the parsed entity data to entities.json and exit.",
                        action='store_true')
    parser.add_argument("--html",
                        help="Output messages to the named HTML file instead of stdout.")
    parser.add_argument("file",
                        help="Only check the indicated file(s). By default, all chapters and extensions are checked.",
                        nargs="*")
    parser.add_argument("--ignore_count",
                        type=int,
                        help="Ignore up to the given number of errors without exiting with a non-zero error code.")
    parser.add_argument("-Wall",
                        help="Enable all warning categories.",
                        action='store_true')

    for message_id in MessageId:
        enable_arg = message_id.enable_arg()
        enable_args.append((message_id, enable_arg))

        disable_arg = message_id.disable_arg()
        disable_args.append((message_id, disable_arg))
        if message_id in enabled_messages:
            parser.add_argument('-' + enable_arg, action="store_true",
                                help="Disable message category {}: {}".format(str(message_id), message_id.desc()))
            # Don't show the disable flag in help since it's disabled by default
            parser.add_argument('-' + disable_arg, action="store_true",
                                help=argparse.SUPPRESS)
        else:
            parser.add_argument('-' + disable_arg, action="store_true",
                                help="Enable message category {}: {}".format(str(message_id), message_id.desc()))
            # Don't show the enable flag in help since it's enabled by default
            parser.add_argument('-' + enable_arg, action="store_true",
                                help=argparse.SUPPRESS)

    args = parser.parse_args()

    arg_dict = vars(args)
    for message_id, arg in enable_args:
        if args.Wall or (arg in arg_dict and arg_dict[arg]):
            enabled_messages.add(message_id)

    for message_id, arg in disable_args:
        if arg in arg_dict and arg_dict[arg]:
            enabled_messages.discard(message_id)

    checker = MacroChecker(enabled_messages)

    if args.dump_entities:
        with open('entities.json', 'w', encoding='utf-8') as f:
            f.write(checker.getEntityJson())
            exit(0)

    if args.file:
        files = [str(Path(f).resolve()) for f in args.file]
    else:
        files = ALL_DOCS

    for fn in files:
        checker.processFile(fn)

    if args.html:
        printer = HTMLPrinter(args.html)
    else:
        printer = ConsolePrinter()

    if args.file:
        printer.output("Only checked specified files.")
        for f in args.file:
            printer.output(f)
    else:
        printer.output("Checked all chapters and extensions.")

    if args.warning_error:
        numErrors = checker.numDiagnostics()
    else:
        numErrors = checker.numErrors()

    check_includes = args.include_warn
    check_broken = True
    if args.file and args.include_warn:
        print('Note: forcing --include_warn off because only checking supplied files.')
    printer.outputResults(checker, broken_links=(not args.file),
                          missing_includes=(args.include_warn and not args.file))

    if args.include_error and not args.file:
        numErrors += len(checker.getMissingUnreferencedApiIncludes())

    printer.close()

    if args.broken_error and not args.file:
        numErrors += len(checker.getBrokenLinks())

    if checker.hasFixes():
        fixFn = 'applyfixes.sh'
        print('Saving shell script to apply fixes as {}'.format(fixFn))
        with open(fixFn, 'w', encoding='utf-8') as f:
            f.write('#!/bin/sh -e\n')
            for fileChecker in checker.files:
                wroteComment = False
                for msg in fileChecker.messages:
                    if msg.fix is not None:
                        if not wroteComment:
                            f.write('\n# {}\n'.format(fileChecker.filename))
                            wroteComment = True
                        search, replace = msg.fix
                        f.write(
                            r"sed -i -r 's~\b{}\b~{}~g' {}".format(re.escape(search), replace, fileChecker.filename))
                        f.write('\n')

    print('Total number of errors with this run: {}'.format(numErrors))

    if args.ignore_count:
        if numErrors > args.ignore_count:
            # Exit with non-zero error code so that we "fail" CI, etc.
            print('Exceeded specified limit of {}, so exiting with error'.format(
                args.ignore_count))
            exit(1)
        else:
            print('At or below specified limit of {}, so exiting with success'.format(
                args.ignore_count))
            exit(0)

    if numErrors:
        # Exit with non-zero error code so that we "fail" CI, etc.
        print('Exiting with error')
        exit(1)
    else:
        print('Exiting with success')
        exit(0)
