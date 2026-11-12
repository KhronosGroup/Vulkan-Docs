# Copyright 2026 Holochip Corporation
# SPDX-License-Identifier: Apache-2.0

# inline_svg_alt - when an image is inlined with opts=inline, Asciidoctor
# discards the 'alt' attribute, leaving the <svg> element without an
# accessible name. This copies an explicitly authored 'alt' onto the
# inlined <svg> as role="img" and aria-label. Alt text that Asciidoctor
# generated from the file name (default-alt) is deliberately not used.
# When the document attribute 'warn-missing-alt' is set (for example with
# make EXTRAATTRIBS='-a warn-missing-alt' html), a warning is issued for each
# inlined image that has no authored alt. It is off by default.

require 'asciidoctor'
require 'asciidoctor/converter/html5'

module InlineSvgAlt
  def convert_image(node)
    html = super
    if (node.option? 'inline') && node.attr?('alt') && !node.attr?('default-alt')
      alt = node.attr('alt').gsub('&', '&amp;').gsub('"', '&quot;').gsub('<', '&lt;')
      html = html.sub(/<svg(\s)(?![^>]*\saria-label=)/, %(<svg role="img" aria-label="#{alt}"\\1))
    end
    if (node.option? 'inline') && node.document.attr?('warn-missing-alt') &&
       !(node.attr?('alt') && !node.attr?('default-alt'))
      logger.warn message_with_context(%(inline image #{node.attr 'target'} has no alt text),
                                       source_location: node.parent.source_location || node.source_location)
    end
    html
  end
end

Asciidoctor::Converter::Html5Converter.prepend(InlineSvgAlt)
