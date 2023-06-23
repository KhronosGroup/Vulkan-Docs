# Copyright 2016-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

RUBY_ENGINE == 'opal' ? (require 'vu-to-json/extension') : (require_relative 'vu-to-json/extension')

Extensions.register do
  treeprocessor ValidUsageToJsonTreeprocessor
end
