#!/usr/bin/env python3 -i
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import os
import pytest
from pathlib import Path

from reg import Registry
from vupreprocessor import processVersionsCommand, processFormatCommand
from vuAST import createAliasMap, createSymbolAvailabilityMap


@pytest.fixture
def registry():
    registryFile = os.path.join(Path(__file__).resolve().parent.parent, 'xml', 'vk.xml')
    registry = Registry()
    registry.loadFile(registryFile)
    return registry

def verify_versions(registry, command, expectedVersions, expectedExtensions):
    response, versions, extensions = processVersionsCommand(command.splitlines(), registry)
    assert(response == ['VERSIONS-SUCCESS'])
    assert(versions == versions)
    assert(extensions == extensions)

def verify_format(registry, versions, extensions, command, expectedResponse):
    aliasMap = createAliasMap(registry)
    featureAvailability, structAvailability, enumAvailability = createSymbolAvailabilityMap(registry, aliasMap)

    response = processFormatCommand(command.splitlines(), registry, versions, extensions,
                                    featureAvailability, structAvailability, enumAvailability)
    response = '\n'.join(response)
    assert(response == expectedResponse)

def test_versions(registry):
    """Test that versions and extensions are parsed correctly."""

    command = """1.0

"""
    verify_versions(registry, command, ['VK_VERSION_1_0'], [])

    command = """1.0 1.1
VK_KHR_maintenance1 VK_EXT_dynamic_rendering"""
    verify_versions(registry, command, ['VK_VERSION_1_0', 'VK_VERSION_1_1'], ['VK_KHR_maintenance1', 'VK_EXT_dynamic_rendering'])

def test_format_fail(registry):
    """Test when the VU fails to build."""

    command = """VkSubpassDescriptionDepthStencilResolveKHR
enderpass.adoc
123

codified-vu
if depthResolveMode == VK_RESOLVE_MODE_MAX_BIT:
    require(stencilResolveMode.has_bit(VK_RESOLVE_MODE_MAX_BIT))"""
    expect = """FORMAT-VU
codified-vu
if depthResolveMode == VK_RESOLVE_MODE_MAX_BIT:
    require(stencilResolveMode.has_bit(VK_RESOLVE_MODE_MAX_BIT))
FORMAT-VU-FAIL"""

    verify_format(registry, ['VK_VERSION_1_0'], ['VK_KHR_depth_stencil_resolve'], command, expect)

def test_format_fail_with_macros(registry):
    """Test when the VU fails to build, including macros."""

    command = """VkSubpassDescriptionDepthStencilResolveKHR
enderpass.adoc
123
dmode$depthResolveMode$smode$stencilResolveMode
codified-vu
if macro(dmode) == VK_RESOLVE_MODE_MAX_BIT:
    require(macro(smode).has_bit(VK_RESOLVE_MODE_MAX_BIT))"""
    expect = """FORMAT-VU
codified-vu
if macro(dmode) == VK_RESOLVE_MODE_MAX_BIT:
    require(macro(smode).has_bit(VK_RESOLVE_MODE_MAX_BIT))
FORMAT-VU-FAIL"""

    verify_format(registry, ['VK_VERSION_1_0'], ['VK_KHR_depth_stencil_resolve'], command, expect)

def test_format_success(registry):
    """Test when the VU succeeds to build."""

    command = """VkSubpassDescriptionDepthStencilResolveKHR
enderpass.adoc
123

codified-vu
if depthResolveMode == VK_RESOLVE_MODE_MAX_BIT:
    require(stencilResolveMode == VK_RESOLVE_MODE_MAX_BIT)"""
    expect = """FORMAT-VU
[vu]#[vu-keyword]##if## depthResolveMode [vu-operator]##==## ename:VK_RESOLVE_MODE_MAX_BIT: +
&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-require,require>>##&lpar;stencilResolveMode [vu-operator]##==## ename:VK_RESOLVE_MODE_MAX_BIT&rpar;#
FORMAT-VU-TEXT
* if the following is true:
** pname:depthResolveMode is equal to ename:VK_RESOLVE_MODE_MAX_BIT
* then:
** pname:stencilResolveMode must: be equal to ename:VK_RESOLVE_MODE_MAX_BIT
FORMAT-VU-SUCCESS"""

    verify_format(registry, ['VK_VERSION_1_0'], ['VK_KHR_depth_stencil_resolve'], command, expect)

def test_format_success_with_macros(registry):
    """Test when the VU succeeds to build, including macros."""

    command = """VkSubpassDescriptionDepthStencilResolveKHR
enderpass.adoc
123
dmode$depthResolveMode$smode$stencilResolveMode
codified-vu
if macro(dmode) == VK_RESOLVE_MODE_MAX_BIT:
    require(macro(smode) == VK_RESOLVE_MODE_MAX_BIT)"""
    expect = """FORMAT-VU
[vu]#[vu-keyword]##if## depthResolveMode [vu-operator]##==## ename:VK_RESOLVE_MODE_MAX_BIT: +
&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-require,require>>##&lpar;stencilResolveMode [vu-operator]##==## ename:VK_RESOLVE_MODE_MAX_BIT&rpar;#
FORMAT-VU-TEXT
* if the following is true:
** pname:depthResolveMode is equal to ename:VK_RESOLVE_MODE_MAX_BIT
* then:
** pname:stencilResolveMode must: be equal to ename:VK_RESOLVE_MODE_MAX_BIT
FORMAT-VU-SUCCESS"""

    verify_format(registry, ['VK_VERSION_1_0'], ['VK_KHR_depth_stencil_resolve'], command, expect)

def test_format_eliminated(registry):
    """Test when the VU is eliminated."""

    command = """VkSubpassDescriptionDepthStencilResolveKHR
enderpass.adoc
123

codified-vu
if is_version(1, 1) and depthResolveMode == VK_RESOLVE_MODE_MAX_BIT:
    require(stencilResolveMode == VK_RESOLVE_MODE_MAX_BIT)"""
    expect = """FORMAT-VU
FORMAT-VU-ELIMINATED"""

    verify_format(registry, ['VK_VERSION_1_0'], ['VK_KHR_depth_stencil_resolve'], command, expect)
    verify_format(registry, ['VK_VERSION_1_0', 'VK_VERSION_1_1'], [], command, expect)

    command = """VkSubpassDescriptionDepthStencilResolveKHR
enderpass.adoc
123

codified-vu
if is_version(1, 1) and depthResolveMode == VK_RESOLVE_MODE_MAX_BIT:
    require(stencilResolveMode == VK_RESOLVE_MODE_MAX_BIT)"""
    expect = """FORMAT-VU
[vu]#[vu-keyword]##if## depthResolveMode [vu-operator]##==## ename:VK_RESOLVE_MODE_MAX_BIT: +
&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-require,require>>##&lpar;stencilResolveMode [vu-operator]##==## ename:VK_RESOLVE_MODE_MAX_BIT&rpar;#
FORMAT-VU-TEXT
* if the following is true:
** pname:depthResolveMode is equal to ename:VK_RESOLVE_MODE_MAX_BIT
* then:
** pname:stencilResolveMode must: be equal to ename:VK_RESOLVE_MODE_MAX_BIT
FORMAT-VU-SUCCESS"""

    verify_format(registry, ['VK_VERSION_1_0', 'VK_VERSION_1_1'], ['VK_KHR_depth_stencil_resolve'], command, expect)
    verify_format(registry, ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2'], [], command, expect)

def test_format_eliminated_with_macros(registry):
    """Test when the VU is eliminated, including macros."""

    command = """VkSubpassDescriptionDepthStencilResolveKHR
enderpass.adoc
123
major$1$minor$1
codified-vu
if is_version(macro(major), macro(minor)) and depthResolveMode == VK_RESOLVE_MODE_MAX_BIT:
    require(stencilResolveMode == VK_RESOLVE_MODE_MAX_BIT)"""
    expect = """FORMAT-VU
FORMAT-VU-ELIMINATED"""

    verify_format(registry, ['VK_VERSION_1_0'], ['VK_KHR_depth_stencil_resolve'], command, expect)

    command = """VkSubpassDescriptionDepthStencilResolveKHR
enderpass.adoc
123
major$1$minor$1
codified-vu
if is_version(macro(major), macro(minor)) and depthResolveMode == VK_RESOLVE_MODE_MAX_BIT:
    require(stencilResolveMode == VK_RESOLVE_MODE_MAX_BIT)"""
    expect = """FORMAT-VU
[vu]#[vu-keyword]##if## depthResolveMode [vu-operator]##==## ename:VK_RESOLVE_MODE_MAX_BIT: +
&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-require,require>>##&lpar;stencilResolveMode [vu-operator]##==## ename:VK_RESOLVE_MODE_MAX_BIT&rpar;#
FORMAT-VU-TEXT
* if the following is true:
** pname:depthResolveMode is equal to ename:VK_RESOLVE_MODE_MAX_BIT
* then:
** pname:stencilResolveMode must: be equal to ename:VK_RESOLVE_MODE_MAX_BIT
FORMAT-VU-SUCCESS"""

    verify_format(registry, ['VK_VERSION_1_0', 'VK_VERSION_1_1'], ['VK_KHR_depth_stencil_resolve'], command, expect)

    command = """VkPipelineRepresentativeFragmentTestStateCreateInfoNV
enderpass.adoc
123
feature$representativeFragmentTest
codified-vu
has_feature = is_feature_enabled(macro(feature))
if has_feature:
    require(sType == VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_REPRESENTATIVE_FRAGMENT_TEST_FEATURES_NV)"""
    expect = """FORMAT-VU
FORMAT-VU-ELIMINATED"""

    verify_format(registry, ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'],
                  ['VK_NV_shader_subgroup_partitioned', 'VK_NV_compute_shader_derivatives'], command, expect)

    command = """VkPipelineRepresentativeFragmentTestStateCreateInfoNV
enderpass.adoc
123
feature$representativeFragmentTest
codified-vu
has_feature = is_feature_enabled(macro(feature))
if not has_feature:
    require(representativeFragmentTestEnable == VK_FALSE)"""
    expect = """FORMAT-VU
[vu]#[vu-predicate]##<<vu-predicate-require,require>>##&lpar;representativeFragmentTestEnable [vu-operator]##==## ename:VK_FALSE&rpar;#
FORMAT-VU-TEXT
* pname:representativeFragmentTestEnable must: be equal to ename:VK_FALSE
FORMAT-VU-SUCCESS"""

    verify_format(registry, ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'],
                  ['VK_NV_shader_subgroup_partitioned', 'VK_NV_compute_shader_derivatives'], command, expect)

    command = """VkPipelineRepresentativeFragmentTestStateCreateInfoNV
enderpass.adoc
123
feature$representativeFragmentTest
codified-vu
has_feature = is_feature_enabled(macro(feature))
if not has_feature:
    require(representativeFragmentTestEnable == VK_FALSE)"""
    expect = """FORMAT-VU
[vu]#has_feature [vu-operator]##=## [vu-predicate]##<<vu-predicate-is_feature_enabled,is_feature_enabled>>##&lpar;<<features-representativeFragmentTest,representativeFragmentTest>>&rpar; +
[vu-keyword]##if## [vu-operator]##not## has_feature: +
&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-require,require>>##&lpar;representativeFragmentTestEnable [vu-operator]##==## ename:VK_FALSE&rpar;#
FORMAT-VU-TEXT
* let pname:has_feature be the <<features-representativeFragmentTest,representativeFragmentTest>> feature is enabled
* if the following is false:
** pname:has_feature is true
* then:
** pname:representativeFragmentTestEnable must: be equal to ename:VK_FALSE
FORMAT-VU-SUCCESS"""

    verify_format(registry, ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2', 'VK_VERSION_1_3'],
                  ['VK_NV_shader_subgroup_partitioned', 'VK_NV_representative_fragment_test', 'VK_NV_compute_shader_derivatives'], command, expect)
