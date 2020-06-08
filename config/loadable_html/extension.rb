# Copyright (c) 2016-2018 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

class MakeHtmlLoadable < Extensions::Postprocessor

  def process document, output

    if document.attr? 'stem'

      loading_msg = '
<div id="loading_msg"><p>Loading... please wait.</p></div>
'
      loadable_class = 'class="loadable"'

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
    .loadable {display: none !important;}
</style>
<script>
    function unhideLoadableContent(){
        document.getElementById("loading_msg").style.display = "none";
        var loadables = document.getElementsByClassName("loadable");
        for( var i = 0; i < loadables.length; ++i ) loadables[i].classList.remove("loadable");
    }

    window.addEventListener("load", unhideLoadableContent);
</script>
'

      output.sub! /(?=<\/head>)/, loaded_script
      output.sub! /(<div id="content")/, '\1' + " " + loadable_class + " "
      output.sub! /(?=<div id="content")/, loading_msg
    end
    output
  end
end
