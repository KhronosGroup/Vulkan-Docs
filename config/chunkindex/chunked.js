/*! loadJS: load a JS file asynchronously. [c]2014 @scottjehl, Filament Group, Inc. (Based on https://goo.gl/REQGQ by Paul Irish). Licensed MIT */
(function( w ){
        var loadJS = function( src, cb, ordered ){
                "use strict";
                var tmp;
                var ref = w.document.getElementsByTagName( "script" )[ 0 ];
                var script = w.document.createElement( "script" );

                if (typeof(cb) === 'boolean') {
                        tmp = ordered;
                        ordered = cb;
                        cb = tmp;
                }

                script.src = src;
                script.async = !ordered;
                ref.parentNode.insertBefore( script, ref );

                if (cb && typeof(cb) === "function") {
                        script.onload = cb;
                }
                return script;
        };
        // commonjs
        if( typeof module !== "undefined" ){
                module.exports = loadJS;
        }
        else {
                w.loadJS = loadJS;
        }
}( typeof global !== "undefined" ? global : this ));
/*! end loadJS */

// Remaining portions of this file are
//
// Copyright (c) 2019 Baldur Karlsson
//
// SPDX-License-Identifier: Apache-2.0

var searchengine = undefined;

// scroll to the first <a> linking to a chapter
function scrollChapter(element, chapter) {
  for(var i=0; i < element.children.length; i++) {
    if(element.children[i].nodeName == "A" && element.children[i].href.indexOf(chapter) >= 0) {
      element.children[i].scrollIntoView(true);
      return true;
    }

    if(scrollChapter(element.children[i], chapter))
      return true;
  }

  return false;
}

var results = undefined;
var searchbox = undefined;
var searchTimeout = undefined;

function clearSearch() {
  while(results.children.length > 0) {
    results.removeChild(results.children[0]);
  }

  document.getElementById("resultsdiv").classList.remove("results");
}

function doSearch() {
  clearSearch();

  var searchtext = searchbox.value;

  if(searchtext == '')
    return;

  if(searchtext.indexOf(' ') == -1 && searchtext.indexOf('\t') == -1 && searchtext.indexOf('"') == -1)
    searchtext = searchtext + ' ' + searchtext + '*';

  searchtext = searchtext.replace(/"/g, '')

  var searchresults = searchengine.search(searchtext);

  if(searchresults.length == 0) {
    var r = document.createElement('LI');
    r.innerHTML = 'No results';

    results.appendChild(r);
  }

  document.getElementById("resultsdiv").classList.add("results");

  for(var i=0; i < 10 && i < searchresults.length; i++) {
    var a = document.createElement('A');
    a.setAttribute('href', searchresults[i].ref);
    a.innerHTML = searchlookup[searchresults[i].ref];

    var r = document.createElement('LI');
    r.appendChild(a);

    results.appendChild(r);
  }
}

function searchInput(e) {
  if(searchTimeout !== undefined)
    clearTimeout(searchTimeout);

  searchTimeout = setTimeout(doSearch, 50);
}

function searchKeyDown(e) {
  if(e.keyCode == 27) {
    // escape
    if(searchTimeout !== undefined)
      clearTimeout(searchTimeout);

    searchbox.value = '';

    clearSearch();
  } else if(e.keyCode == 10 || e.keyCode == 13) {
    // enter/return
    doSearch();
  } else if(e.keyCode == 8) {
    clearSearch();

    searchInput(e);
  }
}

document.addEventListener("DOMContentLoaded", function(event) {
  // get the chapter name from the current URL
  var chap = window.location.pathname.replace(/.*\//, '');

  var toc = document.getElementById("toc");

  // Scroll the sidebar to the appropriate chapter
  if(chap != "") {
    scrollChapter(toc, chap);
    toc.scrollTop -= 96;
  }

  // add anchor links to code blocks
  var blocks = document.getElementsByClassName("listingblock")

  for(var i=0; i < blocks.length; i++) {
    if(blocks[i].id.length > 0) {
      var a = document.createElement("A");
      a.innerHTML = '\u00B6';
      a.setAttribute('class', 'link');
      a.setAttribute('href', '#' + blocks[i].id);

      blocks[i].insertBefore(a, blocks[i].childNodes[0]);
    }
  }

  results = document.getElementById('results');
  searchbox = document.getElementById('searchbox');

  loadJS("lunr.js", function() {
    loadJS(searchindexurl, function() {
      searchengine = lunr.Index.load(searchindex);

      searchbox.value = '';
      searchbox.disabled = false;
      searchbox.addEventListener('keydown', searchKeyDown, false);
      searchbox.addEventListener('input', searchInput, false);
    }, true);
  }, true);
});
