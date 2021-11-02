# Copyright 2016-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

# This is the generated map of API interfaces in this spec build
require 'api.rb'
$apiNames = APInames.new

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
    # Check if a link macro target exists - overridden by specific macros
    # Default assumption is that it does exist
    def exists? target
      return true
    end

    def process parent, target, attributes
      if not exists? target
        # If the macro target isn't in this build, but has an alias,
        # substitute that alias as the argument.
        # Otherwise, turn the (attempted) link into text, and complain.
        if $apiNames.nonexistent.has_key? target
          oldtarget = target
          target = $apiNames.nonexistent[oldtarget]
          msg = 'Rewriting nonexistent link macro target: ' + @name.to_s + ':' + oldtarget + ' to ' + target
          Asciidoctor::LoggerManager.logger.info msg
          # Fall through
        else
          # Suppress warnings for apiext: macros as this is such a common case
          if @name.to_s != 'apiext'
            msg = 'Textifying unknown link macro target: ' + @name.to_s + ':' + target
            Asciidoctor::LoggerManager.logger.warn msg
          end
          return create_inline parent, :quoted, '<code>' + target + '</code>'
        end
      end

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

    def exists? target
        $apiNames.features.has_key? target
    end
end

class FlinkInlineMacro < LinkInlineMacroBase
    named :flink
    match /flink:(\w+)/

    def exists? target
        $apiNames.protos.has_key? target
    end
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

    def exists? target
        $apiNames.structs.has_key? target or $apiNames.handles.has_key? target
    end
end

class StextInlineMacro < CodeInlineMacroBase
    named :stext
    match /stext:([\w\*]+)/
end

class EnameInlineMacro < CodeInlineMacroBase
    named :ename
    match /ename:(\w+)/

    def exists? target
        $apiNames.consts.has_key? target
    end
end

class ElinkInlineMacro < LinkInlineMacroBase
    named :elink
    match /elink:(\w+)/

    def exists? target
        $apiNames.enums.has_key? target
    end
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

    def exists? target
        $apiNames.defines.has_key? target
    end
end

class TnameInlineMacro < CodeInlineMacroBase
    named :tname
    match /tname:(\w+)/
end

class TlinkInlineMacro < LinkInlineMacroBase
    named :tlink
    match /tlink:(\w+)/

    def exists? target
        $apiNames.flags.has_key? target or
            $apiNames.funcpointers.has_key? target or
            $apiNames.defines.has_key? target
    end
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
