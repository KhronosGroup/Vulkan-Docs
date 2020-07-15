# Copyright (c) 2016-2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

class MakeHtmlLoadable < Extensions::Postprocessor

  def process document, output

    if document.attr? 'stem'

      logo_bug_white = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAACXBIWXMAAC4jAAAuIwF4pT92AAAAB3RJTUUH5AYdEwQiw14QHwAAAhpJREFUaN7tWO1xgzAMfc5lADpBGYFO0GxQOkHpBE03YANGyAiQCegGJBMkG5AN1D/KHSXGXxinufO74/gBSHrSk2wMRERERESEABHVpEbxH20PnRQaJ7Wj3YT0SHwQWMTR3MSsTB0JIS4AGs1rG4fcvGme7332gS5bu9BVXVtyaAB8ATgDOPL9PHh+sbSX6/xx5f0QYGMvHofbhROQuspHzJTUVfOpJIhhdc5CiLPCTgqgAPAxsvOkq4CwCDblkr8CyBRZU+HA1xHAjxDiIPGTs0wvQoh3X43b0TLoiWjHQd80+NzAN0R0onA4EVHpa9Gq6H7oZxG5c/A3RKymEE+V1nEcNtycB9nU4YxmAK73Z75nBo3/KWt4l13hGK2sAR37bcv++wlfpYmh3qK8ssmRcjAlX6nknUynb36nkgyRWvmtRfDZKOhyYmJtJT5OAzstf5tPBcbPhsroJkkYzvvNKHhV1TpJZlWoVAsprxnTW2yDCdQqMqrdTRrYLwxknsikaZrRrQPpwqLCXhaxrcJBPtFw2j8qTo73X9IpEjsbjZrISJMYPz/uBiROjr1TBJGPJLDSsA90MuqCycdgV/pnHbCQUTj5TIyuSkVi5iYwQQiMFpPxipw7Bl8jNAZESse9VDj5eBq/i8ln5ZmD7Sma9tznHlXoH1I+jjKaPX1WC3DYP6x8LGXkRT7rhTh8G5zcNYiIiIh4ePwCG/5IoFeZaBUAAAAASUVORK5CYII='
      loading_msg = '<div id="loading_msg">Loading <img alt="" class="loading_spinner" decoding="sync" src="' + logo_bug_white + '" /></div>'
      noJS_class = 'class="noJS"'

      loaded_script = '
<style>
    #loading_msg {
        position: fixed;
        top: 0;
        left: 50vw;
        transform: translateX(-50%);
        z-index: 1;
        padding: 0.5em;
        color: white;
        background-color: #A41E22;
        font-size: larger;
    }
    .loading_spinner {
        display: inline-block;
        width: 1em;
        height: 1em;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% {transform: rotateY(0deg);}
        100% {transform: rotateY(360deg);}
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
      output.sub! /(<body.*?>)/, '\1' + "\n" + loading_msg
    end
    output
  end
end
