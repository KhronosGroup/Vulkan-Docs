#!/usr/bin/python3 -i
#
# Copyright (c) 2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>
"""RecursiveMemoize serves as a base class for a function modeled
as a dictionary computed on-the-fly."""


class RecursiveMemoize:
    """Base class for functions that are recursive.

    Derive and implement `def compute(self, key):` to perform the computation:
    you may use __getitem__ (aka self[otherkey]) to access the results for
    another key. Each value will be computed at most once. Your
    function should never return None, since it is used as a sentinel here.

    """

    def __init__(self, func, key_iterable=None, permit_cycles=False):
        """Initialize data structures, and optionally compute/cache the answer
        for all elements of an iterable.

        If permit_cycles is False, then __getitem__ on something that's
        currently being computed raises an exception.
        If permit_cycles is True, then __getitem__ on something that's
        currently being computed returns None.
        """
        self._compute = func
        self.permit_cycles = permit_cycles
        self.d = {}
        if key_iterable:
            # If we were given an iterable, let's populate those.
            for key in key_iterable:
                _ = self[key]

    def __getitem__(self, key):
        """Access the result of computing the function on the input.

        Performed lazily and cached.
        Implement `def compute(self, key):` with the actual function,
        which will be called on demand."""
        if key in self.d:
            ret = self.d[key]
            # Detect "we're computing this" sentinel and
            # fail if cycles not permitted
            if ret is None and not self.permit_cycles:
                raise RuntimeError("Cycle detected when computing function: " +
                                   "f({}) depends on itself".format(key))
            # return the memoized value
            # (which might be None if we're in a cycle that's permitted)
            return ret

        # Set sentinel for "we're computing this"
        self.d[key] = None
        # Delegate to function to actually compute
        ret = self._compute(key)
        # Memoize
        self.d[key] = ret

        return ret

    def get_dict(self):
        """Return the dictionary where memoized results are stored.

        DO NOT MODIFY!"""
        return self.d
