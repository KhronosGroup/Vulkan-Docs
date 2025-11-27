#!/usr/bin/env python3 -i
#
# Copyright 2013-2025 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, write
from parse_dependency import evaluateDependency
import os

class SyncOutputGenerator(OutputGenerator):
    """SyncOutputGenerator - subclass of OutputGenerator.
    Generates AsciiDoc includes of the table for the Synchronization chapters
    of the API specification.

    ---- methods ----
    SyncOutputGenerator(errFile, warnFile, diagFile) - args as for
      OutputGenerator. Defines additional internal state.
    ---- methods overriding base class ----
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # List of all elements
        self.pipeline_stages = []
        self.access_flags = []

        # <Pipeline Stage, condition as asciidoc string>
        self.pipeline_stage_condition = dict()
        # <success flag, condition as asciidoc string>
        self.access_flag_condition = dict()

        # <Pipeline Stage, [equivalent pipeline stages]>
        self.pipeline_stage_equivalent = dict()
        # <Pipeline Stage, [queue support]>
        self.pipeline_stage_queue_support = dict()

        # <Access Flag, [equivalent access flaga]>
        self.access_flag_equivalent = dict()
        # <Access Flag, [pipeline stage support]>
        self.access_flag_stage_support = dict()

        self.pipeline_order_info = []

    def endFile(self):
        self.writeFlagDefinitions()
        self.supportedPipelineStages()
        self.supportedAccessTypes()
        self.pipelineOrdering()
        OutputGenerator.endFile(self)

    def writeBlock(self, basename, contents):
        """Generate an include file.

        - directory - subdirectory to put file in
        - basename - base name of the file
        - contents - contents of the file (Asciidoc boilerplate aside)"""

        filename = f"{self.genOpts.directory}/{basename}"
        self.logMsg('diag', '# Generating include file:', filename)
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(filename, 'w', encoding='utf-8') as fp:
            write(self.genOpts.conventions.warning_comment, file=fp)

            if len(contents) > 0:
                for str in contents:
                    write(str, file=fp)
            else:
                self.logMsg('diag', '# No contents for:', filename)

    def genSyncStage(self, stageinfo):
        OutputGenerator.genSyncStage(self, stageinfo)
        name = stageinfo.elem.get('name')
        self.pipeline_stages.append(name)

        if stageinfo.condition is not None:
            self.pipeline_stage_condition[name] = stageinfo.condition

        syncsupport = stageinfo.elem.find('syncsupport')
        if syncsupport is not None:
            self.pipeline_stage_queue_support[name] = syncsupport.get('queues').split(',')

        syncequivalent = stageinfo.elem.find('syncequivalent')
        if syncequivalent is not None:
            self.pipeline_stage_equivalent[name] = syncequivalent.get('stage').split(',')

    def genSyncAccess(self, accessinfo):
        OutputGenerator.genSyncStage(self, accessinfo)
        name = accessinfo.elem.get('name')
        self.access_flags.append(name)

        if accessinfo.condition is not None:
            self.access_flag_condition[name] = accessinfo.condition

        syncsupport = accessinfo.elem.find('syncsupport')
        if syncsupport is not None:
            self.access_flag_stage_support[name] = syncsupport.get('stage').split(',')

        syncequivalent = accessinfo.elem.find('syncequivalent')
        if syncequivalent is not None:
            self.access_flag_equivalent[name] = syncequivalent.get('access').split(',')

    def genSyncPipeline(self, pipelineinfo):
        OutputGenerator.genSyncStage(self, pipelineinfo)
        self.pipeline_order_info.append(pipelineinfo)

    def isSameConditionPipeline(self, condition, stage):
        if stage not in self.pipeline_stage_condition:
            return False
        if condition is None:
            return False
        return self.pipeline_stage_condition[stage] == condition

    def isSameConditionPipelineAccess(self, stage, flag):
        if stage not in self.pipeline_stage_condition:
            return False
        if flag not in self.access_flag_condition:
            return False
        return self.pipeline_stage_condition[stage] == self.access_flag_condition[flag]

    def evaluatePipelineIfdef(self, stage):
        """Evaluate condition under which a pipeline stage should be emitted.
           Returns (condition, result) where condition is the dependency
           string, result is a Boolean

           - stage - pipeline stage name"""

        if stage in self.pipeline_stage_condition:
            condition = self.pipeline_stage_condition[stage]
            result = evaluateDependency(condition, lambda name: name in self.registry.genFeatures.keys())
            return (condition, result)
        else:
            # No condition, so always include this stage
            return (None, True)

    def evaluateAccessIfdef(self, flag):
        """Evaluate condition under which an access flag should be emitted.
           Returns (condition, result) where condition is the dependency
           string, result is a Boolean

           - flag - access flag name"""

        if flag in self.access_flag_condition:
            condition = self.access_flag_condition[flag]
            result = evaluateDependency(condition, lambda name: name in self.registry.genFeatures.keys())
            return (condition, result)
        else:
            # No condition, so always include this flag
            return (None, True)

    def writeFlagDefinitions(self):
        for name, stages in self.pipeline_stage_equivalent.items():
            output = []
            for stage in stages:
                (condition, result) = self.evaluatePipelineIfdef(stage)
                if result:
                    output.append(f'  ** ename:{stage}')
                else:
                    output.append(f'// {condition} -> {result}, not emitting ** ename:{stage}')

            self.writeBlock(f'flagDefinitions/{name}{self.file_suffix}', output)

        for name, flags in self.access_flag_equivalent.items():
            output = []
            for flag in flags:
                (condition, result) = self.evaluateAccessIfdef(flag)
                if result:
                    output.append(f'  ** ename:{flag}')
                else:
                    output.append(f'// {condition} -> {result}, not emitting ** ename:{flag}')

            self.writeBlock(f'flagDefinitions/{name}{self.file_suffix}', output)

    def supportedPipelineStages(self):
        output = []
        for stage in self.pipeline_stages:
            (condition, result) = self.evaluatePipelineIfdef(stage)

            if result:
                queue_support = ''
                if stage not in self.pipeline_stage_queue_support:
                    queue_support = 'None required'
                else:
                    for queue in self.pipeline_stage_queue_support[stage]:
                        ename = f'ename:{queue}'
                        if queue_support != '':
                            queue_support += ' or '
                        queue_support += ename

                output.append(f'|ename:{stage} | {queue_support}')
            else:
                output.append(f'// {condition} -> {result}, not emitting | ename:{stage} | <queue support>')

        self.writeBlock(f'supportedPipelineStages{self.file_suffix}', output)

    def supportedAccessTypes(self):
        output = []
        for flag in self.access_flags:
            (condition, result) = self.evaluateAccessIfdef(flag)
            if result:
                output.append(f'|ename:{flag} |')

                if flag not in self.access_flag_stage_support:
                    output.append('\tAny')
                else:
                    stages = self.access_flag_stage_support[flag]
                    for index, stage in enumerate(stages):
                        end_symbol = ''
                        if index != (len(stages) - 1) and len(stages) > 1:
                            end_symbol = ','

                        if not self.isSameConditionPipelineAccess(stage, flag):
                            (condition, result) = self.evaluatePipelineIfdef(stage)
                        else:
                            result = True

                        if result:
                            output.append(f'\tename:{stage}{end_symbol}')
                        else:
                            output.append(f'// {condition} -> {result}, not emitting \tename:{stage}{end_symbol}')
            else:
                output.append(f'// {condition} -> {result}, not emitting | ename:{flag} | <flag stage support>')

        self.writeBlock(f'supportedAccessTypes{self.file_suffix}', output)

    def pipelineOrdering(self):
        for pipelineinfo in self.pipeline_order_info:
            output = []
            name = pipelineinfo.elem.get('name')
            depends = pipelineinfo.elem.get('depends')
            syncPipelineStages = pipelineinfo.elem.findall('syncpipelinestage')

            for stageElem in syncPipelineStages:
                stage = stageElem.text
                order = stageElem.get('order')
                before = stageElem.get('before')
                after = stageElem.get('after')
                if order == 'None':
                    continue

                if not self.isSameConditionPipeline(depends, stage):
                    (condition, result) = self.evaluatePipelineIfdef(stage)
                else:
                    result = True

                if result:
                    output.append(f'  * ename:{stage}')
                else:
                    output.append(f'// {condition} -> {result}, not emitting * ename:{stage}')

            file_name = name.replace(' ', '_')
            self.writeBlock(f'pipelineOrders/{file_name}{self.file_suffix}', output)
