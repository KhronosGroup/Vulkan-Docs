#!/usr/bin/python3 -i
#
# Copyright 2013-2024 The Khronos Group Inc.
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
        # {VkFormat : SpirvFormat}
        self.spirv_image_format = dict()
        # <format, [{plane_info}, ...]>
        self.plane_format = dict()

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
        self.writeBlock(f'compatibility{self.file_suffix}', compatibility_table)

        # Generate packed format list
        packed_table = []
        for packed_size, formats in self.packed_info.items():
            packed_table.append('  * <<formats-packed-{}-bit,Packed into {}-bit data types>>:'.format(packed_size, packed_size))
            # Do an initial loop of formats with same packed size to group conditional together for easier reading of final asciidoc
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
        self.writeBlock(f'packed{self.file_suffix}', packed_table)

        # Generate SPIR-V Image Format Compatibility
        spirv_image_format_table = []
        spirv_image_format_table.append('|code:Unknown|Any')
        for vk_format, spirv_format in self.spirv_image_format.items():
            spirv_image_format_table.append('|code:{}|ename:{}'.format(spirv_format, vk_format))
        self.writeBlock(f'spirvimageformat{self.file_suffix}', spirv_image_format_table)

        # Generate Plane Format Compatibility Table
        plane_format_table = []
        for format_name, plane_infos in self.plane_format.items():
            format_condition = self.format_conditions[format_name]
            # The table is already in a ifdef::VK_VERSION_1_1,VK_KHR_sampler_ycbcr_conversion[]
            # so no need to duplicate the condition
            add_condition = False if format_condition == 'None' or format_condition == 'VK_VERSION_1_1,VK_KHR_sampler_ycbcr_conversion' else True

            if add_condition:
                plane_format_table.append('ifdef::{}[]'.format(format_condition))

            plane_format_table.append('4+| *ename:{}*'.format(format_name))
            for plane_info in plane_infos:
                width_divisor = 'w'
                height_divisor = 'h'
                if plane_info['widthDivisor'] != 1:
                    width_divisor += '/{}'.format(plane_info['widthDivisor'])
                if plane_info['heightDivisor'] != 1:
                    height_divisor += '/{}'.format(plane_info['heightDivisor'])

                plane_format_table.append('^| {} ^| ename:{} ^| {} ^| {}'.format(plane_info['index'],
                                                                                 plane_info['compatible'],
                                                                                 width_divisor,
                                                                                 height_divisor))
            if add_condition:
                plane_format_table.append('endif::{}[]'.format(format_condition))
        self.writeBlock(f'planeformat{self.file_suffix}', plane_format_table)

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
