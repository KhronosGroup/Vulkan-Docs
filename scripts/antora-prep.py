#!/usr/bin/python3
#
# Copyright 2022-2023 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

"""Used to convert files from the asciidoctor spec tree to Antora module
format. Success is highly dependent on strict adherence to Vulkan spec
authoring conventions.

Usage: `antora-prep.py [-root path] -component path files`

- `-root` is the root path (repository root, usually) relative to which spec
  files are processed. Defaults to current directory if not specified.
- `-component` is the path to the module and component in which converted
  files are written (e.g. the component directory under which pages/,
  partials/, images/, etc. are located).
- `files` are asciidoc source files from the spec to convert.

Image files are linked from the component 'images' directory

Asciidoc markup files (.adoc) are scanned for the first title markup and
classified as partials or pages depending on whether it is a top-level title
or not. All .adoc files are rewritten to the component 'partials' directory, to
allow transclusion of pages to work (otherwise the transclusions would also
have to be rewritten).

pages then have additional markup injected immediately following the page
title to set custom attributes needed for the build. pages are then
symbolically linked from the component 'pages' directory to the actual
rewritten file in the 'partials' directory to follow Antora conventions.
"""

# For error and file-loading interfaces only
import argparse
import importlib
import os
import re
import sys
from generator import enquote
from reflib import loadFile, logDiag, logWarn, logErr, setLogFile, getBranch
from pathlib import Path

titleAnchorPat = re.compile(r'^\[\[(?P<anchor>[^,]+).*\]\]$')
titlePat = re.compile(r'^[=#] (?P<title>[A-Z].*)')
subtitlePat = re.compile(r'^[=#]{2,} (?P<title>[A-Z].*)')

Pages = 'pages'
Partials = 'partials'
Images = 'images'

def undefquote(s):
    """Quote a string for JavaScript, or return the JavaScript undefined
       value."""

    if s is not None:
        return enquote(s)
    else:
        return 'undefined'


def mapAnchor(anchor, title, pageMap, xrefMap, closeAnchor):
    """Rewrite a <<anchor{, title}>> xref -> xref:pagemap#anchor[{title}]
        - anchor - anchor name
        - title - xref description or '' if not specified, in which case the
          anchor text from the xrefMap is used if available
        - closeAnchor - True if closing >> is on this line, False otherwise
        - pageMap, xrefMap - per rewriteXrefs below
    """

    #@if anchor == 'features-shaderStorageImageReadWithoutFormat':
    #@    import pdb
    #@    pdb.set_trace()

    # Determine which page anchor this anchor comes from
    # If it cannot be determined, use the unmapped anchor
    #@ Simplify the page anchor if pageName == current page
    try:
        if title != '' or not closeAnchor:
            # Either a (possibly up to a line break) title is supplied, or
            # title is on the next line
            (pageAnchor, _) = xrefMap[anchor]
        else:
            # No explicit title. Infer one from anchor and xrefMap.
            (pageAnchor, title) = xrefMap[anchor]

            # If the title is *still* empty, make a note of it and just use
            # the anchor name
            if title == '':
                print(f'No title found for anchor {anchor}', file=sys.stderr)
                title = anchor

        # Page the page anchor comes from
        pageName = pageMap[pageAnchor]
        print(f'mapAnchor: anchor {anchor} pageAnchor {pageAnchor} -> pageName = {pageName}')

        xref = f'{pageName}#{anchor}'
    except:
        print(f'Cannot determine which page {anchor} comes from, passing through to Antora intact', file=sys.stderr)
        xref = f'{anchor}'

    # Remove extraneous whitespace
    title = ' '.join(title.split())

    if closeAnchor:
        return f'xref:{xref}[{title}]'
    else:
        return f'xref:{xref}[{title}'

def replaceAnchorText(match, pageMap, xrefMap):
    """Rewrite <<anchor,text>> to xref:newanchor[text]
        - match - match object, \1 = anchor, \2 = text
        - pageMap, xrefMap - per rewriteXrefs below
    """

    anchor = match.group(1)
    text = match.group(2)

    return mapAnchor(anchor, text, pageMap, xrefMap, closeAnchor=True)

def replaceAnchorOnly(match, pageMap, xrefMap):
    """Rewrite <<anchor>> to xref:newanchor[]
        - match - match object, \1 = anchor
        - pageMap, xrefMap - per rewriteXrefs below
    """

    anchor = match.group(1)

    return mapAnchor(anchor, '', pageMap, xrefMap, closeAnchor=True)

def replaceAnchorTrailingText(match, pageMap, xrefMap):
    """Rewrite <<anchor, to xref:newanchor[
        - match - match object, \1 = anchor, \2 = text (may be empty)
        - pageMap, xrefMap - per rewriteXrefs below
    """

    anchor = match.group(1)
    text = match.group(2)

    return mapAnchor(anchor, text, pageMap, xrefMap, closeAnchor=False)

class DocFile:
    """Information about a markup file being converted"""

    def __init__(self):
        """Constructor
           - lines - text of file as list of strings
           - root - common base directory for src files
           - component - path to component directory for outputs
           - srcpath - absolute path to file source
           - relpath - path to file source relative to root
           - dstpath - path to output file destination
           - dstlink - path to a an alias (symlink to) dstpath, used for
             files that need to be in both partials and pages directories.
           - category - file type - Pages, Partials, or Images. These are
             string variables containing the corresponding component
             subdirectory name.
           - title - page title for Pages, else ''
           - titleAnchor - page title anchor for Pages, else ''
           - anchors - asciidoc anchors found in the file
           - includes - asciidoc includes found in the file
           - pageMap - dictionary mapping a page anchor to a source file
             relpath
           - xrefMap - dictionary mapping an anchor within a page to a page
             anchor
        """

        self.lines = None
        self.root = None
        self.component = None
        self.srcpath = None
        self.relpath = None
        self.dstpath = None
        self.dstlink = None
        self.category = None
        self.title = ''
        self.titleAnchor = ''
        self.anchors = set()
        self.includes = set()

        self.pageMap = {}
        self.xrefMap = {}

    def findTitle(self):
        """Find category (Pages or Partials) and title, for Pages, in a
           .adoc markup file.

           Heuristic is to search the beginning of the file for a top-level
           asciidoc title, preceded immediately by an anchor for the page.

           Returns (category, title, titleLine, titleAnchor) with '' for a
           Partials title and '' if no title anchor is found."""

        """Chapter title block must be within this many lines of start of file"""
        maxLines = min(30, len(self.lines))

        """Default, if page title and/or page anchor not found"""
        titleAnchor = ''
        title = ''

        for lineno in range(0, maxLines):
            line = self.lines[lineno]

            # Look for the first anchor, which must precede the title to
            # apply to it (really, must precede it by exactly one line).
            match = titleAnchorPat.match(line)
            if match is not None:
                titleAnchor = match.group('anchor')
                continue

            # If we find a top-level title, it is a page.
            match = titlePat.match(line)
            if match is not None:
                return (Pages, match.group('title'), lineno, titleAnchor)

            # If we find a second-level or above title, it is a partial
            match = subtitlePat.match(line)
            if match is not None:
                return (Partials, match.group('title'), lineno, titleAnchor)

        # If we do not find a match in the first maxLines lines, assume it
        # is a partial.
        return(Partials, 'NO TITLE FOUND', -1, titleAnchor)

    def populate(self,
                 filename,
                 root,
                 component):
        """Populate data structures given file content and location.

           - filename - file to scan
           - root - absolute path to root under which all source files are
             read
           - component - absolute path to module / component directory under
             which all destination files are written
        """

        # Load file content
        self.srcpath = os.path.abspath(filename)
        self.lines, _ = loadFile(self.srcpath)
        if self.lines is None:
            raise RuntimeError(f'No such file {self.srcpath}')

        # Miscellaneous relevant paths
        self.root = root
        self.relpath = os.path.relpath(self.srcpath, root)
        self.component = component

        # Determine file category.
        # Only .adoc files are candidates for pages, which is verified by
        # looking at the file header for a top-level title.
        # .svg .jpg .png are always images
        # Anything else is a partial
        (_, fileext) = os.path.splitext(filename)

        # Defaults
        self.title = ''
        self.titleLine = 0
        self.titleAnchor = None

        if fileext in (('.svg', '.jpg', '.png')):
            self.category = Images
        elif fileext == '.adoc':
            (self.category,
             self.title,
             self.titleLine,
             self.titleAnchor) = self.findTitle()
        else:
            self.category = Partials

        # Determine destination path based on category
        # images/ are treated specially since there is only a single
        # directory and the component directory is already named Images.
        if self.category == Partials:
            self.dstpath = Path(self.component) / Partials / self.relpath
        elif self.category == Pages:
            # Save the page in partials/, link from pages/
            self.dstpath = Path(self.component) / Partials / self.relpath
            self.dstlink = Path(self.component) / Pages / self.relpath
        else:
            # Images go under images/, not under images/images/
            # This could fail if there were ever top-level images but as all
            # images used in the spec are required to be specified relative
            # to {images}, it is OK.
            self.dstpath = Path(self.component) / self.relpath


    def rewriteXrefs(self, pageMap = {}, xrefMap = {}):
        """Rewrite asciidoc <<>> xrefs into Antora xref: xrefs, including
           altering the xref target.

           - pageMap - map from page anchors to page names
           - xrefMap - map from anchors within a page to the page anchor"""

        # pageMap and xrefMap are used in functions called by re.subn, so
        # save them in members.
        self.pageMap = pageMap
        self.xrefMap = xrefMap

        # Xref markup may be broken across lines, and may or may not include
        # anchor text. Track whether the closing >> is being looked for at
        # start of line, or not.
        withinXref = False

        for lineno in range(0, len(self.lines)):
            line = self.lines[lineno]

            if withinXref:
                # Could use line.replace, but that does not return a match
                # count, so we cannot tell if the '>>' is missing.
                (line, count) = re.subn(r'>>', r']', line, count=1)
                if count == 0:
                    print(f'WARNING: No closing >> found on line {lineno} of {self.relpath}', file=sys.stderr)
                elif line[0] != ' ' and self.lines[lineno-1][-1] not in '[ ':
                    # Add whitespace corresponding to crushed-out newline on
                    # previous line, so title words do not run together.
                    self.lines[lineno-1] += ' '
                withinXref = False

            # Now look for all xrefs starting on this line and remap them,
            # including remapping the anchor.

            # First, complete xrefs with alt-text (<<anchor, text>>)
            (line, count) = re.subn(r'<<([^,>]*),([^>]+)>>',
                lambda match: replaceAnchorText(match, pageMap, xrefMap),
                line)

            # Next, complete xrefs without alt-text (<<anchor>>)
            (line, count) = re.subn(r'<<([^,>]*)>>',
                lambda match: replaceAnchorOnly(match, pageMap, xrefMap),
                line)

            # Finally, if there is a trailing '<<anchor,' at EOL, remap it
            # and set the flag so the terminating '>>' on the next line will
            # be mapped into an xref closing ']'.
            (line, count) = re.subn(r'<<([^,>]*),([^>]*)$',
                lambda match: replaceAnchorTrailingText(match, pageMap, xrefMap),
                line)
            if count > 0:
                withinXref = True

            self.lines[lineno] = line

    def __str__(self):
        lines = [
            f'Input file {filename}: {len(self.lines)} lines',
            f'root = {self.root} component = {self.component} relpath = {self.relpath}',
            f'category = {self.category} dstpath = {self.dstpath}',
            f'title = {self.title}',
            f'titleAnchor = {self.titleAnchor}',
        ]
        return '\n'.join(lines)

    def removeDestination(self, path, text, overwrite):
        """Remove a destination file, if it exists and overwrite is true.
           Ensure the destination directory exists.

            path - file pathname
            text - descriptive text for errors
            overwrite - if True, replace existing output file
        """

        if os.path.exists(path):
            if overwrite:
                # print(f'Removing {text}: {path}')
                os.remove(path)
            else:
                raise RuntimeError(f'Will not overwrite {text}: {path}')

        dir = os.path.dirname(path)
        if not os.path.exists(dir):
            # print(f'Creating {text} directory {dir}')
            os.makedirs(dir)

    def rewriteFile(self, overwrite = True, pageHeaders = None):
        """Write source file to component directory. Images are just symlinked
           to the external file. Pages are rewritten to Partials, then
           symlinked to Pages.

           - overwrite - if True, replace existing output files
           - pageHeaders - if not None, a list of strings to inject
             following the chapter heading in each page

           <<>>-style xrefs are assumed to be rewritten prior to calling
           rewriteFile.

           May still need to rewrite custom macros.
        """

        self.removeDestination(self.dstpath, 'destination file', overwrite)

        if self.category == Images:
            # Just symlink destination image to source
            # print(f'Symlinking {self.dstpath} -> {self.srcpath}')
            os.symlink(self.srcpath, self.dstpath)
        elif self.category == Partials:
            self.writeFile(self.dstpath)
        elif self.category == Pages:
            if pageHeaders is not None:
                # Add blank lines before and after the pageHeaders to avoid
                # coalescing with file content.
                lines = self.lines[0:self.titleLine+1]
                lines += ['\n'] + pageHeaders + ['\n']
                lines = lines + self.lines[self.titleLine+1:]
                self.lines = lines

            # Inject page headers immediately following page title

            self.writeFile(self.dstpath)

            if self.dstlink is None:
                RuntimeError(f'Wrote Page {self.dstpath} to Partials, but no Pages link supplied')
            else:
                self.removeDestination(self.dstlink, 'destination link', overwrite)
                os.symlink(self.dstpath, self.dstlink)

    def writeFile(self, path):
        """Write self.lines[] to file at specified path"""

        try:
            fp = open(path, 'w', encoding='utf8')
        except:
            raise RuntimeError(f'Cannot open output file {path}')

        for line in self.lines:
            print(line, file=fp, end='')

        fp.close()

def testHarness():
    def printFile(label, lines):
        print(label)
        print('------------------')
        for line in lines:
            print(line)

    # Test harness
    docFile = DocFile()
    docFile.lines = [
        '<<ext,ext chapter>> <<ext-label,',
        'ext chapter/label>>',
        '<<core>>, <<core-label, core chapter/label',
        '>>'
    ]

    pageMap = {
        'ext'  : 'file/ext.adoc',
        'core' : 'file/core.adoc',
    }
    xrefMap = {
        'ext'       : [ 'ext', '' ],
        'ext-label' : [ 'ext', 'LABELLED ext-label' ],
        'core'      : [ 'core', 'Core Title' ],
        'core-label': [ 'core', 'Core Label Title' ],
    }

    printFile('Original File', docFile.lines)

    docFile.rewriteXrefs(pageMap, xrefMap)

    printFile('Edited File', docFile.lines)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-root', action='store', dest='root',
                        default=os.getcwd(),
                        help='Specify root directory under which files are located (default current directory)')
    parser.add_argument('-pageHeaders', action='store', dest='pageHeaders',
                        default=None,
                        help='Specify file whose contents are injected after title of each converted page')
    parser.add_argument('-component', action='store', dest='component',
                        required=True,
                        help='Specify module / component directory in which converted files are written')
    #parser.add_argument('-htmlspec', action='store', dest='htmlspec',
    #                    default=None, required=False,
    #                    help='Specify HTML of generated spec to extract anchor mapping from')
    parser.add_argument('-xrefpath', action='store', dest='xrefpath',
                        default=None, required=False,
                        help='Specify path to xrefMap.py containing map of anchors to chapter anchors')
    parser.add_argument('-pagemappath', action='store', dest='pagemappath',
                        default=None, required=False,
                        help='Specify path to output pageMap.cjs containing map of anchors to chapter anchors')
    parser.add_argument('-filelist', action='store',
                        default=None, required=False,
                        help='Specify file containing a list of filenames to convert, one/line')
    parser.add_argument('files', metavar='filename', nargs='*',
                        help='Specify name of a single file to convert')

    args = parser.parse_args()

    args.root = os.path.abspath(args.root)
    args.component = os.path.abspath(args.component)

    if args.pageHeaders is not None:
        args.pageHeaders, _ = loadFile(args.pageHeaders)

    if False:
        testHarness()
        sys.exit(0)

    # Initialize dictionaries
    pageInfo = {}
    pageMap = {}

    # The xrefmap is imported from the 'xrefMap' module, if it exists
    try:
        if args.xrefpath is not None:
            sys.path.append(args.xrefpath)
        from xrefMap import xrefMap
    except:
        print('WARNING: No module xrefMap containing xrefMap dictionary', file=sys.stderr)
        xrefMap = {}

    # If a file containing a list of files was specified, add each one.
    # Could try using os.walk() instead, but that is very slow.
    if args.filelist is not None:
        count = 0
        lines, _ = loadFile(args.filelist)
        if lines is None:
            raise RuntimeError(f'Error reading filelist {args.filelist}')
        for line in lines:
            path = line.rstrip()
            if path[0].isalpha() and path.endswith('.adoc'):
                args.files.append(path)
                count = count + 1
        print(f'Read {count} paths from {args.filelist}')

    for filename in args.files:
        # Create data structure representing the file.
        docFile = DocFile()
        docFile.populate(filename = filename,
                         root = args.root,
                         component = args.component)
        # print(docFile, '\n')

        # Save information about the file under its relpath
        pageInfo[docFile.relpath] = docFile

        # Save mapping from page anchor to its relpath
        if docFile.titleAnchor is not None:
            pageMap[docFile.titleAnchor] = docFile.relpath

    # All files have been read and classified.
    # Rewrite them in memory.

    for key in pageInfo:
        # Look for <<>>-style anchors and rewrite them to Antora xref-style
        # anchors using the pageMap (of top-level anchors to page names) and
        # xrefmap (of anchors to top-level anchors).
        docFile = pageInfo[key]

        ## print(f'*** Rewriting {key}')
        ## print(docFile, '\n')

        docFile.rewriteXrefs(pageMap, xrefMap)
        docFile.rewriteFile(overwrite = True, pageHeaders = args.pageHeaders)

    # Write the pageMap to a .cjs file for use in the Antora build's
    # specmacros extensions. The xrefMap is already written in JS form.
    if args.pagemappath is not None:
        try:
            fp = open(args.pagemappath, 'w', encoding='utf8')
        except:
            raise RuntimeError(f'Cannot open output pageMap.cjs file {args.pagemappath}')

        print('exports.pageMap = {', file=fp)
        for pageAnchor in sorted(pageMap):
            pageName = pageMap[pageAnchor]
            print(f'    {undefquote(pageAnchor)} : {undefquote(pageName)},', file=fp)
        print('}', file=fp)

        fp.close()

##        if not os.path.exists(args.xrefmap):
##            raise UserWarning(f'Specified xrefmap {args.xrefmap} does not exist')
##        if args.xrefmap[-3:] != '.py':
##            raise UserWarning(f'Specified xrefmap {args.xrefmap} is not a .py file')
##
##        abspath = os.path.abspath(args.xrefmap)
##        xrefdir = os.path.dirname(os.path.abspath(args.xrefmap))
##        sys.path.append(dir)
##
##        xrefbase = os.path.split(args.xrefmap)[1]
##        xrefbase = os.path.splitext(xrefbase)[0]
##
##            raise UserWarning(f'Specified xrefmap {args.xrefmap} does not exist')
