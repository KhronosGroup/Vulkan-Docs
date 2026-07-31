#!/usr/bin/env python3
#
# Copyright 2026 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Strip Asciidoctor HTML to reviewable text and (optionally) unified-diff two builds.

The Vulkan(SC) spec is one ~12MB HTML file. Diffing raw HTML is noisy and
reflows badly. This extracts visible text with ONE line per block-level
element, so a small wording change stays a small diff instead of reflowing a
whole paragraph.

Usage:
  # Emit text for a single file (to stdout):
  specdiff.py path/to/vkspec.html

  # Unified diff of two builds (files or gen dirs containing out/html/vkspec.html):
  specdiff.py BEFORE AFTER
  specdiff.py gen_348_sc gen                 # dir args auto-resolve to out/html/vkspec.html
  specdiff.py BEFORE AFTER > review.diff
"""
import html
import os
import sys
from html.parser import HTMLParser

# Block-level tags: each forces a line break in the output so structure/diff granularity is per-block.
BLOCK = {
    "div", "p", "li", "ul", "ol", "dl", "dt", "dd", "table", "thead", "tbody",
    "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
    "header", "footer", "nav", "pre", "blockquote", "figure", "figcaption",
    "hr", "br", "caption", "aside",
}
# Content inside these tags is discarded entirely.
SKIP = {"script", "style", "head", "svg"}


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []
        self.buf = []
        self.skip_depth = 0

    def _flush(self):
        text = " ".join("".join(self.buf).split())
        if text:
            self.lines.append(text)
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in BLOCK:
            self._flush()
        # Surface section anchors as context markers so you can see WHERE a change is.
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            for k, v in attrs:
                if k == "id":
                    self.buf.append(f"[#{v}] ")

    def handle_endtag(self, tag):
        if tag in SKIP:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in BLOCK:
            self._flush()

    def handle_data(self, data):
        if self.skip_depth:
            return
        self.buf.append(data)

    def close(self):
        super().close()
        self._flush()


def resolve(path):
    """Accept a file, or a gen dir containing out/html/vkspec.html."""
    if os.path.isdir(path):
        cand = os.path.join(path, "out", "html", "vkspec.html")
        if os.path.isfile(cand):
            return cand
        cand = os.path.join(path, "vkspec.html")
        if os.path.isfile(cand):
            return cand
        sys.exit(f"error: no vkspec.html found under {path}")
    if os.path.isfile(path):
        return path
    sys.exit(f"error: no such file or directory: {path}")


def to_text(path):
    p = Extractor()
    with open(path, encoding="utf-8", errors="replace") as f:
        p.feed(f.read())
    p.close()
    return [l + "\n" for l in p.lines]


def main(argv):
    if len(argv) == 2:
        sys.stdout.writelines(to_text(resolve(argv[1])))
        return 0
    if len(argv) == 3:
        import difflib
        a, b = resolve(argv[1]), resolve(argv[2])
        diff = difflib.unified_diff(
            to_text(a), to_text(b), fromfile=a, tofile=b, n=3
        )
        sys.stdout.writelines(diff)
        return 0
    sys.exit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
