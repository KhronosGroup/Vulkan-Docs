#!/usr/bin/env python3
#
# Copyright 2026 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# Purpose:      This file contains tests for parse_dependency.py

from parse_dependency import evaluateDependency, pruneDependency

def supported(*names):
    """Return an isSupported function for a set of names"""
    return lambda name: name in names

def testPruneDependencyUnchanged():
    # Expressions whose names are all supported are returned as they are
    assert pruneDependency('A', supported('A')) == 'A'
    assert pruneDependency('A,B', supported('A', 'B')) == 'A,B'
    assert pruneDependency('(A+B),C', supported('A', 'B', 'C')) == '(A+B),C'

def testPruneDependencyOr():
    # Alternatives which are not supported are dropped
    assert pruneDependency('A,B', supported('A')) == 'A'
    assert pruneDependency('A,B,C', supported('B')) == 'B'
    assert pruneDependency('A,B,C', supported('A', 'C')) == 'A,C'
    assert pruneDependency('A,B', supported()) is None

def testPruneDependencyAnd():
    # All the terms of an 'and' are needed
    assert pruneDependency('A+B', supported('A')) is None
    assert pruneDependency('A+B+C', supported('A', 'B')) is None

def testPruneDependencyNested():
    assert pruneDependency('A+(B,C)', supported('A', 'C')) == 'A+C'
    assert pruneDependency('(A+B),C', supported('A', 'B', 'D')) == 'A+B'
    assert pruneDependency('A,(B+C),D', supported('B', 'D')) == 'D'
    assert pruneDependency('A+(B,C),D', supported('A', 'B', 'C')) == 'A+(B,C)'
    assert pruneDependency('A,(B+C),D', supported('B', 'C')) == 'B+C'

def testPruneDependencyMatchesEvaluation():
    # Treating an unsupported name as False gives the same result as
    # evaluating the pruned expression
    exprs = ['A', 'A,B', 'A+B', 'A+(B,C)', '(A+B),C', '(A,B)+(C,D)', 'A,(B+(C,D))']
    names = 'ABCD'
    for expr in exprs:
        for mask in range(1 << len(names)):
            have = {n for i, n in enumerate(names) if mask & (1 << i)}
            pruned = pruneDependency(expr, supported(*have))
            expected = evaluateDependency(expr, supported(*have))
            # The expression can be satisfied only if it can be satisfied
            # with the names which are supported
            assert (pruned is not None) == expected
            if pruned is not None:
                assert evaluateDependency(pruned, supported(*have))
