# Copyright 2016-2018 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# This script adds CSS and markup to indicate the document is (perhaps
# slowly) loading. It also inserts HTML comments marking where JavaScript
# and HTML specific to the chunked HTML output target should be inserted.

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

class MakeHtmlLoadable < Extensions::Postprocessor

  def process document, output

    if document.attr? 'stem'

      loading_msg = '<div id="loading_msg" class="hidden" hidden><p>Loading&hellip; please wait.</p></div>'
      loadable_class = 'class="loadable"'

      loaded_script = '
<!--ChunkedSearchJSMarker-->
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
    .hidden {display: none;}
</style>
<script>
    function hideElement(e){
        e.setAttribute("hidden", "");
        e.classList.add("hidden");
    }

    function unhideElement(e){
        e.classList.remove("hidden");
        e.removeAttribute("hidden");
    }

    function hideLoadableContent(){
        unhideElement( document.getElementById("loading_msg") );
        for( var loadable of document.getElementsByClassName("loadable") ) hideElement(loadable);
    }

    function unhideLoadableContent(){
        hideElement( document.getElementById("loading_msg") );
        for( var loadable of document.getElementsByClassName("loadable") ) unhideElement(loadable);
    }

    window.addEventListener("load", unhideLoadableContent);
</script>
'

      hide_script = '<script>hideLoadableContent();</script>'

      output.sub! /(?=<\/head>)/, loaded_script
      output.sub! /(<div id="content")/, '\1' + " " + loadable_class + " "
      output.sub! /(<div id="content".*?>)/, '\1' + hide_script
      output.sub! /(?=<div id="content")/, loading_msg + "\n" + "<!--ChunkedSearchboxMarker-->\n"
    end
    output
  end
end
