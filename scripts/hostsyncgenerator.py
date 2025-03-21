#!/usr/bin/env python3 -i
#
# Copyright 2013-2025 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, write
from spec_tools.attributes import ExternSyncEntry
from spec_tools.validity import ValidityCollection, ValidityEntry
from spec_tools.util import getElemName
from pathlib import Path


class HostSynchronizationOutputGenerator(OutputGenerator):
    """HostSynchronizationOutputGenerator - subclass of OutputGenerator.
    Generates AsciiDoc includes of the externsync parameter table for the
    fundamentals chapter of the API specification. Similar to
    DocOutputGenerator.

    ---- methods ----
    HostSynchronizationOutputGenerator(errFile, warnFile, diagFile) - args as for
      OutputGenerator. Defines additional internal state.
    ---- methods overriding base class ----
    genCmd(cmdinfo)"""
    # Generate Host Synchronized Parameters in a table at the top of the spec

    threadsafety = {
        'parameters': ValidityCollection(),
        'parameterlists': ValidityCollection(),
        'implicit': ValidityCollection()
    }

    def makeParameterName(self, name):
        return f"pname:{name}"

    def makeFLink(self, name):
        return f"flink:{name}"

    def writeBlock(self, basename, title, contents):
        """Generate an include file.

        - directory - subdirectory to put file in
        - basename - base name of the file
        - contents - contents of the file (Asciidoc boilerplate aside)"""
        assert self.genOpts
        filename = Path(self.genOpts.directory) / basename
        self.logMsg('diag', '# Generating include file:', filename)
        with open(filename, 'w', encoding='utf-8') as fp:
            write(self.genOpts.conventions.warning_comment, file=fp)

            if contents:
                write(f'.{title}', file=fp)
                write('****', file=fp)
                write(contents, file=fp, end='')
                write('****', file=fp)
                write('', file=fp)
            else:
                self.logMsg('diag', '# No contents for:', filename)

    def writeInclude(self):
        "Generates the asciidoc include files."""
        assert self.genOpts
        file_suffix = self.genOpts.conventions.file_suffix
        self.writeBlock(f'parameters{file_suffix}',
                        'Externally Synchronized Parameters',
                        self.threadsafety['parameters'])
        self.writeBlock(f'parameterlists{file_suffix}',
                        'Externally Synchronized Parameter Lists',
                        self.threadsafety['parameterlists'])
        self.writeBlock(f'implicit{file_suffix}',
                        'Implicit Externally Synchronized Parameters',
                        self.threadsafety['implicit'])

    def makeThreadSafetyBlocks(self, cmd, paramtext):
        # See also makeThreadSafetyBlock in validitygenerator.py - similar but not entirely identical
        protoname = cmd.find('proto/name').text

        # Find and add any parameters that are thread unsafe
        explicitexternsyncparams = cmd.findall(f"{paramtext}[@externsync]")
        if explicitexternsyncparams is not None:
            for param in explicitexternsyncparams:
                self.makeThreadSafetyForParam(protoname, param)

        # Find and add any "implicit" parameters that are thread unsafe
        implicitexternsyncparams = cmd.find('implicitexternsyncparams')
        if implicitexternsyncparams is not None:
            for elem in implicitexternsyncparams:
                entry = ValidityEntry()
                entry += elem.text
                entry += ' in '
                entry += self.makeFLink(protoname)
                self.threadsafety['implicit'] += entry

        # Add a VU for any command requiring host synchronization.
        # This could be further parameterized, if a future non-Vulkan API
        # requires it.
        if self.genOpts.conventions.is_externsync_command(protoname):
            entry = ValidityEntry()
            entry += 'The sname:VkCommandPool that pname:commandBuffer was allocated from, in '
            entry += self.makeFLink(protoname)
            self.threadsafety['implicit'] += entry

    def makeThreadSafetyForParam(self, protoname, param):
        """Create thread safety validity for a single param of a command."""
        externsyncattribs = ExternSyncEntry.parse_externsync_from_param(param)
        param_name = getElemName(param)

        for attrib in externsyncattribs:
            entry = ValidityEntry()
            is_array = False
            if attrib.entirely_extern_sync:
                # "true" or "true_with_children"
                if self.paramIsArray(param):
                    entry += 'Each element of the '
                    is_array = True
                elif self.paramIsPointer(param):
                    entry += 'The object referenced by the '
                else:
                    entry += 'The '

                entry += self.makeParameterName(param_name)
                entry += ' parameter'

                if attrib.children_extern_sync:
                    entry += ', and any child handles,'

            else:
                # parameter/member reference
                readable = attrib.get_human_readable(make_param_name=self.makeParameterName)
                is_array = (' element of ' in readable)
                entry += readable

            entry += ' in '
            entry += self.makeFLink(protoname)

            if is_array:
                self.threadsafety['parameterlists'] += entry
            else:
                self.threadsafety['parameters'] += entry

    def genCmd(self, cmdinfo, name, alias):
        "Generate command."
        OutputGenerator.genCmd(self, cmdinfo, name, alias)

        # @@@ (Jon) something needs to be done here to handle aliases, probably

        self.makeThreadSafetyBlocks(cmdinfo.elem, 'param')

        self.writeInclude()
