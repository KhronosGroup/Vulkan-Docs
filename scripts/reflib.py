#!/usr/bin/python3
#
# Copyright 2016-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Utility functions for automatic ref page generation and other script stuff

import io
import re
import sys
import subprocess

# global errFile, warnFile, diagFile

errFile = sys.stderr
warnFile = sys.stdout
diagFile = None
logSourcefile = None
logProcname = None
logLine = None

def unescapeQuotes(s):
    """Remove \' escape sequences in a string (refpage description)"""
    return s.replace('\\\'', '\'')

def write(*args, **kwargs ):
    file = kwargs.pop('file',sys.stdout)
    end = kwargs.pop('end','\n')
    file.write(' '.join(str(arg) for arg in args))
    file.write(end)

def setLogSourcefile(filename):
    """Metadata which may be printed (if not None) for diagnostic messages"""
    global logSourcefile
    logSourcefile = filename

def setLogProcname(procname):
    global logProcname
    logProcname = procname

def setLogLine(line):
    global logLine
    logLine = line

def logHeader(severity):
    """Generate prefix for a diagnostic line using metadata and severity"""
    global logSourcefile, logProcname, logLine

    msg = severity + ': '
    if logProcname:
        msg = msg + ' in ' + logProcname
    if logSourcefile:
        msg = msg + ' for ' + logSourcefile
    if logLine:
        msg = msg + ' line ' + str(logLine)
    return msg + ' '

def setLogFile(setDiag, setWarn, filename):
    """Set the file handle to log either or both warnings and diagnostics to.

    - setDiag and setWarn are True if the corresponding handle is to be set.
    - filename is None for no logging, '-' for stdout, or a pathname."""
    global diagFile, warnFile

    if filename is None:
        return

    if filename == '-':
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
    if file is not None:
        file.write(logHeader('DIAG') + ' '.join(str(arg) for arg in args))
        file.write(end)

def logWarn(*args, **kwargs):
    file = kwargs.pop('file', warnFile)
    end = kwargs.pop('end','\n')
    if file is not None:
        file.write(logHeader('WARN') + ' '.join(str(arg) for arg in args))
        file.write(end)

def logErr(*args, **kwargs):
    file = kwargs.pop('file', errFile)
    end = kwargs.pop('end','\n')

    strfile = io.StringIO()
    strfile.write(logHeader('ERROR') + ' '.join(str(arg) for arg in args))
    strfile.write(end)

    if file is not None:
        file.write(strfile.getvalue())
    raise UserWarning(strfile.getvalue())

def isempty(s):
    """Return True if s is nothing but white space, False otherwise"""
    return len(''.join(s.split())) == 0

class pageInfo:
    """Information about a ref page relative to the file it is extracted from."""
    def __init__(self):
        self.extractPage = True
        """True if page should be extracted"""

        self.Warning  = None
        """string warning if page is suboptimal or cannot be generated"""

        self.embed    = False
        """False or the name of the ref page this include is embedded within"""

        self.type     = None
        """refpage type attribute - 'structs', 'protos', 'freeform', etc."""

        self.name     = None
        """struct/proto/enumerant/etc. name"""

        self.desc     = None
        """short description of ref page"""

        self.begin    = None
        """index of first line of the page (heuristic or // refBegin)"""

        self.include  = None
        """index of include:: line defining the page"""

        self.param    = None
        """index of first line of parameter/member definitions"""

        self.body     = None
        """index of first line of body text"""

        self.validity = None
        """index of validity include"""

        self.end      = None
        """index of last line of the page (heuristic validity include, or // refEnd)"""

        self.alias    = ''
        """aliases of this name, if supplied, or ''"""

        self.refs     = ''
        """cross-references on // refEnd line, if supplied"""

        self.spec     = None
        """'spec' attribute in refpage open block, if supplied, or None for the default ('api') type"""

        self.anchor   = None
        """'anchor' attribute in refpage open block, if supplied, or inferred to be the same as the 'name'"""

def printPageInfoField(desc, line, file):
    """Print a single field of a pageInfo struct, possibly None.

    - desc - string description of field
    - line - field value or None
    - file - indexed by line"""
    if line is not None:
        logDiag(desc + ':', line + 1, '\t-> ', file[line], end='')
    else:
        logDiag(desc + ':', line)

def printPageInfo(pi, file):
    """Print out fields of a pageInfo struct

    - pi - pageInfo
    - file - indexed by pageInfo"""
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

def prevPara(file, line):
    """Go back one paragraph from the specified line and return the line number
    of the first line of that paragraph.

    Paragraphs are delimited by blank lines. It is assumed that the
    current line is the first line of a paragraph.

    - file is an array of strings
    - line is the starting point (zero-based)"""
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

def nextPara(file, line):
    """Go forward one paragraph from the specified line and return the line
    number of the first line of that paragraph.

    Paragraphs are delimited by blank lines. It is assumed that the
    current line is standalone (which is bogus).

    - file is an array of strings
    - line is the starting point (zero-based)"""
    maxLine = len(file) - 1
    # Skip over current paragraph
    while (line != maxLine and not isempty(file[line])):
        line = line + 1
    # Skip over white space
    while (line != maxLine and isempty(file[line])):
        line = line + 1
    return line

def lookupPage(pageMap, name):
    """Return (creating if needed) the pageInfo entry in pageMap for name"""
    if name not in pageMap:
        pi = pageInfo()
        pi.name = name
        pageMap[name] = pi
    else:
        pi = pageMap[name]
    return pi

def loadFile(filename):
    """Load a file into a list of strings. Return the (list, newline_string) or (None, None) on failure"""
    newline_string = "\n"
    try:
        with open(filename, 'rb') as fp:
            contents = fp.read()
            if contents.count(b"\r\n") > 1:
                newline_string = "\r\n"

        with open(filename, 'r', encoding='utf-8') as fp:
            lines = fp.readlines()
    except:
        logWarn('Cannot open file', filename, ':', sys.exc_info()[0])
        return None, None

    return lines, newline_string

def clampToBlock(line, minline, maxline):
    """Clamp a line number to be in the range [minline,maxline].

    If the line number is None, just return it.
    If minline is None, do not clamp to that value."""
    if line is None:
        return line
    if minline and line < minline:
        return minline
    if line > maxline:
        return maxline

    return line

def fixupRefs(pageMap, specFile, file):
    """Fill in missing fields in pageInfo structures, to the extent they can be
    inferred.

    - pageMap - dictionary of pageInfo structures
    - specFile - filename
    - file - list of strings making up the file, indexed by pageInfo"""
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
        # # chapters/fundamentals.adoc and the table of Vk*Flag types in
        # # appendices/boilerplate.adoc.
        # if pi.begin is None and pi.validity is None and pi.end is None:
        #     pi.begin = pi.include
        #     pi.extractPage = False
        #     pi.Warning = 'No begin, validity, or end lines identified'
        #     continue

        # Using open block delimiters, ref pages must *always* have a
        # defined begin and end. If either is undefined, that is fatal.
        if pi.begin is None:
            pi.extractPage = False
            pi.Warning = 'Can\'t identify begin of ref page open block'
            continue

        if pi.end is None:
            pi.extractPage = False
            pi.Warning = 'Can\'t identify end of ref page open block'
            continue

        # If there is no description of the page, infer one from the type
        if pi.desc is None:
            if pi.type is not None:
                # pi.desc = pi.type[0:len(pi.type)-1] + ' (no short description available)'
                pi.Warning = 'No short description available; could infer from the type and name'
            else:
                pi.extractPage = False
                pi.Warning = 'No short description available, cannot infer from the type'
                continue

        # Try to determine where the parameter and body sections of the page
        # begin. funcpointer, proto, and struct pages infer the location of
        # the parameter and body sections. Other pages infer the location of
        # the body, but have no parameter sections.
        #
        # Probably some other types infer this as well - refer to list of
        # all page types in genRef.py:emitPage()
        if pi.include is not None:
            if pi.type in ['funcpointers', 'protos', 'structs']:
                pi.param = nextPara(file, pi.include)
                if pi.body is None:
                    pi.body = nextPara(file, pi.param)
            else:
                if pi.body is None:
                    pi.body = nextPara(file, pi.include)
        else:
            pi.Warning = 'Page does not have an API definition include::'

        # It is possible for the inferred param and body lines to run past
        # the end of block, if, for example, there is no parameter section.
        pi.param = clampToBlock(pi.param, pi.include, pi.end)
        pi.body = clampToBlock(pi.body, pi.param, pi.end)

        # We can get to this point with .include, .param, and .validity
        # all being None, indicating those sections were not found.

        logDiag('fixupRefs: after processing,', pi.name, 'looks like:')
        printPageInfo(pi, file)

    # Now that all the valid pages have been found, try to make some
    # inferences about invalid pages.
    #
    # If a reference without a .end is entirely inside a valid reference,
    # then it is intentionally embedded - may want to create an indirect
    # page that links into the embedding page. This is done by a very
    # inefficient double loop, but the loop depth is small.
    for name in sorted(pageMap.keys()):
        pi = pageMap[name]

        if pi.end is None:
            for embedName in sorted(pageMap.keys()):
                logDiag('fixupRefs: comparing', pi.name, 'to', embedName)
                embed = pageMap[embedName]
                # Do not check embeddings which are themselves invalid
                if not embed.extractPage:
                    logDiag('Skipping check for embedding in:', embed.name)
                    continue
                if embed.begin is None or embed.end is None:
                    logDiag('fixupRefs:', name + ':',
                            'can\'t compare to unanchored ref:', embed.name,
                            'in', specFile, 'at line', pi.include )
                    printPageInfo(pi, file)
                    printPageInfo(embed, file)
                # If an embed is found, change the error to a warning
                elif (pi.include is not None and pi.include >= embed.begin and
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


def compatiblePageTypes(refpage_type, pagemap_type):
    """Returns whether two refpage 'types' (categories) are compatible -
       this is only true for 'consts' and 'enums' types."""

    constsEnums = [ 'consts', 'enums' ]

    if refpage_type == pagemap_type:
        return True
    if refpage_type in constsEnums and pagemap_type in constsEnums:
        return True
    return False

# Patterns used to recognize interesting lines in an asciidoc source file.
# These patterns are only compiled once.
endifPat   = re.compile(r'^endif::(?P<condition>[\w_+,]+)\[\]')
beginPat   = re.compile(r'^\[open,(?P<attribs>refpage=.*)\]')
# attribute key/value pairs of an open block
attribStr  = r"([a-z]+)='([^'\\]*(?:\\.[^'\\]*)*)'"
attribPat  = re.compile(attribStr)
bodyPat    = re.compile(r'^// *refBody')
errorPat   = re.compile(r'^// *refError')

# This regex transplanted from check_spec_links
# It looks for various generated file conventions, and for the api/validity
# include (generated_type), protos/struct/etc path (category), and API name
# (entity_name).
# It could be put into the API conventions object, instead of being
# generalized for all the different specs.
INCLUDE = re.compile(
        r'include::(?P<directory_traverse>((../){1,4}|\{generated\}/)(generated/)?)(?P<generated_type>[\w]+)/(?P<category>\w+)/(?P<entity_name>[^./]+)\.(adoc|txt)[\[][\]]')

def findRefs(file, filename):
    """Identify reference pages in a list of strings, returning a dictionary of
    pageInfo entries for each one found, or None on failure."""
    setLogSourcefile(filename)
    setLogProcname('findRefs')

    # To reliably detect the open blocks around reference pages, we must
    # first detect the '[open,refpage=...]' markup delimiting the block;
    # skip past the '--' block delimiter on the next line; and identify the
    # '--' block delimiter closing the page.
    # This cannot be done solely with pattern matching, and requires state to
    # track 'inside/outside block'.
    # When looking for open blocks, possible states are:
    #   'outside' - outside a block
    #   'start' - have found the '[open...]' line
    #   'inside' - have found the following '--' line
    openBlockState = 'outside'

    # Dictionary of interesting line numbers and strings related to an API
    # name
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
        if matches is not None:
            logDiag('Matched open block pattern')
            attribs = matches.group('attribs')

            # If the previous open block was not closed, raise an error
            if openBlockState != 'outside':
                logErr('Nested open block starting at line', line, 'of',
                       filename)

            openBlockState = 'start'

            # Parse the block attributes
            matches = attribPat.findall(attribs)

            # Extract each attribute
            name = None
            desc = None
            refpage_type = None
            spec_type = None
            anchor = None
            alias = None
            xrefs = None

            for (key,value) in matches:
                logDiag('got attribute', key, '=', value)
                if key == 'refpage':
                    name = value
                elif key == 'desc':
                    desc = unescapeQuotes(value)
                elif key == 'type':
                    refpage_type = value
                elif key == 'spec':
                    spec_type = value
                elif key == 'anchor':
                    anchor = value
                elif key == 'alias':
                    alias = value
                elif key == 'xrefs':
                    xrefs = value
                else:
                    logWarn('unknown open block attribute:', key)

            if name is None or desc is None or refpage_type is None:
                logWarn('missing one or more required open block attributes:'
                        'refpage, desc, or type')
                # Leave pi is None so open block delimiters are ignored
            else:
                pi = lookupPage(pageMap, name)
                pi.desc = desc
                # Must match later type definitions in interface/validity includes
                pi.type = refpage_type
                pi.spec = spec_type
                pi.anchor = anchor
                if alias:
                    pi.alias = alias
                if xrefs:
                    pi.refs = xrefs
                logDiag('open block for', name, 'added DESC =', desc,
                        'TYPE =', refpage_type, 'ALIAS =', alias,
                        'XREFS =', xrefs, 'SPEC =', spec_type,
                        'ANCHOR =', anchor)

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

                if pi is None:
                    logWarn('no pageInfo available for opening -- delimiter')
                else:
                    pi.begin = line + 1
                    logDiag('opening -- delimiter: added BEGIN =', pi.begin)
            elif openBlockState == 'inside':
                # -- delimiter ending an open block
                if pi is None:
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

        matches = INCLUDE.search(file[line])
        if matches is not None:
            # Something got included, not sure what yet.
            gen_type = matches.group('generated_type')
            refpage_type = matches.group('category')
            name = matches.group('entity_name')

            # This will never match in OpenCL
            if gen_type == 'validity':
                logDiag('Matched validity pattern')
                if pi is not None:
                    if pi.type and not compatiblePageTypes(refpage_type, pi.type):
                        logWarn('ERROR: pageMap[' + name + '] type:',
                                pi.type, 'does not match type:', refpage_type)
                    pi.type = refpage_type
                    pi.validity = line
                    logDiag('added TYPE =', pi.type, 'VALIDITY =', pi.validity)
                else:
                    logWarn('validity include:: line NOT inside block')

                line = line + 1
                continue

            if gen_type == 'api':
                logDiag('Matched include pattern')
                if pi is not None:
                    if pi.include is not None:
                        logDiag('found multiple includes for this block')
                    if pi.type and not compatiblePageTypes(refpage_type, pi.type):
                        logWarn('ERROR: pageMap[' + name + '] type:',
                                pi.type, 'does not match type:', refpage_type)
                    pi.type = refpage_type
                    pi.include = line
                    logDiag('added TYPE =', pi.type, 'INCLUDE =', pi.include)
                else:
                    logWarn('interface include:: line NOT inside block')

                line = line + 1
                continue

            logDiag('ignoring unrecognized include line ', matches.group())

        # Vulkan 1.1 markup allows the last API include construct to be
        # followed by an asciidoctor endif:: construct (and also preceded,
        # at some distance).
        # This looks for endif:: immediately following an include:: line
        # and, if found, moves the include boundary to this line.
        matches = endifPat.search(file[line])
        if matches is not None and pi is not None:
            if pi.include == line - 1:
                logDiag('Matched endif pattern following include; moving include')
                pi.include = line
            else:
                logDiag('Matched endif pattern (not following include)')

            line = line + 1
            continue

        matches = bodyPat.search(file[line])
        if matches is not None:
            logDiag('Matched // refBody pattern')
            if pi is not None:
                pi.body = line
                logDiag('added BODY =', pi.body)
            else:
                logWarn('// refBody line NOT inside block')

            line = line + 1
            continue

        # OpenCL spec uses // refError to tag "validity" (Errors) language,
        # instead of /validity/ includes.
        matches = errorPat.search(file[line])
        if matches is not None:
            logDiag('Matched // refError pattern')
            if pi is not None:
                pi.validity = line
                logDiag('added VALIDITY (refError) =', pi.validity)
            else:
                logWarn('// refError line NOT inside block')

            line = line + 1
            continue

        line = line + 1
        continue

    if pi is not None:
        logErr('Unclosed open block at EOF!')

    setLogSourcefile(None)
    setLogProcname(None)
    setLogLine(None)

    return pageMap


def getBranch():
    """Determine current git branch

    Returns (branch name, ''), or (None, stderr output) if the branch name
    cannot be determined"""

    command = [ 'git', 'symbolic-ref', '--short', 'HEAD' ]
    results = subprocess.run(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

    # git command failed
    if len(results.stderr) > 0:
        return (None, results.stderr)

    # Remove newline from output and convert to a string
    branch = results.stdout.rstrip().decode()
    if len(branch) > 0:
        # Strip trailing newline
        branch = results.stdout.decode()[0:-1]

    return (branch, '')
