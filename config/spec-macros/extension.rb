# Copyright 2016-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

class SpecInlineMacroBase < Extensions::InlineMacroProcessor
    use_dsl
    using_format :short
end

class NormativeInlineMacroBase < SpecInlineMacroBase
    def text
        'normative'
    end

    def process parent, target, attributes
        create_inline parent, :quoted, '<strong class="purple">' + text + '</strong>'
    end
end

class LinkInlineMacroBase < SpecInlineMacroBase
    def process parent, target, attributes
      if parent.document.attributes['cross-file-links']
        return Inline.new(parent, :anchor, target, :type => :link, :target => (target + '.html'))
      else
        return Inline.new(parent, :anchor, target, :type => :xref, :target => ('#' + target), :attributes => {'fragment' => target, 'refid' => target})
      end
    end
end

class CodeInlineMacroBase < SpecInlineMacroBase
    def process parent, target, attributes
        create_inline parent, :quoted, '<code>' + target.gsub('&#8594;', '-&gt;') + '</code>'
    end
end

class StrongInlineMacroBase < SpecInlineMacroBase
    def process parent, target, attributes
        create_inline parent, :quoted, '<code>' + target.gsub('&#8594;', '-&gt;') + '</code>'
    end
end

class ParamInlineMacroBase < SpecInlineMacroBase
    def process parent, target, attributes
         create_inline parent, :quoted, '<code>' + target.gsub('&#8594;', '-&gt;') + '</code>'
    end
end

class CanInlineMacro < NormativeInlineMacroBase
    named :can
    match /can:(\w*)/

    def text
        'can'
    end
end

class CannotInlineMacro < NormativeInlineMacroBase
    named :cannot
    match /cannot:(\w*)/

    def text
        'cannot'
    end
end

class MayInlineMacro < NormativeInlineMacroBase
    named :may
    match /may:(\w*)/

    def text
        'may'
    end
end

class MustInlineMacro < NormativeInlineMacroBase
    named :must
    match /must:(\w*)/

    def text
        'must'
    end
end

class OptionalInlineMacro < NormativeInlineMacroBase
    named :optional
    match /optional:(\w*)/

    def text
        'optional'
    end
end

class OptionallyInlineMacro < NormativeInlineMacroBase
    named :optionally
    match /optionally:(\w*)/

    def text
        'optionally'
    end
end

class RequiredInlineMacro < NormativeInlineMacroBase
    named :required
    match /required:(\w*)/

    def text
        'required'
    end
end

class ShouldInlineMacro < NormativeInlineMacroBase
    named :should
    match /should:(\w*)/

    def text
        'should'
    end
end

# Generic reference page link to any entity with an anchor/refpage
class ReflinkInlineMacro < LinkInlineMacroBase
    named :reflink
    match /reflink:(\w+)/
end

# Link to an extension appendix/refpage
class ApiextInlineMacro < LinkInlineMacroBase
    named :apiext
    match /apiext:(\w+)/
end

class FlinkInlineMacro < LinkInlineMacroBase
    named :flink
    match /flink:(\w+)/
end

class FnameInlineMacro < CodeInlineMacroBase
    named :fname
    match /fname:(\w+)/
end

class FtextInlineMacro < CodeInlineMacroBase
    named :ftext
    match /ftext:([\w\*]+)/
end

class SnameInlineMacro < CodeInlineMacroBase
    named :sname
    match /sname:(\w+)/
end

class SlinkInlineMacro < LinkInlineMacroBase
    named :slink
    match /slink:(\w+)/
end

class StextInlineMacro < CodeInlineMacroBase
    named :stext
    match /stext:([\w\*]+)/
end

class EnameInlineMacro < CodeInlineMacroBase
    named :ename
    match /ename:(\w+)/
end

class ElinkInlineMacro < LinkInlineMacroBase
    named :elink
    match /elink:(\w+)/
end

class EtextInlineMacro < CodeInlineMacroBase
    named :etext
    match /etext:([\w\*]+)/
end

# this does not handle any [] at the moment

class PnameInlineMacro < ParamInlineMacroBase
    named :pname
    match /pname:(\w+((\.|&#8594;)\w+)*)/
end

class PtextInlineMacro < ParamInlineMacroBase
    named :ptext
    match /ptext:([\w\*]+((\.|&#8594;)[\w\*]+)*)/
end

class DnameInlineMacro < CodeInlineMacroBase
    named :dname
    match /dname:(\w+)/
end

class DlinkInlineMacro < LinkInlineMacroBase
    named :dlink
    match /dlink:(\w+)/
end

class TnameInlineMacro < CodeInlineMacroBase
    named :tname
    match /tname:(\w+)/
end

class TlinkInlineMacro < LinkInlineMacroBase
    named :tlink
    match /tlink:(\w+)/
end

class BasetypeInlineMacro < CodeInlineMacroBase
    named :basetype
    match /basetype:(\w+)/
end

# This doesn't include the full range of code: use
# It allows imbedded periods (field separators) and wildcards if followed by
# another word, and an ending wildcard.

class CodeInlineMacro < CodeInlineMacroBase
    named :code
    match /code:(\w+([.*]\w+)*\**)/
end

# The tag: and attr: macros are only used in registry.txt

class TagInlineMacro < StrongInlineMacroBase
    named :tag
    match /tag:(\w+)/
end

class AttrInlineMacro < StrongInlineMacroBase
    named :attr
    match /attr:(\w+)/
end

# Does nothing - just markup that we've considered the use case
class UndefinedInlineMacro < SpecInlineMacroBase
    named :undefined
    match /undefined:/

    def process parent, target, attributes
        create_inline parent, :quoted, 'undefined'
    end
end
