# Copyright 2016-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

#require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'
RUBY_ENGINE == 'opal' ? (require 'katex_replace/extension') : (require_relative 'katex_replace/extension')

# All the inline macros we need
Asciidoctor::Extensions.register do
    postprocessor ReplaceMathjaxWithKatex
end
