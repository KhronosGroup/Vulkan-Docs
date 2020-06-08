"""Provides EntityDatabase, a class that keeps track of spec-defined entities and associated macros."""

# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>

from abc import ABC, abstractmethod

from .shared import (CATEGORIES_WITH_VALIDITY, EXTENSION_CATEGORY,
                     NON_EXISTENT_MACROS, EntityData)
from .util import getElemName


def _entityToDict(data):
    return {
        'macro': data.macro,
        'filename': data.filename,
        'category': data.category,
        'directory': data.directory
    }


class EntityDatabase(ABC):
    """Parsed and processed information from the registry XML.

    Must be subclasses for each specific API.
    """

    ###
    # Methods that must be implemented in subclasses.
    ###
    @abstractmethod
    def makeRegistry(self):
        """Return a Registry object that has already had loadFile() and parseTree() called.

        Called only once during construction.
        """
        raise NotImplementedError

    @abstractmethod
    def getNamePrefix(self):
        """Return the (two-letter) prefix of all entity names for this API.

        Called only once during construction.
        """
        raise NotImplementedError

    @abstractmethod
    def getPlatformRequires(self):
        """Return the 'requires' string associated with external/platform definitions.

        This is the string found in the requires attribute of the XML for entities that
        are externally defined in a platform include file, like the question marks in:

        <type requires="???" name="int8_t"/>

        In Vulkan, this is 'vk_platform'.

        Called only once during construction.
        """
        raise NotImplementedError

    ###
    # Methods that it is optional to **override**
    ###
    def getSystemTypes(self):
        """Return an enumerable of strings that name system types.

        System types use the macro `code`, and they do not generate API/validity includes.

        Called only once during construction.
        """
        return []

    def getGeneratedDirs(self):
        """Return a sequence of strings that are the subdirectories of generates API includes.

        Called only once during construction.
        """
        return ['basetypes',
                'defines',
                'enums',
                'flags',
                'funcpointers',
                'handles',
                'protos',
                'structs']

    def populateMacros(self):
        """Perform API-specific calls, if any, to self.addMacro() and self.addMacros().

        It is recommended to implement/override this and call
        self.addMacros(..., ..., [..., "flags"]),
        since the base implementation, in _basicPopulateMacros(),
        does not add any macros as pertaining to the category "flags".

        Called only once during construction.
        """
        pass

    def populateEntities(self):
        """Perform API-specific calls, if any, to self.addEntity()."""
        pass

    def getEntitiesWithoutValidity(self):
        """Return an enumerable of entity names that do not generate validity includes."""
        return [self.mixed_case_name_prefix +
                x for x in ['BaseInStructure', 'BaseOutStructure']]

    def getExclusionSet(self):
        """Return a set of "support=" attribute strings that should not be included in the database.

        Called only during construction."""
        return set(('disabled',))

    ###
    # Methods that it is optional to **extend**
    ###
    def handleType(self, name, info, requires):
        """Add entities, if appropriate, for an item in registry.typedict.

        Called at construction for every name, info in registry.typedict.items()
        not immediately skipped,
        to perform the correct associated addEntity() call, if applicable.
        The contents of the requires attribute, if any, is passed in requires.

        May be extended by API-specific code to handle some cases preferentially,
        then calling the super implementation to handle the rest.
        """
        if requires == self.platform_requires:
            # Ah, no, don't skip this, it's just in the platform header file.
            # TODO are these code or basetype?
            self.addEntity(name, 'code', elem=info.elem, generates=False)
            return

        protect = info.elem.get('protect')
        if protect:
            self.addEntity(protect, 'dlink',
                           category='configdefines', generates=False)

        alias = info.elem.get('alias')
        if alias:
            self.addAlias(name, alias)

        cat = info.elem.get('category')
        if cat == 'struct':
            self.addEntity(name, 'slink', elem=info.elem)

        elif cat == 'union':
            # TODO: is this right?
            self.addEntity(name, 'slink', elem=info.elem)

        elif cat == 'enum':
            self.addEntity(
                name, 'elink', elem=info.elem)

        elif cat == 'handle':
            self.addEntity(name, 'slink', elem=info.elem,
                           category='handles')

        elif cat == 'bitmask':
            self.addEntity(
                name, 'tlink', elem=info.elem, category='flags')

        elif cat == 'basetype':
            self.addEntity(name, 'basetype',
                           elem=info.elem)

        elif cat == 'define':
            self.addEntity(name, 'dlink', elem=info.elem)

        elif cat == 'funcpointer':
            self.addEntity(name, 'tlink', elem=info.elem)

        elif cat == 'include':
            # skip
            return

        elif cat is None:
            self.addEntity(name, 'code', elem=info.elem, generates=False)

        else:
            raise RuntimeError('unrecognized category {}'.format(cat))

    def handleCommand(self, name, info):
        """Add entities, if appropriate, for an item in registry.cmddict.

        Called at construction for every name, info in registry.cmddict.items().
        Calls self.addEntity() accordingly.
        """
        self.addEntity(name, 'flink', elem=info.elem,
                       category='commands', directory='protos')

    def handleExtension(self, name, info):
        """Add entities, if appropriate, for an item in registry.extdict.

        Called at construction for every name, info in registry.extdict.items().
        Calls self.addEntity() accordingly.
        """
        if info.supported in self._supportExclusionSet:
            # Don't populate with disabled extensions.
            return

        # Only get the protect strings and name from extensions

        self.addEntity(name, None, category=EXTENSION_CATEGORY,
                       generates=False)
        protect = info.elem.get('protect')
        if protect:
            self.addEntity(protect, 'dlink',
                           category='configdefines', generates=False)

    def handleEnumValue(self, name, info):
        """Add entities, if appropriate, for an item in registry.enumdict.

        Called at construction for every name, info in registry.enumdict.items().
        Calls self.addEntity() accordingly.
        """
        self.addEntity(name, 'ename', elem=info.elem,
                       category='enumvalues', generates=False)

    ###
    # END of methods intended to be implemented, overridden, or extended in child classes!
    ###

    ###
    # Accessors
    ###
    def findMacroAndEntity(self, macro, entity):
        """Look up EntityData by macro and entity pair.

        Does **not** resolve aliases."""
        return self._byMacroAndEntity.get((macro, entity))

    def findEntity(self, entity):
        """Look up EntityData by entity name (case-sensitive).

        If it fails, it will try resolving aliases.
        """
        result = self._byEntity.get(entity)
        if result:
            return result

        alias_set = self._aliasSetsByEntity.get(entity)
        if alias_set:
            for alias in alias_set:
                if alias in self._byEntity:
                    return self.findEntity(alias)

            assert(not "Alias without main entry!")

        return None

    def findEntityCaseInsensitive(self, entity):
        """Look up EntityData by entity name (case-insensitive).

        Does **not** resolve aliases."""
        return self._byLowercaseEntity.get(entity.lower())

    def getMemberElems(self, commandOrStruct):
        """Given a command or struct name, retrieve the ETree elements for each member/param.

        Returns None if the entity is not found or doesn't have members/params.
        """
        data = self.findEntity(commandOrStruct)

        if not data:
            return None
        if data.elem is None:
            return None
        if data.macro == 'slink':
            tag = 'member'
        else:
            tag = 'param'
        return data.elem.findall('.//{}'.format(tag))

    def getMemberNames(self, commandOrStruct):
        """Given a command or struct name, retrieve the names of each member/param.

        Returns an empty list if the entity is not found or doesn't have members/params.
        """
        members = self.getMemberElems(commandOrStruct)
        if not members:
            return []
        ret = []
        for member in members:
            name_tag = member.find('name')
            if name_tag:
                ret.append(name_tag.text)
        return ret

    def getEntityJson(self):
        """Dump the internal entity dictionary to JSON for debugging."""
        import json
        d = {entity: _entityToDict(data)
             for entity, data in self._byEntity.items()}
        return json.dumps(d, sort_keys=True, indent=4)

    def entityHasValidity(self, entity):
        """Estimate if we expect to see a validity include for an entity name.

        Returns None if the entity name is not known,
        otherwise a boolean: True if a validity include is expected.

        Related to Generator.isStructAlwaysValid.
        """
        data = self.findEntity(entity)
        if not data:
            return None

        if entity in self.entities_without_validity:
            return False

        if data.category == 'protos':
            # All protos have validity
            return True

        if data.category not in CATEGORIES_WITH_VALIDITY:
            return False

        # Handle structs here.
        members = self.getMemberElems(entity)
        if not members:
            return None
        for member in members:
            member_name = getElemName(member)
            member_type = member.find('type').text
            member_category = member.get('category')

            if member_name in ('next', 'type'):
                return True

            if member_type in ('void', 'char'):
                return True

            if member.get('noautovalidity'):
                # Not generating validity for this member, skip it
                continue

            if member.get('len'):
                # Array
                return True

            typetail = member.find('type').tail
            if typetail and '*' in typetail:
                # Pointer
                return True

            if member_category in ('handle', 'enum', 'bitmask'):
                return True

            if member.get('category') in ('struct', 'union') \
                    and self.entityHasValidity(member_type):
                # struct or union member - recurse
                return True

        # Got this far - no validity needed
        return False

    def entityGenerates(self, entity_name):
        """Return True if the named entity generates include file(s)."""
        return entity_name in self._generating_entities

    @property
    def generating_entities(self):
        """Return a sequence of all generating entity names."""
        return self._generating_entities.keys()

    def shouldBeRecognized(self, macro, entity_name):
        """Determine, based on the macro and the name provided, if we should expect to recognize the entity.

        True if it is linked. Specific APIs may also provide additional cases where it is True."""
        return self.isLinkedMacro(macro)

    def likelyRecognizedEntity(self, entity_name):
        """Guess (based on name prefix alone) if an entity is likely to be recognized."""
        return entity_name.lower().startswith(self.name_prefix)

    def isLinkedMacro(self, macro):
        """Identify if a macro is considered a "linked" macro."""
        return macro in self._linkedMacros

    def isValidMacro(self, macro):
        """Identify if a macro is known and valid."""
        if macro not in self._categoriesByMacro:
            return False

        return macro not in NON_EXISTENT_MACROS

    def getCategoriesForMacro(self, macro):
        """Identify the categories associated with a (known, valid) macro."""
        if macro in self._categoriesByMacro:
            return self._categoriesByMacro[macro]
        return None

    def areAliases(self, first_entity_name, second_entity_name):
        """Return true if the two entity names are equivalent (aliases of each other)."""
        alias_set = self._aliasSetsByEntity.get(first_entity_name)
        if not alias_set:
            # If this assert fails, we have goofed in addAlias
            assert(second_entity_name not in self._aliasSetsByEntity)

            return False

        return second_entity_name in alias_set

    @property
    def macros(self):
        """Return the collection of all known entity-related markup macros."""
        return self._categoriesByMacro.keys()

    ###
    # Methods only used during initial setup/population of this data structure
    ###
    def addMacro(self, macro, categories, link=False):
        """Add a single markup macro to the collection of categories by macro.

        Also adds the macro to the set of linked macros if link=True.

        If a macro has already been supplied to a call, later calls for that macro have no effect.
        """
        if macro in self._categoriesByMacro:
            return
        self._categoriesByMacro[macro] = categories
        if link:
            self._linkedMacros.add(macro)

    def addMacros(self, letter, macroTypes, categories):
        """Add markup macros associated with a leading letter to the collection of categories by macro.

        Also, those macros created using 'link' in macroTypes will also be added to the set of linked macros.

        Basically automates a number of calls to addMacro().
        """
        for macroType in macroTypes:
            macro = letter + macroType
            self.addMacro(macro, categories, link=(macroType == 'link'))

    def addAlias(self, entityName, aliasName):
        """Record that entityName is an alias for aliasName."""
        # See if we already have something with this as the alias.
        alias_set = self._aliasSetsByEntity.get(aliasName)
        other_alias_set = self._aliasSetsByEntity.get(entityName)
        if alias_set and other_alias_set:
            # If this fails, we need to merge sets and update.
            assert(alias_set is other_alias_set)

        if not alias_set:
            # Try looking by the other name.
            alias_set = other_alias_set

        if not alias_set:
            # Nope, this is a new set.
            alias_set = set()
            self._aliasSets.append(alias_set)

        # Add both names to the set
        alias_set.add(entityName)
        alias_set.add(aliasName)

        # Associate the set with each name
        self._aliasSetsByEntity[aliasName] = alias_set
        self._aliasSetsByEntity[entityName] = alias_set

    def addEntity(self, entityName, macro, category=None, elem=None,
                  generates=None, directory=None, filename=None):
        """Add an entity (command, structure type, enum, enum value, etc) in the database.

        If an entityName has already been supplied to a call, later calls for that entityName have no effect.

        Arguments:
        entityName -- the name of the entity.
        macro -- the macro (without the trailing colon) that should be used to refer to this entity.

        Optional keyword arguments:
        category -- If not manually specified, looked up based on the macro.
        elem -- The ETree element associated with the entity in the registry XML.
        generates -- Indicates whether this entity generates api and validity include files.
                     Default depends on directory (or if not specified, category).
        directory -- The directory that include files (under api/ and validity/) are generated in.
                     If not specified (and generates is True), the default is the same as the category,
                     which is almost always correct.
        filename -- The relative filename (under api/ or validity/) where includes are generated for this.
                    This only matters if generates is True (default). If not specified and generates is True,
                    one will be generated based on directory and entityName.
        """
        # Probably dealt with in handleType(), but just in case it wasn't.
        if elem is not None:
            alias = elem.get('alias')
            if alias:
                self.addAlias(entityName, alias)

        if entityName in self._byEntity:
            # skip if already recorded.
            return

        # Look up category based on the macro, if category isn't specified.
        if category is None:
            category = self._categoriesByMacro.get(macro)[0]

        if generates is None:
            potential_dir = directory or category
            generates = potential_dir in self._generated_dirs

        # If directory isn't specified and this entity generates,
        # the directory is the same as the category.
        if directory is None and generates:
            directory = category

        # Don't generate a filename if this entity doesn't generate includes.
        if filename is None and generates:
            filename = '{}/{}.txt'.format(directory, entityName)

        data = EntityData(
            entity=entityName,
            macro=macro,
            elem=elem,
            filename=filename,
            category=category,
            directory=directory
        )
        if entityName.lower() not in self._byLowercaseEntity:
            self._byLowercaseEntity[entityName.lower()] = []

        self._byEntity[entityName] = data
        self._byLowercaseEntity[entityName.lower()].append(data)
        self._byMacroAndEntity[(macro, entityName)] = data
        if generates and filename is not None:
            self._generating_entities[entityName] = data

    def __init__(self):
        """Constructor: Do not extend or override.

        Changing the behavior of other parts of this logic should be done by
        implementing, extending, or overriding (as documented):

        - Implement makeRegistry()
        - Implement getNamePrefix()
        - Implement getPlatformRequires()
        - Override getSystemTypes()
        - Override populateMacros()
        - Override populateEntities()
        - Extend handleType()
        - Extend handleCommand()
        - Extend handleExtension()
        - Extend handleEnumValue()
        """
        # Internal data that we don't want consumers of the class touching for fear of
        # breaking invariants
        self._byEntity = {}
        self._byLowercaseEntity = {}
        self._byMacroAndEntity = {}
        self._categoriesByMacro = {}
        self._linkedMacros = set()
        self._aliasSetsByEntity = {}
        self._aliasSets = []

        self._registry = None

        # Retrieve from subclass, if overridden, then store locally.
        self._supportExclusionSet = set(self.getExclusionSet())

        # Entities that get a generated/api/category/entity.txt file.
        self._generating_entities = {}

        # Name prefix members
        self.name_prefix = self.getNamePrefix().lower()
        self.mixed_case_name_prefix = self.name_prefix[:1].upper(
        ) + self.name_prefix[1:]
        # Regex string for the name prefix that is case-insensitive.
        self.case_insensitive_name_prefix_pattern = ''.join(
            ('[{}{}]'.format(c.upper(), c) for c in self.name_prefix))

        self.platform_requires = self.getPlatformRequires()

        self._generated_dirs = set(self.getGeneratedDirs())

        # Note: Default impl requires self.mixed_case_name_prefix
        self.entities_without_validity = set(self.getEntitiesWithoutValidity())

        # TODO: Where should flags actually go? Not mentioned in the style guide.
        # TODO: What about flag wildcards? There are a few such uses...

        # Abstract method: subclass must implement to define macros for flags
        self.populateMacros()

        # Now, do default macro population
        self._basicPopulateMacros()

        # Abstract method: subclass must implement to add any "not from the registry" (and not system type)
        # entities
        self.populateEntities()

        # Now, do default entity population
        self._basicPopulateEntities(self.registry)

    ###
    # Methods only used internally during initial setup/population of this data structure
    ###
    @property
    def registry(self):
        """Return a Registry."""
        if not self._registry:
            self._registry = self.makeRegistry()
        return self._registry

    def _basicPopulateMacros(self):
        """Contains calls to self.addMacro() and self.addMacros().

        If you need to change any of these, do so in your override of populateMacros(),
        which will be called first.
        """
        self.addMacro('basetype', ['basetypes'])
        self.addMacro('code', ['code'])
        self.addMacros('f', ['link', 'name', 'text'], ['protos'])
        self.addMacros('s', ['link', 'name', 'text'], ['structs', 'handles'])
        self.addMacros('e', ['link', 'name', 'text'], ['enums'])
        self.addMacros('p', ['name', 'text'], ['parameter', 'member'])
        self.addMacros('t', ['link', 'name'], ['funcpointers'])
        self.addMacros('d', ['link', 'name'], ['defines', 'configdefines'])

        for macro in NON_EXISTENT_MACROS:
            # Still search for them
            self.addMacro(macro, None)

    def _basicPopulateEntities(self, registry):
        """Contains typical calls to self.addEntity().

        If you need to change any of these, do so in your override of populateEntities(),
        which will be called first.
        """
        system_types = set(self.getSystemTypes())
        for t in system_types:
            self.addEntity(t, 'code', generates=False)

        for name, info in registry.typedict.items():
            if name in system_types:
                # We already added these.
                continue

            requires = info.elem.get('requires')

            if requires and not requires.lower().startswith(self.name_prefix):
                # This is an externally-defined type, will skip it.
                continue

            # OK, we might actually add an entity here
            self.handleType(name=name, info=info, requires=requires)

        for name, info in registry.enumdict.items():
            self.handleEnumValue(name, info)

        for name, info in registry.cmddict.items():
            self.handleCommand(name, info)

        for name, info in registry.extdict.items():
            self.handleExtension(name, info)
