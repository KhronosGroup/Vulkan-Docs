#!/usr/bin/python3 -i
#
# Copyright (c) 2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Rylie Pavlik <rylie.pavlik@collabora.com>
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


def longest_common_prefix(strings):
    """
    Find the longest common prefix of a list of 2 or more strings.

    Args:
        strings (collection): at least 2 strings.

    Returns:
        string: The longest string that all submitted strings start with.

    >>> longest_common_prefix(["abcd", "abce"])
    'abc'

    """
    assert len(strings) > 1
    a = min(strings)
    b = max(strings)
    prefix = []
    for a_char, b_char in zip(a, b):
        if a_char == b_char:
            prefix.append(a_char)
        else:
            break
    return "".join(prefix)


def longest_common_token_prefix(strings, delimiter='_'):
    """
    Find the longest common token-wise prefix of a list of 2 or more strings.

    Args:
        strings (collection): at least 2 strings.
        delimiter (character): the character to split on.

    Returns:
        string: The longest string that all submitted strings start with.

    >>> longest_common_token_prefix(["xr_abc_123", "xr_abc_567"])
    'xr_abc_'

    "1" is in the per-character longest common prefix, but 123 != 135,
    so it's not in the per-token prefix.

    >>> longest_common_token_prefix(["xr_abc_123", "xr_abc_135"])
    'xr_abc_'

    Here, the prefix is actually the entirety of one string, so no trailing delimiter.

    >>> longest_common_token_prefix(["xr_abc_123", "xr_abc"])
    'xr_abc'


    No common prefix here, because it's per-token:

    >>> longest_common_token_prefix(["abc_123", "ab_123"])
    ''

    """
    assert len(strings) > 1
    a = min(strings).split(delimiter)
    b = max(strings).split(delimiter)
    prefix_tokens = []
    for a_token, b_token in zip(a, b):
        if a_token == b_token:
            prefix_tokens.append(a_token)
        else:
            break
    if prefix_tokens:
        prefix = delimiter.join(prefix_tokens)
        if len(prefix_tokens) < min(len(a), len(b)):
            # This is truly a prefix, not just one of the strings.
            prefix += delimiter
        return prefix
    return ''
