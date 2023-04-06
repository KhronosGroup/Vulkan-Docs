#!/usr/bin/python3 -i
# Copyright 2013-2023 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, enquote, write
from scriptgenerator import ScriptOutputGenerator
import pprint

def undefquote(s):
    if s:
        return enquote(s)
    else:
        return 'undefined'

class JSOutputGenerator(ScriptOutputGenerator):
    """JSOutputGenerator - subclass of ScriptOutputGenerator.
    Generates JavaScript data structures describing API names and
    relationships."""

    def __init__(self, *args, **kwargs):
        self.currentDict = None
        super().__init__(*args, **kwargs)

    def beginDict(self, name):
        """String starting definition of a named dictionary"""
        self.currentDict = name
        return f'exports.{name} = {{'

    def endDict(self):
        """ String ending definition of a named dictionary"""
        return '}'

    def writeDict(self, dict, name, printValues = True):
        """Write dictionary as a JavaScript object with the given name.
           If printValues is False, just output keys with undefined
           values."""

        write(self.beginDict(name), file=self.outFile)
        for key in sorted(dict):
            if printValues:
                value = undefquote(dict[key])
            else:
                value = 'undefined'
            write(f'{enquote(key)} : {value},', file=self.outFile)
        write(self.endDict(), file=self.outFile)

    def writeList(self, l, name):
        """Write list l as a JavaScript hash with the given name"""

        self.writeDict(l, name, printValues = False)

    def endFile(self):
        # Creates the inverse mapping of nonexistent APIs to their aliases.
        super().createInverseMap()

        # Print out all the dictionaries as JavaScript strings.
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
        write(self.beginDict('mapDict'), file=self.outFile)
        for baseType in sorted(self.mapDict):
            # Not actually including the relationships yet
            write(f'{enquote(baseType)} : undefined,',
                file=self.outFile)
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
            reqs = ', '.join('[{}, {}]'.format(undefquote(dep[0]), undefquote(dep[1])) for dep in deps)
            write('{} : [{}],'.format(enquote(api), reqs), file=self.outFile)
        write(self.endDict(), file=self.outFile)

        super().endFile()
