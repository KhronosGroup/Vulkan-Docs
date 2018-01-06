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

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

class VulkanInlineMacroBase < Extensions::InlineMacroProcessor
    use_dsl
    using_format :short
end

class NormativeInlineMacroBase < VulkanInlineMacroBase
    def text
        'normative'
    end

    def process parent, target, attributes
        '<strong class="purple">' + text + '</strong>'
    end
end

class LinkInlineMacroBase < VulkanInlineMacroBase
    def process parent, target, attributes
      if parent.document.attributes['cross-file-links']
        return Inline.new(parent, :anchor, target, :type => :link, :target => (target + '.html')).convert
      else
        return Inline.new(parent, :anchor, target, :type => :xref, :target => ('#' + target), :attributes => {'fragment' => target, 'refid' => target}).convert
      end
    end
end

class CodeInlineMacroBase < VulkanInlineMacroBase
    def process parent, target, attributes
        '<code>' + target + '</code>'
    end
end

class StrongInlineMacroBase < VulkanInlineMacroBase
    def process parent, target, attributes
        '<code>' + target + '</code>'
    end
end

class ParamInlineMacroBase < VulkanInlineMacroBase
    def process parent, target, attributes
        '<code>' + target + '</code>'
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

class FlinkInlineMacro < LinkInlineMacroBase
    named :flink
    match /flink:(\w+)/
end

class FnameInlineMacro < StrongInlineMacroBase
    named :fname
    match /fname:(\w+)/
end

class FtextInlineMacro < StrongInlineMacroBase
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

class PnameInlineMacro < ParamInlineMacroBase
    named :pname
    match /pname:(\w+(\.\w+)*)/
end

class PtextInlineMacro < ParamInlineMacroBase
    named :ptext
    match /ptext:([\w\*]+(\.[\w\*]+)*)/
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

class CodeInlineMacro < StrongInlineMacroBase
    named :code
    match /code:(\w+)/
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

