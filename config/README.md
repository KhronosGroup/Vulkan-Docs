# Vulkan Asciidoc Configuration Files

## Macros

The macros in `vulkan-macros.rb` and `vulkan-macros/extension.rb` are
described in the "Vulkan Documentation and Extensions: Procedures and
Conventions" document (see the [styleguide](../styleguide.txt)).

## Support for Math

Asciidoctor is customized to insert KaTeX `<script>` tags from
`math.js` for HTML5, and properly pass through math which has
`\begin{}\/end{}` delimiters instead of $$\[\]\(\).

For PDF builds, asciidoctor-mathematical is used to generate

`math-docbook.conf` is heavily conditionalized depending on whether the
final output format (which should be described in the a2x-format variable)
is `pdf` or not, since Docbook passes through math differently to dblatex
vs. the XHTML stylesheets. This could be simplified now that we're only
using Docbook for PDFs.

## Stylesheets

`khronos.css` is the stylesheet used for HTML output.
