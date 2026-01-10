#!/usr/bin/env python3 -i
#
# Copyright 2013-2026 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, write
from parse_dependency import evaluateDependency
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
        # {VkFormat : SpirvFormat}
        self.spirv_image_format = dict()
        # <format, [{plane_info}, ...]>
        self.plane_format = dict()

    def evaluateFormatCondition(self, format_name):
        """Evaluate condition under which a format should be emitted.
           Returns (condition, result) where condition is the dependency
           string, result is a Boolean

           - format_name - format name"""

        if format_name in self.format_conditions and self.format_conditions[format_name] is not None:
            condition = self.format_conditions[format_name]
            result = evaluateDependency(condition, lambda name: name in self.registry.genFeatures.keys())
            return (condition, result)
        else:
            # No condition, so always include this format
            return (None, True)

    def endFile(self):

        # Generate compatibility table
        compatibility_table = []
        for class_name, info in self.format_classes.items():
            # Do an initial loop of formats in class to see if whole class is a single condition
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

            # Evaluate class condition if present
            class_condition_result = True
            if class_condition != None:
                class_condition_result = evaluateDependency(class_condition, lambda name: name in self.registry.genFeatures.keys())
                if not class_condition_result:
                    compatibility_table.append(f'// {class_condition} -> {class_condition_result}, not emitting class {class_name}')

            if class_condition_result:
                def tableHeader(continued):
                    """Generate table header for this class.
                       If continued is True, mark it as a continuation of the
                       previous class."""

                    continuedText = '(continued) ' if continued else ''

                    compatibility_table.append(f"| {class_name} {continuedText}+")
                    compatibility_table.append(f"  Block size {info['meta']['blockSize']} byte +")
                    compatibility_table.append(f"  {info['meta']['blockExtent'].replace(',', 'x')} block extent +")
                    compatibility_table.append(f"  {info['meta']['texelsPerBlock']} texel/block |")

                tableHeader(continued = False)

                # This is an ad-hoc restriction due to a limitation of
                # asciidoctor-pdf, which fails with an error if a table cell is
                # too long for a single page.
                # Should be genericized to be reused for other, similar tables.
                max_table_rows = 44

                # First pass: determine which formats will be emitted
                emitted_formats = []
                for format in info['formats']:
                    (condition, result) = self.evaluateFormatCondition(format)
                    if result:
                        emitted_formats.append(format)
                    else:
                        compatibility_table.append(f'// {condition} -> {result}, not emitting ename:{format}')

                num_emitted = len(emitted_formats)

                # Second pass: emit the formats with correct suffixes and row breaks
                for emitted_index, format in enumerate(emitted_formats):
                    # Start a new table cell continuing the previous one BEFORE emitting the format
                    if emitted_index > 0 and emitted_index % max_table_rows == 0:
                        tableHeader(continued = True)

                    # Determine suffix for this format
                    # No suffix if this is the last format overall, or if the next format will trigger a table break
                    is_last_format = (emitted_index == num_emitted - 1)
                    next_triggers_break = ((emitted_index + 1) < num_emitted and
                                          (emitted_index + 1) % max_table_rows == 0)

                    if is_last_format or next_triggers_break:
                        suffix = ""
                    else:
                        suffix = ", +"

                    compatibility_table.append(f"                    ename:{format}{suffix}")

        self.writeBlock(f'compatibility{self.file_suffix}', compatibility_table)

        # Generate packed format list
        packed_table = []
        for packed_size, formats in self.packed_info.items():
            packed_table.append(f'  * <<formats-packed-{packed_size}-bit,Packed into {packed_size}-bit data types>>:')
            # Evaluate each format's condition and only emit if satisfied
            for format in formats:
                (condition, result) = self.evaluateFormatCondition(format)
                if result:
                    packed_table.append(f'  ** ename:{format}')
                else:
                    packed_table.append(f'// {condition} -> {result}, not emitting ** ename:{format}')
        self.writeBlock(f'packed{self.file_suffix}', packed_table)

        # Generate SPIR-V Image Format Compatibility
        spirv_image_format_table = []
        spirv_image_format_table.append('|code:Unknown|Any')
        for vk_format, spirv_format in self.spirv_image_format.items():
            spirv_image_format_table.append(f'|code:{spirv_format}|ename:{vk_format}')
        self.writeBlock(f'spirvimageformat{self.file_suffix}', spirv_image_format_table)

        # Generate Plane Format Compatibility Table
        plane_format_table = []
        for format_name, plane_infos in self.plane_format.items():
            (condition, result) = self.evaluateFormatCondition(format_name)

            if result:
                plane_format_table.append(f'4+| *ename:{format_name}*')
                for plane_info in plane_infos:
                    width_divisor = 'w'
                    height_divisor = 'h'
                    if plane_info['widthDivisor'] != 1:
                        width_divisor += f"/{plane_info['widthDivisor']}"
                    if plane_info['heightDivisor'] != 1:
                        height_divisor += f"/{plane_info['heightDivisor']}"

                    plane_format_table.append('^| {} ^| ename:{} ^| {} ^| {}'.format(plane_info['index'],
                                                                                     plane_info['compatible'],
                                                                                     width_divisor,
                                                                                     height_divisor))
            else:
                plane_format_table.append(f'// {condition} -> {result}, not emitting 4+| *ename:{format_name}*')
        self.writeBlock(f'planeformat{self.file_suffix}', plane_format_table)

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

        # Currently there is only at most one <spirvimageformat>
        spirv_image_format = elem.find('spirvimageformat')
        if (spirv_image_format is not None):
            self.spirv_image_format[format_name] = spirv_image_format.get('name')

        for plane in elem.iterfind('plane'):
            if format_name not in self.plane_format:
                # create list if first time
                self.plane_format[format_name] = []
            self.plane_format[format_name].append({
                'index' : int(plane.get('index')),
                'widthDivisor' : int(plane.get('widthDivisor')),
                'heightDivisor' : int(plane.get('heightDivisor')),
                'compatible' : plane.get('compatible'),
            })
