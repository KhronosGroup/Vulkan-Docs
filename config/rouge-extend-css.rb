# Copyright 2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Khronos overrides for Rouge 'github' theme CSS for accessibility.
# See (note that this code is evolving, works as of asciidoctor 2.0.12):
# https://github.com/asciidoctor/asciidoctor/blob/master/lib/asciidoctor/syntax_highlighter/rouge.rb

include ::Asciidoctor

class ExtendedRougeSyntaxHighlighter < (Asciidoctor::SyntaxHighlighter.for 'rouge')
  register_for 'rouge'

  # Insert rouge stylesheet from super
  # Then replace many 'github' theme colors for accessibility compliance
  # It would be better to use rouge's stylesheet factory, if it has one
  def docinfo location, doc, opts
    overrides = %(<style>
/* Khronos overrides for Rouge 'github' theme for accessibility */
/* Basically everything is overridden, but it's unclear how to add a new Rouge theme */
/* Codelike overrides */
pre.rouge .cm, pre.rouge .cp, pre.rouge .c1, pre.rouge .cs,
pre.rouge .c, pre.rouge .ch, pre.rouge .cd, pre.rouge .cpf,
pre.rouge .gh, pre.rouge .bp {
  color: #5f5f5f;
}
/* Numberlike overrides */
pre.rouge .mf, pre.rouge .mh, pre.rouge .il, pre.rouge .mi,
pre.rouge .mo, pre.rouge .m, pre.rouge .mb, pre.rouge .mx {
  color: #007f7f;
}
/* Namelike overrides */
pre.rouge .ne, pre.rouge .nf, pre.rouge .fm, pre.rouge .nl {
  color: #5f0000;
}
/* Other things ANDI warns about - unsure of their purposes */
pre.rouge .go, pre.rouge .gu {
  color: #727272;
}
pre.rouge .sr {
  color: #008512;
}
pre.rouge .na, pre.rouge .nb {
  color: #007f7f;
}
pre.rouge .no, pre.rouge .vc, pre.rouge .vg, pre.rouge .vi,
pre.rouge .nv, pre.rouge .vm {
  color: #007f7f;
}
pre.rouge .w {
  color: #727272;
}
</style>)

    # super can return either <style> or <link> markup, both work
    %(#{super}
#{overrides})
  end
end

