# Copyright 2023-2024 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# Rewrite VUID anchors with 'href' attributes so they can be selected in a
# browser.

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

class AnchorLinkPostprocessor < Asciidoctor::Extensions::Postprocessor
  def process document, output
    content = (document.attr 'copyright') || 'Copyright Acme, Inc.'
    if document.basebackend? 'html'
      output = output.gsub(/<a id="(VUID\-[\w\-:]+)">/, '<a id="\1" href="#\1">')
    end
    output
  end
end

Asciidoctor::Extensions.register do
  postprocessor AnchorLinkPostprocessor
end
