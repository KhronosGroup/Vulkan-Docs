#!/usr/bin/env python3 -i
#
# Copyright 2013-2026 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, write
from spec_tools.util import getElemName

import pdb

def makeLink(link, altlink = None):
    """Create an asciidoctor link, optionally with altlink text
       if provided"""

    if altlink is not None:
        return f'<<{link},{altlink}>>'
    else:
        return f'<<{link}>>'

class SpirvCapabilityOutputGenerator(OutputGenerator):
    """SpirvCapabilityOutputGenerator - subclass of OutputGenerator.
    Generates AsciiDoc includes of the SPIR-V capabilities table for the
    features chapter of the API specification.

    ---- methods ----
    SpirvCapabilityOutputGenerator(errFile, warnFile, diagFile) - args as for
      OutputGenerator. Defines additional internal state.
    ---- methods overriding base class ----
    genCmd(cmdinfo)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        # Accumulate SPIR-V capability and feature information
        self.spirv = []

    def getCondition(self, enable, parent):
        """Return a strings which is the condition under which an
           enable is supported.

         - enable - ElementTree corresponding to an <enable> XML tag for a
           SPIR-V capability or extension
         - parent - Parent <spirvcapability> or <spirvenable> ElementTree,
           used for error reporting"""

        if enable.get('version'):
            return enable.get('version')
        elif enable.get('extension'):
            return enable.get('extension')
        elif enable.get('struct') or enable.get('property'):
            return enable.get('requires')
        else:
            self.logMsg('error', f"<{parent.tag} name=\"{parent.get('name')}\"> is missing a required attribute for an <enable>")
            return ''

    def getConditions(self, enables):
        """Return a sorted list of strings which are conditions under which
           one or more of the enables is supported.

         - enables - ElementTree corresponding to a <spirvcapability> or
           <spirvextension> XML tag"""

        conditions = set()
        for enable in enables.findall('enable'):
            condition = self.getCondition(enable, parent=enables)
            if condition != None:
                conditions.add(condition)
        return sorted(conditions)

    def endFile(self):
        captable = []
        exttable = []

        # How to "indent" a pseudo-column for better use of space.
        # {captableindent} is defined in appendices/spirvenv.adoc
        indent = '{captableindent}'

        for elem in self.spirv:
            conditions = self.getConditions(elem)

            # Combine all conditions for enables and surround the row with
            # them
            if len(conditions) > 0:
                condition_string = ','.join(conditions)
                prefix = [ f'ifdef::{condition_string}[]' ]
                suffix = [ f'endif::{condition_string}[]' ]
            else:
                prefix = []
                suffix = []

            body = []

            # Generate an anchor for each capability
            if elem.tag == 'spirvcapability':
                anchor = f"[[spirvenv-capabilities-table-{elem.get('name')}]]"
            else:
                # <spirvextension> entries do not get anchors
                anchor = ''

            # First "cell" in a table row, and a break for the other "cells"
            body.append(f"| {anchor}code:{elem.get('name')} +")

            # Iterate over each enable emitting a formatting tag for it
            # Protect the term if there is a version or extension
            # requirement, and if there are multiple enables (otherwise,
            # the ifdef protecting the entire row will suffice).

            enables = [e for e in elem.findall('enable')]

            remaining = len(enables)
            for subelem in enables:
                remaining -= 1

                # Sentinel value
                linktext = None
                if subelem.get('version'):
                    version = subelem.get('version')

                    # Convert API enum to anchor for version appendices (versions-m.n)
                    # version must be the spec conditional macro VK_VERSION_m_n, not
                    # the API version macro VK_API_VERSION_m_n.
                    enable = version
                    link = f"versions-{version[-3:].replace('_', '.')}"
                    altlink = version

                    linktext = makeLink(link, altlink)
                elif subelem.get('extension'):
                    extension = subelem.get('extension')

                    enable = extension
                    link = extension
                    altlink = None

                    # This uses the extension name macro, rather than
                    # asciidoc markup
                    linktext = f'`apiext:{extension}`'
                elif subelem.get('struct'):
                    struct = subelem.get('struct')
                    feature = subelem.get('feature')
                    requires = subelem.get('requires')
                    alias = subelem.get('alias')

                    link_name = feature
                    # For cases, like bufferDeviceAddressEXT where need manual help
                    if alias:
                        link_name = alias

                    enable = requires
                    link = f"features-{link_name}"
                    altlink = f'sname:{struct}::pname:{feature}'

                    linktext = makeLink(link, altlink)
                else:
                    property = subelem.get('property')
                    member = subelem.get('member')
                    requires = subelem.get('requires')
                    value = subelem.get('value')

                    enable = requires
                    # Properties should have a "feature" prefix
                    link = f"limits-{member}"
                    # Display the property value by itself if it is not a boolean (matches original table)
                    # DenormPreserve is an example where it makes sense to just show the
                    #   member value as it is just a boolean and the name implies "true"
                    # GroupNonUniformVote is an example where the whole name is too long
                    #   better to just display the value
                    if value == "VK_TRUE":
                        altlink = f'sname:{property}::pname:{member}'
                    else:
                        altlink = f'{value}'

                    linktext = makeLink(link, altlink)

                # If there are no more enables, do not continue the last line
                if remaining > 0:
                    continuation = ' +'
                else:
                    continuation = ''

                # condition_string != enable is a small optimization
                if enable is not None and condition_string != enable:
                    body.append(f'ifdef::{enable}[]')
                body.append(f'{indent} {linktext}{continuation}')
                if enable is not None and condition_string != enable:
                    body.append(f'endif::{enable}[]')

            if elem.tag == 'spirvcapability':
                captable += prefix + body + suffix
            else:
                exttable += prefix + body + suffix

        # Generate the asciidoc include files
        self.writeBlock('captable.adoc', captable)
        self.writeBlock('exttable.adoc', exttable)

        # Finish processing in superclass
        OutputGenerator.endFile(self)

    def writeBlock(self, basename, contents):
        """Generate an include file.

        - directory - subdirectory to put file in
        - basename - base name of the file
        - contents - contents of the file (Asciidoc boilerplate aside)"""

        filename = f"{self.genOpts.directory}/{basename}"
        self.logMsg('diag', '# Generating include file:', filename)
        with open(filename, 'w', encoding='utf-8') as fp:
            write(self.genOpts.conventions.warning_comment, file=fp)

            if len(contents) > 0:
                for str in contents:
                    write(str, file=fp)
            else:
                self.logMsg('diag', '# No contents for:', filename)

    def genSpirv(self, capinfo, name, alias):
        """Generate SPIR-V capabilities

        capinfo - dictionary entry for an XML <spirvcapability> or
            <spirvextension> element
        name - name attribute of capinfo.elem"""

        OutputGenerator.genSpirv(self, capinfo, name, alias)

        # Just accumulate each element, process in endFile
        self.spirv.append(capinfo.elem)
