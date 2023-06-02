#!/usr/bin/python3

# Copyright 2022-2023 The Khronos Group Inc.
# Copyright 2003-2019 Paul McGuire
# SPDX-License-Identifier: MIT

# apirequirements.py - parse 'depends' expressions in API XML
# Supported methods:
#   dependency - the expression string
#
# evaluateDependency(dependency, isSupported) evaluates the expression,
# returning a boolean result. isSupported takes an extension or version name
# string and returns a boolean.
#
# dependencyLanguage(dependency) returns an English string equivalent
# to the expression, suitable for header file comments.
#
# dependencyNames(dependency) returns a set of the extension and
# version names in the expression.
#
# dependencyMarkup(dependency) returns a string containing asciidoctor
# markup for English equivalent to the expression, suitable for extension
# appendices.
#
# All may throw a ParseException if the expression cannot be parsed or is
# not completely consumed by parsing.

# Supported expressions at present:
#   - extension names
#   - '+' as AND connector
#   - ',' as OR connector
#   - parenthesization for grouping

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
    infixNotation,
)
import math
import operator
import pyparsing as pp
import re

def nameMarkup(name):
    """Returns asciidoc markup to generate a link to an API version or
       extension anchor.

       - name - version or extension name"""

    # Could use ApiConventions.is_api_version_name, but that does not split
    # out the major/minor version numbers.
    match = re.search("[A-Z]+_VERSION_([0-9]+)_([0-9]+)", name)
    if match is not None:
        major = match.group(1)
        minor = match.group(2)
        version = major + '.' + minor

        # Vulkan SC has a different anchor pattern for version appendices
        scMatch = re.search("[A-Z]+SC_VERSION_([0-9]+)_([0-9]+)", name)
        if scMatch is not None:
            if version == '1.0':
                return 'Vulkan SC 1.0'
            else:
                return f'<<versions-sc-{major}.{minor}, Version SC {version}>>'
        else:
            return f'<<versions-{major}.{minor}, Version {version}>>'
    else:
        return 'apiext:' + name

exprStack = []

def push_first(toks):
    """Push a token on the global stack

       - toks - first element is the token to push"""

    exprStack.append(toks[0])

# An identifier (version or extension name)
dependencyIdent = Word(alphanums + '_')

# Infix expression for depends expressions
dependencyExpr = pp.infixNotation(dependencyIdent,
    [ (pp.oneOf(', +'), 2, pp.opAssoc.LEFT), ])

# BNF grammar for depends expressions
_bnf = None
def dependencyBNF():
    """
    boolop  :: '+' | ','
    extname :: Char(alphas)
    atom    :: extname | '(' expr ')'
    expr    :: atom [ boolop atom ]*
    """
    global _bnf
    if _bnf is None:
        and_, or_ = map(Literal, '+,')
        lpar, rpar = map(Suppress, '()')
        boolop = and_ | or_

        expr = Forward()
        expr_list = delimitedList(Group(expr))
        atom = (
            boolop[...]
            + (
                (dependencyIdent).setParseAction(push_first)
                | Group(lpar + expr + rpar)
            )
        )

        expr <<= atom + (boolop + atom).setParseAction(push_first)[...]
        _bnf = expr
    return _bnf


# map operator symbols to corresponding arithmetic operations
_opn = {
    '+': operator.and_,
    ',': operator.or_,
}

# map operator symbols to corresponding words
_opname = {
    '+': 'and',
    ',': 'or',
}

def evaluateStack(stack, isSupported):
    """Evaluate an expression stack, returning a boolean result.

     - stack - the stack
     - isSupported - function taking a version or extension name string and
       returning True or False if that name is supported or not."""

    op, num_args = stack.pop(), 0
    if isinstance(op, tuple):
        op, num_args = op

    if op in '+,':
        # Note: operands are pushed onto the stack in reverse order
        op2 = evaluateStack(stack, isSupported)
        op1 = evaluateStack(stack, isSupported)
        return _opn[op](op1, op2)
    elif op[0].isalpha():
        return isSupported(op)
    else:
        raise Exception(f'invalid op: {op}')

def evaluateDependency(dependency, isSupported):
    """Evaluate a dependency expression, returning a boolean result.

     - dependency - the expression
     - isSupported - function taking a version or extension name string and
       returning True or False if that name is supported or not."""

    global exprStack
    exprStack = []
    results = dependencyBNF().parseString(dependency, parseAll=True)
    val = evaluateStack(exprStack[:], isSupported)
    return val

def evalDependencyLanguage(stack, specmacros):
    """Evaluate an expression stack, returning an English equivalent

     - stack - the stack
     - specmacros - if True, prepare the language for spec inclusion"""

    op, num_args = stack.pop(), 0
    if isinstance(op, tuple):
        op, num_args = op
    if op in '+,':
        # Could parenthesize, not needed yet
        rhs = evalDependencyLanguage(stack, specmacros)
        return evalDependencyLanguage(stack, specmacros) + f' {_opname[op]} ' + rhs
    elif op[0].isalpha():
        # This is an extension or feature name
        if specmacros:
            return nameMarkup(op)
        else:
            return op
    else:
        raise Exception(f'invalid op: {op}')

def dependencyLanguage(dependency, specmacros = False):
    """Return an API dependency expression translated to a form suitable for
       asciidoctor conditionals or header file comments.

     - dependency - the expression
     - specmacros - if False, return a string that can be used as an
       asciidoctor conditional.
       If True, return a string suitable for spec inclusion with macros and
       xrefs included."""

    global exprStack
    exprStack = []
    results = dependencyBNF().parseString(dependency, parseAll=True)
    return evalDependencyLanguage(exprStack, specmacros)

def evalDependencyNames(stack):
    """Evaluate an expression stack, returning the set of extension and
       feature names used in the expression.

     - stack - the stack"""

    op, num_args = stack.pop(), 0
    if isinstance(op, tuple):
        op, num_args = op
    if op in '+,':
        # Do not evaluate the operation. We only care about the names.
        return evalDependencyNames(stack) | evalDependencyNames(stack)
    elif op[0].isalpha():
        return { op }
    else:
        raise Exception(f'invalid op: {op}')

def dependencyNames(dependency):
    """Return a set of the extension and version names in an API dependency
       expression. Used when determining transitive dependencies for spec
       generation with specific extensions included.

     - dependency - the expression"""

    global exprStack
    exprStack = []
    results = dependencyBNF().parseString(dependency, parseAll=True)
    # print(f'names(): stack = {exprStack}')
    return evalDependencyNames(exprStack)

def markupTraverse(expr, level = 0, root = True):
    """Recursively process a dependency in infix form, transforming it into
       asciidoctor markup with expression nesting indicated by indentation
       level.

       - expr - expression to process
       - level - indentation level to render expression at
       - root - True only on initial call"""

    if level > 0:
        prefix = '{nbsp}{nbsp}' * level * 2 + ' '
    else:
        prefix = ''
    str = ''

    for elem in expr:
        if isinstance(elem, pp.ParseResults):
            if not root:
                nextlevel = level + 1
            else:
                # Do not indent the outer expression
                nextlevel = level

            str = str + markupTraverse(elem, level = nextlevel, root = False)
        elif elem in ('+', ','):
            str = str + f'{prefix}{_opname[elem]} +\n'
        else:
            str = str + f'{prefix}{nameMarkup(elem)} +\n'

    return str

def dependencyMarkup(dependency):
    """Return asciidoctor markup for a human-readable equivalent of an API
       dependency expression, suitable for use in extension appendix
       metadata.

     - dependency - the expression"""

    parsed = dependencyExpr.parseString(dependency)
    return markupTraverse(parsed)

if __name__ == "__main__":

    termdict = {
        'VK_VERSION_1_1' : True,
        'false' : False,
        'true' : True,
    }
    termSupported = lambda name: name in termdict and termdict[name]

    def test(dependency, expected):
        val = False
        try:
            val = evaluateDependency(dependency, termSupported)
        except ParseException as pe:
            print(dependency, f'failed parse: {dependency}')
        except Exception as e:
            print(dependency, f'failed eval: {dependency}')

        if val == expected:
            print(f'{dependency} = {val} (as expected)')
        else:
            print(f'{dependency} ERROR: {val} != {expected}')

    # Verify expressions are evaluated left-to-right

    test('false,false+false', False)
    test('false,false+true', False)
    test('false,true+false', False)
    test('false,true+true', True)
    test('true,false+false', False)
    test('true,false+true', True)
    test('true,true+false', False)
    test('true,true+true', True)

    test('false,(false+false)', False)
    test('false,(false+true)', False)
    test('false,(true+false)', False)
    test('false,(true+true)', True)
    test('true,(false+false)', True)
    test('true,(false+true)', True)
    test('true,(true+false)', True)
    test('true,(true+true)', True)


    test('false+false,false', False)
    test('false+false,true', True)
    test('false+true,false', False)
    test('false+true,true', True)
    test('true+false,false', False)
    test('true+false,true', True)
    test('true+true,false', True)
    test('true+true,true', True)

    test('false+(false,false)', False)
    test('false+(false,true)', False)
    test('false+(true,false)', False)
    test('false+(true,true)', False)
    test('true+(false,false)', False)
    test('true+(false,true)', True)
    test('true+(true,false)', True)
    test('true+(true,true)', True)


    #test('VK_VERSION_1_1+(false,true)', True)
    #test('true', True)
    #test('(true)', True)
    #test('false,false', False)
    #test('false,true', True)
    #test('false+true', False)
    #test('true+true', True)

    # Check formatting
    for dependency in [
        #'true',
        #'true+true+false',
        'true+(true+false),(false,true)',
        'true+((true+false),(false,true))',
        #'VK_VERSION_1_1+(true,false)',
    ]:
        print(f'expr = {dependency}\n{dependencyMarkup(dependency)}')
        print(f'  language = {dependencyLanguage(dependency)}')
        print(f'  names = {dependencyNames(dependency)}')
        print(f'  value = {evaluateDependency(dependency, termSupported)}')
