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

class ReflowArgs:
    def __init__(self):
        self.overwrite = False
        self.nowrite = False
        self.outDir = resultsDir
        self.check = True
        self.checkVUID = True
        self.noflow = False
        self.margin = 76
        self.suffix = ''
        self.nextvu = 10000
        self.maxvu = 99999
        self.warnCount = 0
        self.vuidDict = {}

@pytest.fixture
def args():
    return ReflowArgs()

def getPath(*names):
    return os.path.join(testsDir, *names)

def match_with_expected(resultFile, expectation):
    result, result_newline = loadFile(resultFile)
    expect, expect_newline = loadFile(expectation)

    assert(result_newline == expect_newline)
    assert(result == expect)

def run_reflow_test(args, filetag):
    source = 'src-' + filetag + '.adoc'
    expect = 'expect-' + filetag + '.adoc'

    filename = getPath(source)

    reflowFile(filename, args)

    match_with_expected(getPath(resultsDir, source), getPath(expect))

def match_warn_count(args, expected):
    assert(args.warnCount == expected)

def match_vuid_dict(args, expected):
    assert(sorted(args.vuidDict.keys()) == sorted(expected.keys()))

    for vuid, locations in args.vuidDict.items():
        for location, expectedLocation in zip(locations, expected[vuid]):
            filename, tag = location
            expectedFilename, expectedTag = expectedLocation

        assert(expectedFilename in filename)
        assert(tag == expectedTag)

def test_text(args):
    """Basic test of text reflow."""
    run_reflow_test(args, 'text')
    match_warn_count(args, 0)
    match_vuid_dict(args, {})

def test_table(args):
    """Basic test that ensures tables are not reformatted."""
    run_reflow_test(args, 'table')
    match_warn_count(args, 0)
    match_vuid_dict(args, {})

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
                             '[[VUID-vkCmdClearColorImage-commandBuffer-01806]]']]})

def test_ifdef_in_vu(args):
    """Test that ifdef in VUs are warned against."""
    run_reflow_test(args, 'ifdef-in-vu')
    match_warn_count(args, 1)
    match_vuid_dict(args, {'00003':
                           [['scripts/reflow-tests/src-ifdef-in-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-image-00003]]']],
                           '00004':
                           [['scripts/reflow-tests/src-ifdef-in-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-00004]]']],
                           '00005':
                           [['scripts/reflow-tests/src-ifdef-in-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-00005]]']],
                           '04961':
                           [['scripts/reflow-tests/src-ifdef-in-vu.adoc',
                             '[[VUID-vkCmdClearColorImage-pColor-04961]]']]})

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
                             '[[VUID-vkCmdClearColorImage-image-00007]]']]})

def test_new_vuid(args):
    """Test that VUID generation works."""
    run_reflow_test(args, 'new-vuid')
    match_warn_count(args, 0)
    match_vuid_dict(args, {'01993':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-01993]]']],
                           '10000':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-10000]]']],
                           '01545':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-01545]]']],
                           '10001':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-10001]]']],
                           '00004':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-00004]]']],
                           '00005':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-00005]]']],
                           '10002':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-imageLayout-10002]]']],
                           '02498':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-aspectMask-02498]]']],
                           '01470':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-baseMipLevel-01470]]']],
                           '10003':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-pRanges-10003]]']],
                           '01472':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-baseArrayLayer-01472]]']],
                           '01693':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-pRanges-01693]]']],
                           '10004':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-image-10004]]']],
                           '10005':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-pColor-10005]]']],
                           '01805':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-commandBuffer-01805]]']],
                           '01806':
                           [['scripts/reflow-tests/src-new-vuid.adoc',
                             '[[VUID-vkCmdClearColorImage-commandBuffer-01806]]']]})
