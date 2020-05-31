/* Copyright (c) 2020 The Khronos Group Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

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
