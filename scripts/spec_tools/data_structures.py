#!/usr/bin/env python3 -i
#
# Copyright (c) 2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Rylie Pavlik <rylie.pavlik@collabora.com>
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
