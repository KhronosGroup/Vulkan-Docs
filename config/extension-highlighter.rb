# Copyright (c) 2016-2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

RUBY_ENGINE == 'opal' ? (require 'extension-highlighter/extension') : (require_relative 'extension-highlighter/extension')

Extensions.register do
  preprocessor ExtensionHighlighterPreprocessor
  postprocessor AddHighlighterCSS
end
