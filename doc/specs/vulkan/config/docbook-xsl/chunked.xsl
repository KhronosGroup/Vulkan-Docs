<!--
  Generates chunked XHTML documents from DocBook XML source using DocBook XSL
  stylesheets.

  NOTE: The URL reference to the current DocBook XSL stylesheets is
  rewritten to point to the copy on the local disk drive by the XML catalog
  rewrite directives so it doesn't need to go out to the Internet for the
  stylesheets. This means you don't need to edit the <xsl:import> elements on
  a machine by machine basis.
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
<xsl:import href="http://docbook.sourceforge.net/release/xsl/current/xhtml/chunk.xsl"/>
<xsl:import href="common.xsl"/>
<xsl:param name="navig.graphics.path">images/icons/</xsl:param>
<xsl:param name="admon.graphics.path">images/icons/</xsl:param>
<xsl:param name="callout.graphics.path" select="'images/icons/callouts/'"/>

<!-- Generate consistent id attribute values if document is unchanged -->
<xsl:param name="generate.consistent.ids" select="1"></xsl:param>

<!-- Add MathJax <script> tags  to document <head> -->
<xsl:template name="user.head.content">
    <script type="text/x-mathjax-config">
        MathJax.Hub.Config({
            MathML: { extensions: ["content-mathml.js"] },
            tex2jax: { inlineMath: [['$','$'], ['\\(','\\)']] }
        });
    </script>
    <script type="text/javascript"
        src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
    </script>
</xsl:template>
</xsl:stylesheet>
