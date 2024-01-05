#!/usr/bin/python3 -i
#
# Copyright 2013-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, enquote, noneStr

def mostOfficial(api, newapi):
    """Return the 'most official' of two related names, api and newapi.
       KHR is more official than EXT is more official than everything else.
       If there is ambiguity, return api.
       Accommodate APIs using lower-case vendor suffixes."""

    apicat = api[-3:].upper()
    newapicat = newapi[-3:].upper()

    if apicat == 'KHR':
        return api
    if newapicat == 'KHR':
        return newapi;
    if apicat == 'EXT':
        return api
    if newapicat == 'EXT':
        return newapi;
    return api

class ScriptOutputGenerator(OutputGenerator):
    """ScriptOutputGenerator - subclass of OutputGenerator.
    Base class to Generate script (Python/Ruby/JS/etc.) data structures
    describing API names and relationships.
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

        # Reverse map from unsupported APIs in this build to aliases which
        # are supported
        self.nonexistent = {}

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
          'feature'. The additional dependency is a boolean expression of
          one or more extension and/or core version names, which is passed
          through to the output script intact."""

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
        super().endFile()

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)

        # Add this feature to the list being tracked
        self.features.append( self.featureName )

    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    def addName(self, dict, name, value):
        """Add a string entry to the dictionary, quoting it so it gets
           printed out correctly in self.endFile()."""
        dict[name] = value

    def addMapping(self, baseType, refType):
        """Add a mapping between types to mapDict.

        Only include API types, so we do not end up with a lot of useless
        uint32_t and void types."""
        if not self.apiName(baseType) or not self.apiName(refType):
            self.logMsg('diag', 'ScriptOutputGenerator::addMapping: IGNORE map from', baseType, '<->', refType)
            return

        self.logMsg('diag', 'ScriptOutputGenerator::addMapping: map from',
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

    def breakCheck(self, procname, name):
        """Debugging aid - call from procname to break on API 'name' if it
           matches logic in this call."""

        pat = 'VkExternalFenceFeatureFlagBits'
        if name[0:len(pat)] == pat:
            print('{}(name = {}) matches {}'.format(procname, name, pat))
            import pdb
            pdb.set_trace()

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
          to the 'struct' dictionary, because that is how the spec sources
          tag these types even though they are not structs."""
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
                # If the resulting text is an empty string, do not emit it.
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
                    # but the output generator does not emit them directly.
                    self.logMsg('warn', 'ScriptOutputGenerator::genType: invalid \'enum\' category for name:', name)
                elif category == 'funcpointer':
                    self.funcpointers[name] = None
                elif category == 'handle':
                    self.handles[name] = None
                elif category == 'define':
                    self.defines[name] = None
                elif category == 'basetype':
                    self.basetypes[name] = None
                    self.addName(self.typeCategory, name, 'basetype')
            else:
                self.logMsg('diag', 'ScriptOutputGenerator::genType: unprocessed type:', name)

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

        # Add a typeCategory{} entry for the category of this type.
        self.addName(self.typeCategory, groupName, 'group')

        if alias:
            # Add name -> alias mapping
            self.addName(self.alias, groupName, alias)
        else:
            # May want to only emit definition on this branch
            True

        # Add each nested 'enum' tag
        enumerants = [elem.get('name') for elem in groupElem.findall('enum')]
        for name in enumerants:
            self.addName(self.consts, name, groupName)

        # Sort enums for output stability, since their order is irrelevant
        self.enums[groupName] = sorted(enumerants)

    def genEnum(self, enuminfo, name, alias):
        """Generate enumerant (compile time constant).

        - Add the constant name to the 'consts' dictionary, with the
          value being None to indicate that the constant is not
          an enumeration value."""
        OutputGenerator.genEnum(self, enuminfo, name, alias)

        if name not in self.consts:
            # Add a typeCategory{} entry for the category of this type.
            self.addName(self.typeCategory, name, 'consts')
            self.consts[name] = None

        if alias:
            # Add name -> alias mapping
            self.addName(self.alias, name, alias)
        else:
            # May want to only emit definition on this branch
            True

        # Otherwise, do not add it to the consts dictionary because it is
        # already present. This happens due to the generator 'reparentEnums'
        # parameter being False, so each extension enum appears in both the
        # <enums> type and in the <extension> or <feature> it originally
        # came from.

    def genCmd(self, cmdinfo, name, alias):
        """Generate command.

        - Add the command name to the 'protos' dictionary, with the
          value being an ordered list of the parameter names."""
        OutputGenerator.genCmd(self, cmdinfo, name, alias)

        # Add a typeCategory{} entry for the category of this type.
        self.addName(self.typeCategory, name, 'protos')

        if alias:
            # Add name -> alias mapping
            self.addName(self.alias, name, alias)
        else:
            # May want to only emit definition on this branch
            True

        params = [param.text for param in cmdinfo.elem.findall('param/name')]
        self.protos[name] = params
        paramTypes = [param.text for param in cmdinfo.elem.findall('param/type')]
        for param_type in paramTypes:
            self.addMapping(name, param_type)

    def createInverseMap(self):
        """This creates the inverse mapping of nonexistent APIs in this
           build to their aliases which are supported. Must be called by
           language-specific subclasses before emitting that mapping."""

        # Map from APIs not supported in this build to aliases that are.
        # When there are multiple valid choices for remapping, choose the
        # most-official suffixed one (KHR > EXT > vendor).
        for key in self.alias:
            # If the API key is aliased to something which does not exist,
            # then add the thing that does not exist to the nonexistent map.
            # This is used in spec macros to make promoted extension links
            # in specs built without the promoted interface refer to the
            # older interface instead.

            invkey = self.alias[key]

            if invkey not in self.typeCategory:
                if invkey in self.nonexistent:
                    # Potentially remap existing mapping to a more official
                    # alias.
                    self.nonexistent[invkey] = mostOfficial(self.nonexistent[invkey], key)
                else:
                    # Create remapping to an alias
                    self.nonexistent[invkey] = key
