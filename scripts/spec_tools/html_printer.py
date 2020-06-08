"""Defines HTMLPrinter, a BasePrinter subclass for a single-page HTML results file."""

# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>

import html
import re
from collections import namedtuple

from .base_printer import BasePrinter, getColumn
from .shared import (MessageContext, MessageType, generateInclude,
                     getHighlightedRange)

# Bootstrap styles (for constructing CSS class names) associated with MessageType values.
MESSAGE_TYPE_STYLES = {
    MessageType.ERROR: 'danger',
    MessageType.WARNING: 'warning',
    MessageType.NOTE: 'secondary'
}


# HTML Entity for a little emoji-icon associated with MessageType values.
MESSAGE_TYPE_ICONS = {
    MessageType.ERROR: '&#x2297;',  # makeIcon('times-circle'),
    MessageType.WARNING: '&#9888;',  # makeIcon('exclamation-triangle'),
    MessageType.NOTE: '&#x2139;'  # makeIcon('info-circle')
}

LINK_ICON = '&#128279;'  # link icon


class HTMLPrinter(BasePrinter):
    """Implementation of BasePrinter for generating diagnostic reports in HTML format.

    Generates a single file containing neatly-formatted messages.

    The HTML file loads Bootstrap 4 as well as 'prism' syntax highlighting from CDN.
    """

    def __init__(self, filename):
        """Construct by opening the file."""
        self.f = open(filename, 'w', encoding='utf-8')
        self.f.write("""<!doctype html>
        <html lang="en"><head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/themes/prism.min.css" integrity="sha256-N1K43s+8twRa+tzzoF3V8EgssdDiZ6kd9r8Rfgg8kZU=" crossorigin="anonymous" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/line-numbers/prism-line-numbers.min.css" integrity="sha256-Afz2ZJtXw+OuaPX10lZHY7fN1+FuTE/KdCs+j7WZTGc=" crossorigin="anonymous" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/line-highlight/prism-line-highlight.min.css" integrity="sha256-FFGTaA49ZxFi2oUiWjxtTBqoda+t1Uw8GffYkdt9aco=" crossorigin="anonymous" />
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css" integrity="sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO" crossorigin="anonymous">
        <style>
        pre {
            overflow-x: scroll;
            white-space: nowrap;
        }
        </style>
        <title>check_spec_links results</title>
        </head>
        <body>
        <div class="container">
        <h1><code>check_spec_links.py</code> Scan Results</h1>
        """)
        #
        self.filenameTransformer = re.compile(r'[^\w]+')
        self.fileRange = {}
        self.fileLines = {}
        self.backLink = namedtuple(
            'BackLink', ['lineNum', 'col', 'end_col', 'target', 'tooltip', 'message_type'])
        self.fileBackLinks = {}

        self.nextAnchor = 0
        super().__init__()

    def close(self):
        """Write the tail end of the file and close it."""
        self.f.write("""
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/prism.min.js" integrity="sha256-jc6y1s/Y+F+78EgCT/lI2lyU7ys+PFYrRSJ6q8/R8+o=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/keep-markup/prism-keep-markup.min.js" integrity="sha256-mP5i3m+wTxxOYkH+zXnKIG5oJhXLIPQYoiicCV1LpkM=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/components/prism-asciidoc.min.js" integrity="sha256-NHPE1p3VBIdXkmfbkf/S0hMA6b4Ar4TAAUlR+Rlogoc=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/line-numbers/prism-line-numbers.min.js" integrity="sha256-JfF9MVfGdRUxzT4pecjOZq6B+F5EylLQLwcQNg+6+Qk=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.15.0/plugins/line-highlight/prism-line-highlight.min.js" integrity="sha256-DEl9ZQE+lseY13oqm2+mlUr+sVI18LG813P+kzzIm8o=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.3.1/jquery.slim.min.js" integrity="sha256-3edrmyuQ0w65f8gfBsqowzjJe2iM6n0nKciPUp8y+7E=" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.6/esm/popper.min.js" integrity="sha256-T0gPN+ySsI9ixTd/1ciLl2gjdLJLfECKvkQjJn98lOs=" crossorigin="anonymous"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js" integrity="sha384-ChfqqxuZUCnJSK3+MXmPNIyE6ZbWh2IMqE241rYiqJxyMiZ6OW/JmZQ5stwEULTy" crossorigin="anonymous"></script>
        <script>
        $(function () {
            $('[data-toggle="tooltip"]').tooltip();
            function autoExpand() {
                var hash = window.location.hash;
                if (!hash) {
                    return;
                }
                $(hash).parents().filter('.collapse').collapse('show');
            }
            window.addEventListener('hashchange', autoExpand);
            $(document).ready(autoExpand);
            $('.accordion').on('shown.bs.collapse', function(e) {
                e.target.parentNode.scrollIntoView();
            })
        })
        </script>
        </body></html>
        """)
        self.f.close()

    ###
    # Output methods: these all write to the HTML file.
    def outputResults(self, checker, broken_links=True,
                      missing_includes=False):
        """Output the full results of a checker run.

        Includes the diagnostics, broken links (if desired),
        missing includes (if desired), and excerpts of all files with diagnostics.
        """
        self.output(checker)
        self.outputBrokenAndMissing(
            checker, broken_links=broken_links, missing_includes=missing_includes)

        self.f.write("""
        <div class="container">
        <h2>Excerpts of referenced files</h2>""")
        for fn in self.fileRange:
            self.outputFileExcerpt(fn)
        self.f.write('</div><!-- .container -->\n')

    def outputChecker(self, checker):
        """Output the contents of a MacroChecker object.

        Starts and ends the accordion populated by outputCheckerFile().
        """
        self.f.write(
            '<div class="container"><h2>Per-File Warnings and Errors</h2>\n')
        self.f.write('<div class="accordion" id="fileAccordion">\n')
        super(HTMLPrinter, self).outputChecker(checker)
        self.f.write("""</div><!-- #fileAccordion -->
        </div><!-- .container -->\n""")

    def outputCheckerFile(self, fileChecker):
        """Output the contents of a MacroCheckerFile object.

        Stashes the lines of the file for later excerpts,
        and outputs any diagnostics in an accordion card.
        """
        # Save lines for later
        self.fileLines[fileChecker.filename] = fileChecker.lines

        if not fileChecker.numDiagnostics():
            return

        self.f.write("""
        <div class="card">
        <div class="card-header" id="{id}-file-heading">
        <div class="row">
        <div class="col">
        <button data-target="#collapse-{id}" class="btn btn-link btn-primary mb-0 collapsed" type="button" data-toggle="collapse" aria-expanded="false" aria-controls="collapse-{id}">
        {relativefn}
        </button>
        </div>
        """.format(id=self.makeIdentifierFromFilename(fileChecker.filename), relativefn=html.escape(self.getRelativeFilename(fileChecker.filename))))
        self.f.write('<div class="col-1">')
        warnings = fileChecker.numMessagesOfType(MessageType.WARNING)
        if warnings > 0:
            self.f.write("""<span class="badge badge-warning" data-toggle="tooltip" title="{num} warnings in this file">
                            {icon}
                            {num}<span class="sr-only"> warnings</span></span>""".format(num=warnings, icon=MESSAGE_TYPE_ICONS[MessageType.WARNING]))
        self.f.write('</div>\n<div class="col-1">')
        errors = fileChecker.numMessagesOfType(MessageType.ERROR)
        if errors > 0:
            self.f.write("""<span class="badge badge-danger" data-toggle="tooltip" title="{num} errors in this file">
                            {icon}
                            {num}<span class="sr-only"> errors</span></span>""".format(num=errors, icon=MESSAGE_TYPE_ICONS[MessageType.ERROR]))
        self.f.write("""
        </div><!-- .col-1 -->
        </div><!-- .row -->
        </div><!-- .card-header -->
        <div id="collapse-{id}" class="collapse" aria-labelledby="{id}-file-heading" data-parent="#fileAccordion">
        <div class="card-body">
        """.format(id=self.makeIdentifierFromFilename(fileChecker.filename)))
        super(HTMLPrinter, self).outputCheckerFile(fileChecker)

        self.f.write("""
        </div><!-- .card-body -->
        </div><!-- .collapse -->
        </div><!-- .card -->
        <!-- ..................................... -->
        """.format(id=self.makeIdentifierFromFilename(fileChecker.filename)))

    def outputMessage(self, msg):
        """Output a Message."""
        anchor = self.getUniqueAnchor()

        self.recordUsage(msg.context,
                         linkBackTarget=anchor,
                         linkBackTooltip='{}: {} [...]'.format(
                             msg.message_type, msg.message[0]),
                         linkBackType=msg.message_type)

        self.f.write("""
        <div class="card">
        <div class="card-body">
        <h5 class="card-header bg bg-{style}" id="{anchor}">{icon} {t} Line {lineNum}, Column {col} (-{arg})</h5>
        <p class="card-text">
        """.format(
            anchor=anchor,
            icon=MESSAGE_TYPE_ICONS[msg.message_type],
            style=MESSAGE_TYPE_STYLES[msg.message_type],
            t=self.formatBrief(msg.message_type),
            lineNum=msg.context.lineNum,
            col=getColumn(msg.context),
            arg=msg.message_id.enable_arg()))
        self.f.write(self.formatContext(msg.context))
        self.f.write('<br/>')
        for line in msg.message:
            self.f.write(html.escape(line))
            self.f.write('<br />\n')
        self.f.write('</p>\n')
        if msg.see_also:
            self.f.write('<p>See also:</p><ul>\n')
            for see in msg.see_also:
                if isinstance(see, MessageContext):
                    self.f.write(
                        '<li>{}</li>\n'.format(self.formatContext(see)))
                    self.recordUsage(see,
                                     linkBackTarget=anchor,
                                     linkBackType=MessageType.NOTE,
                                     linkBackTooltip='see-also associated with {} at {}'.format(msg.message_type, self.formatContextBrief(see)))
                else:
                    self.f.write('<li>{}</li>\n'.format(self.formatBrief(see)))
            self.f.write('</ul>')
        if msg.replacement is not None:
            self.f.write(
                '<div class="alert alert-primary">Hover the highlight text to view suggested replacement.</div>')
        if msg.fix is not None:
            self.f.write(
                '<div class="alert alert-info">Note: Auto-fix available.</div>')
        if msg.script_location:
            self.f.write(
                '<p>Message originated at <code>{}</code></p>'.format(msg.script_location))
        self.f.write('<pre class="line-numbers language-asciidoc" data-start="{}"><code>'.format(
            msg.context.lineNum))
        highlightStart, highlightEnd = getHighlightedRange(msg.context)
        self.f.write(html.escape(msg.context.line[:highlightStart]))
        self.f.write(
            '<span class="border border-{}"'.format(MESSAGE_TYPE_STYLES[msg.message_type]))
        if msg.replacement is not None:
            self.f.write(
                ' data-toggle="tooltip" title="{}"'.format(msg.replacement))
        self.f.write('>')
        self.f.write(html.escape(
            msg.context.line[highlightStart:highlightEnd]))
        self.f.write('</span>')
        self.f.write(html.escape(msg.context.line[highlightEnd:]))
        self.f.write('</code></pre></div></div>')

    def outputBrokenLinks(self, checker, broken):
        """Output a table of broken links.

        Called by self.outputBrokenAndMissing() if requested.
        """
        self.f.write("""
        <div class="container">
        <h2>Missing Referenced API Includes</h2>
        <p>Items here have been referenced by a linking macro, so these are all broken links in the spec!</p>
        <table class="table table-striped">
        <thead>
        <th scope="col">Add line to include this file</th>
        <th scope="col">or add this macro instead</th>
        <th scope="col">Links to this entity</th></thead>
        """)

        for entity_name, uses in sorted(broken.items()):
            category = checker.findEntity(entity_name).category
            anchor = self.getUniqueAnchor()
            asciidocAnchor = '[[{}]]'.format(entity_name)
            include = generateInclude(dir_traverse='../../generated/',
                                      generated_type='api',
                                      category=category,
                                      entity=entity_name)
            self.f.write("""
            <tr id={}>
            <td><code class="text-dark language-asciidoc">{}</code></td>
            <td><code class="text-dark">{}</code></td>
            <td><ul class="list-inline">
            """.format(anchor, include, asciidocAnchor))
            for context in uses:
                self.f.write(
                    '<li class="list-inline-item">{}</li>'.format(self.formatContext(context, MessageType.NOTE)))
                self.recordUsage(
                    context,
                    linkBackTooltip='Link broken in spec: {} not seen'.format(
                        include),
                    linkBackTarget=anchor,
                    linkBackType=MessageType.NOTE)
            self.f.write("""</ul></td></tr>""")
        self.f.write("""</table></div>""")

    def outputMissingIncludes(self, checker, missing):
        """Output a table of missing includes.

        Called by self.outputBrokenAndMissing() if requested.
        """
        self.f.write("""
        <div class="container">
        <h2>Missing Unreferenced API Includes</h2>
        <p>These items are expected to be generated in the spec build process, but aren't included.
        However, as they also are not referenced by any linking macros, they aren't broken links - at worst they are undocumented entities,
        at best they are errors in <code>check_spec_links.py</code> logic computing which entities get generated files.</p>
        <table class="table table-striped">
        <thead>
        <th scope="col">Add line to include this file</th>
        <th scope="col">or add this macro instead</th>
        """)

        for entity in sorted(missing):
            fn = checker.findEntity(entity).filename
            anchor = '[[{}]]'.format(entity)
            self.f.write("""
            <tr>
            <td><code class="text-dark">{filename}</code></td>
            <td><code class="text-dark">{anchor}</code></td>
            """.format(filename=fn, anchor=anchor))
        self.f.write("""</table></div>""")

    def outputFileExcerpt(self, filename):
        """Output a card containing an excerpt of a file, sufficient to show locations of all diagnostics plus some context.

        Called by self.outputResults().
        """
        self.f.write("""<div class="card">
            <div class="card-header" id="heading-{id}"><h5 class="mb-0">
            <button class="btn btn-link" type="button">
            {fn}
            </button></h5></div><!-- #heading-{id} -->
            <div class="card-body">
            """.format(id=self.makeIdentifierFromFilename(filename), fn=self.getRelativeFilename(filename)))
        lines = self.fileLines[filename]
        r = self.fileRange[filename]
        self.f.write("""<pre class="line-numbers language-asciidoc line-highlight" id="excerpt-{id}" data-start="{start}"><code>""".format(
            id=self.makeIdentifierFromFilename(filename),
            start=r.start))
        for lineNum, line in enumerate(
                lines[(r.start - 1):(r.stop - 1)], r.start):
            # self.f.write(line)
            lineLinks = [x for x in self.fileBackLinks[filename]
                         if x.lineNum == lineNum]
            for col, char in enumerate(line):
                colLinks = (x for x in lineLinks if x.col == col)
                for link in colLinks:
                    # TODO right now the syntax highlighting is interfering with the link! so the link-generation is commented out,
                    # only generating the emoji icon.

                    # self.f.write('<a href="#{target}" title="{title}" data-toggle="tooltip" data-container="body">{icon}'.format(
                    # target=link.target, title=html.escape(link.tooltip),
                    # icon=MESSAGE_TYPE_ICONS[link.message_type]))
                    self.f.write(MESSAGE_TYPE_ICONS[link.message_type])
                    self.f.write('<span class="sr-only">Cross reference: {t} {title}</span>'.format(
                        title=html.escape(link.tooltip, False), t=link.message_type))

                    # self.f.write('</a>')

                # Write the actual character
                self.f.write(html.escape(char))
            self.f.write('\n')

        self.f.write('</code></pre>')
        self.f.write('</div><!-- .card-body -->\n')
        self.f.write('</div><!-- .card -->\n')

    def outputFallback(self, obj):
        """Output some text in a general way."""
        self.f.write(obj)

    ###
    # Format method: return a string.
    def formatContext(self, context, message_type=None):
        """Format a message context in a verbose way."""
        if message_type is None:
            icon = LINK_ICON
        else:
            icon = MESSAGE_TYPE_ICONS[message_type]
        return 'In context: <a href="{href}">{icon}{relative}:{lineNum}:{col}</a>'.format(
            href=self.getAnchorLinkForContext(context),
            icon=icon,
            # id=self.makeIdentifierFromFilename(context.filename),
            relative=self.getRelativeFilename(context.filename),
            lineNum=context.lineNum,
            col=getColumn(context))

    ###
    # Internal methods: not mandated by parent class.
    def recordUsage(self, context, linkBackTooltip=None,
                    linkBackTarget=None, linkBackType=MessageType.NOTE):
        """Internally record a 'usage' of something.

        Increases the range of lines that are included in the excerpts,
        and records back-links if appropriate.
        """
        BEFORE_CONTEXT = 6
        AFTER_CONTEXT = 3
        # Clamp because we need accurate start line number to make line number
        # display right
        start = max(1, context.lineNum - BEFORE_CONTEXT)
        stop = context.lineNum + AFTER_CONTEXT + 1
        if context.filename not in self.fileRange:
            self.fileRange[context.filename] = range(start, stop)
            self.fileBackLinks[context.filename] = []
        else:
            oldRange = self.fileRange[context.filename]
            self.fileRange[context.filename] = range(
                min(start, oldRange.start), max(stop, oldRange.stop))

        if linkBackTarget is not None:
            start_col, end_col = getHighlightedRange(context)
            self.fileBackLinks[context.filename].append(self.backLink(
                lineNum=context.lineNum, col=start_col, end_col=end_col,
                target=linkBackTarget, tooltip=linkBackTooltip,
                message_type=linkBackType))

    def makeIdentifierFromFilename(self, fn):
        """Compute an acceptable HTML anchor name from a filename."""
        return self.filenameTransformer.sub('_', self.getRelativeFilename(fn))

    def getAnchorLinkForContext(self, context):
        """Compute the anchor link to the excerpt for a MessageContext."""
        return '#excerpt-{}.{}'.format(
            self.makeIdentifierFromFilename(context.filename), context.lineNum)

    def getUniqueAnchor(self):
        """Create and return a new unique string usable as a link anchor."""
        anchor = 'anchor-{}'.format(self.nextAnchor)
        self.nextAnchor += 1
        return anchor
