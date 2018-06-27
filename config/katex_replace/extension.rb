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

class ReplaceMathjaxWithKatex < Extensions::Postprocessor

  MathJaXScript = /<script type="text\/x-mathjax-config">((?!<\/script>).)+<\/script>/m
  MathJaXCDN = '<script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.6.0/MathJax.js?config=TeX-MML-AM_HTMLorMML"></script>'

  def process document, output

    if document.attr? 'stem'
      katexpath = document.attr 'katexpath'

      katexScript = '<link rel="stylesheet" href="' + katexpath + '/katex.min.css">
<script src="' + katexpath + '/katex.min.js"></script>
<script>
    "use strict";
    function renderMathForHTMLCollection(htmlCollection, displayMode) {
        // Clone elements into an array so it cannot change underneath us:
        var elements = Array.prototype.slice.call(htmlCollection);
        for (var i = 0; i < elements.length; ++i) {
            var m = elements[i];
            katex.render(m.textContent, m, { displayMode: displayMode });
            m.outerHTML = m.innerHTML;
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        renderMathForHTMLCollection(
            document.getElementsByClassName("latex-math-inline"), false);
        renderMathForHTMLCollection(
            document.getElementsByClassName("latex-math-display"), true);
    });
</script>'

      output.sub! MathJaXScript, ''
      output.sub! MathJaXCDN, ''
      output.sub! /(?=<\/head>)/, katexScript
      output.gsub! /\\\((.*?)\\\)/m, '<span class="latex-math-inline">\1</span>'
      output.gsub! /\\\[(.*?)\\\]/m, '<span class="latex-math-display">\1</span>'
    end
    output
  end
end
