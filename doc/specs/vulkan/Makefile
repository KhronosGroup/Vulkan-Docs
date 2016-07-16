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

allspecs: xhtml chunked pdf styleguide

allman: manhtml manpdf manpages manhtmlpages

allchecks: checkinc checklinks

# Note that the := assignments below are immediate, not deferred, and
# are therefore order-dependent in the Makefile

QUIET?=@
# On Windows, use a2x.py. On Linux, use a2x.
ifeq ($(OS),Windows_NT)
      ASCIIDOC ?= asciidoc.py
      A2X ?= a2x.py
else
      ASCIIDOC ?= asciidoc
      A2X ?= a2x
endif 

DBLATEX ?= dblatex
# DBLATEXPREFIX can be overriden by setting it as an environment variable,
# if not installed in the standard location on your distribution
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
OUTDIR := ../../../out/1.0
HTMLDIR := $(OUTDIR)/html
XHTMLDIR := $(OUTDIR)/xhtml
PDFDIR := $(OUTDIR)/pdf
CHECKDIR := $(OUTDIR)/checks
STYLEXHTMLDIR := $(OUTDIR)/style
# Images used in the API spec
IMAGEPATH :=images
ICONPATH :=$(IMAGEPATH)/icons
PDFXSL :=config/vkspec-dblatex.xsl
PDFSTY :=config/vkspec-dblatex.sty
PYTHON ?= python3

# Set VERBOSE to -v to see what asciidoc is doing.
# Set KEEP to -d to retain intermediate dblatex files
VERBOSE =
KEEP	=

# asciidoc / a2x attributes to set.
# XMLLINT    normally unset - to detect problems with intermediate files
# NOTEOPTS   sets options controlling which NOTEs are generated
# ATTRIBOPTS sets the api revision and enables MathJax generation
# CONFIG     Vulkan-specific Asciidoc macros. File used depends on target.
# ADOCOPTS   options for asciidoc->HTML output
# ADOCPDFOPTS options for asciidoc->PDF output via dblatex (not using a2x)
# A2XOPTS    options for a2x->{HTML,PDF} output
XMLLINT    = --no-xmllint
NOTEOPTS   = -a editing-notes -a implementation-guide
ATTRIBOPTS = -a apirevision="$(SPECREVISION)" -a mathjax
CONFIG	   = config/vkspec.conf
ADOCOPTS   = $(ATTRIBOPTS) $(NOTEOPTS) -f config/mathjax-asciidoc.conf \
	     -f $(CONFIG) $(VERBOSE)
ADOCPDFOPTS= $(ATTRIBOPTS) $(NOTEOPTS) -f config/mathjax-docbook.conf \
	     -f $(CONFIG) $(VERBOSE)
A2XOPTS    = $(ATTRIBOPTS) $(NOTEOPTS) \
	     --asciidoc-opts="-f config/mathjax-docbook.conf -f $(CONFIG)" \
	     --xsltproc-opts="--param generate.consistent.ids 1" \
	     $(XMLLINT) $(VERBOSE) --icons

# XSL customizing Asciibook XSL to pass through equations and add
# MathJax. This varies depending on target type.
XHTMLXSL   = config/docbook-xsl/xhtml.xsl
CHUNKEDXSL = config/docbook-xsl/chunked.xsl

# dblatex options passed two ways, directly to dblatex and via a2x.
DBLATEXOPTS := $(KEEP) -V -T db2latex -I. -I images -I images/icons -s $(DBLATEXPREFIX)/asciidoc-dblatex.sty
A2XDBLATEXOPTS := --dblatex-opts='$(DBLATEXOPTS)'

# Misc. files to clean up (see 'checkinc' target below)
DIRT = $(SPECVERSION)

.PHONY: directories $(MANHTMLDIR) $(MANPAGEDIR)

ICONFILES := $(wildcard $(ICONPATH)/*.png)
PNGFILES := $(ICONFILES) $(wildcard $(IMAGEPATH)/*.png)
# Don't use vulkantexture0.svg as a source SVG file, PNG is available
SVGFILES := $(filter-out $(IMAGEPATH)/vulkantexture0.svg,$(wildcard $(IMAGEPATH)/*.svg))
PDFFILES := $(SVGFILES:.svg=.pdf)
# Misc. directories and files that need to be copied into output directory
WEBIMAGES := $(SVGFILES:%=$(HTMLDIR)/%) $(PNGFILES:%=$(HTMLDIR)/%)
# File suffix for image targets for HTML and PDF Builds - Asciidoc {svgtype} attribute
SVGTYPEHTML := svg
SVGTYPEPDF := pdf
# Main (root) asciidoc spec source file
TOPDOC := vkspec.txt
# Files making up sections of the API spec. The wildcard expression
# should work in extension branches to pull in those files as well.
CHAPTERS := $(wildcard chapters/[A-Za-z]*.txt appendices/[A-Za-z]*.txt chapters/*/[A-Za-z]*.txt appendices/*/[A-Za-z]*.txt)
INCLUDES := $(wildcard protos/*.txt structs/*.txt flags/*.txt enums/*.txt funcpointers/*.txt validity/structs/*.txt validity/protos/*.txt)
# All non-format-specific dependencies
COMMONDOCS := $(CHAPTERS) $(INCLUDES)
# A generated included file with the spec version, date, and git commit
SPECVERSION = specversion.txt
SPECREVISION = 1.0.21
SPECREMARK =

# Spec targets
# There is some complexity to try and avoid short virtual targets like 'html'
# causing specs to *always* be regenerated.

html: $(HTMLDIR)/vkspec.html $(TOPDOC) $(COMMONDOCS) $(WEBIMAGES)

$(HTMLDIR)/vkspec.html: $(CONFIG) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS) $(WEBIMAGES)
	$(QUIET)if test ! -d $(HTMLDIR) ; then $(MKDIR) $(HTMLDIR) ; fi
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) \
	    -o $(HTMLDIR)/vkspec.html -a svgpdf=$(SVGTYPEHTML) $(TOPDOC)

xhtml: $(XHTMLDIR)/vkspec.html $(TOPDOC) $(COMMONDOCS)

$(XHTMLDIR)/vkspec.html: $(CONFIG) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS)
	$(QUIET)if test ! -d $(XHTMLDIR) ; then $(MKDIR) $(XHTMLDIR) ; fi
	$(QUIET)$(A2X) $(A2XOPTS) -f xhtml $(TOPDOC) \
	    --xsl-file=$(XHTMLXSL) \
	    -a toc2 -a toclevels=2 --destination-dir=$(XHTMLDIR) \
	    -a svgpdf=$(SVGTYPEHTML)

chunked: $(OUTDIR)/vkspec.chunked/index.html $(TOPDOC) $(COMMONDOCS)

$(OUTDIR)/vkspec.chunked/index.html: $(CONFIG) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS)
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

$(PDFDIR)/vkspec.xml: $(CONFIG) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS) $(PDFDIR) $(PDFFILES)
	$(QUIET)$(ASCIIDOC) --backend docbook $(ADOCPDFOPTS) \
	    -a a2x-format=pdf -a svgpdf=pdf \
	    --out-file $(PDFDIR)/vkspec.xml $(TOPDOC)

$(PDFDIR):
	$(QUIET)if test ! -d $(PDFDIR) ; then $(MKDIR) $(PDFDIR) ; fi

# Generate Asciidoc attributes for spec version / date
GITHEAD := ../../../.git/logs/HEAD
ifeq ($(wildcard $(GITHEAD)),)
# If GITHEAD does not exist, don't include branch info.
$(SPECVERSION):
	$(QUIET)echo ":revnumber: $(SPECREVISION)" > $@
	$(QUIET)echo ":revdate: " `date` >> $@
	$(QUIET)echo ":revremark: Git branch information not available" >> $@
else
# Could use `git log -1 --format="%cd"` to get branch commit date
# This used to be a dependency in the spec html/chunked/pdf targets,
# but that's likely to lead to merge conflicts. Just regenerate
# when pushing a new spec for review to the sandbox.
# The dependency on HEAD is per the suggestion in
# http://neugierig.org/software/blog/2014/11/binary-revisions.html
$(SPECVERSION): $(GITHEAD)
	$(QUIET)echo ":revnumber: $(SPECREVISION)" > $@
	$(QUIET)echo ":revdate: " `date` >> $@
	$(QUIET)echo ":revremark: $(SPECREMARK) from git branch:" \
	    `git symbolic-ref --short HEAD` \
	    "commit:" `git log -1 --format="%H"` >> $@
endif

STYLESRC = styleguide.txt
STYLEFILES = $(wildcard style/[A-Za-z]*.txt)

styleguide: $(OUTDIR)/styleguide.html

$(OUTDIR)/styleguide.html: $(CONFIG) $(SPECVERSION) $(STYLESRC) $(STYLEFILES)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) \
	    -o $@ -a svgpdf=$(SVGTYPEHTML) \
	    $(STYLESRC)

clean: clean_html clean_pdf clean_chunked clean_checks clean_dirt clean_man

clean_man:
	$(RM) $(MANHTML)
	$(RMRF) $(MANHTMLDIR)
	$(RM) $(MANPAGES)
	$(RMRF) $(MANPAGEDIR)

clean_html:
	$(QUIET)$(RMRF) $(HTMLDIR) $(XHTMLDIR) $(STYLEXHTMLDIR)
	$(QUIET)$(RM) $(OUTDIR)/apispec.html $(OUTDIR)/styleguide.html

clean_pdf:
	$(QUIET)$(RM) \
	    $(PDFDIR)/vkspec.pdf \
	    $(PDFDIR)/vkspec.xml \
	    $(OUTDIR)/apispec.pdf \
	    $(OUTDIR)/apispec.xml

clean_chunked:
	$(QUIET)$(RMRF) $(OUTDIR)/vkspec.chunked

clean_checks:
	$(QUIET)$(RMRF) $(CHECKDIR)

clean_dirt:
	$(QUIET)$(RM) $(DIRT)

# Ref page targets for individual pages
MANDIR	    := man
MANSECTION  := 3

# These lists should be autogenerated

# Ref page sources, split up by core vs. author IDs
# CORESOURCES expansion will accidentally pull in macros defined by
# extensions. Hopefully that won't happen.
WSISOURCES  := $(wildcard $(MANDIR)/*KHR.txt)
EXTSOURCES  := $(wildcard $(MANDIR)/*EXT.txt)
CORESOURCES := $(filter-out $(WSISOURCES) $(EXTSOURCES) $(MANDIR)/vkman.css,$(wildcard $(MANDIR)/[Vv][Kk]* $(MANDIR)/PFN*txt))
MANSOURCES  := $(CORESOURCES) $(WSISOURCES) $(EXTSOURCES)

MANCOPYRIGHT:= $(MANDIR)/khronoscopyright.txt $(MANDIR)/footer.txt
MANPAGEDIR  := $(OUTDIR)/man/$(MANSECTION)
MANPAGES    := $(MANSOURCES:$(MANDIR)/%.txt=$(MANPAGEDIR)/%.$(MANSECTION))
MANHTMLDIR  := $(OUTDIR)/man/html
MANHTML     := $(MANSOURCES:$(MANDIR)/%.txt=$(MANHTMLDIR)/%.html)

manpagesall: manpages manhtmlpages

manpages: $(MANPAGEDIR) $(MANPAGES)

manhtmlpages: $(MANHTMLDIR) $(MANHTML)

# Automatic generation of ref pages. Needs to have a proper dependency
# causing the man page sources to be generated by running genRef (once),
# but adding $(MANSOURCES) to the targets causes genRef to run
# once/target.
man/apispec.txt: $(CHAPTERS) genRef.py reflib.py vkapi.py
	$(PYTHON) genRef.py $(CHAPTERS)

# These dependencies don't take into account include directives

$(MANPAGEDIR)/%.$(MANSECTION): $(MANDIR)/%.$(MANSECTION)
	$(QUIET)mv $< $@

$(MANDIR)/%.$(MANSECTION): CONFIG=config/manpages.conf

$(MANDIR)/%.$(MANSECTION): $(MANDIR)/%.txt $(MANCOPYRIGHT) config/manpages.conf
	$(QUIET)$(ECHO) Building $@
	$(QUIET)$(A2X) -d manpage -f manpage --asciidoc-opts "-f config/manpages.conf" $(A2XOPTS) $<

$(MANHTMLDIR)/%.html: CONFIG=config/manpages.conf

$(MANHTMLDIR)/%.html: $(MANDIR)/%.txt $(MANCOPYRIGHT) config/manpages.conf
	$(QUIET)$(ECHO) Building $@
	$(QUIET)$(ASCIIDOC) -b html5 -d manpage $(ADOCOPTS) \
	    -a themedir=$(CURDIR)/config -a theme=vkman \
	    -o $@ -a svgpdf=$(SVGTYPEHTML) $<

$(MANHTMLDIR):
	$(QUIET)$(MKDIR) $@

$(MANPAGEDIR):
	$(QUIET)$(MKDIR) $@

# Man page targets for HTML and PDF single-file documents

manpdf: $(OUTDIR)/apispec.pdf

manhtml: $(OUTDIR)/apispec.html

$(OUTDIR)/apispec.pdf: $(PDFXSL) $(PDFSTY) $(OUTDIR)/apispec.xml
	$(QUIET)$(DBLATEX) -b pdftex $(DBLATEXOPTS) \
	    -p "$(DBLATEXPREFIX)/asciidoc-dblatex.xsl" \
	    -p $(PDFXSL) -s $(PDFSTY) \
	    $(OUTDIR)/apispec.xml -O $(OUTDIR)

$(OUTDIR)/apispec.xml: $(CONFIG) $(SPECVERSION) man/apispec.txt $(MANSOURCES) $(MANCOPYRIGHT) $(PDFXSL) $(PDFSTY)
	$(QUIET)$(ASCIIDOC) --backend docbook $(ADOCPDFOPTS) \
	    -a a2x-format=pdf -a svgpdf=pdf \
	    -o $@ man/apispec.txt

$(OUTDIR)/apispec.html: $(CONFIG) $(SPECVERSION) man/apispec.txt $(MANSOURCES) $(MANCOPYRIGHT) $(SVGFILES)
	$(QUIET)if test ! -d $(OUTDIR) ; then $(MKDIR) $(OUTDIR) ; fi
	$(QUIET)$(ASCIIDOC) -b html5 -d book $(ADOCOPTS) \
	    -a themedir=$(CURDIR)/config -a theme=vkspec-xhtml \
	    -o $@ -a svgpdf=$(SVGTYPEHTML) man/apispec.txt

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
README.html: $(CONFIG) $(SPECVERSION) README.txt
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) \
	    -o $@ README.txt
