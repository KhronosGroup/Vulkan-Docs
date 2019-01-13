#!/usr/bin/python3
#
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
#
# Purpose:      This file contains tests for check_spec_links.py

from check_spec_links import MacroChecker, MessageId, shouldEntityBeText, ConsolePrinter
import pytest


class CheckerWrapper(object):
    """Little wrapper object for a MacroChecker.

    Intended for use in making test assertions shorter and easier to read."""

    def __init__(self):
        self.ckr = MacroChecker(set([]))

    def enabled(self, enabled_messages):
        """Updates the checker's enable message type set, from an iterable"""
        self.ckr.enabled_messages = set(enabled_messages)
        return self

    def check(self, string):
        """Checks a string (as if it were a file), outputs the results to the console, then returns the MacroFileChecker"""
        f = self.ckr.processString(string + '\n')
        ConsolePrinter().output(f)
        return f


@pytest.fixture
def ckr():
    """Fixture - add an arg named ckr to your test function to automatically get one passed to you."""
    return CheckerWrapper()


def replacement(ckr):
    """Returns the replacement text associated with the first message of a file checker"""
    assert(len(ckr.messages) == 1)
    from pprint import pprint
    pprint(ckr.messages[0].script_location)
    pprint(ckr.messages[0].replacement)
    pprint(ckr.messages[0].fix)
    return ckr.messages[0].replacement


def test_missing_macro(ckr):
    """Verify correct functioning of MessageId.MISSING_MACRO"""
    ckr.enabled([MessageId.MISSING_MACRO])
    # This should have a missing macro warning
    assert(ckr.check('with vkFreeMemory by').numDiagnostics() == 1)

    # These 3 should not have a missing macro warning because of their context (in a link)
    assert(not ckr.check('<<VkObjectType').messages)
    assert(not ckr.check('VkObjectType>>').messages)
    assert(not ckr.check(
        'VkObjectType and Vulkan Handle Relationship>> table').messages)


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


def test_legacy(ckr):

    ckr.enabled([MessageId.LEGACY])
    # Should complain about LEGACY
    assert(ckr.check('sname:VkDeviceMemory').numDiagnostics() == 1)


def test_should_entity_be_text():
    # These 5 are all examples of patterns that would merit usage of a ptext/etext/etc
    # macro, for various reasons:

    # has variable in subscript
    assert(shouldEntityBeText('pBuffers[i]', '[i]'))
    assert(shouldEntityBeText('VK_MEMORY_PLANE_[X]', '[X]'))

    # has asterisk
    assert(shouldEntityBeText('maxPerStage*', None))

    # double-underscores make italicized placeholders
    # (triple are double-underscores delimited by underscores...)
    assert(shouldEntityBeText('VK_MEMORY_PLANE[__x__]', '[__x__]'))
    assert(shouldEntityBeText('VK_MEMORY_PLANE___i___BIT_EXT', None))

    # This shouldn't be a *text: macro because it only has single underscores
    assert(False == shouldEntityBeText('VK_MEMORY_PLANE_i_BIT_EXT', None))


def test_misused_text(ckr):
    # Tests the same patterns as test_should_entity_be_text(),
    # but in a whole checker
    ckr.enabled([MessageId.MISUSED_TEXT])

    assert(ckr.check('etext:VK_MEMORY_PLANE_').numDiagnostics() == 0)
    assert(ckr.check('etext:VK_MEMORY_PLANE_[X]').numDiagnostics() == 0)
    assert(ckr.check('etext:VK_MEMORY_PLANE[i]').numDiagnostics() == 0)
    assert(ckr.check('etext:VK_MEMORY_PLANE[__x__]').numDiagnostics() == 0)

    # Should be OK, since __i__ is a placeholder here
    assert(ckr.check('etext:VK_MEMORY_PLANE___i___BIT_EXT').numDiagnostics() == 0)

    # This shouldn't be a *text: macro because it only has single underscores
    assert(ckr.check('VK_MEMORY_PLANE_i_BIT_EXT').numDiagnostics() == 0)

def test_extension(ckr):
    ckr.enabled(set(MessageId))
    # Check formatting of extension names:
    # the following is the canonical way to refer to an extension
    # (link wrapped in backticks)
    expected_replacement='`<<VK_NV_mesh_shader>>`'

    # Extension name mentioned without any markup, should be added
    assert(ckr.check('asdf VK_NV_mesh_shader asdf').messages)
    assert(replacement(ckr.check('asdf VK_NV_mesh_shader asdf'))
           == expected_replacement)

    # Extension name mentioned without any markup and wrong case,
    # should be added and have case fixed
    assert(ckr.check('asdf VK_NV_MESH_SHADER asdf').messages)
    assert(replacement(ckr.check('asdf VK_NV_MESH_SHADER asdf'))
           == expected_replacement)

    # Extension name using wrong/old macro: ename isn't for extensions.
    assert(ckr.check('asdf ename:VK_NV_mesh_shader asdf').messages)
    assert(replacement(ckr.check('asdf ename:VK_NV_mesh_shader asdf'))
           == expected_replacement)

    # Extension name using wrong macro: elink isn't for extensions.
    assert(ckr.check('asdf elink:VK_NV_mesh_shader asdf').messages)
    assert(replacement(ckr.check('asdf elink:VK_NV_mesh_shader asdf'))
           == expected_replacement)

    # Extension name using wrong macro and wrong case: should have markup and case fixed
    assert(ckr.check('asdf elink:VK_NV_MESH_SHADER asdf').messages)
    assert(replacement(ckr.check('asdf elink:VK_NV_MESH_SHADER asdf'))
           == expected_replacement)

    # This shouldn't cause errors because this is how we want it to look.
    assert(not ckr.check('asdf `<<VK_NV_mesh_shader>>` asdf').messages)

    # This doesn't (shouldn't?) cause errors because just backticks on their own
    # "escape" names from the "missing markup" tests.
    assert(not ckr.check('asdf `VK_NV_mesh_shader` asdf').messages)

    # TODO can we auto-correct this to add the backticks?
    # Doesn't error now, but would be nice if it did...
    assert(not ckr.check('asdf <<VK_NV_mesh_shader>> asdf').messages)


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


def test_refpage_name(ckr):
    ckr.enabled([MessageId.REFPAGE_NAME])
    # Should not error: vkCreateInstance actually exists.
    assert(ckr.check(
        "[open,refpage='vkCreateInstance',desc='',type='']").numDiagnostics() == 0)

    # Should error: vkBogus does not exist.
    assert(
        ckr.check("[open,refpage='vkBogus',desc='',type='']").numDiagnostics() == 1)


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
        "[open,refpage='vkCreateInstance',desc='',type='protos']").messages)

    # Should error: this is of type 'protos', not 'structs'.
    assert(
        ckr.check("[open,refpage='vkCreateInstance',desc='',type='structs']").messages)


def test_refpage_xrefs(ckr):
    ckr.enabled([MessageId.REFPAGE_XREFS])
    # Should not error: VkInstanceCreateInfo is a valid entity to have an xref to.
    assert(not ckr.check(
        "[open,refpage='vkCreateInstance',desc='',type='protos',xrefs='VkInstanceCreateInfo']").messages)

    # case difference:
    # should error but offer a replacement.
    assert(ckr.check(
        "[open,refpage='vkCreateInstance',desc='',type='protos',xrefs='vkInstanceCreateInfo']").numDiagnostics() == 1)
    assert(replacement(ckr.check("[open,refpage='vkCreateInstance',desc='',type='protos',xrefs='vkInstanceCreateInfo']"))
           == 'VkInstanceCreateInfo')

    # Should error: not a valid entity.
    assert(ckr.check(
        "[open,refpage='xrCreateInstance',desc='',type='protos',xrefs='xrBogus']").numDiagnostics() == 1)


def test_refpage_xrefs_comma(ckr):
    ckr.enabled([MessageId.REFPAGE_XREFS_COMMA])
    # Should not error: no commas in the xrefs field
    assert(not ckr.check(
        "[open,refpage='vkCreateInstance',desc='',type='protos',xrefs='VkInstanceCreateInfo']").messages)
    # Should error: commas shouldn't be there since it's space-delimited

    assert(ckr.check(
        "[open,refpage='vkCreateInstance',desc='',type='protos',xrefs='VkInstanceCreateInfo,']").numDiagnostics() == 1)
