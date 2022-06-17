#!/usr/bin/python3 -i
#
# Copyright 2013-2022 The Khronos Group Inc.
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
        # <format, condition as asciidoc string>
        self.format_conditions = dict()
        # <class, {'formats' : [], 'meta' : {} }>
        self.format_classes = dict()
        # {'packedSize' : ['format', 'format', ...]}
        self.packed_info = dict()

    def endFile(self):

        # Generate compatibility table
        compatibility_table = []
        for class_name, info in self.format_classes.items():
            # Do an inital loop of formats in class to see if whole class is a single condition
            class_condition = None
            for index, format in enumerate(info['formats']):
                condition = self.format_conditions[format]
                if (condition == None) or (class_condition != None and class_condition != condition):
                    class_condition = None
                    break
                else:
                    class_condition = condition

            # If not single class condition for the class, next check if a single format has a condition
            # Move all condition formats to the front of array to make listing the formats in table
            if class_condition == None:
                condition_list = []
                noncondition_list = []
                for index, format in enumerate(info['formats']):
                    if self.format_conditions[format] == None:
                        noncondition_list.append(format)
                    else:
                        condition_list.append(format)
                info['formats'] = condition_list + noncondition_list

            if class_condition != None:
                compatibility_table.append('ifdef::{}[]'.format(class_condition))

            compatibility_table.append("| {} +".format(class_name))
            compatibility_table.append("  Block size {} byte +".format(info['meta']['blockSize']))
            compatibility_table.append("  {} block extent +".format(info['meta']['blockExtent'].replace(",", "x")))
            compatibility_table.append("  {} texel/block |".format(info['meta']['texelsPerBlock']))

            for index, format in enumerate(info['formats']):
                format_condition = self.format_conditions[format]
                if format_condition != None and class_condition == None:
                    compatibility_table.append('ifdef::{}[]'.format(format_condition))
                suffix = ", +" if index != len(info['formats']) - 1 else ""
                compatibility_table.append("                    ename:{}{}".format(format, suffix))
                if format_condition != None and class_condition == None:
                    compatibility_table.append('endif::{}[]'.format(format_condition))

            if class_condition != None:
                compatibility_table.append('endif::{}[]'.format(class_condition))
        self.writeBlock('compatibility.txt', compatibility_table)

        # Generate packed format list
        packed_table = []
        for packed_size, formats in self.packed_info.items():
            packed_table.append('  * <<formats-packed-{}-bit,Packed into {}-bit data types>>:'.format(packed_size, packed_size))
            # Do an inital loop of formats with same packed size to group conditional together for easier reading of final asciidoc
            sorted_formats = dict() # {condition : formats}
            for format in formats:
                format_condition = self.format_conditions[format]
                if format_condition == None:
                    format_condition = "None" # to allow as a key in the dict
                if format_condition not in sorted_formats:
                    sorted_formats[format_condition] = []
                sorted_formats[format_condition].append(format)

            for condition, condition_formats in sorted_formats.items():
                if condition != "None":
                    packed_table.append('ifdef::{}[]'.format(condition))
                for format in condition_formats:
                    packed_table.append('  ** ename:{}'.format(format))
                if condition != "None":
                    packed_table.append('endif::{}[]'.format(condition))
        self.writeBlock('packed.txt', packed_table)

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
        self.format_conditions[format_name] = format.condition

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
            # Assert all classes are using same meta info
            if class_meta != self.format_classes[class_name]['meta']:
                self.logMsg('error', 'Class meta info is not consistent for class ', class_name)
        else:
            self.format_classes[class_name] = {
                'formats' : [format_name],
                'meta' : class_meta
            }

        # Build list of formats with packed info in xml
        packed = elem.get('packed')
        if packed is not None:
            if packed not in self.packed_info:
                self.packed_info[packed] = []
            self.packed_info[packed].append(format_name)