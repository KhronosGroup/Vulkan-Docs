# Copyright 2022 The Khronos Group Inc.
# Copyright 2003-2019 Paul McGuire
# SPDX-License-Identifier: MIT

# apirequirements.py - parse 'depends' / 'extension' expressions in API XML
# Supported expressions at present:
#   - extension names
#   - '+' as AND connector
#   - ',' as OR connector
#   - parenthesization for grouping (not used yet)
#

# Based on https://github.com/pyparsing/pyparsing/blob/master/examples/fourFn.py

from pyparsing import (
    Literal,
    Word,
    Group,
    Forward,
    alphas,
    alphanums,
    Regex,
    ParseException,
    CaselessKeyword,
    Suppress,
    delimitedList,
)
import math
import operator
import re

exprStack = []

def push_first(toks):
    # print(f'push_first(toks = {toks}): |exprStack| = {len(exprStack)} exprStack = {exprStack}')

    exprStack.append(toks[0])

bnf = None

def dependencyBNF():
    """
    boolop  :: '+' | ','
    extname :: Char(alphas)
    atom    :: extname | '(' expr ')'
    expr    :: atom [ boolop atom ]*
    """
    global bnf
    if not bnf:
        ident = Word(alphanums + '_')

        and_, or_ = map(Literal, '+,')
        lpar, rpar = map(Suppress, '()')
        boolop = and_ | or_

        expr = Forward()
        expr_list = delimitedList(Group(expr))
        atom = (
            boolop[...]
            + (
                (ident).setParseAction(push_first)
                | Group(lpar + expr + rpar)
            )
        )

        expr <<= atom + (boolop + atom).setParseAction(push_first)[...]
        bnf = expr
    return bnf


# map operator symbols to corresponding arithmetic operations
opn = {
    '+': operator.and_,
    ',': operator.or_,
}

# map operator symbols to corresponding words
opname = {
    '+': 'and',
    ',': 'or',
}

def extensionIsSupported(extname):
    return True

def evaluate_stack(s):
    op, num_args = s.pop(), 0
    # print(f'evaluate_stack: op = {op} num_args {num_args}')
    if isinstance(op, tuple):
        op, num_args = op
    if op in '+,':
        # note: operands are pushed onto the stack in reverse order
        op2 = evaluate_stack(s)
        op1 = evaluate_stack(s)
        return opn[op](op1, op2)
    elif op[0].isalpha():
        # print(f'extname {op} => {supported(op)}')
        return extensionIsSupported(op)
    else:
        raise Exception(f'invalid op: {op}')

def evalDependencyLanguage(s, specmacros):
    """Evaluate an expression stack, returning an English equivalent

     - s - the stack
     - specmacros - if True, prepare the language for spec inclusion"""

    op, num_args = s.pop(), 0
    # print(f'evalDependencyLanguage: op = {op} num_args {num_args}')
    if isinstance(op, tuple):
        op, num_args = op
    if op in '+,':
        # @@ Should parenthesize, not needed yet
        rhs = evalDependencyLanguage(s, specmacros)
        return evalDependencyLanguage(s, specmacros) + f' {opname[op]} ' + rhs
    elif op[0].isalpha():
        # This is an extension or feature name
        if specmacros:
            match = re.search("[A-Z]+_VERSION_([0-9]+)_([0-9]+)", op)
            if match is not None:
                major = match.group(1)
                minor = match.group(2)
                version = major + '.' + minor
                return f'<<versions-{major}.{minor}, Version {version}>>'
            else:
                return 'apiext:' + op
        else:
            return op
    else:
        raise Exception(f'invalid op: {op}')

def dependencyLanguage(dependency, specmacros = False):
    """Return an API dependency expression translated to natural language.

     - dependency - the expression
     - specmacros - if True, prepare the language for spec inclusion with
       macros and xrefs included"""

    global exprStack
    exprStack = []
    results = dependencyBNF().parseString(dependency, parseAll=True)
    # print(f'language(): stack = {exprStack}')
    return evalDependencyLanguage(exprStack, specmacros)

def evalDependencyNames(s):
    """Evaluate an expression stack, returning a set of names

     - s - the stack"""

    op, num_args = s.pop(), 0
    # print(f'evalDependencyNames: op = {op} num_args {num_args}')
    if isinstance(op, tuple):
        op, num_args = op
    if op in '+,':
        # The operation itself is not evaluated, since all we care about is
        # the names
        return evalDependencyNames(s) | evalDependencyNames(s)
    elif op[0].isalpha():
        return { op }
    else:
        raise Exception(f'invalid op: {op}')

def dependencyNames(dependency):
    """Return a set of the extension and version names in an API dependency
       expression

     - dependency - the expression"""

    global exprStack
    exprStack = []
    results = dependencyBNF().parseString(dependency, parseAll=True)
    # print(f'names(): stack = {exprStack}')
    return evalDependencyNames(exprStack)

if __name__ == "__main__":

    def test(dependency, expected):
        global exprStack
        exprStack = []

        try:
            results = dependencyBNF().parseString(dependency, parseAll=True)
            # print('test(): stack =', exprStack)
            val = evaluate_stack(exprStack[:])
        except ParseException as pe:
            print(dependency, "failed parse:", str(pe))
        except Exception as e:
            print(dependency, "failed eval:", str(e), exprStack)
        else:
            print(dependency, "failed eval:", str(e), exprStack)
            if val == expected:
                print(f'{dependency} = {val} {results} => {exprStack}')
            else:
                print(f'{dependency} !!! {val} != {expected} {results} => {exprStack}')

    e = 'VK_VERSION_1_1+(bar,spam)'
    # test(e, False)
    print(f'{e} -> {dependencyNames(e)}')
    print('\n------------\n')
    print(f'{e} -> {dependencyLanguage(e, False)}')
    print('\n------------\n')
    print(f'{e} -> {dependencyLanguage(e, True)}')

    # test('true', True)
    # test('(True)', True)
    # test('false,false', False)
    # test('false,true', True)
    # test('false+true', False)
    # test('VK_foo_bar+true', True)
