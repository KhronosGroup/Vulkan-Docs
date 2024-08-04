# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Utilities to parse a VU into an AST, match its symbols with the registry
and walk the AST.  This can be used to:

- Reformat the VU to make the formatting uniform (for reflow.py)
- Reformat the VU to add syntax highlighting (at build time)
- Generate VVL code directly from the VU (in the VVL repository)
"""

import ast
from collections import namedtuple
import copy
from enum import Enum
import re

from reflib import logDiag, logWarn, logErr
from reg import Registry
import spec_tools.util as util

# A line with an assignment, in the form of `a.b.c = ...`
assignmentPattern = re.compile(r'^\s*[a-zA-Z0-9_.]+\s*=')

# For verification, used to strip added annotations:
stylePattern = re.compile(r'\[vu-[a-z-]*\]')
linkPattern = re.compile(r'<<(vu-[a-z-_]*|features-[a-zA-Z0-9_]*),')
newLinePattern = re.compile(r' \+$', flags=re.MULTILINE)

vuidPat = re.compile(r'\[\[VUID-[^-]+-[^-]+-[0-9]+\]\]')

# For detecting Vk*Features structs
featuresStructPattern = re.compile(r'VkPhysicalDevice.*Features[A-Z0-9]*')

# While VUs are being codified and codified VUs are rare, they are tagged with
# the following in the spec for greppability.  Once they are easy to find, the
# logic in `isCodifiedVU` could distinguish them from prose as it was
# originally implemented in:
# https://github.com/KhronosGroup/Vulkan-Docs/pull/2081/commits/3163f4cb015c85221633ebf9949e77e50814eab8#diff-4ce50680b8e0b8abde0934e7b0095e9a3a6cfb3515bb8e09d662fbe854785510R44
#
# Ultimately, codified VUs can also be found by searching for `require(`
grepTag = 'codified-vu'

def removeVUID(para):
    leftover = vuidPat.sub('', para[0])
    # Keep the line only if there's anything after the VUID tag
    if leftover.strip() == '*':
        return para[1:]
    return [leftover] + para[1:]


def isCodifiedVU(para):
    """Whether this is a legacy VU written in prose, or a codified VU that can
    be parsed.  For now, codified VUs are tagged as such so they are easy to
    find."""

    # See comment on grepTag
    noVUID = removeVUID(para)

    # If the paragraph only contains the VUID, it must be a traditional VU with
    # an ifdef right at the beginning.
    if len(noVUID) == 0:
        return False

    # Remove bullet point (`* `) if any
    if noVUID[0].lstrip()[0] == '*':
        noVUID = [noVUID[0].lstrip()[1:]] + noVUID[1:]

    # Check the first line for the tag
    return noVUID[0].strip() == grepTag


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


def removeGrepTag(vuText):
    assert(vuText[0] == grepTag)
    return vuText[1:]


def retainComments(para):
    """Change comments to a function call so they are retained in the AST.
    Processors would ignore it, and formatter would turn it back into a
    comment."""
    result = []
    for line in para:
        if line.lstrip().startswith('#'):
            indent = len(line) - len(line.lstrip())
            converted = ' ' * indent + '__comment("' + line.lstrip()[1:].strip() + '")'
            result.append(converted)
        else:
            result.append(line)

    return result


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


def createAliasMap(registry):
    # Look at all entries that can be aliased:
    aliasMap = {}

    # Types
    for type_elem in registry.reg.findall('types/type'):
        alias = type_elem.get('alias')
        if not alias:
            continue

        # If the <type> does not already have a 'name' attribute, set
        # it from contents of its <name> tag.
        name = type_elem.get('name')
        if name is None:
            name = type_elem.find('name').text
        aliasMap[name] = alias

    # Commands
    for cmd in registry.reg.findall('commands/command'):
        alias = cmd.get('alias')
        if not alias:
            continue

        # If the <command> does not already have a 'name' attribute, set
        # it from contents of its <proto><name> tag.
        name = cmd.get('name')
        if name is None:
            name = cmd.find('name').text
        aliasMap[name] = alias

    # Enums
    for enums in registry.reg.findall('enums'):
        name = enums.get('name')
        for enum in enums.findall('enum'):
            value = enum.get('name')
            alias = enum.get('alias')
            if alias:
                aliasMap[value] = alias

    return aliasMap


def createEnumValueMap(registry, aliasMap):
    valueMap = {}

    for enums in registry.reg.findall('enums'):
        name = enums.get('name')
        assert(name not in aliasMap)
        for enum in enums.findall('enum'):
            value = enum.get('name')
            if value in valueMap:
                assert(name == valueMap[value])
                continue
            valueMap[value] = name

    return valueMap


def createSymbolAvailabilityMap(registry, aliasMap):
    """Create maps from feature names (i.e. members of Vk*FeaturesSUFFIX
    structs), struct names and enum names to Vulkan versions and extension
    names.  This is used to let the VU directly reference feature names, or
    check for pnexts or enums without doing an extension check.

    At build time, they are appropriately stripped based on these map."""

    featureMap = {}
    structMap = {}
    enumMap = {}

    # First, go over Vulkan versions (<feature> tags) and extensions and
    # see which Vk*Features structs belong to which version/extensions.  At the
    # same time, the structs and enum values defined by the them are gathered.
    featureStructMap = {}

    enumsCache = {enum.get('name'): enum for enum in registry.reg.findall('enums')}

    def addToMap(map, name, versionAndExtensions):
        if name not in map:
            map[name] = set()
        for versionAndExtension in versionAndExtensions:
            map[name].add(versionAndExtension)

    def makeDependencies(versionAndExtension, require):
        deps = [versionAndExtension]
        if 'depends' in require.attrib:
            deps = [versionAndExtension + '+' + others
                    for others in require.attrib['depends'].split(',')]
        return deps

    versionAndExtensionList = [(info.version, info.elem) for _, info
                               in registry.apidict.items()]
    versionAndExtensionList += [(info.name, info.elem) for _, info in
                                registry.extdict.items()]

    for versionAndExtension, elem in versionAndExtensionList:
        enumValuesVisited = set()

        # Visit enums first, to handle the case where an extension introduces
        # an enum, but some of its values are conditional to other extensions.
        for require in elem.findall('require'):
            deps = makeDependencies(versionAndExtension, require)

            for enumDecl in require.findall('.//enum'):
                name = enumDecl.get('name')
                addToMap(enumMap, name, deps)
                enumValuesVisited.add(name)

                # If aliased, add the alias too
                alias = enumDecl.get('alias')
                if alias:
                    addToMap(enumMap, alias, deps)
                    enumValuesVisited.add(alias)

        for require in elem.findall('require'):
            deps = makeDependencies(versionAndExtension, require)

            for typeDecl in require.findall('.//type'):
                name = typeDecl.get('name')

                typeInfo = registry.typedict[name]
                category = typeInfo.elem.get('category')

                if category in ['enum', 'bitmask']:
                    if name not in enumsCache:
                        continue
                    enum = enumsCache[name]

                    # reg.py accumulates all enum values in the enum, even coming
                    # from other extensions.  The version and extname tags are
                    # additionally added to tell where the enum came from.
                    for value in enum.findall('enum'):
                        enumName = value.get('name')
                        # Skip enums that are already specified in the
                        # extension.  That happens if the enums are introduced
                        # by this extension, but have extra requirements.  In
                        # that case, those enums are already added and should
                        # be skipped.
                        if enumName in enumValuesVisited:
                            continue

                        hasVersion = 'version' in value.attrib
                        hasExt = 'extname' in value.attrib
                        if hasVersion:
                            addToMap(enumMap, enumName, [value.attrib['version']])
                        if hasExt:
                            addToMap(enumMap, enumName, [value.attrib['extname']])
                        if not hasVersion and not hasExt:
                            addToMap(enumMap, enumName, deps)
                    continue

                if category != 'struct':
                    continue

                addToMap(structMap, name, deps)

                # If the type is aliased, use the aliased name; later, when
                # looking at members of the struct, the aliasing one doesn't
                # have any.
                if name in aliasMap:
                    name = aliasMap[name]

                # Add the extension/version to the aliased name too. Later, the
                # list accumulated in the aliased name propagates to all aliases.
                addToMap(structMap, name, deps)

                if featuresStructPattern.match(name) is not None:
                    addToMap(featureStructMap, name, deps)

    # Go over the struct and enum map, and propagate the versions and extensions info to all aliases.
    for name, versionsAndExtensions in structMap.items():
        if name in aliasMap:
            versionsAndExtensions.update(structMap[aliasMap[name]])
    for name, versionsAndExtensions in enumMap.items():
        if name in aliasMap:
            versionsAndExtensions.update(enumMap[aliasMap[name]])

    # Go over the members of each Vk*Features struct and map their members
    # to the version/extension list.

    for struct, versionsAndExtensions in featureStructMap.items():
        info = registry.typedict[struct]
        for member in info.getMembers():
            name = util.getElemName(member)
            typeStr = util.getElemType(member)
            # Skip anything that is not VkBool32
            if typeStr != 'VkBool32':
                continue

            # TODO: VK_EXT_buffer_device_address shares feature names with the KHR version but they
            # are semantically different.  The features from the EXT extension need the following
            # special treatment:
            #
            # - Their name should be suffixed with EXT
            # - In output generation, their name should be prefixed with
            # sType:VkPhysicalDeviceBufferDeviceAddressFeaturesEXT and the EXT dropped.
            #
            # I tried removing this exceptional case in
            # https://gitlab.khronos.org/vulkan/vulkan/-/merge_requests/6231 to no avail.  Until we
            # need to codify VUs involving those features, they are not special-cased.  Hopefully
            # that would be never.

            if name not in featureMap:
                featureMap[name] = set()
            featureMap[name].update(versionsAndExtensions)

    return featureMap, structMap, enumMap

def isCommentCall(node):
    assert(isinstance(node, ast.Call))
    return isinstance(node.func, ast.Name) and node.func.id == '__comment'

def isComment(node):
    # When standalone, __comment() calls are always an ast.Expr
    return (isinstance(node, ast.Expr) and
            isinstance(node.value, ast.Call) and
            isCommentCall(node.value))


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
    FEATURE_NAME = 9,

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
FEATURE_NAME_TYPE = VuType(VuTypeClass.FEATURE_NAME, '')

# List of predicates that are used like standalone functions.  Like
# `require(...)`.
FUNC_PREDICATES = {
    # void require(bool)
    'require' : VuFuncType(VOID_TYPE, [BOOL_TYPE]),
    # bool has_pnext(struct_name)
    'has_pnext': VuFuncType(BOOL_TYPE, [STRUCT_NAME_TYPE]),
    # struct pnext(struct_name)
    'pnext': VuFuncType(STRUCT_TYPE, [STRUCT_NAME_TYPE]),
    # uint32_t array_index(loop_variable)
    'array_index': VuFuncType(UINT_TYPE, [VOID_TYPE]),
    # bool is_version(major, minor)
    'is_version': VuFuncType(BOOL_TYPE, [NUM_TYPE, NUM_TYPE]),
    # bool is_ext_enabled(ext_name)
    'is_ext_enabled': VuFuncType(BOOL_TYPE, [EXTENSION_NAME_TYPE]),
    # bool is_feature_enabled(feature_name)
    'is_feature_enabled': VuFuncType(BOOL_TYPE, [FEATURE_NAME_TYPE]),
    # bool externally_synchronized(handle)
    'externally_synchronized': VuFuncType(BOOL_TYPE, [HANDLE_TYPE]),
    # macro() is used like a function, but is never visible in the output
    'macro': VuFuncType(VOID_TYPE, [VOID_TYPE]),
}

# List of predicates that are used as if they are attributes.  Like
# `flags.has_bit(...)`.
ATTR_PREDICATES = {
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

class VuFormatter(ast.NodeVisitor):
    """A helper class to format a VU.

    This is used by reflow.py to format the VUs in the input files.  It is also
    used during build to format the VU appropriately for output, e.g. with
    links, syntax highlighting etc."""
    def __init__(self, styler):
        self.indent = styler.initialIndent
        """The current amount of indent."""

        self.formatted = []
        """The result formatted VU.  A "global" to avoid passing around and
        simplify the code."""

        self.styler = styler
        """A helper used to style the formatted output."""

        self.scopeStack = []
        """A stack of indices into self.formatted, marking the beginning of the
        scope.  Can be used by the styler to process the scope at the end."""

    def format(self, ast, isWholeTree = True):
        """Format a given AST"""
        self.indent = self.styler.initialIndent
        self.formatted = []

        self.beginStyle('vu', '#')
        self.visit(ast)
        self.endStyle('#')

        # Join the pieces to get the final output
        formatted = ''.join(self.formatted)

        if isWholeTree:
            self.styler.verifyIdentical(ast, formatted)

        if self.styler.grepTag is not None:
            formatted = self.styler.space * self.styler.initialIndent + self.styler.grepTag + self.styler.endOfLine + formatted

        return formatted

    def add(self, text):
        self.formatted.append(text)

    def beginScope(self):
        # Scope always begins with : and a new line
        self.add(':')
        self.endLine()
        self.indent += 1

        self.onBeginScope()

    def onBeginScope(self):
        self.scopeStack.append(len(self.formatted))
        self.styler.onBeginScope()

    def endScope(self):
        # Nothing to do on scope end, just reduce the indent level
        self.indent -= 1

        self.onEndScope()

    def onEndScope(self):
        # Give the styler a chance to post-process the scope.
        scopeStart = self.scopeStack.pop()

        beforeScope = self.formatted[:scopeStart]
        scope = self.formatted[scopeStart:]

        self.formatted = beforeScope + self.styler.onEndScope(scope)


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
        #
        # Note that all users of this class use 2 spaces.
        self.add(self.styler.parenOpen)
        self.indent += 2

    def endParenthesis(self):
        self.add(self.styler.parenClose)
        self.indent -= 2

    def beginLine(self):
        self.add(self.styler.space * self.indent)

    def endLine(self):
        self.add(self.styler.endOfLine)

    def beginStyle(self, style, delimiter = '##'):
        self.formatted += self.styler.beginStyle(style, delimiter)

    def endStyle(self, delimiter = '##'):
        self.formatted += self.styler.endStyle(delimiter)

    def beginLink(self, link):
        self.formatted += self.styler.beginLink(link)

    def endLink(self):
        self.formatted += self.styler.endLink()

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

    def addPredicate(self, predicate):
        # Output: <<vu-predicate-name,[vu-predicate]#name#>>
        self.beginStyle('vu-predicate')
        self.beginLink('vu-predicate-' + predicate)
        self.add(predicate)
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

        # If the body is entirely made of comments, add `pass`.  This does not
        # realistically happen in VUs, but it does in unit tests.
        if all([isComment(statement) for statement in statements]):
            assert(not first)
            self.endLine()
            self.visit_Pass(ast.Pass())

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

    def addIfBlock(self, node, keyword):
        # Output: if/elif test:
        #            body
        self.addKeyword(keyword)
        self.visit(node.test)

        self.beginScope()
        self.addBody(node.body)
        self.endScope()

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

    def visit_Pass(self, node):
        self.beginLine()
        self.addKeyword('pass', postSpace = ' ')

    def visit_If(self, node):
        # Output: if test:
        #            body
        #         else:
        #            body
        self.addIfBlock(node, 'if')

        # If there is an else block, output that as well.  If the else block
        # itself is an if node, the `elif` keyword needs to be used.
        while len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            node = node.orelse[0]
            self.endLine()
            self.beginLine()
            self.addIfBlock(node, 'elif')

        if len(node.orelse) > 0:
            self.endLine()
            self.beginLine()
            self.addKeyword('else', postSpace = '')
            self.beginScope()
            self.addBody(node.orelse)
            self.endScope()

    def visit_For(self, node):

        # For loops have an implicit scope (for their loop variable), make sure
        # the styler is aware of that scope.
        self.onBeginScope()

        # Output: for target in iter:
        #            body
        self.addKeyword('for')
        self.visit(node.target)
        self.addOperator('in')
        self.visit(node.iter)

        self.beginScope()
        self.addBody(node.body)
        self.endScope()

        # End the implicit for-loop scope
        self.onEndScope()

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
        # Output: op operand
        # For `not`, output `not operand`
        postSpace = ' ' if isinstance(node.op, ast.Not) else ''
        opText = self.opMap[node.op.__class__]
        self.addOperator(opText, preSpace = '', postSpace = postSpace)
        self.addParenthesizedExpression(node.operand)

    def visit_BinOp(self, node):
        self.addBinaryExpression(node.left, node.op, node.right)

    def visit_Compare(self, node):
        assert(len(node.ops) == 1)
        self.addBinaryExpression(node.left, node.ops[0], node.comparators[0])

    def visit_Call(self, node):
        # Output: func(arg, arg, ...)
        #
        # Predicate function calls do not accept complex boolean arguments, except
        # for `require`.  Since boolean arguments unconditionally get
        # parenthesized, parentheses are not added here for `require(BoolOp)`.
        # For now, this is the simpler method to avoid double parenthesization.

        # Handle comments specially; they are turned back into comments.
        if isCommentCall(node):
            self.beginStyle('vu-comment')
            self.formatted += [self.styler.hashSymbol, ' ', node.args[0].value]
            self.endStyle()
            return

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

        self.formatted += self.styler.onCallVisit(node)

    def visit_Attribute(self, node):
        # Output: value.attr
        self.visit(node.value)
        self.add('.')

        # If it is a predicate, make a link to the reference.
        if node.attr in ATTR_PREDICATES.keys():
            self.addPredicate(node.attr)
        else:
            self.add(node.attr)

            self.formatted += self.styler.onAttributeVisit(node)

    def visit_Subscript(self, node):
        # Output: value[slice]
        self.visit(node.value)
        self.add(self.styler.bracketOpen)
        self.visit(node.slice)
        self.add(self.styler.bracketClose)

        self.formatted += self.styler.onSubscriptVisit(node)

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
        # If it is a predicate, make a link to the reference.
        if node.id in FUNC_PREDICATES.keys():
            self.styler.onPredicateVisit(node.id)
            self.addPredicate(node.id)
            return

        self.formatted += self.styler.getNameSymbol(node)

    # Although unsupported, the following are also output correctly for the
    # sake of VuVerifier.  When the expression is invalid, it will output why
    # and would need the expression formatted well.
    def visit_While(self, node):
        # Output: while test:
        #             body
        self.addKeyword('while')
        self.visit(node.test)

        self.beginScope()
        self.addBody(node.body)
        self.endScope()

    def visit_Break(self, node):
        self.addKeyword('break', postSpace = '')

    def visit_Continue(self, node):
        self.addKeyword('continue', postSpace = '')

    def visit_Tuple(self, node):
        delimiter = self.styler.parenOpen
        for elt in node.elts:
            self.add(delimiter)
            delimiter = ', '
            self.visit(elt)
        self.add(self.styler.parenClose)

    def visit_List(self, node):
        delimiter = '['
        for elt in node.elts:
            self.add(delimiter)
            delimiter = ', '
            self.visit(elt)
        self.add(']')


class VuFormatterText(ast.NodeVisitor):
    """A helper class to turn a VU into text

    This is used during build to turn the VU into text.
    **NOTE: this is a prototype**"""
    def __init__(self, styler, language):
        self.indent = 0
        """The current amount of indent."""

        self.styler = styler
        """A helper used to style the formatted output."""

        self.language = language
        """A helper to generate the text in a given language"""

    def format(self, ast):
        """Format a given AST"""
        self.indent = 0
        formatted = []

        formatted += self.beginStyle('vu', '#')
        formatted += self.visit(ast)
        formatted += self.endStyle('#')

        # Join the pieces to get the final output
        formatted = ''.join(formatted)

        # Make sure single-line VUs also get a *
        if formatted[0] != '*':
            formatted = '* ' + formatted

        return formatted

    def beginScope(self):
        self.indent += 1
        return [':'] + self.endLine()

    def beginApiScope(self):
        self.styler.onBeginScope()
        return self.beginScope()

    def endScope(self, addTerminator = False):
        self.indent -= 1
        # Only add the terminator if requested.  Normally, blocks don't add
        # the terminator because they can be nested.  Additionally, every
        # statement already gets an endLine() in visitBody.  So
        # addTerminator is only for cases where a block is added where
        # Python normally wouldn't have one (like conditions of an if).
        if addTerminator:
            return self.endLine()
        return []

    def endApiScope(self, scope, addTerminator = False):
        return self.styler.onEndScope(scope) + self.endScope(addTerminator)

    def beginLine(self):
        return ['*' * (self.indent + 1) + ' ']

    def endLine(self):
        return [self.styler.endOfLine]

    def beginStyle(self, style, delimiter = '##'):
        return self.styler.beginStyle(style, delimiter)

    def endStyle(self, delimiter = '##'):
        return self.styler.endStyle(delimiter)

    def beginLink(self, link):
        return self.styler.beginLink(link)

    def endLink(self):
        return self.styler.endLink()

    def visitOperator(self, op, preSpace = ' ', postSpace = ' '):
        # Output: ` op `
        return [preSpace] + self.beginStyle('vu-operator') + [op] + self.endStyle() + [postSpace]

    def visitNumber(self, num):
        return self.beginStyle('vu-number') + [str(num)] + self.endStyle()

    def visitPredicate(self, predicate):
        # Output: <<vu-predicate-name,[vu-predicate]#name#>>
        formatted = []
        formatted += self.beginStyle('vu-predicate')
        formatted += self.beginLink('vu-predicate-' + predicate)
        formatted.append(predicate)
        formatted += self.endLink()
        formatted += self.endStyle()
        return formatted

    def visitAPIToken(self, token, prefix):
        return [prefix, token]

    def visitBody(self, statements):
        # Strip all comments
        statements = [statement for statement in statements if not isComment(statement)]

        # Handle a list of statements, adding indentation appropriately
        # Do not end the last line.  If nested, the parent body will end the
        # line.
        first = True
        formatted = []
        for statement in statements:
            if not first:
                formatted += self.endLine()
            first = False

            formatted += self.beginLine()
            formatted += self.visit(statement)

        return formatted

    # Map of op classes to their textual representation
    opMap = {
        # Found in BoolOp
        ast.And: 'UNEXPECTED-AND',
        ast.Or: 'UNEXPECTED-OR',
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
        ast.Not: 'UNEXPECTED-NOT',
        ast.UAdd: '+',
        ast.USub: '-',
        # Found in CompOp
        ast.Eq: 'UNEXPECTED-EQ',
        ast.NotEq: 'UNEXPECTED-NOTEQ',
        ast.Lt: 'UNEXPECTED-LT',
        ast.LtE: 'UNEXPECTED-LTE',
        ast.Gt: 'UNEXPECTED-GT',
        ast.GtE: 'UNEXPECTED-GTE',
        ast.Is: 'UNEXPECTED-IS',
        ast.IsNot: 'UNEXPECTED-ISNOT',
        ast.In: 'UNEXPECTED-IN',
        ast.NotIn: 'UNEXPECTED-NOTIN',
    }

    def visitMaybeParentheses(self, value, needsParentheses):
        formatted = []

        if needsParentheses:
            formatted.append(self.styler.parenOpen)

        formatted += self.visit(value)

        if needsParentheses:
            self.append(self.styler.parenClose)

        return formatted

    def visitParenthesizedExpression(self, value):
        # Add parentheses around value unless obviously unnecessary.  This
        # function is called when `value` is used in another expression with an
        # operator, and operator priorities would change the expression if not
        # parenthesized.
        needsParentheses = value.__class__ not in [ast.Call, ast.Attribute,
                                                   ast.Subscript, ast.Name,
                                                   ast.Constant, ast.BoolOp]

        return self.visitMaybeParentheses(value, needsParentheses)

    def visitBinaryExpression(self, left, op, right):
        # Output: (left) op (right)
        leftOp = left.op if isinstance(left, ast.BinOp) else None
        rightOp = right.op if isinstance(right, ast.BinOp) else None
        formatted = []

        formatted += self.visitParenthesizedExpression(left)

        opText = self.opMap[op.__class__]
        formatted += self.visitOperator(opText)

        formatted += self.visitParenthesizedExpression(right)

        return formatted

    def visitBoolean(self, node, expectTrue, must):
        # If the boolean expression has a not, invert it.
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self.visitBoolean(node.operand, not expectTrue, must)

        # Only not is a boolean unary op.
        assert(not isinstance(node, ast.UnaryOp))

        # If the expression is just a name, generate:
        #   name is true/false
        if isinstance(node, ast.Name):
            return self.language.isTrue(self.styler.getNameSymbol(node), expectTrue, must)

        # If the expression is a comparison, generate something based on the op, such as:
        #    x is greater than y
        #    x is not equal to y
        #    x is equal to y
        if isinstance(node, ast.Compare):
            assert(len(node.ops) == 1)
            op = node.ops[0]
            left = self.visit(node.left)
            right = self.visit(node.comparators[0])

            if isinstance(op, ast.Eq):
                return self.language.equals(left, right, expectTrue, must)
            elif isinstance(op, ast.NotEq):
                return self.language.equals(left, right, not expectTrue, must)
            elif isinstance(op, ast.Lt):
                return self.language.lessThan(left, right, expectTrue, must)
            elif isinstance(op, ast.LtE):
                return self.language.lessThanOrEqual(left, right, expectTrue, must)
            elif isinstance(op, ast.Gt):
                return self.language.greaterThan(left, right, expectTrue, must)
            elif isinstance(op, ast.GtE):
                return self.language.greaterThanOrEqual(left, right, expectTrue, must)
            else:
                assert(False)
                return ['UNEXPECTED COMPARISON OP']

        if isinstance(node, ast.BoolOp):
            isAnd = isinstance(node.op, ast.And)

            formatted = []
            formatted += self.language.allAny(isAnd, expectTrue)
            formatted += self.beginScope()
            formatted += self.visitBooleanList(node.values, isAnd, True, must)
            formatted += self.endScope()
            return formatted

        if isinstance(node, ast.Call):
            args = [self.visit(arg) for arg in node.args]
            if isinstance(node.func, ast.Name):
                # Handle predicates that return bool
                assert(not isComment(node))
                if node.func.id == 'has_pnext':
                    return self.language.hasPNext(args[0], expectTrue, must)
                if node.func.id == 'is_version':
                    version = ['Vulkan '] + args[0] + ['.'] + args[1]
                    return self.language.isVersion(version, expectTrue, must)
                if node.func.id == 'is_ext_enabled':
                    return self.language.isExtEnabled(args[0], expectTrue, must)
                if node.func.id == 'is_feature_enabled':
                    return self.language.isFeatureEnabled(args[0], expectTrue, must)
                if node.func.id == 'externally_synchronized':
                    return self.language.isExternallySynchronized(args[0], expectTrue, must)

            assert(isinstance(node.func, ast.Attribute) and node.func.attr in ATTR_PREDICATES.keys())
            value = self.visit(node.func.value)
            # Handle predicates that return bool
            if node.func.attr == 'has_pnext':
                return self.language.attributeHasPNext(value, args[0], expectTrue, must)
            if node.func.attr == 'has_bit':
                return self.language.hasBit(value, args[0], expectTrue, must)
            if node.func.attr == 'any':
                return self.language.any(value, expectTrue, must)
            if node.func.attr == 'none':
                return self.language.none(value, expectTrue, must)
            if node.func.attr == 'valid':
                return self.language.valid(value, expectTrue, must)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                if node.value == False:
                    # TODO: translate.  Better yet, turn require(False) into an error
                    return ['False']

        assert(False)
        return ['UNHANDLED BOOLEAN EXPRESSION']

    def visitBooleanList(self, nodes, isAnd, expectTrue, must):
        formatted = []
        isFirst = True
        for node in nodes:
            if not isFirst:
                formatted += self.endLine()
            isFirst = False

            formatted += self.beginLine()
            formatted += self.visitBoolean(node, expectTrue, must)

        return formatted

    def visitIfBlock(self, node, keyword):
        # Output: if ...:
        #         * condition 1
        #         * condition 2
        #         then:
        #         * body

        formatted = []

        # Turn `if (..)` into `if ... true:`.  Turn `if not (...)` into `if ... false:`
        isElif = keyword == 'elif'
        testNode = node.test
        expectTrue = True
        if isinstance(testNode, ast.UnaryOp) and isinstance(testNode.op, ast.Not):
            testNode = testNode.operand
            expectTrue = False

        isAnd = True
        values = [testNode]
        if isinstance(testNode, ast.BoolOp):
            isAnd = isinstance(testNode.op, ast.And)
            values = testNode.values

        if len(values) > 1:
            formatted += self.language.ifAllAny(isAnd, isElif, expectTrue)
        else:
            formatted += self.language.ifTrueFalse(isElif, expectTrue)
        formatted += self.beginScope()
        formatted += self.visitBooleanList(values, isAnd, True, False)
        formatted += self.endScope(addTerminator = True)

        formatted += self.beginLine()
        formatted += self.language.then()

        formatted += self.beginApiScope()
        formattedBody = self.visitBody(node.body)
        formatted += self.endApiScope(formattedBody)

        return formatted

    def visit_Module(self, node):
        return self.visitBody(node.body)

    def visit_Expr(self, node):
        return self.visit(node.value)

    def visit_Assign(self, node):
        assert(len(node.targets) == 1)
        target = self.visit(node.targets[0])
        formatted = []

        valueNode = node.value
        expectTrue = True
        if isinstance(valueNode, ast.UnaryOp) and isinstance(valueNode.op, ast.Not):
            valueNode = valueNode.operand
            expectTrue = False

        if isinstance(valueNode, ast.BoolOp):
            isAnd = isinstance(valueNode.op, ast.And)

            formatted += self.language.letComplex(target, isAnd, expectTrue)
            formatted += self.beginScope()
            formatted += self.visitBooleanList(valueNode.values, isAnd, True, False)
            formatted += self.endScope()
            return formatted

        formatted += self.language.let(target, self.visit(node.value))
        return formatted

    def visit_Pass(self, node):
        return ['nothing']

    def visit_If(self, node):
        # Output: if condition:
        #         * body
        #         otherwise:
        #         * body
        formatted = self.visitIfBlock(node, 'if')

        # If there is an else block, output that as well.  If the else block
        # itself is an if node, flatten the chain similar to python's `elif`
        while len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            node = node.orelse[0]
            formatted += self.endLine()
            formatted += self.beginLine()
            formatted += self.visitIfBlock(node, 'elif')

        if len(node.orelse) > 0:
            formatted += self.endLine()
            formatted += self.beginLine()
            formatted += self.language.orelse()
            formatted += self.beginApiScope()
            formattedBody = self.visitBody(node.orelse)
            formatted += self.endApiScope(formattedBody)

        return formatted

    def visit_For(self, node):
        # Output: for each element of Xs, namely X:
        #         * body
        target = self.visit(node.target)
        iter = self.visit(node.iter)

        # For loops have an implicit scope (for their loop variable), make sure
        # the styler is aware of that scope.
        self.styler.onBeginScope()

        formatted = self.language.foreach(target, iter)
        formatted += self.beginApiScope()
        formattedBody = self.visitBody(node.body)
        formatted += self.endApiScope(formattedBody)

        formatted = self.styler.onEndScope(formatted)

        return formatted

    def visit_BoolOp(self, node):
        # Boolean lists are expanded to multiple lines, so everywhere they may
        # have happened should already handle them.  Some obscure cases are not
        # handled right now, such as with (x && y) == (z || w)
        return ['FIXME BOOL OP IN UNUSUAL EXPRESSION']

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            # See comment on visit_BoolOp
            assert(not isinstance(node.operand, ast.BoolOp))
            return self.visitBoolean(node.operand, False, False)

        formatted = [self.opMap[node.op.__class__]]
        formatted += self.visitParenthesizedExpression(node.operand)
        return formatted

    def visit_BinOp(self, node):
        return self.visitBinaryExpression(node.left, node.op, node.right)

    def visit_Compare(self, node):
        assert(len(node.ops) == 1)
        return self.visitBoolean(node, True, False)

    def visitCallHelper(self, node):
        # Comments should be stripped before attempting to traverse a block
        assert(not isCommentCall(node))

        if isinstance(node.func, ast.Name):
            # For boolean functions, use visitBoolean which already handles them
            if FUNC_PREDICATES[node.func.id].returnType == BOOL_TYPE:
                return self.visitBoolean(node, True, False)

            # Handle functions that accept a bool argument
            if node.func.id == 'require':
                condition = node.args[0]
                expectTrue = True
                if isinstance(condition, ast.UnaryOp) and isinstance(condition.op, ast.Not):
                    condition = condition.operand
                    expectTrue = False

                if isinstance(condition, ast.BoolOp):
                    isAnd = isinstance(condition.op, ast.And)
                    formatted = self.language.mustAllAny(isAnd, expectTrue)
                    formatted += self.beginScope()
                    # Don't use must in the list, the "must be true/false" before the list is enough indication.
                    formatted += self.visitBooleanList(condition.values, isAnd, expectTrue, False)
                    formatted += self.endScope()
                    return formatted

                return self.visitBoolean(node.args[0], expectTrue, True)

            # Handle every other predicate
            args = [self.visit(arg) for arg in node.args]
            if node.func.id == 'pnext':
                return self.visitPredicate(node.func.id) + [self.styler.parenOpen] + args[0] + [self.styler.parenClose]
            if node.func.id == 'array_index':
                return self.language.arrayIndex(args[0])

            return ['UNEXPECTED CALL ', node.func.id]

        assert(isinstance(node.func, ast.Attribute))

        # For boolean functions, use visitBoolean which already handles them
        if ATTR_PREDICATES[node.func.attr].funcType.returnType == BOOL_TYPE:
            return self.visitBoolean(node, True, False)

        # Handle every other predicate
        value = self.visit(node.func.value)
        args = [self.visit(arg) for arg in node.args]
        if node.func.attr == 'pnext':
            return self.language.attributePNext(value, args[0])
        if node.func.attr in ['create_info',
                              'graphics_create_info',
                              'compute_create_info',
                              'raytracing_create_info']:
            return value + ['.'] + self.visitPredicate(node.func.attr) + [self.styler.parenOpen, self.styler.parenClose]

        return ['UNEXPECTED CALL ', node.func.attr]

    def visit_Call(self, node):
        return self.visitCallHelper(node) + self.styler.onCallVisit(node)

    def visit_Attribute(self, node):
        assert(node.attr not in ATTR_PREDICATES.keys())
        value = self.visit(node.value)
        # Asciidoc quirk:
        #  * pname:x.y renders as `x.y`
        #  * pname:x.pname:y renders as `x`.pname:y
        #  * ...().pname:y renders as `..().y`
        pname = 'pname:' if value[-1][-1] == ')' else ''
        return value + ['.', pname, node.attr] + self.styler.onAttributeVisit(node)

    def visit_Subscript(self, node):
        # Output: value[slice]
        value = self.visit(node.value)
        index = self.visit(node.slice)

        return value + [self.styler.bracketOpen] + index + [self.styler.bracketClose] + self.styler.onSubscriptVisit(node)

    def visit_IfExp(self, node):
        return ['FIXME UNWEILDY IN TEXT']

    def visit_Constant(self, node):
        # Output: [vu-number]#value#
        formatted = self.beginStyle('vu-number')
        if isinstance(node.value, str):
            formatted += ['"', + node.value, '"']
        else:
            formatted.append(str(node.value))
        formatted += self.endStyle()
        return formatted

    def visit_Name(self, node):
        assert(node.id not in FUNC_PREDICATES.keys())
        return self.styler.getNameSymbol(node)

    def visit_While(self, node):
        return ['WHILE IS NOT SUPPORTED']

    def visit_Break(self, node):
        return ['BREAK IS NOT SUPPORTED']

    def visit_Continue(self, node):
        return ['CONTINUE IS NOT SUPPORTED']

    def visit_Tuple(self, node):
        return ['TUPLE IS NOT SUPPORTED']

    def visit_List(self, node):
        return ['LIST IS NOT SUPPORTED']


class VuSourceStyler:
    """A helper class used with VuFormatter to format the VU for source adoc
    files"""
    def __init__(self, filename, fileline):
        self.filename = filename
        self.fileline = fileline
        """Location of VU."""

        self.space = '  '
        """String used for indentation."""

        self.hashSymbol = '#'
        """Used for generating comments."""

        self.parenOpen = '('
        self.parenClose = ')'
        """Used to avoid (( in asciidoc."""

        self.bracketOpen = '['
        self.bracketClose = ']'
        """Used to avoid [[ in asciidoc."""

        self.endOfLine = '\n'
        """String used to indicate end-of-line."""

        self.initialIndent = 0
        """No indentation necessary when generating the output."""

        self.grepTag = grepTag
        """A tag to ease searching for codified VUs."""

    def verifyIdentical(self, originalAST, formatted):
        try:
            formattedTree = ast.parse(formatted, self.filename, 'exec')
        except SyntaxError as exc:
            logPrefix = self.filename + ':' + str(self.fileline) + ':'
            logErr('Internal error: Parse error after reformatting VU:' , exc)
            return

        # Don't verify comments; VuOutputStyler may have clobbered them in the
        # process of cleaning up the AST.  Either way, this check is to make
        # sure the semantics of the VU haven't changed.  Comment functionality
        # is tested by unit tests.
        noCommentAST = ast.parse(ast.unparse(originalAST).replace('__comment(', '#'))

        if ast.dump(formattedTree) != ast.dump(noCommentAST):
            logPrefix = self.filename + ':' + str(self.fileline) + ':'
            logWarn(ast.dump(noCommentAST, indent=' '))
            logWarn(ast.dump(formattedTree, indent=' '))
            logErr(logPrefix, 'Internal error: Reformatted VU is different from original VU')

    def beginStyle(self, style, delimiter):
        return []

    def endStyle(self, delimiter):
        return []

    def beginLink(self, link):
        return []

    def endLink(self):
        return []

    def getNameSymbol(self, node):
        return [node.id]

    def onPredicateVisit(self, name):
        pass

    def onBeginScope(self):
        pass

    def onEndScope(self, scope):
        return scope

    def onCallVisit(self, node):
        return []

    def onAttributeVisit(self, node):
        return []

    def onSubscriptVisit(self, node):
        return []

class VuOutputStyler:
    """A helper class used with VuFormatter to format the VU for built output"""
    def __init__(self, registry, filename, fileline):
        assert(registry is not None)
        self.registry = registry
        """Registry used to look up symbols used by the VU."""

        self.filename = filename
        self.fileline = fileline
        """Location of VU."""

        self.space = '&nbsp;&nbsp;'
        """String used for indentation."""

        self.hashSymbol = '&#x23;'
        """Used for generating comments."""

        self.parenOpen = '&lpar;'
        self.parenClose = '&rpar;'
        """Used to avoid (( in asciidoc."""

        self.bracketOpen = '&lbrack;'
        self.bracketClose = '&rbrack;'
        """Used to avoid [[ in asciidoc."""

        # ` +` is used to ensure line breaks in the output.
        self.endOfLine = ' +\n'
        """String used to indicate end-of-line."""

        aliasMap = createAliasMap(self.registry)
        featureAvailability, _, _ = createSymbolAvailabilityMap(self.registry, aliasMap)
        self.featureList = featureAvailability.keys()
        """A list of feature names (i.e. members of Vk*FeaturesSUFFIX structs)."""

        self.initialIndent = 0
        """No indentation necessary when generating the output."""

        self.grepTag = None
        """No search tag needed in the output."""

    def verifyIdentical(self, originalAST, formatted):
        toVerify = formatted

        # Strip all annotations first
        toVerify = toVerify.replace('[vu]', '')
        toVerify = toVerify.replace('&nbsp;', ' ')
        toVerify = toVerify.replace(self.parenOpen, '(')
        toVerify = toVerify.replace(self.parenClose, ')')
        toVerify = toVerify.replace(self.bracketOpen, '[')
        toVerify = toVerify.replace(self.bracketClose, ']')
        toVerify = re.sub(stylePattern, '', toVerify)
        toVerify = re.sub(linkPattern, '', toVerify)
        toVerify = re.sub(newLinePattern, '', toVerify)
        toVerify = toVerify.replace(self.hashSymbol, '$$$')
        toVerify = toVerify.replace('#', '')
        toVerify = toVerify.replace('$$$', '#')
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

        # Now that it looks like the source output, use the source styler to verify it.
        sourceStyler = VuSourceStyler(self.filename, self.fileline)
        sourceStyler.verifyIdentical(originalAST, toVerify)

    def beginStyle(self, style, delimiter):
        return ['[', style, ']', delimiter]

    def endStyle(self, delimiter):
        return [delimiter]

    def beginLink(self, link):
        return ['<<', link, ',']

    def endLink(self):
        return ['>>']

    def getNameSymbol(self, node):
        # If it is an API entity, add the appropriate prefix such as slink: etc.
        # Otherwise outputting it plainly is sufficient.  No need for pname: on
        # members, function arguments etc, as the VU is already rendered in
        # monospace.
        prefix = None
        if node.id in self.registry.typedict:
            info = self.registry.typedict[node.id]
            category = info.elem.get('category')
            if category in ['struct', 'union', 'handle']:
                prefix = 'slink:'
            elif category == 'enum':
                prefix = 'elink:'
            elif category == 'bitmask':
                prefix = 'tlink:'
            elif category == 'define':
                prefix = 'dlink:'
        elif node.id in self.registry.cmddict:
            prefix = 'flink:'
        elif node.id in self.registry.enumdict:
            prefix = 'ename:'

        if prefix is not None:
            return [prefix, node.id]

        # For features, create a link as well.
        if node.id in self.featureList:
            return self.beginLink('features-' + node.id) + [node.id] + self.endLink()

        return [node.id]

    def onPredicateVisit(self, name):
        # Make sure `macro()` never makes it to the output.
        assert(name != 'macro')

    def onBeginScope(self):
        pass

    def onEndScope(self, scope):
        return scope

    def onCallVisit(self, node):
        return []

    def onAttributeVisit(self, node):
        return []

    def onSubscriptVisit(self, node):
        return []


class VuTextStyler:
    """A helper class used with VuFormatter to format the VU for built output"""
    def __init__(self, registry, filename, fileline):
        self.outputStyler = VuOutputStyler(registry, filename, fileline)

        self.space = ''
        self.hashSymbol = ''
        self.endOfLine = '\n'
        self.parenOpen = self.outputStyler.parenOpen
        self.parenClose = self.outputStyler.parenClose
        self.bracketOpen = self.outputStyler.bracketOpen
        self.bracketClose = self.outputStyler.bracketClose

    def verifyIdentical(self, originalAST, formatted):
        pass

    def beginStyle(self, style, delimiter):
        if delimiter == '#':
            return []
        return self.outputStyler.beginStyle(style, delimiter)

    def endStyle(self, delimiter):
        if delimiter == '#':
            return []
        return self.outputStyler.endStyle(delimiter)

    def beginLink(self, link):
        return self.outputStyler.beginLink(link)

    def endLink(self):
        return self.outputStyler.endLink()

    def getNameSymbol(self, node):
        symbol = self.outputStyler.getNameSymbol(node)
        if len(symbol) == 1:
            symbol = ['pname:'] + symbol
        return symbol

    def onBeginScope(self):
        pass

    def onEndScope(self, scope):
        return scope

    def onCallVisit(self, node):
        return []

    def onAttributeVisit(self, node):
        return []

    def onSubscriptVisit(self, node):
        return []


class VuLanguageEN:
    """Helper class to generate English out of the VUs"""
    def __init__(self):
        pass

    def isOrMustBe(self, expectTrue, must):
        return [' must: ' if must else ' is ',
                '' if expectTrue else 'not ',
                'be ' if must else '']

    def doesOrMustDo(self, expectTrue, must, verb, verbs):
        if must:
            return [' must: ',
                    '' if expectTrue else 'not ',
                    verb,
                    ' ']
        if expectTrue:
            return [' ', verbs, ' ']
        return [' does not ', verb, ' ']

    def isTrue(self, name, expectTrue, must):
        return name + self.isOrMustBe(True, must) + ['true' if expectTrue else 'false']

    def equals(self, left, right, expectTrue, must):
        return left + self.isOrMustBe(expectTrue, must) + ['equal to '] + right

    def lessThan(self, left, right, expectTrue, must):
        if not expectTrue:
            return self.greaterThanOrEqual(left, right, True, must)
        return left + self.isOrMustBe(True, must) + ['smaller than '] + right

    def lessThanOrEqual(self, left, right, expectTrue, must):
        if not expectTrue:
            return self.greaterThan(left, right, True, must)
        return left + self.isOrMustBe(True, must) + ['smaller than or equal to '] + right

    def greaterThan(self, left, right, expectTrue, must):
        if not expectTrue:
            return self.lessThanOrEqual(left, right, True, must)
        return left + self.isOrMustBe(True, must) + ['greater than '] + right

    def greaterThanOrEqual(self, left, right, expectTrue, must):
        if not expectTrue:
            return self.lessThan(left, right, True, must)
        return left + self.isOrMustBe(True, must) + ['greater than or equal to '] + right

    def ifAllAny(self, isAll, isElif, expectTrue):
        return ['otherwise, ' if isElif else '',
                'if ',
                'all ' if isAll else 'either ',
                'of the following ',
                'are ' if isAll else 'is ',
                'true' if expectTrue else 'false']

    def ifTrueFalse(self, isElif, expectTrue):
        return ['otherwise, ' if isElif else '',
                'if ',
                'the following is ',
                'true' if expectTrue else 'false']

    def ifCond(self, condition, isElif):
        return ['otherwise, if ' if isElif else 'if '] + condition

    def orelse(self):
        return ['otherwise']

    def then(self):
        return ['then']

    def let(self, variable, what):
        return ['let '] + variable + [' be '] + what

    def letComplex(self, variable, isAll, expectTrue):
        return ['let '] + variable + [' be '] + self.allAny(isAll, expectTrue)

    def foreach(self, target, iter):
        return ['for each '] + target + [' in '] + iter

    def allAny(self, isAll, expectTrue):
        return ['all ' if isAll else 'either ',
                'of the following ',
                'are ' if isAll else 'is ',
                'true' if expectTrue else 'false']

    def mustAllAny(self, isAll, expectTrue):
        return ['all ' if isAll else 'either ',
                'of the following must: be ',
                'true' if expectTrue else 'false']

    def hasPNext(self, struct, expectTrue, must):
        return struct + [' struct'] + self.isOrMustBe(expectTrue, must) + ['in the pname:pNext chain']

    def attributeHasPNext(self, value, struct, expectTrue, must):
        return struct + [' struct'] + self.isOrMustBe(expectTrue, must) + ['in the pname:pNext chain of '] + value

    def pNext(self, struct):
        return ['the '] + struct + [' struct in the pname:pNext chain']

    def attributePNext(self, struct):
        return ['the '] + struct + [' struct in the pname:pNext chain of '] + value

    def arrayIndex(self, target):
        return ['the index of '] + target

    def isVersion(self, version, expectTrue, must):
        return ['slink:VkPhysicalDeviceProperties::pname:apiVersion'] + self.isOrMustBe(expectTrue, must) + version

    def isExtEnabled(self, extension, expectTrue, must):
        return ['the `apiext:'] + extension + [' extension'] + self.isOrMustBe(expectTrue, must) + ['enabled']

    def isFeatureEnabled(self, feature, expectTrue, must):
        return ['the '] + feature + [' feature'] + self.isOrMustBe(expectTrue, must) + ['enabled']

    def isExternallySynchronized(self, what, expectTrue, must):
        return what + self.isOrMustBe(expectTrue, must) + ['<<fundamentals-threadingbehavior,externally synchronized>>']

    def hasBit(self, value, bit, expectTrue, must):
        return value + self.doesOrMustDo(expectTrue, must, 'contain', 'contains') + bit

    def any(self, value, expectTrue, must):
        return value + self.isOrMustBe(not expectTrue, must) + ['`0`']

    def none(self, value, expectTrue, must):
        return self.any(value, not expectTrue, must)

    def valid(self, value, expectTrue, must):
        return value + self.isOrMustBe(expectTrue, must) + ['a valid handle of its type']


class VuTypeExtractor:
    """Helper class to extract types out of symbols used in the VU.  Used for
    type checking and code generation."""
    def __init__(self, registry, api):
        self.registry = registry
        self.api = api

        self.aliasMap = createAliasMap(self.registry)
        """A map from aliased symbols to their aliases.  This helps look up the
        type/command/etc that actually has information."""

        self.enumValueMap = createEnumValueMap(self.registry, self.aliasMap)
        """A map from enum values to their enum types, e.g. VK_IMAGE_TYPE_1D to
        VkImageType.  There is no straightforward look up for this, so the xml
        is preprocessed to get this info."""

        self.featureMap, _, _ = createSymbolAvailabilityMap(self.registry, self.aliasMap)
        """A map from feature names (i.e. members of Vk*FeaturesSUFFIX structs)
        to Vulkan versions and extension names."""

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

    def lookupAPIInfo(self, api):
        if api in self.aliasMap:
            api = self.aliasMap[api]

        if api in self.registry.typedict:
            return self.registry.typedict[api]
        if api in self.registry.cmddict:
            return self.registry.cmddict[api]
        if api in self.registry.enumdict:
            return self.registry.enumdict[api]

        return None

    def getMemberOrArgumentSymbolType(self, api, symbol):
        """Get the type of a struct member or function field."""
        # For the specific case of 'VkPipelineCreateInfo' and 'flags', use any
        # of the real Vk*PipelineCreateInfo types.  They all have flags.  This
        # is by far the most common use case of pipeline.create_info(), so it
        # is nice to support that without resorting to graphics_create_info()
        # etc.
        if api == 'VkPipelineCreateInfo' and symbol == 'flags':
            api = 'VkGraphicsPipelineCreateInfo'

        info = self.lookupAPIInfo(api)
        if info is None:
            logWarn('Invalid API name', api)
            if api == 'VkPipelineCreateInfo':
                logWarn('Use graphics_create_info, compute_create_info or raytracing_create_info for pipelines')
            return None

        # Get the <member> or <param> of this struct / command
        isStruct = info.elem.tag == 'type' and info.elem.get('category') in ['struct', 'union']
        isCommand = info.elem.tag == 'command'
        if not (isStruct or isCommand):
            logWarn('Internal error: API name with no member looked up:', api)
            return None

        members = info.elem.findall('.//{}'.format('member' if isStruct else 'param'))
        for member in members:
            name = util.getElemName(member)
            if symbol == name:
                # If found, extract its type info
                return self.getMemberType(member)

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
        if nameTail != '' and nameTail[0] == '[':
            assert(arrayLen is None or arrayLen == 'null-terminated')
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

        if name in self.aliasMap:
            name = self.aliasMap[name]

        # Get the class type of the API entry based on the XML
        typeClass = None
        if name in self.registry.typedict:
            info = self.registry.typedict[name]
            category = info.elem.get('category')
            if category in ['struct', 'union']:
                typeClass = VuTypeClass.STRUCT_NAME
            elif category == 'handle':
                typeClass = VuTypeClass.HANDLE
            elif category == 'enum':
                typeClass = VuTypeClass.ENUM
            elif category == 'bitmask':
                typeClass = VuTypeClass.BITMASK
        elif name in self.registry.enumdict:
            # if one of API Constants, get the underlying type.
            constantType = util.getElemType(self.registry.enumdict[name].elem)
            if constantType in numTypes:
                return VuType(VuTypeClass.NUM, constantType)

            typeClass = VuTypeClass.ENUM

            # If an enum value, we are more interested in its real type.  For
            # example, for VK_IMAGE_TYPE_1D, we would change the typeStr to VkImageType.
            assert(name in self.enumValueMap)
            name = self.enumValueMap[name]

        elif name in self.registry.extdict:
            # Extensions do not have a type an the XML
            return VuType(VuTypeClass.EXTENSION_NAME, name)

        elif name in self.featureMap:
            # Features are members of Vk*Features structs
            return VuType(VuTypeClass.FEATURE_NAME, name)

        if typeClass is None:
            return None

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

    def getBitmaskBitsType(self, bitmaskType):
        """Get the VkFooFlagBits type from VkFooFlags."""
        if bitmaskType.typeStr not in self.registry.typedict:
            return bitmaskType

        info = self.registry.typedict[bitmaskType.typeStr]
        if info.elem.get('category') != 'bitmask':
            return bitmaskType

        bitsType = info.elem.attrib.get('requires')
        if bitsType is None:
            bitsType = info.elem.attrib.get('bitvalues')
            if bitsType is None:
                return bitmaskType

        return VuType(VuTypeClass.BITMASK, bitsType, bitmaskType.pointerLevel, bitmaskType.arrayLen)


class VuVerifier(ast.NodeVisitor):
    """Verify that the VU is semantically valid"""
    def __init__(self, registry, api, filename, fileline):
        self.registry = registry
        self.api = api

        self.typeExtractor = VuTypeExtractor(registry, api)
        """Helper to extract types out of symbols."""

        self.filename = filename
        self.fileline = fileline
        """Location of VU."""

        self.passed = False
        """Whether verification passed."""

        self.requireSeen = False
        """Whether the require() call was seen."""

        self.variableTypeMap = []
        """A list of name->VuType mappings."""

        self.scopeStack = []
        """Stack of indices into variableTypeMap, marking the beginning of the scope."""

        self.loopVariableSet = set()
        """A simple set of names of loop variables.  Scoping is not taken into
        account for simplicity."""

    def formatNode(self, node):
        formatter = VuFormatter(VuSourceStyler(self.filename, self.fileline))
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

    def beginScope(self):
        self.scopeStack.append(len(self.variableTypeMap))

    def endScope(self):
        scopeStart = self.scopeStack.pop()
        self.variableTypeMap = self.variableTypeMap[:scopeStart]

    def isVariableDefined(self, variable):
        return variable in [name for name, _ in self.variableTypeMap]

    def getVariableType(self, variable):
        index = [name for name, _ in self.variableTypeMap].index(variable)
        _, varType = self.variableTypeMap[index]
        return varType

    def visitBody(self, body):
        self.beginScope()
        for statement in body:
            self.visit(statement)
        self.endScope()

    def visit_Assign(self, node):
        # Verify that there are not multiple assignments (like a = b = c).
        if len(node.targets) != 1:
            self.fail([node.targets[0], node.targets[1]], 'Cascaded assignments are not allowed')
        # Verify that the target of assignment is a single variable.
        if not isinstance(node.targets[0], ast.Name):
            self.fail([node.targets[0]], 'Assignment target must be a single variable')
            return

        lhs = node.targets[0].id

        # Verify that the target is not an API entity
        if (lhs in self.registry.typedict or
            lhs in self.registry.enumdict or
            lhs in self.registry.cmddict or
            lhs in self.registry.apidict or
            lhs in self.registry.extensions or
            lhs in self.registry.extdict or
            lhs in self.registry.spirvextdict or
            lhs in self.registry.spirvcapdict or
            lhs in self.registry.formatsdict):
            self.fail([node.targets[0]], 'Invalid assignment to API token')
        # Verify that the target is not a member/argument of the API being defined
        elif self.typeExtractor.getSymbolType(lhs) is not None:
            self.fail([node.targets[0]], 'Invalid assignment to VU parameter')
        # Verify that the target is not a predicate
        elif lhs in FUNC_PREDICATES.keys() or lhs in ATTR_PREDICATES.keys():
            self.fail([node.targets[0]], 'Invalid assignment to predicate')

        # Verify that variables are constants.  This is done by making sure
        # every variable is only assigned-to once.
        if self.isVariableDefined(lhs):
            self.fail([node.targets[0]], 'Mutating variables are not allowed')

        # Visit RHS first, and get its type.  It is assigned to the LHS
        rhsType = self.visit(node.value)
        self.variableTypeMap.append((lhs, rhsType))

    def visit_AugAssign(self, node):
        self.fail([node.target], 'Mutating variables are not allowed')

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
        self.visitBody(node.orelse)

    def visit_For(self, node):
        # Verify that the loop target is a single variable
        if not isinstance(node.target, ast.Name):
            self.fail([node.target], 'Loop target must be a single variable')
            return
        # Verify that the loop iterator is not a list or tuple
        if isinstance(node.iter, ast.Tuple) or isinstance(node.iter, ast.List):
            self.fail([node.target], 'Loop iterator cannot be a list or tuple')
            return

        # Verify that the loop target is not a predicate
        if node.target.id in FUNC_PREDICATES.keys() or node.target.id in ATTR_PREDICATES.keys():
            self.fail([node.target], 'Loop target cannot have the name of a predicate')

        # Verify that the loop target is not an existing variable
        if self.isVariableDefined(node.target.id):
            self.fail([node.target], 'Loop variables shadows existing variable')

        # Verify that the loop iterator is an array
        iterType = self.visit(node.iter)
        if iterType.pointerLevel == 0 or iterType.arrayLen is None:
            self.fail([node.iter], 'Loop iterator must be an array')

        # Verify that there is no else:
        if len(node.orelse) > 0:
            self.fail([node.iter], 'else blocks on loops are not supported')

        # Create a scope for the loop variable
        self.beginScope()

        # Assign the iterator type (minus one array level) to the target
        targetType = self.typeExtractor.getIndexedArrayType(iterType)
        self.variableTypeMap.append((node.target.id, targetType))
        self.loopVariableSet.add(node.target.id)

        self.visitBody(node.body)

        self.endScope()

    def visit_While(self, node):
        # `while` is useless without variables, which are not supported.  As a descriptive language, `for` is sufficient
        self.fail([node], 'while blocks are not supported')

    def visit_Break(self, node):
        # As a descriptive language, `break` is not useful; an `if` is more appropriate.
        self.fail([node], 'break in loops are not allowed')

    def visit_Continue(self, node):
        # As a descriptive language, `continue` is not useful; an `if` is more appropriate.
        self.fail([node], 'continue in loops are not allowed')

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

        # Simplify VkFooFlags to VkFooFlagBits
        if leftType.typeClass == VuTypeClass.BITMASK:
            leftType = self.typeExtractor.getBitmaskBitsType(leftType)
        if rightType.typeClass == VuTypeClass.BITMASK:
            rightType = self.typeExtractor.getBitmaskBitsType(rightType)

        return leftType.typeStr == rightType.typeStr

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
        # Pass over comments.
        if isCommentCall(node):
            return VOID_TYPE

        # Only predicates can be called
        funcType = None
        objectType = None
        predicateName = ''
        if isinstance(node.func, ast.Name) and node.func.id in FUNC_PREDICATES.keys():
            predicateName = node.func.id
            funcType = FUNC_PREDICATES[predicateName]
            if predicateName == 'require':
                self.onRequireVisited()
        elif isinstance(node.func, ast.Attribute) and node.func.attr in ATTR_PREDICATES.keys():
            objectType = self.visit(node.func)
            predicateName = node.func.attr
            funcType = ATTR_PREDICATES[predicateName].funcType
        else:
            self.fail([node.func], 'Invalid function call.  If a predicate was intended, it is misspelled')
            return VOID_TYPE

        # Verify that the number of parameters is correct
        if len(node.args) != len(funcType.argTypes):
            self.fail([node.func], 'Invalid number of arguments passed to predicate')
            return funcType.returnType

        # Verify that arguments have the correct type
        argTypes = []
        for arg, expectedType in zip(node.args, funcType.argTypes):
            argType = self.visit(arg)
            argTypes.append(argType)

            # If predicate argument type is VOID, it means it matches anything.
            if expectedType.typeClass == VuTypeClass.VOID:
                continue

            if not self.doTypesMatch(argType, expectedType,
                                     requireTypeNameMatch = False):
                self.fail([arg], 'Mismatching type in argument to predicate', predicateName)
                return funcType.returnType

        # Some predicates require special attention.  For example,
        # pnext(structName) should have the structName in the return type so
        # members of it can be looked up.
        returnType = funcType.returnType
        if predicateName == 'pnext':
            # TODO: if struct cannot be chained, fail.  Add a check for has_pnext too.
            # The returned struct is of the type specified in the argument of this call
            returnType = VuType(returnType.typeClass, node.args[0].id)
        elif predicateName == 'create_info':
            # The returned struct has the name of the handle type + CreateInfo
            returnType = VuType(returnType.typeClass, objectType.typeStr + 'CreateInfo')
        elif predicateName == 'graphics_create_info':
            # Specialized create_info() to disambiguate VkPipeline
            returnType = VuType(returnType.typeClass,
                                objectType.typeStr[:2] + 'Graphics' + objectType.typeStr[2:] + 'CreateInfo')
        elif predicateName == 'compute_create_info':
            # Specialized create_info() to disambiguate VkPipeline
            returnType = VuType(returnType.typeClass,
                                objectType.typeStr[:2] + 'Compute' + objectType.typeStr[2:] + 'CreateInfo')
        elif predicateName == 'raytracing_create_info':
            # Specialized create_info() to disambiguate VkPipeline
            returnType = VuType(returnType.typeClass,
                                objectType.typeStr[:2] + 'RayTracing' + objectType.typeStr[2:] + 'CreateInfo')
        elif predicateName == 'has_bit':
            # has_bit accepts an enum value that must match the type of the
            # object its being called on.  If object is not a bitmask,
            # visit_Attribute has already generated an error.
            if (objectType.typeClass == VuTypeClass.BITMASK and
                not self.doEnumTypesMatch(objectType, argTypes[0])):
                self.fail([node.func.value, node.args[0]], 'has_bit argument is not an enum value of the object it is called on')
        elif predicateName == 'array_index':
            # Only loop variables may be passed to array_index.
            if not node.args[0].id in self.loopVariableSet:
                self.fail([node.args[0]], 'array_index argument is not a loop variable')

        # Make sure every struct return value carries the name
        assert(returnType.typeClass != VuTypeClass.STRUCT or returnType.typeStr != '')
        return returnType

    def visit_Attribute(self, node):
        valueType = self.visit(node.value)

        # Implicitly dereference pointers
        valueType = VuType(valueType.typeClass, valueType.typeStr)

        # If attr is a predicate, verify the value type based on the predicate requirements
        if node.attr in ATTR_PREDICATES.keys():
            predicateType = ATTR_PREDICATES[node.attr]

            if not self.doTypesMatch(predicateType.objectType, valueType, requireTypeNameMatch = False):
                self.fail([node.value], 'Invalid object type for attribute predicate', node.attr)

            # Attribute predicate must be called.  The original object type is
            # returned here which can be used by some predicates.
            # visit_Call will make sure the return type is taken from the predicate.
            return valueType

        # Otherwise look up the member in the struct and return its type
        if valueType.typeClass != VuTypeClass.STRUCT:
            self.fail([node.value], 'Invalid use of . on non-struct object.  If a predicate was intended, it is misspelled')
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
        # Verify that predicates are not used as variables
        if node.id in FUNC_PREDICATES.keys() or node.id in ATTR_PREDICATES.keys():
            self.fail([node], 'Invalid usage of predicate as variable')
            return VOID_TYPE

        # If this is a variable being referenced, get the type from the variable map
        if self.isVariableDefined(node.id):
            return self.getVariableType(node.id)

        # See if this is a member/arg of the API for which validation is written.
        nodeType = self.typeExtractor.getSymbolType(node.id)
        if nodeType is None:
            self.fail([node], 'Unknown token is neither an API token, nor a member or argument of', self.api)
            return VOID_TYPE

        return nodeType

class VuParametterTagExtractor(ast.NodeVisitor):
    """A traverser that walks the AST and finds the first reference to a symbol
    that is not otherwise defined.  This symbol must be referencing the
    member/parameter of the API for which validation is written.

    The AST is expected to be valid, i.e. has passed VuVerifier checks.  This
    means that adding VUID tags may fail if the spec does not build."""
    def __init__(self):
        self.macros = []
        """Extracted macros."""

        self.params = []
        """Members/parameters that are extracted."""

        self.variableSet = set()
        """Set of variables.  Used to know when referenced that they are not to
        be matched as the VUID tag."""

    def getTag(self, ast):
        self.macros = []
        self.params = []

        self.visit(ast)

        # Prioritize macros, but not the ones in the exception list
        # below.  These have complex expressions including ., ->, or [index]
        # which makes them unsuitable for VUID tags.  Ideally these would be
        # automatically discovered.
        macroExceptionList = ['maxinstancecheck', 'regionsparam',
                              'rayGenShaderBindingTableAddress',
                              'rayGenShaderBindingTableStride',
                              'missShaderBindingTableAddress',
                              'missShaderBindingTableStride',
                              'hitShaderBindingTableAddress',
                              'hitShaderBindingTableStride',
                              'callableShaderBindingTableAddress',
                              'callableShaderBindingTableStride',
                             ]
        macros = [macro for macro in self.macros if macro not in macroExceptionList]

        if len(macros) > 0:
            return '{' + macros[0] + '}'
        elif len(self.params) > 0:
            return self.params[0]
        else:
            return 'None'

    def visitBody(self, body):
        for statement in body:
            self.visit(statement)

    def visit_Assign(self, node):
        # Record the LHS as the variable, and traverse the RHS
        self.variableSet.add(node.targets[0].id)
        self.visit(node.value)

    def visit_If(self, node):
        self.visit(node.test)
        self.visitBody(node.body)
        self.visitBody(node.orelse)

    def visit_For(self, node):
        # Record the loop variable as such, and traverse the iterator and body
        self.variableSet.add(node.target)
        self.visit(node.iter)
        self.visitBody(node.body)

    def visit_Call(self, node):
        # Pass over comments.
        if isCommentCall(node):
            return

        # Note: function arguments are never a member/parameter, except inside
        # require and externally_synchronized.

        if isinstance(node.func, ast.Name):
            # If this is a macro, match the macro name as tag.  For existing
            # VUs, this means that pname: must be removed from the macro value
            # before the VU is reformatted to be codified.
            if node.func.id == 'macro':
                self.macros.append(node.args[0].id)
            elif node.func.id in ['require', 'externally_synchronized']:
                self.visit(node.args[0])
        else:
            assert(isinstance(node.func, ast.Attribute))
            # Check the object of the call
            self.visit(node.func.value)

    def visit_Attribute(self, node):
        # Check only the object of the attribute, the attribute itself is not a
        # member/parameter of the API being validated.
        self.visit(node.value)

    def visit_Name(self, node):
        assert(node.id not in FUNC_PREDICATES.keys() and node.id not in ATTR_PREDICATES.keys())

        # Do not match constants
        if node.id.startswith('VK_'):
            return

        # There should be no references to the Vulkan structs and entry points
        # outside predicate arguments, and those are not traversed.
        assert(not node.id.startswith('vk'))
        assert(not node.id.startswith('Vk'))

        # Do not match variables
        if node.id in self.variableSet:
            return

        # This must be a member or parameter, as it is otherwise undefined
        self.params.append(node.id)


class VuFormat(Enum):
    # Format for adoc source.  Used by reflow.py
    SOURCE = 0,
    # Format for output, with syntax highlighting etc.
    OUTPUT = 1,


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
                offendingChar = ' ' * (exc.offset - 1) + '^'
            else:
                offendingChar = '^'
            logWarn(logPrefix, '    ' + offendingLine)
            logWarn(logPrefix, '    ' + offendingChar)

            return (None, False)

    def parse(self, vuText, filename, fileline, strippedIndent = 0):
        self.filename = filename
        self.fileline = fileline

        # Parse the text.  Remove indentation first, and change comments to
        # functions to be retained in the AST.
        vuTextNoIndent, self.vuIndent = removeIndent(vuText.splitlines())
        self.vuIndent += strippedIndent

        vuTextNoIndent = removeGrepTag(vuTextNoIndent)
        vuTextNoIndent = retainComments(vuTextNoIndent)

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

    def verify(self, registry, api):
        """Verify that the VU is semantically correct.  Must only be called
        when macros have been expanded."""
        #print(ast.dump(self.astExpanded, indent = ' '))
        verifier = VuVerifier(registry, api, self.filename, self.fileline)
        return verifier.verify(self.astExpanded)

    def format(self, fmt, registry):
        """Format the AST.

        If given VuFormat.SOURCE, it will format it for placement in the adoc
        file.  This uses the AST that contains macros.
        If given VuFormat.OUTPUT, it will format it for build, using the AST
        that has gone through macro expansion."""
        assert(fmt == VuFormat.SOURCE or registry is not None)

        ast = self.ast
        styler = VuSourceStyler(self.filename, self.fileline)
        if fmt == VuFormat.OUTPUT:
            ast = self.astExpanded
            styler = VuOutputStyler(registry, self.filename, self.fileline)

        formatter = VuFormatter(styler)
        return formatter.format(ast)

    def formatText(self, registry):
        """Format the AST as English."""
        ast = self.astExpanded
        styler = VuTextStyler(registry, self.filename, self.fileline)
        language = VuLanguageEN()
        formatter = VuFormatterText(styler, language)
        return formatter.format(ast)

    def getParameterTag(self):
        """Find the first reference to a member/parameter of the API for which
        validation is written."""
        tagExtractor = VuParametterTagExtractor()
        return tagExtractor.getTag(self.ast)

def formatVU(vuParagraph, apiName, filename, fileline, vuPrefix):
    """Helper function to format a VU paragraph as seen in the spec text.  The
    paragraph may contain a bullet point, a VUID tag etc.  This function is
    used only for source formatting."""
    # Check if first line is VUID, if so remove it for reformatting
    hasVUID = vuPrefix in vuParagraph[0]

    toFormat = vuParagraph
    vuid = ''
    if hasVUID:
        vuid = vuidPat.search(toFormat[0])[0]
        toFormat = removeVUID(vuParagraph)
        fileline += len(vuParagraph) - len(toFormat)

    toFormat = removeBulletPoint(toFormat)

    # Record the indentation level of the VU to restore after formatting.
    indent = len(toFormat[0]) - len(toFormat[0].lstrip())

    # Parse and reformat the VU
    vu = VuAST()
    if not vu.parse('\n'.join(toFormat), filename, fileline):
        logWarn('VU with parse error cannot be formatted')
        return vuParagraph

    formatted = vu.format(VuFormat.SOURCE, None)

    # Add the VUID back, if any
    # Add indentation back
    formatted = [''.ljust(indent) + line + '\n' for line in formatted.splitlines()]

    if hasVUID:
        formatted = ['  * ' + vuid + '\n'] + formatted
    else:
        # Put back the bullet point
        assert(indent >= 2)
        formatted[0] = ''.ljust(indent - 2) + '* ' + formatted[0][indent:]

    return formatted

def parseAndVerifyVU(vuParagraph, apiName, filename, fileline, strippedIndent, registry, macros):
    """Helper function to format a VU paragraph that has the bullet point,
    indentation and VUID stripped.  This function is used only for output
    formatting during build."""
    vu = VuAST()
    if not vu.parse('\n'.join(vuParagraph), filename, fileline, strippedIndent):
        logWarn('VU with parse error cannot be formatted')
        return None

    # For output, additionally apply macros and validate the VU.
    if not vu.applyMacros(macros):
        return None
    apiName = applyMacrosToApiName(macros, apiName)
    if not vu.verify(registry, apiName):
        return None

    return vu

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
