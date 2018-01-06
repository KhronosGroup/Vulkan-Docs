# Copyright (c) 2016-2018 The Khronos Group Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'
RUBY_ENGINE == 'opal' ? (require 'vulkan-macros/extension') : (require_relative 'vulkan-macros/extension')

# All the inline macros we need
Asciidoctor::Extensions.register do
    inline_macro CanInlineMacro
    inline_macro CannotInlineMacro
    inline_macro MayInlineMacro
    inline_macro MustInlineMacro
    inline_macro OptionalInlineMacro
    inline_macro RequiredInlineMacro
    inline_macro ShouldInlineMacro
    inline_macro FlinkInlineMacro
    inline_macro FnameInlineMacro
    inline_macro FtextInlineMacro
    inline_macro SnameInlineMacro
    inline_macro SlinkInlineMacro
    inline_macro StextInlineMacro
    inline_macro EnameInlineMacro
    inline_macro ElinkInlineMacro
    inline_macro EtextInlineMacro
    inline_macro PnameInlineMacro
    inline_macro PtextInlineMacro
    inline_macro DnameInlineMacro
    inline_macro DlinkInlineMacro
    inline_macro TnameInlineMacro
    inline_macro TlinkInlineMacro
    inline_macro BasetypeInlineMacro
    inline_macro CodeInlineMacro
    inline_macro AttrInlineMacro
    inline_macro TagInlineMacro
end
