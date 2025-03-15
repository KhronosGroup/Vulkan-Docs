#!/usr/bin/env python3 -i
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import os
import pytest
from pathlib import Path

from reg import Registry
from vuAST import VuAST, isCodifiedVU, grepTag


@pytest.fixture
def registry():
    registryFile = os.path.join(Path(__file__).resolve().parent.parent, 'xml', 'vk.xml')
    registry = Registry()
    registry.loadFile(registryFile)
    return registry

def addGrepTag(vu):
    indent = len(vu) - len(vu.lstrip())
    return ' ' * indent + grepTag + '\n' + vu

def assertParseAndVerify(registry, api, vu, filename, fileline = 100, macros = {}):
    ast = VuAST()
    vu = addGrepTag(vu)
    assert(isCodifiedVU(vu.splitlines()))
    assert(ast.parse(vu, filename, fileline))
    assert(ast.applyMacros(macros))
    assert(ast.verify(registry, api))

def assertParseFailVerify(registry, api, vu, filename, fileline = 200, macros = {}):
    ast = VuAST()
    vu = addGrepTag(vu)
    assert(isCodifiedVU(vu.splitlines()))
    assert(ast.parse(vu, filename, fileline))
    assert(ast.applyMacros(macros))
    assert(not ast.verify(registry, api))

def assertParseAndGetTag(vu, filename, fileline, expectedTag):
    ast = VuAST()
    vu = addGrepTag(vu)
    assert(isCodifiedVU(vu.splitlines()))
    assert(ast.parse(vu, filename, fileline))
    assert(ast.getParameterTag() == expectedTag)

##################
### REAL VU Tests.  Make sure each new predicate gets a test based on a real VU
### in this section

def test_basic_function(registry):
    """Basic test of parsing a VU for a function."""
    vu = """   for info in pCreateInfos:
                 if info.flags.has_bit(VK_PIPELINE_CREATE_DERIVATIVE_BIT) and info.basePipelineIndex != -1:
                   require(pCreateInfos[info.basePipelineIndex].flags.has_bit(VK_PIPELINE_CREATE_ALLOW_DERIVATIVES_BIT))
        """

    assertParseAndVerify(registry, 'vkCreateComputePipelines', vu, 'pipelines.adoc', 123, {})

def test_basic_macro(registry):
    """Basic test of parsing a VU for a function, including a macro."""
    vu = """if macro(imageparam).create_info().imageType == VK_IMAGE_TYPE_1D:
              for region in pRegions:
               require(region.imageOffset.y == 0)
               require(region.imageExtent.height == 1)"""

    assertParseAndVerify(registry, 'vkCmdCopyImageToBuffer', vu, 'copy_bufferimage_to_imagebuffer_common.adoc', 45, {'imageparam': 'srcImage'})

    # Make sure macro() is accepted as an attribute call
    vu = """if macro(imageparam).create_info().imageType == VK_IMAGE_TYPE_1D:
  for region in pRegions:
    require(region.macro(imageoffset).y == 0)
    require(region.macro(imageextent).height == 1)"""

    assertParseAndVerify(registry, 'vkCmdCopyImageToBuffer', vu, 'copy_bufferimage_to_imagebuffer_common.adoc', 45,
                         {'imageparam': 'srcImage', 'imageoffset': 'imageOffset', 'imageextent': 'imageExtent'})

def test_basic_variable(registry):
    """Basic test of parsing a VU for a struct, including a temp variable."""
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               for subpass in pSubpasses:
                 shading_rate_attachment = subpass.pnext(VkFragmentShadingRateAttachmentInfoKHR).pFragmentShadingRateAttachment
                 if shading_rate_attachment != NULL:
                   require(shading_rate_attachment.attachment == VK_ATTACHMENT_UNUSED)"""

    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc', 99, {})

def test_basic_extension(registry):
    """Basic test of whether an extension is enabled."""
    vu = """if (renderPass != VK_NULL_HANDLE and
                is_ext_enabled(VK_EXT_multisampled_render_to_single_sampled)):
             subpassInfo = renderPass.create_info().pSubpasses[subpass]
             msrtssInfo = subpassInfo.pnext(VkMultisampledRenderToSingleSampledInfoEXT)
             if msrtssInfo.multisampledRenderToSingleSampledEnable == VK_TRUE:
              require(pMultisampleState.rasterizationSamples == msrtssInfo.rasterizationSamples)"""

    assertParseAndVerify(registry, 'VkGraphicsPipelineCreateInfo', vu, 'pipelines.adoc', 1860, {})

def test_predicate_array_index(registry):
    """Basic test of the array_index() predicate."""
    vu = """for binding in pBindings:
  if binding.descriptorType == VK_DESCRIPTOR_TYPE_MUTABLE_EXT:
    bindingIndex = array_index(binding)
    if bindingIndex != -1:
      require(has_pnext(VkMutableDescriptorTypeCreateInfoEXT))
      mutableType = pnext(VkMutableDescriptorTypeCreateInfoEXT)
      require(mutableType.mutableDescriptorTypeListCount > bindingIndex)"""

    assertParseAndVerify(registry, 'VkDescriptorSetLayoutCreateInfo', vu, 'pipelines.adoc', 1860, {})

def test_predicate_any(registry):
    """Basic test of the any() predicate."""
    vu = """libraryInfo = pnext(VkPipelineLibraryCreateInfoKHR)
graphicsLibraryInfo = pnext(VkGraphicsPipelineLibraryCreateInfoEXT)
if libraryInfo.libraryCount > 0 and graphicsLibraryInfo.flags.any():
  for library in libraryInfo.pLibraries:
    if library.create_info().flags.has_bit(VK_PIPELINE_CREATE_CAPTURE_INTERNAL_REPRESENTATIONS_BIT_KHR):
      require(flags.has_bit(VK_PIPELINE_CREATE_CAPTURE_INTERNAL_REPRESENTATIONS_BIT_KHR))"""

    assertParseAndVerify(registry, 'VkGraphicsPipelineCreateInfo', vu, 'pipelines.adoc', 1860, {})

def test_predicate_version(registry):
    """Basic test of the is_version() predicate."""
    vu = """if is_version(1, 3):
              require(flags.has_bit(VK_PIPELINE_CREATE_CAPTURE_INTERNAL_REPRESENTATIONS_BIT_KHR))"""

    assertParseAndVerify(registry, 'VkGraphicsPipelineCreateInfo', vu, 'pipelines.adoc', 1860, {})

def test_comment(registry):
    """Basic test for comment support."""
    vu = """   for info in pCreateInfos:
                 # This is a comment
                 if info.flags.has_bit(VK_PIPELINE_CREATE_DERIVATIVE_BIT) and info.basePipelineIndex != -1:
                   require(pCreateInfos[info.basePipelineIndex].flags.has_bit(VK_PIPELINE_CREATE_ALLOW_DERIVATIVES_BIT))"""

    assertParseAndVerify(registry, 'vkCreateComputePipelines', vu, 'pipelines.adoc', 123, {})

    vu = """   for info in pCreateInfos:
                 if info.flags.has_bit(VK_PIPELINE_CREATE_DERIVATIVE_BIT) and info.basePipelineIndex != -1:
                   # This is a comment
                   # that spans multiple lines
                   require(pCreateInfos[info.basePipelineIndex].flags.has_bit(VK_PIPELINE_CREATE_ALLOW_DERIVATIVES_BIT))"""

    assertParseAndVerify(registry, 'vkCreateComputePipelines', vu, 'pipelines.adoc', 123, {})

    vu = """   # Comment on first line
   for info in pCreateInfos:
                 if info.flags.has_bit(VK_PIPELINE_CREATE_DERIVATIVE_BIT) and info.basePipelineIndex != -1:
                   require(pCreateInfos[info.basePipelineIndex].flags.has_bit(VK_PIPELINE_CREATE_ALLOW_DERIVATIVES_BIT))"""

    assertParseAndVerify(registry, 'vkCreateComputePipelines', vu, 'pipelines.adoc', 123, {})

    vu = """ # Comment on first line
 # With more comments on next line
 for info in pCreateInfos:
   if info.flags.has_bit(VK_PIPELINE_CREATE_DERIVATIVE_BIT) and info.basePipelineIndex != -1:
     # And comments inline
     require(pCreateInfos[info.basePipelineIndex].flags.has_bit(VK_PIPELINE_CREATE_ALLOW_DERIVATIVES_BIT))"""

    assertParseAndVerify(registry, 'vkCreateComputePipelines', vu, 'pipelines.adoc', 123, {})

##################
### Unit tests for parsing and type checking.

def test_negative_parse(registry):
    """Parse error tests.  Since python's own ast module is used for parsing,
    this is not quite so extensive."""
    ast = VuAST()

    # Missing parenthesis in condition:
    vu = """codified-vu
if (renderPass != VK_NULL_HANDLE and
    is_ext_enabled(VK_EXT_multisampled_render_to_single_sampled):
  require(VK_FALSE)"""
    assert(not ast.parse(vu, 'no_file', 100))

    # Invalid character `
    vu = """codified-vu
require(is_ext_enabled(`VK_EXT_foo`))"""
    assert(not ast.parse(vu, 'no_file', 100))

    # Tag specified in source
    vu = """codified-vu
require(ename:VK_FALSE)"""
    assert(not ast.parse(vu, 'no_file', 100))

def test_negative_macros(registry):
    """Parse error tests post macro expansion."""
    ast = VuAST()

    vu = """codified-vu
if (macro(m)):
             require(VK_FALSE)"""
    assert(ast.parse(vu, 'no_file', 100))
    assert(not ast.applyMacros({'m': 'a b'}))
    assert(not ast.applyMacros({'m': 'ename:VK_TRUE'}))
    assert(not ast.applyMacros({'m': 'VK_TRUE)'}))

def test_negative_no_require(registry):
    """Test that verification fails if require() is not found in VU."""

    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               subpasses = pSubpasses"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_assignment(registry):
    """Test assignment statements."""

    # Basic check
    vu = """variable = flags
require(variable.any())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Test complex expression on RHS
    vu = """variable = pSubpasses[0].pDepthStencilAttachment
require(variable != NULL)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Test predicate call on RHS
    vu = """variable = flags.any()
require(variable)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_assignment(registry):
    """Test validation for assignments."""

    # Multiple targets disallowed
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               subpasses = x = pSubpasses
               require(subpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Tuple disallowed as target
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               subpasses, x = pSubpasses
               require(subpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # List disallowed as target
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               [subpasses, x] = pSubpasses
               require(subpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Assignment to API token is not allowed
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               VkImageType = pSubpasses
               require(pSubpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Assignment to VU token is not allowed
    vu = """ if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               flags = pSubpasses
               require(flags != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Assignment to predicate function is not allowed
    vu = """array_index = pSubpasses
require(0 == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """has_bit = pSubpasses
require(0 == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_if(registry):
    """Test if statements."""

    # Basic check
    vu = """if flags.any():
             require(0 == 0)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Variable inside condition
    vu = """variable = flags.any()
if variable:
 require(0 == 0)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Multiline body
    vu = """if flags.any():
             variable = 0 == 0
             require(variable)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # With else
    vu = """if flags.any():
             variable = 0 == 0
             require(variable)
else:
    variable2 = 0
    require(variable2 == 0)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_if(registry):
    """Test validation for if."""

    # If condition must be a boolean
    vu = """ if flags:
               require(pSubpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # If condition cannot be a pointer
    vu = """ if pSubpasses:
               require(flags.any())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_while(registry):
    """Test validation for while."""

    # While is not supported
    vu = """ while flags.any():
               require(pSubpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_for(registry):
    """Test for loops."""

    # Statically sized arrays can be looped over
    vu = """for c in deviceName:
             require(c >= 'a' and c <= 'z')"""
    assertParseAndVerify(registry, 'VkPhysicalDeviceProperties', vu, 'devsandqueues.adoc', 531, {})

    # Basic test for loops
    vu = """for layer in ppEnabledLayerNames:
             require(layer == ppEnabledExtensionNames[array_index(layer)])"""
    assertParseAndVerify(registry, 'VkDeviceCreateInfo', vu, 'devsandqueues.adoc', 531, {})

    # Multiline for loop
    vu = """for layer in ppEnabledLayerNames:
             variable = array_index(layer)
             require(layer == ppEnabledExtensionNames[variable])"""
    assertParseAndVerify(registry, 'VkDeviceCreateInfo', vu, 'devsandqueues.adoc', 531, {})

def test_negative_for(registry):
    """Test validation for for."""

    # For target must be a single variable
    vu = """ for a, b in pSubpasses:
               require(pSubpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For iterator cannot be a tuple
    vu = """ for subpass in pSubpasses, flags:
               require(flags.any())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For iterator cannot be a list
    vu = """ for subpass in [pSubpasses, flags]:
               require(flags.any())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For iterator must be an array
    vu = """ for attachment in pSubpasses[0].pDepthStencilAttachment:
               require(attachment.attachment == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For target cannot be a predicate
    vu = """ for has_bit in pSubpasses[0].pColorAttachments:
               require(0 == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # For iterator cannot be a predicate
    vu = """ for attachment in array_index:
               require(0 == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # break is not allowed
    vu = """ for attachment in pSubpasses:
               require(0 == 0)
               break"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # continue is not allowed
    vu = """ for subpass in pSubpasses:
               require(0 == 0)
               if subpass.inputAttachmentCount > 1:
                   continue"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')


def test_bool_op(registry):
    """Test and/or."""

    # Basic check
    vu = """require(0 == 0 and flags.any())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # More than 2 expressions
    vu = """require(0 == 0 or flags.any() or pSubpasses != NULL or pCorrelatedViewMasks[0] != 0)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Complex and nested
    vu = """require(0 == 0 or
                    (flags.any() and
                     pSubpasses != NULL) or
                    pCorrelatedViewMasks[0] != 0)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Complex and nested in if
    vu = """if (0 == 0 or
                (flags.any() and
                 pSubpasses != NULL) or
                pCorrelatedViewMasks[0] != 0):
             require(flags.any())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_bool_op(registry):
    """Test validation for and/or."""

    # Pointers do not implicitly cast to bool
    vu = """ if pSubpasses and flags.any():
               require(pSubpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Numbers do not implicitly cast to bool
    vu = """ if flags.any() or pSubpasses[0].colorAttachmentCount:
               require(pSubpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums do not implicitly cast to bool
    vu = """ if flags.any() and pSubpasses != NULL and sType:
               require(pSubpasses != NULL)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bool operations in assignments are no different
    vu = """correct = flags.any() or sType
require(correct)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_unary_not(registry):
    """Test not."""

    # Basic check
    vu = """require(not flags.any())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Complex expression
    vu = """require(not (0 == 0 or
                    (flags.any() and
                     pSubpasses != NULL) or
                    pCorrelatedViewMasks[0] != 0))"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_unary_not(registry):
    """Test validation for not."""

    # Pointers cannot be used with not
    vu = """require(not pSubpasses)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with not
    vu = """require(not flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with not
    vu = """require(not VK_IMAGE_TYPE_1D)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Numbers cannot be used with not
    vu = """require(not pSubpasses[0].colorAttachmentCount)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_unary_invert(registry):
    """Test ~."""

    # Basic check
    vu = """require((~flags).any())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_unary_invert(registry):
    """Test validation for ~."""

    # Pointers cannot be used with ~
    vu = """require(~pSubpasses == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with ~
    vu = """require(~flags.any() == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with ~
    vu = """require(~VK_IMAGE_TYPE_1D == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Numbers cannot be used with ~
    vu = """require(~pSubpasses[0].colorAttachmentCount == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_unary_arithmetic(registry):
    """Test unary + and -."""

    # Basic check
    vu = """require(-attachmentCount > +subpassCount)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_unary_arithmetic(registry):
    """Test validation for unary + and -."""

    # Pointers cannot be used with +/-
    vu = """require(-pSubpasses == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with +/-
    vu = """require(+flags.any() == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with +/-
    vu = """require(-flags == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with +/-
    vu = """require(-VK_IMAGE_TYPE_1D != 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_binary_arithmetic(registry):
    """Test binary +, -, *, /, //, %, **."""

    # Basic check
    vu = """require(attachmentCount + subpassCount > dependencyCount)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pCorrelatedViewMasks[0] - 1 == 0)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(4 * attachmentCount % 5 != 0)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(attachmentCount / 3 == 1.3)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(attachmentCount // 3 == 1)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(2 ** attachmentCount < 4096)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_binary_arithmetic(registry):
    """Test validation for binary +, -, *, /, //, %, **."""

    # Pointers cannot be used with arithmetic ops
    vu = """require(pSubpasses + 5 == 10)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with arithmetic ops
    vu = """require(flags.any() * -1 == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with arithmetic ops
    vu = """require(10 ** flags == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with arithmetic ops
    vu = """require(10 // VK_IMAGE_TYPE_1D != 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_shift(registry):
    """Test << and >>."""

    # Basic check
    vu = """require(1 << attachmentCount == 0x10)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(attachmentCount >> 31 == 0)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_shift(registry):
    """Test validation for << and >>."""

    # Pointers cannot be used with shift
    vu = """require(flags == pSubpasses >> 1)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(flags == 1 << pSubpasses)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with shift
    vu = """require(flags.any() << 1 == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(1 >> flags.any() == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with shift
    vu = """require(flags >> 1 != 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(1 << flags != flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with shift
    vu = """require(VK_IMAGE_TYPE_1D >> 1 == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(1 << VK_IMAGE_TYPE_1D == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_bitwise(registry):
    """Test |, & and ^."""

    # Basic check
    vu = """require((flags | ~flags).any())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require((flags & ~flags).none())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require((flags ^ flags).none())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_bitwise(registry):
    """Test validation for |, & and ^."""

    # Pointers cannot be used with bitwise operations
    vu = """require(pSubpasses | flags == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with bitwise operations
    vu = """require((flags ^ (pSubpasses != NULL)).none())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with bitwise operations
    vu = """require(flags & VK_IMAGE_TYPE_1D == flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitmasks of different types cannot be used with bitwise operations
    vu = """require((flags ^ pSubpasses[0].flags) != flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_comparison(registry):
    """Test >, <, >= and <=."""

    # Basic check
    vu = """require(attachmentCount < subpassCount)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(dependencyCount > subpassCount)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pCorrelatedViewMasks[0] <= subpassCount)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Test that the result of comparison is a boolean
    vu = """require((attachmentCount >= subpassCount) == flags.any())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_comparison(registry):
    """Test validation for <, >, >= and <=."""

    # Pointers cannot be used with comparison
    vu = """require(pSubpasses > 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Booleans cannot be used with comparison
    vu = """require(10 <= flags.any())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Bitfields cannot be used with comparison
    vu = """require(-1 >= flags)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums cannot be used with comparison
    vu = """require(VK_IMAGE_TYPE_1D < 100000)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_equality(registry):
    """Test == and !=."""

    # Basic check
    vu = """require(attachmentCount == subpassCount)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pCorrelatedViewMasks[0] != subpassCount)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Pointers should be comparable if their type matches
    vu = """require(pSubpasses[0].pInputAttachments != pSubpasses[0].pColorAttachments)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pSubpasses[0].pPreserveAttachments != pCorrelatedViewMasks)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Pointers should be comparable with NULL
    vu = """require(pSubpasses[0].pInputAttachments != NULL)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(NULL != pCorrelatedViewMasks)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Handles should be comparable with NULL
    vu = """require(srcImage != VK_NULL_HANDLE)"""
    assertParseAndVerify(registry, 'VkCopyImageInfo2', vu, 'renderpass.adoc')
    vu = """require(VK_NULL_HANDLE != dstImage)"""
    assertParseAndVerify(registry, 'VkCopyImageInfo2', vu, 'renderpass.adoc')

    # Test that the result of comparison is a boolean
    vu = """require((attachmentCount == subpassCount) == flags.any())"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Enums and bitfields should be comparable as long as their underlying
    # types match
    vu = """require(srcImage.create_info().imageType == dstImage.create_info().imageType)"""
    assertParseAndVerify(registry, 'VkCopyImageInfo2', vu, 'renderpass.adoc')
    vu = """require(srcImage.create_info().imageType != VK_IMAGE_TYPE_1D)"""
    assertParseAndVerify(registry, 'VkCopyImageInfo2', vu, 'renderpass.adoc')
    vu = """require(VK_IMAGE_TYPE_3D != dstImage.create_info().imageType)"""
    assertParseAndVerify(registry, 'VkCopyImageInfo2', vu, 'renderpass.adoc')

def test_negative_equality(registry):
    """Test validation for == and !=."""

    # Non-binary comparisons are not allowed
    vu = """require(infoCount == pIndirectStrides[0] == pIndirectStrides[1])"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Pointers and non-pointers cannot be compared
    vu = """require(pInfos == infoCount)"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Pointers and pointers to pointers cannot be compared
    vu = """require(pInfos == ppMaxPrimitiveCounts)"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require(ppMaxPrimitiveCounts != ppMaxPrimitiveCounts[0])"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Pointers cannot have mismatching type classes
    vu = """require(pInfos == pIndirectDeviceAddresses)"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Pointers cannot have mismatching struct types
    vu = """require(pInfos != ppBuildRangeInfos[0])"""
    assertParseFailVerify(registry, 'vkBuildAccelerationStructuresKHR', vu, 'accelstructures.adoc')

    # Mismatching type classes are not allowed
    vu = """require(pInfos[0] != 1)"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require(pIndirectDeviceAddress[0] != pInfos[0])"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Mismatching struct types are not allowed
    vu = """require(pIndirectStrides[0] != pInfos[0])"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Mismatching enum types are not allowed
    vu = """require(VK_IMAGE_TILING_OPTIMAL != VK_IMAGE_TYPE_1D)"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require(VK_IMAGE_TYPE_1D == pInfos[0].flags)"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require(pInfos[0].flags != pInfos[0].mode)"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require(pInfos[0].flags.has_bit(VK_QUEUE_GRAPHICS_BIT))"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

# Note: predicates correct usage is tested in real-VU tests at the top of the file.
def test_negative_predicates(registry):
    """Test validation for the predicate calls.  Not all are tested because the
    code that handles them is generic."""

    # Cannot call nonexistent function
    vu = """require(some_function(flags))"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(flags.some_function())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Function argument count must be correct
    vu = """require(flags.any(), flags.none())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require()"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(flags.any(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM))"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Function argument types must be correct
    vu = """require(flags.has_bit(0))"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(is_ext_enabled(VkImageType))"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Attribute functions must be called on the correct type
    vu = """require(pSubpasses.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM))"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pSubpasses.valid())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(pSubpasses.none())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """require(flags.create_info())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # array_index cannot be used with a non-loop variable
    vu = """require(array_index(pSubpasses) > 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')
    vu = """subpasses = pSubpasses
require(array_index(subpasses) > 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

# Note: attribute correct usage is well tested among all other tests
def test_negative_attribute(registry):
    """Test validation for attributes."""

    # Cannot reference non-existing attribute
    vu = """variable = pDependencies[0].srcGPU
require(flags.any())"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_subscript(registry):
    """Test array subscripts."""

    # Subscripting arrays should work
    vu = """require(pIndirectDeviceAddresses[0] != 0)"""
    assertParseAndVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Subscripting arrays of arrays should work
    vu = """require(ppMaxPrimitiveCounts[0][0] >= 1)"""
    assertParseAndVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')

    # Subscripting a statically sized array should work
    vu = """require(deviceName[0] == 'V')"""
    assertParseAndVerify(registry, 'VkPhysicalDeviceProperties', vu, 'devsandqueues.adoc', 531, {})

def test_negative_subscript(registry):
    """Test validation for subscripts."""

    # Subscript must be applied to an array
    vu = """require(flags[0].none())"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pDepthStencilAttachment[0].attachment != 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[0][0].attachment != 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # Subscript must be a number
    vu = """require(pInputAttachments[pPreserveAttachments].attachment != 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[pNext].attachment != 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[flags].attachment != 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[pipelineBindPoint].attachment != 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(pInputAttachments[VK_EXT_mesh_shader].attachment != 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

def test_ternary(registry):
    """Test ternary operator usage."""

    # Basic test
    vu = """require(True if srcImage != VK_NULL_HANDLE else False)"""
    assertParseAndVerify(registry, 'vkCmdCopyImage', vu, 'copies.adoc')

    # Matching types on left and right should work
    vu = """require((srcImage if srcImage != VK_NULL_HANDLE else dstImage).valid())"""
    assertParseAndVerify(registry, 'vkCmdCopyImage', vu, 'copies.adoc')
    vu = """require((srcImageLayout if srcImage != VK_NULL_HANDLE else dstImageLayout) == VK_IMAGE_LAYOUT_GENERAL)"""
    assertParseAndVerify(registry, 'vkCmdCopyImage', vu, 'copies.adoc')
    vu = """require((pInputAttachments if flags.any() else pColorAttachments) != NULL)"""
    assertParseAndVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((pInputAttachments[0] if flags.any() else pColorAttachments[0]).attachment == 0)"""
    assertParseAndVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # NULL and pointers should work
    vu = """require((pInputAttachments if flags.any() else NULL) != NULL)"""
    assertParseAndVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((NULL if flags.any() else pColorAttachments) != NULL)"""
    assertParseAndVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((NULL if flags.any() else NULL) != pInputAttachments)"""
    assertParseAndVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # VK_NULL_HANDLE and handles should work
    vu = """require((srcImage if srcImage != VK_NULL_HANDLE else VK_NULL_HANDLE) != VK_NULL_HANDLE)"""
    assertParseAndVerify(registry, 'vkCmdCopyImage', vu, 'copies.adoc')
    vu = """require((VK_NULL_HANDLE if srcImage != VK_NULL_HANDLE else dstImage) != VK_NULL_HANDLE)"""
    assertParseAndVerify(registry, 'vkCmdCopyImage', vu, 'copies.adoc')
    vu = """require((VK_NULL_HANDLE if srcImage != VK_NULL_HANDLE else VK_NULL_HANDLE) != srcImage)"""
    assertParseAndVerify(registry, 'vkCmdCopyImage', vu, 'copies.adoc')

    # Bitfields and their enum values should work
    vu = """require((flags if viewMask != 0 else ~flags).any())"""
    assertParseAndVerify(registry, 'VkSubpassDescription2', vu, 'copies.adoc')
    vu = """require((flags if flags.any() else VK_SUBPASS_DESCRIPTION_SHADER_RESOLVE_BIT_QCOM).any())"""
    assertParseAndVerify(registry, 'VkSubpassDescription2', vu, 'copies.adoc')
    vu = """require((VK_SUBPASS_DESCRIPTION_SHADER_RESOLVE_BIT_QCOM if flags.any() else flags).any())"""
    assertParseAndVerify(registry, 'VkSubpassDescription2', vu, 'copies.adoc')

def test_negative_ternary(registry):
    """Test validation for ternary operator."""

    # Condition must be a boolean
    vu = """require(viewMask == 0 if flags else pipelineBindPoint == VK_PIPELINE_BIND_POINT_GRAPHICS)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # Condition cannot be a pointer
    vu = """require(viewMask == 0 if pInputAttachments  else pipelineBindPoint == VK_PIPELINE_BIND_POINT_GRAPHICS)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # Types of left and right expressions must match
    vu = """require((0 if flags.any() else pipelineBindPoint) == 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((0 if flags.any() else pInputAttachments) == 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((0 if flags.any() else pPreserveAttachments) == 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((0 if flags.any() else NULL) == 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(flags.any() if flags.any() else 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((VK_NULL_HANDLE if flags.any() else NULL) == VK_NULL_HANDLE)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require((pIndirectStrides if infoCount > 0 else ppMaxPrimitiveCounts) == pIndirectStrides)"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require((pInfos if infoCount > 0 else pIndirectStrides) == pInfos)"""
    assertParseFailVerify(registry, 'vkCmdBuildAccelerationStructuresIndirectKHR', vu, 'accelstructures.adoc')
    vu = """require((srcBuffer if regionCount == 0 else dstImage) != VK_NULL_HANDLE)"""
    assertParseFailVerify(registry, 'vkCmdCopyBufferToImage', vu, 'copies.adoc')

# Note: variable correct usage is well tested among other tests
def test_negative_variable(registry):
    """Test validation for variables."""

    # Cannot use predicate as variable
    vu = """require(array_index == 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')
    vu = """require(has_bit.any())"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # Cannot use a variable that is not previously declared
    vu = """require(someVariable == 0)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

def test_features(registry):
    """Test that features are correctly detected."""

    # Vulkan 1.0 feature
    vu = """require(is_feature_enabled(imageCubeArray))"""
    assertParseAndVerify(registry, 'vkCmdCopyImage', vu, 'copies.adoc')

    # Promoted feature in Vulkan 1.1 and 1.2
    vu = """require(is_feature_enabled(storageBuffer16BitAccess) and is_feature_enabled(drawIndirectCount))"""
    assertParseAndVerify(registry, 'vkCmdCopyImage', vu, 'copies.adoc')

    # Feature from extensions
    vu = """require(is_feature_enabled(cooperativeMatrix) and is_feature_enabled(shaderSubgroupClock))"""
    assertParseAndVerify(registry, 'vkCmdCopyImage', vu, 'copies.adoc')

def test_negative_features(registry):
    """Test that misspelled features are caught."""

    # Misspelled
    vu = """require(is_feature_enabled(fragmentShaderSampleInterloc))"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

    # Used outside `is_feature_enabled`
    vu = """require(fragmentShaderSampleInterlock == VK_TRUE)"""
    assertParseFailVerify(registry, 'VkSubpassDescription2', vu, 'renderpass.adoc')

def test_variable_scope(registry):
    """Test variable scoping."""

    # Basic check
    vu = """variable = 0
if flags.any():
             require(variable == 0)"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Declaration in outer scope after inner scope ends
    vu = """if flags.any():
                variable = 0
                require(variable == 0)
variable = 1
require(variable == 1)
"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Declaration in both true and false blocks of if
    vu = """if flags.any():
                variable = 0
                require(variable == 0)
else:
 variable = 1
 require(variable == 1)
"""
    assertParseAndVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_negative_variable_scope(registry):
    """Test that variables out of scope are not used."""

    # Use before declaration
    vu = """require(variable == 0)
variable = 1"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Use after out of scope
    vu = """if flags.any():
                variable = 0
                require(variable == 0)
require(variable == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Use in else after declaring in if
    vu = """if flags.any():
                variable = 0
                require(variable == 0)
else:
  require(variable == 0)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

def test_immutable_variables(registry):
    """Test that mutating variables are not allowed."""

    # Basic check
    vu = """variable = 0
variable = 1
require(variable == 1)"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Modification in loop
    vu = """variable = 0
if variable == 0:
  variable += 1
  require(variable == 1)
"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Loop variable shadowing another
    vu = """variable = 0
for variable in pSubpasses:
  require(variable.flags.none())
"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

    # Variable shadowing loop variable
    vu = """for variable in pSubpasses:
  variable = pSubpasses[0]
  require(variable.flags.none())
"""
    assertParseFailVerify(registry, 'VkRenderPassCreateInfo2', vu, 'renderpass.adoc')

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

def test_get_tag_macro_after_symbol():
    """Test extracting tag from a macro."""

    vu = """for range in pRanges:
 require(range.baseMipLevel < macro(imageparam).create_info().mipLevels)
"""
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

def test_get_tag_no_feature():
    """Test extracting tag from a VU that includes a feature check."""

    vu = """if is_feature_enabled(fragmentDensityMapDeferred):
              require(pCreateInfos != NULL)"""
    assertParseAndGetTag(vu, 'pipelines.adoc', 444, 'pCreateInfos')
