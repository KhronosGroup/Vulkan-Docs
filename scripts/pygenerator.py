#!/usr/bin/env python3 -i
#
# Copyright 2013-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, enquote, write
from scriptgenerator import ScriptOutputGenerator
import pprint

class PyOutputGenerator(ScriptOutputGenerator):
    """PyOutputGenerator - subclass of ScriptOutputGenerator.
    Generates Python data structures describing API names and
    relationships."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def beginDict(self, name):
        """String starting definition of a named dictionary"""
        return f'{name} = {{'

    def endDict(self):
        """ String ending definition of a named dictionary"""
        return '}'

    def writeDict(self, dict, name, printValues = True):
        """Write dictionary as a Python dictionary with the given name.
           If printValues is False, just output keys with None values."""

        write(self.beginDict(name), file=self.outFile)
        for key in sorted(dict):
            if printValues:
                value = enquote(dict[key])
            else:
                value = 'None'
            write(f'{enquote(key)} : {value},', file=self.outFile)
        write(self.endDict(), file=self.outFile)

    def writeList(self, l, name):
        """Write list l as a Ruby hash with the given name"""

        self.writeDict(l, name, printValues = False)

    def endFile(self):
        # Creates the inverse mapping of nonexistent APIs to their aliases.
        super().createInverseMap()

        # Print out all the dictionaries as Python strings.
        # Could just print(dict) but that is not human-readable
        dicts = ( [ self.basetypes,     'basetypes' ],
                  [ self.consts,        'consts' ],
                  [ self.enums,         'enums' ],
                  [ self.flags,         'flags' ],
                  [ self.funcpointers,  'funcpointers' ],
                  [ self.protos,        'protos' ],
                  [ self.structs,       'structs' ],
                  [ self.handles,       'handles' ],
                  [ self.defines,       'defines' ],
                  [ self.typeCategory,  'typeCategory' ],
                  [ self.alias,         'alias' ],
                  [ self.nonexistent,   'nonexistent' ],
                )

        for (dict, name) in dicts:
            self.writeDict(dict, name)

        # Dictionary containing the relationships of a type
        # (e.g. a dictionary with each related type as keys).
        # Could just print(self.mapDict), but prefer something
        # human-readable and stable-ordered
        write(self.beginDict('mapDict'), file=self.outFile)
        for baseType in sorted(self.mapDict.keys()):
            write('{} : {},'.format(enquote(baseType),
                pprint.pformat(self.mapDict[baseType])), file=self.outFile)
        write(self.endDict(), file=self.outFile)

        # List of included feature names
        self.writeList(sorted(self.features), 'features')

        # Generate feature <-> interface mappings
        for feature in self.features:
            self.mapInterfaces(feature)

        # Write out the reverse map from APIs to requiring features
        write(self.beginDict('requiredBy'), file=self.outFile)
        for api in sorted(self.apimap):
            # Sort requirements by first feature in each one
            deps = sorted(self.apimap[api], key = lambda dep: dep[0])
            reqs = ', '.join('({}, {})'.format(enquote(dep[0]), enquote(dep[1])) for dep in deps)
            write('{} : [{}],'.format(enquote(api), reqs), file=self.outFile)
        write(self.endDict(), file=self.outFile)

        super().endFile()
