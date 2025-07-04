#!/usr/bin/env python3 -i
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import ast
import os
from pathlib import Path
import pytest

from reg import Registry
from vuAST import VuFormatter, VuFormat, VuSourceStyler, VuOutputStyler, retainComments


@pytest.fixture
def registry():
    registryFile = os.path.join(Path(__file__).resolve().parent.parent, 'xml', 'vk.xml')
    registry = Registry()
    registry.loadFile(registryFile)
    return registry

def verify(formatter, input, output):
    input = '\n'.join(retainComments(input.split('\n')))

    tagAndOutput = output
    if formatter.styler.grepTag is not None:
        tagAndOutput = formatter.styler.grepTag + formatter.styler.endOfLine + tagAndOutput

    assert(formatter.format(ast.parse(input)) == tagAndOutput)

def test_source_unary_op(registry):
    """Source formatting: Test unary ops."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    verify(formatter, '-1', '-1')
    verify(formatter, '- 1', '-1')
    verify(formatter, '-a', '-a')
    verify(formatter, '+1.0', '+1.0')
    verify(formatter, '~b', '~b')
    verify(formatter, 'not  a', 'not a')

    verify(formatter, '-(a+1)', '-(a + 1)')
    verify(formatter, '+(1+a)', '+(1 + a)')
    verify(formatter, '~(a|b)', '~(a | b)')
    verify(formatter, 'not (a and b)', '\n'.join(['not (a and', '    b)']))

def test_source_bool_op(registry):
    """Source formatting: Test boolean ops."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    verify(formatter, 'a and b', '\n'.join(['(a and', '    b)']))
    verify(formatter, 'a and b and c and d', '\n'.join(['(a and', '    b and', '    c and', '    d)']))
    verify(formatter, 'a or b', '\n'.join(['(a or', '    b)']))
    verify(formatter, 'a or b or c or d', '\n'.join(['(a or', '    b or', '    c or', '    d)']))

    verify(formatter, 'not a and b', '\n'.join(['(not a and', '    b)']))
    verify(formatter, 'a and not b', '\n'.join(['(a and', '    not b)']))
    verify(formatter, 'not a or b', '\n'.join(['(not a or', '    b)']))
    verify(formatter, 'a or not b', '\n'.join(['(a or', '    not b)']))

    verify(formatter, 'a == b and c != d', '\n'.join(['(a == b and', '    c != d)']))
    verify(formatter, 'a < b or c >= d', '\n'.join(['(a < b or', '    c >= d)']))
    verify(formatter, 'a <= b or c > d', '\n'.join(['(a <= b or', '    c > d)']))

    verify(formatter, 'a <= b or c > d or (x and y)', '\n'.join(['(a <= b or',
                                                                 '    c > d or',
                                                                 '    (x and',
                                                                 '        y))']))

def test_source_compare_op(registry):
    """Source formatting: Test compare ops."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    verify(formatter, 'a == b', 'a == b')
    verify(formatter, 'a != b + 1', 'a != b + 1')
    verify(formatter, 'a % 4 == b', 'a % 4 == b')
    verify(formatter, 'a-2 <= b*4', 'a - 2 <= b * 4')

    verify(formatter, '(a != b) == (not c)', '(a != b) == (not c)')
    verify(formatter, 'a == (b == c)', 'a == (b == c)')
    verify(formatter, '(a == b) != (c == d)', '(a == b) != (c == d)')

def test_source_binary_op(registry):
    """Source formatting: Test binary ops."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    verify(formatter, 'a + b', 'a + b')
    verify(formatter, 'a - b', 'a - b')
    verify(formatter, 'a * b', 'a * b')
    verify(formatter, 'a / b', 'a / b')
    verify(formatter, 'a % b', 'a % b')
    verify(formatter, 'a ** b', 'a ** b')

    verify(formatter, 'a + b + c + d', 'a + b + c + d')
    verify(formatter, 'a + b - c + d', 'a + b - c + d')
    verify(formatter, 'a - b + c', 'a - b + c')
    verify(formatter, 'a - b - c', 'a - b - c')
    verify(formatter, 'a + b * c', 'a + b * c')
    verify(formatter, 'a - b / c % d + e', 'a - b / c % d + e')
    verify(formatter, 'a * b * c / d / e % f', 'a * b * c / d / e % f')
    verify(formatter, 'a / b % c * d', 'a / b % c * d')

    verify(formatter, 'a % 2**b == -1', 'a % (2 ** b) == -1')

def test_source_assign(registry):
    """Source formatting: Test assignment."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    verify(formatter, 'a=b', 'a = b')
    verify(formatter, 'a=b+1', 'a = b + 1')
    verify(formatter, 'a = b == 2', 'a = b == 2')
    verify(formatter, 'a = f(x)', 'a = f(x)')
    verify(formatter, 'a = b[2]', 'a = b[2]')
    verify(formatter, 'a = b.f(x)', 'a = b.f(x)')

def test_source_call(registry):
    """Source formatting: Test function calls."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    verify(formatter, 'f(x)', 'f(x)')
    verify(formatter, 'f(g(x))', 'f(g(x))')
    verify(formatter, 'f(x, -y, z + 1)', 'f(x, -y, z + 1)')
    verify(formatter, '~f(x, y if a else z)', '~f(x, y if a else z)')

def test_source_subscript(registry):
    """Source formatting: Test array subscripts."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    verify(formatter, 'a[b]', 'a[b]')
    verify(formatter, 'a[b + 1]', 'a[b + 1]')
    verify(formatter, 'a.f().b[array_index(i)]', 'a.f().b[array_index(i)]')

def test_source_attribute(registry):
    """Source formatting: Test attribute selection."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    verify(formatter, 'a.b', 'a.b')
    verify(formatter, 'a.f(x)', 'a.f(x)')
    verify(formatter, 'a[2].b', 'a[2].b')
    verify(formatter, 'a[2].f(b[3], c)', 'a[2].f(b[3], c)')

def test_source_predicates(registry):
    """Source formatting: Test calling predicates."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    # function-style predicates
    verify(formatter, 'array_index(info)', 'array_index(info)')
    verify(formatter, 'require(a == b)', 'require(a == b)')
    verify(formatter, 'require(a <= b and c > d)', '\n'.join(['require(a <= b and', '    c > d)']))
    verify(formatter, 'require(a <= b and c > d and x)', '\n'.join(['require(a <= b and',
                                                                    '    c > d and',
                                                                    '    x)']))
    verify(formatter, 'require(a <= b or c > d or (x and y))', '\n'.join(['require(a <= b or',
                                                                          '    c > d or',
                                                                          '    (x and',
                                                                          '        y))']))

    # attribute-style predicates
    verify(formatter, 'info.has_pnext(other)', 'info.has_pnext(other)')
    verify(formatter, 'info.pnext(other)', 'info.pnext(other)')
    verify(formatter, 'flags.has_bit(VK_CULL_MODE_FRONT_BIT)', 'flags.has_bit(VK_CULL_MODE_FRONT_BIT)')
    verify(formatter, 'srcImage.image_type(VK_IMAGE_TYPE_1D)', 'srcImage.image_type(VK_IMAGE_TYPE_1D)')

def test_source_if(registry):
    """Source formatting: Test conditionals."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    input = '\n'.join(['if a:',
                       '    b'])
    output = '\n'.join(['if a:',
                        '  b'])
    verify(formatter, input, output)

    input = '\n'.join(['if a == b:',
                       '    c',
                       '    d'])
    output = '\n'.join(['if a == b:',
                        '  c',
                        '  d'])
    verify(formatter, input, output)

    input = '\n'.join(['if a == b and c == d and e == f:',
                       '    require(x)'])
    output = '\n'.join(['if (a == b and',
                        '    c == d and',
                        '    e == f):',
                        '  require(x)'])
    verify(formatter, input, output)

    input = '\n'.join(['if a != NULL:',
                       '  if a.f(b) > 1:',
                       '    require(a.f(b) % 4 == 0)'])
    output = '\n'.join(['if a != NULL:',
                        '  if a.f(b) > 1:',
                        '    require(a.f(b) % 4 == 0)'])
    verify(formatter, input, output)

    input = '\n'.join(['if a != NULL:',
                       '  if a.f(b) > 1:',
                       '    require(a.f(b) % 4 == 0)',
                       '  else:',
                       '    require(a.g(b) % 4 == 0)',
                       '    require(a.c > 0)'])
    output = '\n'.join(['if a != NULL:',
                        '  if a.f(b) > 1:',
                        '    require(a.f(b) % 4 == 0)',
                        '  else:',
                        '    require(a.g(b) % 4 == 0)',
                        '    require(a.c > 0)'])
    verify(formatter, input, output)

    input = '\n'.join(['if a != NULL:',
                       '  if a.f(b) > 1:',
                       '    require(a.f(b) % 4 == 0)',
                       '  elif a.g(b) > 2:',
                       '    require(a.g(b) % 4 == 0)',
                       '  elif a.g(c) > 0:',
                       '    require(a.g(b) % 4 == 0)',
                       '    require(a.c > 0)'])
    output = '\n'.join(['if a != NULL:',
                        '  if a.f(b) > 1:',
                        '    require(a.f(b) % 4 == 0)',
                        '  elif a.g(b) > 2:',
                        '    require(a.g(b) % 4 == 0)',
                        '  elif a.g(c) > 0:',
                        '    require(a.g(b) % 4 == 0)',
                        '    require(a.c > 0)'])
    verify(formatter, input, output)

    input = '\n'.join(['if a != NULL:',
                       '  if a.f(b) > 1:',
                       '    require(a.f(b) % 4 == 0)',
                       '  elif a.g(b) > 2:',
                       '    require(a.g(b) % 4 == 0)',
                       '    require(a.c > 0)',
                       '  else:',
                       '    require(a.g(b) == 0)'])
    output = '\n'.join(['if a != NULL:',
                        '  if a.f(b) > 1:',
                        '    require(a.f(b) % 4 == 0)',
                        '  elif a.g(b) > 2:',
                        '    require(a.g(b) % 4 == 0)',
                        '    require(a.c > 0)',
                        '  else:',
                        '    require(a.g(b) == 0)'])
    verify(formatter, input, output)

def test_source_for(registry):
    """Source formatting: Test for loops."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    input = '\n'.join(['for a in b:',
                       '    c'])
    output = '\n'.join(['for a in b:',
                        '  c'])
    verify(formatter, input, output)

    input = '\n'.join(['for a in b:',
                       '    c',
                       '    d'])
    output = '\n'.join(['for a in b:',
                        '  c',
                        '  d'])
    verify(formatter, input, output)

    input = '\n'.join(['for info in pInfos:',
                       ' require(other[array_index(info)].layout == info.layout)'])
    output = '\n'.join(['for info in pInfos:',
                        '  require(other[array_index(info)].layout == info.layout)'])
    verify(formatter, input, output)

    input = '\n'.join(['for info in pInfos:',
                       ' if info.pDepthStencil != NULL:',
                       '  require(info.pDepthStencil.handle != VK_NULL_HANDLE)'])
    output = '\n'.join(['for info in pInfos:',
                        '  if info.pDepthStencil != NULL:',
                        '    require(info.pDepthStencil.handle != VK_NULL_HANDLE)'])
    verify(formatter, input, output)

    input = '\n'.join(['if info.has_pnext(VkSwapchainPresentFenceInfoEXT):',
                       ' for fence in info.pnext(VkSwapchainPresentFenceInfoEXT).pFences:',
                       '  if fence != VK_NULL_HANDLE:',
                       '   require(fence.valid())'])
    output = '\n'.join(['if info.has_pnext(VkSwapchainPresentFenceInfoEXT):',
                        '  for fence in info.pnext(VkSwapchainPresentFenceInfoEXT).pFences:',
                        '    if fence != VK_NULL_HANDLE:',
                        '      require(fence.valid())'])
    verify(formatter, input, output)

def test_source_comment(registry):
    """Source formatting: Test for comments."""
    formatter = VuFormatter(VuSourceStyler('file.adoc', 123))

    input = '\n'.join(['for a in b:',
                       '    #     A comment line   ',
                       '    c'])
    output = '\n'.join(['for a in b:',
                        '  # A comment line',
                        '  c'])
    verify(formatter, input, output)

    input = '\n'.join(['#   Comment on first line',
                       'if a:',
                       '    b'])
    output = '\n'.join(['# Comment on first line',
                        'if a:',
                        '  b'])
    verify(formatter, input, output)

    input = '\n'.join(['#Multiple comment',
                       '#    Lines at the',
                       '#   Beginning ',
                       'if info.has_pnext(VkSwapchainPresentFenceInfoEXT):',
                       ' #   And in between',
                       ' for fence in info.pnext(VkSwapchainPresentFenceInfoEXT).pFences:',
                       '  #the rest',
                       '  if fence != VK_NULL_HANDLE:',
                       '   # of lines',
                       '   require(fence.valid())',
                       '   # Including last line'])
    output = '\n'.join(['# Multiple comment',
                        '# Lines at the',
                        '# Beginning',
                        'if info.has_pnext(VkSwapchainPresentFenceInfoEXT):',
                        '  # And in between',
                        '  for fence in info.pnext(VkSwapchainPresentFenceInfoEXT).pFences:',
                        '    # the rest',
                        '    if fence != VK_NULL_HANDLE:',
                        '      # of lines',
                        '      require(fence.valid())',
                        '      # Including last line'])
    verify(formatter, input, output)

def test_output(registry):
    """Output formatting."""
    formatter = VuFormatter(VuOutputStyler(registry, 'file.adoc', 123))

    input = '\n'.join(['if info.has_pnext(VkSwapchainPresentFenceInfoEXT):',
                       ' for fence in info.pnext(VkSwapchainPresentFenceInfoEXT).pFences:',
                       '  if fence != VK_NULL_HANDLE:',
                       '   require(fence.valid())'])
    output = '\n'.join(['[vu]#[vu-keyword]##if## info.[vu-predicate]##<<vu-predicate-has_pnext,has_pnext>>##&lpar;slink:VkSwapchainPresentFenceInfoEXT&rpar;: +',
                        '&nbsp;&nbsp;[vu-keyword]##for## fence [vu-operator]##in## info.[vu-predicate]##<<vu-predicate-pnext,pnext>>##&lpar;slink:VkSwapchainPresentFenceInfoEXT&rpar;.pFences: +',
                        '&nbsp;&nbsp;&nbsp;&nbsp;[vu-keyword]##if## fence [vu-operator]##!=## dlink:VK_NULL_HANDLE: +',
                        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-require,require>>##&lpar;fence.[vu-predicate]##<<vu-predicate-valid,valid>>##&lpar;&rpar;&rpar;#'])
    verify(formatter, input, output)

def test_output_with_comment(registry):
    """Output formatting with comments."""
    formatter = VuFormatter(VuOutputStyler(registry, 'file.adoc', 123))

    input = '\n'.join(['#Multiple comment',
                       '#    Lines sname:at the',
                       '#   Beginning ',
                       'if info.has_pnext(VkSwapchainPresentFenceInfoEXT):',
                       ' #   And in between',
                       ' for fence in info.pnext(VkSwapchainPresentFenceInfoEXT).pFences:',
                       '  #the rest',
                       '  if fence != VK_NULL_HANDLE:',
                       '   # of lines',
                       '   require(fence.valid())',
                       '   # Including last line'])
    output = '\n'.join(['[vu]#[vu-comment]##&#x23; Multiple comment## +',
                        '[vu-comment]##&#x23; Lines sname:at the## +',
                        '[vu-comment]##&#x23; Beginning## +',
                        '[vu-keyword]##if## info.[vu-predicate]##<<vu-predicate-has_pnext,has_pnext>>##&lpar;slink:VkSwapchainPresentFenceInfoEXT&rpar;: +',
                        '&nbsp;&nbsp;[vu-comment]##&#x23; And in between## +',
                        '&nbsp;&nbsp;[vu-keyword]##for## fence [vu-operator]##in## info.[vu-predicate]##<<vu-predicate-pnext,pnext>>##&lpar;slink:VkSwapchainPresentFenceInfoEXT&rpar;.pFences: +',
                        '&nbsp;&nbsp;&nbsp;&nbsp;[vu-comment]##&#x23; the rest## +',
                        '&nbsp;&nbsp;&nbsp;&nbsp;[vu-keyword]##if## fence [vu-operator]##!=## dlink:VK_NULL_HANDLE: +',
                        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[vu-comment]##&#x23; of lines## +',
                        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-require,require>>##&lpar;fence.[vu-predicate]##<<vu-predicate-valid,valid>>##&lpar;&rpar;&rpar; +',
                        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[vu-comment]##&#x23; Including last line###'])
    verify(formatter, input, output)

def test_output_with_feature(registry):
    """Output formatting with features from 1.0 core, promoted and extension."""
    formatter = VuFormatter(VuOutputStyler(registry, 'file.adoc', 123))

    input = '\n'.join(['if (is_feature_enabled(robustBufferAccess) or',
                       '    is_feature_enabled(storageBuffer16BitAccess) or',
                       '    is_feature_enabled(primitiveFragmentShadingRateMeshShader)):',
                       '  require(fence.valid())'])
    output = '\n'.join(['[vu]#[vu-keyword]##if## &lpar;[vu-predicate]##<<vu-predicate-is_feature_enabled,is_feature_enabled>>##&lpar;<<features-robustBufferAccess,robustBufferAccess>>&rpar; [vu-operator]##or## +',
                        '&nbsp;&nbsp;&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-is_feature_enabled,is_feature_enabled>>##&lpar;<<features-storageBuffer16BitAccess,storageBuffer16BitAccess>>&rpar; [vu-operator]##or## +',
                        '&nbsp;&nbsp;&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-is_feature_enabled,is_feature_enabled>>##&lpar;<<features-primitiveFragmentShadingRateMeshShader,primitiveFragmentShadingRateMeshShader>>&rpar;&rpar;: +',
                        '&nbsp;&nbsp;[vu-predicate]##<<vu-predicate-require,require>>##&lpar;fence.[vu-predicate]##<<vu-predicate-valid,valid>>##&lpar;&rpar;&rpar;#'])
    verify(formatter, input, output)
