#!/usr/bin/python3 -i
#
# Copyright (c) 2013-2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import sys
from generator import OutputGenerator, enquote, noneStr, write
import pprint

class PyOutputGenerator(OutputGenerator):
    """PyOutputGenerator - subclass of OutputGenerator.
    Generates Python data structures describing API names and relationships.
    Similar to DocOutputGenerator, but writes a single file."""

    def apiName(self, name):
        """Return True if name is in the reserved API namespace.

        Delegates to the conventions object. """
        return self.genOpts.conventions.is_api_name(name)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Track features being generated
        self.features = []

        # Reverse map from interface names to features requiring them
        self.apimap = {}

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
        #
        # Dictionaries are keyed by the name of the entity (e.g.
        # self.structs is keyed by structure names). Values are
        # the names of related entities (e.g. structs contain
        # a list of type names of members, enums contain a list
        # of enumerants belong to the enumerated type, etc.), or
        # just None if there are no directly related entities.
        #
        # Collect the mappings, then emit the Python script in endFile
        self.basetypes = {}
        self.consts = {}
        self.enums = {}
        self.flags = {}
        self.funcpointers = {}
        self.protos = {}
        self.structs = {}
        self.handles = {}
        self.defines = {}
        self.alias = {}
        # Dictionary containing the type of a type name
        # (e.g. the string name of the dictionary with its contents).
        self.typeCategory = {}
        self.mapDict = {}

    def addInterfaceMapping(self, api, feature, required):
        """Add a reverse mapping in self.apimap from an API to a feature
           requiring that API.

        - api - name of the API
        - feature - name of the feature requiring it
        - required - None, or an additional feature dependency within
          'feature' """

        # Each entry in self.apimap contains one or more
        # ( feature, required ) tuples.
        deps = ( feature, required )

        if api in self.apimap:
            self.apimap[api].append(deps)
        else:
            self.apimap[api] = [ deps ]

    def mapInterfaceKeys(self, feature, key):
        """Construct reverse mapping of APIs to features requiring them in
           self.apimap.

        - feature - name of the feature being generated
        - key - API category - 'define', 'basetype', etc."""

        dict = self.featureDictionary[feature][key]

        if dict:
            # Not clear why handling of command vs. type APIs is different -
            # see interfacedocgenerator.py, which this was based on.
            if key == 'command':
                for required in dict:
                    for api in dict[required]:
                        self.addInterfaceMapping(api, feature, required)
            else:
                for required in dict:
                    for parent in dict[required]:
                        for api in dict[required][parent]:
                            self.addInterfaceMapping(api, feature, required)

    def mapInterfaces(self, feature):
        """Construct reverse mapping of APIs to features requiring them in
           self.apimap.

        - feature - name of the feature being generated"""

        # Map each category of interface
        self.mapInterfaceKeys(feature, 'basetype')
        self.mapInterfaceKeys(feature, 'bitmask')
        self.mapInterfaceKeys(feature, 'command')
        self.mapInterfaceKeys(feature, 'define')
        self.mapInterfaceKeys(feature, 'enum')
        self.mapInterfaceKeys(feature, 'enumconstant')
        self.mapInterfaceKeys(feature, 'funcpointer')
        self.mapInterfaceKeys(feature, 'handle')
        self.mapInterfaceKeys(feature, 'include')
        self.mapInterfaceKeys(feature, 'struct')
        self.mapInterfaceKeys(feature, 'union')

    def endFile(self):
        # Print out all the dictionaries as Python strings.
        # Could just print(dict) but that's not human-readable
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
                  [ self.alias,         'alias' ] )
        for (entry_dict, name) in dicts:
            write(name + ' = {}', file=self.outFile)
            for key in sorted(entry_dict.keys()):
                write(name + '[' + enquote(key) + '] = ', entry_dict[key],
                      file=self.outFile)

        # Dictionary containing the relationships of a type
        # (e.g. a dictionary with each related type as keys).
        write('mapDict = {}', file=self.outFile)

        # Could just print(self.mapDict), but prefer something
        # human-readable and stable-ordered
        for baseType in sorted(self.mapDict.keys()):
            write('mapDict[' + enquote(baseType) + '] = ', file=self.outFile, end='')
            pprint.pprint(self.mapDict[baseType], self.outFile)

        # Generate feature <-> interface mappings
        for feature in self.features:
            self.mapInterfaces(feature)

        # Write out the reverse map from APIs to requiring features
        write('requiredBy = {}', file=self.outFile)

        for api in sorted(self.apimap):
            # Construct list of requirements as Python list arguments
            ##reqs = ', '.join('({}, {})'.format(enquote(dep[0]), enquote(dep[1])) for dep in self.apimap[api])
            ##write('requiredBy[{}] = ( {} )'.format(enquote(api), reqs), file=self.outFile)

            # Ideally these would be sorted by dep[0] as well
            reqs = ', '.join('({}, {})'.format(enquote(dep[0]), enquote(dep[1])) for dep in self.apimap[api])
            write('requiredBy[{}] = {}'.format(enquote(api), pprint.saferepr(self.apimap[api])), file=self.outFile)

        OutputGenerator.endFile(self)

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)

        # Add this feature to the list being tracked
        self.features.append( self.featureName )

    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    def addName(self, entry_dict, name, value):
        """Add a string entry to the dictionary, quoting it so it gets printed
        out correctly in self.endFile()."""
        entry_dict[name] = enquote(value)

    def addMapping(self, baseType, refType):
        """Add a mapping between types to mapDict.

        Only include API types, so we don't end up with a lot of useless uint32_t and void types."""
        if not self.apiName(baseType) or not self.apiName(refType):
            self.logMsg('diag', 'PyOutputGenerator::addMapping: IGNORE map from', baseType, '<->', refType)
            return

        self.logMsg('diag', 'PyOutputGenerator::addMapping: map from',
                    baseType, '<->', refType)

        if baseType not in self.mapDict:
            baseDict = {}
            self.mapDict[baseType] = baseDict
        else:
            baseDict = self.mapDict[baseType]
        if refType not in self.mapDict:
            refDict = {}
            self.mapDict[refType] = refDict
        else:
            refDict = self.mapDict[refType]

        baseDict[refType] = None
        refDict[baseType] = None

    def genType(self, typeinfo, name, alias):
        """Generate type.

        - For 'struct' or 'union' types, defer to genStruct() to
          add to the dictionary.
        - For 'bitmask' types, add the type name to the 'flags' dictionary,
          with the value being the corresponding 'enums' name defining
          the acceptable flag bits.
        - For 'enum' types, add the type name to the 'enums' dictionary,
          with the value being '@STOPHERE@' (because this case seems
          never to happen).
        - For 'funcpointer' types, add the type name to the 'funcpointers'
          dictionary.
        - For 'handle' and 'define' types, add the handle or #define name
          to the 'struct' dictionary, because that's how the spec sources
          tag these types even though they aren't structs."""
        OutputGenerator.genType(self, typeinfo, name, alias)
        typeElem = typeinfo.elem
        # If the type is a struct type, traverse the embedded <member> tags
        # generating a structure. Otherwise, emit the tag text.
        category = typeElem.get('category')

        # Add a typeCategory{} entry for the category of this type.
        self.addName(self.typeCategory, name, category)

        if category in ('struct', 'union'):
            self.genStruct(typeinfo, name, alias)
        else:
            if alias:
                # Add name -> alias mapping
                self.addName(self.alias, name, alias)

                # Always emit an alias (?!)
                count = 1

                # May want to only emit full type definition when not an alias?
            else:
                # Extract the type name
                # (from self.genOpts). Copy other text through unchanged.
                # If the resulting text is an empty string, don't emit it.
                count = len(noneStr(typeElem.text))
                for elem in typeElem:
                    count += len(noneStr(elem.text)) + len(noneStr(elem.tail))

            if count > 0:
                if category == 'bitmask':
                    requiredEnum = typeElem.get('requires')
                    self.addName(self.flags, name, requiredEnum)

                    # This happens when the Flags type is defined, but no
                    # FlagBits are defined yet.
                    if requiredEnum is not None:
                        self.addMapping(name, requiredEnum)
                elif category == 'enum':
                    # This case does not seem to come up. It nominally would
                    # result from
                    #   <type name="Something" category="enum"/>,
                    # but the output generator doesn't emit them directly.
                    self.logMsg('warn', 'PyOutputGenerator::genType: invalid \'enum\' category for name:', name)
                elif category == 'funcpointer':
                    self.funcpointers[name] = None
                elif category == 'handle':
                    self.handles[name] = None
                elif category == 'define':
                    self.defines[name] = None
                elif category == 'basetype':
                    # Don't add an entry for base types that are not API types
                    # e.g. an API Bool type gets an entry, uint32_t does not
                    if self.apiName(name):
                        self.basetypes[name] = None
                        self.addName(self.typeCategory, name, 'basetype')
                    else:
                        self.logMsg('diag', 'PyOutputGenerator::genType: unprocessed type:', name, 'category:', category)
            else:
                self.logMsg('diag', 'PyOutputGenerator::genType: unprocessed type:', name)

    def genStruct(self, typeinfo, typeName, alias):
        """Generate struct (e.g. C "struct" type).

        Add the struct name to the 'structs' dictionary, with the
        value being an ordered list of the struct member names."""
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)

        if alias:
            # Add name -> alias mapping
            self.addName(self.alias, typeName, alias)
        else:
            # May want to only emit definition on this branch
            True

        members = [member.text for member in typeinfo.elem.findall('.//member/name')]
        self.structs[typeName] = members
        memberTypes = [member.text for member in typeinfo.elem.findall('.//member/type')]
        for member_type in memberTypes:
            self.addMapping(typeName, member_type)

    def genGroup(self, groupinfo, groupName, alias):
        """Generate group (e.g. C "enum" type).

        These are concatenated together with other types.

        - Add the enum type name to the 'enums' dictionary, with
          the value being an ordered list of the enumerant names.
        - Add each enumerant name to the 'consts' dictionary, with
          the value being the enum type the enumerant is part of."""
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)
        groupElem = groupinfo.elem

        if alias:
            # Add name -> alias mapping
            self.addName(self.alias, groupName, alias)
        else:
            # May want to only emit definition on this branch
            True

        # Loop over the nested 'enum' tags.
        enumerants = [elem.get('name') for elem in groupElem.findall('enum')]
        for name in enumerants:
            self.addName(self.consts, name, groupName)
        self.enums[groupName] = enumerants

    def genEnum(self, enuminfo, name, alias):
        """Generate enumerant (compile-time constants).

        - Add the constant name to the 'consts' dictionary, with the
          value being None to indicate that the constant isn't
          an enumeration value."""
        OutputGenerator.genEnum(self, enuminfo, name, alias)

        if name not in self.consts:
            # Add a typeCategory{} entry for the category of this type.
            self.addName(self.typeCategory, name, 'consts')
            self.consts[name] = None
        # Otherwise, don't add it to the consts dictionary because it's
        # already present. This happens due to the generator 'reparentEnums'
        # parameter being False, so each extension enum appears in both the
        # <enums> type and in the <extension> or <feature> it originally
        # came from.

    def genCmd(self, cmdinfo, name, alias):
        """Generate command.

        - Add the command name to the 'protos' dictionary, with the
          value being an ordered list of the parameter names."""
        OutputGenerator.genCmd(self, cmdinfo, name, alias)

        if alias:
            # Add name -> alias mapping
            self.addName(self.alias, name, alias)
        else:
            # May want to only emit definition on this branch
            True

        # Add a typeCategory{} entry for the category of this type.
        self.addName(self.typeCategory, name, 'protos')

        params = [param.text for param in cmdinfo.elem.findall('param/name')]
        self.protos[name] = params
        paramTypes = [param.text for param in cmdinfo.elem.findall('param/type')]
        for param_type in paramTypes:
            self.addMapping(name, param_type)
