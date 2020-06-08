#!/usr/bin/python3
#
# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>
#
# Purpose:      This file contains tests for check_spec_links.py

import pytest

from check_spec_links import MessageId, makeMacroChecker
from spec_tools.console_printer import ConsolePrinter
from spec_tools.macro_checker_file import shouldEntityBeText

# API-specific constants
PROTO = 'vkCreateInstance'
STRUCT = 'VkInstanceCreateInfo'
EXT = 'VK_KHR_display'


class CheckerWrapper(object):
    """Little wrapper object for a MacroChecker.

    Intended for use in making test assertions shorter and easier to read."""

    def __init__(self, capsys):
        self.ckr = makeMacroChecker(set())
        self.capsys = capsys

    def enabled(self, enabled_messages):
        """Updates the checker's enable message type set, from an iterable."""
        self.ckr.enabled_messages = set(enabled_messages)
        return self

    def check(self, string):
        """Checks a string (as if it were a file), outputs the results to the console, then returns the MacroCheckerFile."""

        # Flush the captured output.
        _ = self.capsys.readouterr()

        # Process
        f = self.ckr.processString(string + '\n')

        # Dump messages
        ConsolePrinter().output(f)
        return f


@pytest.fixture
def ckr(capsys):
    """Fixture - add an arg named ckr to your test function to automatically get one passed to you."""
    return CheckerWrapper(capsys)


def msgReplacement(file_checker, which=0):
    """Return the replacement text associated with the specified message."""
    assert(len(file_checker.messages) > which)
    msg = file_checker.messages[which]
    from pprint import pprint
    pprint(msg.script_location)
    pprint(msg.replacement)
    pprint(msg.fix)
    return msg.replacement


def loneMsgReplacement(file_checker):
    """Assert there's only one message in a file checker, and return the replacement text associated with it."""
    assert(len(file_checker.messages) == 1)
    return msgReplacement(file_checker)


def message(file_checker, which=0):
    """Return a string of the message lines associated with the message of a file checker."""
    assert(len(file_checker.messages) > which)
    return "\n".join(file_checker.messages[which].message)


def allMessages(file_checker):
    """Return a list of strings, each being the combination of the message lines of a message from a file checker."""
    return ['\n'.join(msg.message) for msg in file_checker.messages]


def test_missing_macro(ckr):
    """Verify correct functioning of MessageId.MISSING_MACRO."""
    ckr.enabled([MessageId.MISSING_MACRO])

    # This should have a missing macro warning
    assert(ckr.check('with %s by' % PROTO).numDiagnostics() == 1)

    # These 3 should not have a missing macro warning because of their context
    # (in a link)
    assert(not ckr.check('<<%s' % PROTO).messages)
    # These 2 are simulating links that broke over lines
    assert(not ckr.check('%s>>' % PROTO).messages)
    assert(not ckr.check(
        '%s asdf>> table' % PROTO).messages)


def test_entity_detection(ckr):
    ckr.enabled([MessageId.BAD_ENTITY])
    # Should complain about BAD_ENTITY
    assert(ckr.check('flink:abcd').numDiagnostics() == 1)

    # Should just give BAD_ENTITY (an error), not MISSING_TEXT (a warning).
    # Verifying that wrapping in asterisks (for formatting) doesn't get picked up as
    # an asterisk in the entity name (a placeholder).
    ckr.enabled(
        [MessageId.MISSING_TEXT, MessageId.BAD_ENTITY])
    assert(ckr.check('*flink:abcd*').numErrors() == 1)


def test_wrong_macro(ckr):
    ckr.enabled([MessageId.WRONG_MACRO])
    # Should error - this ought to be code:uint32_t
    assert(ckr.check('basetype:uint32_t').numErrors() == 1)

    # This shouldn't error
    assert(ckr.check('code:uint32_t').numErrors() == 0)


def test_should_entity_be_text():
    # These 5 are all examples of patterns that would merit usage of a ptext/etext/etc
    # macro, for various reasons:

    # has variable in subscript
    assert(shouldEntityBeText('pBuffers[i]', '[i]'))
    assert(shouldEntityBeText('API_ENUM_[X]', '[X]'))

    # has asterisk
    assert(shouldEntityBeText('maxPerStage*', None))

    # double-underscores make italicized placeholders
    # (triple are double-underscores delimited by underscores...)
    assert(shouldEntityBeText('API_ENUM[__x__]', '[__x__]'))
    assert(shouldEntityBeText('API_ENUM___i___EXT', None))

    # This shouldn't be a *text: macro because it only has single underscores
    assert(False == shouldEntityBeText('API_ENUM_i_EXT', None))


def test_misused_text(ckr):
    # Tests the same patterns as test_should_entity_be_text(),
    # but in a whole checker
    ckr.enabled([MessageId.MISUSED_TEXT])

    assert(ckr.check('etext:API_ENUM_').numDiagnostics() == 0)
    assert(ckr.check('etext:API_ENUM_[X]').numDiagnostics() == 0)
    assert(ckr.check('etext:API_ENUM[i]').numDiagnostics() == 0)
    assert(ckr.check('etext:API_ENUM[__x__]').numDiagnostics() == 0)

    # Should be OK, since __i__ is a placeholder here
    assert(ckr.check('etext:API_ENUM___i___EXT').numDiagnostics() == 0)

    # This shouldn't be a *text: macro because it only has single underscores
    assert(ckr.check('API_ENUM_i_EXT').numDiagnostics() == 0)


def test_extension(ckr):
    ckr.enabled(set(MessageId))
    # Check formatting of extension names:
    # the following is the canonical way to refer to an extension
    # (link wrapped in backticks)
    expected_replacement = '`<<%s>>`' % EXT

    # Extension name mentioned without any markup, should be added
    assert(loneMsgReplacement(ckr.check('asdf %s asdf' % EXT))
           == expected_replacement)

    # Extension name mentioned without any markup and wrong case,
    # should be added and have case fixed
    assert(loneMsgReplacement(ckr.check('asdf %s asdf' % EXT.upper()))
           == expected_replacement)

    # Extension name using wrong/old macro: ename isn't for extensions.
    assert(loneMsgReplacement(ckr.check('asdf ename:%s asdf' % EXT))
           == expected_replacement)

    # Extension name using wrong macro: elink isn't for extensions.
    assert(loneMsgReplacement(ckr.check('asdf elink:%s asdf' % EXT))
           == expected_replacement)

    # Extension name using wrong macro and wrong case: should have markup and
    # case fixed
    assert(loneMsgReplacement(ckr.check('asdf elink:%s asdf' % EXT.upper()))
           == expected_replacement)

    # This shouldn't cause errors because this is how we want it to look.
    assert(not ckr.check('asdf `<<%s>>` asdf' % EXT).messages)

    # This doesn't (shouldn't?) cause errors because just backticks on their own
    # "escape" names from the "missing markup" tests.
    assert(not ckr.check('asdf `%s` asdf' % EXT).messages)

    # TODO can we auto-correct this to add the backticks?
    # Doesn't error now, but would be nice if it did...
    assert(not ckr.check('asdf <<%s>> asdf' % EXT).messages)


def test_refpage_tag(ckr):
    ckr.enabled([MessageId.REFPAGE_TAG])

    # Should error: missing refpage='' field
    assert(ckr.check("[open,desc='',type='',xrefs='']").numErrors() == 1)
    # Should error: missing desc='' field
    assert(ckr.check("[open,refpage='',type='',xrefs='']").numErrors() == 1)
    # Should error: missing type='' field
    assert(ckr.check("[open,refpage='',desc='',xrefs='']").numErrors() == 1)

    # Should not error: missing xrefs field is optional
    assert(not ckr.check("[open,refpage='',desc='',type='']").messages)

    # Should error, due to missing refpage, but not crash due to message printing (note the unicode smart quote)
    assert(ckr.check("[open,desc='',type='',xrefs=’']").numDiagnostics() == 1)


def test_refpage_name(ckr):
    ckr.enabled([MessageId.REFPAGE_NAME])
    # Should not error: actually exists.
    assert(ckr.check(
        "[open,refpage='%s',desc='',type='']" % PROTO).numDiagnostics() == 0)

    # Should error: does not exist.
    assert(
        ckr.check("[open,refpage='bogus',desc='',type='']").numDiagnostics() == 1)


def test_refpage_missing_desc(ckr):
    ckr.enabled([MessageId.REFPAGE_MISSING_DESC])
    # Should not warn: non-empty description actually exists.
    assert(ckr.check(
        "[open,refpage='',desc='non-empty description',type='']").numDiagnostics() == 0)

    # Should warn: desc field is empty.
    assert(
        ckr.check("[open,refpage='',desc='',type='']").numDiagnostics() == 1)


def test_refpage_type(ckr):
    ckr.enabled([MessageId.REFPAGE_TYPE])
    # Should not error: this is of type 'protos'.
    assert(not ckr.check(
        "[open,refpage='%s',desc='',type='protos']" % PROTO).messages)

    # Should error: this is of type 'protos', not 'structs'.
    assert(
        ckr.check("[open,refpage='%s',desc='',type='structs']" % PROTO).messages)


def test_refpage_xrefs(ckr):
    ckr.enabled([MessageId.REFPAGE_XREFS])
    # Should not error: this is a valid entity to have an xref to.
    assert(not ckr.check(
        "[open,refpage='',desc='',type='protos',xrefs='%s']" % STRUCT).messages)

    # case difference:
    # should error but offer a replacement.
    assert(loneMsgReplacement(ckr.check("[open,refpage='',xrefs='%s']" % STRUCT.lower()))
           == STRUCT)

    # Should error: not a valid entity.
    assert(ckr.check(
        "[open,refpage='',desc='',type='protos',xrefs='bogus']").numDiagnostics() == 1)


def test_refpage_xrefs_comma(ckr):
    ckr.enabled([MessageId.REFPAGE_XREFS_COMMA])
    # Should not error: no commas in the xrefs field
    assert(not ckr.check(
        "[open,refpage='',xrefs='abc']").messages)

    # Should error: commas shouldn't be there since it's space-delimited.
    assert(loneMsgReplacement(
        ckr.check("[open,refpage='',xrefs='abc,']")) == 'abc')

    # All should correct to the same thing.
    equivalent_tags_with_commas = [
        "[open,refpage='',xrefs='abc, 123']",
        "[open,refpage='',xrefs='abc,123']",
        "[open,refpage='',xrefs='abc , 123']"]
    for has_comma in equivalent_tags_with_commas:
        assert(loneMsgReplacement(ckr.check(has_comma)) == 'abc 123')


def test_refpage_block(ckr):
    """Tests of the REFPAGE_BLOCK message."""
    ckr.enabled([MessageId.REFPAGE_BLOCK])
    # Should not error: have the tag, an open, and a close
    assert(not ckr.check(
        """[open,]
        --
        bla
        --""").messages)
    assert(not ckr.check(
        """[open,refpage='abc']
        --
        bla
        --

        [open,refpage='123']
        --
        bla2
        --""").messages)

    # Should have 1 error: file ends immediately after tag
    assert(ckr.check(
        "[open,]").numDiagnostics() == 1)

    # Should have 1 error: line after tag isn't --
    assert(ckr.check(
        """[open,]
        bla
        --""").numDiagnostics() == 1)
    # Checking precedence of checks: this should have 1 error because line after tag isn't --
    # (but it is something that causes a line to be handled differently)
    assert(ckr.check(
        """[open,]
        == Heading
        --""").numDiagnostics() == 1)
    assert(ckr.check(
        """[open,]
        ----
        this is in a code block
        ----
        --""").numDiagnostics() == 1)

    # Should have 1 error: tag inside refpage.
    tag_inside = """[open,]
        --
        bla
        [open,]
        --"""
    assert(ckr.check(tag_inside).numDiagnostics() == 1)
    assert("already in a refpage block" in
           message(ckr.check(tag_inside)))


def test_refpage_missing(ckr):
    """Test the REFPAGE_MISSING message."""
    ckr.enabled([MessageId.REFPAGE_MISSING])
    # Should not error: have the tag, an open, and the include
    assert(not ckr.check(
        """[open,refpage='%s']
        --
        include::{generated}/api/protos/%s.txt[]""" % (PROTO, PROTO)).messages)
    assert(not ckr.check(
        """[open,refpage='%s']
        --
        include::{generated}/validity/protos/%s.txt[]""" % (PROTO, PROTO)).messages)

    # Should not error: manual anchors shouldn't trigger this.
    assert(not ckr.check("[[%s]]" % PROTO).messages)

    # Should have 1 error: file ends immediately after include
    assert(ckr.check(
        "include::{generated}/api/protos/%s.txt[]" % PROTO).numDiagnostics() == 1)
    assert(ckr.check(
        "include::{generated}/validity/protos/%s.txt[]" % PROTO).numDiagnostics() == 1)

    # Should have 1 error: include is before the refpage open
    assert(ckr.check(
        """include::{generated}/api/protos/%s.txt[]
        [open,refpage='%s']
        --""" % (PROTO, PROTO)).numDiagnostics() == 1)
    assert(ckr.check(
        """include::{generated}/validity/protos/%s.txt[]
        [open,refpage='%s']
        --""" % (PROTO, PROTO)).numDiagnostics() == 1)


def test_refpage_mismatch(ckr):
    """Test the REFPAGE_MISMATCH message."""
    ckr.enabled([MessageId.REFPAGE_MISMATCH])
    # Should not error: have the tag, an open, and a matching include
    assert(not ckr.check(
        """[open,refpage='%s']
        --
        include::{generated}/api/protos/%s.txt[]""" % (PROTO, PROTO)).messages)
    assert(not ckr.check(
        """[open,refpage='%s']
        --
        include::{generated}/validity/protos/%s.txt[]""" % (PROTO, PROTO)).messages)

    # Should error: have the tag, an open, and a mis-matching include
    assert(ckr.check(
        """[open,refpage='%s']
        --
        include::{generated}/api/structs/%s.txt[]""" % (PROTO, STRUCT)).numDiagnostics() == 1)
    assert(ckr.check(
        """[open,refpage='%s']
        --
        include::{generated}/validity/structs/%s.txt[]""" % (PROTO, STRUCT)).numDiagnostics() == 1)


def test_refpage_unknown_attrib(ckr):
    """Check the REFPAGE_UNKNOWN_ATTRIB message."""
    ckr.enabled([MessageId.REFPAGE_UNKNOWN_ATTRIB])
    # Should not error: these are known attribute names
    assert(not ckr.check(
        "[open,refpage='',desc='',type='',xrefs='']").messages)

    # Should error: xref isn't an attribute name.
    assert(ckr.check(
        "[open,xref='']").numDiagnostics() == 1)


def test_refpage_self_xref(ckr):
    """Check the REFPAGE_SELF_XREF message."""
    ckr.enabled([MessageId.REFPAGE_SELF_XREF])
    # Should not error: not self-referencing
    assert(not ckr.check(
        "[open,refpage='abc',xrefs='']").messages)
    assert(not ckr.check(
        "[open,refpage='abc',xrefs='123']").messages)

    # Should error: self-referencing isn't an attribute name.
    assert(loneMsgReplacement(
        ckr.check("[open,refpage='abc',xrefs='abc']")) == '')
    assert(loneMsgReplacement(
        ckr.check("[open,refpage='abc',xrefs='abc 123']")) == '123')
    assert(loneMsgReplacement(
        ckr.check("[open,refpage='abc',xrefs='123 abc']")) == '123')


def test_refpage_xref_dupe(ckr):
    """Check the REFPAGE_XREF_DUPE message."""
    ckr.enabled([MessageId.REFPAGE_XREF_DUPE])
    # Should not error: no dupes
    assert(not ckr.check("[open,xrefs='']").messages)
    assert(not ckr.check("[open,xrefs='123']").messages)
    assert(not ckr.check("[open,xrefs='abc 123']").messages)

    # Should error: one dupe.
    assert(loneMsgReplacement(
        ckr.check("[open,xrefs='abc abc']")) == 'abc')
    assert(loneMsgReplacement(
        ckr.check("[open,xrefs='abc   abc']")) == 'abc')
    assert(loneMsgReplacement(
        ckr.check("[open,xrefs='abc abc abc']")) == 'abc')
    assert(loneMsgReplacement(
        ckr.check("[open,xrefs='abc 123 abc']")) == 'abc 123')
    assert(loneMsgReplacement(
        ckr.check("[open,xrefs='123 abc abc']")) == '123 abc')


def test_REFPAGE_WHITESPACE(ckr):
    """Check the REFPAGE_WHITESPACE message."""
    ckr.enabled([MessageId.REFPAGE_WHITESPACE])
    # Should not error: no extra whitespace
    assert(not ckr.check("[open,xrefs='']").messages)
    assert(not ckr.check("[open,xrefs='123']").messages)
    assert(not ckr.check("[open,xrefs='abc 123']").messages)

    # Should error: some extraneous whitespace.
    assert(loneMsgReplacement(
        ckr.check("[open,xrefs='   \t   ']")) == '')
    assert(loneMsgReplacement(
        ckr.check("[open,xrefs='  abc   123  ']")) == 'abc 123')
    assert(loneMsgReplacement(
        ckr.check("[open,xrefs='  abc\t123    xyz  ']")) == 'abc 123 xyz')

    # Should *NOT* remove self-reference, just extra whitespace
    assert(loneMsgReplacement(
        ckr.check("[open,refpage='abc',xrefs='  abc   123  ']")) == 'abc 123')

    # Even if we turn on the self-reference warning
    ckr.enabled([MessageId.REFPAGE_WHITESPACE, MessageId.REFPAGE_SELF_XREF])
    assert(msgReplacement(
        ckr.check("[open,refpage='abc',xrefs='  abc   123  ']"), 1) == 'abc 123')


def test_REFPAGE_DUPLICATE(ckr):
    """Check the REFPAGE_DUPLICATE message."""
    ckr.enabled([MessageId.REFPAGE_DUPLICATE])
    # Should not error: no duplicate refpages.
    assert(not ckr.check("[open,refpage='abc']").messages)
    assert(not ckr.check("[open,refpage='123']").messages)

    # Should error: repeated refpage
    assert(ckr.check(
        """[open,refpage='abc']
        [open,refpage='abc']""").messages)

    # Should error: repeated refpage with something intervening
    assert(ckr.check(
        """[open,refpage='abc']
        [open,refpage='123']
        [open,refpage='abc']""").messages)


def test_UNCLOSED_BLOCK(ckr):
    """Check the UNCLOSED_BLOCK message."""
    ckr.enabled([MessageId.UNCLOSED_BLOCK])
    # These should all have 0 errors
    assert(not ckr.check("== Heading").messages)
    assert(not ckr.check(
        """****
        == Heading
        ****""").messages)
    assert(not ckr.check(
        """****
        contents
        ****""").messages)
    assert(not ckr.check(
        """****
        [source,c]
        ----
        this is code
        ----
        ****""").messages)
    assert(not ckr.check(
        """[open,]
        --
        123

        [source,c]
        ----
        this is code
        ----
        ****
        * this is in a box
        ****

        Now we can close the ref page.
        --""").messages)

    # These should all have 1 error because I removed a block close.
    # Because some of them, the missing block close is an interior one, the stack might look weird,
    # but it's still only 1 error - no matter how many are left unclosed.
    assert(ckr.check(
        """****
        == Heading""").numDiagnostics() == 1)
    assert(ckr.check(
        """****
        contents""").numDiagnostics() == 1)
    assert(ckr.check(
        """****
        [source,c]
        ----
        this is code
        ****""").numDiagnostics() == 1)
    assert(ckr.check(
        """****
        [source,c]
        ----
        this is code
        ----""").numDiagnostics() == 1)
    assert(ckr.check(
        """[open,]
        --
        123

        [source,c]
        ----
        this is code
        ----
        ****
        * this is in a box
        ****""").numDiagnostics() == 1)
    assert(ckr.check(
        """[open,]
        --
        123

        [source,c]
        ----
        this is code
        ----
        ****
        * this is in a box
        --""").numDiagnostics() == 1)
    assert(ckr.check(
        """[open,]
        --
        123

        [source,c]
        ----
        this is code
        ****
        * this is in a box
        ****

        Now we can close the ref page.
        --""").numDiagnostics() == 1)
    assert(ckr.check(
        """[open,]
        --
        123

        [source,c]
        ----
        this is code
        ****
        * this is in a box

        Now we can close the ref page.
        --""").numDiagnostics() == 1)
    assert(ckr.check(
        """[open,]
        --
        123

        [source,c]
        ----
        this is code
        ****
        * this is in a box""").numDiagnostics() == 1)

    # This should have 0 errors of UNCLOSED_BLOCK: the missing opening -- should get automatically fake-inserted,
    assert(not ckr.check(
        """[open,]
        == Heading
        --""").messages)

    # Should have 1 error: block left open at end of file
    assert(ckr.check(
        """[open,]
        --
        bla""").numDiagnostics() == 1)


def test_code_block_tracking(ckr):
    """Check to make sure that no other messages get triggered in a code block."""
    ckr.enabled([MessageId.BAD_ENTITY])

    # Should have 1 error: not a valid entity
    assert(ckr.check("slink:BogusStruct").numDiagnostics() == 1)
    assert(ckr.check(
        """****
        * slink:BogusStruct
        ****""").numDiagnostics() == 1)

    # should have zero errors: the invalid entity is inside a code block,
    # so it shouldn't be parsed.
    # (In reality, it's mostly the MISSING_MACRO message that might interact with code block tracking,
    # but this is easier to test in an API-agnostic way.)
    assert(not ckr.check(
        """[source,c]
        ----
        This code happens to include the characters slink:BogusStruct
        ----""").messages)
