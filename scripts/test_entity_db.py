#!/usr/bin/python3 -i
#
# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>


import pytest

from check_spec_links import VulkanEntityDatabase


@pytest.fixture
def db():
    ret = VulkanEntityDatabase()
    # print(ret.getEntityJson())
    return ret


def test_likely_recognized(db):
    assert(db.likelyRecognizedEntity('vkBla'))
    assert(db.likelyRecognizedEntity('VkBla'))
    assert(db.likelyRecognizedEntity('VK_BLA'))


def test_db(db):
    assert(db.findEntity('vkCreateInstance'))

    # VKAPI_CALL is not referenced, so not added to EntityDatabase.
    # assert(db.findEntity('VKAPI_CALL'))
