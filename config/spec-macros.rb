# Copyright 2016-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

#require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'
RUBY_ENGINE == 'opal' ? (require 'spec-macros/extension') : (require_relative 'spec-macros/extension')

# All the inline macros we need
Asciidoctor::Extensions.register do
    inline_macro CanInlineMacro
    inline_macro CannotInlineMacro
    inline_macro MayInlineMacro
    inline_macro MustInlineMacro
    inline_macro OptionalInlineMacro
    inline_macro OptionallyInlineMacro
    inline_macro RequiredInlineMacro
    inline_macro ShouldInlineMacro
    inline_macro ReflinkInlineMacro
    inline_macro ApiextInlineMacro
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
    inline_macro UndefinedInlineMacro
end
