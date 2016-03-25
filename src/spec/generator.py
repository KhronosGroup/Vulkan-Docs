#!/usr/bin/python3 -i
#
# Copyright (c) 2013-2016 The Khronos Group Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and/or associated documentation files (the
# "Materials"), to deal in the Materials without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Materials, and to
# permit persons to whom the Materials are furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Materials.
#
# THE MATERIALS ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.

import os,re,sys

def write( *args, **kwargs ):
    file = kwargs.pop('file',sys.stdout)
    end = kwargs.pop( 'end','\n')
    file.write( ' '.join([str(arg) for arg in args]) )
    file.write( end )

# noneStr - returns string argument, or "" if argument is None.
# Used in converting lxml Elements into text.
#   str - string to convert
def noneStr(str):
    if (str):
        return str
    else:
        return ""

# enquote - returns string argument with surrounding quotes,
#   for serialization into Python code.
def enquote(str):
    if (str):
        return "'" + str + "'"
    else:
        return None

# Primary sort key for regSortFeatures.
# Sorts by category of the feature name string:
#   Core API features (those defined with a <feature> tag)
#   ARB/KHR/OES (Khronos extensions)
#   other       (EXT/vendor extensions)
# This will need changing for Vulkan!
def regSortCategoryKey(feature):
    if (feature.elem.tag == 'feature'):
        return 0
    elif (feature.category == 'ARB' or
          feature.category == 'KHR' or
          feature.category == 'OES'):
        return 1
    else:
        return 2

# Secondary sort key for regSortFeatures.
# Sorts by extension name.
def regSortNameKey(feature):
    return feature.name

# Second sort key for regSortFeatures.
# Sorts by feature version. <extension> elements all have version number "0"
def regSortFeatureVersionKey(feature):
    return float(feature.version)

# Tertiary sort key for regSortFeatures.
# Sorts by extension number. <feature> elements all have extension number 0.
def regSortExtensionNumberKey(feature):
    return int(feature.number)

# regSortFeatures - default sort procedure for features.
# Sorts by primary key of feature category ('feature' or 'extension')
#   then by version number (for features)
#   then by extension number (for extensions)
def regSortFeatures(featureList):
    featureList.sort(key = regSortExtensionNumberKey)
    featureList.sort(key = regSortFeatureVersionKey)
    featureList.sort(key = regSortCategoryKey)

# GeneratorOptions - base class for options used during header production
# These options are target language independent, and used by
# Registry.apiGen() and by base OutputGenerator objects.
#
# Members
#   filename - name of file to generate, or None to write to stdout.
#   apiname - string matching <api> 'apiname' attribute, e.g. 'gl'.
#   profile - string specifying API profile , e.g. 'core', or None.
#   versions - regex matching API versions to process interfaces for.
#     Normally '.*' or '[0-9]\.[0-9]' to match all defined versions.
#   emitversions - regex matching API versions to actually emit
#    interfaces for (though all requested versions are considered
#    when deciding which interfaces to generate). For GL 4.3 glext.h,
#     this might be '1\.[2-5]|[2-4]\.[0-9]'.
#   defaultExtensions - If not None, a string which must in its
#     entirety match the pattern in the "supported" attribute of
#     the <extension>. Defaults to None. Usually the same as apiname.
#   addExtensions - regex matching names of additional extensions
#     to include. Defaults to None.
#   removeExtensions - regex matching names of extensions to
#     remove (after defaultExtensions and addExtensions). Defaults
#     to None.
#   sortProcedure - takes a list of FeatureInfo objects and sorts
#     them in place to a preferred order in the generated output.
#     Default is core API versions, ARB/KHR/OES extensions, all
#     other extensions, alphabetically within each group.
# The regex patterns can be None or empty, in which case they match
#   nothing.
class GeneratorOptions:
    """Represents options during header production from an API registry"""
    def __init__(self,
                 filename = None,
                 apiname = None,
                 profile = None,
                 versions = '.*',
                 emitversions = '.*',
                 defaultExtensions = None,
                 addExtensions = None,
                 removeExtensions = None,
                 sortProcedure = regSortFeatures):
        self.filename          = filename
        self.apiname           = apiname
        self.profile           = profile
        self.versions          = self.emptyRegex(versions)
        self.emitversions      = self.emptyRegex(emitversions)
        self.defaultExtensions = defaultExtensions
        self.addExtensions     = self.emptyRegex(addExtensions)
        self.removeExtensions  = self.emptyRegex(removeExtensions)
        self.sortProcedure     = sortProcedure
    #
    # Substitute a regular expression which matches no version
    # or extension names for None or the empty string.
    def emptyRegex(self,pat):
        if (pat == None or pat == ''):
            return '_nomatch_^'
        else:
            return pat

# CGeneratorOptions - subclass of GeneratorOptions.
#
# Adds options used by COutputGenerator objects during C language header
# generation.
#
# Additional members
#   prefixText - list of strings to prefix generated header with
#     (usually a copyright statement + calling convention macros).
#   protectFile - True if multiple inclusion protection should be
#     generated (based on the filename) around the entire header.
#   protectFeature - True if #ifndef..#endif protection should be
#     generated around a feature interface in the header file.
#   genFuncPointers - True if function pointer typedefs should be
#     generated
#   protectProto - If conditional protection should be generated
#     around prototype declarations, set to either '#ifdef'
#     to require opt-in (#ifdef protectProtoStr) or '#ifndef'
#     to require opt-out (#ifndef protectProtoStr). Otherwise
#     set to None.
#   protectProtoStr - #ifdef/#ifndef symbol to use around prototype
#     declarations, if protectProto is set
#   apicall - string to use for the function declaration prefix,
#     such as APICALL on Windows.
#   apientry - string to use for the calling convention macro,
#     in typedefs, such as APIENTRY.
#   apientryp - string to use for the calling convention macro
#     in function pointer typedefs, such as APIENTRYP.
#   indentFuncProto - True if prototype declarations should put each
#     parameter on a separate line
#   indentFuncPointer - True if typedefed function pointers should put each
#     parameter on a separate line
#   alignFuncParam - if nonzero and parameters are being put on a
#     separate line, align parameter names at the specified column
class CGeneratorOptions(GeneratorOptions):
    """Represents options during C interface generation for headers"""
    def __init__(self,
                 filename = None,
                 apiname = None,
                 profile = None,
                 versions = '.*',
                 emitversions = '.*',
                 defaultExtensions = None,
                 addExtensions = None,
                 removeExtensions = None,
                 sortProcedure = regSortFeatures,
                 prefixText = "",
                 genFuncPointers = True,
                 protectFile = True,
                 protectFeature = True,
                 protectProto = None,
                 protectProtoStr = None,
                 apicall = '',
                 apientry = '',
                 apientryp = '',
                 indentFuncProto = True,
                 indentFuncPointer = False,
                 alignFuncParam = 0):
        GeneratorOptions.__init__(self, filename, apiname, profile,
                                  versions, emitversions, defaultExtensions,
                                  addExtensions, removeExtensions, sortProcedure)
        self.prefixText      = prefixText
        self.genFuncPointers = genFuncPointers
        self.protectFile     = protectFile
        self.protectFeature  = protectFeature
        self.protectProto    = protectProto
        self.protectProtoStr = protectProtoStr
        self.apicall         = apicall
        self.apientry        = apientry
        self.apientryp       = apientryp
        self.indentFuncProto = indentFuncProto
        self.indentFuncPointer = indentFuncPointer
        self.alignFuncParam  = alignFuncParam

# DocGeneratorOptions - subclass of GeneratorOptions.
#
# Shares many members with CGeneratorOptions, since
# both are writing C-style declarations:
#
#   prefixText - list of strings to prefix generated header with
#     (usually a copyright statement + calling convention macros).
#   apicall - string to use for the function declaration prefix,
#     such as APICALL on Windows.
#   apientry - string to use for the calling convention macro,
#     in typedefs, such as APIENTRY.
#   apientryp - string to use for the calling convention macro
#     in function pointer typedefs, such as APIENTRYP.
#   genDirectory - directory into which to generate include files
#   indentFuncProto - True if prototype declarations should put each
#     parameter on a separate line
#   indentFuncPointer - True if typedefed function pointers should put each
#     parameter on a separate line
#   alignFuncParam - if nonzero and parameters are being put on a
#     separate line, align parameter names at the specified column
#
# Additional members:
#
class DocGeneratorOptions(GeneratorOptions):
    """Represents options during C interface generation for Asciidoc"""
    def __init__(self,
                 filename = None,
                 apiname = None,
                 profile = None,
                 versions = '.*',
                 emitversions = '.*',
                 defaultExtensions = None,
                 addExtensions = None,
                 removeExtensions = None,
                 sortProcedure = regSortFeatures,
                 prefixText = "",
                 apicall = '',
                 apientry = '',
                 apientryp = '',
                 genDirectory = 'gen',
                 indentFuncProto = True,
                 indentFuncPointer = False,
                 alignFuncParam = 0,
                 expandEnumerants = True):
        GeneratorOptions.__init__(self, filename, apiname, profile,
                                  versions, emitversions, defaultExtensions,
                                  addExtensions, removeExtensions, sortProcedure)
        self.prefixText      = prefixText
        self.apicall         = apicall
        self.apientry        = apientry
        self.apientryp       = apientryp
        self.genDirectory    = genDirectory
        self.indentFuncProto = indentFuncProto
        self.indentFuncPointer = indentFuncPointer
        self.alignFuncParam  = alignFuncParam
        self.expandEnumerants = expandEnumerants

# OutputGenerator - base class for generating API interfaces.
# Manages basic logic, logging, and output file control
# Derived classes actually generate formatted output.
#
# ---- methods ----
# OutputGenerator(errFile, warnFile, diagFile)
#   errFile, warnFile, diagFile - file handles to write errors,
#     warnings, diagnostics to. May be None to not write.
# logMsg(level, *args) - log messages of different categories
#   level - 'error', 'warn', or 'diag'. 'error' will also
#     raise a UserWarning exception
#   *args - print()-style arguments
# setExtMap(map) - specify a dictionary map from extension names to
#   numbers, used in creating values for extension enumerants.
# beginFile(genOpts) - start a new interface file
#   genOpts - GeneratorOptions controlling what's generated and how
# endFile() - finish an interface file, closing it when done
# beginFeature(interface, emit) - write interface for a feature
# and tag generated features as having been done.
#   interface - element for the <version> / <extension> to generate
#   emit - actually write to the header only when True
# endFeature() - finish an interface.
# genType(typeinfo,name) - generate interface for a type
#   typeinfo - TypeInfo for a type
# genStruct(typeinfo,name) - generate interface for a C "struct" type.
#   typeinfo - TypeInfo for a type interpreted as a struct
# genGroup(groupinfo,name) - generate interface for a group of enums (C "enum")
#   groupinfo - GroupInfo for a group
# genEnum(enuminfo, name) - generate interface for an enum (constant)
#   enuminfo - EnumInfo for an enum
#   name - enum name
# genCmd(cmdinfo) - generate interface for a command
#   cmdinfo - CmdInfo for a command
# makeCDecls(cmd) - return C prototype and function pointer typedef for a
#     <command> Element, as a list of two strings
#   cmd - Element for the <command>
# newline() - print a newline to the output file (utility function)
#
class OutputGenerator:
    """Generate specified API interfaces in a specific style, such as a C header"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        self.outFile = None
        self.errFile = errFile
        self.warnFile = warnFile
        self.diagFile = diagFile
        # Internal state
        self.featureName = None
        self.genOpts = None
        self.registry = None
        # Used for extension enum value generation
        self.extBase      = 1000000000
        self.extBlockSize = 1000
    #
    # logMsg - write a message of different categories to different
    #   destinations.
    # level -
    #   'diag' (diagnostic, voluminous)
    #   'warn' (warning)
    #   'error' (fatal error - raises exception after logging)
    # *args - print()-style arguments to direct to corresponding log
    def logMsg(self, level, *args):
        """Log a message at the given level. Can be ignored or log to a file"""
        if (level == 'error'):
            strfile = io.StringIO()
            write('ERROR:', *args, file=strfile)
            if (self.errFile != None):
                write(strfile.getvalue(), file=self.errFile)
            raise UserWarning(strfile.getvalue())
        elif (level == 'warn'):
            if (self.warnFile != None):
                write('WARNING:', *args, file=self.warnFile)
        elif (level == 'diag'):
            if (self.diagFile != None):
                write('DIAG:', *args, file=self.diagFile)
        else:
            raise UserWarning(
                '*** FATAL ERROR in Generator.logMsg: unknown level:' + level)
    #
    # enumToValue - parses and converts an <enum> tag into a value.
    # Returns a list
    #   first element - integer representation of the value, or None
    #       if needsNum is False. The value must be a legal number
    #       if needsNum is True.
    #   second element - string representation of the value
    # There are several possible representations of values.
    #   A 'value' attribute simply contains the value.
    #   A 'bitpos' attribute defines a value by specifying the bit
    #       position which is set in that value.
    #   A 'offset','extbase','extends' triplet specifies a value
    #       as an offset to a base value defined by the specified
    #       'extbase' extension name, which is then cast to the
    #       typename specified by 'extends'. This requires probing
    #       the registry database, and imbeds knowledge of the
    #       Vulkan extension enum scheme in this function.
    def enumToValue(self, elem, needsNum):
        name = elem.get('name')
        numVal = None
        if ('value' in elem.keys()):
            value = elem.get('value')
            # print('About to translate value =', value, 'type =', type(value))
            if (needsNum):
                numVal = int(value, 0)
            # If there's a non-integer, numeric 'type' attribute (e.g. 'u' or
            # 'ull'), append it to the string value.
            # t = enuminfo.elem.get('type')
            # if (t != None and t != '' and t != 'i' and t != 's'):
            #     value += enuminfo.type
            self.logMsg('diag', 'Enum', name, '-> value [', numVal, ',', value, ']')
            return [numVal, value]
        if ('bitpos' in elem.keys()):
            value = elem.get('bitpos')
            numVal = int(value, 0)
            numVal = 1 << numVal
            value = '0x%08x' % numVal
            self.logMsg('diag', 'Enum', name, '-> bitpos [', numVal, ',', value, ']')
            return [numVal, value]
        if ('offset' in elem.keys()):
            # Obtain values in the mapping from the attributes
            enumNegative = False
            offset = int(elem.get('offset'),0)
            extnumber = int(elem.get('extnumber'),0)
            extends = elem.get('extends')
            if ('dir' in elem.keys()):
                enumNegative = True
            self.logMsg('diag', 'Enum', name, 'offset =', offset,
                'extnumber =', extnumber, 'extends =', extends,
                'enumNegative =', enumNegative)
            # Now determine the actual enumerant value, as defined
            # in the "Layers and Extensions" appendix of the spec.
            numVal = self.extBase + (extnumber - 1) * self.extBlockSize + offset
            if (enumNegative):
                numVal = -numVal
            value = '%d' % numVal
            # More logic needed!
            self.logMsg('diag', 'Enum', name, '-> offset [', numVal, ',', value, ']')
            return [numVal, value]
        return [None, None]
    #
    def beginFile(self, genOpts):
        self.genOpts = genOpts
        #
        # Open specified output file. Not done in constructor since a
        # Generator can be used without writing to a file.
        if (self.genOpts.filename != None):
            self.outFile = open(self.genOpts.filename, 'w')
        else:
            self.outFile = sys.stdout
    def endFile(self):
        self.errFile and self.errFile.flush()
        self.warnFile and self.warnFile.flush()
        self.diagFile and self.diagFile.flush()
        self.outFile.flush()
        if (self.outFile != sys.stdout and self.outFile != sys.stderr):
            self.outFile.close()
        self.genOpts = None
    #
    def beginFeature(self, interface, emit):
        self.emit = emit
        self.featureName = interface.get('name')
        # If there's an additional 'protect' attribute in the feature, save it
        self.featureExtraProtect = interface.get('protect')
    def endFeature(self):
        # Derived classes responsible for emitting feature
        self.featureName = None
        self.featureExtraProtect = None
    # Utility method to validate we're generating something only inside a
    # <feature> tag
    def validateFeature(self, featureType, featureName):
        if (self.featureName == None):
            raise UserWarning('Attempt to generate', featureType, name,
                    'when not in feature')
    #
    # Type generation
    def genType(self, typeinfo, name):
        self.validateFeature('type', name)
    #
    # Struct (e.g. C "struct" type) generation
    def genStruct(self, typeinfo, name):
        self.validateFeature('struct', name)
    #
    # Group (e.g. C "enum" type) generation
    def genGroup(self, groupinfo, name):
        self.validateFeature('group', name)
    #
    # Enumerant (really, constant) generation
    def genEnum(self, enuminfo, name):
        self.validateFeature('enum', name)
    #
    # Command generation
    def genCmd(self, cmd, name):
        self.validateFeature('command', name)
    #
    # Utility functions - turn a <proto> <name> into C-language prototype
    # and typedef declarations for that name.
    # name - contents of <name> tag
    # tail - whatever text follows that tag in the Element
    def makeProtoName(self, name, tail):
        return self.genOpts.apientry + name + tail
    def makeTypedefName(self, name, tail):
       return '(' + self.genOpts.apientryp + 'PFN_' + name + tail + ')'
    #
    # makeCParamDecl - return a string which is an indented, formatted
    # declaration for a <param> or <member> block (e.g. function parameter
    # or structure/union member).
    # param - Element (<param> or <member>) to format
    # aligncol - if non-zero, attempt to align the nested <name> element
    #   at this column
    def makeCParamDecl(self, param, aligncol):
        paramdecl = '    ' + noneStr(param.text)
        for elem in param:
            text = noneStr(elem.text)
            tail = noneStr(elem.tail)
            if (elem.tag == 'name' and aligncol > 0):
                self.logMsg('diag', 'Aligning parameter', elem.text, 'to column', self.genOpts.alignFuncParam)
                # Align at specified column, if possible
                paramdecl = paramdecl.rstrip()
                oldLen = len(paramdecl)
                paramdecl = paramdecl.ljust(aligncol)
                newLen = len(paramdecl)
                self.logMsg('diag', 'Adjust length of parameter decl from', oldLen, 'to', newLen, ':', paramdecl)
            paramdecl += text + tail
        return paramdecl
    #
    # getCParamTypeLength - return the length of the type field is an indented, formatted
    # declaration for a <param> or <member> block (e.g. function parameter
    # or structure/union member).
    # param - Element (<param> or <member>) to identify
    def getCParamTypeLength(self, param):
        paramdecl = '    ' + noneStr(param.text)
        for elem in param:
            text = noneStr(elem.text)
            tail = noneStr(elem.tail)
            if (elem.tag == 'name'):
                # Align at specified column, if possible
                newLen = len(paramdecl.rstrip())
                self.logMsg('diag', 'Identifying length of', elem.text, 'as', newLen)
            paramdecl += text + tail
        return newLen
    #
    # makeCDecls - return C prototype and function pointer typedef for a
    #   command, as a two-element list of strings.
    # cmd - Element containing a <command> tag
    def makeCDecls(self, cmd):
        """Generate C function pointer typedef for <command> Element"""
        proto = cmd.find('proto')
        params = cmd.findall('param')
        # Begin accumulating prototype and typedef strings
        pdecl = self.genOpts.apicall
        tdecl = 'typedef '
        #
        # Insert the function return type/name.
        # For prototypes, add APIENTRY macro before the name
        # For typedefs, add (APIENTRY *<name>) around the name and
        #   use the PFN_cmdnameproc naming convention.
        # Done by walking the tree for <proto> element by element.
        # lxml.etree has elem.text followed by (elem[i], elem[i].tail)
        #   for each child element and any following text
        # Leading text
        pdecl += noneStr(proto.text)
        tdecl += noneStr(proto.text)
        # For each child element, if it's a <name> wrap in appropriate
        # declaration. Otherwise append its contents and tail contents.
        for elem in proto:
            text = noneStr(elem.text)
            tail = noneStr(elem.tail)
            if (elem.tag == 'name'):
                pdecl += self.makeProtoName(text, tail)
                tdecl += self.makeTypedefName(text, tail)
            else:
                pdecl += text + tail
                tdecl += text + tail
        # Now add the parameter declaration list, which is identical
        # for prototypes and typedefs. Concatenate all the text from
        # a <param> node without the tags. No tree walking required
        # since all tags are ignored.
        # Uses: self.indentFuncProto
        # self.indentFuncPointer
        # self.alignFuncParam
        # Might be able to doubly-nest the joins, e.g.
        #   ','.join(('_'.join([l[i] for i in range(0,len(l))])
        n = len(params)
        # Indented parameters
        if n > 0:
            indentdecl = '(\n'
            for i in range(0,n):
                paramdecl = self.makeCParamDecl(params[i], self.genOpts.alignFuncParam)
                if (i < n - 1):
                    paramdecl += ',\n'
                else:
                    paramdecl += ');'
                indentdecl += paramdecl
        else:
            indentdecl = '(void);'
        # Non-indented parameters
        paramdecl = '('
        if n > 0:
            for i in range(0,n):
                paramdecl += ''.join([t for t in params[i].itertext()])
                if (i < n - 1):
                    paramdecl += ', '
        else:
            paramdecl += 'void'
        paramdecl += ");";
        return [ pdecl + indentdecl, tdecl + paramdecl ]
    #
    def newline(self):
        write('', file=self.outFile)

    def setRegistry(self, registry):
        self.registry = registry
        #

# COutputGenerator - subclass of OutputGenerator.
# Generates C-language API interfaces.
#
# ---- methods ----
# COutputGenerator(errFile, warnFile, diagFile) - args as for
#   OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# beginFile(genOpts)
# endFile()
# beginFeature(interface, emit)
# endFeature()
# genType(typeinfo,name)
# genStruct(typeinfo,name)
# genGroup(groupinfo,name)
# genEnum(enuminfo, name)
# genCmd(cmdinfo)
class COutputGenerator(OutputGenerator):
    """Generate specified API interfaces in a specific style, such as a C header"""
    # This is an ordered list of sections in the header file.
    TYPE_SECTIONS = ['include', 'define', 'basetype', 'handle', 'enum',
                     'group', 'bitmask', 'funcpointer', 'struct']
    ALL_SECTIONS = TYPE_SECTIONS + ['commandPointer', 'command']
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
        # Internal state - accumulators for different inner block text
        self.sections = dict([(section, []) for section in self.ALL_SECTIONS])
    #
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
        # C-specific
        #
        # Multiple inclusion protection & C++ wrappers.
        if (genOpts.protectFile and self.genOpts.filename):
            headerSym = re.sub('\.h', '_h_',
                               os.path.basename(self.genOpts.filename)).upper()
            write('#ifndef', headerSym, file=self.outFile)
            write('#define', headerSym, '1', file=self.outFile)
            self.newline()
        write('#ifdef __cplusplus', file=self.outFile)
        write('extern "C" {', file=self.outFile)
        write('#endif', file=self.outFile)
        self.newline()
        #
        # User-supplied prefix text, if any (list of strings)
        if (genOpts.prefixText):
            for s in genOpts.prefixText:
                write(s, file=self.outFile)
        #
        # Some boilerplate describing what was generated - this
        # will probably be removed later since the extensions
        # pattern may be very long.
        # write('/* Generated C header for:', file=self.outFile)
        # write(' * API:', genOpts.apiname, file=self.outFile)
        # if (genOpts.profile):
        #     write(' * Profile:', genOpts.profile, file=self.outFile)
        # write(' * Versions considered:', genOpts.versions, file=self.outFile)
        # write(' * Versions emitted:', genOpts.emitversions, file=self.outFile)
        # write(' * Default extensions included:', genOpts.defaultExtensions, file=self.outFile)
        # write(' * Additional extensions included:', genOpts.addExtensions, file=self.outFile)
        # write(' * Extensions removed:', genOpts.removeExtensions, file=self.outFile)
        # write(' */', file=self.outFile)
    def endFile(self):
        # C-specific
        # Finish C++ wrapper and multiple inclusion protection
        self.newline()
        write('#ifdef __cplusplus', file=self.outFile)
        write('}', file=self.outFile)
        write('#endif', file=self.outFile)
        if (self.genOpts.protectFile and self.genOpts.filename):
            self.newline()
            write('#endif', file=self.outFile)
        # Finish processing in superclass
        OutputGenerator.endFile(self)
    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)
        # C-specific
        # Accumulate includes, defines, types, enums, function pointer typedefs,
        # end function prototypes separately for this feature. They're only
        # printed in endFeature().
        self.sections = dict([(section, []) for section in self.ALL_SECTIONS])
    def endFeature(self):
        # C-specific
        # Actually write the interface to the output file.
        if (self.emit):
            self.newline()
            if (self.genOpts.protectFeature):
                write('#ifndef', self.featureName, file=self.outFile)
            # If type declarations are needed by other features based on
            # this one, it may be necessary to suppress the ExtraProtect,
            # or move it below the 'for section...' loop.
            if (self.featureExtraProtect != None):
                write('#ifdef', self.featureExtraProtect, file=self.outFile)
            write('#define', self.featureName, '1', file=self.outFile)
            for section in self.TYPE_SECTIONS:
                contents = self.sections[section]
                if contents:
                    write('\n'.join(contents), file=self.outFile)
                    self.newline()
            if (self.genOpts.genFuncPointers and self.sections['commandPointer']):
                write('\n'.join(self.sections['commandPointer']), file=self.outFile)
                self.newline()
            if (self.sections['command']):
                if (self.genOpts.protectProto):
                    write(self.genOpts.protectProto,
                          self.genOpts.protectProtoStr, file=self.outFile)
                write('\n'.join(self.sections['command']), end='', file=self.outFile)
                if (self.genOpts.protectProto):
                    write('#endif', file=self.outFile)
                else:
                    self.newline()
            if (self.featureExtraProtect != None):
                write('#endif /*', self.featureExtraProtect, '*/', file=self.outFile)
            if (self.genOpts.protectFeature):
                write('#endif /*', self.featureName, '*/', file=self.outFile)
        # Finish processing in superclass
        OutputGenerator.endFeature(self)
    #
    # Append a definition to the specified section
    def appendSection(self, section, text):
        # self.sections[section].append('SECTION: ' + section + '\n')
        self.sections[section].append(text)
    #
    # Type generation
    def genType(self, typeinfo, name):
        OutputGenerator.genType(self, typeinfo, name)
        typeElem = typeinfo.elem
        # If the type is a struct type, traverse the imbedded <member> tags
        # generating a structure. Otherwise, emit the tag text.
        category = typeElem.get('category')
        if (category == 'struct' or category == 'union'):
            self.genStruct(typeinfo, name)
        else:
            # Replace <apientry /> tags with an APIENTRY-style string
            # (from self.genOpts). Copy other text through unchanged.
            # If the resulting text is an empty string, don't emit it.
            s = noneStr(typeElem.text)
            for elem in typeElem:
                if (elem.tag == 'apientry'):
                    s += self.genOpts.apientry + noneStr(elem.tail)
                else:
                    s += noneStr(elem.text) + noneStr(elem.tail)
            if s:
                # Add extra newline after multi-line entries.
                if '\n' in s:
                    s += '\n'
                self.appendSection(category, s)
    #
    # Struct (e.g. C "struct" type) generation.
    # This is a special case of the <type> tag where the contents are
    # interpreted as a set of <member> tags instead of freeform C
    # C type declarations. The <member> tags are just like <param>
    # tags - they are a declaration of a struct or union member.
    # Only simple member declarations are supported (no nested
    # structs etc.)
    def genStruct(self, typeinfo, typeName):
        OutputGenerator.genStruct(self, typeinfo, typeName)
        body = 'typedef ' + typeinfo.elem.get('category') + ' ' + typeName + ' {\n'
        # paramdecl = self.makeCParamDecl(typeinfo.elem, self.genOpts.alignFuncParam)
        targetLen = 0;
        for member in typeinfo.elem.findall('.//member'):
            targetLen = max(targetLen, self.getCParamTypeLength(member))
        for member in typeinfo.elem.findall('.//member'):
            body += self.makeCParamDecl(member, targetLen + 4)
            body += ';\n'
        body += '} ' + typeName + ';\n'
        self.appendSection('struct', body)
    #
    # Group (e.g. C "enum" type) generation.
    # These are concatenated together with other types.
    def genGroup(self, groupinfo, groupName):
        OutputGenerator.genGroup(self, groupinfo, groupName)
        groupElem = groupinfo.elem
        
        expandName = re.sub(r'([0-9a-z_])([A-Z0-9][^A-Z0-9]?)',r'\1_\2',groupName).upper()
        
        expandPrefix = expandName
        expandSuffix = ''
        expandSuffixMatch = re.search(r'[A-Z][A-Z]+$',groupName)
        if expandSuffixMatch:
            expandSuffix = '_' + expandSuffixMatch.group()
            # Strip off the suffix from the prefix
            expandPrefix = expandName.rsplit(expandSuffix, 1)[0]
                
        # Prefix
        body = "\ntypedef enum " + groupName + " {\n"
        
        isEnum = ('FLAG_BITS' not in expandPrefix)
        
        # Loop over the nested 'enum' tags. Keep track of the minimum and
        # maximum numeric values, if they can be determined; but only for
        # core API enumerants, not extension enumerants. This is inferred
        # by looking for 'extends' attributes.
        minName = None
        for elem in groupElem.findall('enum'):
            # Convert the value to an integer and use that to track min/max.
            # Values of form -(number) are accepted but nothing more complex.
            # Should catch exceptions here for more complex constructs. Not yet.
            (numVal,strVal) = self.enumToValue(elem, True)
            name = elem.get('name')

            # Extension enumerants are only included if they are requested
            # in addExtensions or match defaultExtensions.
            if (elem.get('extname') is None or
              re.match(self.genOpts.addExtensions,elem.get('extname')) is not None or
              self.genOpts.defaultExtensions == elem.get('supported')):
                body += "    " + name + " = " + strVal + ",\n"

            if (isEnum  and elem.get('extends') is None):
                if (minName == None):
                    minName = maxName = name
                    minValue = maxValue = numVal
                elif (numVal < minValue):
                    minName = name
                    minValue = numVal
                elif (numVal > maxValue):
                    maxName = name
                    maxValue = numVal
        # Generate min/max value tokens and a range-padding enum. Need some
        # additional padding to generate correct names...
        if isEnum:
            body += "    " + expandPrefix + "_BEGIN_RANGE" + expandSuffix + " = " + minName + ",\n"
            body += "    " + expandPrefix + "_END_RANGE" + expandSuffix + " = " + maxName + ",\n"
            body += "    " + expandPrefix + "_RANGE_SIZE" + expandSuffix + " = (" + maxName + " - " + minName + " + 1),\n"
            
        body += "    " + expandPrefix + "_MAX_ENUM" + expandSuffix + " = 0x7FFFFFFF\n"
        
        # Postfix
        body += "} " + groupName + ";"
        if groupElem.get('type') == 'bitmask':
            section = 'bitmask'
        else:
            section = 'group'
        self.appendSection(section, body)
    # Enumerant generation
    # <enum> tags may specify their values in several ways, but are usually
    # just integers.
    def genEnum(self, enuminfo, name):
        OutputGenerator.genEnum(self, enuminfo, name)
        (numVal,strVal) = self.enumToValue(enuminfo.elem, False)
        body = '#define ' + name.ljust(33) + ' ' + strVal
        self.appendSection('enum', body)
    #
    # Command generation
    def genCmd(self, cmdinfo, name):
        OutputGenerator.genCmd(self, cmdinfo, name)
        #
        decls = self.makeCDecls(cmdinfo.elem)
        self.appendSection('command', decls[0] + '\n')
        if (self.genOpts.genFuncPointers):
            self.appendSection('commandPointer', decls[1])

# DocOutputGenerator - subclass of OutputGenerator.
# Generates AsciiDoc includes with C-language API interfaces, for reference
# pages and the Vulkan specification. Similar to COutputGenerator, but
# each interface is written into a different file as determined by the
# options, only actual C types are emitted, and none of the boilerplate
# preprocessor code is emitted.
#
# ---- methods ----
# DocOutputGenerator(errFile, warnFile, diagFile) - args as for
#   OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# beginFile(genOpts)
# endFile()
# beginFeature(interface, emit)
# endFeature()
# genType(typeinfo,name)
# genStruct(typeinfo,name)
# genGroup(groupinfo,name)
# genEnum(enuminfo, name)
# genCmd(cmdinfo)
class DocOutputGenerator(OutputGenerator):
    """Generate specified API interfaces in a specific style, such as a C header"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
    #
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
    def endFile(self):
        OutputGenerator.endFile(self)
    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)
    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)
    #
    # Generate an include file
    #
    # directory - subdirectory to put file in
    # basename - base name of the file
    # contents - contents of the file (Asciidoc boilerplate aside)
    def writeInclude(self, directory, basename, contents):
        # Create file
        filename = self.genOpts.genDirectory + '/' + directory + '/' + basename + '.txt'
        self.logMsg('diag', '# Generating include file:', filename)
        fp = open(filename, 'w')
        # Asciidoc anchor
        write('// WARNING: DO NOT MODIFY! This file is automatically generated from the vk.xml registry', file=fp)
        write('ifndef::doctype-manpage[]', file=fp)
        write('[[{0},{0}]]'.format(basename), file=fp)
        write('["source","{basebackend@docbook:c++:cpp}",title=""]', file=fp)
        write('endif::doctype-manpage[]', file=fp)
        write('ifdef::doctype-manpage[]', file=fp)
        write('["source","{basebackend@docbook:c++:cpp}"]', file=fp)
        write('endif::doctype-manpage[]', file=fp)
        write('------------------------------------------------------------------------------', file=fp)
        write(contents, file=fp)
        write('------------------------------------------------------------------------------', file=fp)
        fp.close()
    #
    # Type generation
    def genType(self, typeinfo, name):
        OutputGenerator.genType(self, typeinfo, name)
        typeElem = typeinfo.elem
        # If the type is a struct type, traverse the imbedded <member> tags
        # generating a structure. Otherwise, emit the tag text.
        category = typeElem.get('category')
        if (category == 'struct' or category == 'union'):
            self.genStruct(typeinfo, name)
        else:
            # Replace <apientry /> tags with an APIENTRY-style string
            # (from self.genOpts). Copy other text through unchanged.
            # If the resulting text is an empty string, don't emit it.
            s = noneStr(typeElem.text)
            for elem in typeElem:
                if (elem.tag == 'apientry'):
                    s += self.genOpts.apientry + noneStr(elem.tail)
                else:
                    s += noneStr(elem.text) + noneStr(elem.tail)
            if (len(s) > 0):
                if (category == 'bitmask'):
                    self.writeInclude('flags', name, s + '\n')
                elif (category == 'enum'):
                    self.writeInclude('enums', name, s + '\n')
                elif (category == 'funcpointer'):
                    self.writeInclude('funcpointers', name, s+ '\n')
                else:
                    self.logMsg('diag', '# NOT writing include file for type:',
                        name, 'category: ', category)
            else:
                self.logMsg('diag', '# NOT writing empty include file for type', name)
    #
    # Struct (e.g. C "struct" type) generation.
    # This is a special case of the <type> tag where the contents are
    # interpreted as a set of <member> tags instead of freeform C
    # C type declarations. The <member> tags are just like <param>
    # tags - they are a declaration of a struct or union member.
    # Only simple member declarations are supported (no nested
    # structs etc.)
    def genStruct(self, typeinfo, typeName):
        OutputGenerator.genStruct(self, typeinfo, typeName)
        s = 'typedef ' + typeinfo.elem.get('category') + ' ' + typeName + ' {\n'
        # paramdecl = self.makeCParamDecl(typeinfo.elem, self.genOpts.alignFuncParam)
        targetLen = 0;
        for member in typeinfo.elem.findall('.//member'):
            targetLen = max(targetLen, self.getCParamTypeLength(member))
        for member in typeinfo.elem.findall('.//member'):
            s += self.makeCParamDecl(member, targetLen + 4)
            s += ';\n'
        s += '} ' + typeName + ';'
        self.writeInclude('structs', typeName, s)
    #
    # Group (e.g. C "enum" type) generation.
    # These are concatenated together with other types.
    def genGroup(self, groupinfo, groupName):
        OutputGenerator.genGroup(self, groupinfo, groupName)
        groupElem = groupinfo.elem
        
        # See if we need min/max/num/padding at end
        expand = self.genOpts.expandEnumerants
        
        if expand:
            expandName = re.sub(r'([0-9a-z_])([A-Z0-9][^A-Z0-9]?)',r'\1_\2',groupName).upper()
            isEnum = ('FLAG_BITS' not in expandName)
        
            expandPrefix = expandName
            expandSuffix = ''
            
            # Look for a suffix
            expandSuffixMatch = re.search(r'[A-Z][A-Z]+$',groupName)
            if expandSuffixMatch:
                expandSuffix = '_' + expandSuffixMatch.group()
                # Strip off the suffix from the prefix
                expandPrefix = expandName.rsplit(expandSuffix, 1)[0]
        
        # Prefix
        s = "typedef enum " + groupName + " {\n"

        # Loop over the nested 'enum' tags. Keep track of the minimum and
        # maximum numeric values, if they can be determined.
        minName = None
        for elem in groupElem.findall('enum'):
            # Convert the value to an integer and use that to track min/max.
            # Values of form -(number) are accepted but nothing more complex.
            # Should catch exceptions here for more complex constructs. Not yet.
            (numVal,strVal) = self.enumToValue(elem, True)
            name = elem.get('name')

            # Extension enumerants are only included if they are requested
            # in addExtensions or match defaultExtensions.
            if (elem.get('extname') is None or
              re.match(self.genOpts.addExtensions,elem.get('extname')) is not None or
              self.genOpts.defaultExtensions == elem.get('supported')):
                s += "    " + name + " = " + strVal + ",\n"

            if (expand and isEnum and elem.get('extends') is None):
                if (minName == None):
                    minName = maxName = name
                    minValue = maxValue = numVal
                elif (numVal < minValue):
                    minName = name
                    minValue = numVal
                elif (numVal > maxValue):
                    maxName = name
                    maxValue = numVal
        # Generate min/max value tokens and a range-padding enum. Need some
        # additional padding to generate correct names...
        if (expand):
            s += "\n"
            if isEnum:
                s += "    " + expandPrefix + "_BEGIN_RANGE" + expandSuffix + " = " + minName + ",\n"
                s += "    " + expandPrefix + "_END_RANGE" + expandSuffix + " = " + maxName + ",\n"
                s += "    " + expandPrefix + "_RANGE_SIZE" + expandSuffix + " = (" + maxName + " - " + minName + " + 1),\n"
            
            s += "    " + expandPrefix + "_MAX_ENUM" + expandSuffix + " = 0x7FFFFFFF\n"
        # Postfix
        s += "} " + groupName + ";"
        self.writeInclude('enums', groupName, s)
    # Enumerant generation
    # <enum> tags may specify their values in several ways, but are usually
    # just integers.
    def genEnum(self, enuminfo, name):
        OutputGenerator.genEnum(self, enuminfo, name)
        (numVal,strVal) = self.enumToValue(enuminfo.elem, False)
        s = '#define ' + name.ljust(33) + ' ' + strVal
        self.logMsg('diag', '# NOT writing compile-time constant', name)
        # self.writeInclude('consts', name, s)
    #
    # Command generation
    def genCmd(self, cmdinfo, name):
        OutputGenerator.genCmd(self, cmdinfo, name)
        #
        decls = self.makeCDecls(cmdinfo.elem)
        self.writeInclude('protos', name, decls[0])

# PyOutputGenerator - subclass of OutputGenerator.
# Generates Python data structures describing API names.
# Similar to DocOutputGenerator, but writes a single
# file.
#
# ---- methods ----
# PyOutputGenerator(errFile, warnFile, diagFile) - args as for
#   OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# beginFile(genOpts)
# endFile()
# genType(typeinfo,name)
# genStruct(typeinfo,name)
# genGroup(groupinfo,name)
# genEnum(enuminfo, name)
# genCmd(cmdinfo)
class PyOutputGenerator(OutputGenerator):
    """Generate specified API interfaces in a specific style, such as a C header"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
    #
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
        for dict in [ 'flags', 'enums', 'structs', 'consts', 'enums',
          'consts', 'protos', 'funcpointers' ]:
            write(dict, '= {}', file=self.outFile)
    def endFile(self):
        OutputGenerator.endFile(self)
    #
    # Add a name from the interface
    #
    # dict - type of name (see beginFile above)
    # name - name to add
    # value - A serializable Python value for the name
    def addName(self, dict, name, value=None):
        write(dict + "['" + name + "'] = ", value, file=self.outFile)
    #
    # Type generation
    # For 'struct' or 'union' types, defer to genStruct() to
    #   add to the dictionary.
    # For 'bitmask' types, add the type name to the 'flags' dictionary,
    #   with the value being the corresponding 'enums' name defining
    #   the acceptable flag bits.
    # For 'enum' types, add the type name to the 'enums' dictionary,
    #   with the value being '@STOPHERE@' (because this case seems
    #   never to happen).
    # For 'funcpointer' types, add the type name to the 'funcpointers'
    #   dictionary.
    # For 'handle' and 'define' types, add the handle or #define name
    #   to the 'struct' dictionary, because that's how the spec sources
    #   tag these types even though they aren't structs.
    def genType(self, typeinfo, name):
        OutputGenerator.genType(self, typeinfo, name)
        typeElem = typeinfo.elem
        # If the type is a struct type, traverse the imbedded <member> tags
        # generating a structure. Otherwise, emit the tag text.
        category = typeElem.get('category')
        if (category == 'struct' or category == 'union'):
            self.genStruct(typeinfo, name)
        else:
            # Extract the type name
            # (from self.genOpts). Copy other text through unchanged.
            # If the resulting text is an empty string, don't emit it.
            count = len(noneStr(typeElem.text))
            for elem in typeElem:
                count += len(noneStr(elem.text)) + len(noneStr(elem.tail))
            if (count > 0):
                if (category == 'bitmask'):
                    requiredEnum = typeElem.get('requires')
                    self.addName('flags', name, enquote(requiredEnum))
                elif (category == 'enum'):
                    # This case never seems to come up!
                    # @enums   C 'enum' name           Dictionary of enumerant names
                    self.addName('enums', name, enquote('@STOPHERE@'))
                elif (category == 'funcpointer'):
                    self.addName('funcpointers', name, None)
                elif (category == 'handle' or category == 'define'):
                    self.addName('structs', name, None)
                else:
                    write('# Unprocessed type:', name, 'category:', category, file=self.outFile)
            else:
                write('# Unprocessed type:', name, file=self.outFile)
    #
    # Struct (e.g. C "struct" type) generation.
    #
    # Add the struct name to the 'structs' dictionary, with the
    # value being an ordered list of the struct member names.
    def genStruct(self, typeinfo, typeName):
        OutputGenerator.genStruct(self, typeinfo, typeName)

        members = [member.text for member in typeinfo.elem.findall('.//member/name')]
        self.addName('structs', typeName, members)
    #
    # Group (e.g. C "enum" type) generation.
    # These are concatenated together with other types.
    #
    # Add the enum type name to the 'enums' dictionary, with
    #   the value being an ordered list of the enumerant names.
    # Add each enumerant name to the 'consts' dictionary, with
    #   the value being the enum type the enumerant is part of.
    def genGroup(self, groupinfo, groupName):
        OutputGenerator.genGroup(self, groupinfo, groupName)
        groupElem = groupinfo.elem

        # @enums   C 'enum' name           Dictionary of enumerant names
        # @consts  C enumerant/const name  Name of corresponding 'enums' key

        # Loop over the nested 'enum' tags. Keep track of the minimum and
        # maximum numeric values, if they can be determined.
        enumerants = [elem.get('name') for elem in groupElem.findall('enum')]
        for name in enumerants:
            self.addName('consts', name, enquote(groupName))
        self.addName('enums', groupName, enumerants)
    # Enumerant generation (compile-time constants)
    #
    # Add the constant name to the 'consts' dictionary, with the
    #   value being None to indicate that the constant isn't
    #   an enumeration value.
    def genEnum(self, enuminfo, name):
        OutputGenerator.genEnum(self, enuminfo, name)

        # @consts  C enumerant/const name  Name of corresponding 'enums' key

        self.addName('consts', name, None)
    #
    # Command generation
    #
    # Add the command name to the 'protos' dictionary, with the
    #   value being an ordered list of the parameter names.
    def genCmd(self, cmdinfo, name):
        OutputGenerator.genCmd(self, cmdinfo, name)

        params = [param.text for param in cmdinfo.elem.findall('param/name')]
        self.addName('protos', name, params)

# ValidityOutputGenerator - subclass of OutputGenerator.
# Generates AsciiDoc includes of valid usage information, for reference
# pages and the Vulkan specification. Similar to DocOutputGenerator.
#
# ---- methods ----
# ValidityOutputGenerator(errFile, warnFile, diagFile) - args as for
#   OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# beginFile(genOpts)
# endFile()
# beginFeature(interface, emit)
# endFeature()
# genCmd(cmdinfo)
class ValidityOutputGenerator(OutputGenerator):
    """Generate specified API interfaces in a specific style, such as a C header"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
    def endFile(self):
        OutputGenerator.endFile(self)
    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)
    def endFeature(self):
        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    def makeParameterName(self, name):
        return 'pname:' + name

    def makeStructName(self, name):
        return 'sname:' + name

    def makeBaseTypeName(self, name):
        return 'basetype:' + name

    def makeEnumerationName(self, name):
        return 'elink:' + name

    def makeEnumerantName(self, name):
        return 'ename:' + name

    def makeFLink(self, name):
        return 'flink:' + name

    #
    # Generate an include file
    #
    # directory - subdirectory to put file in
    # basename - base name of the file
    # contents - contents of the file (Asciidoc boilerplate aside)
    def writeInclude(self, directory, basename, validity, threadsafety, commandpropertiesentry, successcodes, errorcodes):
        # Create file
        filename = self.genOpts.genDirectory + '/' + directory + '/' + basename + '.txt'
        self.logMsg('diag', '# Generating include file:', filename)
        fp = open(filename, 'w')
        # Asciidoc anchor
        write('// WARNING: DO NOT MODIFY! This file is automatically generated from the vk.xml registry', file=fp)

        # Valid Usage
        if validity is not None:
            write('ifndef::doctype-manpage[]', file=fp)
            write('.Valid Usage', file=fp)
            write('*' * 80, file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write('ifdef::doctype-manpage[]', file=fp)
            write('Valid Usage', file=fp)
            write('-----------', file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write(validity, file=fp, end='')
            write('ifndef::doctype-manpage[]', file=fp)
            write('*' * 80, file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write('', file=fp)

        # Host Synchronization
        if threadsafety is not None:
            write('ifndef::doctype-manpage[]', file=fp)
            write('.Host Synchronization', file=fp)
            write('*' * 80, file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write('ifdef::doctype-manpage[]', file=fp)
            write('Host Synchronization', file=fp)
            write('--------------------', file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write(threadsafety, file=fp, end='')
            write('ifndef::doctype-manpage[]', file=fp)
            write('*' * 80, file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write('', file=fp)

        # Command Properties - contained within a block, to avoid table numbering
        if commandpropertiesentry is not None:
            write('ifndef::doctype-manpage[]', file=fp)
            write('.Command Properties', file=fp)
            write('*' * 80, file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write('ifdef::doctype-manpage[]', file=fp)
            write('Command Properties', file=fp)
            write('------------------', file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write('[options="header", width="100%"]', file=fp)
            write('|=====================', file=fp)
            write('|Command Buffer Levels|Render Pass Scope|Supported Queue Types', file=fp)
            write(commandpropertiesentry, file=fp)
            write('|=====================', file=fp)
            write('ifndef::doctype-manpage[]', file=fp)
            write('*' * 80, file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write('', file=fp)

        # Success Codes - contained within a block, to avoid table numbering
        if successcodes is not None or errorcodes is not None:
            write('ifndef::doctype-manpage[]', file=fp)
            write('.Return Codes', file=fp)
            write('*' * 80, file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write('ifdef::doctype-manpage[]', file=fp)
            write('Return Codes', file=fp)
            write('------------', file=fp)
            write('endif::doctype-manpage[]', file=fp)
            if successcodes is not None:
                write('ifndef::doctype-manpage[]', file=fp)
                write('<<fundamentals-successcodes,Success>>::', file=fp)
                write('endif::doctype-manpage[]', file=fp)
                write('ifdef::doctype-manpage[]', file=fp)
                write('On success, this command returns::', file=fp)
                write('endif::doctype-manpage[]', file=fp)
                write(successcodes, file=fp)
            if errorcodes is not None:
                write('ifndef::doctype-manpage[]', file=fp)
                write('<<fundamentals-errorcodes,Failure>>::', file=fp)
                write('endif::doctype-manpage[]', file=fp)
                write('ifdef::doctype-manpage[]', file=fp)
                write('On failure, this command returns::', file=fp)
                write('endif::doctype-manpage[]', file=fp)
                write(errorcodes, file=fp)
            write('ifndef::doctype-manpage[]', file=fp)
            write('*' * 80, file=fp)
            write('endif::doctype-manpage[]', file=fp)
            write('', file=fp)

        fp.close()

    #
    # Check if the parameter passed in is a pointer
    def paramIsPointer(self, param):
        ispointer = False
        paramtype = param.find('type')
        if paramtype.tail is not None and '*' in paramtype.tail:
            ispointer = True

        return ispointer

    #
    # Check if the parameter passed in is a static array
    def paramIsStaticArray(self, param):
        if param.find('name').tail is not None:
            if param.find('name').tail[0] == '[':
                return True

    #
    # Get the length of a parameter that's been identified as a static array
    def staticArrayLength(self, param):
        paramname = param.find('name')
        paramenumsize = param.find('enum')

        if paramenumsize is not None:
            return paramenumsize.text
        else:
            return paramname.tail[1:-1]

    #
    # Check if the parameter passed in is a pointer to an array
    def paramIsArray(self, param):
        return param.attrib.get('len') is not None

    #
    # Get the parent of a handle object
    def getHandleParent(self, typename):
        types = self.registry.findall("types/type")
        for elem in types:
            if (elem.find("name") is not None and elem.find('name').text == typename) or elem.attrib.get('name') == typename:
                return elem.attrib.get('parent')

    #
    # Check if a parent object is dispatchable or not
    def isHandleTypeDispatchable(self, handlename):
        handle = self.registry.find("types/type/[name='" + handlename + "'][@category='handle']")
        if handle is not None and handle.find('type').text == 'VK_DEFINE_HANDLE':
            return True
        else:
            return False

    def isHandleOptional(self, param, params):

        # See if the handle is optional
        isOptional = False

        # Simple, if it's optional, return true
        if param.attrib.get('optional') is not None:
            return True

        # If no validity is being generated, it usually means that validity is complex and not absolute, so let's say yes.
        if param.attrib.get('noautovalidity') is not None:
            return True

        # If the parameter is an array and we haven't already returned, find out if any of the len parameters are optional
        if self.paramIsArray(param):
            lengths = param.attrib.get('len').split(',')
            for length in lengths:
                if (length) != 'null-terminated' and (length) != '1':
                    for otherparam in params:
                        if otherparam.find('name').text == length:
                            if otherparam.attrib.get('optional') is not None:
                                return True

        return False
    #
    # Get the category of a type
    def getTypeCategory(self, typename):
        types = self.registry.findall("types/type")
        for elem in types:
            if (elem.find("name") is not None and elem.find('name').text == typename) or elem.attrib.get('name') == typename:
                return elem.attrib.get('category')

    #
    # Make a chunk of text for the end of a parameter if it is an array
    def makeAsciiDocPreChunk(self, param, params):
        paramname = param.find('name')
        paramtype = param.find('type')

        # General pre-amble. Check optionality and add stuff.
        asciidoc = '* '

        if self.paramIsStaticArray(param):
            asciidoc += 'Any given element of '

        elif self.paramIsArray(param):
            lengths = param.attrib.get('len').split(',')

            # Find all the parameters that are called out as optional, so we can document that they might be zero, and the array may be ignored
            optionallengths = []
            for length in lengths:
                if (length) != 'null-terminated' and (length) != '1':
                    for otherparam in params:
                        if otherparam.find('name').text == length:
                            if otherparam.attrib.get('optional') is not None:
                                if self.paramIsPointer(otherparam):
                                    optionallengths.append('the value referenced by ' + self.makeParameterName(length))
                                else:
                                    optionallengths.append(self.makeParameterName(length))

            # Document that these arrays may be ignored if any of the length values are 0
            if len(optionallengths) != 0 or param.attrib.get('optional') is not None:
                asciidoc += 'If '


                if len(optionallengths) != 0:
                    if len(optionallengths) == 1:

                        asciidoc += optionallengths[0]
                        asciidoc += ' is '

                    else:
                        asciidoc += ' or '.join(optionallengths)
                        asciidoc += ' are '

                    asciidoc += 'not `0`, '

                if len(optionallengths) != 0 and param.attrib.get('optional') is not None:
                    asciidoc += 'and '

                if param.attrib.get('optional') is not None:
                    asciidoc += self.makeParameterName(paramname.text)
                    asciidoc += ' is not `NULL`, '

        elif param.attrib.get('optional') is not None:
            # Don't generate this stub for bitflags
            if self.getTypeCategory(paramtype.text) != 'bitmask':
                if param.attrib.get('optional').split(',')[0] == 'true':
                    asciidoc += 'If '
                    asciidoc += self.makeParameterName(paramname.text)
                    asciidoc += ' is not '
                    if self.paramIsArray(param) or self.paramIsPointer(param) or self.isHandleTypeDispatchable(paramtype.text):
                        asciidoc += '`NULL`'
                    elif self.getTypeCategory(paramtype.text) == 'handle':
                        asciidoc += 'sname:VK_NULL_HANDLE'
                    else:
                        asciidoc += '`0`'

                    asciidoc += ', '

        return asciidoc

    #
    # Make the generic asciidoc line chunk portion used for all parameters.
    # May return an empty string if nothing to validate.
    def createValidationLineForParameterIntroChunk(self, param, params, typetext):
        asciidoc = ''
        paramname = param.find('name')
        paramtype = param.find('type')

        asciidoc += self.makeAsciiDocPreChunk(param, params)

        asciidoc += self.makeParameterName(paramname.text)
        asciidoc += ' must: be '

        if self.paramIsArray(param):
            # Arrays. These are hard to get right, apparently

            lengths = param.attrib.get('len').split(',')

            if (lengths[0]) == 'null-terminated':
                asciidoc += 'a null-terminated '
            elif (lengths[0]) == '1':
                asciidoc += 'a pointer to '
            else:
                asciidoc += 'a pointer to an array of '

                # Handle equations, which are currently denoted with latex
                if 'latexmath:' in lengths[0]:
                    asciidoc += lengths[0]
                else:
                    asciidoc += self.makeParameterName(lengths[0])
                asciidoc += ' '

            for length in lengths[1:]:
                if (length) == 'null-terminated': # This should always be the last thing. If it ever isn't for some bizarre reason, then this will need some massaging.
                    asciidoc += 'null-terminated '
                elif (length) == '1':
                    asciidoc += 'pointers to '
                else:
                    asciidoc += 'pointers to arrays of '
                    # Handle equations, which are currently denoted with latex
                    if 'latex:' in length:
                        asciidoc += length
                    else:
                        asciidoc += self.makeParameterName(length)
                    asciidoc += ' '

            # Void pointers don't actually point at anything - remove the word "to"
            if paramtype.text == 'void':
                if lengths[-1] == '1':
                    if len(lengths) > 1:
                        asciidoc = asciidoc[:-5]    # Take care of the extra s added by the post array chunk function. #HACK#
                    else:
                        asciidoc = asciidoc[:-4]
                else:
                    # An array of void values is a byte array.
                    asciidoc += 'byte'

            elif paramtype.text == 'char':
                # A null terminated array of chars is a string
                if lengths[-1] == 'null-terminated':
                    asciidoc += 'string'
                else:
                    # Else it's just a bunch of chars
                    asciidoc += 'char value'
            elif param.text is not None:
                # If a value is "const" that means it won't get modified, so it must be valid going into the function.
                if 'const' in param.text:
                    typecategory = self.getTypeCategory(paramtype.text)
                    if (typecategory != 'struct' and typecategory != 'union' and typecategory != 'basetype' and typecategory is not None) or not self.isStructAlwaysValid(paramtype.text):
                        asciidoc += 'valid '

            asciidoc += typetext

            # pluralize
            if len(lengths) > 1 or (lengths[0] != '1' and lengths[0] != 'null-terminated'):
                asciidoc += 's'

        elif self.paramIsPointer(param):
            # Handle pointers - which are really special case arrays (i.e. they don't have a length)
            pointercount = paramtype.tail.count('*')

            # Could be multi-level pointers (e.g. ppData - pointer to a pointer). Handle that.
            for i in range(0, pointercount):
                asciidoc += 'a pointer to '

            if paramtype.text == 'void':
                # If there's only one pointer, it's optional, and it doesn't point at anything in particular - we don't need any language.
                if pointercount == 1 and param.attrib.get('optional') is not None:
                    return '' # early return
                else:
                    # Pointer to nothing in particular - delete the " to " portion
                    asciidoc = asciidoc[:-4]
            else:
                # Add an article for English semantic win
                asciidoc += 'a '

            # If a value is "const" that means it won't get modified, so it must be valid going into the function.
            if param.text is not None and paramtype.text != 'void':
                if 'const' in param.text:
                    asciidoc += 'valid '

            asciidoc += typetext

        else:
            # Non-pointer, non-optional things must be valid
            asciidoc += 'a valid '
            asciidoc += typetext

        if asciidoc != '':
            asciidoc += '\n'

            # Add additional line for non-optional bitmasks
            if self.getTypeCategory(paramtype.text) == 'bitmask':
                if param.attrib.get('optional') is None:
                    asciidoc += '* '
                    if self.paramIsArray(param):
                        asciidoc += 'Each element of '
                    asciidoc += 'pname:'
                    asciidoc += paramname.text
                    asciidoc += ' mustnot: be `0`'
                    asciidoc += '\n'

        return asciidoc

    def makeAsciiDocLineForParameter(self, param, params, typetext):
        if param.attrib.get('noautovalidity') is not None:
            return ''
        asciidoc  = self.createValidationLineForParameterIntroChunk(param, params, typetext)

        return asciidoc

    # Try to do check if a structure is always considered valid (i.e. there's no rules to its acceptance)
    def isStructAlwaysValid(self, structname):

        struct = self.registry.find("types/type[@name='" + structname + "']")

        params = struct.findall('member')
        validity = struct.find('validity')

        if validity is not None:
            return False

        for param in params:
            paramname = param.find('name')
            paramtype = param.find('type')
            typecategory = self.getTypeCategory(paramtype.text)

            if paramname.text == 'pNext':
                return False

            if paramname.text == 'sType':
                return False

            if paramtype.text == 'void' or paramtype.text == 'char' or self.paramIsArray(param) or self.paramIsPointer(param):
                if self.makeAsciiDocLineForParameter(param, params, '') != '':
                    return False
            elif typecategory == 'handle' or typecategory == 'enum' or typecategory == 'bitmask' or param.attrib.get('returnedonly') == 'true':
                return False
            elif typecategory == 'struct' or typecategory == 'union':
                if self.isStructAlwaysValid(paramtype.text) is False:
                    return False

        return True

    #
    # Make an entire asciidoc line for a given parameter
    def createValidationLineForParameter(self, param, params, typecategory):
        asciidoc = ''
        paramname = param.find('name')
        paramtype = param.find('type')

        if paramtype.text == 'void' or paramtype.text == 'char':
            # Chars and void are special cases - needs care inside the generator functions
            # A null-terminated char array is a string, else it's chars.
            # An array of void values is a byte array, a void pointer is just a pointer to nothing in particular
            asciidoc += self.makeAsciiDocLineForParameter(param, params, '')
        elif typecategory == 'bitmask':
            bitsname = paramtype.text.replace('Flags', 'FlagBits')
            if self.registry.find("enums[@name='" + bitsname + "']") is None:
                asciidoc += '* '
                asciidoc += self.makeParameterName(paramname.text)
                asciidoc += ' must: be `0`'
                asciidoc += '\n'
            else:
                if self.paramIsArray(param):
                    asciidoc += self.makeAsciiDocLineForParameter(param, params, 'combinations of ' + self.makeEnumerationName(bitsname) + ' value')
                else:
                    asciidoc += self.makeAsciiDocLineForParameter(param, params, 'combination of ' + self.makeEnumerationName(bitsname) + ' values')
        elif typecategory == 'handle':
            asciidoc += self.makeAsciiDocLineForParameter(param, params, self.makeStructName(paramtype.text) + ' handle')
        elif typecategory == 'enum':
            asciidoc += self.makeAsciiDocLineForParameter(param, params, self.makeEnumerationName(paramtype.text) + ' value')
        elif typecategory == 'struct':
            if (self.paramIsArray(param) or self.paramIsPointer(param)) or not self.isStructAlwaysValid(paramtype.text):
                asciidoc += self.makeAsciiDocLineForParameter(param, params, self.makeStructName(paramtype.text) + ' structure')
        elif typecategory == 'union':
            if (self.paramIsArray(param) or self.paramIsPointer(param)) or not self.isStructAlwaysValid(paramtype.text):
                asciidoc += self.makeAsciiDocLineForParameter(param, params, self.makeStructName(paramtype.text) + ' union')
        elif self.paramIsArray(param) or self.paramIsPointer(param):
            asciidoc += self.makeAsciiDocLineForParameter(param, params, self.makeBaseTypeName(paramtype.text) + ' value')

        return asciidoc

    #
    # Make an asciidoc validity entry for a handle's parent object
    def makeAsciiDocHandleParent(self, param, params):
        asciidoc = ''
        paramname = param.find('name')
        paramtype = param.find('type')

        # Deal with handle parents
        handleparent = self.getHandleParent(paramtype.text)
        if handleparent is not None:
            parentreference = None
            for otherparam in params:
                if otherparam.find('type').text == handleparent:
                    parentreference = otherparam.find('name').text
            if parentreference is not None:
                asciidoc += '* '

                if self.isHandleOptional(param, params):
                    if self.paramIsArray(param):
                        asciidoc += 'Each element of '
                        asciidoc += self.makeParameterName(paramname.text)
                        asciidoc += ' that is a valid handle'
                    else:
                        asciidoc += 'If '
                        asciidoc += self.makeParameterName(paramname.text)
                        asciidoc += ' is a valid handle, it'
                else:
                    if self.paramIsArray(param):
                        asciidoc += 'Each element of '
                    asciidoc += self.makeParameterName(paramname.text)
                asciidoc += ' must: have been created, allocated or retrieved from '
                asciidoc += self.makeParameterName(parentreference)

                asciidoc += '\n'
        return asciidoc

    #
    # Generate an asciidoc validity line for the sType value of a struct
    def makeStructureType(self, blockname, param):
        asciidoc = '* '
        paramname = param.find('name')
        paramtype = param.find('type')

        asciidoc += self.makeParameterName(paramname.text)
        asciidoc += ' must: be '

        structuretype = ''
        for elem in re.findall(r'(([A-Z][a-z]+)|([A-Z][A-Z]+))', blockname):
            if elem[0] == 'Vk':
                structuretype += 'VK_STRUCTURE_TYPE_'
            else:
                structuretype += elem[0].upper()
                structuretype += '_'

        asciidoc += self.makeEnumerantName(structuretype[:-1])
        asciidoc += '\n'

        return asciidoc

    #
    # Generate an asciidoc validity line for the pNext value of a struct
    def makeStructureExtensionPointer(self, param):
        asciidoc = '* '
        paramname = param.find('name')
        paramtype = param.find('type')

        asciidoc += self.makeParameterName(paramname.text)

        validextensionstructs = param.attrib.get('validextensionstructs')
        if validextensionstructs is None:
            asciidoc += ' must: be `NULL`'
        else:
            extensionstructs = validextensionstructs.split(',')
            asciidoc += ' must: point to one of ' + extensionstructs[:-1].join(', ') + ' or ' + extensionstructs[-1] + 'if the extension that introduced them is enabled '

        asciidoc += '\n'

        return asciidoc

    #
    # Generate all the valid usage information for a given struct or command
    def makeValidUsageStatements(self, cmd, blockname, params, usages):
        # Start the asciidoc block for this
        asciidoc = ''

        handles = []
        anyparentedhandlesoptional = False
        parentdictionary = {}
        arraylengths = set()
        for param in params:
            paramname = param.find('name')
            paramtype = param.find('type')

            # Get the type's category
            typecategory = self.getTypeCategory(paramtype.text)

            # Generate language to independently validate a parameter
            if paramtype.text == 'VkStructureType' and paramname.text == 'sType':
                asciidoc += self.makeStructureType(blockname, param)
            elif paramtype.text == 'void' and paramname.text == 'pNext':
                asciidoc += self.makeStructureExtensionPointer(param)
            else:
                asciidoc += self.createValidationLineForParameter(param, params, typecategory)

            # Ensure that any parenting is properly validated, and list that a handle was found
            if typecategory == 'handle':
                # Don't detect a parent for return values!
                if not self.paramIsPointer(param) or (param.text is not None and 'const' in param.text):
                    parent = self.getHandleParent(paramtype.text)
                    if parent is not None:
                        handles.append(param)

                        # If any param is optional, it affects the output
                        if self.isHandleOptional(param, params):
                            anyparentedhandlesoptional = True

                        # Find the first dispatchable parent
                        ancestor = parent
                        while ancestor is not None and not self.isHandleTypeDispatchable(ancestor):
                            ancestor = self.getHandleParent(ancestor)

                        # If one was found, add this parameter to the parent dictionary
                        if ancestor is not None:
                            if ancestor not in parentdictionary:
                                parentdictionary[ancestor] = []

                            if self.paramIsArray(param):
                                parentdictionary[ancestor].append('the elements of ' + self.makeParameterName(paramname.text))
                            else:
                                parentdictionary[ancestor].append(self.makeParameterName(paramname.text))

            # Get the array length for this parameter
            arraylength = param.attrib.get('len')
            if arraylength is not None:
                for onelength in arraylength.split(','):
                    arraylengths.add(onelength)

        # For any vkQueue* functions, there might be queue type data
        if 'vkQueue' in blockname:
            # The queue type must be valid
            queuetypes = cmd.attrib.get('queues')
            if queuetypes is not None:
                queuebits = []
                for queuetype in re.findall(r'([^,]+)', queuetypes):
                    queuebits.append(queuetype.replace('_',' '))

                asciidoc += '* '
                asciidoc += 'The pname:queue must: support '
                if len(queuebits) == 1:
                    asciidoc += queuebits[0]
                else:
                    asciidoc += (', ').join(queuebits[:-1])
                    asciidoc += ' or '
                    asciidoc += queuebits[-1]
                asciidoc += ' operations'
                asciidoc += '\n'

        if 'vkCmd' in blockname:
            # The commandBuffer parameter must be being recorded
            asciidoc += '* '
            asciidoc += 'pname:commandBuffer must: be in the recording state'
            asciidoc += '\n'

            # The queue type must be valid
            queuetypes = cmd.attrib.get('queues')
            queuebits = []
            for queuetype in re.findall(r'([^,]+)', queuetypes):
                queuebits.append(queuetype.replace('_',' '))

            asciidoc += '* '
            asciidoc += 'The sname:VkCommandPool that pname:commandBuffer was allocated from must: support '
            if len(queuebits) == 1:
                asciidoc += queuebits[0]
            else:
                asciidoc += (', ').join(queuebits[:-1])
                asciidoc += ' or '
                asciidoc += queuebits[-1]
            asciidoc += ' operations'
            asciidoc += '\n'

            # Must be called inside/outside a renderpass appropriately
            renderpass = cmd.attrib.get('renderpass')

            if renderpass != 'both':
                asciidoc += '* This command must: only be called '
                asciidoc += renderpass
                asciidoc += ' of a render pass instance'
                asciidoc += '\n'

            # Must be in the right level command buffer
            cmdbufferlevel = cmd.attrib.get('cmdbufferlevel')

            if cmdbufferlevel != 'primary,secondary':
                asciidoc += '* pname:commandBuffer must: be a '
                asciidoc += cmdbufferlevel
                asciidoc += ' sname:VkCommandBuffer'
                asciidoc += '\n'

        # Any non-optional arraylengths should specify they must be greater than 0
        for param in params:
            paramname = param.find('name')

            for arraylength in arraylengths:
                if paramname.text == arraylength and param.attrib.get('optional') is None:
                    # Get all the array dependencies
                    arrays = cmd.findall("param/[@len='" + arraylength + "'][@optional='true']")

                    # Get all the optional array dependencies, including those not generating validity for some reason
                    optionalarrays = cmd.findall("param/[@len='" + arraylength + "'][@optional='true']")
                    optionalarrays.extend(cmd.findall("param/[@len='" + arraylength + "'][@noautovalidity='true']"))

                    asciidoc += '* '

                    # Allow lengths to be arbitrary if all their dependents are optional
                    if len(optionalarrays) == len(arrays) and len(optionalarrays) != 0:
                        asciidoc += 'If '
                        if len(optionalarrays) > 1:
                            asciidoc += 'any of '

                        for array in optionalarrays[:-1]:
                            asciidoc += self.makeParameterName(optionalarrays.find('name').text)
                            asciidoc += ', '

                        if len(optionalarrays) > 1:
                            asciidoc += 'and '
                            asciidoc += self.makeParameterName(optionalarrays[-1].find('name').text)
                            asciidoc += ' are '
                        else:
                            asciidoc += self.makeParameterName(optionalarrays[-1].find('name').text)
                            asciidoc += ' is '

                        asciidoc += 'not `NULL`, '

                        if self.paramIsPointer(param):
                            asciidoc += 'the value referenced by '

                    elif self.paramIsPointer(param):
                        asciidoc += 'The value referenced by '

                    asciidoc += self.makeParameterName(arraylength)
                    asciidoc += ' must: be greater than `0`'
                    asciidoc += '\n'

        # Find the parents of all objects referenced in this command
        for param in handles:
            asciidoc += self.makeAsciiDocHandleParent(param, params)

        # Find the common ancestors of objects
        noancestorscount = 0
        while noancestorscount < len(parentdictionary):
            noancestorscount = 0
            oldparentdictionary = parentdictionary.copy()
            for parent in oldparentdictionary.items():
                ancestor = self.getHandleParent(parent[0])

                while ancestor is not None and ancestor not in parentdictionary:
                    ancestor = self.getHandleParent(ancestor)

                if ancestor is not None:
                    parentdictionary[ancestor] += parentdictionary.pop(parent[0])
                else:
                    # No ancestors possible - so count it up
                    noancestorscount += 1

        # Add validation language about common ancestors
        for parent in parentdictionary.items():
            if len(parent[1]) > 1:
                parentlanguage = '* '

                parentlanguage += 'Each of '
                parentlanguage += ", ".join(parent[1][:-1])
                parentlanguage += ' and '
                parentlanguage += parent[1][-1]
                if anyparentedhandlesoptional is True:
                    parentlanguage += ' that are valid handles'
                parentlanguage += ' must: have been created, allocated or retrieved from the same '
                parentlanguage += self.makeStructName(parent[0])
                parentlanguage += '\n'

                # Capitalize and add to the main language
                asciidoc += parentlanguage

        # Add in any plain-text validation language that should be added
        for usage in usages:
            asciidoc += '* '
            asciidoc += usage
            asciidoc += '\n'

        # In case there's nothing to report, return None
        if asciidoc == '':
            return None
        # Delimit the asciidoc block
        return asciidoc

    def makeThreadSafetyBlock(self, cmd, paramtext):
        """Generate C function pointer typedef for <command> Element"""
        paramdecl = ''

        # For any vkCmd* functions, the commandBuffer parameter must be being recorded
        if cmd.find('proto/name') is not None and 'vkCmd' in cmd.find('proto/name'):
            paramdecl += '* '
            paramdecl += 'The sname:VkCommandPool that pname:commandBuffer was created from'
            paramdecl += '\n'

        # Find and add any parameters that are thread unsafe
        explicitexternsyncparams = cmd.findall(paramtext + "[@externsync]")
        if (explicitexternsyncparams is not None):
            for param in explicitexternsyncparams:
                externsyncattribs = param.attrib.get('externsync')
                paramname = param.find('name')
                for externsyncattrib in externsyncattribs.split(','):
                    paramdecl += '* '
                    paramdecl += 'Host access to '
                    if externsyncattrib == 'true':
                        if self.paramIsArray(param):
                            paramdecl += 'each member of ' + self.makeParameterName(paramname.text)
                        elif self.paramIsPointer(param):
                            paramdecl += 'the object referenced by ' + self.makeParameterName(paramname.text)
                        else:
                            paramdecl += self.makeParameterName(paramname.text)
                    else:
                        paramdecl += 'pname:'
                        paramdecl += externsyncattrib
                    paramdecl += ' must: be externally synchronized\n'

        # Find and add any "implicit" parameters that are thread unsafe
        implicitexternsyncparams = cmd.find('implicitexternsyncparams')
        if (implicitexternsyncparams is not None):
            for elem in implicitexternsyncparams:
                paramdecl += '* '
                paramdecl += 'Host access to '
                paramdecl += elem.text
                paramdecl += ' must: be externally synchronized\n'

        if (paramdecl == ''):
            return None
        else:
            return paramdecl

    def makeCommandPropertiesTableEntry(self, cmd, name):

        if 'vkCmd' in name:
            # Must be called inside/outside a renderpass appropriately
            cmdbufferlevel = cmd.attrib.get('cmdbufferlevel')
            cmdbufferlevel = (' + \n').join(cmdbufferlevel.title().split(','))

            renderpass = cmd.attrib.get('renderpass')
            renderpass = renderpass.capitalize()

            queues = cmd.attrib.get('queues')
            queues = (' + \n').join(queues.upper().split(','))

            return '|' + cmdbufferlevel + '|' + renderpass + '|' + queues
        elif 'vkQueue' in name:
            # Must be called inside/outside a renderpass appropriately

            queues = cmd.attrib.get('queues')
            if queues is None:
                queues = 'Any'
            else:
                queues = (' + \n').join(queues.upper().split(','))

            return '|-|-|' + queues

        return None

    def makeSuccessCodes(self, cmd, name):

        successcodes = cmd.attrib.get('successcodes')
        if successcodes is not None:

            successcodeentry = ''
            successcodes = successcodes.split(',')
            return '* ename:' + '\n* ename:'.join(successcodes)

        return None

    def makeErrorCodes(self, cmd, name):

        errorcodes = cmd.attrib.get('errorcodes')
        if errorcodes is not None:

            errorcodeentry = ''
            errorcodes = errorcodes.split(',')
            return '* ename:' + '\n* ename:'.join(errorcodes)

        return None

    #
    # Command generation
    def genCmd(self, cmdinfo, name):
        OutputGenerator.genCmd(self, cmdinfo, name)
        #
        # Get all the parameters
        params = cmdinfo.elem.findall('param')
        usageelements = cmdinfo.elem.findall('validity/usage')
        usages = []

        for usage in usageelements:
            usages.append(usage.text)
        for usage in cmdinfo.additionalValidity:
            usages.append(usage.text)
        for usage in cmdinfo.removedValidity:
            usages.remove(usage.text)
                
        validity = self.makeValidUsageStatements(cmdinfo.elem, name, params, usages)
        threadsafety = self.makeThreadSafetyBlock(cmdinfo.elem, 'param')
        commandpropertiesentry = self.makeCommandPropertiesTableEntry(cmdinfo.elem, name)
        successcodes = self.makeSuccessCodes(cmdinfo.elem, name)
        errorcodes = self.makeErrorCodes(cmdinfo.elem, name)

        self.writeInclude('validity/protos', name, validity, threadsafety, commandpropertiesentry, successcodes, errorcodes)

    #
    # Struct Generation
    def genStruct(self, typeinfo, typename):
        OutputGenerator.genStruct(self, typeinfo, typename)

        # Anything that's only ever returned can't be set by the user, so shouldn't have any validity information.
        if typeinfo.elem.attrib.get('returnedonly') is None:
            params = typeinfo.elem.findall('member')

            usageelements = typeinfo.elem.findall('validity/usage')
            usages = []

            for usage in usageelements:
                usages.append(usage.text)
            for usage in typeinfo.additionalValidity:
                usages.append(usage.text)
            for usage in typeinfo.removedValidity:
                usages.remove(usage.text)
            
            validity = self.makeValidUsageStatements(typeinfo.elem, typename, params, usages)
            threadsafety = self.makeThreadSafetyBlock(typeinfo.elem, 'member')

            self.writeInclude('validity/structs', typename, validity, threadsafety, None, None, None)
        else:
            # Still generate files for return only structs, in case this state changes later
            self.writeInclude('validity/structs', typename, None, None, None, None, None)

    #
    # Type Generation
    def genType(self, typeinfo, typename):
        OutputGenerator.genType(self, typeinfo, typename)

        category = typeinfo.elem.get('category')
        if (category == 'struct' or category == 'union'):
            self.genStruct(typeinfo, typename)

# HostSynchronizationOutputGenerator - subclass of OutputGenerator.
# Generates AsciiDoc includes of the externsync parameter table for the
# fundamentals chapter of the Vulkan specification. Similar to
# DocOutputGenerator.
#
# ---- methods ----
# HostSynchronizationOutputGenerator(errFile, warnFile, diagFile) - args as for
#   OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# genCmd(cmdinfo)
class HostSynchronizationOutputGenerator(OutputGenerator):
    # Generate Host Synchronized Parameters in a table at the top of the spec
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)

    threadsafety = {'parameters': '', 'parameterlists': '', 'implicit': ''}

    def makeParameterName(self, name):
        return 'pname:' + name

    def makeFLink(self, name):
        return 'flink:' + name

    #
    # Generate an include file
    #
    # directory - subdirectory to put file in
    # basename - base name of the file
    # contents - contents of the file (Asciidoc boilerplate aside)
    def writeInclude(self):

        if self.threadsafety['parameters'] is not None:
            # Create file
            filename = self.genOpts.genDirectory + '/' + self.genOpts.filename + '/parameters.txt'
            self.logMsg('diag', '# Generating include file:', filename)
            fp = open(filename, 'w')

            # Host Synchronization
            write('// WARNING: DO NOT MODIFY! This file is automatically generated from the vk.xml registry', file=fp)
            write('.Externally Synchronized Parameters', file=fp)
            write('*' * 80, file=fp)
            write(self.threadsafety['parameters'], file=fp, end='')
            write('*' * 80, file=fp)
            write('', file=fp)

        if self.threadsafety['parameterlists'] is not None:
            # Create file
            filename = self.genOpts.genDirectory + '/' + self.genOpts.filename + '/parameterlists.txt'
            self.logMsg('diag', '# Generating include file:', filename)
            fp = open(filename, 'w')

            # Host Synchronization
            write('// WARNING: DO NOT MODIFY! This file is automatically generated from the vk.xml registry', file=fp)
            write('.Externally Synchronized Parameter Lists', file=fp)
            write('*' * 80, file=fp)
            write(self.threadsafety['parameterlists'], file=fp, end='')
            write('*' * 80, file=fp)
            write('', file=fp)

        if self.threadsafety['implicit'] is not None:
            # Create file
            filename = self.genOpts.genDirectory + '/' + self.genOpts.filename + '/implicit.txt'
            self.logMsg('diag', '# Generating include file:', filename)
            fp = open(filename, 'w')

            # Host Synchronization
            write('// WARNING: DO NOT MODIFY! This file is automatically generated from the vk.xml registry', file=fp)
            write('.Implicit Externally Synchronized Parameters', file=fp)
            write('*' * 80, file=fp)
            write(self.threadsafety['implicit'], file=fp, end='')
            write('*' * 80, file=fp)
            write('', file=fp)

        fp.close()

    #
    # Check if the parameter passed in is a pointer to an array
    def paramIsArray(self, param):
        return param.attrib.get('len') is not None

    # Check if the parameter passed in is a pointer
    def paramIsPointer(self, param):
        ispointer = False
        paramtype = param.find('type')
        if paramtype.tail is not None and '*' in paramtype.tail:
            ispointer = True

        return ispointer

    # Turn the "name[].member[]" notation into plain English.
    def makeThreadDereferenceHumanReadable(self, dereference):
        matches = re.findall(r"[\w]+[^\w]*",dereference)
        stringval = ''
        for match in reversed(matches):
            if '->' in match or '.' in match:
                stringval += 'member of '
            if '[]' in match:
                stringval += 'each element of '

            stringval += 'the '
            stringval += self.makeParameterName(re.findall(r"[\w]+",match)[0])
            stringval += ' '

        stringval += 'parameter'

        return stringval[0].upper() + stringval[1:]

    def makeThreadSafetyBlocks(self, cmd, paramtext):
        protoname = cmd.find('proto/name').text

        # Find and add any parameters that are thread unsafe
        explicitexternsyncparams = cmd.findall(paramtext + "[@externsync]")
        if (explicitexternsyncparams is not None):
            for param in explicitexternsyncparams:
                externsyncattribs = param.attrib.get('externsync')
                paramname = param.find('name')
                for externsyncattrib in externsyncattribs.split(','):

                    tempstring = '* '
                    if externsyncattrib == 'true':
                        if self.paramIsArray(param):
                            tempstring += 'Each element of the '
                        elif self.paramIsPointer(param):
                            tempstring += 'The object referenced by the '
                        else:
                            tempstring += 'The '

                        tempstring += self.makeParameterName(paramname.text)
                        tempstring += ' parameter'

                    else:
                        tempstring += self.makeThreadDereferenceHumanReadable(externsyncattrib)

                    tempstring += ' in '
                    tempstring += self.makeFLink(protoname)
                    tempstring += '\n'


                    if ' element of ' in tempstring:
                        self.threadsafety['parameterlists'] += tempstring
                    else:
                        self.threadsafety['parameters'] += tempstring


        # Find and add any "implicit" parameters that are thread unsafe
        implicitexternsyncparams = cmd.find('implicitexternsyncparams')
        if (implicitexternsyncparams is not None):
            for elem in implicitexternsyncparams:
                self.threadsafety['implicit'] += '* '
                self.threadsafety['implicit'] += elem.text[0].upper()
                self.threadsafety['implicit'] += elem.text[1:]
                self.threadsafety['implicit'] += ' in '
                self.threadsafety['implicit'] += self.makeFLink(protoname)
                self.threadsafety['implicit'] += '\n'


        # For any vkCmd* functions, the commandBuffer parameter must be being recorded
        if protoname is not None and 'vkCmd' in protoname:
            self.threadsafety['implicit'] += '* '
            self.threadsafety['implicit'] += 'The sname:VkCommandPool that pname:commandBuffer was allocated from, in '
            self.threadsafety['implicit'] += self.makeFLink(protoname)

            self.threadsafety['implicit'] += '\n'

    #
    # Command generation
    def genCmd(self, cmdinfo, name):
        OutputGenerator.genCmd(self, cmdinfo, name)
        #
        # Get all thh parameters
        params = cmdinfo.elem.findall('param')
        usages = cmdinfo.elem.findall('validity/usage')

        self.makeThreadSafetyBlocks(cmdinfo.elem, 'param')

        self.writeInclude()
