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
# Purpose:      This file contains tests for check_spec_links.py

from check_spec_links import MacroChecker, MessageId, shouldEntityBeText
import pytest


class CheckerWrapper(object):
    def __init__(self):
        self.ckr = MacroChecker(set([]))

    def enabled(self, enabled_messages):
        self.ckr.enabled_messages = set(enabled_messages)
        return self

    def check(self, string):
        return self.ckr.processString(string + '\n')


@pytest.fixture
def ckr():
    return CheckerWrapper()


def replacement(ckr):
    assert(len(ckr.messages) == 1)
    from pprint import pprint
    pprint(ckr.messages[0].script_location)
    pprint(ckr.messages[0].replacement)
    pprint(ckr.messages[0].fix)
    return ckr.messages[0].replacement


def test_missing_macro(ckr):
    ckr.enabled([MessageId.MISSING_MACRO])
    assert(ckr.check('with vkFreeMemory by').numDiagnostics() == 1)

    assert(not ckr.check('<<VkObjectType').messages)
    assert(not ckr.check('VkObjectType>>').messages)
    assert(not ckr.check(
        'VkObjectType and Vulkan Handle Relationship>> table').messages)


def test_entity_detection(ckr):
    ckr.enabled([MessageId.BAD_ENTITY])
    # Should complain about BAD_ENTITY
    assert(ckr.check('flink:abcd').numDiagnostics() == 1)

    # Should just give BAD_ENTITY (an error), not MISSING_TEXT (a warning).
    ckr.enabled(
        [MessageId.MISSING_TEXT, MessageId.BAD_ENTITY])
    assert(ckr.check('*flink:abcd*').numErrors() == 1)


def test_wrong_macro(ckr):
    ckr.enabled([MessageId.WRONG_MACRO])
    assert(ckr.check('basetype:uint32_t').numErrors() == 1)
    assert(ckr.check('code:uint32_t').numErrors() == 0)


def test_legacy(ckr):

    ckr.enabled([MessageId.LEGACY])
    # Should complain about LEGACY
    assert(ckr.check('sname:VkDeviceMemory').numDiagnostics() == 1)


def test_should_entity_be_text():
    assert(shouldEntityBeText('pBuffers[i]', '[i]'))
    assert(shouldEntityBeText('maxPerStage*', None))
    assert(shouldEntityBeText('VK_MEMORY_PLANE_[X]', '[X]'))
    assert(shouldEntityBeText('VK_MEMORY_PLANE[__x__]', '[__x__]'))
    assert(shouldEntityBeText('VK_MEMORY_PLANE___i___BIT_EXT', None))
    assert(False == shouldEntityBeText('VK_MEMORY_PLANE_i_BIT_EXT', None))


def test_misused_text(ckr):
    ckr.enabled([MessageId.MISUSED_TEXT])

    assert(ckr.check('etext:VK_MEMORY_PLANE_').numDiagnostics() == 0)
    assert(ckr.check('etext:VK_MEMORY_PLANE_[X]').numDiagnostics() == 0)
    assert(ckr.check('etext:VK_MEMORY_PLANE[i]').numDiagnostics() == 0)
    assert(ckr.check('etext:VK_MEMORY_PLANE[__x__]').numDiagnostics() == 0)

    # Should be OK, since __i__ is a placeholder here
    assert(ckr.check('etext:VK_MEMORY_PLANE___i___BIT_EXT').numDiagnostics() == 0)


def test_extension(ckr):
    ckr.enabled(set(MessageId))
    expected_replacement = '`<<VK_NV_mesh_shader>>`'
    assert(ckr.check('asdf VK_NV_mesh_shader asdf').messages)
    assert(replacement(ckr.check('asdf VK_NV_mesh_shader asdf'))
           == expected_replacement)

    assert(ckr.check('asdf VK_NV_MESH_SHADER asdf').messages)
    assert(replacement(ckr.check('asdf VK_NV_MESH_SHADER asdf'))
           == expected_replacement)

    assert(ckr.check('asdf ename:VK_NV_mesh_shader asdf').messages)
    assert(replacement(ckr.check('asdf ename:VK_NV_mesh_shader asdf'))
           == expected_replacement)

    assert(ckr.check('asdf elink:VK_NV_mesh_shader asdf').messages)
    assert(replacement(ckr.check('asdf elink:VK_NV_mesh_shader asdf'))
           == expected_replacement)

    assert(ckr.check('asdf elink:VK_NV_MESH_SHADER asdf').messages)
    assert(replacement(ckr.check('asdf elink:VK_NV_MESH_SHADER asdf'))
           == expected_replacement)

    assert(not ckr.check('asdf `<<VK_NV_mesh_shader>>` asdf').messages)
    assert(not ckr.check('asdf `VK_NV_mesh_shader` asdf').messages)

    # TODO can we auto-correct this to add the backticks?
    assert(not ckr.check('asdf <<VK_NV_mesh_shader>> asdf').messages)
