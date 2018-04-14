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
