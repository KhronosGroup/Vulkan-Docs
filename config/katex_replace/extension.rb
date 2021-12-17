# Copyright 2016-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

class ReplaceMathjaxWithKatex < Extensions::Postprocessor

  MathJaXScript = /<script type="text\/x-mathjax-config">((?!<\/script>).)+<\/script>/m
  MathJaXCDN = /<script src="https:\/\/cdnjs.cloudflare.com\/ajax\/libs\/mathjax\/[0-9].[0-9].[0-9]\/MathJax.js\?config=[-_A-Za-z]+"><\/script>/m

  def process document, output

    if document.attr? 'stem'
      katexpath = document.attr 'katexpath'

      katexScript = '
<!-- dragged in by font-awesome css included by asciidoctor, but preloaded in this extension for convenience -->
<link rel="preload" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/fonts/fontawesome-webfont.woff2?v=4.7.0" as="font" type="font/woff2" crossorigin="">

<!-- Note: Chrome needs crossorigin="" even for same-origin fonts -->
<link rel="preload" href="../katex/fonts/KaTeX_Main-Bold.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="../katex/fonts/KaTeX_Main-Italic.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="../katex/fonts/KaTeX_Main-Regular.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="../katex/fonts/KaTeX_Math-Italic.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="../katex/fonts/KaTeX_Size1-Regular.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="../katex/fonts/KaTeX_Size2-Regular.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="../katex/fonts/KaTeX_Size3-Regular.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="../katex/fonts/KaTeX_Size4-Regular.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="../katex/fonts/KaTeX_Typewriter-Regular.woff2" as="font" type="font/woff2" crossorigin="">'

      # Load KaTeX stylesheet, but we no longer run a script to convert math
      # using KaTeX, since that's now done at spec generation time.
      katexScript += '<link rel="stylesheet" href="' + katexpath + '/katex.min.css">'

      output.sub! MathJaXScript, ''
      output.sub! MathJaXCDN, ''
      output.sub! /(?=<\/head>)/, katexScript
    end
    output
  end
end
