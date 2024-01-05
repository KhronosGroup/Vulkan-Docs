# Copyright 2023-2024 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# open_listing_block - allows a listing block to masquerade as an open
# block:
#
# [open]
# ----
# (block content)
# ----
#
# This allows nesting arbitrary open blocks inside 'refpage' open blocks.

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

Asciidoctor::Extensions.register do
    block do
        named :open
        on_context :listing
        process do |parent, reader, attrs|
            wrapper = create_open_block parent, [], {}
            parse_content wrapper, reader
            wrapper
        end
    end
end
