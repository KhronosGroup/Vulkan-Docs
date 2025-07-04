# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

RUBY_ENGINE == 'opal' ? (require 'vu-formatter/extension') : (require_relative 'vu-formatter/extension')

class Asciidoctor::Document
  attr_writer :sourcemap unless method_defined? :sourcemap=
end

Extensions.register do
  # Enable the sourcemap feature
  preprocessor do
    process do |doc, reader|
      doc.sourcemap = true
      nil
    end
  end

  preprocessor WorkaroundWhitespaceSwallowPreprocessor
  treeprocessor VuFormatterTreeprocessor
end
