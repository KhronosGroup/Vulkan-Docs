#!/usr/bin/python3 -i
#
# Copyright 2013-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, enquote, write
from scriptgenerator import ScriptOutputGenerator

def nilquote(s):
    if s:
        return enquote(s)
    else:
        return 'nil'

def makeHash(name):
    return '@{} = {{'.format(name)

class RubyOutputGenerator(ScriptOutputGenerator):
    """RubyOutputGenerator - subclass of ScriptOutputGenerator.
    Generates Ruby data structures describing API names and
    relationships."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def endFile(self):
        ## Actually, this just prints out the dictionary *keys* for now.

        # Print out all the dictionaries as Ruby strings.

        # Use a simple container class for namespace control
        write('class APInames\n', ' def initialize', file=self.outFile)

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
                  [ self.alias,         'aliases' ] )
        for (entry_dict, name) in dicts:
            write(makeHash(name), file=self.outFile)
            for key in sorted(entry_dict.keys()):
                write('{} => {},'.format(enquote(key),
                      nilquote(entry_dict[key])), file=self.outFile)
            write('}', file=self.outFile)

        # Dictionary containing the relationships of a type
        # (e.g. a dictionary with each related type as keys).
        write(makeHash('mapDict'), file=self.outFile)
        for baseType in sorted(self.mapDict.keys()):
            # Not actually including the relationships yet
            write('{} => {},'.format(enquote(baseType), 'nil'),
                file=self.outFile)
        write('}', file=self.outFile)

        # Generate feature <-> interface mappings
        for feature in self.features:
            self.mapInterfaces(feature)

        # Write out the reverse map from APIs to requiring features
        write(makeHash('requiredBy'), file=self.outFile)
        for api in sorted(self.apimap):
            # Sort requirements by first feature in each one
            deps = sorted(self.apimap[api], key = lambda dep: dep[0])
            reqs = ', '.join('[{}, {}]'.format(nilquote(dep[0]), nilquote(dep[1])) for dep in deps)
            write('{} => [{}],'.format(enquote(api), reqs), file=self.outFile)
        write('}', file=self.outFile)

        # Remainder of the class definition
        # End initialize method
        write('end', file=self.outFile)

        # Accessor methods
        for (entry_dict, name) in dicts:
            write('def {}'.format(name), file=self.outFile)
            write('    @{}'.format(name), file=self.outFile)
            write('end', file=self.outFile)

        # Class end
        write('end', file=self.outFile)

        super().endFile()
