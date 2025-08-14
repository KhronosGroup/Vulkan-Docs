#!/usr/bin/env python3
#
# Copyright 2016-2025 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# genRef.py - create API ref pages from spec source files
#
# Usage: genRef.py files

import argparse
import io
import os
import re
import sys
from collections import OrderedDict
from reflib import (findRefs, fixupRefs, loadFile, logDiag, logWarn, logErr,
                    printPageInfo, setLogFile, importFileModule)
from reg import Registry
from generator import GeneratorOptions
from parse_dependency import dependencyNames
from apiconventions import APIConventions


# refpage 'type' attributes which are API entities and contain structured
# content such as API includes, valid usage blocks, etc.
refpage_api_types = (
    'basetypes',
    'consts',
    'defines',
    'enums',
    'flags',
    'funcpointers',
    'handles',
    'protos',
    'structs',
)

# Other refpage types - SPIR-V builtins, API feature blocks, etc. - which do
# not have structured content.
refpage_other_types = (
    'builtins',
    'feature',
    'freeform',
    'spirv'
)

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
    # REUSE-IgnoreStart
    print('// Copyright 2014-2025 The Khronos Group Inc.', file=fp)
    print('//', file=fp)
    # This works around constraints of the 'reuse' tool
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
          f"include::{{config}}/copyright-ccby{conventions.file_suffix}[]",
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
        return f"basetype:{name}"
    if name in api.defines:
        return f"dlink:{name}"
    if name in api.enums:
        return f"elink:{name}"
    if name in api.flags:
        return f"tlink:{name}"
    if name in api.funcpointers:
        return f"tlink:{name}"
    if name in api.handles:
        return f"slink:{name}"
    if name in api.protos:
        return f"flink:{name}"
    if name in api.structs:
        return f"slink:{name}"
    if name == 'TBD':
        return 'No cross-references are available'

    # Fallthrough - cannot find API type for name, so treat as a reflink.
    # This mostly affects feature and extension names e.g. VK_VERSION_1_0.
    return f"reflink:{name}"


def seeAlsoList(apiName, explicitRefs=None, apiAliases=[]):
    """Return an asciidoc string with a list of 'See Also' references for the
    API entity 'apiName', based on the relationship mapping in the api module.

    'explicitRefs' is a list of additional cross-references.

    If apiAliases is not None, it is a list of aliases of apiName whose
    cross-references will also be included.

    If no relationships are available, return None."""

    refs = set(())

    # apiName and its aliases are treated equally
    allApis = apiAliases.copy()
    allApis.append(apiName)

    # Add all the implicit references from the XML definition of the API
    for name in allApis:
        if name in api.mapDict:
            refs.update(api.mapDict[name])

    # Add all the explicit references from the refpage block attributes
    if explicitRefs is not None:
        if isinstance(explicitRefs, str):
            explicitRefs = explicitRefs.split()
        refs.update(name for name in explicitRefs)

    # Add extensions / core versions based on dependencies
    for name in allApis:
        if name in api.requiredBy:
            for (base,dependency) in api.requiredBy[name]:
                refs.add(base)
                if dependency is not None:
                    # 'dependency' may be a boolean expression of extension
                    # names.
                    # Extract them for use in cross-references.
                    for extname in dependencyNames(dependency):
                        refs.add(extname)

    if len(refs) == 0:
        return None
    else:
        return f"{', '.join(macroPrefix(name) for name in sorted(refs))}\n"


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
                incPath = f"{specDir}/{path}"
                # Remap to be relative to baseDir
                newPath = os.path.relpath(incPath, baseDir)
                newLine = f"include::{newPath}[]\n"
                logDiag('remapIncludes: remapping', line, '->', newLine)
                newLines.append(newLine)
            else:
                # An asciidoctor variable starts the path.
                # This must be an absolute path, not needing to be rewritten.
                newLines.append(line)
        else:
            newLines.append(line)
    return newLines


def refPageShell(pageName, pageDesc, fp, head_content = None, sections=None, tail_content=None, man_section=3):
    """Generate body of a reference page.

    - pageName - string name of the page
    - pageDesc - string short description of the page
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

    s = f'{pageName}({man_section})'
    print(f"= {s}",
          '',
          conventions.extra_refpage_body,
          '',
          sep='\n', file=fp)
    if pageDesc.strip() == '':
        pageDesc = 'NO SHORT DESCRIPTION PROVIDED'
        logWarn('refPageHead: no short description provided for', pageName)

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

    refPageShell(pageName, pageDesc, fp, head_content=None, sections=sections)


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
            f"This page is extracted from the {specName} Specification. ",
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
    if pi.type in refpage_api_types:
        if pi.include is None:
            logWarn('emitPage:', pageName, 'INCLUDE is None, no page generated')
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
                logWarn('emitPage: unknown field type:', pi.type,
                        'for', pi.name)
            lines = remapIncludes(file[pi.param:pi.body], baseDir, specDir)
            fieldText = ''.join(lines)

        # Description text
        if pi.body != pi.include:
            lines = remapIncludes(file[pi.body:pi.end + 1], baseDir, specDir)
            descText = ''.join(lines)
        else:
            descText = None
            logWarn('emitPage: INCLUDE == BODY, so description will be empty for', pi.name)
            if pi.begin != pi.include:
                logWarn('emitPage: Note: BEGIN != INCLUDE, so the description might be incorrectly located before the API include!')
    elif pi.type in refpage_other_types:
        specText = None
        descText = ''.join(file[pi.begin:pi.end + 1])
    else:
        # This should be caught in the spec markup checking tests
        logErr(f"emitPage: refpage type='{pi.type}' is unrecognized")

    # Rewrite asciidoctor xrefs to resolve properly in refpages
    specURL = conventions.specURL(pi.spec)

    specText = xrefRewrite(specText, specURL)
    fieldText = xrefRewrite(fieldText, specURL)
    descText = xrefRewrite(descText, specURL)

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
                seeAlso=seeAlsoList(pi.name, pi.refs, pi.alias.split()),
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
        f"  * The {apiName} Specification.\n"))

    refPageHead(pi.name,
                pi.desc,
                ''.join(file[pi.begin:pi.include + 1]),
                None, None,
                txt,
                fp)
    refPageTail(pageName=pi.name,
                specType=pi.spec,
                specAnchor=pi.anchor,
                seeAlso=seeAlsoList(pi.name, pi.refs, pi.alias.split()),
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
        flagBits = f"{name}FlagBits{author}"
        desc = f"Bitmask of {flagBits}"
    else:
        logWarn('autoGenFlagsPage:', pageName, 'does not end in "Flags{author ID}". Cannot infer FlagBits type.')
        flagBits = None
        desc = f"Unknown {apiName} flags type"

    # Description text
    if flagBits is not None:
        txt = ''.join((
            f"etext:{flagName}",
            f" is a mask of zero or more elink:{flagBits}.\n",
            'It is used as a member and/or parameter of the structures and commands\n',
            'in the See Also section below.\n'))
    else:
        txt = ''.join((
            f"etext:{flagName}",
            f" is an unknown {apiName} type, assumed to be a bitmask.\n"))

    refPageHead(flagName,
                desc,
                makeAPIInclude('flags', flagName),
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
    pageName = f'{baseDir}/{handleName}{conventions.file_suffix}'
    fp = open(pageName, 'w', encoding='utf-8')

    # Add a dictionary entry for this page
    global genDict
    genDict[handleName] = None
    logDiag('autoGenHandlePage:', pageName)

    # Short description
    desc = f"{apiName} object handle"

    descText = ''.join((
        f"sname:{handleName}",
        ' is an object handle type, referring to an object used\n',
        f"by the {apiName} implementation. These handles are created or allocated\n",
        f"by the @@ TBD @@ function, and used by other {apiName} structures\n",
        'and commands in the See Also section below.\n'))

    refPageHead(handleName,
                desc,
                makeAPIInclude('handles', handleName),
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
    # We do not care the newline format used here.
    file, _ = loadFile(specFile)
    if file is None:
        return

    # Save the path to this file for later use in rewriting relative includes
    specDir = os.path.dirname(os.path.abspath(specFile))

    pageMap = findRefs(file, specFile)
    logDiag(f"{specFile}: found", len(pageMap.keys()), 'potential pages')

    sys.stderr.flush()

    # Fix up references in pageMap
    fixupRefs(pageMap, specFile, file)

    # Create each page, if possible
    pages = {}

    for name in sorted(pageMap):
        pi = pageMap[name]

        # Only generate the page if it is in the requested build
        # 'freeform' pages are always generated
        # 'feature' pages (core versions & extensions) are generated if they are in
        # the requested feature list
        # All other pages (APIs) are generated if they are in the API map for
        # the build.
        if pi.type in refpage_api_types:
            if name not in api.typeCategory:
                # Also check aliases of name - api.nonexistent is the same
                # mapping used to rewrite *link: macros in this build.
                if name not in api.nonexistent:
                    logWarn(f'genRef: NOT generating feature page {name} - API not in this build')
                    continue
                else:
                    logWarn(f'genRef: generating feature page {name} because its alias {api.nonexistent[name]} exists')
        elif pi.type in refpage_other_types:
            # The only non-API type which can be checked is a feature refpage
            if pi.type == 'feature':
                if name not in api.features:
                    logWarn(f'genRef: NOT generating feature page {name} - feature not in this build')
                    continue

        printPageInfo(pi, file)

        if pi.Warning:
            logDiag('genRef:', f"{pi.name}:", pi.Warning)

        if pi.extractPage:
            emitPage(baseDir, specDir, pi, file)
        elif pi.type == 'enums':
            autoGenEnumsPage(baseDir, pi, file)
        elif pi.type == 'flags':
            autoGenFlagsPage(baseDir, pi.name)
        else:
            # Do not extract this page
            logWarn('genRef: Cannot extract or autogenerate:', pi.name)

        pages[pi.name] = pi
        for alias in pi.alias.split():
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
        '* xref:index.adoc[{apiName} API Reference Pages]',
    ))

    printCopyrightSourceComments(fp)
    print(head, file=fp)


    # Add the table of contents, split up by API type.
    # There are many ways this could be done.
    sections = [
        [api.protos,       'protos',       f'{apiName} Commands'],
        [api.handles,      'handles',      'Object Handles'],
        [api.structs,      'structs',      'Structures'],
        [api.enums,        'enums',        'Enumerations'],
        [api.flags,        'flags',        'Flags'],
        [api.funcpointers, 'funcpointers', 'Function Pointer Types'],
        [api.basetypes,    'basetypes',    f'{apiName} Scalar types'],
        [api.defines,      'defines',      'C Macro Definitions'],
        [extensions,       'extensions',   f'{apiName} Extensions']
    ]

    def apiSortKey(name):
        """Sort on refpage names not considering any 'vk' prefix"""
        name = name.upper()

        if name[0:3] == 'VK_':
            return name[3:]
        elif name[0:2] == 'VK':
            return name[2:]
        else:
            return name

    for (apiDict, label, title) in sections:
        print(f'\n[[{label}]]', file=fp)
        print(f'* {title}', file=fp)

        if label == 'extensions':
            # Extensions are already sorted the way we want
            keys = apiDict.keys()
        else:
            keys = sorted(apiDict.keys(), key=apiSortKey)

        lastLetter = ''

        for refPage in keys:
            # Also generate links for aliases, to be complete
            if 'FlagBits' in refPage and conventions.unified_flag_refpages:
                # OpenXR does not create separate ref pages for FlagBits:
                # FlagBits includes go in the Flags refpage.
                # Vulkan has separate pages.
                continue

            letter = apiSortKey(refPage)[0:1]

            if letter != lastLetter:
                # Start new section
                print(f'* {letter}', file=fp)
                lastLetter = letter

            # Add this page to the list, or link to its alias if that exists
            if refPage not in api.alias:
                print(f'** xref:source/{refPage}{conventions.file_suffix}[{refPage}]', file=fp)
            else:
                alias = api.alias[refPage]
                print(f'** xref:source/{alias}{conventions.file_suffix}[{refPage}]', file=fp)

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
    declares = []
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

        declares.append(req_name)

    appbody = None
    tail_content = None
    if extpath is not None:
        try:
            appPath = f"{extpath}/{conventions.extension_file_path(name)}"
            appfp = open(appPath, 'r', encoding='utf-8')
            appbody = appfp.read()
            appfp.close()

            # Transform internal links to crosslinks
            specURL = conventions.specURL()
            appbody = xrefRewrite(appbody, specURL)
        except FileNotFoundError:
            print('Cannot find extension appendix for', name)
            logWarn('Cannot find extension appendix for', name)

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

    refPageShell(name,
                 conventions.extension_short_description(elem),
                 fp,
                 appbody,
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
                seeAlso=seeAlsoList(name, declares),
                fp=fp,
                auto=True,
                leveloffset=leveloffset)
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
    parser.add_argument('-genpath', action='store',
                        default='gen',
                        help='Path to directory containing generated files')
    parser.add_argument('-basedir', action='store', dest='baseDir',
                        default=None,
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
    parser.add_argument('-nav', action='store',
                        default=None,
                        help='Name of output file to write an Antora navigation index to')
    parser.add_argument('-toc', action='store',
                        default=None,
                        help='Name of output file to write an alphabetical TOC to')
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
        d = genRef(file, baseDir)
        pages.update(d)

    # Now figure out which pages were not generated from the spec.
    # This relies on the dictionaries of API constructs in the api module.

    if not results.noauto:
        # Must have an apiname selected to avoid complaints from
        # registry.loadFile, even though it is irrelevant to our uses.
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
                    # logWarn('NOT autogenerating extension refpage for', name)
                    extensions[name] = None
                    genExtension(baseDir, results.extpath, name, registry.extdict[name])

        sections = [
            (api.flags,        'Flag Types'),
            (api.enums,        'Enumerated Types'),
            (api.structs,      'Structures'),
            (api.protos,       'Prototypes'),
            (api.funcpointers, 'Function Pointers'),
            (api.basetypes,    f"{apiName} Scalar Types"),
            (extensions,       f"{apiName} Extensions"),
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
                        logWarn('No ref page generated for  ', title, page)

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

    if results.nav:
        # Generate Antora navigation TOC
        genAntoraNav(results.nav)

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
