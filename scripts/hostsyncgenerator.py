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
    genCmd(cmdinfo)
    genType(typeinfo)
    endFile()"""
    # Generate Host Synchronized Parameters in a table at the top of the spec

    threadsafety = {
        'parameters': ValidityCollection(),
        'members': ValidityCollection(),
        'parameterlists': ValidityCollection(),
        'memberlists': ValidityCollection(),
        'implicit': ValidityCollection()
    }

    def makeParameterName(self, name):
        return f"pname:{name}"

    def makeFLink(self, name):
        return f"flink:{name}"

    def makeSLink(self, name):
        return f"slink:{name}"

    def writeBlock(self, basename, title, contents, add_conditional_footer):
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
                if add_conditional_footer:
                    write('\n^1^ See Valid Usage language for this token for details.', file=fp)
                write('****', file=fp)
                write('', file=fp)
            else:
                self.logMsg('diag', '# No contents for:', filename)

    def writeInclude(self):
        "Generates the asciidoc include files."""
        assert self.genOpts
        file_suffix = self.genOpts.conventions.file_suffix
        self.writeBlock(f'parameters{file_suffix}',
                        'Externally Synchronized Parameters and Members',
                        str(self.threadsafety['parameters']) + str(self.threadsafety['members']), True)
        self.writeBlock(f'parameterlists{file_suffix}',
                        'Externally Synchronized Parameter and Member Lists',
                        str(self.threadsafety['parameterlists']) + str(self.threadsafety['memberlists']), True)
        self.writeBlock(f'implicit{file_suffix}',
                        'Implicit Externally Synchronized Parameters',
                        self.threadsafety['implicit'], False)

    def makeThreadSafetyBlocks(self, token, paramtext):
        # This function is either called with 'param' or 'member', the former used with entry points and the latter with
        # struct types.
        isfunction = paramtext == 'param'

        # See also makeThreadSafetyBlock in validitygenerator.py - similar but not entirely identical
        tokenname = token.find('proto/name').text if isfunction else getElemName(token)

        # Find and add any parameters that are thread unsafe
        explicitexternsyncparams = token.findall(f"{paramtext}[@externsync]")
        if explicitexternsyncparams is not None:
            for param in explicitexternsyncparams:
                self.makeThreadSafetyForParam(tokenname, param, isfunction)

        # Find and add any "implicit" parameters that are thread unsafe
        implicitexternsyncparams = token.find('implicitexternsyncparams')
        if implicitexternsyncparams is not None:
            assert isfunction
            for elem in implicitexternsyncparams:
                entry = ValidityEntry()
                entry += elem.text
                entry += ' in '
                entry += self.makeFLink(tokenname)
                self.threadsafety['implicit'] += entry

        # Add a VU for any command requiring host synchronization.
        # This could be further parameterized, if a future non-Vulkan API
        # requires it.
        if self.genOpts.conventions.is_externsync_command(tokenname):
            assert isfunction
            entry = ValidityEntry()
            entry += 'The sname:VkCommandPool that pname:commandBuffer was allocated from, in '
            entry += self.makeFLink(tokenname)
            self.threadsafety['implicit'] += entry

    def makeThreadSafetyForParam(self, tokenname, param, isfunction):
        """Create thread safety validity for a single param of a command or member of struct."""
        externsyncattribs = ExternSyncEntry.parse_externsync_from_param(param)
        param_name = getElemName(param)

        collectionname = 'parameters' if isfunction else 'members'
        listcollectionname = 'parameterlists' if isfunction else 'memberlists'

        for attrib in externsyncattribs:
            entry = ValidityEntry()
            is_array = False
            if attrib.entirely_extern_sync:
                # "true" or "maybe"
                if self.paramIsArray(param):
                    entry += 'Each element of the '
                    is_array = True
                elif self.paramIsPointer(param):
                    entry += 'The object referenced by the '
                else:
                    entry += 'The '

                entry += self.makeParameterName(param_name)
                entry += ' parameter' if isfunction else ' member'

            else:
                # parameter/member reference
                readable = attrib.get_human_readable(make_param_name=self.makeParameterName)
                is_array = (' element of ' in readable)
                entry += readable

            if isfunction:
                entry += ' in '
                entry += self.makeFLink(tokenname)
            else:
                entry += ' of '
                entry += self.makeSLink(tokenname)

            if attrib.conditionally_extern_sync:
                entry += ', conditionally^1^'

            if is_array:
                self.threadsafety[listcollectionname] += entry
            else:
                self.threadsafety[collectionname] += entry

    def genCmd(self, cmdinfo, name, alias):
        "Generate command."
        OutputGenerator.genCmd(self, cmdinfo, name, alias)

        # @@@ (Jon) something needs to be done here to handle aliases, probably

        self.makeThreadSafetyBlocks(cmdinfo.elem, 'param')

    def genType(self, typeinfo, name, alias):
        "Generate struct."
        OutputGenerator.genType(self, typeinfo, name, alias)

        self.makeThreadSafetyBlocks(typeinfo.elem, 'member')

    def endFile(self):
        self.writeInclude()

        OutputGenerator.endFile(self)
