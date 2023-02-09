# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Utilities to strip a VU based on build configurations.  In particular, conditions such as
is_version(1, 3), is_ext_enabled() and is_feature_enabled() are changed to False in builds of the
spec that don't include the relevant version/extension/feature, then const-propagation is done to
simplify the VU.  VUs that are entirely stripped (i.e. hold no require() calls) are dropped from
the build."""

import ast
from reflib import logWarn
from vuAST import isComment

class VuBuildStrip(ast.NodeVisitor):
    """Strip a VU to remove references to Vulkan versions and extensions that
    are not being built."""
    def __init__(self, vu, versions, extensions, featureAvailability, structAvailability, enumAvailability):
        self.vu = vu
        """The original AST."""

        self.versions = versions
        """The versions being included in the build (e.g. ['VK_VERSION_1_0', 'VK_VERSION_1_1'])."""

        self.extensions = extensions
        """The extensions being included in the build."""

        # Note that asciidoctor turns all attributes to lower case.  To ensure no
        # case problems, deal with extensions in lower case only.
        self.versions = [version.lower() for version in self.versions]
        self.extensions = [ext.lower() for ext in self.extensions]

        self.versionsAndExtensions = self.versions + self.extensions
        """Aggregate of versions and extensions."""

        self.featureAvailability = featureAvailability
        """A map from feature names to the list of versions and extensions they
        are defined in.  If support for a version or extension is begin
        removed, so will the support for that feature."""

        self.structAvailability = structAvailability
        """A map from struct names to the list of versions and extensions they
        are defined in.  If support for a version or extension is begin
        removed, so will the support for that struct."""

        self.enumAvailability = enumAvailability
        """A map from enum value names to the list of versions and extensions
        they are defined in.  If support for a version or extension is begin
        removed, so will the support for that struct."""

        self.strippedVariables = dict()
        """Map of variables that have been stripped out -> their value.  When
        referenced, they are replaced with their value to allow
        const-propagation through them."""

    def strip(self):
        stripped = self.visit(self.vu.astExpanded)
        if stripped is not None:
            ast.fix_missing_locations(stripped)
        return stripped

    def warn(self, *args):
        logWarn(self.vu.filename + ':' + str(self.vu.fileline) + ':', *args)

    def stripBody(self, statements):
        result = []
        for statement in statements:
            stripped = self.visit(statement)
            if stripped is not None:
                # Flatten bodies of if if the condition is constant.
                if isinstance(stripped, list):
                    for s in stripped:
                        result.append(s)
                else:
                    result.append(stripped)

        # If the only thing left is comments, remove the block.
        if all([isinstance(statement, ast.Call) and isComment(statement) for statement in result]):
            return None

        return result if len(result) > 0 else None

    def stripIsVersion(self, node):
        # Verified by VuVerifier
        assert(len(node.args) == 2)
        assert(isinstance(node.args[0], ast.Constant))
        assert(isinstance(node.args[1], ast.Constant))

        version = f'vk_version_{node.args[0].value}_{node.args[1].value}'
        hasVersion = version in self.versions

        # Always strip is_version from the output.
        return ast.Constant(hasVersion)

    def stripIsExtEnabled(self, node):
        # Verified by VuVerifier
        assert(len(node.args) == 1)
        assert(isinstance(node.args[0], ast.Name))

        # Strip this if extension is not being built.  Otherwise it remains as a run-time if.
        if node.args[0].id.lower() not in self.extensions:
            return ast.Constant(False)

        return node

    def isDefinedInBuild(self, availabilityMap, name):
        for cond in availabilityMap[name]:
            # Each condition may be in the form of version+extension1+extension2.  They should all be built.
            if all([versionOrExtension.lower() in self.versionsAndExtensions
                    for versionOrExtension in cond.split('+')]):
                return True

        return False

    def stripIsFeatureEnabled(self, node):
        # Verified by VuVerifier
        assert(len(node.args) == 1)
        assert(isinstance(node.args[0], ast.Name))

        featureName = node.args[0].id
        assert(featureName in self.featureAvailability)

        # Strip this if none of the extensions and versions that expose this
        # feature are not being built.  Otherwise it remains as a run-time if.
        hasFeature = self.isDefinedInBuild(self.featureAvailability, featureName)

        if not hasFeature:
            # The spec defines a set of features that were added for older extensions that did not
            # have features when they were promoted to core.  When building older versions of the
            # spec, is_feature_enabled for those features should implicitly turn into is_ext_enabled
            # for the corresponding extension.
            extension_feature_alises = {
                    'shaderDrawParameters': 'VK_KHR_shader_draw_parameters',
                    'drawIndirectCount': 'VK_KHR_draw_indirect_count',
                    'samplerMirrorClampToEdge': 'VK_KHR_sampler_mirror_clamp_to_edge',
                    'descriptorIndexing': 'VK_EXT_descriptor_indexing',
                    'samplerFilterMinmax': 'VK_EXT_sampler_filter_minmax',
                    'shaderOutputViewportIndex': 'VK_EXT_shader_viewport_index_layer',
                    'shaderOutputLayer': 'VK_EXT_shader_viewport_index_layer',
            }

            if featureName in extension_feature_alises:
                extension = extension_feature_alises[featureName]
                # If extension is being built, replace with is_ext_enabled(extension).
                extCheck = ast.Call(ast.Name('is_ext_enabled', ast.Load()),
                                    [ast.Name(extension, ast.Load())],
                                    [])
                return self.stripIsExtEnabled(extCheck)

            return ast.Constant(False)

        return node

    def stripHasPnext(self, node):
        # Verified by VuVerifier
        assert(len(node.args) == 1)
        assert(isinstance(node.args[0], ast.Name))
        assert(node.args[0].id in self.structAvailability)

        # Strip this if none of the extensions and versions that expose this
        # struct are not being built.  Otherwise it remains as a run-time if.
        hasStruct = self.isDefinedInBuild(self.structAvailability, node.args[0].id)

        if not hasStruct:
            return ast.Constant(False)

        return node

    def stripHasBit(self, node):
        # Verified by VuVerifier
        assert(len(node.args) == 1)
        assert(isinstance(node.args[0], ast.Name))
        assert(node.args[0].id in self.enumAvailability)

        # Strip this if none of the extensions and versions that expose this
        # enum value are not being built.  Otherwise it remains as a run-time if.
        hasEnum = self.isDefinedInBuild(self.enumAvailability, node.args[0].id)

        if not hasEnum:
            return ast.Constant(False)

        return node

    def stripEnumComparison(self, node):
        # Verified by VuVerifier
        assert(len(node.ops) == 1)

        def stripEnum(availabilityMap, node):
            return (isinstance(node, ast.Name) and
                    node.id in availabilityMap and
                    not self.isDefinedInBuild(availabilityMap, node.id))

        stripLeftEnum = stripEnum(self.enumAvailability, node.left)
        stripRightEnum = stripEnum(self.enumAvailability, node.comparators[0])

        if stripLeftEnum or stripRightEnum:
            assert(isinstance(node.ops[0], ast.Eq) or isinstance(node.ops[0], ast.NotEq))

            # If comparing for equality with a stripped enum value, comparison would always fail.
            # If comparing not equal, it would always pass.
            return ast.Constant(not isinstance(node.ops[0], ast.Eq))

        return node

    def isConstantBool(self, node):
        return isinstance(node, ast.Constant) and isinstance(node.value, bool)

    def isConstantBoolValue(self, node, value):
        if isinstance(node, ast.Constant):
            assert(isinstance(node.value, bool))
            return node.value == value
        return False

    def visit_Module(self, node):
        newBody = self.stripBody(node.body)
        if newBody is None:
            return None
        return ast.Module(newBody, node.type_ignores)

    def visit_Expr(self, node):
        stripped = self.visit(node.value)
        return ast.Expr(stripped) if stripped is not None else None

    def visit_Assign(self, node):
        # Verified by VuVerifier
        assert(len(node.targets) == 1)
        variable = node.targets[0].id

        # Strip the RHS of assignment first.
        rhs = self.visit(node.value)

        # If constant, strip the variable.  Note: VuVerifier ensures that variables are immutable.
        if self.isConstantBool(rhs):
            self.strippedVariables[variable] = rhs.value
            return None

        # Otherwise create the assignment with the new rhs
        return ast.Assign(node.targets, rhs)

    def visit_If(self, node):
        # Strip the condition.  If the result is constant, only process the
        # true or false block.
        test = self.visit(node.test)

        if self.isConstantBool(test):
            return self.stripBody(node.body) if test.value == True else self.stripBody(node.orelse)

        # Otherwise strip both blocks
        trueBlock = self.stripBody(node.body)
        falseBlock = self.stripBody(node.orelse)

        # There are a couple of possibilities:
        #
        # - If both blocks are stripped, remove the if entirely
        # - If only the false block remains, create the if with the condition inversed
        # - If only the true block remains, create the if with only that block
        # - Otherwise, create the if with both blocks
        if trueBlock is None and falseBlock is None:
            return None

        if trueBlock is None:
            test = ast.UnaryOp(ast.Not(), test)
            return ast.If(test, falseBlock, [])

        return ast.If(test, trueBlock, [] if falseBlock is None else falseBlock)

    def visit_For(self, node):
        # Strip the iterator set; if empty, remove the entire loop.  This is
        # currently a no-op, but may be possible if list support is added.
        loopIter = self.visit(node.iter)
        if loopIter is None:
            return None

        # Strip the body; if empty, remove the entire loop too.
        body = self.stripBody(node.body)
        if body is None:
            return None

        return ast.For(node.target, loopIter, body, [])

    def visit_BoolOp(self, node):
        # Strip every subexpression.  The op is either & or |, and the
        # subexpressions that are constant are either dropped or they turn the
        # entire expression into constant.
        values = [self.visit(value) for value in node.values]

        zeroOperand = True if isinstance(node.op, ast.And) else False
        shortCircuitOperand = not zeroOperand

        # If there are any False subexpressions in &, or True subexpressions in
        # |, evaluate the entire expression to that constant.
        if any([self.isConstantBoolValue(value, shortCircuitOperand) for value in values]):
            return ast.Constant(shortCircuitOperand)

        # Otherwise remove any True subexpressions in & and False
        # subexpressions in |.
        values = [value for value in values if not self.isConstantBool(value)]

        # If nothing remains, the entire subexpression is a constant
        if len(values) == 0:
            return ast.Constant(zeroOperand)

        # If the expression is reduced to a single value, just return that
        if len(values) == 1:
            return values[0]

        return ast.BoolOp(node.op, values)

    def visit_UnaryOp(self, node):
        # Strip the operand.  Only do const-propagation if the operator is Not
        operand = self.visit(node.operand)

        if self.isConstantBool(operand):
            # No other operator accepts a boolean operand than Not
            assert(isinstance(node.op, ast.Not))
            return ast.Constant(not operand.value)

        # TODO: const-propagate integers

        # Remove any potential double-Nots.  For example, `not (X or not Y)`
        # can turn into `not not Y` if `X` is false.  Turn that into just `Y`.
        if (isinstance(node.op, ast.Not) and
            isinstance(operand, ast.UnaryOp) and
            isinstance(operand.op, ast.Not)):
            return operand.operand

        return ast.UnaryOp(node.op, operand)

    def visit_BinOp(self, node):
        # No boolean operations can be found in BinOp.
        # TODO: const-propagate integers
        return ast.BinOp(self.visit(node.left), node.op, self.visit(node.right))

    def visit_Compare(self, node):
        # Verified by VuVerifier
        assert(len(node.ops) == 1)

        # Strip for enums first; if either side is an enum not being built,
        # turn the comparison into a constant.
        node = self.stripEnumComparison(node)
        if self.isConstantBool(node):
            return node

        # Strip the operands.  If both are constant, evaluate the results.
        left = self.visit(node.left)
        right = self.visit(node.comparators[0])
        op = node.ops[0]

        if self.isConstantBool(left) and self.isConstantBool(right):
            assert(isinstance(op, ast.Eq) or isinstance(op, ast.NotEq))
            if isinstance(op, ast.Eq):
                value = left.value == right.value
            else:
                value = left.value != right.value
            return ast.Compare(value)

        # TODO: const-propagate integers

        return ast.Compare(left, [op], [right])

    def visit_Call(self, node):
        # Keep comments as they are
        if isComment(node):
            return node

        # Strip the operands
        args = [self.visit(arg) for arg in node.args]

        if isinstance(node.func, ast.Name):
            if node.func.id == 'require' and self.isConstantBool(args[0]):
                # For require() calls, drop the call if the argument is True.
                if args[0].value == True:
                    return None
                # If the argument is False, this is a badly written VU and a
                # warning is issued.  For example, a VU written as such:
                #
                #     if x != 0:
                #       require(is_feature_enabled(feature))
                #
                # would translate to (assuming feature is not being built):
                #
                #     if x != 0:
                #       require(False)
                #
                # It is better if the VU was instead written as:
                #
                #     if not is_feature_enabled(feature):
                #       require(x == 0)
                #
                # In that case, the VU would look like the following if feature
                # is not being built:
                #
                #     require(x == 0)
                #
                self.warn('require() condition evaluates to False in this build.')
                self.warn('This hurts VU readability, invert the VU logic instead.')

            elif node.func.id == 'is_version':
                return self.stripIsVersion(node)
            elif node.func.id == 'is_ext_enabled':
                return self.stripIsExtEnabled(node)
            elif node.func.id == 'is_feature_enabled':
                return self.stripIsFeatureEnabled(node)
            elif node.func.id == 'has_pnext':
                return self.stripHasPnext(node)
        else:
            assert(isinstance(node.func, ast.Attribute))
            if node.func.attr == 'has_pnext':
                return self.stripHasPnext(node)
            elif node.func.attr == 'has_bit':
                return self.stripHasBit(node)

        return ast.Call(self.visit(node.func), args, [])

    def visit_Attribute(self, node):
        return ast.Attribute(self.visit(node.value), node.attr, node.ctx)

    def visit_Subscript(self, node):
        return ast.Subscript(self.visit(node.value), self.visit(node.slice), node.ctx)

    def visit_IfExp(self, node):
        # Strip the condition.  If the result is constant, only process the
        # true or false expressions.
        test = self.visit(node.test)

        if self.isConstantBool(test):
            return self.visit(node.body) if test.value == True else self.visit(node.orelse)

        # Otherwise strip both expressions
        trueExpression = self.visit(node.body)
        falseExpression = self.visit(node.orelse)

        return ast.IfExp(test, trueExpression, falseExpression)

    def visit_Constant(self, node):
        return node

    def visit_Name(self, node):
        # If it is a stripped variable, replace it with its constant
        if node.id in self.strippedVariables:
            return ast.Constant(self.strippedVariables[node.id])

        # Otherwise keep the reference as-is.
        return node

class VuStripDeadCode(ast.NodeTransformer):
    """Strip a VU further to remove dead code.  This can happen after
    VuBuildStrip has removed code that has lead to unreferenced variables for
    example."""
    def __init__(self, vu):
        self.vu = vu
        """The original AST."""

        self.unreferencedVariables = self.findUnreferencedVariables()
        """A set of variables that are unreferenced and can be removed."""

        self.anyDeadCodeStripped = False
        """Whether any dead code was eliminated."""

    def findUnreferencedVariables(self):
        variables = set()
        symbolReferences = {}

        for node in ast.walk(self.vu):
            if isinstance(node, ast.Assign):
                # Verified by VuVerifier
                assert(len(node.targets) == 1)
                assert(node.targets[0].id not in variables)
                variables.add(node.targets[0].id)

            elif isinstance(node, ast.Name):
                if node.id not in symbolReferences:
                    symbolReferences[node.id] = 0
                symbolReferences[node.id] += 1

        return set([variable for variable in variables if symbolReferences[variable] <= 1])

    def strip(self):
        stripped = self.visit(self.vu)
        if stripped is not None:
            ast.fix_missing_locations(stripped)
        return stripped, self.anyDeadCodeStripped

    def stripBody(self, statements):
        result = []
        for statement in statements:
            stripped = self.visit(statement)
            if stripped is not None:
                result.append(stripped)
            else:
                self.anyDeadCodeStripped = True

        # If the only thing left is comments, remove the block.
        if (len(statements) > 0 and
            all([isComment(statement) for statement in result])):
            self.anyDeadCodeStripped = True
            return None

        return result if len(result) > 0 else None

    def visit_Module(self, node):
        newBody = self.stripBody(node.body)
        if newBody is None:
            return None
        return ast.Module(newBody, node.type_ignores)

    def visit_Assign(self, node):
        # If the variable is unreferenced, remove the assignment
        if node.targets[0].id in self.unreferencedVariables:
            self.anyDeadCodeStripped = True
            return None

        return node

    def visit_Pass(self, node):
        self.anyDeadCodeStripped = True
        return None

    def visit_If(self, node):
        trueBlock = self.stripBody(node.body)
        falseBlock = self.stripBody(node.orelse)

        if trueBlock is None and falseBlock is None:
            return None

        if trueBlock is None:
            test = ast.UnaryOp(ast.Not(), node.test)
            return ast.If(test, falseBlock, [])

        return ast.If(node.test, trueBlock, [] if falseBlock is None else falseBlock)

    def visit_For(self, node):
        body = self.stripBody(node.body)
        if body is None:
            return None

        return ast.For(node.target, node.iter, body, [])

def stripVUForBuild(vu, versions, extensions, featureAvailability, structAvailability, enumAvailability):
    """Strip a VU to remove references to Vulkan versions and extensions that
    are not being built.

    Takes the VU AST after macro substitution, the list of versions that are
    being built (such as ['VK_VERSION_1_0', 'VK_VERSION_1_1',
    'VK_VERSION_1_2']) and the list of extensions.  Note that normally the
    latest version (e.g. 1.2) implies the earlier versions (e.g. 1.1), but the
    Makefile technically allows building a later but not earlier version.

    The version and extension lists are used to turn is_ext_enabled() and
    is_feature_enabled() to False when not being included in build.  Similarly,
    has_pnext is turned to False for structs not being included in build, as
    well as has_bit and enum comparisons for unavailable enum values.
    is_version is turned to True or False such that it is never visible in the
    spec.

    Then, const-propagation is applied to the VU and the result is returned.
    """

    buildstrip = VuBuildStrip(vu, versions, extensions, featureAvailability, structAvailability, enumAvailability)
    stripped = buildstrip.strip()

    # Remove any dead code there might be left
    anyDeadCodeStripped = True
    while anyDeadCodeStripped and stripped is not None:
        dce = VuStripDeadCode(stripped)
        stripped, anyDeadCodeStripped = dce.strip()

    return stripped
