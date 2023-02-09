#!/usr/bin/env python3 -i
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import ast
import os
import pytest
from pathlib import Path

from reg import Registry
from vuAST import VuAST, VuFormatter, VuSourceStyler, grepTag
from vubuildstrip import VuStripDeadCode


@pytest.fixture
def registry():
    registryFile = os.path.join(Path(__file__).resolve().parent.parent, 'xml', 'vk.xml')
    registry = Registry()
    registry.loadFile(registryFile)
    return registry

def verify(registry, api, vuText, macros, expectText, expectAnyDCE):
    # Parse and verify the VU first
    vu = VuAST()
    vuText = grepTag + '\n' + vuText
    expectText = grepTag + '\n' + expectText if expectText else None
    assert(vu.parse(vuText, 'test.adoc', 100))
    assert(vu.applyMacros(macros))
    assert(vu.verify(registry, api))

    # Apply dead-code elimination
    dce = VuStripDeadCode(vu.astExpanded)
    stripped, anyDCE = dce.strip()

    # Format the result and verify against expectation
    if expectText is None:
        assert(stripped is None)
    else:
        formatter = VuFormatter(VuSourceStyler('test.adoc', 100))
        assert(formatter.format(stripped) == expectText)
    assert(anyDCE == expectAnyDCE)

def test_no_dce(registry):
    """Test when DCE should do nothing."""

    vu = """if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
   for subpass in pSubpasses:
       shading_rate_attachment = subpass.pnext(VkFragmentShadingRateAttachmentInfoKHR).pFragmentShadingRateAttachment
       if shading_rate_attachment != NULL:
         require(shading_rate_attachment.attachment == VK_ATTACHMENT_UNUSED)
else:
    subpass = pSubpasses[0 if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM) else 0]
    if subpass.viewMask > 3:
     count = subpass.inputAttachmentCount + subpass.colorAttachmentCount + 1
     require(count != subpass.preserveAttachmentCount and count == subpass.preserveAttachmentCount)"""
    expect = """if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
  for subpass in pSubpasses:
    shading_rate_attachment = subpass.pnext(VkFragmentShadingRateAttachmentInfoKHR).pFragmentShadingRateAttachment
    if shading_rate_attachment != NULL:
      require(shading_rate_attachment.attachment == VK_ATTACHMENT_UNUSED)
else:
  subpass = pSubpasses[0 if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM) else 0]
  if subpass.viewMask > 3:
    count = subpass.inputAttachmentCount + subpass.colorAttachmentCount + 1
    require(count != subpass.preserveAttachmentCount and
        count == subpass.preserveAttachmentCount)"""

    verify(registry, 'VkRenderPassCreateInfo2', vu, {}, expect, False)

def test_empty_if_block(registry):
    """Test DCE with empty if blocks."""

    vu = """if False:
  pass
require(pCreateInfo == NULL)"""
    expect = """require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', vu, {}, expect, True)

    vu = """if False:
  pass
else:
  require(pCreateInfo == NULL)"""
    expect = """if not False:
  require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', vu, {}, expect, True)

    vu = """if True:
  pass
require(pCreateInfo == NULL)"""
    expect = """require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', vu, {}, expect, True)

    vu = """if True:
  # Comment
  pass
else:
  require(pCreateInfo == NULL)"""
    expect = """if not True:
  require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', vu, {}, expect, True)

def test_empty_for_body(registry):
    """Test DCE with empty loop body."""

    vu = """for attachment in pAttachments:
  pass
require(pSubpasses != NULL)"""
    expect = """require(pSubpasses != NULL)"""
    verify(registry, 'VkRenderPassCreateInfo2', vu, {}, expect, True)

    vu = """for attachment in pAttachments:
  # A comment line
  pass
require(pSubpasses != NULL)"""
    expect = """require(pSubpasses != NULL)"""
    verify(registry, 'VkRenderPassCreateInfo2', vu, {}, expect, True)

    vu = """require(pSubpasses != NULL)
for attachment in pAttachments:
  # A comment line
  # And another
  pass
"""
    expect = """require(pSubpasses != NULL)"""
    verify(registry, 'VkRenderPassCreateInfo2', vu, {}, expect, True)

def test_unused_variable(registry):
    """Test DCE with empty loop body."""

    vu = """attachments = pAttachments
require(pSubpasses != NULL)"""
    expect = """require(pSubpasses != NULL)"""
    verify(registry, 'VkRenderPassCreateInfo2', vu, {}, expect, True)

    # Removing variables may need multiple passes; this test only tests one pass
    vu = """require(pSubpasses != NULL)
attachments = pAttachments
for attachment in attachments:
    pass
"""
    expect = """require(pSubpasses != NULL)
attachments = pAttachments"""
    verify(registry, 'VkRenderPassCreateInfo2', vu, {}, expect, True)
