#!/usr/bin/python3
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Shahbaz Youssefi <syoussefi@google.com>
#
# Purpose:      This file contains tests for reflow.py

import pytest

from collections import namedtuple
import os

from reflib import loadFile
from reflow import reflowFile

testsDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'reflow-tests')
resultsDir = os.path.join(testsDir, 'results')

Variations = namedtuple('Variations', ['reflow', 'addVUID'])

def makeTestId(variations):
    separator = ''
    testid = ''

    if not variations.reflow:
        testid += separator + 'noreflow'
        separator = '-'

    if not variations.addVUID:
        testid += separator + 'novuid'
        separator = '-'

    if testid == '':
        testid = 'default'

    return testid

class ReflowArgs:
    def __init__(self, variations):
        self.overwrite = False
        self.nowrite = False
        self.outDir = os.path.join(resultsDir, makeTestId(variations))
        self.check = True
        self.checkVUID = True
        self.noflow = not variations.reflow
        self.margin = 76
        self.suffix = ''
        self.nextvu = 10000 if variations.addVUID else None
        self.maxvu = 99999
        self.warnCount = 0
        self.vuidDict = {}

        self.variations = variations

variations = [
    Variations(False, False),
    Variations(False, True),
    Variations(True, False),
    Variations(True, True),
]

@pytest.fixture(params=variations, ids=makeTestId)
def args(request):
    return ReflowArgs(request.param)

def getPath(*names):
    return os.path.join(testsDir, *names)

def match_with_expected(resultFile, expectation):
    result, result_newline = loadFile(resultFile)
    expect, expect_newline = loadFile(expectation)

    assert(result_newline == expect_newline)
    assert(result == expect)

def run_reflow_test(args, filetag):
    testid = makeTestId(args.variations)

    source = 'src-' + filetag + '.adoc'
    expect = 'expect-' + filetag + '-' + testid + '.adoc'

    filename = getPath(source)

    reflowFile(filename, args)

    match_with_expected(getPath(resultsDir, testid, source), getPath(expect))

def match_warn_count(args, expected):
    assert(args.warnCount == expected)

def match_vuid_dict(args, expectedExisting, expectedNew):
    expected = expectedExisting
    if args.nextvu is not None:
        expected = expected | expectedNew

    assert(sorted(args.vuidDict.keys()) == sorted(expected.keys()))

    for vuid, locations in args.vuidDict.items():
        for location, expectedLocation in zip(locations, expected[vuid]):
            filename, tagline = location
            expectedFilename, expectedTag = expectedLocation

        assert(expectedFilename in filename)
        assert(expectedTag in tagline)

def test_text(args):
    """Basic test of text reflow."""
    run_reflow_test(args, 'text')
    match_warn_count(args, 0)
    match_vuid_dict(args, {}, {})

def test_table(args):
    """Basic test that ensures tables are not reformatted."""
    run_reflow_test(args, 'table')
    match_warn_count(args, 0)
    match_vuid_dict(args, {}, {})

def test_vu(args):
    """Basic test that VU reflows work."""
    run_reflow_test(args, 'vu')
    match_warn_count(args, 0)
    match_vuid_dict(args, {'01993':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-image-01993]]']],
                           '00002':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-image-00002]]']],
                           '01545':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-image-01545]]']],
                           '00003':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-image-00003]]']],
                           '00004':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-00004]]']],
                           '00005':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-00005]]']],
                           '01394':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-01394]]']],
                           '02498':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-aspectMask-02498]]']],
                           '01470':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-baseMipLevel-01470]]']],
                           '01692':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-pRanges-01692]]']],
                           '01472':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-baseArrayLayer-01472]]']],
                           '01693':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-pRanges-01693]]']],
                           '00007':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-image-00007]]']],
                           '04961':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-pColor-04961]]']],
                           '01805':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-commandBuffer-01805]]']],
                           '01806':
                           [['scripts/reflow-tests/src-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-commandBuffer-01806]]']]},
                    {})

# Commented out now that VU extractor supports this, but may
# need to refactor through a conventions object enable if
# OpenXR still needs this.
# def test_ifdef_in_vu(args):
#     """Test that ifdef in VUs are warned against."""
#     run_reflow_test(args, 'ifdef-in-vu')
#     match_warn_count(args, 1)
#     match_vuid_dict(args, {'00003':
#                            [['scripts/reflow-tests/src-ifdef-in-vu.adoc',
#                              '[[VUID-vkCmdClearColorImage-image-00003]]']],
#                            '00004':
#                            [['scripts/reflow-tests/src-ifdef-in-vu.adoc',
#                              '[[VUID-vkCmdClearColorImage-imageLayout-00004]]']],
#                            '00005':
#                            [['scripts/reflow-tests/src-ifdef-in-vu.adoc',
#                              '[[VUID-vkCmdClearColorImage-imageLayout-00005]]']],
#                            '04961':
#                            [['scripts/reflow-tests/src-ifdef-in-vu.adoc',
#                              '[[VUID-vkCmdClearColorImage-pColor-04961]]']]},
#                     {})

def test_vuid_repeat(args):
    """Test that same VUID in multiple VUs is detected."""
    run_reflow_test(args, 'vuid-repeat')
    match_warn_count(args, 0)
    match_vuid_dict(args, {'02498':
                           [['scripts/reflow-tests/src-vuid-repeat.adoc',
                             '[[VUID-vkCmdClearColorImage-aspectMask-02498]]'],
                            ['scripts/reflow-tests/src-vuid-repeat.adoc',
                             '[[VUID-vkCmdClearColorImage-pRanges-02498]]'],
                            ['scripts/reflow-tests/src-vuid-repeat.adoc',
                             '[[VUID-vkCmdClearColorImage-pRanges-02498]]'],
                            ['scripts/reflow-tests/src-vuid-repeat.adoc',
                             '[[VUID-vkCmdClearColorImage-pColor-02498]]']],
                           '01470':
                           [['scripts/reflow-tests/src-vuid-repeat.adoc',
                             '[[VUID-vkCmdClearColorImage-baseMipLevel-01470]]']],
                           '00007':
                           [['scripts/reflow-tests/src-vuid-repeat.adoc',
                             '[[VUID-vkCmdClearColorImage-baseArrayLayer-00007]]'],
                            ['scripts/reflow-tests/src-vuid-repeat.adoc',
                             '[[VUID-vkCmdClearColorImage-image-00007]]']]},
                    {})

def test_new_vuid(args):
    """Test that VUID generation works."""
    run_reflow_test(args, 'new-vuid')
    match_warn_count(args, 0)
    match_vuid_dict(args, {'01993':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-01993]]']],
                           '01545':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-01545]]']],
                           '00004':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-00004]]']],
                           '00005':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-00005]]']],
                           '02498':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-aspectMask-02498]]']],
                           '01470':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-baseMipLevel-01470]]']],
                           '01472':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-baseArrayLayer-01472]]']],
                           '01693':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-pRanges-01693]]']],
                           '01805':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-commandBuffer-01805]]']],
                           '01806':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-commandBuffer-01806]]']]},
                          {'10000':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-10000]]']],
                           '10001':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-10001]]']],
                           '10002':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-10002]]']],
                           '10003':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-pRanges-10003]]']],
                           '10004':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-10004]]']],
                           '10005':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-pColor-10005]]']]})

def test_new_vuid_attribute(args):
    """Test that VUID generation works and prioritizes attributes for tags."""
    run_reflow_test(args, 'new-vuid-attribute')
    match_warn_count(args, 0)
    match_vuid_dict(args, {}, {'10000':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10000]]']],
                               '10001':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imagesubresource}-10001]]']],
                               '10002':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10002]]']],
                               '10003':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10003]]']],
                               '10004':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10004]]']],
                               '10005':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10005]]']],
                               '10006':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10006]]']],
                               '10007':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10007]]']],
                               '10008':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10008]]']],
                               '10009':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10009]]']],
                               '10010':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10010]]']],
                               '10011':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imagesubresource}-10011]]']],
                               '10012':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10012]]']],
                               '10013':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10013]]']],
                               '10014':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10014]]']],
                               '10015':
                               [['scripts/reflow-tests/src-new-vuid-attribute.adoc',
                                 '[[VUID-{refpage}-{imageparam}-10015]]']]})

def test_common_validity(args):
    """Test that VUID generation works for common validity files."""
    run_reflow_test(args, 'common-validity')
    match_warn_count(args, 0)
    match_vuid_dict(args, {'00171':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-pRegions-00171]]']],
                           '00176':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-srcBuffer-00176]]']],
                           '00177':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-dstImage-00177]]']],
                           '00178':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-dstImage-00178]]']],
                           '00181':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-dstImageLayout-00181]]']]},
                          {'10000':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-pRegions-10000]]']],
                           '10001':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-srcBuffer-10001]]']],
                           '10002':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-dstImage-10002]]']],
                           '10003':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-dstImage-10003]]']],
                           '10004':
                           [['scripts/reflow-tests/src-common-validity.adoc',
                             '[[VUID-{refpage}-dstImageLayout-10004]]']]})

def test_nested_lists_in_vu(args):
    """Test that nested lists in VU work correctly."""
    run_reflow_test(args, 'nested-lists-in-vu')
    match_warn_count(args, 0)
    match_vuid_dict(args, {'08971':
                           [['scripts/reflow-tests/src-nested-lists-in-vu.adoc',
                             '[[VUID-{refpage}-None-08971]]']]},
                          {})


def test_math_block_in_vu(args):
    """Test that nested lists in VU work correctly."""
    run_reflow_test(args, 'math-block-in-vu')
    match_warn_count(args, 0)
    match_vuid_dict(args, {'00004':
                           [['scripts/reflow-tests/src-math-block-in-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-00004]]']]},
                          {'10000':
                           [['scripts/reflow-tests/src-math-block-in-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-image-10000]]']]})
