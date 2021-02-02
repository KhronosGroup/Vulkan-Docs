#!/usr/bin/python3 -i
#
# Copyright 2013-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Utilities for working with attributes of the XML registry."""

import re

_PARAM_REF_NAME_RE = re.compile(
    r"(?P<name>[\w]+)(?P<brackets>\[\])?(?P<delim>\.|::|->)?")


def _split_param_ref(val):
    return [name for name, _, _ in _PARAM_REF_NAME_RE.findall(val)]


def _human_readable_deref(val, make_param_name=None):
    """Turn the "name[].member[]" notation into plain English."""
    parts = []
    matches = _PARAM_REF_NAME_RE.findall(val)
    for name, brackets, delim in reversed(matches):
        if make_param_name:
            name = make_param_name(name)
        if delim:
            parts.append('member of')
        if brackets:
            parts.append('each element of')
        parts.append('the')
        parts.append(name)
    parts.append('parameter')
    return ' '.join(parts)


class LengthEntry:
    """An entry in a (comma-separated) len attribute"""
    NULL_TERMINATED_STRING = 'null-terminated'
    MATH_STRING = 'latexmath:'

    def __init__(self, val):
        self.full_reference = val
        self.other_param_name = None
        self.null_terminated = False
        self.number = None
        self.math = None
        self.param_ref_parts = None
        if val == LengthEntry.NULL_TERMINATED_STRING:
            self.null_terminated = True
            return

        if val.startswith(LengthEntry.MATH_STRING):
            self.math = val.replace(LengthEntry.MATH_STRING, '')[1:-1]
            return

        if val.isdigit():
            self.number = int(val)
            return

        # Must be another param name.
        self.param_ref_parts = _split_param_ref(val)
        self.other_param_name = self.param_ref_parts[0]

    def __str__(self):
        return self.full_reference

    def get_human_readable(self, make_param_name=None):
        assert(self.other_param_name)
        return _human_readable_deref(self.full_reference, make_param_name=make_param_name)

    def __repr__(self):
        "Formats an object for repr(), debugger display, etc."
        return 'spec_tools.attributes.LengthEntry("{}")'.format(self.full_reference)

    @staticmethod
    def parse_len_from_param(param):
        """Get a list of LengthEntry."""
        len_str = param.get('len')
        if len_str is None:
            return None
        return [LengthEntry(elt) for elt in len_str.split(',')]


class ExternSyncEntry:
    """An entry in a (comma-separated) externsync attribute"""

    TRUE_STRING = 'true'
    TRUE_WITH_CHILDREN_STRING = 'true_with_children'

    def __init__(self, val):
        self.full_reference = val
        self.entirely_extern_sync = (val in (ExternSyncEntry.TRUE_STRING, ExternSyncEntry.TRUE_WITH_CHILDREN_STRING))
        self.children_extern_sync = (val == ExternSyncEntry.TRUE_WITH_CHILDREN_STRING)
        if self.entirely_extern_sync:
            return

        self.param_ref_parts = _split_param_ref(val)
        self.member = self.param_ref_parts[0]

    def get_human_readable(self, make_param_name=None):
        assert(not self.entirely_extern_sync)
        return _human_readable_deref(self.full_reference, make_param_name=make_param_name)

    @staticmethod
    def parse_externsync_from_param(param):
        """Get a list of ExternSyncEntry."""
        sync_str = param.get('externsync')
        if sync_str is None:
            return None
        return [ExternSyncEntry(elt) for elt in sync_str.split(',')]

    def __repr__(self):
        "Formats an object for repr(), debugger display, etc."
        return 'spec_tools.attributes.ExternSyncEntry("{}")'.format(self.full_reference)

