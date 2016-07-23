#!/usr/bin/python3

# Utility functions for automatic ref page generation

import io,os,re,sys

# global errFile, warnFile, diagFile

errFile = sys.stderr
warnFile = sys.stdout
diagFile = None

def write(*args, **kwargs ):
    file = kwargs.pop('file',sys.stdout)
    end = kwargs.pop('end','\n')
    file.write(' '.join([str(arg) for arg in args]))
    file.write(end)

# Set the file handle to log either or both warnings and diagnostics to.
# setDiag and setWarn are True if the corresponding handle is to be set.
# filename is None for no logging, '-' for stdout, or a pathname.
def setLogFile(setDiag, setWarn, filename):
    global diagFile, warnFile

    if (filename == None):
        return
    elif (filename == '-'):
        fp = sys.stdout
    else:
        fp = open(filename, 'w')

    if (setDiag):
        diagFile = fp
    if (setWarn):
        warnFile = fp

def logDiag(*args, **kwargs):
    file = kwargs.pop('file', diagFile)
    end = kwargs.pop('end','\n')
    if (file != None):
        file.write('DIAG:  ' + ' '.join([str(arg) for arg in args]))
        file.write(end)

def logWarn(*args, **kwargs):
    file = kwargs.pop('file', warnFile)
    end = kwargs.pop('end','\n')
    if (file != None):
        file.write('WARN:  ' + ' '.join([str(arg) for arg in args]))
        file.write(end)

def logErr(*args, **kwargs):
    file = kwargs.pop('file', errFile)
    end = kwargs.pop('end','\n')

    strfile = io.StringIO()
    strfile.write( 'ERROR: ' + ' '.join([str(arg) for arg in args]))
    strfile.write(end)

    if (file != None):
        file.write(strfile.getvalue())
    raise UserWarning(strfile.getvalue())

# Return True if s is nothing but white space, False otherwise
def isempty(s):
    return len(''.join(s.split())) == 0

# pageInfo - information about a ref page relative to the file it's
# extracted from.
#
#   extractPage - True if page should not be extracted
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
    if (line != None):
        logDiag(desc + ':', line + 1, '\t-> ', file[line], end='')
    else:
        logDiag(desc + ':', line)

# Print out fields of a pageInfo struct
#   pi - pageInfo
#   file - indexed by pageInfo
def printPageInfo(pi, file):
    logDiag('TYPE:   ', pi.type)
    logDiag('NAME:   ', pi.name)
    logDiag('WARN:   ', pi.Warning)
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
    if (not name in pageMap.keys()):
        pi = pageInfo()
        pi.name = name
        pageMap[name] = pi
    else:
        pi = pageMap[name]
    return pi

# Load a file into a list of strings. Return the list or None on failure
def loadFile(specFile):
    if (not os.path.exists(specFile)):
        error('No such spec file', specFile, '- skipping ref page generation')
        return None

    fp = open(specFile, 'r')
    file = fp.readlines()
    fp.close()

    return file

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
        # if (pi.begin == None and pi.validity == None and pi.end == None):
        #     pi.begin = pi.include
        #     pi.extractPage = False
        #     pi.Warning = 'No begin, validity, or end lines identified'
        #     continue

        # If there's no refBegin line, try to determine where the page
        # starts by going back a paragraph from the include statement.
        if (pi.begin == None):
            if (pi.include != None):
                # structs and protos are the only pages with sufficiently
                # regular structure to guess at the boundaries
                if (pi.type == 'structs' or pi.type == 'protos'):
                    pi.begin = prevPara(file, pi.include)
                else:
                    pi.begin = pi.include
        if (pi.begin == None):
            pi.extractPage = False
            pi.Warning = 'Can\'t identify beginning of page'
            continue

        # If there's no description of the page, infer one from the type
        if (pi.desc == None):
            if (pi.type != None):
                # pi.desc = pi.type[0:len(pi.type)-1] + ' (no short description available)'
                pi.Warning = 'No short description available; could infer from the type and name'
                True
            else:
                pi.extractPage = False
                pi.Warning = 'No short description available, cannot infer from the type'
                continue

        # If there's no refEnd line, try to determine where the page ends
        # by the location of the validity include
        if (pi.end == None):
            if (pi.validity != None):
                pi.end = pi.validity
            else:
                pi.extractPage = False
                pi.Warning = 'Can\'t identify end of page (no validity include)'
                continue

        # funcpointer, proto, and struct pages infer the location of the
        # parameter and body sections. Other pages infer the location of the
        # body but have no parameter sections.
        if (pi.include != None):
            if (pi.type in ['funcpointers', 'protos', 'structs']):
                pi.param = nextPara(file, pi.include)
                pi.body = nextPara(file, pi.param)
            else:
                pi.body = nextPara(file, pi.include)
        else:
            pi.Warning = 'Page does not have an API definition include::'

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

        if (pi.end == None):
            for embedName in sorted(pageMap.keys()):
                logDiag('fixupRefs: comparing', pi.name, 'to', embedName)
                embed = pageMap[embedName]
                # Don't check embeddings which are themselves invalid
                if (not embed.extractPage):
                    logDiag('Skipping check for embedding in:', embed.name)
                    continue
                if (embed.begin == None or embed.end == None):
                    logDiag('fixupRefs:', name + ':',
                            'can\'t compare to unanchored ref:', embed.name,
                            'in', specFile, 'at line', pi.include )
                    printPageInfo(pi, file)
                    printPageInfo(embed, file)
                # If an embed is found, change the error to a warning
                elif (pi.include >= embed.begin and pi.include <= embed.end):
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
validPat   = re.compile('^include::(\.\./)+validity/(?P<type>\w+)/(?P<name>\w+).txt\[\]')
beginPat   = re.compile('^// *refBegin (?P<name>\w+) *(?P<desc>.*)')
endPat     = re.compile('^// *refEnd (?P<name>\w+) *(?P<refs>.*)')

# Identify reference pages in a list of strings, returning a dictionary of
# pageInfo entries for each one found, or None on failure.
def findRefs(file):
    # This is a dictionary of interesting line numbers and strings related
    # to a Vulkan API name
    pageMap = {}

    numLines = len(file)
    line = numLines - 1

    while (line >= 0):
        # Only one of the patterns can possibly match. Add it to
        # the dictionary for that name.
        matches = validPat.search(file[line])
        if (matches != None):
            logDiag('findRefs: Matched validPat on line', line, '->', file[line], end='')
            type = matches.group('type')
            name = matches.group('name')
            pi = lookupPage(pageMap, name)
            if (pi.type and type != pi.type):
                logErr('ERROR: pageMap[' + name + '] type:',
                    pi.type, 'does not match type:', type,
                    'at line:', line)
            pi.type = type
            pi.validity = line
            logDiag('findRefs:', name, '@', line, 'added TYPE =', pi.type, 'VALIDITY =', pi.validity)
            line = line - 1
            continue

        matches = includePat.search(file[line])
        if (matches != None):
            logDiag('findRefs: Matched includePat on line', line, '->', file[line], end='')
            type = matches.group('type')
            name = matches.group('name')
            pi = lookupPage(pageMap, name)
            if (pi.type and type != pi.type):
                logErr('ERROR: pageMap[' + name + '] type:',
                    pi.type, 'does not match type:', type,
                    'at line:', line)
            pi.type = type
            pi.include = line
            logDiag('findRefs:', name, '@', line, 'added TYPE =', pi.type, 'INCLUDE =', pi.include)
            line = line - 1
            continue

        matches = beginPat.search(file[line])
        if (matches != None):
            logDiag('findRefs: Matched beginPat on line', line, '->', file[line], end='')
            name = matches.group('name')
            pi = lookupPage(pageMap, name)
            pi.begin = line
            pi.desc = matches.group('desc').strip()
            if (pi.desc[0:2] == '- '):
                pi.desc = pi.desc[2:]
            logDiag('findRefs:', name, '@', line, 'added BEGIN =', pi.begin, 'DESC =', pi.desc)
            line = line - 1
            continue

        matches = endPat.search(file[line])
        if (matches != None):
            logDiag('findRefs: Matched endPat on line', line, '->', file[line], end='')
            name = matches.group('name')
            pi = lookupPage(pageMap, name)
            pi.refs = matches.group('refs')
            pi.end = line
            logDiag('findRefs:', name, '@', line, 'added END =', pi.end, 'Crossrefs =', pi.refs)
            line = line - 1
            continue

        line = line - 1
        continue

    return pageMap

