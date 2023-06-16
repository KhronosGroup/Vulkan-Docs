# Copyright 2016-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

RUBY_ENGINE == 'opal' ? (require 'ifdef-mismatch/extension') : (require_relative 'ifdef-mismatch/extension')

Extensions.register do
  preprocessor IfDefMismatchPreprocessor
end
