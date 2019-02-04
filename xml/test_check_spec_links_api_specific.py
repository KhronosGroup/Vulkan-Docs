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
#               that depend on the API being used.

import pytest

from check_spec_links import MacroChecker, MessageId, makeMacroChecker
from spec_tools.console_printer import ConsolePrinter
from spec_tools.macro_checker_file import shouldEntityBeText
from test_check_spec_links import (CheckerWrapper, allMessages,
                                   loneMsgReplacement, message, msgReplacement)


@pytest.fixture
def ckr(capsys):
    """Fixture - add an arg named ckr to your test function to automatically get one passed to you."""
    return CheckerWrapper(capsys)


def test_vulkan_refpage_mismatch(ckr):
    """Vulkan-specific tests of the REFPAGE_MISMATCH message."""
    ckr.enabled([MessageId.REFPAGE_MISMATCH])
    # Should error: this is actually a mismatch in Vulkan
    assert(ckr.check(
        """[open,refpage='VkQueueFlags']
        --
        include::../api/enums/VkQueueFlagBits.txt[]""").numDiagnostics() == 1)
    assert(ckr.check(
        """[open,refpage='VkQueueFlags']
        --
        include::../validity/enums/VkQueueFlagBits.txt[]""").numDiagnostics() == 1)


def test_vulkan_refpage_missing(ckr):
    """Vulkan-specific tests of the REFPAGE_MISSING message."""
    ckr.enabled([MessageId.REFPAGE_MISSING])

    # Should error: flags are expected to have their own ref page.
    assert(ckr.check(
        "include::../api/flags/VkQueueFlags.txt[]").numDiagnostics() == 1)


def test_vulkan_refpage_block(ckr):
    """Vulkan-specific tests of the REFPAGE_BLOCK message."""
    ckr.enabled([MessageId.REFPAGE_BLOCK])

    # Should have no errors: Non-refpage usage of '--' is acceptable
    assert(not ckr.check(
        """--
        bla
        --""").messages)

    # Should have 1 error:
    #  - line after tag isn't '--'
    result = ckr.check(
        """--
        [open,]
        bla
        --""")
    assert(result.numDiagnostics() == 1)
    # Internally, it's as if the following were the spec source, after putting in the "fake" lines
    # (each of the added lines comes from one message):
    #
    # --
    # [open,]
    # --
    # bla
    # --
    assert("but did not find, a line containing only -- following a reference page tag" in message(result))


def test_vulkan_legacy(ckr):
    """Test the LEGACY message which is Vulkan-only."""
    ckr.enabled([MessageId.LEGACY])
    # Should complain about LEGACY
    assert(ckr.check('sname:VkDeviceMemory').numDiagnostics() == 1)
