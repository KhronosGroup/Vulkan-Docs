# Copyright 2016-2018 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

#require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'
RUBY_ENGINE == 'opal' ? (require 'loadable_html/extension') : (require_relative 'loadable_html/extension')

# All the inline macros we need
Asciidoctor::Extensions.register do
    postprocessor MakeHtmlLoadable
end
