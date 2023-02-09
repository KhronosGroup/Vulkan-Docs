#!/usr/bin/python3 -i
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import os
import pytest
import xml.etree.ElementTree as etree

from check_spec_links import VulkanEntityDatabase
from vuAST import VuAST


@pytest.fixture
def db():
    entity_db = VulkanEntityDatabase()
    return entity_db

def assertParseAndVerify(db, api, vu, filename, fileline = 100, macros = {}):
    ast = VuAST()
    assert(ast.parse(vu, filename, fileline))
    assert(ast.applyMacros(macros))
    assert(ast.verify(db, api))

def assertParseFailVerify(db, api, vu, filename, fileline = 200, macros = {}):
    ast = VuAST()
    assert(ast.parse(vu, filename, fileline))
    assert(ast.applyMacros(macros))
    assert(not ast.verify(db, api))

def assertParseAndGetTag(vu, filename, fileline, expectedTag):
    ast = VuAST()
    assert(ast.parse(vu, filename, fileline))
    assert(ast.getParameterTag() == expectedTag)

##################
### REAL VU Tests.  Make sure each new builtin gets a test based on a real VU
### in this section

def test_basic_function(db):
    """Basic test of parsing a VU for a function."""
    vu = """   for info in pCreateInfos:
                 if info.flags.has_bit(VK_PIPELINE_CREATE_DERIVATIVE_BIT) and info.basePipelineIndex != -1:
                   require(pCreateInfos[info.basePipelineIndex].flags.has_bit(VK_PIPELINE_CREATE_ALLOW_DERIVATIVES_BIT))
        """

    assertParseAndVerify(db, 'vkCreateComputePipelines', vu, 'pipelines.adoc', 123, {})

def test_basic_macro(db):
    """Basic test of parsing a VU for a function, including a macro."""
    vu = """if macro(imageparam).create_info().imageType == VK_IMAGE_TYPE_1D:
              for region in pRegions:
               require(region.imageOffset.y == 0)
               require(region.imageExtent.height == 1)"""

    assertParseAndVerify(db, 'vkCmdCopyImageToBuffer', vu, 'copy_bufferimage_to_imagebuffer_common.adoc', 45, {'imageparam': 'srcImage'})

def test_basic_variable(db):
    """Basic test of parsing a VU for a struct, including a temp variable."""
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               for subpass in pSubpasses:
                 shading_rate_attachment = subpass.pnext(VkFragmentShadingRateAttachmentInfoKHR).pFragmentShadingRateAttachment
                 if shading_rate_attachment != NULL:
                   require(shading_rate_attachment.attachment == VK_ATTACHMENT_UNUSED)"""

    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc', 99, {})

def test_basic_extension(db):
    """Basic test of whether an extension is enabled."""
    vu = """if (renderPass != VK_NULL_HANDLE and
                ext_enabled(VK_EXT_multisampled_render_to_single_sampled)):
             subpassInfo = renderPass.create_info().pSubpasses[subpass]
             msrtssInfo = subpassInfo.pnext(VkMultisampledRenderToSingleSampledInfoEXT)
             if msrtssInfo.multisampledRenderToSingleSampledEnable == VK_TRUE:
              require(pMultisampleState.rasterizationSamples == msrtssInfo.rasterizationSamples)"""

    assertParseAndVerify(db, 'VkGraphicsPipelineCreateInfo', vu, 'pipelines.adoc', 1860, {})

def test_builtin_loop_index(db):
    """Basic test of the loop_index() builtin."""
    vu = """maxMutableBindingIndex = -1
for binding in pBindings:
  if binding.descriptorType == VK_DESCRIPTOR_TYPE_MUTABLE_EXT:
    maxMutableBindingIndex = loop_index(binding)
if maxMutableBindingIndex != -1:
  require(has_pnext(VkMutableDescriptorTypeCreateInfoEXT))
  mutableType = pnext(VkMutableDescriptorTypeCreateInfoEXT)
  require(mutableType.mutableDescriptorTypeListCount > maxMutableBindingIndex)"""

    assertParseAndVerify(db, 'VkDescriptorSetLayoutCreateInfo', vu, 'pipelines.adoc', 1860, {})

def test_builtin_any(db):
    """Basic test of the any() builtin."""
    vu = """libraryInfo = pnext(VkPipelineLibraryCreateInfoKHR)
graphicsLibraryInfo = pnext(VkGraphicsPipelineLibraryCreateInfoEXT)
withCaptureFlag = False
if libraryInfo.libraryCount > 0 and graphicsLibraryInfo.flags.any():
  for library in libraryInfo.pLibraries:
    if library.create_info().flags.has_bit(VK_PIPELINE_CREATE_CAPTURE_INTERNAL_REPRESENTATIONS_BIT_KHR):
      withCaptureFlag = True
      break
  if withCaptureFlag:
    require(flags.has_bit(VK_PIPELINE_CREATE_CAPTURE_INTERNAL_REPRESENTATIONS_BIT_KHR))"""

    assertParseAndVerify(db, 'VkGraphicsPipelineCreateInfo', vu, 'pipelines.adoc', 1860, {})

##################
### Unit tests for parsing and type checking.

def test_negative_parse(db):
    """Parse error tests.  Since python's own ast module is used for parsing,
    this is not quite so extensive."""
    ast = VuAST()

    # Missing parenthesis in condition:
    vu = """if (renderPass != VK_NULL_HANDLE and
                ext_enabled(VK_EXT_multisampled_render_to_single_sampled):
             require(VK_FALSE)"""
    assert(not ast.parse(vu, 'no_file', 100))

    # Invalid character `
    vu = """require(ext_enabled(`VK_EXT_foo`))"""
    assert(not ast.parse(vu, 'no_file', 100))

    # Tag specified in source
    vu = """require(ename:VK_FALSE)"""
    assert(not ast.parse(vu, 'no_file', 100))

def test_negative_macros(db):
    """Parse error tests post macro expansion."""
    ast = VuAST()

    vu = """if (macro(m)):
             require(VK_FALSE)"""
    assert(ast.parse(vu, 'no_file', 100))
    assert(not ast.applyMacros({'m': 'a b'}))
    assert(not ast.applyMacros({'m': 'ename:VK_TRUE'}))
    assert(not ast.applyMacros({'m': 'VK_TRUE)'}))

def test_negative_no_require(db):
    """Test that verification fails if require() is not found in VU."""

    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               subpasses = pSubpasses"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_assignment(db):
    """Test assignment statements."""

    # Basic check
    vu = """variable = flags
require(variable.any())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Test complex expression on RHS
    vu = """variable = pSubpasses[0].pDepthStencilAttachment
require(variable != NULL)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Test builtin call on RHS
    vu = """variable = flags.any()
require(variable)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_assignment(db):
    """Test validation for assignments."""

    # Multiple targets disallowed
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               subpasses = x = pSubpasses
               require(subpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Tuple disallowed as target
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               subpasses, x = pSubpasses
               require(subpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # List disallowed as target
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               [subpasses, x] = pSubpasses
               require(subpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Assignment to API token is not allowed
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               VkImageType = pSubpasses
               require(pSubpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Assignment to VU token is not allowed
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               flags = pSubpasses
               require(flags != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Assignment to builtin function is not allowed
    vu = """loop_index = pSubpasses
require(0 == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """has_bit = pSubpasses
require(0 == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_if(db):
    """Test if statements."""

    # Basic check
    vu = """if flags.any():
             require(0 == 0)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Variable inside condition
    vu = """variable = flags.any()
if variable:
 require(0 == 0)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Multiline body
    vu = """if flags.any():
             variable = 0 == 0
             require(variable)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_if(db):
    """Test validation for if."""

    # If condition must be a boolean
    vu = """ if flags:
               require(pSubpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # If condition cannot be a pointer
    vu = """ if pSubpasses:
               require(flags.any())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_while(db):
    """Test while statements."""

    # Basic check
    vu = """while flags.any():
             require(0 == 0)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For loop emulation
    vu = """index = 0
while index < correlatedViewMaskCount:
 require(pCorrelatedViewMasks[index] == 0)
 index = index + 1"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Multiline body
    vu = """while flags.any():
             variable = 0 == 0
             require(variable)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_while(db):
    """Test validation for while."""

    # While condition must be a boolean
    vu = """ while flags:
               require(pSubpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # While condition cannot be a pointer
    vu = """ while pSubpasses:
               require(flags.any())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_for(db):
    """Test for loops."""

    # Statically sized arrays can be looped over
    vu = """for c in deviceName:
             require(c >= 'a' and c <= 'z')"""
    assertParseAndVerify(db, 'VkPhysicalDeviceProperties', vu, 'devsandqueues.adoc', 531, {})

    # Basic test for loops
    vu = """for layer in ppEnabledLayerNames:
             require(layer == ppEnabledExtensionNames[loop_index(layer)])"""
    assertParseAndVerify(db, 'VkDeviceCreateInfo', vu, 'devsandqueues.adoc', 531, {})

    # Multiline for loop
    vu = """for layer in ppEnabledLayerNames:
             variable = loop_index(layer)
             require(layer == ppEnabledExtensionNames[variable])"""
    assertParseAndVerify(db, 'VkDeviceCreateInfo', vu, 'devsandqueues.adoc', 531, {})

def test_negative_for(db):
    """Test validation for for."""

    # For target must be a single variable
    vu = """ for a, b in pSubpasses:
               require(pSubpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For iterator cannot be a tuple
    vu = """ for subpass in pSubpasses, flags:
               require(flags.any())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For iterator cannot be a list
    vu = """ for subpass in [pSubpasses, flags]:
               require(flags.any())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For iterator must be an array
    vu = """ for attachment in pSubpasses[0].pDepthStencilAttachment:
               require(attachment.attachment == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For target cannot be a builtin
    vu = """ for has_bit in pSubpasses[0].pColorAttachments:
               require(0 == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For iterator cannot be a builtin
    vu = """ for attachment in loop_index:
               require(0 == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_bool_op(db):
    """Test and/or."""

    # Basic check
    vu = """require(0 == 0 and flags.any())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # More than 2 expressions
    vu = """require(0 == 0 or flags.any() or pSubpasses != NULL or pCorrelatedViewMasks[0] != 0)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Complex and nested
    vu = """require(0 == 0 or
                    (flags.any() and
                     pSubpasses != NULL) or
                    pCorrelatedViewMasks[0] != 0)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Complex and nested in if
    vu = """if (0 == 0 or
                (flags.any() and
                 pSubpasses != NULL) or
                pCorrelatedViewMasks[0] != 0):
             require(flags.any())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_bool_op(db):
    """Test validation for and/or."""

    # Pointers do not implicitly cast to bool
    vu = """ if pSubpasses and flags.any():
               require(pSubpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Numbers do not implicitly cast to bool
    vu = """ if flags.any() or pSubpasses[0].colorAttachmentCount:
               require(pSubpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums do not implicitly cast to bool
    vu = """ if flags.any() and pSubpasses != NULL and sType:
               require(pSubpasses != NULL)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bool operations in assignments are no different
    vu = """correct = flags.any() or sType
require(correct)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_unary_not(db):
    """Test not."""

    # Basic check
    vu = """require(not flags.any())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Complex expression
    vu = """require(not (0 == 0 or
                    (flags.any() and
                     pSubpasses != NULL) or
                    pCorrelatedViewMasks[0] != 0))"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_unary_not(db):
    """Test validation for not."""

    # Pointers cannot be used with not
    vu = """require(not pSubpasses)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with not
    vu = """require(not flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with not
    vu = """require(not VK_IMAGE_TYPE_1D)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Numbers cannot be used with not
    vu = """require(not pSubpasses[0].colorAttachmentCount)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_unary_invert(db):
    """Test ~."""

    # Basic check
    vu = """require((~flags).any())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_unary_invert(db):
    """Test validation for ~."""

    # Pointers cannot be used with ~
    vu = """require(~pSubpasses == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with ~
    vu = """require(~flags.any() == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with ~
    vu = """require(~VK_IMAGE_TYPE_1D == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Numbers cannot be used with ~
    vu = """require(~pSubpasses[0].colorAttachmentCount == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_unary_arithmetic(db):
    """Test unary + and -."""

    # Basic check
    vu = """require(-attachmentCount > +subpassCount)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_unary_arithmetic(db):
    """Test validation for unary + and -."""

    # Pointers cannot be used with +/-
    vu = """require(-pSubpasses == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with +/-
    vu = """require(+flags.any() == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with +/-
    vu = """require(-flags == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with +/-
    vu = """require(-VK_IMAGE_TYPE_1D != 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_binary_arithmetic(db):
    """Test binary +, -, *, /, //, %, **."""

    # Basic check
    vu = """require(attachmentCount + subpassCount > dependencyCount)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pCorrelatedViewMasks[0] - 1 == 0)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(4 * attachmentCount % 5 != 0)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(attachmentCount / 3 == 1.3)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(attachmentCount // 3 == 1)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(2 ** attachmentCount < 4096)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_binary_arithmetic(db):
    """Test validation for binary +, -, *, /, //, %, **."""

    # Pointers cannot be used with arithmetic ops
    vu = """require(pSubpasses + 5 == 10)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with arithmetic ops
    vu = """require(flags.any() * -1 == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with arithmetic ops
    vu = """require(10 ** flags == 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with arithmetic ops
    vu = """require(10 // VK_IMAGE_TYPE_1D != 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_shift(db):
    """Test << and >>."""

    # Basic check
    vu = """require(1 << attachmentCount == 0x10)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(attachmentCount >> 31 == 0)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_shift(db):
    """Test validation for << and >>."""

    # Pointers cannot be used with shift
    vu = """require(flags == pSubpasses >> 1)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(flags == 1 << pSubpasses)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with shift
    vu = """require(flags.any() << 1 == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(1 >> flags.any() == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with shift
    vu = """require(flags >> 1 != 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(1 << flags != flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with shift
    vu = """require(VK_IMAGE_TYPE_1D >> 1 == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(1 << VK_IMAGE_TYPE_1D == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_bitwise(db):
    """Test |, & and ^."""

    # Basic check
    vu = """require((flags | ~flags).any())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require((flags & ~flags).none())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require((flags ^ flags).none())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_bitwise(db):
    """Test validation for |, & and ^."""

    # Pointers cannot be used with bitwise operations
    vu = """require(pSubpasses | flags == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with bitwise operations
    vu = """require((flags ^ (pSubpasses != NULL)).none())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with bitwise operations
    vu = """require(flags & VK_IMAGE_TYPE_1D == flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitmasks of different types cannot be used with bitwise operations
    vu = """require((flags ^ pSubpasses[0].flags) != flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_comparison(db):
    """Test >, <, >= and <=."""

    # Basic check
    vu = """require(attachmentCount < subpassCount)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(dependencyCount > subpassCount)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pCorrelatedViewMasks[0] <= subpassCount)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Test that the result of comparison is a boolean
    vu = """require((attachmentCount >= subpassCount) == flags.any())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_comparison(db):
    """Test validation for <, >, >= and <=."""

    # Pointers cannot be used with comparison
    vu = """require(pSubpasses > 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with comparison
    vu = """require(10 <= flags.any())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with comparison
    vu = """require(-1 >= flags)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with comparison
    vu = """require(VK_IMAGE_TYPE_1D < 100000)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_equality(db):
    """Test == and !=."""

    # Basic check
    vu = """require(attachmentCount == subpassCount)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pCorrelatedViewMasks[0] != subpassCount)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Pointers should be comparable if their type matches
    vu = """require(pSubpasses[0].pInputAttachments != pSubpasses[0].pColorAttachments)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pSubpasses[0].pPreserveAttachments != pCorrelatedViewMasks)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Pointers should be comparable with NULL
    vu = """require(pSubpasses[0].pInputAttachments != NULL)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(NULL != pCorrelatedViewMasks)"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Handles should be comparable with NULL
    vu = """require(srcImage != VK_NULL_HANDLE)"""
    assertParseAndVerify(db, 'VkCopyImageInfo2', vu, 'renderpass.adoc')
    vu = """require(VK_NULL_HANDLE != dstImage)"""
    assertParseAndVerify(db, 'VkCopyImageInfo2', vu, 'renderpass.adoc')

    # Test that the result of comparison is a boolean
    vu = """require((attachmentCount == subpassCount) == flags.any())"""
    assertParseAndVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums and bitfields should be comparable as long as their underlying
    # types match
    vu = """require(srcImage.create_info().imageType == dstImage.create_info().imageType)"""
    assertParseAndVerify(db, 'VkCopyImageInfo2', vu, 'renderpass.adoc')
    vu = """require(srcImage.create_info().imageType != VK_IMAGE_TYPE_1D)"""
    assertParseAndVerify(db, 'VkCopyImageInfo2', vu, 'renderpass.adoc')
    vu = """require(VK_IMAGE_TYPE_3D != dstImage.create_info().imageType)"""
    assertParseAndVerify(db, 'VkCopyImageInfo2', vu, 'renderpass.adoc')

def test_negative_equality(db):
    """Test validation for == and !=."""

    # Non-binary comparisons are not allowed
    vu = """require(infoCount == pIndirectStrides[0] == pIndirectStrides[1])"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Pointers and non-pointers cannot be compared
    vu = """require(pInfos == infoCount)"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Pointers and pointers to pointers cannot be compared
    vu = """require(pInfos == ppMaxPrimitiveCounts)"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require(ppMaxPrimitiveCounts != ppMaxPrimitiveCounts[0])"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Pointers cannot have mismatching type classes
    vu = """require(pInfos == pIndirectDeviceAddresses)"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Pointers cannot have mismatching struct types
    vu = """require(pInfos != ppBuildRangeInfos[0])"""
    assertParseFailVerify(db, 'vkBuildAccelerationStructuresKHR', vu, 'accelstructures.adoc')

    # Mismatching type classes are not allowed
    vu = """require(pInfos[0] != 1)"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require(pIndirectDeviceAddress[0] != pInfos[0])"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Mismatching struct types are not allowed
    vu = """require(pIndirectStrides[0] != pInfos[0])"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # TODO: mismatching enums should not be allowed (like VkImageTiling and
    # VkImageType), but currently not implemented.

# Note: builtins correct usage is tested in real-VU tests at the top of the file.
def test_negative_builtins(db):
    """Test validation for the builtin calls.  Not all are tested because the
    code that handles them is generic."""

    # Cannot call nonexistent function
    vu = """require(some_function(flags))"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(flags.some_function())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Function argument count must be correct
    vu = """require(flags.any(), flags.none())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require()"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(flags.any(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM))"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Function argument types must be correct
    vu = """require(flags.has_bit(0))"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(ext_enabled(VkImageType))"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Attribute functions must be called on the correct type
    vu = """require(pSubpasses.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM))"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pSubpasses.valid())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pSubpasses.none())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(flags.create_info())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # loop_index cannot be used with a non-loop variable
    vu = """require(loop_index(pSubpasses) > 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """subpasses = pSubpasses
require(loop_index(subpasses) > 0)"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

# Note: attribute correct usage is well tested among all other tests
def test_negative_attribute(db):
    """Test validation for attributes."""

    # Cannot reference non-existing attribute
    vu = """variable = pDependencies[0].srcGPU
require(flags.any())"""
    assertParseFailVerify(db, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_subscript(db):
    """Test array subscripts."""

    # Subscripting arrays should work
    vu = """require(pIndirectDeviceAddresses[0] != 0)"""
    assertParseAndVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Subscripting arrays of arrays should work
    vu = """require(ppMaxPrimitiveCounts[0][0] >= 1)"""
    assertParseAndVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Subscripting a statically sized array should work
    vu = """require(deviceName[0] == 'V')"""
    assertParseAndVerify(db, 'VkPhysicalDeviceProperties', vu, 'devsandqueues.adoc', 531, {})

def test_negative_subscript(db):
    """Test validation for subscripts."""

    # Subscript must be applied to an array
    vu = """require(flags[0].none())"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pDepthStencilAttachment[0].attachment != 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[0][0].attachment != 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # Subscript must be a number
    vu = """require(pInputAttachments[pPreserveAttachments].attachment != 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[pNext].attachment != 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[flags].attachment != 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[pipelineBindPoint].attachment != 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[VK_EXT_mesh_shader].attachment != 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')

def test_ternary(db):
    """Test ternary operator usage."""

    # Basic test
    vu = """require(True if srcImage != VK_NULL_HANDLE else False)"""
    assertParseAndVerify(db, 'vkCmdCopyImage', vu, 'copies.adoc')

    # Matching types on left and right should work
    vu = """require((srcImage if srcImage != VK_NULL_HANDLE else dstImage).valid())"""
    assertParseAndVerify(db, 'vkCmdCopyImage', vu, 'copies.adoc')
    vu = """require((srcImageLayout if srcImage != VK_NULL_HANDLE else dstImageLayout) == VK_IMAGE_LAYOUT_GENERAL)"""
    assertParseAndVerify(db, 'vkCmdCopyImage', vu, 'copies.adoc')
    vu = """require((pInputAttachments if flags.any() else pColorAttachments) != NULL)"""
    assertParseAndVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((pInputAttachments[0] if flags.any() else pColorAttachments[0]).attachment == 0)"""
    assertParseAndVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # NULL and pointers should work
    vu = """require((pInputAttachments if flags.any() else NULL) != NULL)"""
    assertParseAndVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((NULL if flags.any() else pColorAttachments) != NULL)"""
    assertParseAndVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((NULL if flags.any() else NULL) != pInputAttachments)"""
    assertParseAndVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # VK_NULL_HANDLE and handles should work
    vu = """require((srcImage if srcImage != VK_NULL_HANDLE else VK_NULL_HANDLE) != VK_NULL_HANDLE)"""
    assertParseAndVerify(db, 'vkCmdCopyImage', vu, 'copies.adoc')
    vu = """require((VK_NULL_HANDLE if srcImage != VK_NULL_HANDLE else dstImage) != VK_NULL_HANDLE)"""
    assertParseAndVerify(db, 'vkCmdCopyImage', vu, 'copies.adoc')
    vu = """require((VK_NULL_HANDLE if srcImage != VK_NULL_HANDLE else VK_NULL_HANDLE) != srcImage)"""
    assertParseAndVerify(db, 'vkCmdCopyImage', vu, 'copies.adoc')

    # Bitfields and their enum values should work
    vu = """require((flags if viewMask != 0 else ~flags).any())"""
    assertParseAndVerify(db, 'VkSubpassDescription2', vu, 'copies.adoc')
    vu = """require((flags if flags.any() else VK_SUBPASS_DESCRIPTION_SHADER_RESOLVE_BIT_QCOM).any())"""
    assertParseAndVerify(db, 'VkSubpassDescription2', vu, 'copies.adoc')
    vu = """require((VK_SUBPASS_DESCRIPTION_SHADER_RESOLVE_BIT_QCOM if flags.any() else flags).any())"""
    assertParseAndVerify(db, 'VkSubpassDescription2', vu, 'copies.adoc')

def test_negative_ternary(db):
    """Test validation for ternary operator."""

    # Condition must be a boolean
    vu = """require(viewMask == 0 if flags else pipelineBindPoint == VK_PIPELINE_BIND_POINT_GRAPHICS)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # Condition cannot be a pointer
    vu = """require(viewMask == 0 if pInputAttachments  else pipelineBindPoint == VK_PIPELINE_BIND_POINT_GRAPHICS)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # Types of left and right expressions must match
    vu = """require((0 if flags.any() else pipelineBindPoint) == 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((0 if flags.any() else pInputAttachments) == 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((0 if flags.any() else pPreserveAttachments) == 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((0 if flags.any() else NULL) == 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(flags.any() if flags.any() else 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((VK_NULL_HANDLE if flags.any() else NULL) == VK_NULL_HANDLE)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((pIndirectStrides if infoCount > 0 else ppMaxPrimitiveCounts) == pIndirectStrides)"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require((pInfos if infoCount > 0 else pIndirectStrides) == pInfos)"""
    assertParseFailVerify(db, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require((srcBuffer if regionCount == 0 else dstImage) != VK_NULL_HANDLE)"""
    assertParseFailVerify(db, 'vkCmdCopyBufferToImage', vu, 'copies.adoc')

# Note: variable correct usage is well tested among other tests
def test_negative_variable(db):
    """Test validation for variables."""

    # Cannot use builtin as variable
    vu = """require(loop_index == 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(has_bit.any())"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # Cannot use a variable that is not previously declared
    vu = """require(someVariable == 0)"""
    assertParseFailVerify(db, 'VkSubpassDescription2', vu, 'renderpass.adoc')

##################
### Unit tests for extracting VUID tags

def test_get_tag_basic():
    """Test extracting tag from a simple VU."""

    vu = """require(pCreateInfos != NULL)"""
    assertParseAndGetTag(vu, 'pipelines.adoc', 444, 'pCreateInfos')

def test_get_tag_macro():
    """Test extracting tag from a macro."""

    vu = """require(externally_synchronized(macro(imageparam)))"""
    assertParseAndGetTag(vu, 'copies.adoc', 444, '{imageparam}')

def test_get_tag_assignment():
    """Test extracting tag found in an assignment."""

    vu = """var = pCreateInfos
require(var != NULL)"""
    assertParseAndGetTag(vu, 'pipelines.adoc', 444, 'pCreateInfos')

def test_get_tag_if():
    """Test extracting tag found in an if condition."""

    vu = """if 0 != pCreateInfos[0].basePipelineIndex:
             require(pCreateInfos[0].flags.has_bit(VK_PIPELINE_CREATE_DISABLE_OPTIMIZATION_BIT))"""
    assertParseAndGetTag(vu, 'pipelines.adoc', 444, 'pCreateInfos')

def test_get_tag_for():
    """Test extracting tag found in for iterator."""

    vu = """for info in pCreateInfos:
             require(info[0].flags.none())"""
    assertParseAndGetTag(vu, 'pipelines.adoc', 444, 'pCreateInfos')

def test_get_tag_while():
    """Test extracting tag found in a while condition."""

    vu = """while flags.any():
             require(0 == 0)"""
    assertParseAndGetTag(vu, 'renderpass.adoc', 444, 'flags')
