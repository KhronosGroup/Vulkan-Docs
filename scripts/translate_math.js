// Copyright (c) 2020 The Khronos Group, Inc.
//
// SPDX-License-Identifier: Apache-2.0

// Translates the latexmath in html on build time using KaTeX
// Usage: nodejs translate_math.js katex/katex.min.js vkspec.html

const katex = require(process.argv[2]);
const fs = require("fs");
const escapeRegex = require("escape-string-regexp");
const he = require('he');

const filepath = process.argv[3];

var html = fs.readFileSync(filepath, "utf8");

const delimiters = [
                     //{ left: "$$", right: "$$", display: true},
                     { left: "\\[", right: "\\]", display: true},
                     //{ left: "$", right: "$", display: false},
                     { left: "\\(", right: "\\)", display: false}
                   ]

for( var delim of delimiters ) {
    const regex = new RegExp( escapeRegex(delim.left) + "([\\S\\s]*?)" + escapeRegex(delim.right), "g");
    html = html.replace( regex,
        function(match, g1) {
            return katex.renderToString( he.decode(g1, {'strict': true}), {displayMode: delim.display, output: 'html', strict: true} );
        }
    );
}

fs.writeFileSync(filepath, html, 'utf8');
