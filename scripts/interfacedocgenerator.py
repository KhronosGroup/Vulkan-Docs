#!/usr/bin/python3 -i
#
# Copyright 2013-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import re
from generator import OutputGenerator, write
from parse_dependency import dependencyLanguage

def interfaceDocSortKey(item):
    if item == None:
        return '\0'
    else:
        return item.casefold()

class InterfaceDocGenerator(OutputGenerator):
    """InterfaceDocGenerator - subclass of OutputGenerator.
    Generates AsciiDoc includes of the interfaces added by a an API version
    or extension."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.features = []

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

        # Create subdirectory, if needed
        self.makeDir(self.genOpts.directory)

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)

        self.features.append( self.featureName )

    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    def writeNewInterfaces(self, feature, key, title, markup, fp):
        dict = self.featureDictionary[feature][key]

        parentmarkup = markup
        if key == 'enumconstant':
            parentmarkup = 'elink:'

        if dict:
            write('=== ' + title, file=fp)
            write('',file=fp)

            # Loop through required blocks, sorted so they start with "core" features
            for required in sorted(dict, key = interfaceDocSortKey):
                # 'required' may be a boolean expression of extension
                # names.
                # Currently this syntax is the same as asciidoc conditional
                # syntax, but will eventually become more complex.
                if required is not None:
                    # Rewrite with spec macros and xrefs applied to names
                    requiredlink = dependencyLanguage(required, specmacros=True)

                    # @@ A better approach would be to actually evaluate the
                    # logical expression at generation time.
                    # If the extensions required are not in the spec build,
                    # then do not include these requirements.
                    # This would support arbitrarily complex expressions,
                    # unlike asciidoc ifdef syntax.
                    write('ifdef::' + required + '[]', file=fp)
                    write(f'If {requiredlink} is supported:', file=fp)
                    write('',file=fp)

                # Commands are relatively straightforward
                if key == 'command':
                    for api in sorted(dict[required]):
                        write('  * ' + markup + api, file=fp)
                # Types and constants are potentially parented, so need to handle that
                else:
                    # Loop through parents, sorted so they start with unparented items
                    for parent in sorted(dict[required], key = interfaceDocSortKey):
                        parentstring = ''
                        if parent:
                            parentstring = parentmarkup + (', ' + markup).join(parent.split(','))
                            write('  * Extending ' + parentstring + ':', file=fp)
                            for api in sorted(dict[required][parent]):
                                write('  ** ' + markup + api, file=fp)
                        else:
                            for api in sorted(dict[required][parent]):
                                write('  * ' + markup + api, file=fp)

                if required is not None:
                    write('endif::' + required + '[]', file=fp)
                write('',file=fp)

    def makeInterfaceFile(self, feature):
        """Generate a file containing feature interface documentation in
           asciidoctor markup form.

        - feature - name of the feature being generated"""

        filename = feature + self.genOpts.conventions.file_suffix
        fp = open(self.genOpts.directory + '/' + filename, 'w', encoding='utf-8')

        # Write out the lists of new interfaces added by the feature
        self.writeNewInterfaces(feature, 'define',      'New Macros',           'dlink:',   fp)
        self.writeNewInterfaces(feature, 'basetype',    'New Base Types',       'basetype:',fp)
        self.writeNewInterfaces(feature, 'handle',      'New Object Types',     'slink:',   fp)
        self.writeNewInterfaces(feature, 'command',     'New Commands',         'flink:',   fp)
        self.writeNewInterfaces(feature, 'struct',      'New Structures',       'slink:',   fp)
        self.writeNewInterfaces(feature, 'union',       'New Unions',           'slink:',   fp)
        self.writeNewInterfaces(feature, 'funcpointer', 'New Function Pointers','tlink:',   fp)
        self.writeNewInterfaces(feature, 'enum',        'New Enums',            'elink:',   fp)
        self.writeNewInterfaces(feature, 'bitmask',     'New Bitmasks',         'tlink:',   fp)
        self.writeNewInterfaces(feature, 'include',     'New Headers',          'code:',    fp)
        self.writeNewInterfaces(feature, 'enumconstant','New Enum Constants',   'ename:',   fp)

        fp.close()

    def endFile(self):
        # Generate metadoc feature files, in refpage and non-refpage form
        for feature in self.features:
            self.makeInterfaceFile(feature)

        OutputGenerator.endFile(self)
