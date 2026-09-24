#!/usr/bin/env python3 -i
#
# Copyright 2026 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

import os
from generator import write
from base_generator import BaseGenerator

# Display name for each graphics pipeline library subset, keyed by the
# <dynamicstate pipelinesubstate=""> value in the XML
PIPELINE_SUB_STATE_NAMES = {
    'Vertex Input': 'Vertex Input',
    'Pre-Rasterization Shader': 'Pre-Rasterization',
    'Fragment Shader': 'Fragment Shader',
    'Fragment Output': 'Fragment Output',
}

STATIC_STATE_FLAG_PROTOTYPE = {
    # TODO - Currently not static state here
}

class DynamicStateOutputGenerator(BaseGenerator):
    """
    DynamicStateOutputGenerator - Generates the AsciiDoc Dynamic State table.
    """

    def __init__(self, errFile=None, warnFile=None, diagFile=None):
        BaseGenerator.__init__(self)
        self.errFile = errFile
        self.warnFile = warnFile
        self.diagFile = diagFile

    def writeBlock(self, basename, contents):
        filename = os.path.join(self.genOpts.directory, basename)
        self.logMsg('diag', '# Generating include file:', filename)
        with open(filename, 'w', encoding='utf-8') as fp:
            write(self.genOpts.conventions.warning_comment, file=fp)
            for line in contents:
                write(line, file=fp)

    def getConditionLines(self, reqs):
        """
        Parses definingRequirements dict[extName, depends] into AsciiDoc ifdef/endif lines.
        Handles complex 'depends' scenarios.
        """
        if not reqs:
            return [], []

        exts = sorted(list(reqs.keys()))
        if exts == ['VK_VERSION_1_0']:
            return [], []

        # Group extensions by their dependency string
        # e.g., {'VK_NV_clip_space_w_scaling': ['VK_EXT_extended_dynamic_state3', 'VK_EXT_shader_object']}
        deps_to_exts = {}
        for ext, dep in reqs.items():
            deps_to_exts.setdefault(dep, []).append(ext)

        # If all defining requirements share the exact same dependencies
        if len(deps_to_exts) == 1:
            dep = list(deps_to_exts.keys())[0]

            open_ifdefs = []
            close_endifs = []

            # The outer OR condition for the extensions providing it
            cond = ",".join(exts)
            open_ifdefs.append(f"ifdef::{cond}[]")
            close_endifs.insert(0, f"endif::{cond}[]")

            # The nested AND condition for the dependencies (e.g., VK_NV_clip_space_w_scaling)
            if dep:
                # '+' in depends represents AND in Vulkan XML
                for sub_dep in dep.split('+'):
                    open_ifdefs.append(f"ifdef::{sub_dep}[]")
                    close_endifs.insert(0, f"endif::{sub_dep}[]")

            return open_ifdefs, close_endifs

        # Fallback for mixed dependencies (e.g., feature promoted to core with no dependencies,
        # but extension retains dependencies). AsciiDoc does not easily support (A AND B) OR C,
        # so we fall back to just tracking the base extensions to prevent hiding core functionality.
        cond = ",".join(exts)
        return [f"ifdef::{cond}[]"], [f"endif::{cond}[]"]

    def getStateConditions(self, ds):
        """Returns the ifdef/endif lines wrapping a whole dynamic state.
        Uses the VkDynamicState of the first command, as that is what defines when the state exists."""
        if not (ds.commands and ds.commands[0].pipelineEnum and 'VkDynamicState' in self.vk.enums):
            return [], []
        enum_field = next((f for f in self.vk.enums['VkDynamicState'].fields if f.name == ds.commands[0].pipelineEnum), None)
        if not (enum_field and enum_field.definingRequirements):
            return [], []
        return self.getConditionLines(enum_field.definingRequirements)

    def shaderStageName(self, ds):
        if ds.shaderStage == 'VK_SHADER_STAGE_ALL':
            return 'Any'
        if not ds.shaderStage:
            return ''
        # VK_SHADER_STAGE_TESSELLATION_EVALUATION_BIT -> Tessellation Evaluation
        raw_stage = ds.shaderStage.replace('VK_SHADER_STAGE_', '').replace('_BIT', '')
        return ' '.join(word.capitalize() for word in raw_stage.split('_'))

    def pipelineStateName(self, ds):
        if not ds.pipelineSubStates:
            # Not graphics (ex VK_DYNAMIC_STATE_RAY_TRACING_PIPELINE_STACK_SIZE_KHR)
            return 'None'
        return ', '.join(PIPELINE_SUB_STATE_NAMES.get(sub_state, sub_state) for sub_state in ds.pipelineSubStates)

    def dependsOn(self, ds):
        """The other dynamic state and/or special condition this state is ignored without."""
        deps = []
        if ds.stateRequired:
            # Link to that state's own row in this table
            deps.append(f'<<dynamic-state-{ds.stateRequired}, pname:{ds.stateRequired}>>')
        if ds.specialRequired:
            deps.append(f'<<shaders-special-{ds.specialRequired}, {ds.specialRequired}>>')
        return ' and '.join(deps) if deps else 'None'

    def enabledBy(self, ds):
        """Text for the feature(s) or extension that must be enabled for the state to be available, or None."""
        features = []
        extensions = []
        for enable in ds.enable:
            if enable.feature:
                features.append(f'<<features-{enable.feature}, pname:{enable.feature}>>')
            elif enable.extension:
                extensions.append(f'`apiext:{enable.extension}`')
            # No <dynamicstate> uses version= or property= today

        if features:
            if len(features) == 1:
                return f'Requires the {features[0]} feature'
            return f'Requires any of the {", ".join(features[:-1])} or {features[-1]} features'
        if extensions:
            return f'Requires the {" or ".join(extensions)} extension'
        return None

    def commandLines(self, ds, ds_open):
        """Bullet list of the commands which set this state dynamically, each with its VkDynamicState,
        wrapped in its own ifdef/endif where that differs from the whole row's condition."""
        lines = []
        for cmd in ds.commands:
            cmd_str = f'* flink:{cmd.name}'
            if cmd.pipelineEnum:
                cmd_str += f' (ename:{cmd.pipelineEnum})'
            if cmd.pipelineOnly:
                cmd_str += ' - pipelines only'

            cmd_obj = self.vk.commands.get(cmd.name)
            cmd_reqs = cmd_obj.definingRequirements if (cmd_obj and cmd_obj.definingRequirements) else {}
            cmd_open, cmd_close = self.getConditionLines(cmd_reqs)

            # Only wrap the command if it requires something beyond base 1.0
            # AND it differs from the outer block's conditions
            if cmd_open and cmd_open != ds_open:
                lines.extend(cmd_open)
                lines.append(cmd_str)
                lines.extend(cmd_close)
            else:
                lines.append(cmd_str)
        return lines

    def generate(self):
        out = []

        out.append('.Dynamic State Table')
        out.append('[cols="23%,13%,18%,12%,34%",options="header"]')
        out.append('|====')
        out.append('| Dynamic State | Shader Stage | Pipeline State | Requires Rasterization | Depends On')

        for ds_name, ds in self.vk.dynamicStates.items():
            ds_open, ds_close = self.getStateConditions(ds)
            out.extend(ds_open)

            # First row: the name (spanning both rows) and the short attributes
            out.append(f'.2+| [[dynamic-state-{ds_name}]]pname:{ds_name}')
            out.append(f'| {self.shaderStageName(ds)}')
            out.append(f'| {self.pipelineStateName(ds)}')
            out.append(f'| {"Yes" if ds.requiresRasterization else "No"}')
            out.append(f'| {self.dependsOn(ds)}')

            # Second row: everything with a long identifier, spanning the remaining columns.
            # Preprocessor directives must be on their own line to be parsed, so the cell
            # content always starts on the line after the cell separator.
            out.append('4+a|')
            out.extend(self.commandLines(ds, ds_open))

            enabled_by = self.enabledBy(ds)
            if enabled_by:
                out.append(f'* {enabled_by}')

            static_flag = STATIC_STATE_FLAG_PROTOTYPE.get(ds_name)
            if static_flag:
                out.append(f'* Static with code:{static_flag}')

            out.extend(ds_close)

        out.append('|====')

        self.writeBlock(f'dynamic_state_table{self.file_suffix}', out)
