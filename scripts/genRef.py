#!/usr/bin/python3
#
# Copyright (c) 2016-2019 The Khronos Group Inc.
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

# genRef.py - create API ref pages from spec source files
#
# Usage: genRef.py files

import argparse
import io
import os
import re
import sys
from collections import OrderedDict
from reflib import (findRefs, fixupRefs, loadFile, logDiag, logWarn,
                    printPageInfo, setLogFile)
from reg import Registry
import vkapi as api
from vkconventions import VulkanConventions as APIConventions

def makeExtensionInclude(name):
    """Return an include command, given an extension name."""
    return 'include::{}/refpage.{}{}[]'.format(
        conventions.specification_path,
        name,
        conventions.file_suffix)

def isextension(name):
    """Return True if name is an API extension name (ends with an upper-case
    author ID).

    This assumes that author IDs are at least two characters."""
    return name[-2:].isalpha() and name[-2:].isupper()

def printCopyrightSourceComments(fp):
    """Print Khronos CC-BY copyright notice on open file fp.

    Writes an asciidoc comment block, which copyrights the source
    file."""
    print('// Copyright (c) 2014-2019 Khronos Group. This work is licensed under a', file=fp)
    print('// Creative Commons Attribution 4.0 International License; see', file=fp)
    print('// http://creativecommons.org/licenses/by/4.0/', file=fp)
    print('', file=fp)

def printFooter(fp):
    print('include::footer.txt[]', file=fp)
    print('', file=fp)


def macroPrefix(name):
    """Add a spec asciidoc macro prefix to an API name, depending on its type
    (protos, structs, enums, etc.).

    If the name is not recognized, use the generic link macro 'reflink:'."""
    if name in api.basetypes:
        return 'basetype:' + name
    if name in api.defines:
        return 'dlink:' + name
    if name in api.enums:
        return 'elink:' + name
    if name in api.flags:
        return 'elink:' + name
    if name in api.funcpointers:
        return 'tlink:' + name
    if name in api.handles:
        return 'slink:' + name
    if name in api.protos:
        return 'flink:' + name
    if name in api.structs:
        return 'slink:' + name
    if name == 'TBD':
        return 'No cross-references are available'
    return 'reflink:' + name

def seeAlsoList(apiName, explicitRefs = None):
    """Return an asciidoc string with a list of 'See Also' references for the
    API entity 'apiName', based on the relationship mapping in the api module.

    'explicitRefs' is a list of additional cross-references.
    If no relationships are available, return None."""
    refs = {}

    # Add all the implicit references to refs
    if apiName in api.mapDict:
        for name in sorted(api.mapDict[apiName]):
            refs[name] = None

    # Add all the explicit references
    if explicitRefs is not None:
        if isinstance(explicitRefs, str):
            explicitRefs = explicitRefs.split()
        for name in explicitRefs:
            refs[name] = None

    if not refs:
        return None
    return ', '.join(macroPrefix(name) for name in sorted(refs.keys())) + '\n'

def remapIncludes(lines, baseDir, specDir):
    """Remap include directives in a list of lines so they can be extracted to a
    different directory.

    Returns remapped lines.

    - lines - text to remap
    - baseDir - target directory
    - specDir - source directory"""
    # This should be compiled only once
    includePat = re.compile(r'^include::(?P<path>.*)\[\]')

    newLines = []
    for line in lines:
        matches = includePat.search(line)
        if matches is not None:
            path = matches.group('path')

            if path[0] != '{':
                # Relative path to include file from here
                incPath = specDir + '/' + path
                # Remap to be relative to baseDir
                newPath = os.path.relpath(incPath, baseDir)
                newLine = 'include::' + newPath + '[]\n'
                logDiag('remapIncludes: remapping', line, '->', newLine)
                newLines.append(newLine)
            else:
                # An asciidoctor variable starts the path.
                # This must be an absolute path, not needing to be rewritten.
                newLines.append(line)
        else:
            newLines.append(line)
    return newLines


def refPageShell(pageName, pageDesc, fp, sections=None, tail_content=None, man_section=3):
    printCopyrightSourceComments(fp)

    print(':data-uri:',
          ':icons: font',
          conventions.extra_refpage_headers,
          '',
          sep='\n', file=fp)

    s = '{}({})'.format(pageName, man_section)
    print('= ' + s,
          '',
          sep='\n', file=fp)
    if pageDesc.strip() == '':
        pageDesc = 'NO SHORT DESCRIPTION PROVIDED'
        logWarn('refPageHead: no short description provided for', pageName)

    print('== Name',
          '{} - {}'.format(pageName, pageDesc),
          '',
          sep='\n', file=fp)

    if sections:
        for title, content in sections.items():
            print('== {}'.format(title),
                  '',
                  content,
                  '',
                  sep='\n', file=fp)

    if tail_content:
        print(tail_content,
              '',
              sep='\n', file=fp)


def refPageHead(pageName, pageDesc, specText, fieldName, fieldText, descText, fp):
    """Generate header of a reference page.

    - pageName - string name of the page
    - pageDesc - string short description of the page
    - specType - string containing 'spec' field from refpage open block, or None.
      Used to determine containing spec name and URL.
    - specText - string that goes in the "C Specification" section
    - fieldName - string heading an additional section following specText, if not None
    - fieldText - string that goes in the additional section
    - descText - string that goes in the "Description" section
    - fp - file to write to"""
    sections = OrderedDict()

    if specText is not None:
        sections['C Specification'] = specText

    if fieldName is not None:
        sections[fieldName] = fieldText

    if descText is None or descText.strip() == '':
        logWarn('refPageHead: no description provided for', pageName)

    if descText is not None:
        sections['Description'] = descText

    refPageShell(pageName, pageDesc, fp, sections=sections)

# specType is None or the 'spec' attribute from the refpage open block,
#   identifying the specification name and URL this refpage links to.
# specAnchor is None or the 'anchor' attribute from the refpage open block,
#   identifying the anchor in the specification this refpage links to. If
#   None, the pageName is assumed to be a valid anchor.
def refPageTail(pageName,
                specType = None,
                specAnchor = None,
                seeAlso = None,
                fp = None,
                auto = False):

    specName = conventions.api_name(specType)
    specURL = conventions.specURL(specType)
    if specAnchor is None:
        specAnchor = pageName

    if seeAlso is None:
        seeAlso = 'No cross-references are available\n'

    notes = [
        'For more information, see the {}#{}[{} Specification^]'.format(
            specURL, specAnchor, specName),
        '',
        ]

    if auto:
        notes.extend((
            'This page is a generated document.',
            'Fixes and changes should be made to the generator scripts, '
            'not directly.',
            ))
    else:
        notes.extend((
            'This page is extracted from the ' + specName + ' Specification. ',
            'Fixes and changes should be made to the Specification, '
            'not directly.',
            ))

    print('== See Also',
          '',
          seeAlso,
          '',
          sep='\n', file=fp)

    print('== Document Notes',
          '',
          '\n'.join(notes),
          '',
          sep='\n', file=fp)

    printFooter(fp)

def emitPage(baseDir, specDir, pi, file):
    """Extract a single reference page into baseDir.

    - baseDir - base directory to emit page into
    - specDir - directory extracted page source came from
    - pi - pageInfo for this page relative to file
    - file - list of strings making up the file, indexed by pi"""
    pageName = baseDir + '/' + pi.name + '.txt'

    # Add a dictionary entry for this page
    global genDict
    genDict[pi.name] = None
    logDiag('emitPage:', pageName)

    # Short description
    if pi.desc is None:
        pi.desc = '(no short description available)'

    # Member/parameter section label and text, if there is one
    field = None
    fieldText = None

    if pi.type != 'freeform':
        # Not sure how this happens yet
        if pi.include is None:
            logWarn('emitPage:', pageName, 'INCLUDE is None, no page generated')
            return

        # Specification text
        lines = remapIncludes(file[pi.begin:pi.include+1], baseDir, specDir)
        specText = ''.join(lines)

        if pi.param is not None:
            if pi.type == 'structs':
                field = 'Members'
            elif pi.type in ['protos', 'funcpointers']:
                field = 'Parameters'
            else:
                logWarn('emitPage: unknown field type:', pi.type,
                    'for', pi.name)
            lines = remapIncludes(file[pi.param:pi.body], baseDir, specDir)
            fieldText = ''.join(lines)

        # Description text
        if pi.body != pi.include:
            lines = remapIncludes(file[pi.body:pi.end+1], baseDir, specDir)
            descText = ''.join(lines)
        else:
            descText = None
            logWarn('emitPage: INCLUDE == BODY, so description will be empty for', pi.name)
            if pi.begin != pi.include:
                logWarn('emitPage: Note: BEGIN != INCLUDE, so the description might be incorrectly located before the API include!')
    else:
        specText = None
        descText = ''.join(file[pi.begin:pi.end+1])

    specURL = conventions.specURL(pi.spec)

    # Substitute xrefs to point at the main spec
    specLinksPattern = re.compile(r'<<([^>,]+)[,]?[ \t\n]*([^>,]*)>>')
    specLinksSubstitute = r'link:{}#\1[\2^]'.format(specURL)
    if specText is not None:
        specText, _ = specLinksPattern.subn(specLinksSubstitute, specText)
    if fieldText is not None:
        fieldText, _ = specLinksPattern.subn(specLinksSubstitute, fieldText)
    if descText is not None:
        descText, _ = specLinksPattern.subn(specLinksSubstitute, descText)

    fp = open(pageName, 'w', encoding='utf-8')
    refPageHead(pi.name,
                pi.desc,
                specText,
                field, fieldText,
                descText,
                fp)
    refPageTail(pageName=pi.name,
                specType=pi.spec,
                specAnchor=pi.anchor,
                seeAlso=seeAlsoList(pi.name, pi.refs),
                fp=fp,
                auto=False)
    fp.close()

def autoGenEnumsPage(baseDir, pi, file):
    """Autogenerate a single reference page in baseDir.

    Script only knows how to do this for /enums/ pages, at present.

    - baseDir - base directory to emit page into
    - pi - pageInfo for this page relative to file
    - file - list of strings making up the file, indexed by pi"""
    pageName = baseDir + '/' + pi.name + '.txt'
    fp = open(pageName, 'w', encoding='utf-8')

    # Add a dictionary entry for this page
    global genDict
    genDict[pi.name] = None
    logDiag('autoGenEnumsPage:', pageName)

    # Short description
    if pi.desc is None:
        pi.desc = '(no short description available)'

    # Description text. Allow for the case where an enum definition
    # is not embedded.
    if not pi.embed:
        embedRef = ''
    else:
        embedRef = ''.join((
                           '  * The reference page for ',
                           macroPrefix(pi.embed),
                           ', where this interface is defined.\n' ))

    txt = ''.join((
        'For more information, see:\n\n',
        embedRef,
        '  * The See Also section for other reference pages using this type.\n',
        '  * The ' + apiName + ' Specification.\n' ))

    refPageHead(pi.name,
                pi.desc,
                ''.join(file[pi.begin:pi.include+1]),
                None, None,
                txt,
                fp)
    refPageTail(pageName=pi.name,
                specType=pi.spec,
                specAnchor=pi.anchor,
                seeAlso=seeAlsoList(pi.name, pi.refs),
                fp=fp,
                auto=True)
    fp.close()


# Pattern to break apart an API *Flags{authorID} name, used in
# autoGenFlagsPage.
flagNamePat = re.compile(r'(?P<name>\w+)Flags(?P<author>[A-Z]*)')


def autoGenFlagsPage(baseDir, flagName):
    """Autogenerate a single reference page in baseDir for an API *Flags type.

    - baseDir - base directory to emit page into
    - flagName - API *Flags name"""
    pageName = baseDir + '/' + flagName + '.txt'
    fp = open(pageName, 'w', encoding='utf-8')

    # Add a dictionary entry for this page
    global genDict
    genDict[flagName] = None
    logDiag('autoGenFlagsPage:', pageName)

    # Short description
    matches = flagNamePat.search(flagName)
    if matches is not None:
        name = matches.group('name')
        author = matches.group('author')
        logDiag('autoGenFlagsPage: split name into', name, 'Flags', author)
        flagBits = name + 'FlagBits' + author
        desc = 'Bitmask of ' + flagBits
    else:
        logWarn('autoGenFlagsPage:', pageName, 'does not end in "Flags{author ID}". Cannot infer FlagBits type.')
        flagBits = None
        desc = 'Unknown ' + apiName + ' flags type'

    # Description text
    if flagBits is not None:
        txt = ''.join((
            'etext:' + flagName,
            ' is a mask of zero or more elink:' + flagBits + '.\n',
            'It is used as a member and/or parameter of the structures and commands\n',
            'in the See Also section below.\n' ))
    else:
        txt = ''.join((
            'etext:' + flagName,
            ' is an unknown ' + apiName + ' type, assumed to be a bitmask.\n' ))

    refPageHead(flagName,
                desc,
                'include::../api/flags/' + flagName + '.txt[]\n',
                None, None,
                txt,
                fp)
    refPageTail(pageName=flagName,
                specType=pi.spec,
                specAnchor=pi.anchor,
                seeAlso=seeAlsoList(flagName, None),
                fp=fp,
                auto=True)
    fp.close()

def autoGenHandlePage(baseDir, handleName):
    """Autogenerate a single handle page in baseDir for an API handle type.

    - baseDir - base directory to emit page into
    - handleName - API handle name"""
    # @@ Need to determine creation function & add handles/ include for the
    # @@ interface in generator.py.
    pageName = baseDir + '/' + handleName + '.txt'
    fp = open(pageName, 'w', encoding='utf-8')

    # Add a dictionary entry for this page
    global genDict
    genDict[handleName] = None
    logDiag('autoGenHandlePage:', pageName)

    # Short description
    desc = apiName + ' object handle'

    descText = ''.join((
        'sname:' + handleName,
        ' is an object handle type, referring to an object used\n',
        'by the ' + apiName + ' implementation. These handles are created or allocated\n',
        'by the @@ TBD @@ function, and used by other ' + apiName + ' structures\n',
        'and commands in the See Also section below.\n' ))

    refPageHead(handleName,
                desc,
                'include::../api/handles/' + handleName + '.txt[]\n',
                None, None,
                descText,
                fp)
    refPageTail(pageName=handleName,
                specType=pi.spec,
                specAnchor=pi.anchor,
                seeAlso=seeAlsoList(handleName, None),
                fp=fp,
                auto=True)
    fp.close()

def genRef(specFile, baseDir):
    """Extract reference pages from a spec asciidoc source file.

    - specFile - filename to extract from
    - baseDir - output directory to generate page in"""
    file = loadFile(specFile)
    if file is None:
        return

    # Save the path to this file for later use in rewriting relative includes
    specDir = os.path.dirname(os.path.abspath(specFile))

    pageMap = findRefs(file, specFile)
    logDiag(specFile + ': found', len(pageMap.keys()), 'potential pages')

    sys.stderr.flush()

    # Fix up references in pageMap
    fixupRefs(pageMap, specFile, file)

    # Create each page, if possible
    pages = {}

    for name in sorted(pageMap):
        pi = pageMap[name]

        printPageInfo(pi, file)

        if pi.Warning:
            logDiag('genRef:', pi.name + ':', pi.Warning)

        if pi.extractPage:
            emitPage(baseDir, specDir, pi, file)
        elif pi.type == 'enums':
            autoGenEnumsPage(baseDir, pi, file)
        elif pi.type == 'flags':
            autoGenFlagsPage(baseDir, pi.name)
        else:
            # Don't extract this page
            logWarn('genRef: Cannot extract or autogenerate:', pi.name)

        pages[pi.name] = pi
        for alias in pi.alias.split():
            pages[alias] = pi

    return pages

def genSinglePageRef(baseDir):
    """Generate baseDir/apispec.txt, the single-page version of the ref pages.

    This assumes there's a page for everything in the api module dictionaries.
    Extensions (KHR, EXT, etc.) are currently skipped"""
    # Accumulate head of page
    head = io.StringIO()

    printCopyrightSourceComments(head)

    print('= ' + apiName + ' API Reference Pages',
          ':data-uri:',
          ':icons: font',
          ':doctype: book',
          ':numbered!:',
          ':max-width: 200',
          ':data-uri:',
          ':toc2:',
          ':toclevels: 2',
          '',
          sep='\n', file=head)

    print('include::copyright-ccby.txt[]', file=head)
    print('', file=head)
    # Inject the table of contents. Asciidoc really ought to be generating
    # this for us.

    sections = [
        [ api.protos,       'protos',       apiName + ' Commands' ],
        [ api.handles,      'handles',      'Object Handles' ],
        [ api.structs,      'structs',      'Structures' ],
        [ api.enums,        'enums',        'Enumerations' ],
        [ api.flags,        'flags',        'Flags' ],
        [ api.funcpointers, 'funcpointers', 'Function Pointer Types' ],
        [ api.basetypes,    'basetypes',    apiName + ' Scalar types' ],
        [ api.defines,      'defines',      'C Macro Definitions' ],
        [ extensions,       'extensions',   apiName + ' Extensions' ]
      ]

    # Accumulate body of page
    body = io.StringIO()

    for (apiDict,label,title) in sections:
        # Add section title/anchor header to body
        anchor = '[[' + label + ',' + title + ']]'
        print(anchor,
              '== ' + title,
              '',
              ':leveloffset: 2',
              '',
              sep='\n', file=body)

        if label == 'extensions':
            # preserve order of extensions since we already sorted the way we want.
            keys = apiDict.keys()
        else:
            keys = sorted(apiDict.keys())

        for refPage in keys:
            # Don't generate links for aliases, which are included with the
            # aliased page
            if refPage not in api.alias:
                # Add page to body
                if 'FlagBits' in refPage and conventions.unified_flag_refpages:
                    # OpenXR does not create separate ref pages for FlagBits:
                    # the FlagBits includes go in the Flags refpage.
                    # Previously the Vulkan script would only emit non-empty
                    # Vk*Flags pages, via the logic
                    #   if refPage not in api.flags or api.flags[refPage] is not None
                    #       emit page
                    # Now, all are emitted.
                    continue
                else:
                    print('include::' + refPage + '.txt[]', file=body)
            else:
                # Alternatively, we could (probably should) link to the
                # aliased refpage
                logWarn('(Benign) Not including', refPage,
                        'in single-page reference',
                        'because it is an alias of', api.alias[refPage])

        print('\n' + ':leveloffset: 0' + '\n', file=body)

    # Write head and body to the output file
    pageName = baseDir + '/apispec.txt'
    fp = open(pageName, 'w', encoding='utf-8')

    print(head.getvalue(), file=fp, end='')
    print(body.getvalue(), file=fp, end='')

    head.close()
    body.close()
    fp.close()


def genExtension(baseDir, name, info):
    # Add a dictionary entry for this page
    global genDict
    genDict[name] = None
    declares = []
    elem = info.elem

    ext_type = elem.get('type')

    for required in elem.find('require'):
        req_name = required.get('name')
        if not req_name:
            # This isn't what we're looking for
            continue
        if req_name.endswith('_SPEC_VERSION') or req_name.endswith('_EXTENSION_NAME'):
            # Don't link to spec version or extension name - those ref pages aren't created.
            continue

        if required.get('extends'):
            # These are either extensions of enums,
            # or enum values: neither of which get a ref page.
            continue

        if req_name not in genDict:
            logWarn('ERROR: {} (in extension {}) does not have a ref page.'.format(req_name, name))

        declares.append(req_name)
    pageName = baseDir + '/' + name + '.txt'
    logDiag('genExtension:', pageName)

    fp = open(pageName, 'w', encoding='utf-8')

    sections = OrderedDict()
    sections['Specification'] = 'See link:{html_spec_relative}#%s[ %s] in the main specification for complete information.' % (
        name, name)
    refPageShell(name,
                 "{} extension".format(ext_type),
                 fp,
                 sections=sections,
                 tail_content=makeExtensionInclude(name))
    refPageTail(pageName=name,
                specType=None,
                specAnchor=name,
                seeAlso=seeAlsoList(name, declares),
                fp=fp,
                auto=True)
    fp.close()


if __name__ == '__main__':
    global genDict, extensions, conventions, apiName
    genDict = {}
    extensions = OrderedDict()
    conventions = APIConventions()
    apiName = conventions.api_name('api')

    parser = argparse.ArgumentParser()

    parser.add_argument('-diag', action='store', dest='diagFile',
                        help='Set the diagnostic file')
    parser.add_argument('-warn', action='store', dest='warnFile',
                        help='Set the warning file')
    parser.add_argument('-log', action='store', dest='logFile',
                        help='Set the log file for both diagnostics and warnings')
    parser.add_argument('-basedir', action='store', dest='baseDir',
                        default='man',
                        help='Set the base directory in which pages are generated')
    parser.add_argument('-noauto', action='store_true',
                        help='Don\'t generate inferred ref pages automatically')
    parser.add_argument('files', metavar='filename', nargs='*',
                        help='a filename to extract ref pages from')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-extension', action='append',
                        default=[],
                        help='Specify an extension or extensions to add to targets')
    parser.add_argument('-rewrite', action='store',
                        default=None,
                        help='Name of output file to write Apache mod_rewrite directives to')
    parser.add_argument('-toc', action='store',
                        default=None,
                        help='Name of output file to write an alphabetical TOC to')
    parser.add_argument('-registry', action='store',
                        default=conventions.registry_path,
                        help='Use specified registry file instead of default')

    results = parser.parse_args()

    setLogFile(True,  True, results.logFile)
    setLogFile(True, False, results.diagFile)
    setLogFile(False, True, results.warnFile)

    baseDir = results.baseDir

    # Dictionary of pages & aliases
    pages = {}

    for file in results.files:
        d = genRef(file, baseDir)
        pages.update(d)

    # Now figure out which pages *weren't* generated from the spec.
    # This relies on the dictionaries of API constructs in the api module.

    if not results.noauto:

        registry = Registry()
        registry.loadFile(results.registry)

        if conventions.write_refpage_include:
            # Only extensions with a supported="..." attribute in this set
            # will be considered for extraction/generation.
            supported_strings = set((conventions.xml_supported_name_of_api,))
            ext_names = set(k for k, v in registry.extdict.items()
                            if v.supported in supported_strings)

            desired_extensions = ext_names.intersection(set(results.extension))
            for prefix in conventions.extension_index_prefixes:
                # Splits up into chunks, sorted within each chunk.
                filtered_extensions = sorted(
                    [name for name in desired_extensions
                     if name.startswith(prefix) and name not in extensions])
                for name in filtered_extensions:
                    extensions[name] = None
                    genExtension(baseDir, name, registry.extdict[name])

        # autoGenFlagsPage is no longer needed because they are added to
        # the spec sources now.
        # for page in api.flags:
        #     if page not in genDict:
        #         autoGenFlagsPage(baseDir, page)

        # autoGenHandlePage is no longer needed because they are added to
        # the spec sources now.
        # for page in api.structs:
        #    if typeCategory[page] == 'handle':
        #        autoGenHandlePage(baseDir, page)

        sections = [
            ( api.flags,        'Flag Types' ),
            ( api.enums,        'Enumerated Types' ),
            ( api.structs,      'Structures' ),
            ( api.protos,       'Prototypes' ),
            ( api.funcpointers, 'Function Pointers' ),
            ( api.basetypes,    apiName + ' Scalar Types' ),
            ( extensions,       apiName + ' Extensions'),
          ]

        # Summarize pages that weren't generated, for good or bad reasons

        for (apiDict,title) in sections:
            # OpenXR was keeping a 'flagged' state which only printed out a
            # warning for the first non-generated page, but was otherwise
            # unused. This doesn't seem helpful.
            for page in apiDict:
                if page not in genDict:
                    # Page was not generated - why not?
                    if page in api.alias:
                        logWarn('(Benign, is an alias) Ref page for', title, page, 'is aliased into', api.alias[page])
                    elif page in api.flags and api.flags[page] is None:
                        logWarn('(Benign, no FlagBits defined) No ref page generated for ', title,
                                page)
                    else:
                        # Could introduce additional logic to detect
                        # external types and not emit them.
                        logWarn('No ref page generated for  ', title, page)

        genSinglePageRef(baseDir)

    if results.rewrite:
        # Generate Apache rewrite directives for refpage aliases
        fp = open(results.rewrite, 'w', encoding='utf-8')

        for page in sorted(pages):
            p = pages[page]
            rewrite = p.name

            if page != rewrite:
                print('RewriteRule ^', page, '.html$ ', rewrite, '.html',
                      sep='', file=fp)
        fp.close()

    if results.toc:
        # Generate dynamic portion of refpage TOC
        fp = open(results.toc, 'w', encoding='utf-8')

        # Run through dictionary of pages generating an TOC
        print(12 * ' ', '<li class="Level1">Alphabetic Contents', sep='', file=fp)
        print(16 * ' ', '<ul class="Level2">', sep='', file=fp)
        lastLetter = None

        for page in sorted(pages, key=str.upper):
            p = pages[page]
            letter = page[0:1].upper()

            if letter != lastLetter:
                if lastLetter:
                    # End previous block
                    print(24 * ' ', '</ul>', sep='', file=fp)
                    print(20 * ' ', '</li>', sep='', file=fp)
                # Start new block
                print(20 * ' ', '<li>', letter, sep='', file=fp)
                print(24 * ' ', '<ul class="Level3">', sep='', file=fp)
                lastLetter = letter

            # Add this page to the list
            print(28 * ' ', '<li><a href="', p.name, '.html" ',
                  'target="pagedisplay">', page, '</a></li>',
                  sep='', file=fp)

        if lastLetter:
            # Close the final letter block
            print(24 * ' ', '</ul>', sep='', file=fp)
            print(20 * ' ', '</li>', sep='', file=fp)

        # Close the list
        print(16 * ' ', '</ul>', sep='', file=fp)
        print(12 * ' ', '</li>', sep='', file=fp)

        # print('name {} -> page {}'.format(page, pages[page].name))

        fp.close()

