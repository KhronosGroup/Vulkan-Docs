#!/usr/bin/python3 -i
#
# Copyright (c) 2019 Collabora, Ltd.
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
"""Provides general-purpose data structures."""


class DictOfStringSets:
    """A dictionary where the values are sets of strings.

    Has some convenience functions to allow easier maintenance via
    the .add method."""

    def __init__(self, d=None):
        self.d = {}
        if d:
            for k, v in d.items():
                self.add(k, v)

    def __getitem__(self, k):
        return self.d[k]

    def __contains__(self, k):
        return k in self.d

    def get(self, k, default=None):
        return self.d.get(k, default)

    def get_dict(self):
        return self.d

    def items(self):
        """Return an iterator like dict().items()."""
        return self.d.items()

    def keys(self):
        """Return an iterator over keys."""
        return self.d.keys()

    def values(self):
        """Return an iterator over values."""
        return self.d.values()

    def add_key(self, k):
        """Ensure the set for the given key exists."""
        if k not in self.d:
            self.d[k] = set()

    def add(self, k, v):
        self.add_key(k)
        if isinstance(v, str):
            v = (v, )
        if not isinstance(v, set):
            v = set(v)
        self.d[k].update(v)
