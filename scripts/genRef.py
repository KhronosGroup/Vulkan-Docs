#!/usr/bin/env python3
#
# Copyright 2016-2026 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# genRef.py - create API ref pages from spec source files
# Usage: genRef.py --help

import argparse
import io
import os
import re
import sys
from collections import OrderedDict, namedtuple
from reflib import (findRefs, fixupRefs, loadFile, logDiag, logWarn, logErr,
                    printPageInfo, setLogFile, importFileModule)
from reg import Registry
from generator import GeneratorOptions
from parse_dependency import dependencyNames
from apiconventions import APIConventions


# Information about different types of refpages.
# These are in the order in which the navigation index will be generated.
# Keys are 'type' fields from the refpage block.
# Values are named tuples containing:
#   isapi - boolean, True if this is an API refpage and False otherwise
#   navlabel - label to use for these pages in the index
RefpageInfo = namedtuple('RefpageInfo', [ 'isapi', 'navlabel', 'pagenames' ])

refpageType = {
    'protos':       RefpageInfo(True, 'Commands', set()),
    'structs':      RefpageInfo(True, 'Structures', set()),
    'enums':        RefpageInfo(True, 'Enumerations', set()),
    'flags':        RefpageInfo(True, 'Flags', set()),
    'handles':      RefpageInfo(True, 'Object Handles', set()),
    'funcpointers': RefpageInfo(True, 'Function Pointer Types', set()),
    'basetypes':    RefpageInfo(True, 'Scalar Types', set()),
    'consts':       RefpageInfo(True, 'Constants', set()),
    'defines':      RefpageInfo(True, 'C Macro Definitions', set()),
    'builtins':     RefpageInfo(False, 'SPIR-V built-ins', set()),
    'feature':      RefpageInfo(False, 'API Core Versions', set()),
    'extensions':   RefpageInfo(False, 'API Extensions', set()),
    'freeform':     RefpageInfo(False, 'Miscellaneous', set()),
    'spirv':        RefpageInfo(False, 'Other SPIR-V', set()),
}

class RemapState:
    """State used to remap spec anchors to Antora resource IDs
        antora - True if remapping is to be done
        module - Antora component/module containing the spec to target
        xrefMap - dictionary mapping spec anchors to chapter anchors
        pageMap - dictionary mapping chapter anchors to Antora page names
    """

    def __init__(self, antora=False, module='', pageMap={}, xrefMap={}):
        self.antora = antora
        self.module = module
        self.pageMap = pageMap
        self.xrefMap = xrefMap

class RemapPatterns:
    """Regular expressions used to remap spec anchors using RemapState
        refLinkPattern, refLinkSubstitute - match and rewrite an internal
            xref to an API entity to the corresponding refpage (xref without
            descriptive text).
        refLinkTextPattern, refLinkTextSubstitute - match and rewrite an
            internal xref to an API entity to the corresponding refpage
            (xref with descriptive text).
        specLinkPattern, specLinkSubstitute - match and rewrite an
            internal xref to another specification anchor to the
            corresponding specification module."""

    def __init__(self):
        refLinkPattern = None
        refLinkSubstitute = None
        refLinkTextPattern = None
        refLinkTextSubstitute = None
        specLinkPattern = None
        specLinkSubstitute = None

def makeExtensionInclude(name):
    """Return an include command for a generated extension interface.
       - name - extension name"""

    return 'include::{}/meta/refpage.{}{}[]'.format(
            conventions.generated_include_path,
            name,
            conventions.file_suffix)


def makeAPIInclude(type, name):
    """Return an include command for a generated API interface
       - type - type of the API, e.g. 'flags', 'handles', etc
       - name - name of the API"""

    return 'include::{}/api/{}/{}{}\n'.format(
            conventions.generated_include_path,
            type, name, conventions.file_suffix)


def isextension(name):
    """Return True if name is an API extension name (ends with an upper-case
    author ID).

    This assumes that author IDs are at least two characters."""
    return name[-2:].isalpha() and name[-2:].isupper()


def printCopyrightSourceComments(fp):
    """Print Khronos CC-BY copyright notice on open file fp.

    Writes an asciidoc comment block, which copyrights the source
    file."""

    # Work around constraints of the 'reuse' tool
    # REUSE-IgnoreStart
    print('// Copyright 2014-2026 The Khronos Group Inc.', file=fp)
    print('// SPDX' + '-License-Identifier: CC-BY-4.0', file=fp)
    # REUSE-IgnoreEnd

    print('', file=fp)


def printFooter(fp, leveloffset=0):
    """Print footer material at the end of each refpage on open file fp.

    If generating separate refpages, adds the copyright.
    If generating the single combined refpage, just add a separator.

    - leveloffset - number of levels to bias section titles up or down."""

    # Generate the section header.
    # Default depth is 2.
    depth = max(0, leveloffset + 2)
    prefix = '=' * depth

    print('ifdef::doctype-manpage[]',
          f'{prefix} Copyright',
          '',
          f'include::{{config}}/copyright-ccby{conventions.file_suffix}[]',
          'endif::doctype-manpage[]',
          '',
          'ifndef::doctype-manpage[]',
          '<<<',
          'endif::doctype-manpage[]',
          '',
          sep='\n', file=fp)


def macroPrefix(name, rewriteAlias = True):
    """Add a spec asciidoc macro prefix to an API name, depending on its type
       (protos, structs, enums, etc.).

       If the name is not recognized, use the generic link macro 'reflink:'.

       If rewriteAlias is True, and name is an alias of something else, use
       that name instead (on the assumption that the promoted-to API has a
       target refpage, while the alias does not).
    """

    if rewriteAlias:
        while name in api.alias:
            name = api.alias[name]

    if name in api.basetypes:
        return f'basetype:{name}'
    if name in api.defines:
        return f'dlink:{name}'
    if name in api.enums:
        return f'elink:{name}'
    if name in api.flags:
        return f'tlink:{name}'
    if name in api.funcpointers:
        return f'tlink:{name}'
    if name in api.handles:
        return f'slink:{name}'
    if name in api.protos:
        return f'flink:{name}'
    if name in api.structs:
        return f'slink:{name}'
    if name == 'TBD':
        return 'No cross-references are available'

    # Fallthrough - cannot find API type for name, so treat as a reflink.
    # This mostly affects feature and extension names e.g. VK_VERSION_1_0.
    return f'reflink:{name}'


def seeAlsoList(apiName, explicitRefs=set(), apiAliases=set()):
    """Return an asciidoc string with a list of 'See Also' references for the
    API entity 'apiName', based on the relationship mapping in the api module.

    - explicitRefs - set of additional cross-references.
    - apiAliases - set of aliases of this apiName to cross-reference

    If no relationships are available, return None."""

    xrefs = set()

    # apiName and its aliases are treated equally
    allApis = apiAliases.copy()
    allApis.add(apiName)

    # Add all the implicit references from the XML definition of the API
    for name in allApis:
        if name in api.mapDict:
            xrefs.update(api.mapDict[name])

    # Add all the explicit references from the refpage block attributes
    xrefs.update(name for name in explicitRefs)

    # Add extensions / core versions based on dependencies
    for name in allApis:
        if name in api.requiredBy:
            for (base,dependency) in api.requiredBy[name]:
                xrefs.add(base)
                if dependency is not None:
                    # 'dependency' may be a boolean expression of extension
                    # names.
                    # Extract them for use in cross-references.
                    for extname in dependencyNames(dependency):
                        xrefs.add(extname)

    if len(xrefs) == 0:
        return None
    else:
        return f'{", ".join(macroPrefix(name) for name in sorted(xrefs))}\n'


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
                incPath = f'{specDir}/{path}'
                # Remap to be relative to baseDir
                newPath = os.path.relpath(incPath, baseDir)
                newLine = f'include::{newPath}[]\n'
                logDiag('remapIncludes: remapping', line, '->', newLine)
                newLines.append(newLine)
            else:
                # An asciidoctor variable starts the path.
                # This must be an absolute path, not needing to be rewritten.
                newLines.append(line)
        else:
            newLines.append(line)
    return newLines


def refPageShell(pageName, pageDesc, pageAliases, fp, head_content = None, sections=None, tail_content=None, man_section=3):
    """Generate body of a reference page.

    - pageName - string name of the page
    - pageDesc - string short description of the page
    - pageAliases - set of aliases of this page
    - fp - file to write to
    - head_content - text to include before the sections
    - sections - iterable returning (title,body) for each section.
    - tail_content - text to include after the sections
    - man_section - Unix man page section"""

    printCopyrightSourceComments(fp)

    print(':data-uri:',
          ':!icons:',
          ':attribute-missing: warn',
          conventions.extra_refpage_headers,
          '',
          sep='\n', file=fp)

    if len(pageAliases) > 0:
        # Generate page-aliases relative to {refpage-alias-path}.
        # This is set in the refpages component antora.yml for Antora builds
        # only; otherwise refpage-alias-path is set to empty to prevent
        # warnings from asciidoctor.
        # The page-aliases attribute is irrelevant to non-Antora builds.
        pathaliases = ', '.join(f'{{refpage-alias-path}}{page}.adoc' for page in sorted(pageAliases))
        aliases = 'ifndef::refpage-alias-path[:refpage-alias-path:]\n'
        aliases += ':page-aliases: ' + pathaliases
    else:
        aliases = ''

    s = f'{pageName}({man_section})'
    print(f'= {s}',
          aliases,
          '',
          conventions.extra_refpage_body,
          '',
          sep='\n', file=fp)
    if pageDesc.strip() == '':
        pageDesc = 'NO SHORT DESCRIPTION PROVIDED'
        logWarn('refPageShell: no short description provided for', pageName)

    print('== Name',
          f'{pageName} - {pageDesc}',
          '',
          sep='\n', file=fp)

    if head_content is not None:
        print(head_content,
              '',
              sep='\n', file=fp)

    if sections is not None:
        for title, content in sections.items():
            print(f'== {title}',
                  '',
                  content,
                  '',
                  sep='\n', file=fp)

    if tail_content is not None:
        print(tail_content,
              '',
              sep='\n', file=fp)


def refPageHead(pageName, pageDesc, pageAliases, specText, fieldName, fieldText, descText, fp):
    """Generate header of a reference page.

    - pageName - string name of the page
    - pageDesc - string short description of the page
    - pageAliases - set of aliases of this page
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

    refPageShell(pageName, pageDesc, pageAliases, fp, head_content=None, sections=sections)


def refPageTail(pageName,
                specType=None,
                specAnchor=None,
                seeAlso=None,
                fp=None,
                auto=False,
                leveloffset=0):
    """Generate end boilerplate of a reference page.

    - pageName - name of the page
    - specType - None or the 'spec' attribute from the refpage block,
      identifying the specification name and URL this refpage links to.
    - specAnchor - None or the 'anchor' attribute from the refpage block,
      identifying the anchor in the specification this refpage links to. If
      None, the pageName is assumed to be a valid anchor.
    - seeAlso - text of the "See Also" section
    - fp - file to write the page to
    - auto - True if this is an entirely generated refpage, False if it is
      handwritten content from the spec.

    - leveloffset - number of levels to bias section titles up or down."""

    specName = conventions.api_name(specType)
    specURL = conventions.specURL(specType)
    if specAnchor is None:
        specAnchor = pageName

    if seeAlso is None:
        seeAlso = 'No cross-references are available\n'

    # Create reference to the Specification document from which this refpage
    # was extracted.

    global remapState
    if remapState.antora:
        # Determine which page anchor this anchor comes from.
        # If it cannot be determined, use the unmapped anchor.
        # This happens for e.g. SPIR-V keywords like 'BaryCoordKHR', which
        # have their own refpage but no anchor.

        module = remapState.module

        try:
            (pageAnchor, _) = remapState.pageMap[specAnchor]
            pageName = remapState.xrefMap[pageAnchor]
            specref = f'xref:{module}{pageName}#{specAnchor}[{specName} Specification]'
        except:
            logWarn(f'refPageTail: cannot determine specification page containing {specAnchor}')

            specref = f'xref:{module}index.adoc[{specName} Specification] (NOTE: cannot determine Specification page containing this refpage)'
    else:
        specref = f'link:{specURL}#{specAnchor}[{specName} Specification^]'

    notes = [
        f'For more information, see the {specref}.',
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
            f'This page is extracted from the {specName} Specification. ',
            'Fixes and changes should be made to the Specification, '
            'not directly.',
        ))

    # Generate the section header.
    # Default depth is 2.
    depth = max(0, leveloffset + 2)
    prefix = '=' * depth

    print(f'{prefix} See Also',
          '',
          seeAlso,
          '',
          sep='\n', file=fp)

    print(f'{prefix} Document Notes',
          '',
          '\n'.join(notes),
          '',
          sep='\n', file=fp)

    printFooter(fp, leveloffset)

def xrefRewriteInitialize(remapState, remapPatterns):
    """Initialize substitution patterns for asciidoctor xrefs to Antora
       resource IDs and add them to the remapPatterns object."""

    # These are xrefs to API entities, rewritten to link to refpages
    # The refLink variants are for xrefs with only an anchor and no text.
    # The refLinkText variants are for xrefs with both anchor and text
    remapPatterns.refLinkPattern = re.compile(r'<<([Vv][Kk][A-Za-z0-9_]+)>>')
    remapPatterns.refLinkTextPattern = re.compile(r'<<([Vv][Kk][A-Za-z0-9_]+)[,]?[ \t\n]*([^>,]*)>>')

    if remapState.antora:
        remapPatterns.refLinkSubstitute = r'xref:\1.adoc[\1]'
        remapPatterns.refLinkTextSubstitute = r'xref:\1.adoc[\2]'
    else:
        remapPatterns.refLinkSubstitute = r'link:\1.html[\1^]'
        remapPatterns.refLinkTextSubstitute = r'link:\1.html[\2^]'

    # These are xrefs to other anchors, rewritten to link to the spec
    remapPatterns.specLinkPattern = re.compile(r'<<([-A-Za-z0-9_.(){}:]+)[,]?[ \t\n]*([^>,]*)>>')

    # Unfortunately specLinkSubstitute depends on the link target,
    # so must be generated for each target
    remapPatterns.specLinkSubstitute = None

def xrefRewrite(text, specURL):
    """Rewrite asciidoctor xrefs in text to resolve properly in refpages.
    Xrefs which are to refpages are rewritten to link to those
    refpages. The remainder are rewritten to generate external links into
    the supplied specification document URL.

    - text - string to rewrite, or None
    - specURL - URL to target

    Returns rewritten text, or None, respectively"""

    if text is None:
        return text

    global remapState, remapPatterns

    # Define specLinkSubstitute, a callback function passed to re.subn to
    # rewrite <<anchor, text>> for the targeted output form (Antora or
    # regular HTML refpages).
    if remapState.antora:
        # This should never happen, because the refpages for Antora are
        # generated by extraction from the already transformed spec source,
        # and xrefs should already have been rewritten.
        # If it needs to work for some reason, it will be necessary to
        # import xrefMap.py and pageMap.py to determine the Antora page to
        # link to.

        # For Antora, rewrite the anchor into an Antora resource ID
        # containing that anchor in the specification module.
        # This is more complex than a static regular expression allows.

        def rewriteResourceID(match, module):
            anchor = match.group(1)
            text = match.group(2)

            return f'xref:{module}{pagename}#{anchor}[{text}]'

        specLinkSubstitute = lambda match: rewriteResourceID(match, remapState.module)
    else:
        # For the standalone refpages, rewrite relative to the HTML spec
        # URL.

        def substituteURL(match, specURL):
            anchor = match.group(1)
            text = match.group(2)

            return f'link:{specURL}#{anchor}[{text}^]'

        specLinkSubstitute = lambda match: substituteURL(match, specURL)

    # Substitute
    text, _ = remapPatterns.refLinkPattern.subn(remapPatterns.refLinkSubstitute, text)
    text, _ = remapPatterns.refLinkTextPattern.subn(remapPatterns.refLinkTextSubstitute, text)
    text, _ = remapPatterns.specLinkPattern.subn(specLinkSubstitute, text)

    return text

def emitPage(baseDir, specDir, pi, file):
    """Extract a single reference page into baseDir.

    - baseDir - base directory to emit page into
    - specDir - directory extracted page source came from
    - pi - pageInfo for this page relative to file
    - file - list of strings making up the file, indexed by pi"""
    pageName = f'{baseDir}/{pi.name}{conventions.file_suffix}'

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

    # Only do structural checks on API pages
    if pi.type in refpageType:
        if refpageType[pi.type].isapi:
            if pi.include is None:
                logWarn(f'emitPage: {pageName} INCLUDE is None, no page generated')
                return

            # Specification text from beginning to just before the parameter
            # section. This covers the description, the prototype, the version
            # note, and any additional version note text. If a parameter section
            # is absent then go a line beyond the include.
            remap_end = pi.include + 1 if pi.param is None else pi.param
            lines = remapIncludes(file[pi.begin:remap_end], baseDir, specDir)
            specText = ''.join(lines)

            if pi.param is not None:
                if pi.type == 'structs':
                    field = 'Members'
                elif pi.type in ['protos', 'funcpointers']:
                    field = 'Parameters'
                else:
                    logWarn(f'emitPage: unknown field type: {pi.type} for {pi.name}')
                lines = remapIncludes(file[pi.param:pi.body], baseDir, specDir)
                fieldText = ''.join(lines)

            # Description text
            if pi.body != pi.include:
                lines = remapIncludes(file[pi.body:pi.end + 1], baseDir, specDir)
                descText = ''.join(lines)
            else:
                descText = None
                logWarn(f'emitPage: INCLUDE == BODY, so description will be empty for {pi.name}')
                if pi.begin != pi.include:
                    logWarn('emitPage: Note: BEGIN != INCLUDE, so the description might be incorrectly located before the API include!')
        else:
            specText = None
            descText = ''.join(file[pi.begin:pi.end + 1])
    else:
        # This should be caught in the spec markup checking tests
        logErr(f'emitPage: refpage type="{pi.type}" is unrecognized')

    # Rewrite asciidoctor xrefs to resolve properly in refpages
    specURL = conventions.specURL(pi.spec)

    specText = xrefRewrite(specText, specURL)
    fieldText = xrefRewrite(fieldText, specURL)
    descText = xrefRewrite(descText, specURL)

    fp = open(pageName, 'w', encoding='utf-8')
    refPageHead(pageName=pi.name,
                pageDesc=pi.desc,
                pageAliases=pi.alias,
                specText=specText,
                fieldName=field,
                fieldText=fieldText,
                descText=descText,
                fp=fp)
    refPageTail(pageName=pi.name,
                specType=pi.spec,
                specAnchor=pi.anchor,
                seeAlso=seeAlsoList(apiName=pi.name, explicitRefs=pi.xrefs, apiAliases=pi.alias),
                fp=fp,
                auto=False)
    fp.close()


def autoGenEnumsPage(baseDir, pi, file):
    """Autogenerate a single reference page in baseDir.

    Script only knows how to do this for /enums/ pages, at present.

    - baseDir - base directory to emit page into
    - pi - pageInfo for this page relative to file
    - file - list of strings making up the file, indexed by pi"""
    pageName = f'{baseDir}/{pi.name}{conventions.file_suffix}'
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
                           ', where this interface is defined.\n'))

    txt = ''.join((
        'For more information, see:\n\n',
        embedRef,
        '  * The See Also section for other reference pages using this type.\n',
        f'  * The {apiName} Specification.\n'))

    refPageHead(pageName=pi.name,
                pageDesc=pi.desc,
                pageAliases=pi.alias,
                specText=''.join(file[pi.begin:pi.include + 1]),
                fieldName=None,
                fieldText=None,
                descText=txt,
                fp=fp)
    refPageTail(pageName=pi.name,
                specType=pi.spec,
                specAnchor=pi.anchor,
                seeAlso=seeAlsoList(apiName=pi.name, explicitRefs=pi.xrefs, apiAliases=pi.alias),
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
    pageName = f'{baseDir}/{flagName}{conventions.file_suffix}'
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
        flagBits = f'{name}FlagBits{author}'
        desc = f'Bitmask of {flagBits}'
    else:
        logWarn(f'autoGenFlagsPage: {pageName} does not end in "Flags<author ID>". Cannot infer FlagBits type.')
        flagBits = None
        desc = f'Unknown {apiName} flags type'

    # Description text
    if flagBits is not None:
        txt = ''.join((
            f'etext:{flagName}',
            f' is a mask of zero or more elink:{flagBits}.\n',
            'It is used as a member and/or parameter of the structures and commands\n',
            'in the See Also section below.\n'))
    else:
        txt = ''.join((
            f'etext:{flagName}',
            f' is an unknown {apiName} type, assumed to be a bitmask.\n'))

    refPageHead(pageName=flagName,
                pageDesc=desc,
                pageAliases=set(),
                specText=makeAPIInclude('flags', flagName),
                fieldName=None,
                fieldText=None,
                descText=txt,
                fp=fp)
    refPageTail(pageName=flagName,
                specType=pi.spec,
                specAnchor=pi.anchor,
                seeAlso=seeAlsoList(apiName=flagName),
                fp=fp,
                auto=True)
    fp.close()


def autoGenHandlePage(baseDir, handleName):
    """Autogenerate a single handle page in baseDir for an API handle type.

    - baseDir - base directory to emit page into
    - handleName - API handle name"""
    # @@ Need to determine creation function & add handles/ include for the
    # @@ interface in generator.py.
    pageName = f'{baseDir}/{handleName}{conventions.file_suffix}'
    fp = open(pageName, 'w', encoding='utf-8')

    # Add a dictionary entry for this page
    global genDict
    genDict[handleName] = None
    logDiag('autoGenHandlePage:', pageName)

    # Short description
    desc = f'{apiName} object handle'

    descText = ''.join((
        f'sname:{handleName}',
        ' is an object handle type, referring to an object used\n',
        f'by the {apiName} implementation. These handles are created or allocated\n',
        f'by the @@ TBD @@ function, and used by other {apiName} structures\n',
        'and commands in the See Also section below.\n'))

    refPageHead(pageName=handleName,
                pageDesc=desc,
                pageAliases=set(),
                specText=makeAPIInclude('handles', handleName),
                fieldName=None,
                fieldText=None,
                descText=descText,
                fp=fp)
    refPageTail(pageName=handleName,
                specType=pi.spec,
                specAnchor=pi.anchor,
                seeAlso=seeAlsoList(apiName=handleName),
                fp=fp,
                auto=True)
    fp.close()


def genRef(specFile, baseDir, aliasFrom):
    """Extract reference pages from a spec asciidoc source file.

    - specFile - filename to extract from
    - baseDir - output directory to generate page in
    - aliasFrom - map from refpage name to a set of its aliases"""

    # We do not care the newline format used here.
    file, _ = loadFile(specFile)
    if file is None:
        return

    # Save the path to this file for later use in rewriting relative includes
    specDir = os.path.dirname(os.path.abspath(specFile))

    refpageMap = findRefs(file, specFile, aliasFrom)
    logDiag(f'{specFile}: found {len(refpageMap)} potential pages')

    # Fix up references in refpageMap
    fixupRefs(refpageMap, specFile, file)

    # Create each page, if possible
    pages = {}

    for (name, pi) in sorted(refpageMap.items()):
        # Only generate the page if it is in the requested build
        # 'freeform' pages are always generated
        # 'feature' pages (core versions & extensions) are generated if they are in
        # the requested feature list
        # All other pages (APIs) are generated if they are in the API map for
        # the build.
        if pi.type in refpageType:
            isapi = refpageType[pi.type].isapi

            if isapi:
                if name not in api.typeCategory:
                    # Also check aliases of name - api.nonexistent is the same
                    # mapping used to rewrite *link: macros in this build.
                    if name not in api.nonexistent:
                        logWarn(f'genRef: NOT generating feature page {name} - API not in this build')
                        continue
                    else:
                        logWarn(f'genRef: generating feature page {name} because its alias {api.nonexistent[name]} exists')
            else:
                # The only non-API type which can be checked is a feature refpage
                if pi.type == 'feature':
                    if name not in api.features:
                        logWarn(f'genRef: NOT generating feature page {name} - feature not in this build')
                        continue

        printPageInfo(pi, file)

        if pi.Warning:
            logWarn(f'genRef: {pi.name}: {pi.Warning}')

        if pi.extractPage:
            emitPage(baseDir, specDir, pi, file)
        elif pi.type == 'enums':
            autoGenEnumsPage(baseDir, pi, file)
        elif pi.type == 'flags':
            autoGenFlagsPage(baseDir, pi.name)
        else:
            # Do not extract this page
            logWarn(f'genRef: Cannot extract or autogenerate: {pi.name}')

        # Add entries for aliases specified in the refpage attributes
        # Because the output pages have already been emitted at this point,
        # there are no copies of files.
        pages[pi.name] = pi
        for alias in pi.alias:
            logDiag(f'genRef: adding alias {alias} for {pi.name} in pages[]')
            pages[alias] = pi

    return pages


def genAntoraNav(navfile):
    """Generate the Antora navigation sidebar for the refpages.

       Assumes there is a page for everything in the api module dictionaries.
       Extensions (KHR, EXT, etc.) are currently skipped

       navfile - output filename to generate
       """

    fp = open(navfile, 'w', encoding='utf-8')

    head = '\n'.join((
        '// Generated by genRef.py:genAntoraNav() from the setup_refpages_antora',
        '// Makefile target.',
        '// To make changes, modify that script.',
        '',
        ':chapters:',
        '',
        f'* xref:index.adoc[{apiName} API Reference Pages]',
    ))

    printCopyrightSourceComments(fp)
    print(head, file=fp)

    #@ Temporary workaround - remap XML category to match refpage 'type'
    # We do not need the refpage 'type' for API types, since the API map is a
    # canonical source of that information.
    remapXMLCategory = {
        'basetype'    : 'basetypes',
        'define'      : 'defines',
        'consts'      : 'enums',
        'group'       : 'enums',
        'bitmask'     : 'flags',
        'funcpointer' : 'funcpointers',
        'handle'      : 'handles',
        'struct'      : 'structs',
        'union'       : 'structs',
    }

    # Sweep over generated pages
    #@@@ refPageTail cannot determine specification page containing
    # [SPIR-V terms, VK_NO_PROTOTYPES, RuntimeSpirv, etc.]
    for (name, pi) in sorted(pages.items()):
        # Classify each page into tables of either an API or other type
        #  depending on its 'type'.
        # The set of names of pages for each refpage type is built here.
        if pi.type not in refpageType:
            logErr(f'genAntoraNav: unknown refpage type {pi.type}')
        refpageType[pi.type].pagenames.add(name)

        # Check that the refpage 'type' attribute matches the type from
        # the API map, if this is an API
        if name in api.typeCategory:
            category = api.typeCategory[name]

            if category in remapXMLCategory:
                category = remapXMLCategory[category]

            if category != pi.type:
                logWarn(f'genAntoraNav: {name} refpage type {pi.type} does not match XML category {category}')
        elif refpageType[pi.type].isapi:
            logWarn(f'genAntoraNav: {name} refpage type {pi.type} is tagged as a {pi.type} type, but does not have an XML category')
        # else this is a page without a corresponding XML API

    # Each refpage should already tag its aliases, but we could sweep over
    # the API map alias information instead (or additionally), removing the
    # needs for refpage 'alias' attributes for API pages.

    # Do a final consistency check looking for refpages not found in the
    #  API map, and entry points in the API map not found in the refpages.

    def apiSortKey(name):
        """Sort on refpage names not considering any 'vk' prefix"""
        name = name.upper()

        if name[0:3] == 'VK_':
            return name[3:]
        elif name[0:2] == 'VK':
            return name[2:]
        else:
            return name

    # Look over each refpage type, generating a sorted navigation index of
    # the pages belonging to it.
    for (refpage_type, (isapi, navlabel, pagenames)) in refpageType.items():
        print(f'\n[[{refpage_type}]]', file=fp)
        print(f'* {navlabel}', file=fp)

        if navlabel == 'extensions':
            # Extensions are already sorted the way we want
            # @@ However, they are not yet in the refpageType 'pagenames' field
            # because they are generated, not extracted.
            sorted_pages = [ 'NO EXTENSIONS YET!' ]
        else:
            sorted_pages = sorted(pagenames, key=apiSortKey)

        lastLetter = ''

        for pagename in sorted_pages:
            # Also generate links for aliases, to be complete
            if 'FlagBits' in pagename and conventions.unified_flag_refpages:
                # OpenXR does not create separate ref pages for FlagBits:
                # FlagBits includes go in the Flags refpage.
                # Vulkan has separate pages.
                continue

            letter = apiSortKey(pagename)[0:1]

            if letter != lastLetter:
                # Start new section
                print(f'** {letter}', file=fp)
                lastLetter = letter

            # Add this page to the list, or a link to its alias if that exists
            if pagename in api.alias:
                # Use alias from the API map, if one exists
                target = api.alias[pagename]
            elif pagename in pages and pages[pagename].name != pagename:
                # Use alias from the refpage attributes
                target = pages[pagename].name
            else:
                # This is (probably) not an alias
                target = pagename

            print(f'*** xref:source/{target}{conventions.file_suffix}[{pagename}]', file=fp)

    fp.close()


def genExtension(baseDir, extpath, name, info):
    """Generate refpage, and add dictionary entry for an extension

    - baseDir - output directory to generate page in
    - extpath - None, or path to per-extension specification sources if
                those are to be included in extension refpages
    - name - extension name
    - info - <extension> Element from XML"""

    # Add a dictionary entry for this page
    global genDict
    genDict[name] = None
    declares = set()
    elem = info.elem

    # Autogenerate interfaces from <extension> entry
    for required in elem.findall('require'):
        req_name = required.get('name')
        if not req_name:
            # This is not what we are looking for
            continue
        if req_name.endswith('_SPEC_VERSION') or req_name.endswith('_EXTENSION_NAME'):
            # Do not link to spec version or extension name - those ref pages are not created.
            continue

        if required.get('extends'):
            # These are either extensions of enumerated types, or const enum
            # values: neither of which get a ref page - although we could
            # include the enumerated types in the See Also list.
            continue

        if req_name not in genDict:
            if req_name in api.alias:
                logWarn(f'WARN: {req_name} (in extension {name}) is an alias, so does not have a ref page')
            else:
                logWarn(f'ERROR: {req_name} (in extension {name}) does not have a ref page.')

        declares.add(req_name)

    appbody = None
    tail_content = None
    if extpath is not None:
        try:
            appPath = f'{extpath}/{conventions.extension_file_path(name)}'
            appfp = open(appPath, 'r', encoding='utf-8')
            appbody = appfp.read()
            appfp.close()

            # Transform internal links to crosslinks
            specURL = conventions.specURL()
            appbody = xrefRewrite(appbody, specURL)
        except FileNotFoundError:
            print('Cannot find extension appendix for', name)
            logWarn(f'Cannot find extension appendix for {name}')

            # Fall through to autogenerated page
            extpath = None
            appbody = None

            appbody = f'Cannot find extension appendix {appPath} for {name}\n'
    else:
        tail_content = makeExtensionInclude(name)

    # Write the extension refpage
    pageName = f'{baseDir}/{name}{conventions.file_suffix}'
    logDiag('genExtension:', pageName)
    fp = open(pageName, 'w', encoding='utf-8')

    # There are no generated titled sections
    sections = None

    refPageShell(pageName=name,
                 pageDesc=conventions.extension_short_description(elem),
                 pageAliases=set(),
                 fp=fp,
                 head_content=appbody,
                 sections=sections,
                 tail_content=tail_content)

    # Restore leveloffset for boilerplate in refPageTail
    if conventions.include_extension_appendix_in_refpage:
        # The generated metadata include (refpage.extensionname.adoc) moved
        # the leveloffset attribute by -1 to account for the relative
        # structuring of the spec extension appendix section structure vs.
        # the refpages.
        # This restores leveloffset for the boilerplate in refPageTail.
        leveloffset = 1
    else:
        leveloffset = 0

    refPageTail(pageName=name,
                specType=None,
                specAnchor=name,
                seeAlso=seeAlsoList(apiName=name, explicitRefs=declares),
                fp=fp,
                auto=True,
                leveloffset=leveloffset)
    fp.close()


if __name__ == '__main__':
    global genDict, conventions, apiName
    genDict = {}
    conventions = APIConventions()
    apiName = conventions.api_name('api')

    parser = argparse.ArgumentParser()

    parser.add_argument('-diag', action='store', dest='diagFile',
                        help='Set the diagnostic file')
    parser.add_argument('-warn', action='store', dest='warnFile',
                        help='Set the warning file')
    parser.add_argument('-log', action='store', dest='logFile',
                        help='Set the log file for both diagnostics and warnings')
    parser.add_argument('-genpath', action='store',
                        default='gen',
                        help='Path to directory containing generated files')
    parser.add_argument('-basedir', action='store', dest='baseDir',
                        default=None,
                        help='Set the base directory in which pages are generated')
    parser.add_argument('-noauto', action='store_true',
                        help='Do not generate inferred ref pages automatically')
    parser.add_argument('files', metavar='filename', nargs='*',
                        help='a filename to extract ref pages from')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-extension', action='append',
                        default=[],
                        help='Specify an extension or extensions to add to targets')
    parser.add_argument('-rewrite', action='store',
                        default=None,
                        help='Name of output file to write Apache mod_rewrite directives to')
    parser.add_argument('-nav', action='store',
                        default=None,
                        help='Name of output file to write an Antora navigation index to')
    parser.add_argument('-registry', action='store',
                        default=conventions.registry_path,
                        help='Use specified registry file instead of default')
    parser.add_argument('-extpath', action='store',
                        default=None,
                        help='Use extension descriptions from this directory instead of autogenerating extension refpages')
    parser.add_argument('-antora', action='store_true',
                        help='Prepare refpage source for Antora instead of asciidoctor build')
    parser.add_argument('-xrefMap', action='store',
                        default=None, required=False,
                        help='Specify path to xrefMap.py, containing map of anchors to chapter anchors')
    parser.add_argument('-pageMap', action='store',
                        default=None, required=False,
                        help='Specify path to pageMap.py, containing map of chapter anchors to Antora page names')
    parser.add_argument('-module', action='store',
                        default='',
                        help='Specify Antora module name for resolving links within the specification')

    results = parser.parse_args()

    setLogFile(True,  True, results.logFile)
    setLogFile(True, False, results.diagFile)
    setLogFile(False, True, results.warnFile)

    # Load the generated apimap module
    sys.path.insert(0, results.genpath)
    import apimap as api

    # Generate an inverse map from api.alias, which contains (alias =>
    # aliased API), to (aliased API, set(aliases of that API)).
    # This is a more reliable replacement for the 'alias' attribute formerly
    # on refpage blocks.
    aliasFrom = {}
    for alias, apiname in api.alias.items():
        aliasFrom.setdefault(apiname, set()).add(alias)

    # Load the xrefMap and pageMap modules, if specified
    xrefMap = {}
    if results.xrefMap is not None:
        try:
            xrefMap = importFileModule(results.xrefMap).xrefMap
        except:
            print(f'WARNING: Cannot rewrite links - xrefMap module was not imported from {results.xrefMap}', file=sys.stderr)
            sys.exit(1)

    pageMap = {}
    if results.pageMap is not None:
        try:
            pageMap = importFileModule(results.pageMap).pageMap
        except:
            print(f'WARNING: Cannot rewrite links - pageMap module was not imported from {results.pageMap}', file=sys.stderr)
            sys.exit(1)

    # Setup remapping parameters in a global object to avoid passing them
    # through many layers.

    global remapState, remapPatterns
    remapState = RemapState(results.antora, results.module, xrefMap, pageMap)
    remapPatterns = RemapPatterns
    xrefRewriteInitialize(remapState, remapPatterns)

    if results.baseDir is None:
        baseDir = results.genpath + '/ref'
    else:
        baseDir = results.baseDir

    # Dictionary of pages & aliases
    pages = {}

    for file in results.files:
        d = genRef(file, baseDir, aliasFrom)
        pages.update(d)

    # Now figure out which pages were not generated from the spec.
    # This relies on the dictionaries of API constructs in the api module.

    # Extensions are generated by rewriting the corresponding appendix,
    # rather than looking for refpage block markup.
    # We still track extensions in the corresponding refpageType, like
    # extracted pages.
    extensions = refpageType['extensions'].pagenames

    if not results.noauto:
        genOpts = GeneratorOptions(apiname = conventions.xml_api_name)
        registry = Registry(genOpts = genOpts)
        registry.loadFile(results.registry)

        if conventions.write_refpage_include:
            # Only extensions with a supported="..." attribute in this set
            # will be considered for extraction/generation.
            ext_names = set(k for k, v in registry.extdict.items()
                            if conventions.xml_api_name in v.supported.split(','))

            desired_extensions = ext_names.intersection(set(results.extension))
            for prefix in conventions.extension_index_prefixes:
                # Splits up into chunks, sorted within each chunk.
                filtered_extensions = sorted(
                    [name for name in desired_extensions
                     if name.startswith(prefix) and name not in extensions])
                for name in filtered_extensions:
                    extensions.add(name)
                    genExtension(baseDir, results.extpath, name, registry.extdict[name])

        sections = [
            (api.flags,        'Flag Types'),
            (api.enums,        'Enumerated Types'),
            (api.structs,      'Structures'),
            (api.protos,       'Prototypes'),
            (api.funcpointers, 'Function Pointers'),
            (api.basetypes,    f'{apiName} Scalar Types'),
            (extensions,       f'{apiName} Extensions'),
        ]

        # Summarize pages that were not generated, for good or bad reasons

        for (apiDict, title) in sections:
            # OpenXR was keeping a 'flagged' state which only printed out a
            # warning for the first non-generated page, but was otherwise
            # unused. This does not seem helpful.
            for page in apiDict:
                if page not in genDict:
                    # Page was not generated - why not?
                    if page in api.alias:
                        logDiag('(Benign, is an alias) Ref page for', title, page, 'is aliased into', api.alias[page])
                    elif page in api.flags and api.flags[page] is None:
                        logDiag('(Benign, no FlagBits defined) No ref page generated for ', title,
                                page)
                    else:
                        # Could introduce additional logic to detect
                        # external types and not emit them.
                        logWarn(f'No ref page generated for {title} {page}')

    if results.rewrite:
        # Generate Apache rewrite directives for refpage aliases
        # Each alias is in the pages[] list, but its key and its .name field
        # differ, unlike a non-alias.

        fp = open(results.rewrite, 'w', encoding='utf-8')

        for page in sorted(pages):
            p = pages[page]
            rewrite = p.name

            if page != rewrite:
                print('RewriteRule ^', page, '.html$ ', rewrite, '.html',
                      sep='', file=fp)
        fp.close()

    if results.nav:
        # Generate Antora navigation index
        genAntoraNav(results.nav)
