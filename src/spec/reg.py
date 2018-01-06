#!/usr/bin/python3 -i
#
# Copyright (c) 2013-2018 The Khronos Group Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io,os,re,string,sys,copy
import xml.etree.ElementTree as etree
from collections import defaultdict

# matchAPIProfile - returns whether an API and profile
#   being generated matches an element's profile
# api - string naming the API to match
# profile - string naming the profile to match
# elem - Element which (may) have 'api' and 'profile'
#   attributes to match to.
# If a tag is not present in the Element, the corresponding API
#   or profile always matches.
# Otherwise, the tag must exactly match the API or profile.
# Thus, if 'profile' = core:
#   <remove> with no attribute will match
#   <remove profile='core'> will match
#   <remove profile='compatibility'> will not match
# Possible match conditions:
#   Requested   Element
#   Profile     Profile
#   ---------   --------
#   None        None        Always matches
#   'string'    None        Always matches
#   None        'string'    Does not match. Can't generate multiple APIs
#                           or profiles, so if an API/profile constraint
#                           is present, it must be asked for explicitly.
#   'string'    'string'    Strings must match
#
#   ** In the future, we will allow regexes for the attributes,
#   not just strings, so that api="^(gl|gles2)" will match. Even
#   this isn't really quite enough, we might prefer something
#   like "gl(core)|gles1(common-lite)".
def matchAPIProfile(api, profile, elem):
    """Match a requested API & profile name to a api & profile attributes of an Element"""
    match = True
    # Match 'api', if present
    if ('api' in elem.attrib):
        if (api == None):
            raise UserWarning("No API requested, but 'api' attribute is present with value '" +
                              elem.get('api') + "'")
        elif (api != elem.get('api')):
            # Requested API doesn't match attribute
            return False
    if ('profile' in elem.attrib):
        if (profile == None):
            raise UserWarning("No profile requested, but 'profile' attribute is present with value '" +
                elem.get('profile') + "'")
        elif (profile != elem.get('profile')):
            # Requested profile doesn't match attribute
            return False
    return True

# BaseInfo - base class for information about a registry feature
# (type/group/enum/command/API/extension).
#   required - should this feature be defined during header generation
#     (has it been removed by a profile or version)?
#   declared - has this feature been defined already?
#   elem - etree Element for this feature
#   resetState() - reset required/declared to initial values. Used
#     prior to generating a new API interface.
class BaseInfo:
    """Represents the state of a registry feature, used during API generation"""
    def __init__(self, elem):
        self.required = False
        self.declared = False
        self.elem = elem
    def resetState(self):
        self.required = False
        self.declared = False

# TypeInfo - registry information about a type. No additional state
#   beyond BaseInfo is required.
class TypeInfo(BaseInfo):
    """Represents the state of a registry type"""
    def __init__(self, elem):
        BaseInfo.__init__(self, elem)
        self.additionalValidity = []
        self.removedValidity = []
    def resetState(self):
        BaseInfo.resetState(self)
        self.additionalValidity = []
        self.removedValidity = []

# GroupInfo - registry information about a group of related enums
# in an <enums> block, generally corresponding to a C "enum" type.
class GroupInfo(BaseInfo):
    """Represents the state of a registry <enums> group"""
    def __init__(self, elem):
        BaseInfo.__init__(self, elem)

# EnumInfo - registry information about an enum
#   type - numeric type of the value of the <enum> tag
#     ( '' for GLint, 'u' for GLuint, 'ull' for GLuint64 )
class EnumInfo(BaseInfo):
    """Represents the state of a registry enum"""
    def __init__(self, elem):
        BaseInfo.__init__(self, elem)
        self.type = elem.get('type')
        if (self.type == None):
            self.type = ''

# CmdInfo - registry information about a command
class CmdInfo(BaseInfo):
    """Represents the state of a registry command"""
    def __init__(self, elem):
        BaseInfo.__init__(self, elem)
        self.additionalValidity = []
        self.removedValidity = []
    def resetState(self):
        BaseInfo.resetState(self)
        self.additionalValidity = []
        self.removedValidity = []

# FeatureInfo - registry information about an API <feature>
# or <extension>
#   name - feature name string (e.g. 'VK_KHR_surface')
#   version - feature version number (e.g. 1.2). <extension>
#     features are unversioned and assigned version number 0.
#     ** This is confusingly taken from the 'number' attribute of <feature>.
#        Needs fixing.
#   number - extension number, used for ordering and for
#     assigning enumerant offsets. <feature> features do
#     not have extension numbers and are assigned number 0.
#   category - category, e.g. VERSION or khr/vendor tag
#   emit - has this feature been defined already?
class FeatureInfo(BaseInfo):
    """Represents the state of an API feature (version/extension)"""
    def __init__(self, elem):
        BaseInfo.__init__(self, elem)
        self.name = elem.get('name')
        # Determine element category (vendor). Only works
        # for <extension> elements.
        if (elem.tag == 'feature'):
            self.category = 'VERSION'
            self.version = elem.get('number')
            self.number = "0"
            self.supported = None
        else:
            self.category = self.name.split('_', 2)[1]
            self.version = "0"
            self.number = elem.get('number')
            self.supported = elem.get('supported')
        self.emit = False

from generator import write, GeneratorOptions, OutputGenerator

# Registry - object representing an API registry, loaded from an XML file
# Members
#   tree - ElementTree containing the root <registry>
#   typedict - dictionary of TypeInfo objects keyed by type name
#   groupdict - dictionary of GroupInfo objects keyed by group name
#   enumdict - dictionary of EnumInfo objects keyed by enum name
#   cmddict - dictionary of CmdInfo objects keyed by command name
#   apidict - dictionary of <api> Elements keyed by API name
#   extensions - list of <extension> Elements
#   extdict - dictionary of <extension> Elements keyed by extension name
#   gen - OutputGenerator object used to write headers / messages
#   genOpts - GeneratorOptions object used to control which
#     fetures to write and how to format them
#   emitFeatures - True to actually emit features for a version / extension,
#     or False to just treat them as emitted
# Public methods
#   loadElementTree(etree) - load registry from specified ElementTree
#   loadFile(filename) - load registry from XML file
#   setGenerator(gen) - OutputGenerator to use
#   parseTree() - parse the registry once loaded & create dictionaries
#   dumpReg(maxlen, filehandle) - diagnostic to dump the dictionaries
#     to specified file handle (default stdout). Truncates type /
#     enum / command elements to maxlen characters (default 80)
#   generator(g) - specify the output generator object
#   apiGen(apiname, genOpts) - generate API headers for the API type
#     and profile specified in genOpts, but only for the versions and
#     extensions specified there.
#   apiReset() - call between calls to apiGen() to reset internal state
# Private methods
#   addElementInfo(elem,info,infoName,dictionary) - add feature info to dict
#   lookupElementInfo(fname,dictionary) - lookup feature info in dict
class Registry:
    """Represents an API registry loaded from XML"""
    def __init__(self):
        self.tree         = None
        self.typedict     = {}
        self.groupdict    = {}
        self.enumdict     = {}
        self.cmddict      = {}
        self.apidict      = {}
        self.extensions   = []
        self.requiredextensions = [] # Hack - can remove it after validity generator goes away
        self.validextensionstructs = defaultdict(list)
        self.extdict      = {}
        # A default output generator, so commands prior to apiGen can report
        # errors via the generator object.
        self.gen          = OutputGenerator()
        self.genOpts      = None
        self.emitFeatures = False
    def loadElementTree(self, tree):
        """Load ElementTree into a Registry object and parse it"""
        self.tree = tree
        self.parseTree()
    def loadFile(self, file):
        """Load an API registry XML file into a Registry object and parse it"""
        self.tree = etree.parse(file)
        self.parseTree()
    def setGenerator(self, gen):
        """Specify output generator object. None restores the default generator"""
        self.gen = gen
        self.gen.setRegistry(self)

    # addElementInfo - add information about an element to the
    # corresponding dictionary
    #   elem - <type>/<enums>/<enum>/<command>/<feature>/<extension> Element
    #   info - corresponding {Type|Group|Enum|Cmd|Feature}Info object
    #   infoName - 'type' / 'group' / 'enum' / 'command' / 'feature' / 'extension'
    #   dictionary - self.{type|group|enum|cmd|api|ext}dict
    # If the Element has an 'api' attribute, the dictionary key is the
    # tuple (name,api). If not, the key is the name. 'name' is an
    # attribute of the Element
    def addElementInfo(self, elem, info, infoName, dictionary):
        if ('api' in elem.attrib):
            key = (elem.get('name'),elem.get('api'))
        else:
            key = elem.get('name')
        if key in dictionary:
            self.gen.logMsg('warn', '*** Attempt to redefine',
                            infoName, 'with key:', key)
        else:
            dictionary[key] = info
    #
    # lookupElementInfo - find a {Type|Enum|Cmd}Info object by name.
    # If an object qualified by API name exists, use that.
    #   fname - name of type / enum / command
    #   dictionary - self.{type|enum|cmd}dict
    def lookupElementInfo(self, fname, dictionary):
        key = (fname, self.genOpts.apiname)
        if (key in dictionary):
            # self.gen.logMsg('diag', 'Found API-specific element for feature', fname)
            return dictionary[key]
        elif (fname in dictionary):
            # self.gen.logMsg('diag', 'Found generic element for feature', fname)
            return dictionary[fname]
        else:
            return None
    def parseTree(self):
        """Parse the registry Element, once created"""
        # This must be the Element for the root <registry>
        self.reg = self.tree.getroot()
        #
        # Create dictionary of registry types from toplevel <types> tags
        # and add 'name' attribute to each <type> tag (where missing)
        # based on its <name> element.
        #
        # There's usually one <types> block; more are OK
        # Required <type> attributes: 'name' or nested <name> tag contents
        self.typedict = {}
        for type in self.reg.findall('types/type'):
            # If the <type> doesn't already have a 'name' attribute, set
            # it from contents of its <name> tag.
            if (type.get('name') == None):
                type.attrib['name'] = type.find('name').text
            self.addElementInfo(type, TypeInfo(type), 'type', self.typedict)
        #
        # Create dictionary of registry enum groups from <enums> tags.
        #
        # Required <enums> attributes: 'name'. If no name is given, one is
        # generated, but that group can't be identified and turned into an
        # enum type definition - it's just a container for <enum> tags.
        self.groupdict = {}
        for group in self.reg.findall('enums'):
            self.addElementInfo(group, GroupInfo(group), 'group', self.groupdict)
        #
        # Create dictionary of registry enums from <enum> tags
        #
        # <enums> tags usually define different namespaces for the values
        #   defined in those tags, but the actual names all share the
        #   same dictionary.
        # Required <enum> attributes: 'name', 'value'
        # For containing <enums> which have type="enum" or type="bitmask",
        # tag all contained <enum>s are required. This is a stopgap until
        # a better scheme for tagging core and extension enums is created.
        self.enumdict = {}
        for enums in self.reg.findall('enums'):
            required = (enums.get('type') != None)
            for enum in enums.findall('enum'):
                enumInfo = EnumInfo(enum)
                enumInfo.required = required
                self.addElementInfo(enum, enumInfo, 'enum', self.enumdict)
        #
        # Create dictionary of registry commands from <command> tags
        # and add 'name' attribute to each <command> tag (where missing)
        # based on its <proto><name> element.
        #
        # There's usually only one <commands> block; more are OK.
        # Required <command> attributes: 'name' or <proto><name> tag contents
        self.cmddict = {}
        for cmd in self.reg.findall('commands/command'):
            # If the <command> doesn't already have a 'name' attribute, set
            # it from contents of its <proto><name> tag.
            if (cmd.get('name') == None):
                cmd.attrib['name'] = cmd.find('proto/name').text
            ci = CmdInfo(cmd)
            self.addElementInfo(cmd, ci, 'command', self.cmddict)
        #
        # Create dictionaries of API and extension interfaces
        #   from toplevel <api> and <extension> tags.
        #
        self.apidict = {}
        for feature in self.reg.findall('feature'):
            featureInfo = FeatureInfo(feature)
            self.addElementInfo(feature, featureInfo, 'feature', self.apidict)
        self.extensions = self.reg.findall('extensions/extension')
        self.extdict = {}
        for feature in self.extensions:
            featureInfo = FeatureInfo(feature)
            self.addElementInfo(feature, featureInfo, 'extension', self.extdict)

            # Add additional enums defined only in <extension> tags
            # to the corresponding core type.
            # When seen here, the <enum> element, processed to contain the
            # numeric enum value, is added to the corresponding <enums>
            # element, as well as adding to the enum dictionary. It is
            # *removed* from the <require> element it is introduced in.
            # Not doing this will cause spurious genEnum()
            # calls to be made in output generation, and it's easier
            # to handle here than in genEnum().
            #
            # In lxml.etree, an Element can have only one parent, so the
            # append() operation also removes the element. But in Python's
            # ElementTree package, an Element can have multiple parents. So
            # it must be explicitly removed from the <require> tag, leading
            # to the nested loop traversal of <require>/<enum> elements
            # below.
            #
            # This code also adds a 'extnumber' attribute containing the
            # extension number, used for enumerant value calculation.
            #
            # For <enum> tags which are actually just constants, if there's
            # no 'extends' tag but there is a 'value' or 'bitpos' tag, just
            # add an EnumInfo record to the dictionary. That works because
            # output generation of constants is purely dependency-based, and
            # doesn't need to iterate through the XML tags.
            #
            # Something like this will need to be done for 'feature's up
            # above, if we use the same mechanism for adding to the core
            # API in 1.1.
            #
            for elem in feature.findall('require'):
              for enum in elem.findall('enum'):
                addEnumInfo = False
                groupName = enum.get('extends')
                if (groupName != None):
                    # self.gen.logMsg('diag', '*** Found extension enum',
                    #     enum.get('name'))
                    # Add extension number attribute to the <enum> element
                    enum.attrib['extnumber'] = featureInfo.number
                    enum.attrib['extname'] = featureInfo.name
                    enum.attrib['supported'] = featureInfo.supported
                    # Look up the GroupInfo with matching groupName
                    if (groupName in self.groupdict.keys()):
                        # self.gen.logMsg('diag', '*** Matching group',
                        #     groupName, 'found, adding element...')
                        gi = self.groupdict[groupName]
                        gi.elem.append(enum)
                        # Remove element from parent <require> tag
                        # This should be a no-op in lxml.etree
                        elem.remove(enum)
                    else:
                        self.gen.logMsg('warn', '*** NO matching group',
                            groupName, 'for enum', enum.get('name'), 'found.')
                    addEnumInfo = True
                elif (enum.get('value') or enum.get('bitpos')):
                    # self.gen.logMsg('diag', '*** Adding extension constant "enum"',
                    #     enum.get('name'))
                    addEnumInfo = True
                if (addEnumInfo):
                    enumInfo = EnumInfo(enum)
                    self.addElementInfo(enum, enumInfo, 'enum', self.enumdict)
        # Construct a "validextensionstructs" list for parent structures
        # based on "structextends" tags in child structures
        for type in self.reg.findall('types/type'):
            parentStructs = type.get('structextends')
            if (parentStructs != None):
                for parent in parentStructs.split(','):
                    # self.gen.logMsg('diag', type.get('name'), 'extends', parent)
                    self.validextensionstructs[parent].append(type.get('name'))
        # Sort the lists so they don't depend on the XML order
        for parent in self.validextensionstructs:
            self.validextensionstructs[parent].sort()

    def dumpReg(self, maxlen = 40, filehandle = sys.stdout):
        """Dump all the dictionaries constructed from the Registry object"""
        write('***************************************', file=filehandle)
        write('    ** Dumping Registry contents **',     file=filehandle)
        write('***************************************', file=filehandle)
        write('// Types', file=filehandle)
        for name in self.typedict:
            tobj = self.typedict[name]
            write('    Type', name, '->', etree.tostring(tobj.elem)[0:maxlen], file=filehandle)
        write('// Groups', file=filehandle)
        for name in self.groupdict:
            gobj = self.groupdict[name]
            write('    Group', name, '->', etree.tostring(gobj.elem)[0:maxlen], file=filehandle)
        write('// Enums', file=filehandle)
        for name in self.enumdict:
            eobj = self.enumdict[name]
            write('    Enum', name, '->', etree.tostring(eobj.elem)[0:maxlen], file=filehandle)
        write('// Commands', file=filehandle)
        for name in self.cmddict:
            cobj = self.cmddict[name]
            write('    Command', name, '->', etree.tostring(cobj.elem)[0:maxlen], file=filehandle)
        write('// APIs', file=filehandle)
        for key in self.apidict:
            write('    API Version ', key, '->',
                etree.tostring(self.apidict[key].elem)[0:maxlen], file=filehandle)
        write('// Extensions', file=filehandle)
        for key in self.extdict:
            write('    Extension', key, '->',
                etree.tostring(self.extdict[key].elem)[0:maxlen], file=filehandle)
        # write('***************************************', file=filehandle)
        # write('    ** Dumping XML ElementTree **', file=filehandle)
        # write('***************************************', file=filehandle)
        # write(etree.tostring(self.tree.getroot(),pretty_print=True), file=filehandle)
    #
    # typename - name of type
    # required - boolean (to tag features as required or not)
    def markTypeRequired(self, typename, required):
        """Require (along with its dependencies) or remove (but not its dependencies) a type"""
        self.gen.logMsg('diag', '*** tagging type:', typename, '-> required =', required)
        # Get TypeInfo object for <type> tag corresponding to typename
        type = self.lookupElementInfo(typename, self.typedict)
        if (type != None):
            if (required):
                # Tag type dependencies in 'required' attributes as
                # required. This DOES NOT un-tag dependencies in a <remove>
                # tag. See comments in markRequired() below for the reason.
                if ('requires' in type.elem.attrib):
                    depType = type.elem.get('requires')
                    self.gen.logMsg('diag', '*** Generating dependent type',
                        depType, 'for type', typename)
                    self.markTypeRequired(depType, required)
                # Tag types used in defining this type (e.g. in nested
                # <type> tags)
                # Look for <type> in entire <command> tree,
                # not just immediate children
                for subtype in type.elem.findall('.//type'):
                    self.gen.logMsg('diag', '*** markRequired: type requires dependent <type>', subtype.text)
                    self.markTypeRequired(subtype.text, required)
                # Tag enums used in defining this type, for example in
                #   <member><name>member</name>[<enum>MEMBER_SIZE</enum>]</member>
                for subenum in type.elem.findall('.//enum'):
                    self.gen.logMsg('diag', '*** markRequired: type requires dependent <enum>', subenum.text)
                    self.markEnumRequired(subenum.text, required)
            type.required = required
        else:
            self.gen.logMsg('warn', '*** type:', typename , 'IS NOT DEFINED')
    #
    # enumname - name of enum
    # required - boolean (to tag features as required or not)
    def markEnumRequired(self, enumname, required):
        self.gen.logMsg('diag', '*** tagging enum:', enumname, '-> required =', required)
        enum = self.lookupElementInfo(enumname, self.enumdict)
        if (enum != None):
            enum.required = required
        else:
            self.gen.logMsg('warn', '*** enum:', enumname , 'IS NOT DEFINED')
    #
    # features - Element for <require> or <remove> tag
    # required - boolean (to tag features as required or not)
    def markRequired(self, features, required):
        """Require or remove features specified in the Element"""
        self.gen.logMsg('diag', '*** markRequired (features = <too long to print>, required =', required, ')')
        # Loop over types, enums, and commands in the tag
        # @@ It would be possible to respect 'api' and 'profile' attributes
        #  in individual features, but that's not done yet.
        for typeElem in features.findall('type'):
            self.markTypeRequired(typeElem.get('name'), required)
        for enumElem in features.findall('enum'):
            self.markEnumRequired(enumElem.get('name'), required)
        for cmdElem in features.findall('command'):
            name = cmdElem.get('name')
            self.gen.logMsg('diag', '*** tagging command:', name, '-> required =', required)
            cmd = self.lookupElementInfo(name, self.cmddict)
            if (cmd != None):
                cmd.required = required
                # Tag all parameter types of this command as required.
                # This DOES NOT remove types of commands in a <remove>
                # tag, because many other commands may use the same type.
                # We could be more clever and reference count types,
                # instead of using a boolean.
                if (required):
                    # Look for <type> in entire <command> tree,
                    # not just immediate children
                    for type in cmd.elem.findall('.//type'):
                        self.gen.logMsg('diag', '*** markRequired: command implicitly requires dependent type', type.text)
                        self.markTypeRequired(type.text, required)
            else:
                self.gen.logMsg('warn', '*** command:', name, 'IS NOT DEFINED')
    #
    # interface - Element for <version> or <extension>, containing
    #   <require> and <remove> tags
    # api - string specifying API name being generated
    # profile - string specifying API profile being generated
    def requireAndRemoveFeatures(self, interface, api, profile):
        """Process <recquire> and <remove> tags for a <version> or <extension>"""
        # <require> marks things that are required by this version/profile
        for feature in interface.findall('require'):
            if (matchAPIProfile(api, profile, feature)):
                self.markRequired(feature,True)
        # <remove> marks things that are removed by this version/profile
        for feature in interface.findall('remove'):
            if (matchAPIProfile(api, profile, feature)):
                self.markRequired(feature,False)

    def assignAdditionalValidity(self, interface, api, profile):
        #
        # Loop over all usage inside all <require> tags.
        for feature in interface.findall('require'):
            if (matchAPIProfile(api, profile, feature)):
                for v in feature.findall('usage'):
                    if v.get('command'):
                        self.cmddict[v.get('command')].additionalValidity.append(copy.deepcopy(v))
                    if v.get('struct'):
                        self.typedict[v.get('struct')].additionalValidity.append(copy.deepcopy(v))

        #
        # Loop over all usage inside all <remove> tags.
        for feature in interface.findall('remove'):
            if (matchAPIProfile(api, profile, feature)):
                for v in feature.findall('usage'):
                    if v.get('command'):
                        self.cmddict[v.get('command')].removedValidity.append(copy.deepcopy(v))
                    if v.get('struct'):
                        self.typedict[v.get('struct')].removedValidity.append(copy.deepcopy(v))

    #
    # generateFeature - generate a single type / enum group / enum / command,
    # and all its dependencies as needed.
    #   fname - name of feature (<type>/<enum>/<command>)
    #   ftype - type of feature, 'type' | 'enum' | 'command'
    #   dictionary - of *Info objects - self.{type|enum|cmd}dict
    def generateFeature(self, fname, ftype, dictionary):
        f = self.lookupElementInfo(fname, dictionary)
        if (f == None):
            # No such feature. This is an error, but reported earlier
            self.gen.logMsg('diag', '*** No entry found for feature', fname,
                            'returning!')
            return
        #
        # If feature isn't required, or has already been declared, return
        if (not f.required):
            self.gen.logMsg('diag', '*** Skipping', ftype, fname, '(not required)')
            return
        if (f.declared):
            self.gen.logMsg('diag', '*** Skipping', ftype, fname, '(already declared)')
            return
        # Always mark feature declared, as though actually emitted
        f.declared = True
        #
        # Pull in dependent declaration(s) of the feature.
        # For types, there may be one type in the 'required' attribute of
        #   the element, as well as many in imbedded <type> and <enum> tags
        #   within the element.
        # For commands, there may be many in <type> tags within the element.
        # For enums, no dependencies are allowed (though perhaps if you
        #   have a uint64 enum, it should require that type).
        genProc = None
        if (ftype == 'type'):
            genProc = self.gen.genType
            if ('requires' in f.elem.attrib):
                depname = f.elem.get('requires')
                self.gen.logMsg('diag', '*** Generating required dependent type',
                                depname)
                self.generateFeature(depname, 'type', self.typedict)
            for subtype in f.elem.findall('.//type'):
                self.gen.logMsg('diag', '*** Generating required dependent <type>',
                    subtype.text)
                self.generateFeature(subtype.text, 'type', self.typedict)
            for subtype in f.elem.findall('.//enum'):
                self.gen.logMsg('diag', '*** Generating required dependent <enum>',
                    subtype.text)
                self.generateFeature(subtype.text, 'enum', self.enumdict)
            # If the type is an enum group, look up the corresponding
            # group in the group dictionary and generate that instead.
            if (f.elem.get('category') == 'enum'):
                self.gen.logMsg('diag', '*** Type', fname, 'is an enum group, so generate that instead')
                group = self.lookupElementInfo(fname, self.groupdict)
                if (group == None):
                    # Unless this is tested for, it's probably fatal to call below
                    genProc = None
                    self.logMsg('warn', '*** NO MATCHING ENUM GROUP FOUND!!!')
                else:
                    genProc = self.gen.genGroup
                    f = group
        elif (ftype == 'command'):
            genProc = self.gen.genCmd
            for type in f.elem.findall('.//type'):
                depname = type.text
                self.gen.logMsg('diag', '*** Generating required parameter type',
                                depname)
                self.generateFeature(depname, 'type', self.typedict)
        elif (ftype == 'enum'):
            genProc = self.gen.genEnum
        # Actually generate the type only if emitting declarations
        if self.emitFeatures:
            self.gen.logMsg('diag', '*** Emitting', ftype, 'decl for', fname)
            genProc(f, fname)
        else:
            self.gen.logMsg('diag', '*** Skipping', ftype, fname,
                            '(not emitting this feature)')
    #
    # generateRequiredInterface - generate all interfaces required
    # by an API version or extension
    #   interface - Element for <version> or <extension>
    def generateRequiredInterface(self, interface):
        """Generate required C interface for specified API version/extension"""

        #
        # Loop over all features inside all <require> tags.
        for features in interface.findall('require'):
            for t in features.findall('type'):
                self.generateFeature(t.get('name'), 'type', self.typedict)
            for e in features.findall('enum'):
                self.generateFeature(e.get('name'), 'enum', self.enumdict)
            for c in features.findall('command'):
                self.generateFeature(c.get('name'), 'command', self.cmddict)

    #
    # apiGen(genOpts) - generate interface for specified versions
    #   genOpts - GeneratorOptions object with parameters used
    #   by the Generator object.
    def apiGen(self, genOpts):
        """Generate interfaces for the specified API type and range of versions"""
        #
        self.gen.logMsg('diag', '*******************************************')
        self.gen.logMsg('diag', '  Registry.apiGen file:', genOpts.filename,
                        'api:', genOpts.apiname,
                        'profile:', genOpts.profile)
        self.gen.logMsg('diag', '*******************************************')
        #
        self.genOpts = genOpts
        # Reset required/declared flags for all features
        self.apiReset()
        #
        # Compile regexps used to select versions & extensions
        regVersions = re.compile(self.genOpts.versions)
        regEmitVersions = re.compile(self.genOpts.emitversions)
        regAddExtensions = re.compile(self.genOpts.addExtensions)
        regRemoveExtensions = re.compile(self.genOpts.removeExtensions)
        #
        # Get all matching API versions & add to list of FeatureInfo
        features = []
        apiMatch = False
        for key in self.apidict:
            fi = self.apidict[key]
            api = fi.elem.get('api')
            if (api == self.genOpts.apiname):
                apiMatch = True
                if (regVersions.match(fi.version)):
                    # Matches API & version #s being generated. Mark for
                    # emission and add to the features[] list .
                    # @@ Could use 'declared' instead of 'emit'?
                    fi.emit = (regEmitVersions.match(fi.version) != None)
                    features.append(fi)
                    if (not fi.emit):
                        self.gen.logMsg('diag', '*** NOT tagging feature api =', api,
                            'name =', fi.name, 'version =', fi.version,
                            'for emission (does not match emitversions pattern)')
                else:
                    self.gen.logMsg('diag', '*** NOT including feature api =', api,
                        'name =', fi.name, 'version =', fi.version,
                        '(does not match requested versions)')
            else:
                self.gen.logMsg('diag', '*** NOT including feature api =', api,
                    'name =', fi.name,
                    '(does not match requested API)')
        if (not apiMatch):
            self.gen.logMsg('warn', '*** No matching API versions found!')
        #
        # Get all matching extensions, in order by their extension number,
        # and add to the list of features.
        # Start with extensions tagged with 'api' pattern matching the API
        # being generated. Add extensions matching the pattern specified in
        # regExtensions, then remove extensions matching the pattern
        # specified in regRemoveExtensions
        for (extName,ei) in sorted(self.extdict.items(),key = lambda x : x[1].number):
            extName = ei.name
            include = False
            #
            # Include extension if defaultExtensions is not None and if the
            # 'supported' attribute matches defaultExtensions. The regexp in
            # 'supported' must exactly match defaultExtensions, so bracket
            # it with ^(pat)$.
            pat = '^(' + ei.elem.get('supported') + ')$'
            if (self.genOpts.defaultExtensions and
                     re.match(pat, self.genOpts.defaultExtensions)):
                self.gen.logMsg('diag', '*** Including extension',
                    extName, "(defaultExtensions matches the 'supported' attribute)")
                include = True
            #
            # Include additional extensions if the extension name matches
            # the regexp specified in the generator options. This allows
            # forcing extensions into an interface even if they're not
            # tagged appropriately in the registry.
            if (regAddExtensions.match(extName) != None):
                self.gen.logMsg('diag', '*** Including extension',
                    extName, '(matches explicitly requested extensions to add)')
                include = True
            # Remove extensions if the name matches the regexp specified
            # in generator options. This allows forcing removal of
            # extensions from an interface even if they're tagged that
            # way in the registry.
            if (regRemoveExtensions.match(extName) != None):
                self.gen.logMsg('diag', '*** Removing extension',
                    extName, '(matches explicitly requested extensions to remove)')
                include = False
            #
            # If the extension is to be included, add it to the
            # extension features list.
            if (include):
                ei.emit = True
                features.append(ei)

                # Hack - can be removed when validity generator goes away
                self.requiredextensions.append(extName)
            else:
                self.gen.logMsg('diag', '*** NOT including extension',
                    extName, '(does not match api attribute or explicitly requested extensions)')
        #
        # Sort the extension features list, if a sort procedure is defined
        if (self.genOpts.sortProcedure):
            self.genOpts.sortProcedure(features)
        #
        # Pass 1: loop over requested API versions and extensions tagging
        #   types/commands/features as required (in an <require> block) or no
        #   longer required (in an <remove> block). It is possible to remove
        #   a feature in one version and restore it later by requiring it in
        #   a later version.
        # If a profile other than 'None' is being generated, it must
        #   match the profile attribute (if any) of the <require> and
        #   <remove> tags.
        self.gen.logMsg('diag', '*** PASS 1: TAG FEATURES ********************************************')
        for f in features:
            self.gen.logMsg('diag', '*** PASS 1: Tagging required and removed features for',
                f.name)
            self.requireAndRemoveFeatures(f.elem, self.genOpts.apiname, self.genOpts.profile)
            self.assignAdditionalValidity(f.elem, self.genOpts.apiname, self.genOpts.profile)
        #
        # Pass 2: loop over specified API versions and extensions printing
        #   declarations for required things which haven't already been
        #   generated.
        self.gen.logMsg('diag', '*** PASS 2: GENERATE INTERFACES FOR FEATURES ************************')
        self.gen.beginFile(self.genOpts)
        for f in features:
            self.gen.logMsg('diag', '*** PASS 2: Generating interface for',
                f.name)
            emit = self.emitFeatures = f.emit
            if (not emit):
                self.gen.logMsg('diag', '*** PASS 2: NOT declaring feature',
                    f.elem.get('name'), 'because it is not tagged for emission')
            # Generate the interface (or just tag its elements as having been
            # emitted, if they haven't been).
            self.gen.beginFeature(f.elem, emit)
            self.generateRequiredInterface(f.elem)
            self.gen.endFeature()
        self.gen.endFile()
    #
    # apiReset - use between apiGen() calls to reset internal state
    #
    def apiReset(self):
        """Reset type/enum/command dictionaries before generating another API"""
        for type in self.typedict:
            self.typedict[type].resetState()
        for enum in self.enumdict:
            self.enumdict[enum].resetState()
        for cmd in self.cmddict:
            self.cmddict[cmd].resetState()
        for cmd in self.apidict:
            self.apidict[cmd].resetState()
    #
    # validateGroups - check that group= attributes match actual groups
    #
    def validateGroups(self):
        """Validate group= attributes on <param> and <proto> tags"""
        # Keep track of group names not in <group> tags
        badGroup = {}
        self.gen.logMsg('diag', '*** VALIDATING GROUP ATTRIBUTES ***')
        for cmd in self.reg.findall('commands/command'):
            proto = cmd.find('proto')
            funcname = cmd.find('proto/name').text
            if ('group' in proto.attrib.keys()):
                group = proto.get('group')
                # self.gen.logMsg('diag', '*** Command ', funcname, ' has return group ', group)
                if (group not in self.groupdict.keys()):
                    # self.gen.logMsg('diag', '*** Command ', funcname, ' has UNKNOWN return group ', group)
                    if (group not in badGroup.keys()):
                        badGroup[group] = 1
                    else:
                        badGroup[group] = badGroup[group] +  1
            for param in cmd.findall('param'):
                pname = param.find('name')
                if (pname != None):
                    pname = pname.text
                else:
                    pname = type.get('name')
                if ('group' in param.attrib.keys()):
                    group = param.get('group')
                    if (group not in self.groupdict.keys()):
                        # self.gen.logMsg('diag', '*** Command ', funcname, ' param ', pname, ' has UNKNOWN group ', group)
                        if (group not in badGroup.keys()):
                            badGroup[group] = 1
                        else:
                            badGroup[group] = badGroup[group] +  1
        if (len(badGroup.keys()) > 0):
            self.gen.logMsg('diag', '*** SUMMARY OF UNRECOGNIZED GROUPS ***')
            for key in sorted(badGroup.keys()):
                self.gen.logMsg('diag', '    ', key, ' occurred ', badGroup[key], ' times')
