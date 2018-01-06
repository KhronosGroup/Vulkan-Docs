#!/usr/bin/python3
#
# Copyright (c) 2015-2018 The Khronos Group Inc.
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

# checkLinks.py - validate link/reference API constructs in files
#
# Usage: checkLinks.py files > logfile
#
# Uses vkapi.py, which is a Python representation of relevant parts
# of the Vulkan API.

import copy, os, pdb, re, string, sys
from vkapi import *

global curFile, curLine, sectionDepth
global errCount, warnCount, emittedPrefix, printInfo

curFile = '???'
curLine = -1
sectionDepth = 0
errCount = 0
warnCount = 0
emittedPrefix = {}
printInfo = False

# Called before printing a warning or error. Only prints once prior
# to output for a given file.
def emitPrefix():
    global curFile, curLine, emittedPrefix
    if (curFile not in emittedPrefix.keys()):
        emittedPrefix[curFile] = None
        print('Checking file:', curFile)
        print('-------------------------------')

def info(*args, **kwargs):
    global curFile, curLine, printInfo
    if (printInfo):

        emitPrefix()
        print('INFO: %s line %d:' % (curFile, curLine),
            ' '.join([str(arg) for arg in args]))

# Print a validation warning found in a file
def warning(*args, **kwargs):
    global curFile, curLine, warnCount

    warnCount = warnCount + 1
    emitPrefix()
    print('WARNING: %s line %d:' % (curFile, curLine),
        ' '.join([str(arg) for arg in args]))

# Print a validation error found in a file
def error(*args, **kwargs):
    global curFile, curLine, errCount

    errCount = errCount + 1
    emitPrefix()
    print('ERROR: %s line %d:' % (curFile, curLine),
        ' '.join([str(arg) for arg in args]))

# See if a tag value exists in the specified dictionary and
# suggest it as an alternative if so.
def checkTag(tag, value, dict, dictName, tagName):
    if (value in dict.keys()):
        warning(value, 'exists in the API but not as a',
            tag + ': .', 'Try using the', tagName + ': tag.')

# Report an error due to an asciidoc tag which doesn't match
# a corresponding API entity.
def foundError(errType, tag, value):
    global curFile, curLine
    error('no such', errType, tag + ':' + value)
    # Try some heuristics to detect likely problems such as missing vk
    # prefixes or the wrong tag.

    # Look in all the dictionaries in vkapi.py to see if the tag
    # is just wrong but the API entity actually exists.
    checkTag(tag, value, flags,   'flags', 'elink')
    checkTag(tag, value, enums,   'enums', 'elink')
    checkTag(tag, value, structs, 'structs', 'slink/sname')
    checkTag(tag, value, handles, 'handles', 'slink/sname')
    checkTag(tag, value, defines, 'defines', 'slink/sname')
    checkTag(tag, value, consts,  'consts', 'ename')
    checkTag(tag, value, protos,  'protos', 'flink/fname')
    checkTag(tag, value, funcpointers, 'funcpointers', 'tlink/tname')

    # Look for missing vk prefixes (quirky since it's case-dependent)
    # NOT DONE YET

# Look for param in the list of all parameters of the specified functions
# Returns True if found, False otherwise
def findParam(param, funclist):
    for f in funclist:
        if (param in protos[f]):
            info('parameter:', param, 'found in function:', f)
            return True
    return False

# Initialize tracking state for checking links/includes
def initChecks():
    global curFile, curLine, curFuncs, curStruct, accumFunc, sectionDepth
    global errCount, warnCount
    global incPat, linkPat, pathPat, sectionPat

    # Matches asciidoc single-line section tags
    sectionPat = re.compile('^(=+) ')

    # Matches any asciidoc include:: directive
    pathPat = re.compile('^include::([\w./_]+)\[\]')

    # Matches asciidoc include:: directives used in spec/ref pages (and also
    # others such as validity). This is specific to the layout of the api/
    # includes and allows any path precding 'api/' followed by the category
    # (protos, structs, enums, etc.) followed by the name of the proto,
    # struct, etc. file.
    incPat = re.compile('^.*api/(\w+)/(\w+)\.txt')

    # Lists of current /protos/ (functions) and /structs/ includes. There
    # can be several protos contiguously for different forms of a command
    curFuncs = []
    curStruct = None

    # Tag if we should accumulate funcs or start a new list. Any intervening
    # pname: tags or struct includes will restart the list.
    accumFunc = False

    # Matches all link names in the current spec/man pages. Assumes these
    # macro names are not trailing subsets of other macros. Used to
    # precede the regexp with [^A-Za-z], but this didn't catch macros
    # at start of line.
    linkPat = re.compile('([efpst](name|link)):(\w*)')

    # Total error/warning counters
    errCount = 0
    warnCount = 0

# Validate asciidoc internal links in specified file.
#   infile - filename to validate
#   follow - if True, recursively follow include:: directives
#   included - if True, function was called recursively
# Links checked are:
#   fname:vkBlah     - Vulkan command name (generates internal link)
#   flink:vkBlah     - Vulkan command name
#   sname:VkBlah     - Vulkan struct name (generates internal link)
#   slink:VkBlah     - Vulkan struct name
#   elink:VkEnumName - Vulkan enumeration ('enum') type name
#   ename:VK_BLAH    - Vulkan enumerant token name
#   pname:name       - parameter name to a command or a struct member
#   tlink:name       - Other Vulkan type name (generates internal link)
#   tname:name       - Other Vulkan type name
def checkLinks(infile, follow = False, included = False):
    global curFile, curLine, curFuncs, curStruct, accumFunc, sectionDepth
    global errCount, warnCount
    global incPat, linkPat, pathPat, sectionPat

    # Global state which gets saved and restored by this function
    oldCurFile = curFile
    oldCurLine = curLine
    curFile = infile
    curLine = 0

    # N.b. dirname() returns an empty string for a path with no directories,
    # unlike the shell dirname(1).
    if (not os.path.exists(curFile)):
        error('No such file', curFile, '- skipping check')
        # Restore global state before exiting the function
        curFile = oldCurFile
        curLine = oldCurLine
        return

    inPath = os.path.dirname(curFile)
    fp = open(curFile, 'r', encoding='utf-8')

    for line in fp:
        curLine = curLine + 1

        # Track changes up and down section headers, and forget
        # the current functions/structure when popping up a level
        match = sectionPat.search(line)
        if (match):
            info('Match sectionPat for line:', line)
            depth = len(match.group(1))
            if (depth < sectionDepth):
                info('Resetting current function/structure for section:', line)
                curFuncs = []
                curStruct = None
            sectionDepth = depth

        match = pathPat.search(line)
        if (match):
            incpath = match.group(1)
            info('Match pathPat for line:', line)
            info('  incpath =', incpath)
            # An include:: directive. First check if it looks like a
            # function or struct include file, and modify the corresponding
            # current function or struct state accordingly.
            match = incPat.search(incpath)
            if (match):
                info('Match incPat for line:', line)
                # For prototypes, if it is preceded by
                # another include:: directive with no intervening link: tags,
                # add to the current function list. Otherwise start a new list.
                # There is only one current structure.
                category = match.group(1)
                tag = match.group(2)
                # @ Validate tag!
                # @ Arguably, any intervening text should shift to accumFuncs = False,
                # e.g. only back-to-back includes separated by blank lines would be
                # accumulated.
                if (category == 'protos'):
                    if (tag in protos.keys()):
                        if (accumFunc):
                            curFuncs.append(tag)
                        else:
                            curFuncs = [ tag ]
                            # Restart accumulating functions
                            accumFunc = True
                        info('curFuncs =', curFuncs, 'accumFunc =', accumFunc)
                    else:
                        error('include of nonexistent function', tag)
                elif (category == 'structs'):
                    if (tag in structs.keys()):
                        curStruct = tag
                        # Any /structs/ include means to stop accumulating /protos/
                        accumFunc = False
                        info('curStruct =', curStruct)
                    else:
                        error('include of nonexistent struct', tag)
            if (follow):
                # Actually process the included file now, recursively
                newpath = os.path.normpath(os.path.join(inPath, incpath))
                info(curFile, ': including file:', newpath)
                checkLinks(newpath, follow, included=True)

        matches = linkPat.findall(line)
        for match in matches:
            # Start actual validation work. Depending on what the
            # asciidoc tag name is, look up the value in the corresponding
            # dictionary.
            tag = match[0]
            value = match[2]
            if (tag == 'fname' or tag == 'flink'):
                if (value not in protos.keys()):
                    foundError('function', tag, value)
            elif (tag == 'sname' or tag == 'slink'):
                if (value not in structs.keys() and
                    value not in handles.keys()):
                    foundError('aggregate/scalar/handle/define type', tag, value)
            elif (tag == 'ename'):
                if (value not in consts.keys() and value not in defines.keys()):
                    foundError('enumerant/constant', tag, value)
            elif (tag == 'elink'):
                if (value not in enums.keys() and value not in flags.keys()):
                    foundError('enum/bitflag type', tag, value)
            elif (tag == 'tlink' or tag == 'tname'):
                if (value not in funcpointers.keys()):
                    foundError('function pointer/other type', tag, value)
            elif (tag == 'pname'):
                # Any pname: tag means to stop accumulating /protos/
                accumFunc = False
                # See if this parameter is in the current proto(s) and struct
                foundParam = False
                if (curStruct and value in structs[curStruct]):
                    info('parameter', value, 'found in struct', curStruct)
                elif (curFuncs and findParam(value, curFuncs)):
                    True
                else:
                    warning('parameter', value, 'not found. curStruct =',
                            curStruct, 'curFuncs =', curFuncs)
            else:
                # This is a logic error
                error('unknown tag', tag + ':' + value)
    fp.close()

    if (errCount > 0 or warnCount > 0):
        if (not included):
            print('Errors found:', errCount, 'Warnings found:', warnCount)
            print('')

    if (included):
        info('----- returning from:', infile, 'to parent file', '-----')

    # Don't generate any output for files without errors
    # else:
    #     print(curFile + ': No errors found')

    # Restore global state before exiting the function
    curFile = oldCurFile
    curLine = oldCurLine

if __name__ == '__main__':
    follow = False
    if (len(sys.argv) > 1):
        for file in sys.argv[1:]:
            if (file == '-follow'):
                follow = True
            elif (file == '-info'):
                printInfo = True
            else:
                initChecks()
                checkLinks(file, follow)
    else:
        print('Need arguments: [-follow] [-info] infile [infile...]', file=sys.stderr)
