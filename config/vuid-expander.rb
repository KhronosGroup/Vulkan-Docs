# Copyright 2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

# Preprocessor hook to insert vuid: inline macro after every VUID anchor
class VUIDExpanderPreprocessor < Extensions::Preprocessor
  def process document, reader
    new_lines = reader.read_lines.map do | line |
      line.gsub(/\[\[(VUID.*?)\]\]/, '[[\1]]vuid:\1')
    end
    Reader.new(new_lines)
  end
end

Extensions.register do
  preprocessor VUIDExpanderPreprocessor
end
