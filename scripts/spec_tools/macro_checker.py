"""Provides the MacroChecker class."""

# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>

from io import StringIO
import re


class MacroChecker(object):
    """Perform and track checking of one or more files in an API spec.

    This does not necessarily need to be subclassed per-API: it is sufficiently
    parameterized in the constructor for expected usage.
    """

    def __init__(self, enabled_messages, entity_db,
                 macro_checker_file_type, root_path):
        """Construct an object that tracks checking one or more files in an API spec.

        enabled_messages -- a set of MessageId that should be enabled.
        entity_db -- an object of a EntityDatabase subclass for this API.
        macro_checker_file_type -- Type to instantiate to create the right
                                   MacroCheckerFile subclass for this API.
        root_path -- A Path object for the root of this repository.
        """
        self.enabled_messages = enabled_messages
        self.entity_db = entity_db
        self.macro_checker_file_type = macro_checker_file_type
        self.root_path = root_path

        self.files = []

        self.refpages = set()

        # keys: entity names. values: MessageContext
        self.links = {}
        self.apiIncludes = {}
        self.validityIncludes = {}
        self.headings = {}

        # Regexes that are members because they depend on the name prefix.

        # apiPrefix, followed by some word characters or * as many times as desired,
        # NOT followed by >> and NOT preceded by one of the characters in that first character class.
        # (which distinguish "names being used somewhere other than prose").
        self.suspected_missing_macro_re = re.compile(
            r'\b(?<![-=:/[\.`+,])(?P<entity_name>{}[\w*]+)\b(?!>>)'.format(
                self.entity_db.case_insensitive_name_prefix_pattern)
        )
        self.heading_command_re = re.compile(
            r'=+ (?P<command>{}[\w]+)'.format(self.entity_db.name_prefix)
        )

        macros_pattern = '|'.join((re.escape(macro)
                                   for macro in self.entity_db.macros))
        # the "formatting" group is to strip matching */**/_/__
        # surrounding an entire macro.
        self.macro_re = re.compile(
            r'(?P<formatting>\**|_*)(?P<macro>{}):(?P<entity_name>[\w*]+((?P<subscript>[\[][^\]]*[\]]))?)(?P=formatting)'.format(macros_pattern))

    def haveLinkTarget(self, entity):
        """Report if we have parsed an API include (or heading) for an entity.

        None if there is no entity with that name.
        """
        if not self.findEntity(entity):
            return None
        if entity in self.apiIncludes:
            return True
        return entity in self.headings

    def hasFixes(self):
        """Report if any files have auto-fixes."""
        for f in self.files:
            if f.hasFixes():
                return True
        return False

    def addLinkToEntity(self, entity, context):
        """Record seeing a link to an entity's docs from a context."""
        if entity not in self.links:
            self.links[entity] = []
        self.links[entity].append(context)

    def seenRefPage(self, entity):
        """Check if a ref-page markup block has been seen for an entity."""
        return entity in self.refpages

    def addRefPage(self, entity):
        """Record seeing a ref-page markup block for an entity."""
        self.refpages.add(entity)

    def findMacroAndEntity(self, macro, entity):
        """Look up EntityData by macro and entity pair.

        Forwards to the EntityDatabase.
        """
        return self.entity_db.findMacroAndEntity(macro, entity)

    def findEntity(self, entity):
        """Look up EntityData by entity name (case-sensitive).

        Forwards to the EntityDatabase.
        """
        return self.entity_db.findEntity(entity)

    def findEntityCaseInsensitive(self, entity):
        """Look up EntityData by entity name (case-insensitive).

        Forwards to the EntityDatabase.
        """
        return self.entity_db.findEntityCaseInsensitive(entity)

    def getMemberNames(self, commandOrStruct):
        """Given a command or struct name, retrieve the names of each member/param.

        Returns an empty list if the entity is not found or doesn't have members/params.

        Forwards to the EntityDatabase.
        """
        return self.entity_db.getMemberNames(commandOrStruct)

    def likelyRecognizedEntity(self, entity_name):
        """Guess (based on name prefix alone) if an entity is likely to be recognized.

        Forwards to the EntityDatabase.
        """
        return self.entity_db.likelyRecognizedEntity(entity_name)

    def isLinkedMacro(self, macro):
        """Identify if a macro is considered a "linked" macro.

        Forwards to the EntityDatabase.
        """
        return self.entity_db.isLinkedMacro(macro)

    def processFile(self, filename):
        """Parse an .adoc file belonging to the spec and check it for errors."""
        class FileStreamMaker(object):
            def __init__(self, filename):
                self.filename = filename

            def make_stream(self):
                return open(self.filename, 'r', encoding='utf-8')

        f = self.macro_checker_file_type(self, filename, self.enabled_messages,
                                         FileStreamMaker(filename))
        f.process()
        self.files.append(f)

    def processString(self, s):
        """Process a string as if it were a spec file.

        Used for testing purposes.
        """
        if "\n" in s.rstrip():
            # remove leading spaces from each line to allow easier
            # block-quoting in tests
            s = "\n".join((line.lstrip() for line in s.split("\n")))
            # fabricate a "filename" that will display better.
            filename = "string{}\n****START OF STRING****\n{}\n****END OF STRING****\n".format(
                len(self.files), s.rstrip())

        else:
            filename = "string{}: {}".format(
                len(self.files), s.rstrip())

        class StringStreamMaker(object):
            def __init__(self, string):
                self.string = string

            def make_stream(self):
                return StringIO(self.string)

        f = self.macro_checker_file_type(self, filename, self.enabled_messages,
                                         StringStreamMaker(s))
        f.process()
        self.files.append(f)
        return f

    def numDiagnostics(self):
        """Return the total number of diagnostics (warnings and errors) over all the files processed."""
        return sum((f.numDiagnostics() for f in self.files))

    def numErrors(self):
        """Return the total number of errors over all the files processed."""
        return sum((f.numErrors() for f in self.files))

    def getMissingUnreferencedApiIncludes(self):
        """Return the unreferenced entity names that we expected to see an API include or link target for, but did not.

        Counterpart to getBrokenLinks(): This method returns the entity names
        that were not used in a linking macro (and thus wouldn't create a broken link),
        but were nevertheless expected and not seen.
        """
        return (entity for entity in self.entity_db.generating_entities
                if (not self.haveLinkTarget(entity)) and entity not in self.links)

    def getBrokenLinks(self):
        """Return the entity names and usage contexts that we expected to see an API include or link target for, but did not.

        Counterpart to getMissingUnreferencedApiIncludes(): This method returns only the
        entity names that were used in a linking macro (and thus create a broken link),
        but were not seen. The values of the dictionary are a list of MessageContext objects
        for each linking macro usage for this entity name.
        """
        return {entity: contexts for entity, contexts in self.links.items()
                if self.entity_db.entityGenerates(entity) and not self.haveLinkTarget(entity)}

    def getMissingRefPages(self):
        """Return a list of entities that we expected, but did not see, a ref page block for.

        The heuristics here are rather crude: we expect a ref page for every generating entry.
        """
        return (entity for entity in sorted(self.entity_db.generating_entities)
                if entity not in self.refpages)
