# Copyright (c) 2016-2018 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

class MakeHtmlLoadable < Extensions::Postprocessor

  def process document, output

    if document.attr? 'stem'

      loading_msg = '<div id="loading_msg"><p>Loading&hellip; please wait.</p></div>'
      noJS_class = 'class="noJS"'

      loaded_script = '
<style>
    #loading_msg {
        width: 100%;
        margin-left: auto;
        margin-right: auto;
        margin-top: 1ex;
        margin-bottom: 1ex;
        max-width: 62.5em;
        position: relative;
        padding-left: 1.5em;
        padding-right: 1.5em;
    }

    html.noJS #loading_msg {display: none !important;}
    #loading_msg.hidden {display: none !important;}
    html:not(.noJS) #content:not(.loaded) {display: none !important;}
</style>
<script>
    function hideContent(){ document.getElementById("content").classList.remove("loaded"); }
    function showContent(){ document.getElementById("content").classList.add("loaded"); }
    function hideLoadingMsg(){ document.getElementById("loading_msg").classList.add("hidden"); }
    function showLoadingMsg(){ document.getElementById("loading_msg").classList.remove("hidden"); }

    document.documentElement.classList.remove("noJS");
    if( !document.documentElement.classList.contains("chunked") )
        window.addEventListener("load", function(){showContent(); hideLoadingMsg();});
</script>
'

      output.sub! /(<html lang="en")/, '\1' + " " + noJS_class + " "
      output.sub! /(?=<\/head>)/, loaded_script
      output.sub! /(?=<div id="content")/, loading_msg + "\n"
    end
    output
  end
end
