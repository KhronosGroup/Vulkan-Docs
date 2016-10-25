# Copyright (c) 2014-2016 The Khronos Group Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Vulkan Specification makefile
#
# To build the specification and reference pages with optional
# extensions included, set the $(EXTENSIONS) variable on the make
# command line to a space-separated list of extension names. The
# VK_KHR_sampler_mirror_clamp_to_edge extension which is a required part
# of Vulkan 1.0, is always included. $(EXTENSIONS) is converted into
# asciidoc and generator script arguments $(EXTATTRIBS) and
# $(EXTOPTIONS).

EXTS := $(sort VK_KHR_sampler_mirror_clamp_to_edge $(EXTENSIONS))
EXTATTRIBS := $(foreach ext,$(EXTS),-a $(ext))
EXTOPTIONS := $(foreach ext,$(EXTS),-extension $(ext))

# APITITLE can be set to extra text to append to the document title,
# normally used when building with extensions included.
APITITLE =

# The default 'all' target builds the following sub-targets:
#  xhtml - XHTML single-page API specification
#  pdf - PDF single-page API specification
#  styleguide - HTML single-page "Documentation and Extensions" guide
#  manhtml - XHTML single-page reference guide
#  manpdf - PDF reference guide
#  manhtmlpages - XHTML separate per-feature reference pages
#  checkinc - validator script for asciidoc include files
#  checklinks - validator script for asciidoc xrefs
#
# The following targets are supported, but not invoked by default:
#  html - HTML5 single-page API specification
#  chunked - XHTML chunked (page per section) API specification
#  manpages - nroff Unix 'man' format separate per-feature reference pages

all: alldocs allchecks

alldocs: allspecs allman

allspecs: xhtml pdf styleguide

allman: manhtml manpdf manhtmlpages

allchecks: checkinc checklinks

# Note that the := assignments below are immediate, not deferred, and
# are therefore order-dependent in the Makefile

QUIET	 ?= @
PYTHON	 ?= python3
ASCIIDOC ?= asciidoc.py
DBLATEX  ?= dblatex
XSLTPROC ?= xsltproc
# DBLATEXPREFIX can be overriden by setting it as an environment variable,
# if not installed in the standard location on your distribution
DBLATEXPREFIX ?= /etc/asciidoc/dblatex
RM	 = rm -f
RMRF	 = rm -rf
MKDIR	 = mkdir -p
CP	 = cp
ECHO	 = echo

# Target directories for output files
# HTMLDIR - 'html' target
# XHTMLDIR - 'xhtml' target
# CHUNKDIR - 'chunked' target
# PDFDIR - 'pdf' target
# CHECKDIR - 'allchecks' target
# STYLEXHTMLDIR - 'styleguide' target
OUTDIR	  := ../../../out/1.0
HTMLDIR   := $(OUTDIR)/html
XHTMLDIR  := $(OUTDIR)/xhtml
CHUNKDIR  := $(OUTDIR)/chunked
PDFDIR	  := $(OUTDIR)/pdf
CHECKDIR  := $(OUTDIR)/checks
# Images used in the API spec
IMAGEPATH :=images
ICONPATH  :=$(IMAGEPATH)/icons
PDFXSL	  :=config/vkspec-dblatex.xsl
PDFSTY	  :=config/vkspec-dblatex.sty

# Set VERBOSE to -v to see what asciidoc is doing.
# Set KEEP to -d to retain intermediate dblatex files
VERBOSE =
KEEP	=

# asciidoc attributes to set.
# XMLLINT    normally unset - to detect problems with intermediate files
# NOTEOPTS   sets options controlling which NOTEs are generated
# ATTRIBOPTS sets the api revision and enables MathJax generation
# EXTATTRIBS sets attributes for enabled extensions (set above based on
#	     $(EXTENSIONS))
# CONFIG     Vulkan-specific Asciidoc macros. File used depends on target.
# ADOCOPTS   options for asciidoc->HTML output
# ADOCDBOPTS options for asciidoc->XHTML or PDF output via docbook
XMLLINT    = --no-xmllint
NOTEOPTS   = -a editing-notes -a implementation-guide
ATTRIBOPTS = -a apirevision="$(SPECREVISION)" \
	     -a apititle="$(APITITLE)" \
	     -a mathjax $(EXTATTRIBS)
CONFIG	   = config/vkspec.conf
ADOCOPTS   = $(ATTRIBOPTS) $(NOTEOPTS) -f config/mathjax-asciidoc.conf \
	     -f $(CONFIG) $(VERBOSE)
ADOCDBOPTS = $(ATTRIBOPTS) $(NOTEOPTS) -f config/mathjax-docbook.conf \
	     -f $(CONFIG) $(VERBOSE)

# All the options except the first are taken from a2x defaults
XSLTOPTS = \
    --param generate.consistent.ids 1 \
    --stringparam callout.graphics 1 \
    --stringparam navig.graphics 1 \
    --stringparam admon.textlabel 0 \
    --stringparam admon.graphics 1

# XSL customizing Asciibook XSL to pass through equations and add
# MathJax. This varies depending on target type.
XHTMLXSL = config/docbook-xsl/xhtml.xsl
CHUNKXSL = config/docbook-xsl/chunked.xsl
MANPAGEXSL = config/docbook-xsl/manpage.xsl

# dblatex options, passed directly to dblatex
DBLATEXOPTS := $(KEEP) -V -T db2latex -I. -I images -I images/icons -s $(DBLATEXPREFIX)/asciidoc-dblatex.sty

# Misc. files to clean up (see 'checkinc' target below)
DIRT = $(SPECVERSION)

.PHONY: directories

# Images and icons that are used in or referenced by targets.
# For some targets they must be copied to output directories.
ICONFILES := $(wildcard $(ICONPATH)/*.png)
PNGFILES := $(ICONFILES) $(wildcard $(IMAGEPATH)/*.png)
# Don't use vulkantexture0.svg as a source SVG file, PNG is available
SVGFILES := $(filter-out $(IMAGEPATH)/vulkantexture0.svg,$(wildcard $(IMAGEPATH)/*.svg))
PDFFILES := $(SVGFILES:.svg=.pdf)

# File suffix for image targets for HTML and PDF Builds - Asciidoc {svgtype} attribute
SVGTYPEHTML := svg
SVGTYPEPDF := pdf
# Top-level spec source file
TOPDOC := vkspec.txt
# Files making up sections of the API spec. The wildcard expression
# should work in extension branches to pull in those files as well.
CHAPTERS = $(wildcard chapters/[A-Za-z]*.txt appendices/[A-Za-z]*.txt chapters/*/[A-Za-z]*.txt appendices/*/[A-Za-z]*.txt)
GENINCLUDE = $(wildcard api/*/[A-Za-z]*.txt validity/*/[A-Za-z]*.txt hostsynctable/*.txt)
GENDEPENDS = api/timeMarker validity/timeMarker hostsynctable/timeMarker
# All non-format-specific dependencies
COMMONDOCS = $(CHAPTERS) $(GENINCLUDE) $(GENDEPENDS)
# A generated included file containing the spec version, date, and git commit
SPECVERSION = specversion.txt
SPECREVISION = 1.0.32
SPECREMARK =

# Spec targets
# There is some complexity to try and avoid short virtual targets like 'html'
# causing specs to *always* be regenerated.

html: $(HTMLDIR)/vkspec.html $(TOPDOC) $(COMMONDOCS)

$(HTMLDIR)/vkspec.html: $(CONFIG) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS)
	$(QUIET)$(MKDIR) $(HTMLDIR)/images/icons
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) \
	    -a themedir=$(CURDIR)/config -a theme=vkspec-html \
	    -o $(HTMLDIR)/vkspec.html -a svgpdf=$(SVGTYPEHTML) $(TOPDOC)
	# Copy resource files in explicitly
	$(QUIET)$(CP) $(SVGFILES) $(PNGFILES) $(HTMLDIR)/images
	$(QUIET)$(CP) $(ICONFILES) $(HTMLDIR)/images/icons

xhtml: $(XHTMLDIR)/vkspec.html $(TOPDOC) $(COMMONDOCS)

$(XHTMLDIR)/vkspec.html: $(CONFIG) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS)
	$(QUIET)$(MKDIR) $(XHTMLDIR)/images/icons $(XHTMLDIR)/config
	$(QUIET)$(ASCIIDOC) --backend docbook $(ADOCDBOPTS) \
	    -a a2x-format=xhtml -a svgpdf=$(SVGTYPEHTML) \
	    -o $(XHTMLDIR)/vkspec.xml $(TOPDOC)
	$(QUIET)$(XSLTPROC) $(XSLTOPTS) -o $@ $(XHTMLXSL) \
	    $(XHTMLDIR)/vkspec.xml
	# Copy resource files in explicitly
	$(QUIET)$(CP) config/vkspec-xhtml.css $(XHTMLDIR)/config/
	$(QUIET)$(CP) $(SVGFILES) $(PNGFILES) $(XHTMLDIR)/images
	$(QUIET)$(CP) $(ICONFILES) $(XHTMLDIR)/images/icons
	$(QUIET)$(RM) $(XHTMLDIR)/vkspec.xml

chunked: $(CHUNKDIR)/index.html $(TOPDOC) $(COMMONDOCS)

$(CHUNKDIR)/index.html: $(CONFIG) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS)
	$(QUIET)$(MKDIR) $(CHUNKDIR)/images/icons $(CHUNKDIR)/config
	$(QUIET)$(ASCIIDOC) --backend docbook $(ADOCDBOPTS) \
	    -a a2x-format=chunked -a svgpdf=$(SVGTYPEHTML) \
	    -o $(CHUNKDIR)/vkspec.xml $(TOPDOC)
	$(QUIET)$(XSLTPROC) $(XSLTOPTS) \
	    --stringparam base.dir $(CHUNKDIR)/ \
	    -o $@ $(CHUNKXSL) $(CHUNKDIR)/vkspec.xml
	# Copy resource files in explicitly
	$(QUIET)$(CP) config/vkspec-xhtml.css $(CHUNKDIR)/config/
	$(QUIET)$(CP) $(SVGFILES) $(PNGFILES) $(CHUNKDIR)/images
	$(QUIET)$(CP) $(ICONFILES) $(CHUNKDIR)/images/icons
	$(QUIET)$(RM) $(CHUNKDIR)/vkspec.xml

pdf: $(PDFDIR)/vkspec.pdf

$(PDFDIR)/vkspec.pdf: $(CONFIG) $(SPECVERSION) $(TOPDOC) $(COMMONDOCS) $(PDFFILES)
	$(QUIET)$(MKDIR) $(PDFDIR)
	$(QUIET)$(ASCIIDOC) --backend docbook $(ADOCDBOPTS) \
	    -a a2x-format=pdf -a svgpdf=pdf \
	    -o $(PDFDIR)/vkspec.xml $(TOPDOC)
	$(QUIET)$(DBLATEX) -b pdftex $(DBLATEXOPTS) \
	    -p "$(DBLATEXPREFIX)/asciidoc-dblatex.xsl" \
	    -p $(PDFXSL) -s $(PDFSTY) \
	    -o $@ $(PDFDIR)/vkspec.xml
	$(QUIET)$(RM) $(PDFDIR)/vkspec.xml

# Generate Asciidoc attributes for spec version / date
GITHEAD := ../../../.git/logs/HEAD
# Spell out RFC2822 format as not all date commands support -R
DATE := `date -u "+%a, %d %b %Y %T %z"`
ifeq ($(wildcard $(GITHEAD)),)
# If GITHEAD does not exist, don't include branch info.
$(SPECVERSION):
	$(QUIET)echo ":revnumber: $(SPECREVISION)" > $@
	$(QUIET)echo ":revdate: " $(DATE) >> $@
	$(QUIET)echo ":revremark: $(SPECREMARK) Git branch information not available" >> $@
else
# Could use `git log -1 --format="%cd"` to get branch commit date
# This used to be a dependency in the spec html/chunked/pdf targets,
# but that's likely to lead to merge conflicts. Just regenerate
# when pushing a new spec for review to the sandbox.
# The dependency on HEAD is per the suggestion in
# http://neugierig.org/software/blog/2014/11/binary-revisions.html
$(SPECVERSION): $(GITHEAD)
	$(QUIET)echo ":revnumber: $(SPECREVISION)" > $@
	$(QUIET)echo ":revdate: " $(DATE) >> $@
	$(QUIET)echo ":revremark: $(SPECREMARK) from git branch:" \
	    `git symbolic-ref --short HEAD` \
	    "commit:" `git log -1 --format="%H"` >> $@
endif

# Vulkan Documentation and Extensions, a.k.a. "Style Guide"

STYLESRC = styleguide.txt
STYLEFILES = $(wildcard style/[A-Za-z]*.txt)

styleguide: $(OUTDIR)/styleguide.html

$(OUTDIR)/styleguide.html: $(CONFIG) $(SPECVERSION) $(STYLESRC) $(STYLEFILES) $(GENINCLUDE) $(GENDEPENDS)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) \
	    -a themedir=$(CURDIR)/config -a theme=vkspec-html \
	    -o $@ -a svgpdf=$(SVGTYPEHTML) \
	    $(STYLESRC)

# Reflow text in spec sources
REFLOW = reflow.py
REFLOWOPTS = -overwrite

reflow:
	$(QUIET) echo "Warning: please verify the spec outputs build without changes!"
	$(PYTHON) $(REFLOW) $(REFLOWOPTS) $(TOPDOC) $(CHAPTERS) $(STYLESRC) $(STYLEFILES)

# Clean generated and output files

clean: clean_html clean_pdf clean_man clean_checks clean_generated clean_dirt

clean_html:
	$(QUIET)$(RMRF) $(HTMLDIR) $(XHTMLDIR) $(CHUNKDIR)
	$(QUIET)$(RM) $(OUTDIR)/apispec.html $(OUTDIR)/styleguide.html

clean_pdf:
	$(QUIET)$(RM) $(PDFDIR)/vkspec.pdf $(OUTDIR)/apispec.pdf

clean_man:
	$(QUIET)$(RMRF) $(MANHTMLDIR)
	$(QUIET)$(RMRF) $(MANPAGEDIR)

clean_checks:
	$(QUIET)$(RMRF) $(CHECKDIR)

clean_generated:
	$(QUIET)$(RMRF) api/* hostsynctable/* validity/* vkapi.py
	$(QUIET)$(RM) man/apispec.txt man/[Vv][Kk]*.txt man/PFN*.txt

clean_dirt:
	$(QUIET)$(RM) $(DIRT)

# Ref page targets for individual pages
MANDIR	    := man
MANSECTION  := 3

# These lists should be autogenerated

# Ref page sources, split up by core API (CORE), KHR extensions (KHR), and
# other extensions (VEN). This is a hacky approach to ref page generation
# now that the single-branch model is in place, and there are outstanding
# issues to resolve it. For the moment, we always just build the core
# ref pages.

KHRSOURCES   = $(wildcard $(MANDIR)/*KHR.txt)
MACROSOURCES = $(wildcard $(MANDIR)/VK_*[A-Z][A-Z].txt)
VENSOURCES   = $(filter-out $(KHRSOURCES) $(MACROSOURCES),$(wildcard $(MANDIR)/*[A-Z][A-Z].txt))
CORESOURCES  = $(filter-out $(KHRSOURCES) $(VENSOURCES) $(MANDIR)/vkman.css,$(wildcard $(MANDIR)/[Vv][Kk]*.txt $(MANDIR)/PFN*.txt))
MANSOURCES   = $(CORESOURCES)
MANCOPYRIGHT = $(MANDIR)/copyright-ccby.txt $(MANDIR)/footer.txt

# Automatic generation of ref pages. Needs to have a proper dependency
# causing the man page sources to be generated by running genRef (once),
# but adding $(MANSOURCES) to the targets causes genRef to run
# once/target.
#
# @@ Needs to pass in $(EXTOPTIONS) and use that to determine which
# pages to generate. As it stands, all the extension ref pages are
# also generated, though they are not useable at present.
man/apispec.txt: $(CHAPTERS) genRef.py reflib.py vkapi.py
	$(PYTHON) genRef.py $(CHAPTERS)

# These dependencies don't take into account include directives

# These targets are Unix 'man' nroff source, and are essentially useless
# since the ref pages contain both LaTeX math equations and images.

MANPAGEDIR  := $(OUTDIR)/man/$(MANSECTION)
MANPAGES    = $(MANSOURCES:$(MANDIR)/%.txt=$(MANPAGEDIR)/%.$(MANSECTION))

manpages: man/apispec.txt $(MANPAGES)

$(MANPAGEDIR)/%.$(MANSECTION): CONFIG=config/manpages.conf

$(MANPAGEDIR)/%.$(MANSECTION): $(MANDIR)/%.txt $(MANCOPYRIGHT) config/manpages.conf $(GENINCLUDE) $(GENDEPENDS)
	$(QUIET)$(MKDIR) $(MANPAGEDIR)
	$(QUIET)$(ASCIIDOC) --backend docbook $(ADOCDBOPTS) --doctype manpage \
	    -a a2x-format=manpage -a svgpdf=$(SVGTYPEHTML) \
	    -o $@.xml $<
	$(QUIET)$(XSLTPROC) $(XSLTOPTS) -o $@ $(MANPAGEXSL) $@.xml
	$(QUIET)$(RM) $@.xml

# These targets are HTML ref pages

MANHTMLDIR  := $(OUTDIR)/man/html
MANHTML     = $(MANSOURCES:$(MANDIR)/%.txt=$(MANHTMLDIR)/%.html)

manhtmlpages: man/apispec.txt $(MANHTML)

$(MANHTMLDIR)/%.html: CONFIG=config/manpages.conf

$(MANHTMLDIR)/%.html: $(MANDIR)/%.txt $(MANCOPYRIGHT) config/manpages.conf $(GENINCLUDE) $(GENDEPENDS)
	$(QUIET)$(MKDIR) $(MANHTMLDIR)
	$(QUIET)$(ASCIIDOC) -b html5 -d manpage $(ADOCOPTS) \
	    -a themedir=$(CURDIR)/config -a theme=vkman \
	    -o $@ -a svgpdf=$(SVGTYPEHTML) $<

# These targets are HTML and PDF single-file versions of the ref pages

manpdf: $(OUTDIR)/apispec.pdf

manhtml: $(OUTDIR)/apispec.html

$(OUTDIR)/apispec.pdf: $(CONFIG) $(SPECVERSION) man/apispec.txt $(MANSOURCES) $(MANCOPYRIGHT) $(PDFXSL) $(PDFSTY) $(GENINCLUDE) $(GENDEPENDS)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) --backend docbook $(ADOCDBOPTS) \
	    -a a2x-format=pdf -a svgpdf=pdf \
	    -o $(OUTDIR)/apispec.xml man/apispec.txt
	$(QUIET)$(DBLATEX) -b pdftex $(DBLATEXOPTS) \
	    -p "$(DBLATEXPREFIX)/asciidoc-dblatex.xsl" \
	    -p $(PDFXSL) -s $(PDFSTY) \
	    -o $(OUTDIR) $(OUTDIR)/apispec.xml
	$(QUIET)$(RM) $(OUTDIR)/apispec.xml

$(OUTDIR)/apispec.html: $(CONFIG) $(SPECVERSION) man/apispec.txt $(MANSOURCES) $(MANCOPYRIGHT) $(SVGFILES) $(GENINCLUDE) $(GENDEPENDS)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 -d book $(ADOCOPTS) \
	    -a themedir=$(CURDIR)/config -a theme=vkspec-xhtml \
	    -o $@ -a svgpdf=$(SVGTYPEHTML) man/apispec.txt

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
	$(QUIET)ls $(GENINCLUDE) | sort > $(ACTUAL)
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
checklinks: vkapi.py
	$(QUIET)if test ! -d $(CHECKDIR) ; then $(MKDIR) $(CHECKDIR) ; fi
	$(QUIET)echo "Generating link checks for spec (specErrs.txt) and man pages (manErrs.txt)"
	$(QUIET)$(PYTHON) checkLinks.py -follow man/[Vv][Kk]*.txt > $(CHECKDIR)/manErrs.txt
	$(QUIET)$(PYTHON) checkLinks.py -follow $(CHAPTERS) > $(CHECKDIR)/specErrs.txt

# Targets generated from the XML and registry processing scripts
#   vkapi.py - Python encoding of the registry
#   api/timeMarker - proxy for 'apiincludes' - API include files under api/*/*.txt
#   hostsynctable/timeMarker - proxy for host sync table include files under hostsynctable/*.txt
#   validity/timeMarker - proxy for API validity include files under validity/*/*.txt
#
# $(EXTOPTIONS) specifies the extensions which are included in these
# targets, and is set above based on $(EXTENSIONS).

REGISTRY = ../../../src/spec
VKXML	 = $(REGISTRY)/vk.xml
GENVK	 = $(REGISTRY)/genvk.py
GENVKOPTS= $(EXTOPTIONS) -registry $(VKXML)

vkapi.py: $(VKXML) $(GENVK)
	$(PYTHON) $(GENVK) $(GENVKOPTS) -o . vkapi.py

apiinc: api/timeMarker

api/timeMarker: $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) api
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o api apiinc

hostsyncinc: hostsynctable/timeMarker

hostsynctable/timeMarker: $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) hostsynctable
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o hostsynctable hostsyncinc

validinc: validity/timeMarker

validity/timeMarker: $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) validity
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o validity validinc

# Debugging aid - generate all files from registry XML
generated: vkapi.py api/timeMarker hostsynctable/timeMarker validity/timeMarker

# README file with build instructions
README.html: $(CONFIG) $(SPECVERSION) README.adoc
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) \
	    -o $@ README.adoc
