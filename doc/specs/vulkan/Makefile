# Copyright (c) 2014-2016 The Khronos Group Inc.
# Copyright notice at https://www.khronos.org/registry/speccopyright.html

# Vulkan Specification makefile
#
# Default targets:
#  - XHTML, XHTML chunked, and PDF specs ('allspecs')
#  - HTML single-document reference pages ('manhtml' and 'manpdf')
#  - HTML and nroff separate reference pages ('manpages' and 'manhtmlpages')
#  - Validator scripts ('allchecks')
#
# The 'html' target is deprecated but still supported, for now. It uses
# a different toolchain than XHTML/PDF outputs, isn't quite compatible,
# and will not be published, but is faster to generate for quick tests.

all: alldocs allchecks

alldocs: allspecs allman

allspecs: xhtml chunked pdf

allman: manhtml manpdf manpages manhtmlpages

allchecks: checkinc checklinks

# Note that the := assignments below are immediate, not deferred, and
# are therefore order-dependent in the Makefile

APINAME=Vulkan
QUIET?=@
ASCIIDOC ?= asciidoc.py
A2X ?= a2x.py
DBLATEX ?= dblatex
# DBLATEXPREFIX can be overriden by setting it as an environment variable if
# the not installed in the standard location on your distribution
DBLATEXPREFIX ?= /etc/asciidoc/dblatex
RM=rm -f
RMRF=rm -rf
MKDIR=mkdir -p
CP=cp
ECHO:=echo
# Target directories for output files
# HTMLDIR - 'html' target
# XHTMLDIR - 'xhtml' target
# PDFDIR - 'pdf' target
# CHECKDIR - 'allchecks' target
OUTDIR :=../../../out/core
HTMLDIR := $(OUTDIR)/html
XHTMLDIR := $(OUTDIR)/xhtml
PDFDIR := $(OUTDIR)/pdf
CHECKDIR := $(OUTDIR)/checks
# Images used in the API spec
IMAGEPATH :=images
ICONPATH :=$(IMAGEPATH)/icons
PDFXSL :=config/vkspec-dblatex.xsl
PDFSTY :=config/vkspec-dblatex.sty
PYTHON ?= python3

# asciidoc / a2x attributes to set.
# XMLLINT    normally unset - to detect problems with intermediate files
# NOTEOPTS   sets options controlling which NOTEs are generated
# ATTRIBOPTS sets {apiname} to "Vulkan" and enables MathJax generation
# VKCONF     contains Vulkan-specific Asciidoc macros
# ADOCOPTS   options for asciidoc->HTML output
# ADOCPDFOPTS options for asciidoc->PDF output via dblatex (not using a2x)
# A2XOPTS    options for a2x->{HTML,PDF} output
XMLLINT    = --no-xmllint
NOTEOPTS   = -a editing-notes -a implementation-guide
ATTRIBOPTS = -a apiname=$(APINAME)@ -a mathjax
VKCONF	   = config/vkspec.conf
ADOCOPTS   = $(ATTRIBOPTS) $(NOTEOPTS) -f config/mathjax-asciidoc.conf \
	     -f $(VKCONF) $(VERBOSE)
ADOCPDFOPTS= $(ATTRIBOPTS) $(NOTEOPTS) -f config/mathjax-docbook.conf \
	     -f $(VKCONF) $(VERBOSE)
A2XOPTS    = $(ATTRIBOPTS) $(NOTEOPTS) \
	     --asciidoc-opts="-f config/mathjax-docbook.conf -f $(VKCONF)" \
	     --xsltproc-opts="--param generate.consistent.ids 1" \
	     $(XMLLINT) $(VERBOSE) --icons

# XSL customizing Asciibook XSL to pass through equations and add
# MathJax. This varies depending on target type.
XHTMLXSL   = config/docbook-xsl/xhtml.xsl
CHUNKEDXSL = config/docbook-xsl/chunked.xsl

# dblatex options passed two ways, directly to dblatex and via a2x.
DBLATEXOPTS := $(KEEP) -V -T db2latex -I. -I images -I images/icons -s $(DBLATEXPREFIX)/asciidoc-dblatex.sty
A2XDBLATEXOPTS := --dblatex-opts='$(DBLATEXOPTS)'

# Set VERBOSE to -v to see what asciidoc is doing.
# Set KEEP to -d to retain intermediate dblatex files
VERBOSE =
KEEP	=

# Misc. files to clean up (see 'checkinc' target below)
DIRT :=

.PHONY: directories

ICONFILES := \
    $(ICONPATH)/caution.png \
    $(ICONPATH)/example.png \
    $(ICONPATH)/home.png \
    $(ICONPATH)/important.png \
    $(ICONPATH)/next.png \
    $(ICONPATH)/note.png \
    $(ICONPATH)/prev.png \
    $(ICONPATH)/tip.png \
    $(ICONPATH)/up.png \
    $(ICONPATH)/warning.png
PNGFILES := $(ICONFILES) $(wildcard $(IMAGEPATH)/*.png)
# This is a horrible hack to avoid pulling in vulkantexture0.svg
SVGFILES := $(wildcard $(IMAGEPATH)/[A-Za-uw-z]*.svg)
PDFFILES := $(SVGFILES:.svg=.pdf)
# Some random directories and files that need to be copied into spec
# output directory
WEBIMAGES := $(SVGFILES:%=$(HTMLDIR)/%) $(PNGFILES:%=$(HTMLDIR)/%)
# File suffix for image targets for HTML and PDF Builds - Asciidoc {svgtype} attribute
SVGTYPEHTML := svg
SVGTYPEPDF := pdf
# Main (root) asciidoc spec source file
TOPDOC := vkspec.txt
# Included chapters of the API spec
CHAPTERS := $(wildcard chapters/[A-Za-z]*.txt appendices/[A-Za-z]*.txt chapters/wsi/[A-Za-z]*.txt)
INCLUDES := $(wildcard protos/*.txt structs/*.txt flags/*.txt enums/*.txt funcpointers/*.txt validity/structs/*.txt validity/protos/*.txt)
# All non-format-specific dependencies
COMMONDOCS := $(CHAPTERS) $(INCLUDES)
# A generate included file with the spec version, date, and git commit
SPECVERSION = specversion.txt
SPECREVISION = 1.0
SPECREMARK =

# Spec targets
# There is some complexity to try and avoid short virtual targets like 'html'
# causing specs to *always* be regenerated.

html: $(HTMLDIR)/vkspec.html $(TOPDOC) $(COMMONDOCS) $(WEBIMAGES)

$(HTMLDIR)/vkspec.html: $(VKCONF) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS) $(WEBIMAGES)
	$(QUIET)if test ! -d $(HTMLDIR) ; then $(MKDIR) $(HTMLDIR) ; fi
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) -o $(HTMLDIR)/vkspec.html -a svgpdf=$(SVGTYPEHTML) $(TOPDOC)

xhtml: $(XHTMLDIR)/vkspec.html $(TOPDOC) $(COMMONDOCS)

$(XHTMLDIR)/vkspec.html: $(VKCONF) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS)
	$(QUIET)if test ! -d $(XHTMLDIR) ; then $(MKDIR) $(XHTMLDIR) ; fi
	$(QUIET)$(A2X) $(A2XOPTS) -f xhtml $(TOPDOC) \
	    --xsl-file=$(XHTMLXSL) \
	    -a toc2 -a toclevels=2 --destination-dir=$(XHTMLDIR) \
	    -a svgpdf=$(SVGTYPEHTML)

chunked: $(OUTDIR)/vkspec.chunked/index.html $(TOPDOC) $(COMMONDOCS)

$(OUTDIR)/vkspec.chunked/index.html: $(VKCONF) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS)
	$(QUIET)if test ! -d $(OUTDIR)/chunked ; then $(MKDIR) $(OUTDIR) ; fi
	$(QUIET)$(A2X) $(A2XOPTS) -f chunked $(TOPDOC) \
	    --xsl-file=$(CHUNKEDXSL) \
	    -a toc2 -a toclevels=2 --destination-dir=$(OUTDIR) \
	    -a svgpdf=$(SVGTYPEHTML)

pdf: $(PDFDIR)/vkspec.pdf

$(PDFDIR)/vkspec.pdf: $(PDFXSL) $(PDFSTY) $(PDFDIR)/vkspec.xml
	$(QUIET)$(DBLATEX) -b pdftex $(DBLATEXOPTS) \
	    -p "$(DBLATEXPREFIX)/asciidoc-dblatex.xsl" \
	    -p $(PDFXSL) -s $(PDFSTY) \
	    $(PDFDIR)/vkspec.xml -O $(PDFDIR)

$(PDFDIR)/vkspec.xml: $(VKCONF) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS) $(PDFDIR) $(PDFFILES)
	$(QUIET)$(ASCIIDOC) --backend docbook $(ADOCPDFOPTS) \
	    -a a2x-format=pdf -a svgpdf=pdf \
	    --out-file $(PDFDIR)/vkspec.xml $(TOPDOC)

$(PDFDIR):
	$(QUIET)if test ! -d $(PDFDIR) ; then $(MKDIR) $(PDFDIR) ; fi

# Generate Asciidoc attributes for spec version / date
# Could use `git log -1 --format="%cd"` to get branch commit date
# This used to be a dependency in the spec html/chunked/pdf targets,
# but that's likely to lead to merge conflicts. Just regenerate
# when pushing a new spec for review to the sandbox.
# The dependency on HEAD is per the suggestion in
# http://neugierig.org/software/blog/2014/11/binary-revisions.html
GITHEAD := ../../../.git/logs/HEAD
$(SPECVERSION): $(GITHEAD)
	$(QUIET)echo ":revnumber: $(SPECREVISION)" > $@
	$(QUIET)echo ":revdate: " `date` >> $@
	$(QUIET)echo ":revremark: $(SPECREMARK) from git branch:" \
	    `git symbolic-ref --short HEAD` \
	    "commit:" `git log -1 --format="%H"` >> $@

styleguide: $(OUTDIR)/styleguide.html

STYLESRC = style/styleguide.txt
$(OUTDIR)/styleguide.html: $(VKCONF) $(SPECVERSION) $(STYLESRC)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) \
	    -o $(OUTDIR)/styleguide.html -a svgpdf=$(SVGTYPEHTML) \
	    $(STYLESRC)

clean: clean_html clean_pdf clean_chunked clean_checks clean_dirt

clean_html:
	$(QUIET)$(RMRF) $(HTMLDIR) $(XHTMLDIR)
	$(QUIET)$(RM) $(OUTDIR)/apispec.html

clean_pdf:
	$(QUIET)$(RM) $(PDFDIR)/vkspec.pdf $(PDFDIR)/vkspec.xml $(OUTDIR)/apispec.pdf

clean_chunked:
	$(QUIET)$(RMRF) $(OUTDIR)/vkspec.chunked

clean_checks:
	$(QUIET)$(RMRF) $(CHECKDIR)

clean_dirt:
	$(QUIET)$(RM) $(DIRT)

# Man page targets for individual pages
MANDIR:=man
-include man/manpages.mak

# Man page targets for HTML and PDF single-file documents

manpdf: $(OUTDIR)/apispec.pdf

manhtml: $(OUTDIR)/apispec.html

$(OUTDIR)/apispec.pdf: $(CONFFILE) man/apispec.txt $(MANSOURCES) $(PDFXSL)
	$(QUIET)if test ! -d $(OUTDIR) ; then $(MKDIR) $(OUTDIR) ; fi
	$(QUIET)$(A2X) -f pdf $(A2XDBLATEXOPTS) $(A2XOPTS) --icons man/apispec.txt --destination-dir=$(OUTDIR)

$(OUTDIR)/apispec.html: $(CONFFILE) man/apispec.txt $(MANSOURCES) $(SVGFILES)
	$(QUIET)if test ! -d $(OUTDIR) ; then $(MKDIR) $(OUTDIR) ; fi
	$(QUIET)$(ASCIIDOC) $(ADOCOPTS) -d book -b html --out-file=$(OUTDIR)/apispec.html man/apispec.txt

$(HTMLDIR)/images/%: images/%
	$(QUIET)$(MKDIR) $(@D)
	$(QUIET)$(CP) $< $@

# Automated (though heuristic) checks of consistency in the spec and
# ref page sources

# Validate includes in spec source vs. includes actually in the tree
# Generates file in $(CHECKDIR)
#   $(NOTINSPEC) notInSpec.txt - include files only found in XML, not in spec
# Intermediate files removed after the run
#   $(ACTUAL) - include files generated from vk.xml
#   $(INSPEC) - include files referenced from the spec (not ref page) source
# Other files which could be generated but are basically useless
#   include files only found in the spec source - comm -13 $(ACTUAL) $(INSPEC)
#   include files both existing and referenced by the spec - comm -12 $(ACTUAL) $(INSPEC)
INCFILES = $(CHECKDIR)/incfiles
ACTUAL = $(CHECKDIR)/actual
INSPEC = $(CHECKDIR)/inspec
NOTINSPEC = $(CHECKDIR)/notInSpec.txt
checkinc:
	$(QUIET)if test ! -d $(CHECKDIR) ; then $(MKDIR) $(CHECKDIR) ; fi
	$(QUIET)ls $(INCLUDES) | sort > $(ACTUAL)
	$(QUIET)cat $(CHAPTERS) | \
	    egrep '^include::\.\./' | tr -d '[]' | \
	    sed -e 's#^include::\.\./##g' | sort > $(INCFILES)
	$(QUIET)echo "List of API include files repeatedly included in the API specification"  > $(NOTINSPEC)
	$(QUIET)echo "----------------------------------------------------------------------" >> $(NOTINSPEC)
	$(QUIET)uniq -d $(INCFILES) >> $(NOTINSPEC)
	$(QUIET)(echo ; echo "List of API include files not referenced in the API specification") >> $(NOTINSPEC)
	$(QUIET)echo "-----------------------------------------------------------------" >> $(NOTINSPEC)
	$(QUIET)comm -23 $(ACTUAL) $(INCFILES) >> $(NOTINSPEC)
	$(QUIET)echo "Include files not found in the spec source are in $(CHECKDIR)/notInSpec.txt"
	$(QUIET)$(RM) $(INCFILES) $(ACTUAL) $(INSPEC)

# Validate link tags in spec and ref page sources against vk.xml
# (represented in vkapi.py, which is autogenerated along with the
# headers and ref page includes).
# Generates files in $(CHECKDIR):
#   specErrs.txt - errors & warnings in API spec
#   manErrs.txt - errors & warnings in man pages
checklinks:
	$(QUIET)if test ! -d $(CHECKDIR) ; then $(MKDIR) $(CHECKDIR) ; fi
	$(QUIET)echo "Generating link checks for spec (specErrs.txt) and man pages (manErrs.txt)"
	$(QUIET)$(PYTHON) checkLinks.py -follow man/[Vv][Kk]*.txt > $(CHECKDIR)/manErrs.txt
	$(QUIET)$(PYTHON) checkLinks.py -follow $(CHAPTERS) > $(CHECKDIR)/specErrs.txt

# README file with build instructions
README.html: README.txt
	$(ASCIIDOC) -b html5 README.txt
