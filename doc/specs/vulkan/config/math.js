    <!-- Asciidoc configuration file attribute substitution is applied when
         including this file, so care in formatting braces is required. Thus
         the spaces before left: below. -->
    <!-- Load KaTeX from relative path {katexpath=katex}.
         This can also be an absolute URL prefix, allowing use of either a
         local copy or the KaTeX CDN (see https://github.com/Khan/KaTeX for
         CDN URLs). -->
<link rel="stylesheet" href="{katexpath=katex}/katex.min.css">
<script src="{katexpath=katex}/katex.min.js"></script>
<script src="{katexpath=katex}/contrib/auto-render.min.js"></script>
    <!-- Use KaTeX to render math once document is loaded, see
         https://github.com/Khan/KaTeX/tree/master/contrib/auto-render -->
<script>
    document.addEventListener("DOMContentLoaded", function () {
        renderMathInElement(
            document.body,
            {
                delimiters: [
                    { left: "$$", right: "$$", display: true},
                    { left: "\\[", right: "\\]", display: true},
                    { left: "$", right: "$", display: false},
                    { left: "\\(", right: "\\)", display: false}
                ]
            }
        );
    });
</script>
