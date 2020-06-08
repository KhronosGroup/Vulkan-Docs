#!/usr/bin/python3
#
# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
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
        include::{generated}/api/enums/VkQueueFlagBits.txt[]""").numDiagnostics() == 1)
    assert(ckr.check(
        """[open,refpage='VkQueueFlags']
        --
        include::{generated}/validity/enums/VkQueueFlagBits.txt[]""").numDiagnostics() == 1)

    # Should not error: this is just an alias
    assert(ckr.check(
        """[open,refpage='vkUpdateDescriptorSetWithTemplate']
        --
        include::{generated}/api/protos/vkUpdateDescriptorSetWithTemplateKHR.txt[]""").numDiagnostics() == 0)


def test_vulkan_refpage_missing(ckr):
    """Vulkan-specific tests of the REFPAGE_MISSING message."""
    ckr.enabled([MessageId.REFPAGE_MISSING])

    # Should error: flags are expected to have their own ref page.
    assert(ckr.check(
        "include::{generated}/api/flags/VkQueueFlags.txt[]").numDiagnostics() == 1)


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


def test_vulkan_alias(ckr):
    """Tests of the aliasing data structure, dependent on Vulkan-specific registry."""
    entity_db = ckr.ckr.entity_db

    assert(entity_db.areAliases(
        'VkCommandPoolTrimFlagsKHR', 'VkCommandPoolTrimFlags'))
    # Try one reversed-order, though the assert in that method should fire if this is wrong.
    assert(entity_db.areAliases(
        'VkCommandPoolTrimFlags', 'VkCommandPoolTrimFlagsKHR'))

    assert(entity_db.areAliases(
        'VkDescriptorUpdateTemplateKHR', 'VkDescriptorUpdateTemplate'))
    assert(entity_db.areAliases('VkDescriptorUpdateTemplateTypeKHR',
                                'VkDescriptorUpdateTemplateType'))
    assert(entity_db.areAliases('VkQueueFamilyProperties2KHR',
                                'VkQueueFamilyProperties2'))
    assert(entity_db.areAliases('VK_COLORSPACE_SRGB_NONLINEAR_KHR',
                                'VK_COLOR_SPACE_SRGB_NONLINEAR_KHR'))
    assert(entity_db.areAliases('vkEnumeratePhysicalDeviceGroupsKHR',
                                'vkEnumeratePhysicalDeviceGroups'))
    assert(entity_db.areAliases(
        'vkCmdDrawIndirectCountAMD', 'vkCmdDrawIndirectCountKHR'))
    assert(entity_db.areAliases('VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT',
                                'VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT'))

    assert(entity_db.areAliases('VK_LUID_SIZE_KHR', 'VK_LUID_SIZE'))

def test_vulkan_entity_detection(ckr):
    ckr.enabled([MessageId.BAD_ENTITY])
    # Should complain about BAD_ENTITY even though it's sname
    assert(ckr.check('sname:VkInstanceCreateInfoBOGUS').numDiagnostics() == 1)
