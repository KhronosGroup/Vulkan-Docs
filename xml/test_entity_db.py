#!/usr/bin/python3 -i
#
# Copyright (c) 2018-2019 Collabora, Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
