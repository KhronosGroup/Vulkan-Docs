#!/usr/bin/python3
#
# Copyright (c) 2016-2018 The Khronos Group Inc.
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

# Utility functions for automatic ref page generation

import io,os,re,sys

# global errFile, warnFile, diagFile

errFile = sys.stderr
warnFile = sys.stdout
diagFile = None
logSourcefile = None
logProcname = None
logLine = None

# Remove \' escape sequences in a string (refpage description)
def unescapeQuotes(str):
    return str.replace('\\\'', '\'')

def write(*args, **kwargs ):
    file = kwargs.pop('file',sys.stdout)
    end = kwargs.pop('end','\n')
    file.write(' '.join([str(arg) for arg in args]))
    file.write(end)

# Metadata which may be printed (if not None) for diagnostic messages
def setLogSourcefile(filename):
    global logSourcefile
    logSourcefile = filename

def setLogProcname(procname):
    global logProcname
    logProcname = procname

def setLogLine(line):
    global logLine
    logLine = line

# Generate prefix for a diagnostic line using metadata and severity
def logHeader(severity):
    global logSourcefile, logProcname, logLine

    msg = severity + ': '
    if logProcname:
        msg = msg + ' in ' + logProcname
    if logSourcefile:
        msg = msg + ' for ' + logSourcefile
    if logLine:
        msg = msg + ' line ' + str(logLine)
    return msg + ' '

# Set the file handle to log either or both warnings and diagnostics to.
# setDiag and setWarn are True if the corresponding handle is to be set.
# filename is None for no logging, '-' for stdout, or a pathname.
def setLogFile(setDiag, setWarn, filename):
    global diagFile, warnFile

    if filename == None:
        return
    elif filename == '-':
        fp = sys.stdout
    else:
        fp = open(filename, 'w', encoding='utf-8')

    if setDiag:
        diagFile = fp
    if setWarn:
        warnFile = fp

def logDiag(*args, **kwargs):
    file = kwargs.pop('file', diagFile)
    end = kwargs.pop('end','\n')
    if file != None:
        file.write(logHeader('DIAG') + ' '.join([str(arg) for arg in args]))
        file.write(end)

def logWarn(*args, **kwargs):
    file = kwargs.pop('file', warnFile)
    end = kwargs.pop('end','\n')
    if file != None:
        file.write(logHeader('WARN') + ' '.join([str(arg) for arg in args]))
        file.write(end)

def logErr(*args, **kwargs):
    file = kwargs.pop('file', errFile)
    end = kwargs.pop('end','\n')

    strfile = io.StringIO()
    strfile.write(logHeader('ERROR') + ' '.join([str(arg) for arg in args]))
    strfile.write(end)

    if file != None:
        file.write(strfile.getvalue())
    raise UserWarning(strfile.getvalue())

# Return True if s is nothing but white space, False otherwise
def isempty(s):
    return len(''.join(s.split())) == 0

# pageInfo - information about a ref page relative to the file it's
# extracted from.
#
#   extractPage - True if page should be extracted
#   Warning - string warning if page is suboptimal or can't be generated
#   embed - False or the name of the ref page this include is imbedded within
#
#   type - 'structs', 'protos', 'funcpointers', 'flags', 'enums'
#   name - struct/proto/enumerant/etc. name
#   desc - short description of ref page
#   begin - index of first line of the page (heuristic or // refBegin)
#   include - index of include:: line defining the page
#   param - index of first line of parameter/member definitions
#   body - index of first line of body text
#   validity - index of validity include
#   end - index of last line of the page (heuristic validity include, or // refEnd)
#   refs - cross-references on // refEnd line, if supplied
class pageInfo:
    def __init__(self):
        self.extractPage = True
        self.Warning  = None
        self.embed    = False

        self.type     = None
        self.name     = None
        self.desc     = None
        self.begin    = None
        self.include  = None
        self.param    = None
        self.body     = None
        self.validity = None
        self.end      = None
        self.refs     = ''

# Print a single field of a pageInfo struct, possibly None
#   desc - string description of field
#   line - field value or None
#   file - indexed by line
def printPageInfoField(desc, line, file):
    if line != None:
        logDiag(desc + ':', line + 1, '\t-> ', file[line], end='')
    else:
        logDiag(desc + ':', line)

# Print out fields of a pageInfo struct
#   pi - pageInfo
#   file - indexed by pageInfo
def printPageInfo(pi, file):
    logDiag('TYPE:   ', pi.type)
    logDiag('NAME:   ', pi.name)
    logDiag('WARNING:', pi.Warning)
    logDiag('EXTRACT:', pi.extractPage)
    logDiag('EMBED:  ', pi.embed)
    logDiag('DESC:   ', pi.desc)
    printPageInfoField('BEGIN   ', pi.begin,    file)
    printPageInfoField('INCLUDE ', pi.include,  file)
    printPageInfoField('PARAM   ', pi.param,    file)
    printPageInfoField('BODY    ', pi.body,     file)
    printPageInfoField('VALIDITY', pi.validity, file)
    printPageInfoField('END     ', pi.end,      file)
    logDiag('REFS: "' + pi.refs + '"')

# Go back one paragraph from the specified line and return the line number
# of the first line of that paragraph.
#
# Paragraphs are delimited by blank lines. It is assumed that the
# current line is the first line of a paragraph.
#   file is an array of strings
#   line is the starting point (zero-based)
def prevPara(file, line):
    # Skip over current paragraph
    while (line >= 0 and not isempty(file[line])):
        line = line - 1
    # Skip over white space
    while (line >= 0 and isempty(file[line])):
        line = line - 1
    # Skip to first line of previous paragraph
    while (line >= 1 and not isempty(file[line-1])):
        line = line - 1
    return line

# Go forward one paragraph from the specified line and return the line
# number of the first line of that paragraph.
#
# Paragraphs are delimited by blank lines. It is assumed that the
# current line is standalone (which is bogus)
#   file is an array of strings
#   line is the starting point (zero-based)
def nextPara(file, line):
    maxLine = len(file) - 1
    # Skip over current paragraph
    while (line != maxLine and not isempty(file[line])):
        line = line + 1
    # Skip over white space
    while (line != maxLine and isempty(file[line])):
        line = line + 1
    return line

# Return (creating if needed) the pageInfo entry in pageMap for name
def lookupPage(pageMap, name):
    if not name in pageMap.keys():
        pi = pageInfo()
        pi.name = name
        pageMap[name] = pi
    else:
        pi = pageMap[name]
    return pi

# Load a file into a list of strings. Return the list or None on failure
def loadFile(filename):
    try:
        fp = open(filename, 'r', encoding='utf-8')
    except:
        logWarn('Cannot open file', filename, ':', sys.exc_info()[0])
        return None

    file = fp.readlines()
    fp.close()

    return file

# Clamp a line number to be in the range [minline,maxline].
# If the line number is None, just return it.
# If minline is None, don't clamp to that value.
def clampToBlock(line, minline, maxline):
    if line == None:
        return line
    elif minline and line < minline:
        return minline
    elif line > maxline:
        return maxline
    else:
        return line

# Fill in missing fields in pageInfo structures, to the extent they can be
# inferred.
#   pageMap - dictionary of pageInfo structures
#   specFile - filename
#   file - list of strings making up the file, indexed by pageInfo
def fixupRefs(pageMap, specFile, file):
    # All potential ref pages are now in pageMap. Process them to
    # identify actual page start/end/description boundaries, if
    # not already determined from the text.
    for name in sorted(pageMap.keys()):
        pi = pageMap[name]

        # # If nothing is found but an include line with no begin, validity,
        # # or end, this is not intended as a ref page (yet). Set the begin
        # # line to the include line, so autogeneration can at least
        # # pull the include out, but mark it not to be extracted.
        # # Examples include the host sync table includes in
        # # chapters/fundamentals.txt and the table of Vk*Flag types in
        # # appendices/boilerplate.txt.
        # if pi.begin == None and pi.validity == None and pi.end == None:
        #     pi.begin = pi.include
        #     pi.extractPage = False
        #     pi.Warning = 'No begin, validity, or end lines identified'
        #     continue

        # Using open block delimiters, ref pages must *always* have a
        # defined begin and end. If either is undefined, that's fatal.
        if pi.begin == None:
            pi.extractPage = False
            pi.Warning = 'Can\'t identify begin of ref page open block'
            continue

        if pi.end == None:
            pi.extractPage = False
            pi.Warning = 'Can\'t identify end of ref page open block'
            continue

        # If there's no description of the page, infer one from the type
        if pi.desc == None:
            if pi.type != None:
                # pi.desc = pi.type[0:len(pi.type)-1] + ' (no short description available)'
                pi.Warning = 'No short description available; could infer from the type and name'
                True
            else:
                pi.extractPage = False
                pi.Warning = 'No short description available, cannot infer from the type'
                continue

        # Try to determine where the parameter and body sections of the page
        # begin. funcpointer, proto, and struct pages infer the location of
        # the parameter and body sections. Other pages infer the location of
        # the body, but have no parameter sections.
        if pi.include != None:
            if pi.type in ['funcpointers', 'protos', 'structs']:
                pi.param = nextPara(file, pi.include)
                if pi.body == None:
                    pi.body = nextPara(file, pi.param)
            else:
                if pi.body == None:
                    pi.body = nextPara(file, pi.include)
        else:
            pi.Warning = 'Page does not have an API definition include::'

        # It's possible for the inferred param and body lines to run past
        # the end of block, if, for example, there is no parameter section.
        pi.param = clampToBlock(pi.param, pi.include, pi.end)
        pi.body = clampToBlock(pi.body, pi.param, pi.end)

        # We can get to this point with .include, .param, and .validity
        # all being None, indicating those sections weren't found.

        logDiag('fixupRefs: after processing,', pi.name, 'looks like:')
        printPageInfo(pi, file)

    # Now that all the valid pages have been found, try to make some
    # inferences about invalid pages.
    #
    # If a reference without a .end is entirely inside a valid reference,
    # then it's intentionally embedded - may want to create an indirect
    # page that links into the embedding page. This is done by a very
    # inefficient double loop, but the loop depth is small.
    for name in sorted(pageMap.keys()):
        pi = pageMap[name]

        if pi.end == None:
            for embedName in sorted(pageMap.keys()):
                logDiag('fixupRefs: comparing', pi.name, 'to', embedName)
                embed = pageMap[embedName]
                # Don't check embeddings which are themselves invalid
                if not embed.extractPage:
                    logDiag('Skipping check for embedding in:', embed.name)
                    continue
                if embed.begin == None or embed.end == None:
                    logDiag('fixupRefs:', name + ':',
                            'can\'t compare to unanchored ref:', embed.name,
                            'in', specFile, 'at line', pi.include )
                    printPageInfo(pi, file)
                    printPageInfo(embed, file)
                # If an embed is found, change the error to a warning
                elif (pi.include != None and pi.include >= embed.begin and
                      pi.include <= embed.end):
                    logDiag('fixupRefs: Found embed for:', name,
                            'inside:', embedName,
                            'in', specFile, 'at line', pi.include )
                    pi.embed = embed.name
                    pi.Warning = 'Embedded in definition for ' + embed.name
                    break
                else:
                    logDiag('fixupRefs: No embed match for:', name,
                            'inside:', embedName, 'in', specFile,
                            'at line', pi.include)


# Patterns used to recognize interesting lines in an asciidoc source file.
# These patterns are only compiled once.
includePat = re.compile('^include::(\.\./)+api/+(?P<type>\w+)/(?P<name>\w+).txt\[\]')
endifPat   = re.compile('^endif::(?P<condition>[\w_+,]+)\[\]')
validPat   = re.compile('^include::(\.\./)+validity/(?P<type>\w+)/(?P<name>\w+).txt\[\]')
beginPat   = re.compile('^\[open,(?P<attribs>refpage=.*)\]')
# attribute key/value pairs of an open block
attribStr  = "([a-z]+)='([^'\\\\]*(?:\\\\.[^'\\\\]*)*)'"
attribPat  = re.compile(attribStr)
bodyPat    = re.compile('^// *refBody')

# Identify reference pages in a list of strings, returning a dictionary of
# pageInfo entries for each one found, or None on failure.
def findRefs(file, filename):
    setLogSourcefile(filename)
    setLogProcname('findRefs')

    # To reliably detect the open blocks around reference pages, we must
    # first detect the '[open,refpage=...]' markup delimiting the block;
    # skip past the '--' block delimiter on the next line; and identify the
    # '--' block delimiter closing the page.
    # This can't be done solely with pattern matching, and requires state to
    # track 'inside/outside block'.
    # When looking for open blocks, possible states are:
    #   'outside' - outside a block
    #   'start' - have found the '[open...]' line
    #   'inside' - have found the following '--' line
    openBlockState = 'outside'

    # This is a dictionary of interesting line numbers and strings related
    # to a Vulkan API name
    pageMap = {}

    numLines = len(file)
    line = 0

    # Track the pageInfo object corresponding to the current open block
    pi = None

    while (line < numLines):
        setLogLine(line)

        # Only one of the patterns can possibly match. Add it to
        # the dictionary for that name.

        # [open,refpage=...] starting a refpage block
        matches = beginPat.search(file[line])
        if matches != None:
            logDiag('Matched open block pattern')
            attribs = matches.group('attribs')

            openBlockState = 'start'

            # Parse the block attributes
            matches = attribPat.findall(attribs)

            # Extract each attribute
            name = None
            desc = None
            type = None
            xrefs = None

            for (key,value) in matches:
                logDiag('got attribute', key, '=', value)
                if key == 'refpage':
                    name = value
                elif key == 'desc':
                    desc = unescapeQuotes(value)
                elif key == 'type':
                    type = value
                elif key == 'xrefs':
                    xrefs = value
                else:
                    logWarn('unknown open block attribute:', key)

            if name == None or desc == None or type == None:
                logWarn('missing one or more required open block attributes:'
                        'refpage, desc, or type')
                # Leave pi == None so open block delimiters are ignored
            else:
                pi = lookupPage(pageMap, name)
                pi.desc = desc
                # Must match later type definitions in interface/validity includes
                pi.type = type
                if xrefs:
                    pi.refs = xrefs
                logDiag('open block for', name, 'added DESC =', desc,
                        'TYPE =', type, 'XREFS =', xrefs)

            line = line + 1
            continue

        # '--' starting or ending and open block
        if file[line].rstrip() == '--':
            if openBlockState == 'outside':
                # Only refpage open blocks should use -- delimiters
                logWarn('Unexpected double-dash block delimiters')
            elif openBlockState == 'start':
                # -- delimiter following [open,refpage=...]
                openBlockState = 'inside'

                if pi == None:
                    logWarn('no pageInfo available for opening -- delimiter')
                else:
                    pi.begin = line + 1
                    logDiag('opening -- delimiter: added BEGIN =', pi.begin)
            elif openBlockState == 'inside':
                # -- delimiter ending an open block
                if pi == None:
                    logWarn('no pageInfo available for closing -- delimiter')
                else:
                    pi.end = line - 1
                    logDiag('closing -- delimiter: added END =', pi.end)

                openBlockState = 'outside'
                pi = None
            else:
                logWarn('unknown openBlockState:', openBlockState)

            line = line + 1
            continue

        matches = validPat.search(file[line])
        if matches != None:
            logDiag('Matched validity pattern')
            type = matches.group('type')
            name = matches.group('name')

            if pi != None:
                if pi.type and type != pi.type:
                    logWarn('ERROR: pageMap[' + name + '] type:',
                            pi.type, 'does not match type:', type)
                pi.type = type
                pi.validity = line
                logDiag('added TYPE =', pi.type, 'VALIDITY =', pi.validity)
            else:
                logWarn('validity include:: line NOT inside block')

            line = line + 1
            continue

        matches = includePat.search(file[line])
        if matches != None:
            logDiag('Matched include pattern')
            type = matches.group('type')
            name = matches.group('name')
            if pi != None:
                if pi.include != None:
                    logDiag('found multiple includes for this block')
                if pi.type and type != pi.type:
                    logWarn('ERROR: pageMap[' + name + '] type:',
                            pi.type, 'does not match type:', type)
                pi.type = type
                pi.include = line
                logDiag('added TYPE =', pi.type, 'INCLUDE =', pi.include)
            else:
                logWarn('interface include:: line NOT inside block')

            line = line + 1
            continue

        # Vulkan 1.1 markup allows the last API include construct to be
        # followed by an asciidoctor endif:: construct (and also preceded,
        # at some distance).
        # This looks for endif:: immediately following an include:: line
        # and, if found, moves the include boundary to this line.
        matches = endifPat.search(file[line])
        if matches != None and pi != None:
            if pi.include == line - 1:
                logDiag('Matched endif pattern following include; moving include')
                pi.include = line
            else:
                logDiag('Matched endif pattern (not following include)')

            line = line + 1
            continue

        matches = bodyPat.search(file[line])
        if matches != None:
            logDiag('Matched // refBody pattern')
            if pi != None:
                pi.body = line
                logDiag('added BODY =', pi.body)
            else:
                logWarn('// refBody line NOT inside block')

            line = line + 1
            continue

        line = line + 1
        continue

    if pi != None:
        logErr('Unclosed open block at EOF!')

    setLogSourcefile(None)
    setLogProcname(None)
    setLogLine(None)

    return pageMap

