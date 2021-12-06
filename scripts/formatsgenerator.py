#!/usr/bin/python3 -i
#
# Copyright 2013-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, write
from spec_tools.attributes import ExternSyncEntry
from spec_tools.util import getElemName

import pdb

class FormatsOutputGenerator(OutputGenerator):
    """FormatsOutputGenerator - subclass of OutputGenerator.
    Generates AsciiDoc includes of the table for the format chapters
    of the API specification.

    ---- methods ----
    FormatsOutputGenerator(errFile, warnFile, diagFile) - args as for
      OutputGenerator. Defines additional internal state.
    ---- methods overriding base class ----
    genCmd(cmdinfo)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        # List of all the formats elements
        self.formats = []
        # <format, condition>
        self.format_conditions = dict()
        # <class, {'formats' : [], 'meta' : {} }>
        self.format_classes = dict()

    def getCondition(self, enable):
        """Return a strings which is the condition under which an
           enable is supported.

         - enable - ElementTree corresponding to an <enable> XML tag for a Format"""

        if enable.get('version'):
            # Turn VK_API_VERSION_1_0 -> VK_VERSION_1_0
            return enable.get('version').replace('API_', '')
        elif enable.get('extension'):
            return enable.get('extension')
        elif enable.get('struct') or enable.get('property'):
            return enable.get('requires')
        else:
            self.logMsg('error', 'Unrecognized Format enable')
            return ''

    def getConditions(self, enables):
        """Return a sorted list of strings which are conditions under which
           one or more of the enables is supported.

         - enables - ElementTree corresponding to a <format> XML tag"""

        conditions = set()
        for enable in enables.findall('enable'):
            condition = self.getCondition(enable)
            if condition != None:
                conditions.add(condition)
        return sorted(conditions)

    def endFile(self):
        compatibility_table = []

        # Generate compatibility table
        for class_name, info in self.format_classes.items():
            # Do an inital loop of formats in class to see if whole class is a single condition
            class_condition = []
            for index, format in enumerate(info['formats']):
                condition = self.format_conditions[format]
                if (len(condition) == 0) or (len(class_condition) != 0 and class_condition != condition):
                    class_condition = []
                    break
                else:
                    class_condition = condition

            # If not single class condition for the class, next check if a single format has a condition
            # Move all condition formats to the front of array to make listing the formats in table
            if len(class_condition) == 0:
                condition_list = []
                noncondition_list = []
                for index, format in enumerate(info['formats']):
                    if len(self.format_conditions[format]) == 0:
                        noncondition_list.append(format)
                    else:
                        condition_list.append(format)
                info['formats'] = condition_list + noncondition_list

            if len(class_condition) > 0:
                compatibility_table.append('ifdef::{}[]'.format(','.join(class_condition)))

            compatibility_table.append("| {} +".format(class_name))
            compatibility_table.append("  Block size {} byte +".format(info['meta']['blockSize']))
            compatibility_table.append("  {} block extent +".format(info['meta']['blockExtent'].replace(",", "x")))
            compatibility_table.append("  {} texel/block |".format(info['meta']['texelsPerBlock']))

            for index, format in enumerate(info['formats']):
                format_condition = self.format_conditions[format]
                if len(format_condition) > 0 and len(class_condition) == 0:
                    compatibility_table.append('ifdef::{}[]'.format(','.join(format_condition)))
                suffix = ", +" if index != len(info['formats']) - 1 else ""
                compatibility_table.append("                    ename:{}{}".format(format, suffix))
                if len(format_condition) > 0 and len(class_condition) == 0:
                    compatibility_table.append('endif::{}[]'.format(','.join(format_condition)))

            if len(class_condition) > 0:
                compatibility_table.append('endif::{}[]'.format(','.join(class_condition)))

        # Generate the asciidoc include files
        self.writeBlock('compatibility.txt', compatibility_table)
        # Finish processing in superclass
        OutputGenerator.endFile(self)

    def writeBlock(self, basename, contents):
        """Generate an include file.

        - directory - subdirectory to put file in
        - basename - base name of the file
        - contents - contents of the file (Asciidoc boilerplate aside)"""

        filename = self.genOpts.directory + '/' + basename
        self.logMsg('diag', '# Generating include file:', filename)
        with open(filename, 'w', encoding='utf-8') as fp:
            write(self.genOpts.conventions.warning_comment, file=fp)

            if len(contents) > 0:
                for str in contents:
                    write(str, file=fp)
            else:
                self.logMsg('diag', '# No contents for:', filename)

    def genFormat(self, format, formatinfo, alias):
        """Generate Formats

        formatinfo - dictionary entry for an XML <format> element
        name - name attribute of format.elem"""

        OutputGenerator.genFormat(self, format, formatinfo, alias)
        elem = format.elem
        format_name = elem.get('name')

        self.formats.append(elem)
        self.format_conditions[format_name] = self.getConditions(elem)

        # Create format class data structure to be processed later
        class_name = elem.get('class')
        class_meta = {
            'blockSize' : elem.get('blockSize'),
            'texelsPerBlock' : elem.get('texelsPerBlock'),
            # default extent
            'blockExtent' : "1,1,1" if elem.get('blockExtent') == None else elem.get('blockExtent')
        }

        if class_name in self.format_classes:
            self.format_classes[class_name]['formats'].append(format_name)
            # Asser all classes are using same meta info
            if class_meta != self.format_classes[class_name]['meta']:
                self.logMsg('error', 'Class meta info is not consistent for class ', class_name)
        else:
            self.format_classes[class_name] = {
                'formats' : [format_name],
                'meta' : class_meta
            }