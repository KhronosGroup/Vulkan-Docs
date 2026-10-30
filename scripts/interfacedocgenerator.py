#!/usr/bin/env python3 -i
#
# Copyright 2013-2026 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import re
from generator import OutputGenerator, write
from parse_dependency import dependencyLanguageSpecMacros, pruneDependency

def interfaceDocSortKey(item):
    if item == None:
        return '\0'
    else:
        return item.casefold()

class InterfaceDocGenerator(OutputGenerator):
    """InterfaceDocGenerator - subclass of OutputGenerator.
    Generates AsciiDoc includes of the interfaces added by an API version
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

    def inBuild(self, key, name):
        """Return whether an interface is part of the API being generated.

         - key - label of API element, as for writeNewInterfaces
         - name - name of the API element"""

        if key == 'command':
            infodict = self.registry.cmddict
        elif key == 'enumconstant':
            infodict = self.registry.enumdict
        else:
            infodict = self.registry.typedict

        # Names the registry does not know about are listed as before
        return self.registry.isElementRequired(name, infodict, default=True)

    def writeNewInterfaces(self, feature, key, title, markup, fp):
        """Generate lists of interfaces for an API feature

         - feature - name of the feature being generated
         - key - label of API element being generated, used to index into
           the featureDictionary for this feature
         - title - title for the subsection of the feature documentation for
           this type of API element
         - markup - API macro prefix for this type of API element
         - fp - file being written"""

        # Only list interfaces which are in this API, since a feature may name
        # interfaces which are removed (or not supported) for the API being
        # generated. Leave out any group of interfaces left empty.
        dict = {}
        for required, group in self.featureDictionary[feature][key].items():
            if key == 'command':
                names = [api for api in group if self.inBuild(key, api)]
                if names:
                    dict[required] = names
            else:
                parents = {}
                for parent, apis in group.items():
                    names = [api for api in apis if self.inBuild(key, api)]
                    if names:
                        parents[parent] = names
                if parents:
                    dict[required] = parents

        parentmarkup = markup
        if key == 'enumconstant':
            parentmarkup = 'elink:'

        if dict:
            write(f'=== {title}', file=fp)
            write('',file=fp)

            # Loop through required blocks, sorted so they start with "core" features
            # 'required', if not None, is a boolean expression of
            # extension names (the 'depends' XML attribute).
            # The expression may not be valid asciidoc conditional
            # syntax, since the 'depends' XML syntax is more powerful.
            # Consequently we no longer surround these interfaces with
            # asciidoc ifdef markup (per vulkan/vulkan#3907), instead
            # relying on the API name macros to render correctly.
            # An alternative is to actually evaluate the expression
            # here.
            for required in sorted(dict, key = interfaceDocSortKey):
                if required is not None:
                    # Leave out the versions and extensions which are not part
                    # of this API (use the expression as it is if what is left
                    # cannot be satisfied), then rewrite with spec macros and
                    # xrefs applied to names
                    pruned = pruneDependency(required, self.registry.isDependencyNameInAPI)
                    requiredlink = dependencyLanguageSpecMacros(pruned if pruned is not None else required)

                    write(f'If {requiredlink} is supported:', file=fp)
                    write('', file=fp)

                # Commands are relatively straightforward
                if key == 'command':
                    for api in sorted(dict[required]):
                        write(f'  * {markup}{api}', file=fp)
                # Types and constants are potentially parented, so need to handle that
                else:
                    # Loop through parents, sorted so they start with unparented items
                    for parent in sorted(dict[required], key = interfaceDocSortKey):
                        parentstring = ''
                        if parent:
                            # Do not display the parents not in this spec build
                            parentlist = []
                            for p in parent.split(','):
                                if self.registry.isElementRequired(p, self.registry.typedict):
                                    parentlist.append(parentmarkup + p)
                                else:
                                    print(f'Dropping {p} from extending structs')
                            parentstring = ', '.join(parentlist)
                        # If none of the parents are in this build, list the
                        # items as unparented rather than 'Extending :'
                        if parentstring != '':
                            write(f'  * Extending {parentstring}:', file=fp)

                            for api in sorted(dict[required][parent]):
                                write(f'  ** {markup}{api}', file=fp)
                        else:
                            # Do not emit _EXTENSION_NAME and _SPEC_VERSION
                            # 'enums' as linkable spec macros, because they
                            # are not APIs.
                            for api in sorted(dict[required][parent]):
                                if api.endswith('_EXTENSION_NAME') or api.endswith('_SPEC_VERSION'):
                                    write(f'  * etext:{api}', file=fp)
                                else:
                                    write(f'  * {markup}{api}', file=fp)

                write('', file=fp)

    def makeInterfaceFile(self, feature):
        """Generate a file containing feature interface documentation in
           asciidoctor markup form.

        - feature - name of the feature being generated"""

        filename = feature + self.genOpts.conventions.file_suffix
        fp = open(f'{self.genOpts.directory}/{filename}', 'w', encoding='utf-8')

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
