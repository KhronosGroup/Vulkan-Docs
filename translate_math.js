const katex = require("./katex/katex.js");
const fs = require("fs");
const escapeRegex = require("escape-string-regexp");
const he = require('he');

const filepath = process.argv[2];

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
