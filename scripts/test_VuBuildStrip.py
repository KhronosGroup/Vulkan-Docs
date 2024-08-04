#!/usr/bin/env python3 -i
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import os
import pytest
from pathlib import Path

from reg import Registry
from vuAST import VuAST, VuFormatter, VuSourceStyler, createAliasMap, createSymbolAvailabilityMap, grepTag
from vubuildstrip import stripVUForBuild


@pytest.fixture
def registry():
    registryFile = os.path.join(Path(__file__).resolve().parent.parent, 'xml', 'vk.xml')
    registry = Registry()
    registry.loadFile(registryFile)
    return registry

def verify(registry, api, versions, extensions, vuText, macros, expectText):
    aliasMap = createAliasMap(registry)
    featureAvailability, structAvailability, enumAvailability = createSymbolAvailabilityMap(registry, aliasMap)

    # Parse and verify the VU first
    vu = VuAST()
    vuText = grepTag + '\n' + vuText
    expectText = grepTag + '\n' + expectText if expectText else None
    assert(vu.parse(vuText, 'test.adoc', 100))
    assert(vu.applyMacros(macros))
    assert(vu.verify(registry, api))

    # Strip for build
    stripped = stripVUForBuild(vu, versions, extensions, featureAvailability, structAvailability, enumAvailability)

    # Format the result and verify against expectation
    if expectText is None:
        assert(stripped is None)
    else:
        assert(stripped is not None)
        formatter = VuFormatter(VuSourceStyler('test.adoc', 100))
        assert(formatter.format(stripped) == expectText)

def test_no_strip(registry):
    """Test when there is nothing to strip."""

    vu = """if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM):
               for subpass in pSubpasses:
                   shading_rate_attachment = subpass.pnext(VkFragmentShadingRateAttachmentInfoKHR).pFragmentShadingRateAttachment
                   if shading_rate_attachment != NULL:
                     require(shading_rate_attachment.attachment == VK_ATTACHMENT_UNUSED)
else:
                subpass = pSubpasses[0 if flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM) else 0]
                if subpass.viewMask > 3:
                 count = subpass.inputAttachmentCount + subpass.colorAttachmentCount + 1
                 require(count != subpass.preserveAttachmentCount and count == subpass.preserveAttachmentCount)
              """
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

    verify(registry, 'VkRenderPassCreateInfo2', ['VK_VERSION_1_0'], ['VK_QCOM_render_pass_transform'], vu, {}, expect)

def test_stripped_condition_in_if(registry):
    """Test when a condition in if is True/False."""

    vu = """if is_ext_enabled(VK_KHR_depth_stencil_resolve):
              require(pCreateInfo != NULL)"""
    expect = None
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """if is_ext_enabled(VK_KHR_depth_stencil_resolve):
              require(pCreateInfo != NULL)
require(pCreateInfo == NULL)"""
    expect = """require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """if is_feature_enabled(descriptorBuffer):
              require(pCreateInfo != NULL)
else:
              require(pCreateInfo == NULL)"""
    expect = """require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """if not is_feature_enabled(descriptorBuffer) and is_version(1, 0):
              require(pCreateInfo != NULL)
require(pCreateInfo == NULL)"""
    expect = """require(pCreateInfo != NULL)
require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """if not is_version(1, 1):
              require(pCreateInfo != NULL)
else:
              require(pCreateInfo == NULL)"""
    expect = """require(pCreateInfo != NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    # Test nested: stripped if is at the beginning of the parent block, condition is true
    vu = """if device.valid():
              if not is_feature_enabled(descriptorBuffer):
                require(pCreateInfo != NULL)
              allocator = pAllocator
              require(allocator != NULL)
require(pCreateInfo == NULL)"""
    expect = """if device.valid():
  require(pCreateInfo != NULL)
  allocator = pAllocator
  require(allocator != NULL)
require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    # Test nested: stripped if is in the middle of the parent block, condition is true
    vu = """if device.valid():
              allocator = pAllocator
              if not is_feature_enabled(descriptorBuffer):
                require(pCreateInfo != NULL)
              require(allocator != NULL)
require(pCreateInfo == NULL)"""
    expect = """if device.valid():
  allocator = pAllocator
  require(pCreateInfo != NULL)
  require(allocator != NULL)
require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    # Test nested: stripped if is at the end of the parent block, condition is true
    vu = """if device.valid():
              allocator = pAllocator
              require(allocator != NULL)
              if not is_feature_enabled(descriptorBuffer):
                require(pCreateInfo != NULL)
require(pCreateInfo == NULL)"""
    expect = """if device.valid():
  allocator = pAllocator
  require(allocator != NULL)
  require(pCreateInfo != NULL)
require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    # Test nested: stripped if is at the beginning of the parent block, condition is false
    vu = """if device.valid():
              if is_feature_enabled(descriptorBuffer):
                require(pCreateInfo != NULL)
              allocator = pAllocator
              require(allocator != NULL)
require(pCreateInfo == NULL)"""
    expect = """if device.valid():
  allocator = pAllocator
  require(allocator != NULL)
require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    # Test nested: stripped if is in the middle of the parent block, condition is false
    vu = """if device.valid():
              allocator = pAllocator
              if is_feature_enabled(descriptorBuffer):
                require(pCreateInfo != NULL)
              require(allocator != NULL)
require(pCreateInfo == NULL)"""
    expect = """if device.valid():
  allocator = pAllocator
  require(allocator != NULL)
require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    # Test nested: stripped if is at the end of the parent block, condition is false
    vu = """if device.valid():
              allocator = pAllocator
              require(allocator != NULL)
              if is_feature_enabled(descriptorBuffer):
                require(pCreateInfo != NULL)
require(pCreateInfo == NULL)"""
    expect = """if device.valid():
  allocator = pAllocator
  require(allocator != NULL)
require(pCreateInfo == NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

def test_stripped_variables(registry):
    """Test when a variable is stripped when deemed unused."""

    # Basic removal of unused variables.
    vu = """unused = pAllocator.pfnAllocation
if pCreateInfo != NULL:
  unused2 = pCreateInfo.flags.any()
  for subpass in pCreateInfo.pSubpasses:
    unused3 = pCreateInfo.pSubpasses[0].inputAttachmentCount + pCreateInfo.pSubpasses[0].colorAttachmentCount
    require(subpass.viewMask == 0)"""
    expect = """if pCreateInfo != NULL:
  for subpass in pCreateInfo.pSubpasses:
    require(subpass.viewMask == 0)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    # Removal of a chain of unused variables
    vu = """unused = pAllocator.pfnAllocation
if pCreateInfo != NULL:
  unused2 = pCreateInfo.flags.any() and unused != NULL
  for subpass in pCreateInfo.pSubpasses:
    unused3 = pCreateInfo.pSubpasses[0].inputAttachmentCount + pCreateInfo.pSubpasses[0].colorAttachmentCount + (1 if unused2 else 0)
    unused4 = unused3 == 0 or unused2 or unused == NULL
    require(subpass.viewMask == 0)"""
    expect = """if pCreateInfo != NULL:
  for subpass in pCreateInfo.pSubpasses:
    require(subpass.viewMask == 0)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    # Removal of a partial chain of unused variables
    vu = """allocator = pAllocator.pfnAllocation
if pCreateInfo != NULL:
  condition = pCreateInfo.flags.any() and allocator != NULL
  for subpass in pCreateInfo.pSubpasses:
    unused = pCreateInfo.pSubpasses[0].inputAttachmentCount + pCreateInfo.pSubpasses[0].colorAttachmentCount + (1 if condition else 0)
    if condition:
      unused2 = unused == 0 or condition or allocator == NULL
      require(condition)
    else:
      require(subpass.viewMask == 0)"""
    expect = """allocator = pAllocator.pfnAllocation
if pCreateInfo != NULL:
  condition = (pCreateInfo.flags.any() and
      allocator != NULL)
  for subpass in pCreateInfo.pSubpasses:
    if condition:
      require(condition)
    else:
      require(subpass.viewMask == 0)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    # Removal of unused variables after their use is stripped
    vu = """unused = regionCount + srcImage.create_info().mipLevels
if is_version(1, 2):
  unused2 = unused != 0
  require(dstImage.valid())
else:
  unused3 = dstImageLayout != VK_IMAGE_LAYOUT_UNDEFINED
  for region in pRegions:
    require(unused3 and region.srcOffset.x > unused)"""
    expect = """require(dstImage.valid())"""
    verify(registry, 'VkCopyImageInfo2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'], [], vu, {}, expect)

def test_stripped_version(registry):
    """Test when condition is stripped based on a version that is not supported."""

    vu = """unused = pAllocator.pfnAllocation
if pCreateInfo != NULL and is_version(1, 1):
  require(unused != NULL)
require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    expect = """require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """allocator = pAllocator.pfnAllocation
if pCreateInfo != NULL or is_version(1, 1):
  require(allocator != NULL)
require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    expect = """allocator = pAllocator.pfnAllocation
if pCreateInfo != NULL:
  require(allocator != NULL)
require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """allocator = pAllocator.pfnAllocation
if pCreateInfo != NULL or is_version(1, 1):
  require(allocator != NULL)
require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    expect = """allocator = pAllocator.pfnAllocation
require(allocator != NULL)
require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0', 'VK_VERSION_1_1'], [], vu, {}, expect)

    vu = """unused = pAllocator.pfnAllocation
if is_version(1, 3):
  require(unused != NULL)
require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    expect = """require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], [], vu, {}, expect)

    vu = """allocator = pAllocator.pfnAllocation
if is_version(1, 3):
  require(allocator != NULL)
require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    expect = """allocator = pAllocator.pfnAllocation
require(allocator != NULL)
require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'], [], vu, {}, expect)

    vu = """unused = pAllocator.pfnAllocation
if is_version(1, 3) and not is_version(1, 3):
  require(unused != NULL)
require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    expect = """require(pCreateInfo.pSubpasses[0].viewMask == 0)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], [], vu, {}, expect)
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'], [], vu, {}, expect)

    vu = """unused = pAllocator.pfnAllocation
if is_version(1, 3) and not is_version(1, 3):
  require(unused != NULL)"""
    expect = None
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'], [], vu, {}, expect)

def test_stripped_extension(registry):
    """Test when condition is an extension check."""

    vu = """require(is_ext_enabled(VK_EXT_host_query_reset))"""
    expect = """require(False)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """if pAllocator != NULL:
        require(is_ext_enabled(VK_EXT_host_query_reset))"""
    expect = """if pAllocator != NULL:
  require(False)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(is_ext_enabled(VK_EXT_host_query_reset))"""
    expect = """require(is_ext_enabled(VK_EXT_host_query_reset))"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], ['VK_EXT_host_query_reset'], vu, {}, expect)

    vu = """if is_ext_enabled(VK_EXT_host_query_reset):
        require(pAllocator != NULL)"""
    expect = """if is_ext_enabled(VK_EXT_host_query_reset):
  require(pAllocator != NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], ['VK_EXT_host_query_reset'], vu, {}, expect)

    vu = """require(is_ext_enabled(VK_KHR_get_physical_device_properties2) or is_ext_enabled(VK_EXT_host_query_reset))"""
    expect = """require(is_ext_enabled(VK_EXT_host_query_reset))"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'],
           ['VK_EXT_line_rasterization', 'VK_EXT_host_query_reset', 'VK_KHR_buffer_device_address'], vu, {}, expect)

    vu = """if is_ext_enabled(VK_EXT_host_query_reset) and is_ext_enabled(VK_KHR_get_physical_device_properties2):
        require(pAllocator != NULL)"""
    expect = """if (is_ext_enabled(VK_EXT_host_query_reset) and
    is_ext_enabled(VK_KHR_get_physical_device_properties2)):
  require(pAllocator != NULL)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'],
           ['VK_EXT_line_rasterization', 'VK_EXT_host_query_reset', 'VK_KHR_buffer_device_address', 'VK_KHR_get_physical_device_properties2'], vu, {}, expect)

    vu = """has_the_right_exts = is_ext_enabled(VK_EXT_host_query_reset) or is_ext_enabled(VK_KHR_get_physical_device_properties2)
if has_the_right_exts:
  require(pAllocator != NULL)"""
    expect = """has_the_right_exts = (is_ext_enabled(VK_EXT_host_query_reset) or
    is_ext_enabled(VK_KHR_get_physical_device_properties2))
if has_the_right_exts:
  require(pAllocator != NULL)"""
    # Note: since asciidoctor turns the extension names to lower case, the following also makes sure the checks are case-insensitive
    verify(registry, 'vkCreateRenderPass2', ['vk_version_1_0'],
           ['vk_ext_line_rasterization', 'vk_ext_host_query_reset', 'vk_khr_buffer_device_address', 'vk_khr_get_physical_device_properties2'], vu, {}, expect)

    vu = """has_the_right_exts = is_ext_enabled(VK_EXT_host_query_reset) or is_ext_enabled(VK_KHR_get_physical_device_properties2)
if has_the_right_exts:
  require(pAllocator != NULL)"""
    expect = None
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

def test_stripped_features(registry):
    """Test when condition is a feature check."""

    vu = """require(is_feature_enabled(hostQueryReset))"""
    expect = """require(False)"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(is_feature_enabled(hostQueryReset))"""
    expect = """require(is_feature_enabled(hostQueryReset))"""
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0'], ['VK_EXT_host_query_reset'], vu, {}, expect)
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], [], vu, {}, expect)
    verify(registry, 'vkCreateRenderPass2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], ['VK_EXT_host_query_reset'], vu, {}, expect)

    vu = """has_eds2 = is_feature_enabled(extendedDynamicState2)
if has_eds2:
  require(is_feature_enabled(extendedDynamicState))"""
    expect = None
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0'], ['VK_EXT_host_query_reset'], vu, {}, expect)
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'],
           ['VK_EXT_host_query_reset', 'VK_EXT_extended_dynamic_state'], vu, {}, expect)

    vu = """has_eds2 = is_feature_enabled(extendedDynamicState2)
if has_eds2:
  require(is_feature_enabled(extendedDynamicState))"""
    expect = """has_eds2 = is_feature_enabled(extendedDynamicState2)
if has_eds2:
  require(False)"""
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0'], ['VK_EXT_host_query_reset', 'VK_EXT_extended_dynamic_state2'], vu, {}, expect)

    vu = """has_eds2 = is_feature_enabled(extendedDynamicState2)
if has_eds2:
  require(is_feature_enabled(extendedDynamicState))"""
    expect = """has_eds2 = is_feature_enabled(extendedDynamicState2)
if has_eds2:
  require(is_feature_enabled(extendedDynamicState))"""
    # Note: since asciidoctor turns the extension names to lower case, the following also makes sure the checks are case-insensitive
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'],
           ['vk_ext_host_query_reset', 'vk_ext_extended_dynamic_state', 'vk_ext_extended_dynamic_state2'], vu, {}, expect)

    vu = """require(not is_feature_enabled(shaderDrawParameters))"""
    expect = None
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(not is_feature_enabled(shaderDrawParameters))"""
    expect = """require(not is_feature_enabled(shaderDrawParameters))"""
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0', 'VK_VERSION_1_1'], [], vu, {}, expect)
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0', 'VK_VERSION_1_2'], [], vu, {}, expect)
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], [], vu, {}, expect)

def test_stripped_struct(registry):
    """Test when condition is a pnext check."""

    vu = """require(has_pnext(VkBufferUsageFlags2CreateInfoKHR))"""
    expect = """require(False)"""
    verify(registry, 'VkBufferViewCreateInfo', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(has_pnext(VkBufferUsageFlags2CreateInfoKHR))"""
    expect = """require(has_pnext(VkBufferUsageFlags2CreateInfoKHR))"""
    verify(registry, 'VkBufferViewCreateInfo', ['VK_VERSION_1_0'], ['VK_KHR_maintenance5'], vu, {}, expect)

    vu = """require(pCreateInfo.has_pnext(VkBufferUsageFlags2CreateInfoKHR))"""
    expect = """require(False)"""
    verify(registry, 'vkCreateBufferView', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(pCreateInfo.has_pnext(VkBufferUsageFlags2CreateInfoKHR))"""
    expect = """require(pCreateInfo.has_pnext(VkBufferUsageFlags2CreateInfoKHR))"""
    verify(registry, 'vkCreateBufferView', ['VK_VERSION_1_0'], ['VK_KHR_maintenance5'], vu, {}, expect)

    vu = """for bindInfo in pBindInfos:
              # Check for device group info
              if bindInfo.has_pnext(VkBindImageMemoryDeviceGroupInfo):
                  require(bindInfo.has_pnext(VkBindImageMemorySwapchainInfoKHR))"""
    expect = """for bindInfo in pBindInfos:
  # Check for device group info
  if bindInfo.has_pnext(VkBindImageMemoryDeviceGroupInfo):
    require(False)"""
    verify(registry, 'vkBindImageMemory2', ['VK_VERSION_1_0'],
           ['VK_KHR_device_group', 'VK_KHR_bind_memory2'], vu, {}, expect)
    verify(registry, 'vkBindImageMemory2', ['VK_VERSION_1_1'], [], vu, {}, expect)

    expect = """for bindInfo in pBindInfos:
  # Check for device group info
  if bindInfo.has_pnext(VkBindImageMemoryDeviceGroupInfo):
    require(bindInfo.has_pnext(VkBindImageMemorySwapchainInfoKHR))"""
    verify(registry, 'vkBindImageMemory2', ['VK_VERSION_1_0'],
           ['VK_KHR_device_group', 'VK_KHR_bind_memory2', 'VK_KHR_swapchain'], vu, {}, expect)

    vu = """if (has_pnext(VkPipelineFragmentShadingRateStateCreateInfoKHR) or
                has_pnext(VkPipelineRenderingCreateInfo)):
              require(has_pnext(VkPipelineCreationFeedbackCreateInfo))
              require(has_pnext(VkPipelineRepresentativeFragmentTestStateCreateInfoNV))"""
    expect = None
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_0'], [], vu, {}, expect)
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'], [], vu, {}, expect)
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], [], vu, {}, expect)
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'],
           ['VK_EXT_pipeline_creation_feedback', 'VK_NV_representative_fragment_test'], vu, {}, expect)

    expect = """if has_pnext(VkPipelineFragmentShadingRateStateCreateInfoKHR):
  require(False)
  require(False)"""
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_0'], ['VK_KHR_fragment_shading_rate'], vu, {}, expect)

    expect = """if has_pnext(VkPipelineRenderingCreateInfo):
  require(False)
  require(False)"""
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_0'], ['VK_KHR_dynamic_rendering'], vu, {}, expect)

    expect = """if (has_pnext(VkPipelineFragmentShadingRateStateCreateInfoKHR) or
    has_pnext(VkPipelineRenderingCreateInfo)):
  require(False)
  require(False)"""
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_0'],
           ['VK_KHR_dynamic_rendering', 'VK_KHR_fragment_shading_rate'], vu, {}, expect)

    expect = """if has_pnext(VkPipelineRenderingCreateInfo):
  require(has_pnext(VkPipelineCreationFeedbackCreateInfo))
  require(False)"""
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_0'],
           ['VK_KHR_dynamic_rendering', 'VK_EXT_pipeline_creation_feedback'], vu, {}, expect)
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_3'], [], vu, {}, expect)

    expect = """if has_pnext(VkPipelineRenderingCreateInfo):
  require(has_pnext(VkPipelineCreationFeedbackCreateInfo))
  require(has_pnext(VkPipelineRepresentativeFragmentTestStateCreateInfoNV))"""
    verify(registry, 'VkGraphicsPipelineCreateInfo', ['VK_VERSION_1_3'], ['VK_NV_representative_fragment_test'], vu, {}, expect)

def test_stripped_enum(registry):
    """Test when condition is an enum equality or has_bit check."""

    vu = """require(srcImageLayout == VK_IMAGE_LAYOUT_GENERAL)"""
    expect = """require(srcImageLayout == VK_IMAGE_LAYOUT_GENERAL)"""
    verify(registry, 'vkCmdCopyImage', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(VK_IMAGE_LAYOUT_GENERAL != srcImageLayout)"""
    expect = """require(VK_IMAGE_LAYOUT_GENERAL != srcImageLayout)"""
    verify(registry, 'vkCmdCopyImage', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(imageLayout == VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL or
        imageLayout == VK_IMAGE_LAYOUT_GENERAL or
        imageLayout == VK_IMAGE_LAYOUT_SHARED_PRESENT_KHR)"""
    expect = """require(imageLayout == VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL or
    imageLayout == VK_IMAGE_LAYOUT_GENERAL)"""
    verify(registry, 'vkCmdClearColorImage', ['VK_VERSION_1_0'], [], vu, {}, expect)

    expect = """require(imageLayout == VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL or
    imageLayout == VK_IMAGE_LAYOUT_GENERAL or
    imageLayout == VK_IMAGE_LAYOUT_SHARED_PRESENT_KHR)"""
    verify(registry, 'vkCmdClearColorImage', ['VK_VERSION_1_0'], ['VK_KHR_shared_presentable_image'], vu, {}, expect)

    vu = """for attachment in pAttachments:
              if attachment.storeOp != VK_ATTACHMENT_STORE_OP_NONE_QCOM:
                  require(attachment.loadOp == VK_ATTACHMENT_LOAD_OP_LOAD or
                          attachment.loadOp == VK_ATTACHMENT_LOAD_OP_NONE_EXT)"""
    expect = """for attachment in pAttachments:
  require(attachment.loadOp == VK_ATTACHMENT_LOAD_OP_LOAD)"""
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0'], [], vu, {}, expect)

    expect = """for attachment in pAttachments:
  if attachment.storeOp != VK_ATTACHMENT_STORE_OP_NONE_QCOM:
    require(attachment.loadOp == VK_ATTACHMENT_LOAD_OP_LOAD)"""
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'],
           ['VK_QCOM_render_pass_store_ops'], vu, {}, expect)
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'],
           ['VK_KHR_dynamic_rendering'], vu, {}, expect)
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'], [], vu, {}, expect)

    expect = """for attachment in pAttachments:
  if attachment.storeOp != VK_ATTACHMENT_STORE_OP_NONE_QCOM:
    require(attachment.loadOp == VK_ATTACHMENT_LOAD_OP_LOAD or
        attachment.loadOp == VK_ATTACHMENT_LOAD_OP_NONE_EXT)"""
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'],
           ['VK_EXT_load_store_op_none'], vu, {}, expect)
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'],
           ['VK_EXT_load_store_op_none'], vu, {}, expect)

    vu = """if has_pnext(VkBufferUsageFlags2CreateInfoKHR):
              usage = pnext(VkBufferUsageFlags2CreateInfoKHR).usage
              if usage.has_bit(VK_BUFFER_USAGE_2_SHADER_DEVICE_ADDRESS_BIT_KHR):
                require(usage.has_bit(VK_BUFFER_USAGE_2_ACCELERATION_STRUCTURE_BUILD_INPUT_READ_ONLY_BIT_KHR))"""
    expect = None
    verify(registry, 'VkBufferViewCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'], [], vu, {}, expect)
    verify(registry, 'VkBufferViewCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'],
           ['VK_KHR_maintenance5'], vu, {}, expect)
    verify(registry, 'VkBufferViewCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'],
           ['VK_KHR_acceleration_structure'], vu, {}, expect)
    verify(registry, 'VkBufferViewCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'],
           ['VK_KHR_maintenance5', 'VK_KHR_acceleration_structure'], vu, {}, expect)

    expect = """if has_pnext(VkBufferUsageFlags2CreateInfoKHR):
  usage = pnext(VkBufferUsageFlags2CreateInfoKHR).usage
  if usage.has_bit(VK_BUFFER_USAGE_2_SHADER_DEVICE_ADDRESS_BIT_KHR):
    require(False)"""
    verify(registry, 'VkBufferViewCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'],
           ['VK_KHR_maintenance5', 'VK_KHR_buffer_device_address'], vu, {}, expect)
    verify(registry, 'VkBufferViewCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1'],
           ['VK_KHR_maintenance5', 'VK_EXT_buffer_device_address'], vu, {}, expect)
    verify(registry, 'VkBufferViewCreateInfo', ['vk_version_1_0', 'vk_version_1_1', 'vk_version_1_2'],
           ['vk_khr_maintenance5'], vu, {}, expect)

    expect = """if has_pnext(VkBufferUsageFlags2CreateInfoKHR):
  usage = pnext(VkBufferUsageFlags2CreateInfoKHR).usage
  if usage.has_bit(VK_BUFFER_USAGE_2_SHADER_DEVICE_ADDRESS_BIT_KHR):
    require(usage.has_bit(VK_BUFFER_USAGE_2_ACCELERATION_STRUCTURE_BUILD_INPUT_READ_ONLY_BIT_KHR))"""
    verify(registry, 'VkBufferViewCreateInfo', ['vk_version_1_0', 'vk_version_1_1', 'vk_version_1_2'],
           ['vk_khr_maintenance5', 'VK_KHR_acceleration_structure'], vu, {}, expect)

def test_stripped_not(registry):
    """Test when `not` is involved."""

    vu = """require(not not is_feature_enabled(shaderDrawParameters))"""
    expect = """require(False)"""
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(not not is_feature_enabled(shaderDrawParameters))"""
    expect = """require(is_feature_enabled(shaderDrawParameters))"""
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0', 'VK_VERSION_1_1'], [], vu, {}, expect)
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0', 'VK_VERSION_1_2'], [], vu, {}, expect)
    verify(registry, 'vkCmdDraw', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], [], vu, {}, expect)

    vu = """require(not (is_feature_enabled(shaderDrawParameters) or not flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM)))"""
    expect = """require(flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM))"""
    verify(registry, 'VkRenderPassCreateInfo2', ['VK_VERSION_1_0'], ['VK_QCOM_render_pass_transform'], vu, {}, expect)
    expect = """require(False)"""
    verify(registry, 'VkRenderPassCreateInfo2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(not (not flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM) or is_feature_enabled(shaderDrawParameters)))"""
    expect = """require(flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM))"""
    verify(registry, 'VkRenderPassCreateInfo2', ['VK_VERSION_1_0'], ['VK_QCOM_render_pass_transform'], vu, {}, expect)
    expect = """require(False)"""
    verify(registry, 'VkRenderPassCreateInfo2', ['VK_VERSION_1_0'], [], vu, {}, expect)

    vu = """require(not (is_feature_enabled(shaderDrawParameters) or not flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM)))"""
    expect = """require(not (is_feature_enabled(shaderDrawParameters) or
        not flags.has_bit(VK_RENDER_PASS_CREATE_TRANSFORM_BIT_QCOM)))"""
    verify(registry, 'VkRenderPassCreateInfo2', ['VK_VERSION_1_0', 'VK_VERSION_1_1'],
           ['VK_QCOM_render_pass_transform'], vu, {}, expect)
    verify(registry, 'VkRenderPassCreateInfo2', ['VK_VERSION_1_0', 'VK_VERSION_1_2'],
           ['VK_QCOM_render_pass_transform'], vu, {}, expect)
    verify(registry, 'VkRenderPassCreateInfo2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'],
           ['VK_QCOM_render_pass_transform'], vu, {}, expect)
    expect = """require(False)"""
    verify(registry, 'VkRenderPassCreateInfo2', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], [], vu, {}, expect)

def test_stripped_extension_feature_aliases(registry):
    """Test when feature check should be replaced with extension check in older core versions."""

    vu = """if is_feature_enabled(shaderDrawParameters) or is_feature_enabled(drawIndirectCount):
  require(attachmentCount > 0)
if ((is_feature_enabled(samplerMirrorClampToEdge) and not is_feature_enabled(descriptorIndexing)) or
    is_feature_enabled(samplerFilterMinmax)):
  require(subpassCount > 0)
for dependency in pDependencies:
  if not is_feature_enabled(shaderOutputViewportIndex):
    require(dependency.srcStageMask.has_bit(VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT))
  if is_feature_enabled(shaderOutputLayer):
    require(dependency.dstStageMask.has_bit(VK_PIPELINE_STAGE_VERTEX_INPUT_BIT))"""

    expect = """if (is_feature_enabled(shaderDrawParameters) or
    is_feature_enabled(drawIndirectCount)):
  require(attachmentCount > 0)
if ((is_feature_enabled(samplerMirrorClampToEdge) and
        not is_feature_enabled(descriptorIndexing)) or
    is_feature_enabled(samplerFilterMinmax)):
  require(subpassCount > 0)
for dependency in pDependencies:
  if not is_feature_enabled(shaderOutputViewportIndex):
    require(dependency.srcStageMask.has_bit(VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT))
  if is_feature_enabled(shaderOutputLayer):
    require(dependency.dstStageMask.has_bit(VK_PIPELINE_STAGE_VERTEX_INPUT_BIT))"""
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], [], vu, {}, expect)

    # Check that is_feature_enabled turns to is_ext_enabled for all these features when the ext is built
    expect = """if (is_ext_enabled(VK_KHR_shader_draw_parameters) or
    is_ext_enabled(VK_KHR_draw_indirect_count)):
  require(attachmentCount > 0)
if ((is_ext_enabled(VK_KHR_sampler_mirror_clamp_to_edge) and
        not is_ext_enabled(VK_EXT_descriptor_indexing)) or
    is_ext_enabled(VK_EXT_sampler_filter_minmax)):
  require(subpassCount > 0)
for dependency in pDependencies:
  if not is_ext_enabled(VK_EXT_shader_viewport_index_layer):
    require(dependency.srcStageMask.has_bit(VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT))
  if is_ext_enabled(VK_EXT_shader_viewport_index_layer):
    require(dependency.dstStageMask.has_bit(VK_PIPELINE_STAGE_VERTEX_INPUT_BIT))"""
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0'],
           ['VK_KHR_shader_draw_parameters', 'VK_KHR_draw_indirect_count',
            'VK_KHR_sampler_mirror_clamp_to_edge',
            'VK_EXT_descriptor_indexing', 'VK_EXT_sampler_filter_minmax',
            'VK_EXT_shader_viewport_index_layer'], vu, {}, expect)

    # Check that is_feature_enabled turns to is_ext_enabled for all these features, but also gets const-folded if the extension is not being built
    expect = """if is_ext_enabled(VK_KHR_draw_indirect_count):
  require(attachmentCount > 0)
if (is_ext_enabled(VK_KHR_sampler_mirror_clamp_to_edge) or
    is_ext_enabled(VK_EXT_sampler_filter_minmax)):
  require(subpassCount > 0)
for dependency in pDependencies:
  if not is_ext_enabled(VK_EXT_shader_viewport_index_layer):
    require(dependency.srcStageMask.has_bit(VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT))
  if is_ext_enabled(VK_EXT_shader_viewport_index_layer):
    require(dependency.dstStageMask.has_bit(VK_PIPELINE_STAGE_VERTEX_INPUT_BIT))"""
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0'],
           ['VK_KHR_draw_indirect_count',
            'VK_KHR_sampler_mirror_clamp_to_edge',
            'VK_EXT_sampler_filter_minmax',
            'VK_EXT_shader_viewport_index_layer'], vu, {}, expect)

    expect = """if is_ext_enabled(VK_EXT_sampler_filter_minmax):
  require(subpassCount > 0)
for dependency in pDependencies:
  if not is_ext_enabled(VK_EXT_shader_viewport_index_layer):
    require(dependency.srcStageMask.has_bit(VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT))
  if is_ext_enabled(VK_EXT_shader_viewport_index_layer):
    require(dependency.dstStageMask.has_bit(VK_PIPELINE_STAGE_VERTEX_INPUT_BIT))"""
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0'],
           ['VK_EXT_sampler_filter_minmax',
            'VK_EXT_shader_viewport_index_layer'], vu, {}, expect)

    expect = """for dependency in pDependencies:
  require(dependency.srcStageMask.has_bit(VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT))"""
    verify(registry, 'VkRenderPassCreateInfo', ['VK_VERSION_1_0'], [], vu, {}, expect)
