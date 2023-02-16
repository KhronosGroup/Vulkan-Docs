# Copyright 2021-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include Asciidoctor

class ExistsIncludeProcessor < Extensions::IncludeProcessor
  def handles? target
    # Only handle files which do not exist
    # This relies on the full absolute path to every include file being
    # given, since relative directory information exists only in the
    # process method.

    not File.exist? target
  end

  def process doc, reader, target, attributes
    # If we reach this point, we have been asked to include a file which
    # does not exist. Do nothing, instead of raising an error.

    reader
  end
end

Extensions.register do
  include_processor ExistsIncludeProcessor
end

