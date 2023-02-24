# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Utilities to parse a VU into an AST, match its symbols with the entity_db
and walk the AST.  This can be used to:

- Reformat the VU to add syntax highlighting and make the formatting uniform
  (at build time)
- Generate VVL code directly from the VU (in the VVL repository)
"""

import ast
from collections import namedtuple
from enum import Enum
import re

from reflib import logDiag, logWarn, logErr
from spec_tools.entity_db import EntityDatabase
import spec_tools.util as util

# A line with an assignment, in the form of `a.b.c = ...`
assignmentPattern = re.compile(r'^\s*[a-zA-Z0-9.]+\s*=')

# For verification, used to strip added annotations:
stylePattern = re.compile(r'\[vu-[a-z-]*\]')
linkPattern = re.compile(r'<<vu-[a-z-_]*,')
newLinePattern = re.compile(r' \+$', flags=re.MULTILINE)

def isCodifiedVU(para):
    """Whether this is a legacy VU written in prose, or a codified VU that can
    be parsed.  For simplicity, codified VUs are distinguished with their
    starting line that is in one of the following forms:

    - if ...
    - for ...
    - lvalue = ...
    - require(

    Note that VUs written in prose are capitalized."""

    # Get the first line and remove bullet point (`* `) if any
    firstline = para[0].lstrip()
    if firstline[0] == '*':
        firstline = firstline[1:].lstrip()

    isIf = firstline.startswith('if ')
    isFor = firstline.startswith('for ')
    isAssign = assignmentPattern.search(firstline) is not None
    isRequire = firstline.startswith('require(')

    return isIf or isFor or isAssign or isRequire


def removeBulletPoint(vuText):
    bulletRemoved = vuText

    indent = len(vuText[0]) - len(vuText[0].lstrip())

    if vuText[0][indent] == '*':
        postBulletPoint = vuText[0][(indent+1):]
        indent += len(postBulletPoint) - len(postBulletPoint.lstrip()) + 1
        bulletRemoved[0] = ' ' * indent + postBulletPoint.lstrip()

    return bulletRemoved


def removeIndent(vuText):
    """Make the first line have 0 indent to satisfy the python parser."""
    indent = len(vuText[0]) - len(vuText[0].lstrip())

    indentRemoved = []
    for line in vuText:
        # Make sure input is at least indented as much as the first line.
        assert(line[:indent].strip() == '')
        indentRemoved.append(line[indent:])

    return indentRemoved, indent


def convertMacrosToVuLanguage(macros):
    """During transition, let the adoc macros retain their current form (i.e.
    C-style).  This function transforms them to the VU language (i.e.
    python-style)."""
    converted = {}

    for macro, value in macros.items():
        # remove pname: (currently the only adoc macro in a macro value)
        vuValue = value.replace('pname:', '')

        # Change -> to .
        vuValue = vuValue.replace('->', '.')

        # Almost all macros are now covered.  Other macros would need to be
        # changed as their VUs are made codified.
        converted[macro] = vuValue

    return converted


def expandVuMacros(vuText, macros):
    """Expand macros (in the form macro(x)) given the dictionary."""
    expanded = vuText

    # A simple text replace of macro(x) will do
    for macro, value in macros.items():
        expanded = expanded.replace('macro(' + macro + ')', value)

    return expanded


def applyMacrosToApiName(macros, apiName):
    """If apiName is {refpage}, replace it according to current macro
    values."""
    if apiName[0] != '{':
        return apiName
    assert(apiName[-1] == '}')

    # It is an error if refpage is not defined.
    macroName = apiName[1:-1]
    if macroName not in macros:
        logErr('API name macro ' + apiName + ' is not defined')
        return apiName

    return macros[macroName]


class VuTypeClass(Enum):
    VOID = 0,
    BOOL = 1,
    NUM = 2,
    BITMASK = 3,
    ENUM = 4,
    STRUCT = 5,
    HANDLE = 6,
    STRUCT_NAME = 7,
    EXTENSION_NAME = 8,

# C type of an expression, for type checking and code generation.
#
# - typeClass: The type class of the type.  Used for coarse-level type checking
#   of spec VUs.
# - typeStr: The actual type.  Used for type checking of spec VUs, specially
#   w.r.t API tokens.  Can also be used for code generation.
# - pointerLevel: How many *s in the type.
# - arrayLen: Whether this is an array type and what its length is.  For VU
#   type checking, its existence is used in addition to pointerLevel to make
#   sure there are no loops on non-array types.  For code generation, the
#   length can be used for generating C++ loops.
VuType = namedtuple(
    'VuType', ['typeClass', 'typeStr', 'pointerLevel', 'arrayLen'], defaults=[0, None])

VuFuncType = namedtuple( 'VuFuncType', ['returnType', 'argTypes'])

VuAttrFuncType = namedtuple(
    'VuAttrType', ['objectType', 'funcType'])

# Some common types:
VOID_TYPE = VuType(VuTypeClass.VOID, 'void')
BOOL_TYPE = VuType(VuTypeClass.BOOL, 'bool')
UINT_TYPE = VuType(VuTypeClass.NUM, 'uint32_t')
NUM_TYPE = VuType(VuTypeClass.NUM, '')
BITMASK_TYPE = VuType(VuTypeClass.BITMASK, '')
ENUM_TYPE = VuType(VuTypeClass.ENUM, '')
STRUCT_TYPE = VuType(VuTypeClass.STRUCT, '')
HANDLE_TYPE = VuType(VuTypeClass.HANDLE, '')
STRUCT_NAME_TYPE = VuType(VuTypeClass.STRUCT_NAME, '')
EXTENSION_NAME_TYPE = VuType(VuTypeClass.EXTENSION_NAME, '')

# List of builtins that are used like standalone functions.  Like
# `require(...)`.
FUNC_BUILTINS = {
    # void require(bool)
    'require' : VuFuncType(VOID_TYPE, [BOOL_TYPE]),
    # bool has_pnext(struct_name)
    'has_pnext': VuFuncType(BOOL_TYPE, [STRUCT_NAME_TYPE]),
    # struct pnext(struct_name)
    'pnext': VuFuncType(STRUCT_TYPE, [STRUCT_NAME_TYPE]),
    # uint32_t loop_index(loop_variable)
    'loop_index': VuFuncType(UINT_TYPE, [VOID_TYPE]),
    # bool ext_enabled(ext_name)
    'ext_enabled': VuFuncType(BOOL_TYPE, [EXTENSION_NAME_TYPE]),
    # bool externally_synchronized(handle)
    'externally_synchronized': VuFuncType(BOOL_TYPE, [HANDLE_TYPE]),
    # macro() is used like a function, but is never visible in the output
    'macro': VuFuncType(VOID_TYPE, [VOID_TYPE]),
}

# List of builtins that are used as if they are attributes.  Like
# `flags.has_bit(...)`.
ATTR_BUILTINS = {
    # bool struct.has_pnext(struct_name)
    'has_pnext': VuAttrFuncType(STRUCT_TYPE, VuFuncType(BOOL_TYPE, [STRUCT_NAME_TYPE])),
    # struct struct.pnext(struct_name)
    'pnext': VuAttrFuncType(STRUCT_TYPE, VuFuncType(STRUCT_TYPE, [STRUCT_NAME_TYPE])),
    # bool bitfield.has_bit(enum)
    'has_bit': VuAttrFuncType(BITMASK_TYPE, VuFuncType(BOOL_TYPE, [ENUM_TYPE])),
    # bool bitfield.any()
    'any': VuAttrFuncType(BITMASK_TYPE, VuFuncType(BOOL_TYPE, [])),
    # bool bitfield.none()
    'none': VuAttrFuncType(BITMASK_TYPE, VuFuncType(BOOL_TYPE, [])),
    # bool handle.valid()
    'valid': VuAttrFuncType(HANDLE_TYPE, VuFuncType(BOOL_TYPE, [])),
    # Vk*CreateInfo handle.create_info()
    'create_info': VuAttrFuncType(HANDLE_TYPE, VuFuncType(STRUCT_TYPE, [])),
    # VkGraphics*CreateInfo handle.graphics_create_info()
    'graphics_create_info': VuAttrFuncType(HANDLE_TYPE, VuFuncType(STRUCT_TYPE, [])),
    # VkCompute*CreateInfo handle.compute_create_info()
    'compute_create_info': VuAttrFuncType(HANDLE_TYPE, VuFuncType(STRUCT_TYPE, [])),
    # VkRayTracing*CreateInfo handle.raytracing_create_info()
    'raytracing_create_info': VuAttrFuncType(HANDLE_TYPE, VuFuncType(STRUCT_TYPE, [])),
}

class VuFormat(Enum):
    # Format for adoc source.  Used by reflow.py
    SOURCE = 0,
    # Format for output, with syntax highlighting etc.
    OUTPUT = 1,


class VuFormatter(ast.NodeVisitor):
    """A helper class to format a VU.

    This is used by reflow.py to format the VUs in the input files.  It is also
    used during build to format the VU appropriately for output, e.g. with
    links, syntax highlighting etc."""
    def __init__(self, entity_db, fmt, filename, fileline):
        # entity_db is not used when formatting source
        assert(fmt == VuFormat.SOURCE or entity_db is not None)

        self.entity_db = entity_db
        """EntityDatabase used to look up symbols used by the VU."""

        self.filename = filename
        self.fileline = fileline
        """Location of VU."""

        self.indent = 0
        """The current amount of indent."""

        assert(fmt in [VuFormat.SOURCE, VuFormat.OUTPUT])
        self.fmt = fmt
        """How to format the code."""

        self.formatted = []
        """The result formatted VU.  A "global" to avoid passing around and
        simplify the code."""

    def format(self, ast, isWholeTree = True):
        """Format a given AST"""
        self.indent = 0
        self.formatted = []

        self.beginStyle('vu', '#')
        self.visit(ast)
        self.endStyle('#')

        formatted = ''.join(self.formatted)

        if isWholeTree:
            self.verifyIdentical(ast, formatted)

        # Join the pieces to get the final output
        return formatted

    def verifyIdentical(self, tree, formatted):
        """Verify that the formatted text is syntactically identical to the input."""

        toVerify = formatted
        if self.fmt == VuFormat.OUTPUT:
            # Strip all annotations first
            toVerify = toVerify.replace('[vu]', '')
            toVerify = toVerify.replace('&nbsp;', ' ')
            toVerify = re.sub(stylePattern, '', toVerify)
            toVerify = re.sub(linkPattern, '', toVerify)
            toVerify = re.sub(newLinePattern, '', toVerify)
            toVerify = toVerify.replace('#', '')
            toVerify = toVerify.replace('>>', '')
            toVerify = toVerify.replace('ename:', '')
            toVerify = toVerify.replace('sname:', '')
            toVerify = toVerify.replace('fname:', '')
            toVerify = toVerify.replace('dname:', '')
            toVerify = toVerify.replace('tname:', '')
            toVerify = toVerify.replace('elink:', '')
            toVerify = toVerify.replace('slink:', '')
            toVerify = toVerify.replace('flink:', '')
            toVerify = toVerify.replace('dlink:', '')
            toVerify = toVerify.replace('tlink:', '')

        try:
            formattedTree = ast.parse(toVerify, self.filename, 'exec')
        except SyntaxError as exc:
            logPrefix = self.filename + ':' + str(self.fileline) + ':'
            logErr('Internal error: Parse error after reformatting VU:' , exc)
            return

        if ast.dump(formattedTree) != ast.dump(tree):
            logPrefix = self.filename + ':' + str(self.fileline) + ':'
            logWarn(ast.dump(tree, indent=' '))
            logWarn(ast.dump(formattedTree, indent=' '))
            logErr(logPrefix, 'Internal error: Reformatted VU is different from original VU')

    def add(self, text):
        self.formatted.append(text)

    def beginScope(self):
        # Scope always begins with : and a new line
        self.add(':')
        self.endLine()
        self.indent += 1

    def endScope(self):
        # Nothing to do on scope end, just reduce the indent level
        self.indent -= 1

    def beginParenthesis(self):
        # When parentheses are opened, add a larger indentation level for the
        # expressions that are placed in the following lines.  This makes it
        # less confusing if a scope is opened after the parentheses.  4 is
        # chosen so that the common case of an `if` has its expressions
        # aligned:
        #
        #  if (first_expression and
        #      second_expression and
        #      third_expression):
        #   body
        self.add('(')
        self.indent += 4

    def endParenthesis(self):
        self.add(')')
        self.indent -= 4

    def beginLine(self):
        space = ' ' if self.fmt == VuFormat.SOURCE else '&nbsp;'
        self.add(space * self.indent)

    def endLine(self):
        # For SOURCE formatting, just a new line is sufficient.  For OUTPUT
        # formatting, add ` +` to make sure there is a line break in the
        # output.
        if self.fmt == VuFormat.OUTPUT:
            self.add(' +')
        self.add('\n')

    def beginStyle(self, style, delimiter = '##'):
        if (self.fmt == VuFormat.OUTPUT):
            self.add('[' + style + ']' + delimiter)

    def endStyle(self, delimiter = '##'):
        if (self.fmt == VuFormat.OUTPUT):
            self.add(delimiter)

    def beginLink(self, link):
        if (self.fmt == VuFormat.OUTPUT):
            self.add('<<' + link + ',')

    def endLink(self):
        if (self.fmt == VuFormat.OUTPUT):
            self.add('>>')

    def addReference(self, tag, ref):
        assert(self.fmt == VuFormat.OUTPUT)
        self.add(tag)
        self.add(ref)

    def addOperator(self, op, preSpace = ' ', postSpace = ' '):
        # Output: ` op `
        self.add(preSpace)
        self.beginStyle('vu-operator')
        self.add(op)
        self.endStyle()
        self.add(postSpace)

    def addNumber(self, num):
        self.beginStyle('vu-number')
        self.add(str(num))
        self.endStyle()

    def addKeyword(self, keyword, preSpace = '', postSpace = ' '):
        # Output: `keyword `
        self.add(preSpace)
        self.beginStyle('vu-keyword')
        self.add(keyword)
        self.endStyle()
        self.add(postSpace)

    def addBuiltIn(self, builtin):
        # Output: <<vu-builtin-name,[vu-builtin]#name#>>
        self.beginStyle('vu-builtin')
        self.beginLink('vu-builtin-' + builtin)
        self.add(builtin)
        self.endLink()
        self.endStyle()

    def addAPIToken(self, token, prefix):
        self.add(prefix)
        self.add(token)

    def addBody(self, statements):
        # Handle a list of statements, adding indentation appropriately
        # Do not end the last line.  If nested, the parent body will end the
        # line.
        first = True
        for statement in statements:
            if not first:
                self.endLine()
            first = False

            self.beginLine()
            self.visit(statement)

    # Map of op classes to their textual representation
    opMap = {
        # Found in BoolOp
        ast.And: 'and',
        ast.Or: 'or',
        # Found in BinOp
        ast.Add: '+',
        ast.Sub: '-',
        ast.Mult: '*',
        ast.MatMult: '@',
        ast.Div: '/',
        ast.Mod: '%',
        ast.Pow: '**',
        ast.LShift: '<<',
        ast.RShift: '>>',
        ast.BitOr: '|',
        ast.BitXor: '^',
        ast.BitAnd: '&',
        ast.FloorDiv: '//',
        # Found in UnaryOp
        ast.Invert: '~',
        ast.Not: 'not',
        ast.UAdd: '+',
        ast.USub: '-',
        # Found in CompOp
        ast.Eq: '==',
        ast.NotEq: '!=',
        ast.Lt: '<',
        ast.LtE: '<=',
        ast.Gt: '>',
        ast.GtE: '>=',
        ast.Is: 'is',
        ast.IsNot: 'is not',
        ast.In: 'in',
        ast.NotIn: 'not in',
    }

    def addMaybeParentheses(self, value, needsParentheses):
        if needsParentheses:
            self.beginParenthesis()

        self.visit(value)

        if needsParentheses:
            self.endParenthesis()

    def addParenthesizedExpression(self, value):
        # Add parentheses around value unless obviously unnecessary.  This
        # function is called when `value` is used in another expression with an
        # operator, and operator priorities would change the expression if not
        # parenthesized.
        #
        # Note that BoolOp is currently always parenthesized.
        needsParentheses = value.__class__ not in [ast.Call, ast.Attribute,
                                                   ast.Subscript, ast.Name,
                                                   ast.Constant, ast.BoolOp]
        if needsParentheses and value.__class__ == ast.UnaryOp:
            needsParentheses = value.op.__class__ == ast.Not

        self.addMaybeParentheses(value, needsParentheses)

    def addBinaryExpression(self, left, op, right):
        # Output: left op right
        #
        # This function deals with parenthesization based on operator
        # priorities.  In some cases, no parenthesization is needed if left or
        # right are also binary operators with the same op (like +).  In some
        # cases, parenthesization is still necessary (like ==).
        #
        # For simplicity, this function is not avoiding parentheses according
        # to complex rules, but rather only handles what can be found in VUs:
        #
        #   (a +,- b) +,- c
        #   (a *,/,% b) +,-,*,/,% c
        #   a +,- (c *,/,% d)
        #   binary compare binary
        #   TODO: add more as they are encountered
        #
        # Note that python parses a + b + c (and similar) as (a + b) + c, so
        # it is only the left node is checked for those expressions.
        #
        # Note also that all binary operators have a smaller precedence than
        # compare operators.
        #
        # If necessary, the ast.unparse implementation in Python has generic
        # operator-priority-based code that can be used.
        leftOp = left.op if isinstance(left, ast.BinOp) else None
        rightOp = right.op if isinstance(right, ast.BinOp) else None

        parenthesizeLeftOp = True
        parenthesizeRightOp = True

        # Same priority arithmetic ops nested under - and +
        if (op.__class__ in [ast.Add ,ast.Sub] and
              leftOp.__class__ in [ast.Add, ast.Sub]):
            parenthesizeLeftOp = False
        # Higher or same priority arithmetic ops nested under +, -, *, / and %
        if (op.__class__ in [ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod] and
            leftOp.__class__ in [ast.Mult, ast.Div, ast.Mod]):
            parenthesizeLeftOp = False

        # Higher priority arithmetic ops nested under + and - on the right
        if (op.__class__ in [ast.Add, ast.Sub] and
            rightOp.__class__ in [ast.Mult, ast.Div, ast.Mod]):
            parenthesizeRightOp = False

        # Binary operator nested under compare operator
        opIsCompare = op.__class__ in [ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
                                       ast.Gt, ast.GtE]
        if opIsCompare and isinstance(left, ast.BinOp):
            parenthesizeLeftOp = False
        if opIsCompare and isinstance(right, ast.BinOp):
            parenthesizeRightOp = False


        if parenthesizeLeftOp:
            self.addParenthesizedExpression(left)
        else:
            self.visit(left)

        opText = self.opMap[op.__class__]
        self.addOperator(opText)

        if parenthesizeRightOp:
            self.addParenthesizedExpression(right)
        else:
            self.visit(right)


    # AST nodes of class ast.Foo are handled by the visit_Foo function.
    # Not all AST nodes are handled as they are not used in VUs, e.g.
    # ast.Yield or ast.ClassDef.
    #
    # Please refer to the ast module reference at:
    # https://docs.python.org/3/library/ast.html

    def visit_Module(self, node):
        # Output: Each statement on a new line
        self.addBody(node.body)

    def visit_Assign(self, node):
        # Verified by VuVerifier
        assert(len(node.targets) == 1)

        # Output: target = value
        self.visit(node.targets[0])
        self.addOperator('=')
        self.visit(node.value)

    def visit_If(self, node):
        # Output: if test:
        #            body
        self.addKeyword('if')
        self.visit(node.test)

        self.beginScope()
        self.addBody(node.body)
        self.endScope()

    def visit_For(self, node):
        # Output: for target in iter:
        #            body
        self.addKeyword('for')
        self.visit(node.target)
        self.addOperator('in')
        self.visit(node.iter)

        self.beginScope()
        self.addBody(node.body)
        self.endScope()

    def visit_While(self, node):
        # Output: while test:
        #             body
        #
        # Note: implemented to have more coverage, but unlikely to be used by VUs
        self.addKeyword('while')
        self.visit(node.test)

        self.beginScope()
        self.addBody(node.body)
        self.endScope()

    def visit_Break(self, node):
        # Note: implemented to have more coverage, but unlikely to be used by VUs
        self.addKeyword('break', postSpace = '')

    def visit_Continue(self, node):
        # Note: implemented to have more coverage, but unlikely to be used by VUs
        self.addKeyword('continue', postSpace = '')

    def visit_BoolOp(self, node):
        # Output: (values[0] op
        #          values[1] op
        #          ...)

        # Handle parenthesization and line breaks.  Bool operations are always
        # parenthesized because in practice conditions in VUs end up quite
        # lengthy.  This also simplifies the logic a bit.
        opText = self.opMap[node.op.__class__]

        self.beginParenthesis()

        assert(len(node.values) > 1)

        first = True
        for value in node.values:
            # Add the operator and break the line.  The expression would look
            # like:
            #
            # (values[0] op
            #  values[1] op
            #  values[2])
            if not first:
                self.addOperator(opText, postSpace = '')
                self.endLine()
                self.beginLine()
            first = False

            # Of supported nodes, only IfExp has lower priority than boolean
            # expressions, so parenthesize those.
            needsParentheses = isinstance(value, ast.IfExp)
            self.addMaybeParentheses(value, needsParentheses)

        self.endParenthesis()


    def visit_UnaryOp(self, node):
        # Output: opoperand
        # For `not`, output `not operand`
        postSpace = ' ' if isinstance(node.op, ast.Not) else ''
        opText = self.opMap[node.op.__class__]
        self.addOperator(opText, preSpace = '', postSpace = postSpace)
        self.addParenthesizedExpression(node.operand)

    def visit_BinOp(self, node):
        self.addBinaryExpression(node.left, node.op, node.right);

    def visit_Compare(self, node):
        assert(len(node.ops) == 1)
        self.addBinaryExpression(node.left, node.ops[0], node.comparators[0]);

    def visit_Call(self, node):
        # Output: func(arg, arg, ...)
        #
        # Builtin function calls do not accept complex boolean arguments, except
        # for `require`.  Since boolean arguments unconditionally get
        # parenthesized, parentheses are not added here for `require(BoolOp)`.
        # For now, this is the simpler method to avoid double parenthesization.
        self.visit(node.func)

        argumentIsParenthesized = (len(node.args) == 1 and
                                   isinstance(node.args[0], ast.BoolOp))

        if not argumentIsParenthesized:
            self.beginParenthesis()

        first = True
        for arg in node.args:
            if not first:
                self.add(', ')
            first = False

            self.visit(arg)

        if not argumentIsParenthesized:
            self.endParenthesis()

    def visit_Attribute(self, node):
        # Output: value.attr
        self.visit(node.value)
        self.add('.')

        # If it is a builtin, make a link to the reference.
        if node.attr in ATTR_BUILTINS.keys():
            self.addBuiltIn(node.attr)
        else:
            self.add(node.attr)

    def visit_Subscript(self, node):
        # Output: value[slice]
        self.visit(node.value)
        self.add('[')
        self.visit(node.slice)
        self.add(']')

    def visit_IfExp(self, node):
        # Output: body if test else orelse
        self.visit(node.body)
        self.addKeyword('if', preSpace = ' ')
        self.visit(node.test)
        self.addKeyword('else', preSpace = ' ')
        self.visit(node.orelse)

    def visit_Constant(self, node):
        # Output: [vu-number]#value#
        self.beginStyle('vu-number')
        if isinstance(node.value, str):
            self.add("'" + node.value + "'")
        else:
            self.add(str(node.value))
        self.endStyle()

    def visit_Name(self, node):
        # If it is a builtin, make a link to the reference.
        if node.id in FUNC_BUILTINS.keys():
            # Make sure `macro()` never makes it to the output.
            if self.fmt == VuFormat.OUTPUT:
                assert(node.id != 'macro')

            self.addBuiltIn(node.id)
            return

        # If it is an API entity, add the appropriate prefix such as slink: etc.
        # Otherwise outputting it plainly is sufficient.  No need for pname: on
        # members, function arguments etc, as the VU is already rendered in
        # monospace.
        if (self.fmt == VuFormat.OUTPUT):
            entity = self.entity_db.findEntity(node.id)
            if entity is None or entity.macro is None:
                self.add(node.id)
            else:
                self.addReference(entity.macro + ':', node.id)
        else:
            self.add(node.id)

    # Although unsupported, the following are also output correctly for the
    # sake of VuVerifier.  When the expression is invalid, it will output why
    # and would need the expression formatted well.
    def visit_Tuple(self, node):
        delimiter = '('
        for elt in node.elts:
            self.add(delimiter)
            delimiter = ', '
            self.visit(elt)
        self.add(')')

    def visit_List(self, node):
        delimiter = '['
        for elt in node.elts:
            self.add(delimiter)
            delimiter = ', '
            self.visit(elt)
        self.add(']')


class VuTypeExtractor:
    """Helper class to extract types out of symbols used in the VU.  Used for
    type checking and code generation."""
    def __init__(self, entity_db, api):
        self.entity_db = entity_db
        self.api = api

    def getSymbolType(self, symbol):
        """Called on a symbol that needs identification.  Not called on
        builtsin, lhs of assignments or loop variables"""
        if symbol == 'NULL':
            return VuType(VuTypeClass.VOID, '', 1)

        if symbol == 'VK_NULL_HANDLE':
            return VuType(VuTypeClass.HANDLE, 'VK_NULL_HANDLE')

        # The symbol could be a member of the API entity (if struct) or a
        # function argument of it (if command).
        memberType = self.getMemberOrArgumentSymbolType(self.api, symbol)
        if memberType is not None:
            return memberType

        # The symbol could also be an API token such as a struct name or enum.
        return self.getAPIType(symbol)

    def getMemberOrArgumentSymbolType(self, api, symbol):
        """Get the type of a struct member or function field."""
        # For the specific case of 'VkPipelineCreateInfo' and 'flags', use any
        # of the real Vk*PipelineCreateInfo types.  They all have flags.  This
        # is by far the most common use case of pipeline.create_info(), so it
        # is nice to support that without resorting to graphics_create_info()
        # etc.
        if api == 'VkPipelineCreateInfo' and symbol == 'flags':
            api = 'VkGraphicsPipelineCreateInfo'
        members = self.entity_db.getMemberElems(api)
        if members is None:
            logWarn('Invalid API name', api)
            if api == 'VkPipelineCreateInfo':
                logWarn('Use graphics_create_info, compute_create_info or raytracing_create_info for pipelines')
            return None

        for member in members:
            name = util.getElemName(member)
            if symbol == name:
                return self.getMemberType(member)

        # If no members, check to see if this is an alias
        entity = self.entity_db.findEntity(api)
        if entity is not None:
            alias = entity.elem.get('alias')
            if alias:
                return self.getMemberOrArgumentSymbolType(alias, symbol)

        # VU contains an unrecognized symbol
        return None

    def getMemberType(self, elem):
        """Get the type of a struct field or function argument."""
        typeStr = util.getElemType(elem)
        nameTail = elem.find('name').tail.strip() if elem.find('name').tail is not None else ''
        typeTail = elem.find('type').tail.strip()

        pointerLevel = 0
        arrayLen = elem.attrib.get('len')

        # Handle fixed sized arrays like
        # <member limittype="noauto"><type>char</type> <name>deviceName</name>[<enum>VK_MAX_PHYSICAL_DEVICE_NAME_SIZE</enum>]</member>
        if arrayLen is None and nameTail != '' and nameTail[0] == '[':
            arrayLen = elem.find('enum').text
            pointerLevel = 1

        # typeTail can contain * to specify a pointer type.
        if '*' in typeTail:
            # Note that non * characters can exist too, for example like `* const *`
            pointerLevel += typeTail.count('*')

        # Find the class type.
        apiType = self.getAPIType(typeStr)
        typeClass = VuTypeClass.VOID

        if apiType is not None:
            typeClass = apiType.typeClass

            # A member is not a struct 'name', but an actual struct
            # The distinction helps elsewhere make sure a type name is not used
            # where an instance of the type is expected.
            if typeClass == VuTypeClass.STRUCT_NAME:
                typeClass = VuTypeClass.STRUCT

        return VuType(typeClass, typeStr, pointerLevel, arrayLen)

    def getAPIType(self, name):
        numTypes = ['char', 'float', 'double', 'int8_t', 'uint8_t', 'int16_t',
                    'uint16_t', 'uint32_t', 'uint64_t', 'int32_t', 'int64_t',
                    'size_t', 'int', 'VkBool32', 'VkDeviceSize',
                    'VkDeviceAddress']
        if name in numTypes:
            return VuType(VuTypeClass.NUM, name)

        if name in ['VkSampleMask', 'VkFlags', 'VkFlags64']:
            return VuType(VuTypeClass.BITMASK, name)

        entity = self.entity_db.findEntity(name)
        if entity is None:
            return None

        classMap = {'flags': VuTypeClass.BITMASK,
                    'enumvalues': VuTypeClass.ENUM,
                    'handles': VuTypeClass.HANDLE,
                    'basetypes': VuTypeClass.HANDLE,
                    'structs': VuTypeClass.STRUCT_NAME,
                    'enums': VuTypeClass.ENUM,
                    'extension': VuTypeClass.EXTENSION_NAME,
                    'code': VuTypeClass.VOID,
        }

        typeClass = classMap[entity.category]
        if typeClass is None:
            return None

        # Extensions do not have a type an the XML
        if typeClass == VuTypeClass.EXTENSION_NAME:
            return VuType(typeClass, name)

        # if one of API Constants, it is considered an enum in XML, while it is
        # really just a number.
        if entity.category == 'enumvalues':
            constantType = util.getElemType(entity.elem)
            if constantType in numTypes:
                return VuType(VuTypeClass.NUM, constantType)

        # If an enum value, we are more interested in its real type, but
        # unfortunately that is not efficiently available at the moment.  For
        # example, for VK_IMAGE_TYPE_1D, we would ideally change the typeStr to
        # VkImageType.

        return VuType(typeClass, name)

    # Evaluate the type of array[index]
    def getIndexedArrayType(self, arrayType):
        # Reduce one pointer level.  If VU has errors (and subscripts a
        # non-pointer), an error is generated but guard against it here so
        # compilation can continue.
        pointerLevel = max(arrayType.pointerLevel - 1, 0)
        # Note: 2D arrays are rare in the spec, and they do not specify the
        # length of the inner dimensions.  This needs to be fixed.
        arrayLen = None if pointerLevel == 0 else 'UNSPECIFIED'
        return VuType(arrayType.typeClass, arrayType.typeStr, pointerLevel, arrayLen)

    # Evaluate the type of a.b
    def getStructAttributeType(self, objectType, fieldName):
        return self.getMemberOrArgumentSymbolType(objectType.typeStr, fieldName)

    # Determine whether enum value belongs to enum type:
    def isValueOfEnum(self, enumType, valueType):
        """Test whether VK_FOO is an enum in VkFoo."""
        assert(enumType.typeClass in [VuTypeClass.ENUM, VuTypeClass.BITMASK])
        assert(valueType.typeClass == VuTypeClass.ENUM)
        assert('_' not in enumType.typeStr)
        assert('_' in valueType.typeStr)

        # TODO: Currently, entity_db does not seem to have enough info to
        # answer this.
        return True

    def getBitmaskBitsType(self, bitmaskType):
        """Get the VkFooFlagBits type from VkFooFlags."""
        entity = self.entity_db.findEntity(bitmaskType.typeStr)
        if entity is None:
            return bitmaskType

        if entity.category != 'flags':
            return bitmaskType

        bitsType = entity.elem.attrib.get('requires')
        if bitsType is None:
            return bitmaskType

        return VuType(VuTypeClass.BITMASK, bitsType, bitmaskType.pointerLevel, bitmaskType.arrayLen)

        #if bitmaskType[-5:] != 'Flags':
        #    return None

        # TODO: Find a way to extract this from the xml
        #return self.getAPIType(bitMaskType[:-5] + 'FlagBits')


class VuVerifier(ast.NodeVisitor):
    """Verify that the VU is semantically valid"""
    def __init__(self, entity_db, api, filename, fileline):
        self.entity_db = entity_db
        self.api = api

        self.typeExtractor = VuTypeExtractor(entity_db, api)
        """Helper to extract types out of symbols."""

        self.filename = filename
        self.fileline = fileline
        """Location of VU."""

        self.passed = False
        """Whether verification passed."""

        self.requireSeen = False
        """Whether the require() call was seen."""

        self.variableTypeMap = {}
        """A simple name->VuType map.  Scoping is not taken into account for
        simplicity."""

        self.loopVariableSet = set()
        """A simple set of names of loop variables.  Scoping is not taken into
        account for simplicity."""

    def formatNode(self, node):
        formatter = VuFormatter(self.entity_db, VuFormat.SOURCE, self.filename, self.fileline)
        return formatter.format(node, isWholeTree = False)

    def fail(self, nodes, *args):
        logWarn(self.filename + ':' + str(self.fileline) + ':', *args)
        # Output the offending node.  Indent it by 4 spaces + 7 for 'WARN:  '
        # as added by logWarn.  Remove 7 spaces from the indentation of the
        # first line (because of the WARN: tag, so it aligns with the lines
        # below it, if any.
        def formatForLog(expression):
            return '\n'.join([''.ljust(11) + line for line in
                              expression.splitlines()])

        formatted = formatForLog(self.formatNode(nodes[0]))[7:]
        for node in nodes[1:]:
            formatted += '\n' + ''.ljust(7) + 'vs\n'
            formatted += formatForLog(self.formatNode(node))
        logWarn(formatted)
        self.passed = False

    def verify(self, ast):
        self.passed = True
        self.visit(ast)
        if not self.requireSeen:
            self.fail([ast], 'VUs must contain at least one require()')
        return self.passed

    def onRequireVisited(self):
        # Rembmer that require is visited.  If it is never seen, that is an
        # error.  Currently, more than one require can be present, but if that
        # is to be constrained, an error can be generated here, as well as in
        # visitBody() to make sure there are no statements after a require().
        self.requireSeen = True

    def visitBody(self, body):
        for statement in body:
            self.visit(statement)

    def visit_Assign(self, node):
        # Verify that there are not multiple assignments (like a = b = c).
        if len(node.targets) != 1:
            self.fail([node.targets[0], node.targets[1]], 'Cascaded assignments are not allowed')
        # Verify that the target of assignment is a single variable.
        if not isinstance(node.targets[0], ast.Name):
            self.fail([node.targets[0]], 'Assignment target must be a single variable')
            return
        # Verify that the target is not an API entity
        if self.entity_db.findEntity(node.targets[0].id) is not None:
            self.fail([node.targets[0]], 'Invalid assignment to API token')
        # Verify that the target is not a member/argument of the API being defined
        elif self.typeExtractor.getSymbolType(node.targets[0].id) is not None:
            self.fail([node.targets[0]], 'Invalid assignment to VU parameter')
        # Verify that the target is not a builtin
        elif node.targets[0].id in FUNC_BUILTINS.keys() or node.targets[0].id in ATTR_BUILTINS.keys():
            self.fail([node.targets[0]], 'Invalid assignment to builtin')

        # Visit RHS first, and get its type.  It is assigned to the LHS
        rhsType = self.visit(node.value)
        self.variableTypeMap[node.targets[0].id] = rhsType

    def visitCondition(self, testNode, context):
        testType = self.visit(testNode)
        if testType.pointerLevel != 0:
            self.fail([testNode], 'Condition of ' + context + ' cannot be a pointer.  Use comparison with NULL')
        elif testType.typeClass != VuTypeClass.BOOL:
            self.fail([testNode], 'Condition of ' + context + ' must be boolean')
        return testType

    def visit_If(self, node):
        # Verify that the test type is a boolean
        self.visitCondition(node.test, 'if')
        self.visitBody(node.body)

    def visit_For(self, node):
        # Verify that the loop target is a single variable
        if not isinstance(node.target, ast.Name):
            self.fail([node.target], 'Loop target must be a single variable')
            return
        # Verify that the loop iterator is not a list or tuple
        if isinstance(node.iter, ast.Tuple) or isinstance(node.iter, ast.List):
            self.fail([node.target], 'Loop iterator cannot be a list or tuple')
            return

        # Verify that the loop target is not a builtin
        if node.target.id in FUNC_BUILTINS.keys() or node.target.id in ATTR_BUILTINS.keys():
            self.fail([node.target], 'Loop target cannot have the name of a builtin')

        # Verify that the loop iterator is an array
        iterType = self.visit(node.iter)
        if iterType.pointerLevel == 0 or iterType.arrayLen is None:
            self.fail([node.iter], 'Loop iterator must be an array')

        # Assign the iterator type (minus one array level) to the target
        targetType = self.typeExtractor.getIndexedArrayType(iterType)
        self.variableTypeMap[node.target.id] = targetType
        self.loopVariableSet.add(node.target.id)

        self.visitBody(node.body)

    def visit_While(self, node):
        # Verify that the test type is a boolean
        self.visitCondition(node.test, 'while')
        self.visitBody(node.body)

    def visit_BoolOp(self, node):
        # All values must be boolean too
        for value in node.values:
            valueType = self.visit(value)
            if valueType.typeClass != VuTypeClass.BOOL:
                self.fail([value], 'Parameter of boolean operation must be boolean')
            if valueType.pointerLevel != 0:
                self.fail([value], 'Parameter of boolean operation cannot be a pointer.  Use comparison with NULL')
        return BOOL_TYPE

    def visit_UnaryOp(self, node):
        operandType = self.visit(node.operand)
        if operandType.pointerLevel != 0:
            self.fail([node.operand], 'Operand of unary operation cannot be a pointer.  Use comparison with NULL')

        # Operand of not must be a boolean
        if isinstance(node.op, ast.Not):
            if operandType.typeClass != VuTypeClass.BOOL:
                self.fail([node.operand], 'Operand of `not` must be boolean')
            return BOOL_TYPE

        # Operand of ~ must be a bitmask
        if isinstance(node.op, ast.Invert):
            if operandType.typeClass != VuTypeClass.BITMASK:
                self.fail([node.operand], 'Operand of `~` must be a bitmask')
                return BITMASK_TYPE
            else:
                return operandType

        # Operand of + and - must be a number
        assert(isinstance(node.op, ast.UAdd) or isinstance(node.op, ast.USub))

        if operandType.typeClass != VuTypeClass.NUM:
            self.fail([node.operand], 'Operand of unary `+`/`-` must be a number')
        return NUM_TYPE

    def doEnumTypesMatch(self, leftType, rightType):
        # Support matching the following:
        #
        # VK_FOO and VK_BAR
        # VkFoo and VK_FOO
        # VkFooFlags and VKFooFlagBits
        # VkFooFlags and VK_FOO_BIT

        assert(leftType.typeClass in [VuTypeClass.ENUM, VuTypeClass.BITMASK])
        assert(rightType.typeClass in [VuTypeClass.ENUM, VuTypeClass.BITMASK])
        if leftType.typeStr == rightType.typeStr:
            return True

        # Simplify VkFooFlags to VkFooFlagBits
        if leftType.typeClass == VuTypeClass.BITMASK:
            leftType = self.typeExtractor.getBitmaskBitsType(leftType)
        if rightType.typeClass == VuTypeClass.BITMASK:
            rightType = self.typeExtractor.getBitmaskBitsType(rightType)

        # If both are bitfields, they should match in type exactly
        if (leftType.typeClass == VuTypeClass.BITMASK and
            rightType.typeClass == VuTypeClass.BITMASK):
            return leftType.typeStr == rightType.typeStr

        # One must be in the form VkFoo and another VK_FOO
        enumType, valueType = leftType, rightType
        if '_' in leftType.typeStr:
            enumType, valueType = rightType, leftType

        return self.typeExtractor.isValueOfEnum(enumType, valueType)

    def doHandleTypesMatch(self, leftType, rightType):
        assert(leftType.typeClass == rightType.typeClass == VuTypeClass.HANDLE)
        if leftType.typeStr == rightType.typeStr:
            return True

        # Match handle types if one of them is VK_NULL_HANDLE
        return leftType.typeStr == 'VK_NULL_HANDLE' or rightType.typeStr == 'VK_NULL_HANDLE'

    def doBaseTypesMatch(self, leftType, rightType, requireTypeNameMatch):
        # Disregarding pointer levels, check whether base types match

        # Bitfields and enums may need to match, if enum is a member of the bitfield type.
        if requireTypeNameMatch:
            if (leftType.typeClass in [VuTypeClass.ENUM, VuTypeClass.BITMASK] and
                rightType.typeClass in [VuTypeClass.ENUM, VuTypeClass.BITMASK]):
                return self.doEnumTypesMatch(leftType, rightType)

        # For other types, the class should always match
        if leftType.typeClass != rightType.typeClass:
            return False

        # For structs and handles, make sure their API type also matches.
        if requireTypeNameMatch:
            if leftType.typeClass == VuTypeClass.STRUCT:
                return leftType.typeStr == rightType.typeStr
            elif leftType.typeClass == VuTypeClass.HANDLE:
                # For handles, we should allow VK_NULL_HANDLE
                return self.doHandleTypesMatch(leftType, rightType)

        return True

    def doTypesMatch(self, leftType, rightType, requireTypeNameMatch = True):
        # For non-pointer types, they should match by type class only
        if leftType.pointerLevel == 0 and rightType.pointerLevel == 0:
            return self.doBaseTypesMatch(leftType, rightType, requireTypeNameMatch)

        leftPointerLevel = leftType.pointerLevel
        rightPointerLevel = rightType.pointerLevel
        if leftType.typeClass == VuTypeClass.VOID and rightPointerLevel > 0:
            leftPointerLevel = rightPointerLevel
        elif rightType.typeClass == VuTypeClass.VOID and leftPointerLevel > 0:
            rightPointerLevel = leftPointerLevel

        # Make sure pointer and non-pointer (or pointer to pointer) types do not
        # match
        if leftPointerLevel != rightPointerLevel:
            return False

        # Verify that pointer types match (allowing void* to match anything)
        return (leftType.typeClass == VuTypeClass.VOID or
                rightType.typeClass == VuTypeClass.VOID or
                self.doBaseTypesMatch(leftType, rightType, requireTypeNameMatch))

    def visitBinaryCompareOperand(self, left, op, right):
        leftType = self.visit(left)
        rightType = self.visit(right)
        isEqualityCheck = op.__class__ in [ast.Eq, ast.NotEq]

        if not isEqualityCheck:
            if leftType.pointerLevel != 0:
                self.fail([left], 'Operand of binary operation cannot be a pointer.  Use comparison with NULL')
            if rightType.pointerLevel != 0:
                self.fail([right], 'Operand of binary operation cannot be a pointer.  Use comparison with NULL')

        if isEqualityCheck:
            if not self.doTypesMatch(leftType, rightType):
                self.fail([left, right], 'Operands of `==` and `!=` must have matching types')
            return BOOL_TYPE

        if op.__class__ in [ast.Add, ast.Sub, ast.Mult, ast.MatMult, ast.Div,
                            ast.Mod, ast.Pow, ast.FloorDiv]:
            if leftType.typeClass != VuTypeClass.NUM:
                self.fail([left], 'Operands of arithmetic operations must be numbers')
            if rightType.typeClass != VuTypeClass.NUM:
                self.fail([right], 'Operands of arithmetic operations must be numbers')
            return NUM_TYPE

        if op.__class__ in [ast.Lt, ast.LtE, ast.Gt, ast.GtE]:
            if leftType.typeClass != VuTypeClass.NUM:
                self.fail([left], 'Operands of comparison operations must be numbers')
            if rightType.typeClass != VuTypeClass.NUM:
                self.fail([right], 'Operands of comparison operations must be numbers')
            return BOOL_TYPE

        if op.__class__ in [ast.LShift, ast.RShift]:
            if leftType.typeClass != VuTypeClass.NUM:
                self.fail([left], 'Operands of shift operations must be numbers')
            if rightType.typeClass != VuTypeClass.NUM:
                self.fail([right], 'Operands of shift operations must be numbers')
            return NUM_TYPE

        if op.__class__ in [ast.BitOr, ast.BitXor, ast.BitAnd]:
            leftIsBitMask = leftType.typeClass == VuTypeClass.BITMASK
            rightIsBitMask = rightType.typeClass == VuTypeClass.BITMASK
            if not leftIsBitMask:
                self.fail([left], 'Operands of bitwise operations must be bitmasks')
            if not rightIsBitMask:
                self.fail([right], 'Operands of bitwise operations must be bitmasks')
            if leftIsBitMask and rightIsBitMask and not self.doTypesMatch(leftType, rightType):
                self.fail([left, right], 'Operands of bitwise operations must have matching types')

            return leftType if leftIsBitMask else rightType if rightIsBitMask else BITMASK_TYPE

        # Verify that is, is not, in, and not in are not used in VUs.
        # Currently there is no need for them.
        assert(op.__class__ in [ast.Is, ast.IsNot, ast.In, ast.NotIn])
        self.fail([node], 'Unsupported binary operator is, is not, in, not in')
        return BOOL_TYPE

    def visit_BinOp(self, node):
        return self.visitBinaryCompareOperand(node.left, node.op, node.right)

    def visit_Compare(self, node):
        # Verify that compares are binary (like a < b, not like a < b < c).
        if len(node.ops) != 1:
            self.fail([node.left] + node.comparators, 'Only binary comparisons are allowed')

        return self.visitBinaryCompareOperand(node.left, node.ops[0], node.comparators[0])

    def visit_Call(self, node):
        # Only builtins can be called
        funcType = None
        objectType = None
        builtinName = ''
        if isinstance(node.func, ast.Name) and node.func.id in FUNC_BUILTINS.keys():
            builtinName = node.func.id
            funcType = FUNC_BUILTINS[builtinName]
            if builtinName == 'require':
                self.onRequireVisited()
        elif isinstance(node.func, ast.Attribute) and node.func.attr in ATTR_BUILTINS.keys():
            objectType = self.visit(node.func)
            builtinName = node.func.attr
            funcType = ATTR_BUILTINS[builtinName].funcType
        else:
            self.fail([node.func], 'Invalid function call.  If a builtin was intended, it is misspelled')
            return VOID_TYPE

        # Verify that the number of parameters is correct
        if len(node.args) != len(funcType.argTypes):
            self.fail([node.func], 'Invalid number of arguments passed to builtin')
            return funcType.returnType

        # Verify that arguments have the correct type
        argTypes = []
        for arg, expectedType in zip(node.args, funcType.argTypes):
            argType = self.visit(arg)
            argTypes.append(argType)

            # If builtin argument type is VOID, it means it matches anything.
            if expectedType.typeClass == VuTypeClass.VOID:
                continue

            if not self.doTypesMatch(argType, expectedType,
                                     requireTypeNameMatch = False):
                self.fail([arg], 'Mismatching type in argument to builtin', builtinName)
                return funcType.returnType

        # Some builtins require special attention.  For example,
        # pnext(structName) should have the structName in the return type so
        # members of it can be looked up.
        returnType = funcType.returnType
        if builtinName == 'pnext':
            # The returned struct is of the type specified in the argument of this call
            returnType = VuType(returnType.typeClass, node.args[0].id)
        elif builtinName == 'create_info':
            # The returned struct has the name of the handle type + CreateInfo
            returnType = VuType(returnType.typeClass, objectType.typeStr + 'CreateInfo')
        elif builtinName == 'graphics_create_info':
            # Specialized create_info() to disambiguate VkPipeline
            returnType = VuType(returnType.typeClass,
                                objectType.typeStr[:2] + 'Graphics' + objectType.typeStr[2:] + 'CreateInfo')
        elif builtinName == 'compute_create_info':
            # Specialized create_info() to disambiguate VkPipeline
            returnType = VuType(returnType.typeClass,
                                objectType.typeStr[:2] + 'Compute' + objectType.typeStr[2:] + 'CreateInfo')
        elif builtinName == 'raytracing_create_info':
            # Specialized create_info() to disambiguate VkPipeline
            returnType = VuType(returnType.typeClass,
                                objectType.typeStr[:2] + 'RayTracing' + objectType.typeStr[2:] + 'CreateInfo')
        elif builtinName == 'has_bit':
            # has_bit accepts an enum value that must match the type of the
            # object its being called on.  If object is not a bitmask,
            # visit_Attribute has already generated an error.
            if (objectType == VuTypeClass.BITMASK and
                not self.doEnumTypesMatch(objectType, argTypes[0])):
                self.fail([node.func.attr, node.args[0]], 'has_bit argument is not an enum value of the object it is called on')
        elif builtinName == 'loop_index':
            # Only loop variables may be passed to loop_index.
            if not node.args[0].id in self.loopVariableSet:
                self.fail([node.args[0]], 'loop_index argument is not a loop variable')

        # Make sure every struct return value carries the name
        assert(returnType.typeClass != VuTypeClass.STRUCT or returnType.typeStr != '')
        return returnType

    def visit_Attribute(self, node):
        valueType = self.visit(node.value)

        # Implicitly dereference pointers
        valueType = VuType(valueType.typeClass, valueType.typeStr)

        # If attr is a builtin, verify the value type based on the builtin requirements
        if node.attr in ATTR_BUILTINS.keys():
            builtinType = ATTR_BUILTINS[node.attr]

            if not self.doTypesMatch(builtinType.objectType, valueType, requireTypeNameMatch = False):
                self.fail([node.value], 'Invalid object type for attribute builtin', node.attr)

            # Attribute builtin must be called.  The original object type is
            # returned here which can be used by some builtins.
            # visit_Call will make sure the return type is taken from the builtin.
            return valueType

        # Otherwise look up the member in the struct and return its type
        if valueType.typeClass != VuTypeClass.STRUCT:
            self.fail([node.value], 'Invalid use of . on non-struct object.  If a builtin was intended, it is misspelled')
            return valueType

        assert(valueType.typeStr != '')
        fieldType = self.typeExtractor.getMemberOrArgumentSymbolType(valueType.typeStr, node.attr)
        if fieldType is None:
            self.fail([node.value], 'No such attribute', node.attr, 'in struct', valueType.typeStr)
            return valueType

        return fieldType

    def visit_Subscript(self, node):
        # Verify that subscripts are neither Tuples nor Slices.  Otherwise
        # translation to C++ would be harder for VVL.
        if isinstance(node.slice, ast.Tuple):
            self.fail([node.value], 'Tuples in array subscripts are not supported')
        if isinstance(node.slice, ast.Slice):
            self.fail([node.value], 'Ranges in array subscripts are not supported')

        valueType = self.visit(node.value)
        sliceType = self.visit(node.slice)

        # Verify that value is an array
        if valueType.pointerLevel == 0 or valueType.arrayLen is None:
            self.fail([node.value], 'Subscript only allowed on arrays')
        # Verify that slice is a number
        if sliceType.typeClass != VuTypeClass.NUM or sliceType.pointerLevel > 0:
            self.fail([node.slice], 'Array subscript must be a number')

        return self.typeExtractor.getIndexedArrayType(valueType)

    def visit_IfExp(self, node):
        # Verify that the test type is a boolean
        self.visitCondition(node.test, 'ternary operator')

        bodyType = self.visit(node.body)
        orelseType = self.visit(node.orelse)
        if not self.doTypesMatch(bodyType, orelseType):
            self.fail([node.body, node.orelse], 'Expressions in ternary operator must have matching types')

        # To support bitmask vs enum selection, return a bitmask if either is bitmask
        orelseIsBitMask = orelseType.typeClass == VuTypeClass.BITMASK

        return orelseType if orelseIsBitMask else bodyType

    def visit_Constant(self, node):
        if node.value.__class__ == bool:
            return BOOL_TYPE
        return NUM_TYPE

    def visit_Name(self, node):
        # Verify that builtins are not used as variables
        if node.id in FUNC_BUILTINS.keys() or node.id in ATTR_BUILTINS.keys():
            self.fail([node], 'Invalid usage of builtin as variable')
            return VOID_TYPE

        # If this is a variable being referenced, get the type from the variable map
        if node.id in self.variableTypeMap.keys():
            return self.variableTypeMap[node.id]

        # See if this is a member/arg of the API for which validation is written.
        nodeType = self.typeExtractor.getSymbolType(node.id)
        if nodeType is None:
            self.fail([node], 'Unknown token is neither an API token, or a member or argument of', self.api)
            return VOID_TYPE

        return nodeType

class VuParametterTagExtractor(ast.NodeVisitor):
    """A traverser that walks the AST and finds the first reference to a symbol
    that is not otherwise defined.  This symbol must be referencing the
    member/parameter of the API for which validation is written.

    The AST is expected to be valid, i.e. has passed VuVerifier checks.  This
    means that adding VUID tags may fail if the spec does not build."""
    def __init__(self):
        self.tag = None
        """The tag that is extracted.  AST traversal stops once this is done."""

        self.variableSet = set()
        """Set of variables.  Used to know when referenced that they are not to
        be matched as the VUID tag."""

    def getTag(self, ast):
        self.tag = None
        self.visit(ast)
        return self.tag

    def visitBody(self, body):
        for statement in body:
            self.visit(statement)
            if self.tag is not None:
                break

    def visit_Assign(self, node):
        if self.tag is not None:
            return

        # Record the LHS as the variable, and traverse the RHS
        self.variableSet.add(node.targets[0].id)
        self.visit(node.value)

    def visit_If(self, node):
        if self.tag is not None:
            return

        self.visit(node.test)
        self.visitBody(node.body)

    def visit_For(self, node):
        if self.tag is not None:
            return

        # Record the loop variable as such, and traverse the iterator and body
        self.variableSet.add(node.target)
        self.visit(node.iter)
        self.visitBody(node.body)

    def visit_While(self, node):
        if self.tag is not None:
            return

        self.visit(node.test)
        self.visitBody(node.body)

    def visit_Call(self, node):
        if self.tag is not None:
            return

        # Note: function arguments are never a member/parameter, except inside
        # require and externally_synchronized.

        if isinstance(node.func, ast.Name):
            # If this is a macro, match the macro name as tag.  For existing
            # VUs, this means that pname: must be removed from the macro value
            # before the VU is reformatted to be codified.
            if node.func.id == 'macro':
                self.tag = '{' + node.args[0].id + '}'
            elif node.func.id in ['require', 'externally_synchronized']:
                self.visit(node.args[0])
        else:
            assert(isinstance(node.func, ast.Attribute))
            # Check the object of the call
            self.visit(node.func.value)

    def visit_Attribute(self, node):
        if self.tag is not None:
            return

        # Check only the object of the attribute, the attribute itself is not a
        # member/parameter of the API being validated.
        self.visit(node.value)

    def visit_Name(self, node):
        if self.tag is not None:
            return

        assert(node.id not in FUNC_BUILTINS.keys() and node.id not in ATTR_BUILTINS.keys())

        # Do not match constants
        if node.id.startswith('VK_'):
            return

        # There should be no references to the Vulkan structs and entry points
        # outside builtin arguments, and those are not traversed.
        assert(not node.id.startswith('vk'))
        assert(not node.id.startswith('Vk'))

        # Do not match variables
        if node.id in self.variableSet:
            return

        # This must be a member or parameter, as it is otherwise undefined
        self.tag = node.id


class VuAST:
    """The AST corresponding to a codified VU."""
    def __init__(self):
        self.vu = ''
        """The vu text, ready to be parsed."""

        self.vuIndent = 0
        """How much indent was removed from VU.  This is used for adjusting the
        offset in the error report."""

        self.filename = ''
        """The file name in which the VU appears."""

        self.fileline = 0
        """The line number of the VU."""

        self.ast = None
        """The AST corresponding to the VU text.  Macros are not expanded.
        Used for source formatting."""

        self.astExpanded = None
        """The AST with macros expanded.  Used for correctness check and output
        formatting."""

        self.macros = {}
        """A list of adoc macros to be replaced in the VU."""

    def _parse(self, vu, message):
        try:
            return (ast.parse(vu, self.filename, 'exec'), True)
        except SyntaxError as exc:
            inVuLineNo = self.fileline + exc.lineno - 1
            logPrefix = self.filename + ':' + str(inVuLineNo) + ':' + str(exc.offset + self.vuIndent) + ':'
            logWarn(logPrefix, message + ': ', exc)

            offendingLine = vu.splitlines()[exc.lineno - 1]
            if exc.offset > 1:
                offendingChar = ' ' * (exc.offset - 2) + '^'
            else:
                offendingChar = '^'
            logWarn(logPrefix, '    ' + offendingLine)
            logWarn(logPrefix, '    ' + offendingChar)

            return (None, False)

    def parse(self, vuText, filename, fileline):
        self.filename = filename
        self.fileline = fileline

        # Parse the text
        vuTextNoIndent, self.vuIndent = removeIndent(vuText.splitlines())
        self.vu = '\n'.join(vuTextNoIndent)
        #print(self.vu)
        self.ast, result = self._parse(self.vu, 'VU parse error')
        return result

    def applyMacros(self, macros):
        self.macros = convertMacrosToVuLanguage(macros)

        # Parse the macro-expanded text as well
        vuExpanded = expandVuMacros(self.vu, self.macros)

        self.astExpanded, result = self._parse(vuExpanded, 'VU parse error (post macro expansion)')
        return result

    def verify(self, entity_db, api):
        """Verify that the VU is semantically correct.  Must only be called
        when macros have been expanded."""
        #print(ast.dump(self.astExpanded, indent = ' '))
        verifier = VuVerifier(entity_db, api, self.filename, self.fileline)
        return verifier.verify(self.astExpanded)

    def format(self, fmt, entity_db):
        """Format the AST.

        If given VuFormat.SOURCE, it will format it for placement in the adoc
        file.  This uses the AST that contains macros.
        If given VuFormat.OUTPUT, it will format it for build, using the AST
        that has gone through macro expansion."""
        assert(fmt == VuFormat.SOURCE or entity_db is not None)

        ast = self.ast if fmt == VuFormat.SOURCE else self.astExpanded

        formatter = VuFormatter(entity_db, fmt, self.filename, self.fileline)
        return formatter.format(ast)

    def getParameterTag(self):
        """Find the first reference to a member/parameter of the API for which
        validation is written."""
        tagExtractor = VuParametterTagExtractor()
        return tagExtractor.getTag(self.ast)

def formatVU(vuParagraph, apiName, filename, fileline, vuPrefix, fmt, entity_db = None, macros = {}):
    """Helper function to format a VU paragraph as soon in the spec text.  The
    paragraph may contain a bullet point, a VUID tag etc."""
    # Check if first line is VUID, if so remove it for reformatting
    hasVUID = vuPrefix in vuParagraph[0]

    toFormat = vuParagraph
    vuid = ''
    if hasVUID:
        vuid = toFormat[0]
        toFormat = toFormat[1:]
        fileline += 1

    toFormat = removeBulletPoint(toFormat)

    # Record the indentation level of the VU to restore after formatting.
    indent = len(toFormat[0]) - len(toFormat[0].lstrip())

    # Parse and reformat the VU
    vu = VuAST()
    if not vu.parse('\n'.join(toFormat), filename, fileline):
        logWarn('VU with parse error cannot be formatted')
        accept = fmt == VuFormat.SOURCE
        return vuParagraph, accept

    # For output, additionally apply macros and validate the VU.
    if fmt == VuFormat.OUTPUT:
        if not vu.applyMacros(macros):
            return vuParagraph, False
        apiName = applyMacrosToApiName(macros, apiName)
        if not vu.verify(entity_db, apiName):
            return vuParagraph, False

    formatted = vu.format(fmt, entity_db)

    # Add the VUID back, if any
    # Add indentation back
    formatted = [''.ljust(indent) + line + '\n' for line in formatted.splitlines()]

    if hasVUID:
        formatted = [vuid] + formatted
    else:
        # Put back the bullet point
        assert(indent >= 2)
        formatted[0] = ''.ljust(indent - 2) + '* ' + formatted[0][indent:]

    return formatted, True

def determineVUIDParameterTag(vuParagraph, filename, fileline):
    """Parse the tree and find the first reference to a member/parameter of the
    API for which validation is written.  This is assuming the VU is written
    correctly, as any otherwise-undefined symbol would have to implicitly
    reference the VU API.

    This is called when generating VUIDs, so vuParagraph cannot not have a VUID
    already."""
    vuParagraph = removeBulletPoint(vuParagraph)
    vu = VuAST()
    if not vu.parse('\n'.join(vuParagraph), filename, fileline):
        logWarn('Cannot determine parameter tag in VU with parse error')
        return 'None'

    return vu.getParameterTag()
