"""Provides MacroCheckerFile, a subclassable type that validates a single file in the spec."""

# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>

import logging
import re
from collections import OrderedDict, namedtuple
from enum import Enum
from inspect import currentframe

from .shared import (AUTO_FIX_STRING, CATEGORIES_WITH_VALIDITY,
                     EXTENSION_CATEGORY, NON_EXISTENT_MACROS, EntityData,
                     Message, MessageContext, MessageId, MessageType,
                     generateInclude, toNameAndLine)

# Code blocks may start and end with any number of ----
CODE_BLOCK_DELIM = '----'

# Mostly for ref page blocks, but also used elsewhere?
REF_PAGE_LIKE_BLOCK_DELIM = '--'

# For insets/blocks like the implicit valid usage
# TODO think it must start with this - does it have to be exactly this?
BOX_BLOCK_DELIM = '****'


INTERNAL_PLACEHOLDER = re.compile(
    r'(?P<delim>__+)([a-zA-Z]+)(?P=delim)'
)

# Matches a generated (api or validity) include line.
INCLUDE = re.compile(
    r'include::(?P<directory_traverse>((../){1,4}|\{(INCS-VAR|generated)\}/)(generated/)?)(?P<generated_type>[\w]+)/(?P<category>\w+)/(?P<entity_name>[^./]+).txt[\[][\]]')

# Matches an [[AnchorLikeThis]]
ANCHOR = re.compile(r'\[\[(?P<entity_name>[^\]]+)\]\]')

# Looks for flink:foo:: or slink::foo:: at the end of string:
# used to detect explicit pname context.
PRECEDING_MEMBER_REFERENCE = re.compile(
    r'\b(?P<macro>[fs](text|link)):(?P<entity_name>[\w*]+)::$')

# Matches something like slink:foo::pname:bar as well as
# the under-marked-up slink:foo::bar.
MEMBER_REFERENCE = re.compile(
    r'\b(?P<first_part>(?P<scope_macro>[fs](text|link)):(?P<scope>[\w*]+))(?P<double_colons>::)(?P<second_part>(?P<member_macro>pname:?)(?P<entity_name>[\w]+))\b'
)

# Matches if a string ends while a link is still "open".
# (first half of a link being broken across two lines,
# or containing our interested area when matched against the text preceding).
# Used to skip checking in some places.
OPEN_LINK = re.compile(
    r'.*(?<!`)<<[^>]*$'
)

# Matches if a string begins and is followed by a link "close" without a matching open.
# (second half of a link being broken across two lines)
# Used to skip checking in some places.
CLOSE_LINK = re.compile(
    r'[^<]*>>.*$'
)

# Matches if a line should be skipped without further considering.
# Matches lines starting with:
# - `ifdef:`
# - `endif:`
# - `todo` (followed by something matching \b, like : or (. capitalization ignored)
SKIP_LINE = re.compile(
    r'^(ifdef:)|(endif:)|([tT][oO][dD][oO]\b).*'
)

# Matches the whole inside of a refpage tag.
BRACKETS = re.compile(r'\[(?P<tags>.*)\]')

# Matches a key='value' pair from a ref page tag.
REF_PAGE_ATTRIB = re.compile(
    r"(?P<key>[a-z]+)='(?P<value>[^'\\]*(?:\\.[^'\\]*)*)'")


class Attrib(Enum):
    """Attributes of a ref page."""

    REFPAGE = 'refpage'
    DESC = 'desc'
    TYPE = 'type'
    ALIAS = 'alias'
    XREFS = 'xrefs'
    ANCHOR = 'anchor'


VALID_REF_PAGE_ATTRIBS = set(
    (e.value for e in Attrib))

AttribData = namedtuple('AttribData', ['match', 'key', 'value'])


def makeAttribFromMatch(match):
    """Turn a match of REF_PAGE_ATTRIB into an AttribData value."""
    return AttribData(match=match, key=match.group(
        'key'), value=match.group('value'))


def parseRefPageAttribs(line):
    """Parse a ref page tag into a dictionary of attribute_name: AttribData."""
    return {m.group('key'): makeAttribFromMatch(m)
            for m in REF_PAGE_ATTRIB.finditer(line)}


def regenerateIncludeFromMatch(match, generated_type):
    """Create an include directive from an INCLUDE match and a (new or replacement) generated_type."""
    return generateInclude(
        match.group('directory_traverse'),
        generated_type,
        match.group('category'),
        match.group('entity_name'))


BlockEntry = namedtuple(
    'BlockEntry', ['delimiter', 'context', 'block_type', 'refpage'])


class BlockType(Enum):
    """Enumeration of the various distinct block types known."""
    CODE = 'code'
    REF_PAGE_LIKE = 'ref-page-like'  # with or without a ref page tag before
    BOX = 'box'

    @classmethod
    def lineToBlockType(self, line):
        """Return a BlockType if the given line is a block delimiter.

        Returns None otherwise.
        """
        if line == REF_PAGE_LIKE_BLOCK_DELIM:
            return BlockType.REF_PAGE_LIKE
        if line.startswith(CODE_BLOCK_DELIM):
            return BlockType.CODE
        if line.startswith(BOX_BLOCK_DELIM):
            return BlockType.BOX

        return None


def _pluralize(word, num):
    if num == 1:
        return word
    if word.endswith('y'):
        return word[:-1] + 'ies'
    return word + 's'


def _s_suffix(num):
    """Simplify pluralization."""
    if num > 1:
        return 's'
    return ''


def shouldEntityBeText(entity, subscript):
    """Determine if an entity name appears to use placeholders, wildcards, etc. and thus merits use of a *text macro.

    Call with the entity and subscript groups from a match of MacroChecker.macro_re.
    """
    entity_only = entity
    if subscript:
        if subscript == '[]' or subscript == '[i]' or subscript.startswith(
                '[_') or subscript.endswith('_]'):
            return True
        entity_only = entity[:-len(subscript)]

    if ('*' in entity) or entity.startswith('_') or entity_only.endswith('_'):
        return True

    if INTERNAL_PLACEHOLDER.search(entity):
        return True
    return False


class MacroCheckerFile(object):
    """Object performing processing of a single AsciiDoctor file from a specification.

    For testing purposes, may also process a string as if it were a file.
    """

    def __init__(self, checker, filename, enabled_messages, stream_maker):
        """Construct a MacroCheckerFile object.

        Typically called by MacroChecker.processFile or MacroChecker.processString().

        Arguments:
        checker -- A MacroChecker object.
        filename -- A string to use in messages to refer to this checker, typically the file name.
        enabled_messages -- A set() of MessageId values that should be considered "enabled" and thus stored.
        stream_maker -- An object with a makeStream() method that returns a stream.
        """
        self.checker = checker
        self.filename = filename
        self.stream_maker = stream_maker
        self.enabled_messages = enabled_messages
        self.missing_validity_suppressions = set(
            self.getMissingValiditySuppressions())

        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())

        self.fixes = set()
        self.messages = []

        self.pname_data = None
        self.pname_mentions = {}

        self.refpage_includes = {}

        self.lines = []

        # For both of these:
        # keys: entity name
        # values: MessageContext
        self.fs_api_includes = {}
        self.validity_includes = {}

        self.in_code_block = False
        self.in_ref_page = False
        self.prev_line_ref_page_tag = None
        self.current_ref_page = None

        # Stack of block-starting delimiters.
        self.block_stack = []

        # Regexes that are members because they depend on the name prefix.
        self.suspected_missing_macro_re = self.checker.suspected_missing_macro_re
        self.heading_command_re = self.checker.heading_command_re

    ###
    # Main process/checking methods, arranged roughly from largest scope to smallest scope.
    ###

    def process(self):
        """Check the stream (file, string) created by the streammaker supplied to the constructor.

        This is the top-level method for checking a spec file.
        """
        self.logger.info("processing file %s", self.filename)

        # File content checks - performed line-by-line
        with self.stream_maker.make_stream() as f:
            # Iterate through lines, calling processLine on each.
            for lineIndex, line in enumerate(f):
                trimmedLine = line.rstrip()
                self.lines.append(trimmedLine)
                self.processLine(lineIndex + 1, trimmedLine)

        # End of file checks follow:

        # Check "state" at end of file: should have blocks closed.
        if self.prev_line_ref_page_tag:
            self.error(MessageId.REFPAGE_BLOCK,
                       "Reference page tag seen, but block not opened before end of file.",
                       context=self.storeMessageContext(match=None))

        if self.block_stack:
            locations = (x.context for x in self.block_stack)
            formatted_locations = ['{} opened at {}'.format(x.delimiter, self.getBriefLocation(x.context))
                                   for x in self.block_stack]
            self.logger.warning("Unclosed blocks: %s",
                                ', '.join(formatted_locations))

            self.error(MessageId.UNCLOSED_BLOCK,
                       ["Reached end of page, with these unclosed blocks remaining:"] +
                       formatted_locations,
                       context=self.storeMessageContext(match=None),
                       see_also=locations)

        # Check that every include of an /api/ file in the protos or structs category
        # had a matching /validity/ include
        for entity, includeContext in self.fs_api_includes.items():
            if not self.checker.entity_db.entityHasValidity(entity):
                continue

            if entity in self.missing_validity_suppressions:
                continue

            if entity not in self.validity_includes:
                self.warning(MessageId.MISSING_VALIDITY_INCLUDE,
                             ['Saw /api/ include for {}, but no matching /validity/ include'.format(entity),
                              'Expected a line with ' + regenerateIncludeFromMatch(includeContext.match, 'validity')],
                             context=includeContext)

        # Check that we never include a /validity/ file
        # without a matching /api/ include
        for entity, includeContext in self.validity_includes.items():
            if entity not in self.fs_api_includes:
                self.error(MessageId.MISSING_API_INCLUDE,
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
            fixes = ', '.join(('{} -> {}'.format(search, replace)
                               for search, replace in self.fixes))

            print('{} unique auto-fix {} recorded: {}'.format(numFixes,
                                                              _pluralize('pattern', numFixes), fixes))

    def processLine(self, lineNum, line):
        """Check the contents of a single line from a file.

        Eventually populates self.match, self.entity, self.macro,
        before calling processMatch.
        """
        self.lineNum = lineNum
        self.line = line
        self.match = None
        self.entity = None
        self.macro = None

        self.logger.debug("processing line %d", lineNum)

        if self.processPossibleBlockDelimiter():
            # This is a block delimiter - proceed to next line.
            # Block-type-specific stuff goes in processBlockOpen and processBlockClosed.
            return

        if self.in_code_block:
            # We do no processing in a code block.
            return

        ###
        # Detect if the previous line was [open,...] starting a refpage
        # but this line isn't --
        # If the line is some other block delimiter,
        # the related code in self.processPossibleBlockDelimiter()
        # would have handled it.
        # (because execution would never get to here for that line)
        if self.prev_line_ref_page_tag:
            self.handleExpectedRefpageBlock()

        ###
        # Detect headings
        if line.startswith('=='):
            # Headings cause us to clear our pname_context
            self.pname_data = None

            command = self.heading_command_re.match(line)
            if command:
                data = self.checker.findEntity(command)
                if data:
                    self.pname_data = data
            return

        ###
        # Detect [open, lines for manpages
        if line.startswith('[open,'):
            self.checkRefPage()
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

            data = self.checker.findEntity(entity)
            if not data:
                self.error(MessageId.UNKNOWN_INCLUDE,
                           'Saw include for {}, but that entity is unknown.'.format(entity))
                self.pname_data = None
                return

            self.pname_data = data

            if match.group('generated_type') == 'api':
                self.recordInclude(self.checker.apiIncludes)

                # Set mentions to None. The first time we see something like `* pname:paramHere`,
                # we will set it to an empty set
                self.pname_mentions[entity] = None

                if match.group('category') in CATEGORIES_WITH_VALIDITY:
                    self.fs_api_includes[entity] = self.storeMessageContext()

                if entity in self.validity_includes:
                    name_and_line = toNameAndLine(
                        self.validity_includes[entity], root_path=self.checker.root_path)
                    self.error(MessageId.API_VALIDITY_ORDER,
                               ['/api/ include found for {} after a corresponding /validity/ include'.format(entity),
                                'Validity include located at {}'.format(name_and_line)])

            elif match.group('generated_type') == 'validity':
                self.recordInclude(self.checker.validityIncludes)
                self.validity_includes[entity] = self.storeMessageContext()

                if entity not in self.pname_mentions:
                    self.error(MessageId.API_VALIDITY_ORDER,
                               '/validity/ include found for {} without a preceding /api/ include'.format(entity))
                    return

                if self.pname_mentions[entity]:
                    # Got a validity include and we have seen at least one * pname: line
                    # since we got the API include
                    # so we can warn if we haven't seen a reference to every
                    # parameter/member.
                    members = self.checker.getMemberNames(entity)
                    missing = [member for member in members
                               if member not in self.pname_mentions[entity]]
                    if missing:
                        self.error(MessageId.UNDOCUMENTED_MEMBER,
                                   ['Validity include found for {}, but not all members/params apparently documented'.format(entity),
                                    'Members/params not mentioned with pname: {}'.format(', '.join(missing))])

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
                # We found an anchor with the same name as an entity:
                # treat it (mostly) like an API include
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
        for match in self.suspected_missing_macro_re.finditer(line):
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
                                 ['Seems like a "{}" macro was omitted for this reference to a known entity in category "{}".'.format(data.macro, data.category),
                                  'Wrap in ` ` to silence this if you do not want a verified macro here.'],
                                 group='entity_name',
                                 replacement=self.makeMacroMarkup(data.macro))
            else:

                dataArray = self.checker.findEntityCaseInsensitive(entity)
                # We might have found the goof...

                if dataArray:
                    if len(dataArray) == 1:
                        # Yep, found the goof:
                        # incorrect macro and entity capitalization
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
        for match in self.checker.macro_re.finditer(line):
            self.match = match
            self.macro = match.group('macro')
            self.entity = match.group('entity_name')
            self.subscript = match.group('subscript')
            self.processMatch()

    def processPossibleBlockDelimiter(self):
        """Look at the current line, and if it's a delimiter, update the block stack.

        Calls self.processBlockDelimiter() as required.

        Returns True if a delimiter was processed, False otherwise.
        """
        line = self.line
        new_block_type = BlockType.lineToBlockType(line)
        if not new_block_type:
            return False

        ###
        # Detect if the previous line was [open,...] starting a refpage
        # but this line is some block delimiter other than --
        # Must do this here because if we get a different block open instead of the one we want,
        # the order of block opening will be wrong.
        if new_block_type != BlockType.REF_PAGE_LIKE and self.prev_line_ref_page_tag:
            self.handleExpectedRefpageBlock()

        # Delegate to the main process for delimiters.
        self.processBlockDelimiter(line, new_block_type)

        return True

    def processBlockDelimiter(self, line, new_block_type, context=None):
        """Update the block stack based on the current or supplied line.

        Calls self.processBlockOpen() or self.processBlockClosed() as required.

        Called by self.processPossibleBlockDelimiter() both in normal operation, as well as
        when "faking" a ref page block open.

        Returns BlockProcessResult.
        """
        if not context:
            context = self.storeMessageContext()

        location = self.getBriefLocation(context)

        top = self.getInnermostBlockEntry()
        top_delim = self.getInnermostBlockDelimiter()
        if top_delim == line:
            self.processBlockClosed()
            return

        if top and top.block_type == new_block_type:
            # Same block type, but not matching - might be an error?
            # TODO maybe create a diagnostic here?
            self.logger.warning(
                "processPossibleBlockDelimiter: %s: Matched delimiter type %s, but did not exactly match current delim %s to top of stack %s, may be a typo?",
                location, new_block_type, line, top_delim)

        # Empty stack, or top doesn't match us.
        self.processBlockOpen(new_block_type, delimiter=line)

    def processBlockOpen(self, block_type, context=None, delimiter=None):
        """Do any block-type-specific processing and push the new block.

        Must call self.pushBlock().
        May be overridden (carefully) or extended.

        Called by self.processBlockDelimiter().
        """
        if block_type == BlockType.REF_PAGE_LIKE:
            if self.prev_line_ref_page_tag:
                if self.current_ref_page:
                    refpage = self.current_ref_page
                else:
                    refpage = '?refpage-with-invalid-tag?'

                self.logger.info(
                    'processBlockOpen: Opening refpage for %s', refpage)
                # Opening of refpage block "consumes" the preceding ref
                # page context
                self.prev_line_ref_page_tag = None
                self.pushBlock(block_type, refpage=refpage,
                               context=context, delimiter=delimiter)
                self.in_ref_page = True
                return

        if block_type == BlockType.CODE:
            self.in_code_block = True

        self.pushBlock(block_type, context=context, delimiter=delimiter)

    def processBlockClosed(self):
        """Do any block-type-specific processing and pop the top block.

        Must call self.popBlock().
        May be overridden (carefully) or extended.

        Called by self.processPossibleBlockDelimiter().
        """
        old_top = self.popBlock()

        if old_top.block_type == BlockType.CODE:
            self.in_code_block = False

        elif old_top.block_type == BlockType.REF_PAGE_LIKE and old_top.refpage:
            self.logger.info(
                'processBlockClosed: Closing refpage for %s', old_top.refpage)
            # leaving a ref page so reset associated state.
            self.current_ref_page = None
            self.prev_line_ref_page_tag = None
            self.in_ref_page = False

    def processMatch(self):
        """Process a match of the macro:entity regex for correctness."""
        match = self.match
        entity = self.entity
        macro = self.macro

        ###
        # Track entities that we're actually linking to.
        ###
        if self.checker.entity_db.isLinkedMacro(macro):
            self.checker.addLinkToEntity(entity, self.storeMessageContext())

        ###
        # Link everything that should be, and nothing that shouldn't be
        ###
        if self.checkRecognizedEntity():
            # if this returns true,
            # then there is no need to do the remaining checks on this match
            return

        ###
        # Non-existent macros
        if macro in NON_EXISTENT_MACROS:
            self.error(MessageId.BAD_MACRO, '{} is not a macro provided in the specification, despite resembling other macros.'.format(
                macro), group='macro')

        ###
        # Wildcards (or leading underscore, or square brackets)
        # if and only if a 'text' macro
        self.checkText()

        # Do some validation of pname references.
        if macro == 'pname':
            # See if there's an immediately-preceding entity
            preceding = self.line[:match.start()]
            scope = PRECEDING_MEMBER_REFERENCE.search(preceding)
            if scope:
                # Yes there is, check it out.
                self.checkPname(scope.group('entity_name'))
            elif self.current_ref_page is not None:
                # No, but there is a current ref page: very reliable
                self.checkPnameImpliedContext(self.current_ref_page)
            elif self.pname_data is not None:
                # No, but there is a pname_context - better than nothing.
                self.checkPnameImpliedContext(self.pname_data)
            else:
                # no, and no existing context we can imply:
                # can't check this.
                pass

    def checkRecognizedEntity(self):
        """Check the current macro:entity match to see if it is recognized.

        Returns True if there is no need to perform further checks on this match.

        Helps avoid duplicate warnings/errors: typically each macro should have at most
        one of this class of errors.
        """
        entity = self.entity
        macro = self.macro
        if self.checker.findMacroAndEntity(macro, entity) is not None:
            # We know this macro-entity combo
            return True

        # We don't know this macro-entity combo.
        possibleCats = self.checker.entity_db.getCategoriesForMacro(macro)
        if possibleCats is None:
            possibleCats = ['???']
        msg = ['Definition of link target {} with macro {} (used for {} {}) does not exist.'.format(
            entity,
            macro,
            _pluralize('category', len(possibleCats)),
            ', '.join(possibleCats))]

        data = self.checker.findEntity(entity)
        if data:
            # We found the goof: incorrect macro
            msg.append('Apparently matching entity in category {} found.'.format(
                data.category))
            self.handleWrongMacro(msg, data)
            return True

        see_also = []
        dataArray = self.checker.findEntityCaseInsensitive(entity)
        if dataArray:
            # We might have found the goof...

            if len(dataArray) == 1:
                # Yep, found the goof:
                # incorrect macro and entity capitalization
                data = dataArray[0]
                msg.append('Apparently matching entity in category {} found by searching case-insensitively.'.format(
                    data.category))
                self.handleWrongMacro(msg, data)
                return True
            else:
                # Ugh, more than one resolution
                msg.append(
                    'More than one apparent match found by searching case-insensitively, cannot auto-fix.')
                see_also = dataArray[:]

        # OK, so we don't recognize this entity (and couldn't auto-fix it).

        if self.checker.entity_db.shouldBeRecognized(macro, entity):
            # We should know the target - it's a link macro,
            # or there's some reason the entity DB thinks we should know it.
            if self.checker.likelyRecognizedEntity(entity):
                # Should be linked and it matches our pattern,
                # so probably not wrong macro.
                # Human brains required.
                if not self.checkText():
                    self.error(MessageId.BAD_ENTITY, msg + ['Might be a misspelling, or, less likely, the wrong macro.'],
                               see_also=see_also)
            else:
                # Doesn't match our pattern,
                # so probably should be name instead of link.
                newMacro = macro[0] + 'name'
                if self.checker.entity_db.isValidMacro(newMacro):
                    self.error(MessageId.BAD_ENTITY, msg +
                               ['Entity name does not fit the pattern for this API, which would mean it should be a "name" macro instead of a "link" macro'],
                               group='macro', replacement=newMacro, fix=self.makeFix(newMacro=newMacro), see_also=see_also)
                else:
                    self.error(MessageId.BAD_ENTITY, msg +
                               ['Entity name does not fit the pattern for this API, which would mean it should be a "name" macro instead of a "link" macro',
                                'However, {} is not a known macro so cannot auto-fix.'.format(newMacro)], see_also=see_also)

        elif macro == 'ename':
            # TODO This might be an ambiguity in the style guide - ename might be a known enumerant value,
            # or it might be an enumerant value in an external library, etc. that we don't know about - so
            # hard to check this.
            if self.checker.likelyRecognizedEntity(entity):
                if not self.checkText():
                    self.warning(MessageId.BAD_ENUMERANT, msg +
                                 ['Unrecognized ename:{} that we would expect to recognize since it fits the pattern for this API.'.format(entity)], see_also=see_also)
        else:
            # This is fine:
            # it doesn't need to be recognized since it's not linked.
            pass
        # Don't skip other tests.
        return False

    def checkText(self):
        """Evaluate the usage (or non-usage) of a *text macro.

        Wildcards (or leading or trailing underscore, or square brackets with
        nothing or a placeholder) if and only if a 'text' macro.

        Called by checkRecognizedEntity() when appropriate.
        """
        macro = self.macro
        entity = self.entity
        shouldBeText = shouldEntityBeText(entity, self.subscript)
        if shouldBeText and not self.macro.endswith(
                'text') and not self.macro == 'code':
            newMacro = macro[0] + 'text'
            if self.checker.entity_db.getCategoriesForMacro(newMacro):
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
                if self.checker.likelyRecognizedEntity(entity):
                    # This is a use of *text: for something that fits the pattern but isn't in the spec.
                    # This is OK.
                    return False
                msg.append('Entity not found in spec, either.')
                if macro[0] != 'e':
                    # Only suggest a macro if we aren't in elink/ename/etext,
                    # since ename and elink are not related in an equivalent way
                    # to the relationship between flink and fname.
                    newMacro = macro[0] + 'name'
                    if self.checker.entity_db.getCategoriesForMacro(newMacro):
                        msg.append(
                            'Consider if {}: might be the correct macro to use here.'.format(newMacro))
                    else:
                        msg.append(
                            'Cannot suggest a new macro because {}: is not a known macro.'.format(newMacro))
                self.warning(MessageId.MISUSED_TEXT, msg)
            return True
        return False

    def checkPnameImpliedContext(self, pname_context):
        """Handle pname: macros not immediately preceded by something like flink:entity or slink:entity.

        Also records pname: mentions of members/parameters for completeness checking in doc blocks.

        Contains call to self.checkPname().
        Called by self.processMatch()
        """
        self.checkPname(pname_context.entity)
        if pname_context.entity in self.pname_mentions and \
                self.pname_mentions[pname_context.entity] is not None:
            # Record this mention,
            # in case we're in the documentation block.
            self.pname_mentions[pname_context.entity].add(self.entity)

    def checkPname(self, pname_context):
        """Check the current match (as a pname: usage) with the given entity as its 'pname context', if possible.

        e.g. slink:foo::pname:bar, pname_context would be 'foo', while self.entity would be 'bar', etc.

        Called by self.processLine(), self.processMatch(), as well as from self.checkPnameImpliedContext().
        """
        if '*' in pname_context:
            # This context has a placeholder, can't verify it.
            return

        entity = self.entity

        context_data = self.checker.findEntity(pname_context)
        members = self.checker.getMemberNames(pname_context)

        if context_data and not members:
            # This is a recognized parent entity that doesn't have detectable member names,
            # skip validation
            # TODO: Annotate parameters of function pointer types with <name>
            # and <param>?
            return
        if not members:
            self.warning(MessageId.UNRECOGNIZED_CONTEXT,
                         'pname context entity was un-recognized {}'.format(pname_context))
            return

        if entity not in members:
            self.warning(MessageId.UNKNOWN_MEMBER, ["Could not find member/param named '{}' in {}".format(entity, pname_context),
                                                    'Known {} mamber/param names are: {}'.format(
                pname_context, ', '.join(members))], group='entity_name')

    def checkIncludeRefPageRelation(self, entity, generated_type):
        """Identify if our current ref page (or lack thereof) is appropriate for an include just recorded.

        Called by self.recordInclude().
        """
        if not self.in_ref_page:
            # Not in a ref page block: This probably means this entity needs a
            # ref-page block added.
            self.handleIncludeMissingRefPage(entity, generated_type)
            return

        if not isinstance(self.current_ref_page, EntityData):
            # This isn't a fully-valid ref page, so can't check the includes any better.
            return

        ref_page_entity = self.current_ref_page.entity
        if ref_page_entity not in self.refpage_includes:
            self.refpage_includes[ref_page_entity] = set()
        expected_ref_page_entity = self.computeExpectedRefPageFromInclude(
            entity)
        self.refpage_includes[ref_page_entity].add((generated_type, entity))

        if ref_page_entity == expected_ref_page_entity:
            # OK, this is a total match.
            pass
        elif self.checker.entity_db.areAliases(expected_ref_page_entity, ref_page_entity):
            # This appears to be a promoted synonym which is OK.
            pass
        else:
            # OK, we are in a ref page block that doesn't match
            self.handleIncludeMismatchRefPage(entity, generated_type)

    def checkRefPage(self):
        """Check if the current line (a refpage tag) meets requirements.

        Called by self.processLine().
        """
        line = self.line

        # Should always be found
        self.match = BRACKETS.match(line)

        data = None
        directory = None
        if self.in_ref_page:
            msg = ["Found reference page markup, but we are already in a refpage block.",
                   "The block before the first message of this type is most likely not closed.", ]
            # Fake-close the previous ref page, if it's trivial to do so.
            if self.getInnermostBlockEntry().block_type == BlockType.REF_PAGE_LIKE:
                msg.append(
                    "Pretending that there was a line with `--` immediately above to close that ref page, for more readable messages.")
                self.processBlockDelimiter(
                    REF_PAGE_LIKE_BLOCK_DELIM, BlockType.REF_PAGE_LIKE)
            else:
                msg.append(
                    "Ref page wasn't the last block opened, so not pretending to auto-close it for more readable messages.")

            self.error(MessageId.REFPAGE_BLOCK, msg)

        attribs = parseRefPageAttribs(line)

        unknown_attribs = set(attribs.keys()).difference(
            VALID_REF_PAGE_ATTRIBS)
        if unknown_attribs:
            self.error(MessageId.REFPAGE_UNKNOWN_ATTRIB,
                       "Found unknown attrib(s) in reference page markup: " + ','.join(unknown_attribs))

        # Required field: refpage='xrValidEntityHere'
        if Attrib.REFPAGE.value in attribs:
            attrib = attribs[Attrib.REFPAGE.value]
            text = attrib.value
            self.entity = text

            context = self.storeMessageContext(
                group='value', match=attrib.match)
            if self.checker.seenRefPage(text):
                self.error(MessageId.REFPAGE_DUPLICATE,
                           ["Found reference page markup when we already saw refpage='{}' elsewhere.".format(
                               text),
                            "This (or the other mention) may be a copy-paste error."],
                           context=context)
            self.checker.addRefPage(text)

            # Skip entity check if it's a spir-v built in
            type = ''
            if Attrib.TYPE.value in attribs:
                type = attribs[Attrib.TYPE.value].value

            if type != 'builtins' and type != 'spirv':
                data = self.checker.findEntity(text)
                self.current_ref_page = data
                if data:
                    # OK, this is a known entity that we're seeing a refpage for.
                    directory = data.directory
                else:
                    # TODO suggest fixes here if applicable
                    self.error(MessageId.REFPAGE_NAME,
                               [ "Found reference page markup, but refpage='{}' type='{}' does not refer to a recognized entity".format(
                                   text, type),
                                 'If this is intentional, add the entity to EXTRA_DEFINES or EXTRA_REFPAGES in check_spec_links.py.' ],
                               context=context)

        else:
            self.error(MessageId.REFPAGE_TAG,
                       "Found apparent reference page markup, but missing refpage='...'",
                       group=None)

        # Required field: desc='preferably non-empty'
        if Attrib.DESC.value in attribs:
            attrib = attribs[Attrib.DESC.value]
            text = attrib.value
            if not text:
                context = self.storeMessageContext(
                    group=None, match=attrib.match)
                self.warning(MessageId.REFPAGE_MISSING_DESC,
                             "Found reference page markup, but desc='' is empty",
                             context=context)
        else:
            self.error(MessageId.REFPAGE_TAG,
                       "Found apparent reference page markup, but missing desc='...'",
                       group=None)

        # Required field: type='protos' for example
        # (used by genRef.py to compute the macro to use)
        if Attrib.TYPE.value in attribs:
            attrib = attribs[Attrib.TYPE.value]
            text = attrib.value
            if directory and not text == directory:
                context = self.storeMessageContext(
                    group='value', match=attrib.match)
                self.error(MessageId.REFPAGE_TYPE,
                           "Found reference page markup, but type='{}' is not the expected value '{}'".format(
                               text, directory),
                           context=context)
        else:
            self.error(MessageId.REFPAGE_TAG,
                       "Found apparent reference page markup, but missing type='...'",
                       group=None)

        # Optional field: alias='spaceDelimited validEntities'
        # Currently does nothing. Could modify checkRefPageXrefs to also
        # check alias= attribute value
        # if Attrib.ALIAS.value in attribs:
        #    # This field is optional
        #    self.checkRefPageXrefs(attribs[Attrib.XREFS.value])

        # Optional field: xrefs='spaceDelimited validEntities'
        if Attrib.XREFS.value in attribs:
            # This field is optional
            self.checkRefPageXrefs(attribs[Attrib.XREFS.value])
        self.prev_line_ref_page_tag = self.storeMessageContext()

    def checkRefPageXrefs(self, xrefs_attrib):
        """Check all cross-refs indicated in an xrefs attribute for a ref page.

        Called by self.checkRefPage().

        Argument:
        xrefs_attrib -- A match of REF_PAGE_ATTRIB where the group 'key' is 'xrefs'.
        """
        text = xrefs_attrib.value
        context = self.storeMessageContext(
            group='value', match=xrefs_attrib.match)

        def splitRefs(s):
            """Split the string on whitespace, into individual references."""
            return s.split()  # [x for x in s.split() if x]

        def remakeRefs(refs):
            """Re-create a xrefs string from something list-shaped."""
            return ' '.join(refs)

        refs = splitRefs(text)

        # Pre-checking if messages are enabled, so that we can correctly determine
        # the current string following any auto-fixes:
        # the fixes for messages directly in this method would interact,
        # and thus must be in the order specified here.

        if self.messageEnabled(MessageId.REFPAGE_XREFS_COMMA) and ',' in text:
            old_text = text
            # Re-split after replacing commas.
            refs = splitRefs(text.replace(',', ' '))
            # Re-create the space-delimited text.
            text = remakeRefs(refs)
            self.error(MessageId.REFPAGE_XREFS_COMMA,
                       "Found reference page markup, with an unexpected comma in the (space-delimited) xrefs attribute",
                       context=context,
                       replacement=text,
                       fix=(old_text, text))

        # We could conditionally perform this creation, but the code complexity would increase substantially,
        # for presumably minimal runtime improvement.
        unique_refs = OrderedDict.fromkeys(refs)
        if self.messageEnabled(MessageId.REFPAGE_XREF_DUPE) and len(unique_refs) != len(refs):
            # TODO is it safe to auto-fix here?
            old_text = text
            text = remakeRefs(unique_refs.keys())
            self.warning(MessageId.REFPAGE_XREF_DUPE,
                         ["Reference page for {} contains at least one duplicate in its cross-references.".format(
                             self.entity),
                             "Look carefully to see if this is a copy and paste error and should be changed to a different but related entity:",
                             "auto-fix simply removes the duplicate."],
                         context=context,
                         replacement=text,
                         fix=(old_text, text))

        if self.messageEnabled(MessageId.REFPAGE_SELF_XREF) and self.entity and self.entity in unique_refs:
            # Not modifying unique_refs here because that would accidentally affect the whitespace auto-fix.
            new_text = remakeRefs(
                [x for x in unique_refs.keys() if x != self.entity])

            # DON'T AUTOFIX HERE because these are likely copy-paste between related entities:
            # e.g. a Create function and the associated CreateInfo struct.
            self.warning(MessageId.REFPAGE_SELF_XREF,
                         ["Reference page for {} included itself in its cross-references.".format(self.entity),
                          "This is typically a copy and paste error, and the dupe should likely be changed to a different but related entity.",
                          "Not auto-fixing for this reason."],
                         context=context,
                         replacement=new_text,)

        # We didn't have another reason to replace the whole attribute value,
        # so let's make sure it doesn't have any extra spaces
        if self.messageEnabled(MessageId.REFPAGE_WHITESPACE) and xrefs_attrib.value == text:
            old_text = text
            text = remakeRefs(unique_refs.keys())
            if old_text != text:
                self.warning(MessageId.REFPAGE_WHITESPACE,
                             ["Cross-references for reference page for {} had non-minimal whitespace,".format(self.entity),
                              "and no other enabled message has re-constructed this value already."],
                             context=context,
                             replacement=text,
                             fix=(old_text, text))

        for entity in unique_refs.keys():
            self.checkRefPageXref(entity, context)

    def checkRefPageXref(self, referenced_entity, line_context):
        """Check a single cross-reference entry for a refpage.

        Called by self.checkRefPageXrefs().

        Arguments:
        referenced_entity -- The individual entity under consideration from the xrefs='...' string.
        line_context -- A MessageContext referring to the entire line.
        """
        data = self.checker.findEntity(referenced_entity)
        if data:
            # This is OK
            return
        context = line_context
        match = re.search(r'\b{}\b'.format(referenced_entity), self.line)
        if match:
            context = self.storeMessageContext(
                group=None, match=match)
        msg = ["Found reference page markup, with an unrecognized entity listed: {}".format(
            referenced_entity)]

        see_also = None
        dataArray = self.checker.findEntityCaseInsensitive(
            referenced_entity)

        if dataArray:
            # We might have found the goof...

            if len(dataArray) == 1:
                # Yep, found the goof - incorrect entity capitalization
                data = dataArray[0]
                new_entity = data.entity
                self.error(MessageId.REFPAGE_XREFS, msg + [
                    'Apparently matching entity in category {} found by searching case-insensitively.'.format(
                        data.category),
                    AUTO_FIX_STRING],
                    replacement=new_entity,
                    fix=(referenced_entity, new_entity),
                    context=context)
                return

            # Ugh, more than one resolution
            msg.append(
                'More than one apparent match found by searching case-insensitively, cannot auto-fix.')
            see_also = dataArray[:]
        else:
            # Probably not just a typo
            msg.append(
                'If this is intentional, add the entity to EXTRA_DEFINES or EXTRA_REFPAGES in check_spec_links.py.')

        # Multiple or no resolutions found
        self.error(MessageId.REFPAGE_XREFS,
                   msg,
                   see_also=see_also,
                   context=context)

    ###
    # Message-related methods.
    ###

    def warning(self, message_id, messageLines, context=None, group=None,
                replacement=None, fix=None, see_also=None, frame=None):
        """Log a warning for the file, if the message ID is enabled.

        Wrapper around self.diag() that automatically sets severity as well as frame.

        Arguments:
        message_id -- A MessageId value.
        messageLines -- A string or list of strings containing a human-readable error description.

        Optional, named arguments:
        context -- A MessageContext. If None, will be constructed from self.match and group.
        group -- The name of the regex group in self.match that contains the problem. Only used if context is None.
          If needed and is None, self.group is used instead.
        replacement -- The string, if any, that should be suggested as a replacement for the group in question.
          Does not create an auto-fix: sometimes we want to show a possible fix but aren't confident enough
          (or can't easily phrase a regex) to do it automatically.
        fix -- A (old text, new text) pair if this error is auto-fixable safely.
        see_also -- An optional array of other MessageContext locations relevant to this message.
        frame -- The 'inspect' stack frame corresponding to the location that raised this message.
          If None, will assume it is the direct caller of self.warning().
        """
        if not frame:
            frame = currentframe().f_back
        self.diag(MessageType.WARNING, message_id, messageLines, group=group,
                  replacement=replacement, context=context, fix=fix, see_also=see_also, frame=frame)

    def error(self, message_id, messageLines, group=None, replacement=None,
              context=None, fix=None, see_also=None, frame=None):
        """Log an error for the file, if the message ID is enabled.

        Wrapper around self.diag() that automatically sets severity as well as frame.

        Arguments:
        message_id -- A MessageId value.
        messageLines -- A string or list of strings containing a human-readable error description.

        Optional, named arguments:
        context -- A MessageContext. If None, will be constructed from self.match and group.
        group -- The name of the regex group in self.match that contains the problem. Only used if context is None.
          If needed and is None, self.group is used instead.
        replacement -- The string, if any, that should be suggested as a replacement for the group in question.
          Does not create an auto-fix: sometimes we want to show a possible fix but aren't confident enough
          (or can't easily phrase a regex) to do it automatically.
        fix -- A (old text, new text) pair if this error is auto-fixable safely.
        see_also -- An optional array of other MessageContext locations relevant to this message.
        frame -- The 'inspect' stack frame corresponding to the location that raised this message.
          If None, will assume it is the direct caller of self.error().
        """
        if not frame:
            frame = currentframe().f_back
        self.diag(MessageType.ERROR, message_id, messageLines, group=group,
                  replacement=replacement, context=context, fix=fix, see_also=see_also, frame=frame)

    def diag(self, severity, message_id, messageLines, context=None, group=None,
             replacement=None, fix=None, see_also=None, frame=None):
        """Log a diagnostic for the file, if the message ID is enabled.

        Also records the auto-fix, if applicable.

        Arguments:
        severity -- A MessageType value.
        message_id -- A MessageId value.
        messageLines -- A string or list of strings containing a human-readable error description.

        Optional, named arguments:
        context -- A MessageContext. If None, will be constructed from self.match and group.
        group -- The name of the regex group in self.match that contains the problem. Only used if context is None.
          If needed and is None, self.group is used instead.
        replacement -- The string, if any, that should be suggested as a replacement for the group in question.
          Does not create an auto-fix: sometimes we want to show a possible fix but aren't confident enough
          (or can't easily phrase a regex) to do it automatically.
        fix -- A (old text, new text) pair if this error is auto-fixable safely.
        see_also -- An optional array of other MessageContext locations relevant to this message.
        frame -- The 'inspect' stack frame corresponding to the location that raised this message.
          If None, will assume it is the direct caller of self.diag().
        """
        if not self.messageEnabled(message_id):
            self.logger.debug(
                'Discarding a %s message because it is disabled.', message_id)
            return

        if isinstance(messageLines, str):
            messageLines = [messageLines]

        self.logger.info('Recording a %s message: %s',
                         message_id, ' '.join(messageLines))

        # Ensure all auto-fixes are marked as such.
        if fix is not None and AUTO_FIX_STRING not in messageLines:
            messageLines.append(AUTO_FIX_STRING)

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

    def messageEnabled(self, message_id):
        """Return true if the given message ID is enabled."""
        return message_id in self.enabled_messages

    ###
    # Accessors for externally-interesting information

    def numDiagnostics(self):
        """Count the total number of diagnostics (errors or warnings) for this file."""
        return len(self.messages)

    def numErrors(self):
        """Count the total number of errors for this file."""
        return self.numMessagesOfType(MessageType.ERROR)

    def numMessagesOfType(self, message_type):
        """Count the number of messages of a particular type (severity)."""
        return len(
            [msg for msg in self.messages if msg.message_type == message_type])

    def hasFixes(self):
        """Return True if any messages included auto-fix patterns."""
        return len(self.fixes) > 0

    ###
    # Assorted internal methods.
    def printMessageCounts(self):
        """Print a simple count of each MessageType of diagnostics."""
        for message_type in [MessageType.ERROR, MessageType.WARNING]:
            count = self.numMessagesOfType(message_type)
            if count > 0:
                print('{num} {mtype}{s} generated.'.format(
                    num=count, mtype=message_type, s=_s_suffix(count)))

    def dumpInternals(self):
        """Dump internal variables to screen, for debugging."""
        print('self.lineNum: ', self.lineNum)
        print('self.line:', self.line)
        print('self.prev_line_ref_page_tag: ', self.prev_line_ref_page_tag)
        print('self.current_ref_page:', self.current_ref_page)

    def getMissingValiditySuppressions(self):
        """Return an enumerable of entity names that we shouldn't warn about missing validity.

        May override.
        """
        return []

    def recordInclude(self, include_dict, generated_type=None):
        """Store the current line as being the location of an include directive or equivalent.

        Reports duplicate include errors, as well as include/ref-page mismatch or missing ref-page,
        by calling self.checkIncludeRefPageRelation() for "actual" includes (where generated_type is None).

        Arguments:
        include_dict -- The include dictionary to update: one of self.apiIncludes or self.validityIncludes.
        generated_type -- The type of include (e.g. 'api', 'valid', etc). By default, extracted from self.match.
        """
        entity = self.match.group('entity_name')
        if generated_type is None:
            generated_type = self.match.group('generated_type')

            # Only checking the ref page relation if it's retrieved from regex.
            # Otherwise it might be a manual anchor recorded as an include,
            # etc.
            self.checkIncludeRefPageRelation(entity, generated_type)

        if entity in include_dict:
            self.error(MessageId.DUPLICATE_INCLUDE,
                       "Included {} docs for {} when they were already included.".format(generated_type,
                                                                                         entity), see_also=include_dict[entity])
            include_dict[entity].append(self.storeMessageContext())
        else:
            include_dict[entity] = [self.storeMessageContext()]

    def getInnermostBlockEntry(self):
        """Get the BlockEntry for the top block delim on our stack."""
        if not self.block_stack:
            return None
        return self.block_stack[-1]

    def getInnermostBlockDelimiter(self):
        """Get the delimiter for the top block on our stack."""
        top = self.getInnermostBlockEntry()
        if not top:
            return None
        return top.delimiter

    def pushBlock(self, block_type, refpage=None, context=None, delimiter=None):
        """Push a new entry on the block stack."""
        if not delimiter:
            self.logger.info("pushBlock: not given delimiter")
            delimiter = self.line
        if not context:
            context = self.storeMessageContext()

        old_top_delim = self.getInnermostBlockDelimiter()

        self.block_stack.append(BlockEntry(
            delimiter=delimiter,
            context=context,
            refpage=refpage,
            block_type=block_type))

        location = self.getBriefLocation(context)
        self.logger.info(
            "pushBlock: %s: Pushed %s delimiter %s, previous top was %s, now %d elements on the stack",
            location, block_type.value, delimiter, old_top_delim, len(self.block_stack))

        self.dumpBlockStack()

    def popBlock(self):
        """Pop and return the top entry from the block stack."""
        old_top = self.block_stack.pop()
        location = self.getBriefLocation(old_top.context)
        self.logger.info(
            "popBlock: %s: popping %s delimiter %s, now %d elements on the stack",
            location, old_top.block_type.value, old_top.delimiter, len(self.block_stack))

        self.dumpBlockStack()

        return old_top

    def dumpBlockStack(self):
        self.logger.debug('Block stack, top first:')
        for distFromTop, x in enumerate(reversed(self.block_stack)):
            self.logger.debug(' - block_stack[%d]: Line %d: "%s" refpage=%s',
                              -1 - distFromTop,
                              x.context.lineNum, x.delimiter, x.refpage)

    def getBriefLocation(self, context):
        """Format a context briefly - omitting the filename if it has newlines in it."""
        if '\n' in context.filename:
            return 'input string line {}'.format(context.lineNum)
        return '{}:{}'.format(
            context.filename, context.lineNum)

    ###
    # Handlers for a variety of diagnostic-meriting conditions
    #
    # Split out for clarity and for allowing fine-grained override on a per-project basis.
    ###

    def handleIncludeMissingRefPage(self, entity, generated_type):
        """Report a message about an include outside of a ref-page block."""
        msg = ["Found {} include for {} outside of a reference page block.".format(generated_type, entity),
               "This is probably a missing reference page block."]
        refpage = self.computeExpectedRefPageFromInclude(entity)
        data = self.checker.findEntity(refpage)
        if data:
            msg.append('Expected ref page block might start like:')
            msg.append(self.makeRefPageTag(refpage, data=data))
        else:
            msg.append(
                "But, expected ref page entity name {} isn't recognized...".format(refpage))
        self.warning(MessageId.REFPAGE_MISSING, msg)

    def handleIncludeMismatchRefPage(self, entity, generated_type):
        """Report a message about an include not matching its containing ref-page block."""
        self.warning(MessageId.REFPAGE_MISMATCH, "Found {} include for {}, inside the reference page block of {}".format(
            generated_type, entity, self.current_ref_page.entity))

    def handleWrongMacro(self, msg, data):
        """Report an appropriate message when we found that the macro used is incorrect.

        May be overridden depending on each API's behavior regarding macro misuse:
        e.g. in some cases, it may be considered a MessageId.LEGACY warning rather than
        a MessageId.WRONG_MACRO or MessageId.EXTENSION.
        """
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
            message_type = MessageType.ERROR
        msg.append(AUTO_FIX_STRING)
        self.diag(message_type, message_id, msg,
                  group=group, replacement=self.makeMacroMarkup(data=data), fix=self.makeFix(data=data))

    def handleExpectedRefpageBlock(self):
        """Handle expecting to see -- to start a refpage block, but not seeing that at all."""
        self.error(MessageId.REFPAGE_BLOCK,
                   ["Expected, but did not find, a line containing only -- following a reference page tag,",
                    "Pretending to insert one, for more readable messages."],
                   see_also=[self.prev_line_ref_page_tag])
        # Fake "in ref page" regardless, to avoid spurious extra errors.
        self.processBlockDelimiter('--', BlockType.REF_PAGE_LIKE,
                                   context=self.prev_line_ref_page_tag)

    ###
    # Construct related values (typically named tuples) based on object state and supplied arguments.
    #
    # Results are typically supplied to another method call.
    ###

    def storeMessageContext(self, group=None, match=None):
        """Create message context from corresponding instance variables.

        Arguments:
        group -- The regex group name, if any, identifying the part of the match to highlight.
        match -- The regex match. If None, will use self.match.
        """
        if match is None:
            match = self.match
        return MessageContext(filename=self.filename,
                              lineNum=self.lineNum,
                              line=self.line,
                              match=match,
                              group=group)

    def makeFix(self, newMacro=None, newEntity=None, data=None):
        """Construct a fix pair for replacing the old macro:entity with new.

        Wrapper around self.makeSearch() and self.makeMacroMarkup().
        """
        return (self.makeSearch(), self.makeMacroMarkup(
            newMacro, newEntity, data))

    def makeSearch(self):
        """Construct the string self.macro:self.entity, for use in the old text part of a fix pair."""
        return '{}:{}'.format(self.macro, self.entity)

    def makeMacroMarkup(self, newMacro=None, newEntity=None, data=None):
        """Construct appropriate markup for referring to an entity.

        Typically constructs macro:entity, but can construct `<<EXTENSION_NAME>>` if the supplied
        entity is identified as an extension.

        Arguments:
        newMacro -- The macro to use. Defaults to data.macro (if available), otherwise self.macro.
        newEntity -- The entity to use. Defaults to data.entity (if available), otherwise self.entity.
        data -- An EntityData value corresponding to this entity. If not provided, will be looked up by newEntity.
        """
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
        """Create a correctly-formatted link to an extension.

        Result takes the form `<<EXTENSION_NAME>>`.

        Argument:
        newEntity -- The extension name to link to. Defaults to self.entity.
        """
        if not newEntity:
            newEntity = self.entity
        return '`<<{}>>`'.format(newEntity)

    def computeExpectedRefPageFromInclude(self, entity):
        """Compute the expected ref page entity based on an include entity name."""
        # No-op in general.
        return entity

    def makeRefPageTag(self, entity, data=None,
                       ref_type=None, desc='', xrefs=None):
        """Construct a ref page tag string from attribute values."""
        if ref_type is None and data is not None:
            ref_type = data.directory
        if ref_type is None:
            ref_type = "????"
        return "[open,refpage='{}',type='{}',desc='{}',xrefs='{}']".format(
            entity, ref_type, desc, ' '.join(xrefs or []))
