#!/usr/bin/python3
#
# Copyright (c) 2016-2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# Makes a smart chunked spec that dynamically loads the right chapter page
# based on what # anchor is in the URL
#
# Usage:
# cd <root of Vulkan-Docs repo>
# ./scripts/motherchunker.py ./gen/out/html/vkspec.html ./gen/out/chunked/vkspec.html

import os,sys,re
from html.parser import HTMLParser

# Produces a map between html id anchor and a html file it will be in
class IdHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)

        self.current_section = 0

        self.id_map = [('', 'chap0.html')]

    def handle_starttag(self, tag, attrs):
        if tag == 'div' and ('class', 'sect1') in attrs:
            self.current_section += 1

        html_id = next((attr[1] for attr in attrs if attr[0] == 'id'), None)

        if html_id is not None:
            self.id_map.append((html_id, 'chap' + str(self.current_section) + '.html'))

    # only actually triggers if there is explicitly '/' there at the end
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def unknown_decl(self, data):
        print( 'WARNING: unregognized syntax at {}!'.format(self.getpos()) )

# Produces a template and the chunks the template loads into itself
# plus some select modifications, like adding the searchbox
class ChunkerHTMLParser(HTMLParser):
    def __init__(self, additional_headers):
        HTMLParser.__init__(self, convert_charrefs=False)

        self.SELFCLOSING_TAGS = ['meta', 'link', 'br', 'col', 'wbr']
        self.PLACEHOLDER_CONTENTS = \
'''
<noscript>
    <p>The chunked specification requires JavaScript. Please enable JavaScript for this page, or consider using the <a href="../html/vkspec.html">single-page</a> specification.</p>
</noscript>
'''
        self.PREAMBLE_TOC_ENTRY = '\n<li><a href="#preamble">0. Preamble</a></li>'
        self.SEARCHBOX = \
'''<div class="searchbox">
    <label for="searchbox">Search: </label>
    <input id="searchbox" type="text" disabled="disabled" value="Loading Search Data" />
    <div id="resultsdiv"><ol id="results"></ol></div>
</div>'''
        self.additional_headers = additional_headers

        self.current_section = 0
        self.header_tag_level = None
        self.content_tag_level = None
        self.tag_stack = []

        self.html_template = []
        self.chunks = [] # For perf reasons, each chunk will be an array of strings to later be joined

    def handle_starttag(self, tag, attrs):
        # Track which section we are in to write to appropriate chunk
        if tag == 'div' and ('class', 'sect1') in attrs:
            self.current_section += 1
            self.chunks.append([])

        # Append "chunked" to the class of the <html> tag
        if tag == 'html':
            tag_text = '<html'
            class_found = False
            for (attr_name, attr_value) in attrs:
                if attr_name == 'class':
                    class_found = True
                    attr_value += ' chunked'
                tag_text += ' ' + attr_name + '="' + attr_value + '"'
            if not class_found: tag_text += ' class="chunked"'
            tag_text += '>'
            self.html_template.append(tag_text)
        # Add everything before first section to template, and everything after it to appropriate chunk
        elif self.content_tag_level is None: self.html_template.append(self.get_starttag_text())
        else: self.chunks[self.current_section].append(self.get_starttag_text())

        # Add Preamble to the TOC
        if tag == 'ul' and ('class', 'sectlevel1') in attrs:
            self.html_template.append(self.PREAMBLE_TOC_ENTRY)

        # Track whether we are in the common section of the html, or already in the first chunk
        if tag == 'div' and ('id', 'content') in attrs:
            if self.content_tag_level is not None: sys.exit( 'ERROR: second "content" tag encountered!' )
            self.content_tag_level = len(self.tag_stack)
            self.chunks.append([])

        # Track whether we are in the header section of the spec (also includes the sidebar)
        if tag == 'div' and ('id', 'header') in attrs:
            self.header_tag_level = len(self.tag_stack)

        if tag not in self.SELFCLOSING_TAGS: self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        opened_tag = self.tag_stack.pop()
        if tag != opened_tag: sys.exit( 'ERROR: closing tag <{}> at {} did not match opened tag <{}> !'.format(tag, self.getpos(), opened_tag) )

        if self.content_tag_level is not None and len(self.tag_stack) == self.content_tag_level:
            if tag != 'div': sys.exit( 'ERROR: expected <div> as a closing tag of content!' )
            self.content_tag_level = None

            # Add contents that will be in the contents container before any chunk loads
            self.html_template.append(self.PLACEHOLDER_CONTENTS)

        if tag == 'head': self.html_template.append(self.additional_headers)

        # Add searchbox to the sidebar
        if self.header_tag_level is not None and len(self.tag_stack) == self.header_tag_level:
            self.html_template.append(self.SEARCHBOX)
            self.header_tag_level = None

        # Add everything after last section to template, and everything before it to appropriate chunk
        if self.content_tag_level is None: self.html_template.append('</' + tag + '>')
        else: self.chunks[self.current_section].append('</' + tag + '>')

    # Write the rest of the html elements to either template or chunk as appropriate
    def handle_startendtag(self, tag, attrs): # only actually triggers if there is explicitly '/' there at the end (usually in SVG)
        if self.content_tag_level is None: self.html_template.append(self.get_starttag_text())
        else: self.chunks[self.current_section].append(self.get_starttag_text())
    def handle_data(self, data):
        if self.content_tag_level is None: self.html_template.append(data)
        else: self.chunks[self.current_section].append(data)
    def handle_comment(self, data):
        self.handle_data( '<!--' + data + '-->' )
    def handle_decl(self, decl):
        self.handle_data( '<!' + decl + '>' )
    def handle_entityref(self, name):
        self.handle_data( '&' + name + ';' )
    def handle_charref(self, name):
        self.handle_data( '&#' + name + ';' )
    def unknown_decl(self, data):
        print( 'WARNING: unregognized syntax at {}!'.format(self.getpos()) )
        self.handle_data( data )

def makeChunked(in_file, out_file):
    try:
        with open(in_file, 'r', encoding='utf8') as f: data = f.read()
    except FileNotFoundError:
        print('Error: File %s does not exist.' % in_file)
        sys.exit(2)

    id_parser = IdHTMLParser()
    id_parser.feed(data)

    redirect_script = \
'''<script>
var id_map = {{{}}};

var current_page;

function panic( reason ){{
    console.error("Page load failed! Reason: " + reason);
    document.getElementById("content").innerHTML = "<p>Page failed to load (reason: " + reason + ").</p>";
    showContent();
    hideLoadingMsg();
    current_page = undefined;
}}

function locationHashChanged(){{
    var hash = location.hash;
    if( !hash ) hash = "";
    if( hash.startsWith("#") ) hash = hash.substring(1);

    var page = id_map[hash];
    if( page !== undefined && page != current_page ){{
        showLoadingMsg();

        var xhr = new XMLHttpRequest();
        xhr.onload = function() {{
            console.assert(xhr.readyState == 4, "readyState of XMLHttpRequest is not DONE on load event");
            console.assert(xhr.status == 200 || window.location.protocol == "file:", "HTTP status is not 200 on load event");

            //hideContent(); // keep the previous contents on so there is no page blink
            document.getElementById("content").innerHTML = xhr.response;
            showContent();
            hideLoadingMsg();

            if( hash != "" ){{
                document.getElementById(hash).scrollIntoView();
                var chapter_n = parseInt(page.substr(4));
                document.getElementById("toc").getElementsByClassName("sectlevel1")[0].children[chapter_n].scrollIntoView({{block: "center"}});
            }}
            else{{
                window.scrollTo(0,0);
            }}

            if( current_page === undefined ) initSearchbox(); // TODO: should be async call?
            current_page = page;
        }};
        xhr.onerror = function() {{
            // file protocol does not send any status codes; have to assume it failed for security reasons
            if( window.location.protocol == "file:" ) panic( "<code>file://</code> protocol used; this website is not suitable for offline viewing" );
            else panic( "request error; HTTP code " + xhr.status );
        }};
        xhr.onabort = function() {{ panic( "request aborted" ); }};
        xhr.ontimeout = function() {{ panic( "request timed out" );  }};

        xhr.open("GET", page + "?v=" + document.title.replace(/[^0-9.]/g, ''));
        xhr.timeout = 5000; //ms
        xhr.send();
    }}
}}

window.onhashchange = locationHashChanged;
window.addEventListener("load", locationHashChanged);
</script>'''

    redirect_map = ['"{}":"{}"'.format(html_id, page) for html_id, page in id_parser.id_map]
    redirect_map = ','.join(redirect_map)
    redirect_script = redirect_script.format(redirect_map)

    searchbox_script = \
'''
<link href="chunked.css?v=4" rel="stylesheet">
<script>var searchindexurl = 'search.index.js?v=2.3.8&spec=' + (document.title.replace(/[^0-9.]/g, ''));</script>
<script src="chunked.js?v=5"></script>
'''

    additional_headers = redirect_script + searchbox_script
    chunker_parser = ChunkerHTMLParser(additional_headers)
    chunker_parser.feed(data)

    with open(out_file, 'w', encoding='utf8') as f: f.write(''.join(chunker_parser.html_template))

    out_dir = os.path.dirname(out_file)
    for section, chunk in enumerate(chunker_parser.chunks):
        chunk_file = os.path.join(out_dir, 'chap' + str(section) + '.html')
        with open(chunk_file, 'w', encoding='utf8') as f: f.write(''.join(chunk))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Error: .py requires two arguments.')
        print('Usage: .py file.html file.html')
        sys.exit(1)
    makeChunked(sys.argv[1], sys.argv[2])