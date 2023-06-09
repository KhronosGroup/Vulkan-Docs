#!/usr/bin/python3 -i
#
# Copyright 2013-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, write
import os

queueTypeToQueueFlags = {
    'graphics' : 'VK_QUEUE_GRAPHICS_BIT',
    'compute' : 'VK_QUEUE_COMPUTE_BIT',
    'transfer' : 'VK_QUEUE_TRANSFER_BIT',
    'sparse_binding' : 'VK_QUEUE_SPARSE_BINDING_BIT',
    'decode' : 'VK_QUEUE_VIDEO_DECODE_BIT_KHR',
    'encode'  : 'VK_QUEUE_VIDEO_ENCODE_BIT_KHR',
    'opticalflow' : 'VK_QUEUE_OPTICAL_FLOW_BIT_NV',
}

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
        # <sccess flag, condition as asciidoc string>
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

        filename = self.genOpts.directory + '/' + basename
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

    def writePipelineIfdef(self, stage, list):
        condition = self.pipeline_stage_condition[stage] if stage in self.pipeline_stage_condition else None
        if condition is not None:
            list.append('ifdef::{}[]'.format(condition))

    def writePipelineEndif(self, stage, list):
        condition = self.pipeline_stage_condition[stage] if stage in self.pipeline_stage_condition else None
        if condition is not None:
            list.append('endif::{}[]'.format(condition))

    def writeAccessIfdef(self, flag, list):
        condition = self.access_flag_condition[flag] if flag in self.access_flag_condition else None
        if condition is not None:
            list.append('ifdef::{}[]'.format(condition))

    def writeAccessEndif(self, flag, list):
        condition = self.access_flag_condition[flag] if flag in self.access_flag_condition else None
        if condition is not None:
            list.append('endif::{}[]'.format(condition))

    def writeFlagDefinitions(self):
        for name, stages in self.pipeline_stage_equivalent.items():
            output = []
            for stage in stages:
                self.writePipelineIfdef(stage, output)
                output.append('  ** ename:{}'.format(stage))
                self.writePipelineEndif(stage, output)

            self.writeBlock(f'flagDefinitions/{name}{self.file_suffix}', output)

        for name, flags in self.access_flag_equivalent.items():
            output = []
            for flag in flags:
                self.writeAccessIfdef(flag, output)
                output.append('  ** ename:{}'.format(flag))
                self.writeAccessEndif(flag, output)

            self.writeBlock(f'flagDefinitions/{name}{self.file_suffix}', output)

    def supportedPipelineStages(self):
        output = []
        for stage in self.pipeline_stages:
            self.writePipelineIfdef(stage, output)
            queue_support = ''
            if stage not in self.pipeline_stage_queue_support:
                queue_support = 'None required'
            else:
                for queue in self.pipeline_stage_queue_support[stage]:
                    ename = 'ename:{}'.format(queueTypeToQueueFlags[queue])
                    if queue_support != '':
                        queue_support += ' or '
                    queue_support += ename

            output.append('|ename:{} | {}'.format(stage, queue_support))

            self.writePipelineEndif(stage, output)

        self.writeBlock(f'supportedPipelineStages{self.file_suffix}', output)

    def supportedAccessTypes(self):
        output = []
        for flag in self.access_flags:
            self.writeAccessIfdef(flag, output)
            output.append('|ename:{} |'.format(flag))

            if flag not in self.access_flag_stage_support:
                output.append('\tAny')
            else:
                stages = self.access_flag_stage_support[flag]
                for index, stage in enumerate(stages):
                    end_symbol = ''
                    if index != (len(stages) - 1) and len(stages) > 1:
                        end_symbol = ','

                    if not self.isSameConditionPipelineAccess(stage, flag):
                        self.writePipelineIfdef(stage, output)
                    output.append('\tename:{}{}'.format(stage, end_symbol))
                    if not self.isSameConditionPipelineAccess(stage, flag):
                        self.writePipelineEndif(stage, output)

            self.writeAccessEndif(flag, output)

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
                    self.writePipelineIfdef(stage, output)

                output.append('  * ename:{}'.format(stage))

                if not self.isSameConditionPipeline(depends, stage):
                    self.writePipelineEndif(stage, output)

            file_name = name.replace(' ', '_')
            self.writeBlock(f'pipelineOrders/{file_name}{self.file_suffix}', output)
