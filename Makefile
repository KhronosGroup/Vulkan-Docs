# Copyright (c) 2014-2020 The Khronos Group Inc.
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
# To build the spec with a specific version included, set the
# $(VERSIONS) variable on the make command line to a space-separated
# list of version names (e.g. VK_VERSION_1_2) *including all previous
# versions of the API* (e.g. VK_VERSION_1_1 must also include
# VK_VERSION_1_0). $(VERSIONS) is converted into asciidoc and generator
# script arguments $(VERSIONATTRIBS) and $(VERSIONOPTIONS)
#
# To build the specification and reference pages with optional
# extensions included, set the $(EXTENSIONS) variable on the make
# command line to a space-separated list of extension names.
# $(EXTENSIONS) is converted into asciidoc and generator script
# arguments $(EXTATTRIBS) and $(EXTOPTIONS).

# If a recipe fails, delete its target file. Without this cleanup, the leftover
# file from the failed recipe can falsely satisfy dependencies on subsequent
# runs of `make`.
.DELETE_ON_ERROR:

VERSIONS := VK_VERSION_1_0 VK_VERSION_1_1 VK_VERSION_1_2
VERSIONATTRIBS := $(foreach version,$(VERSIONS),-a $(version))
VERSIONOPTIONS := $(foreach version,$(VERSIONS),-feature $(version))

EXTS := $(sort $(EXTENSIONS) $(DIFFEXTENSIONS))
EXTATTRIBS := $(foreach ext,$(EXTS),-a $(ext))
EXTOPTIONS := $(foreach ext,$(EXTS),-extension $(ext))

# APITITLE can be set to extra text to append to the document title,
# normally used when building with extensions included.
APITITLE =

# IMAGEOPTS is normally set to generate inline SVG images, but can be
# overridden to an empty string, since the inline option doesn't work
# well with our HTML diffs.
IMAGEOPTS = inline

# The default 'all' target builds the following sub-targets:
#  html - HTML single-page API specification
#  pdf - PDF single-page API specification
#  styleguide - HTML5 single-page "Documentation and Extensions" guide
#  registry - HTML5 single-page XML Registry Schema documentation
#  manhtml - HTML5 single-page reference guide - NOT SUPPORTED
#  manpdf - PDF reference guide - NOT SUPPORTED
#  manhtmlpages - HTML5 separate per-feature reference pages
#  allchecks - Python sanity checker for script markup and macro use

all: alldocs allchecks

alldocs: allspecs allman

allspecs: html pdf styleguide registry

allman: manhtmlpages

allchecks:
	$(PYTHON) $(SCRIPTS)/check_spec_links.py -Werror --ignore_count 0

# Note that the := assignments below are immediate, not deferred, and
# are therefore order-dependent in the Makefile

QUIET	 ?= @
PYTHON	 ?= python3
ASCIIDOC ?= asciidoctor
RUBY	 = ruby
NODEJS	 = node
PATCH	 = patch
RM	 = rm -f
RMRF	 = rm -rf
MKDIR	 = mkdir -p
CP	 = cp
ECHO	 = echo
GS_EXISTS := $(shell command -v gs 2> /dev/null)

# Path to Python scripts used in generation
SCRIPTS  = scripts

# Target directories for output files
# HTMLDIR - 'html' target
# PDFDIR - 'pdf' target
# CHECKDIR - 'allchecks' target
OUTDIR	  := $(CURDIR)/out
HTMLDIR   := $(OUTDIR)/html
VUDIR	  := $(OUTDIR)/validation
PDFDIR	  := $(OUTDIR)/pdf
CHECKDIR  := $(OUTDIR)/checks

# PDF Equations are written to SVGs, this dictates the location to store those files (temporary)
PDFMATHDIR:=$(OUTDIR)/equations_temp

# Set VERBOSE to -v to see what asciidoc is doing.
VERBOSE =

# asciidoc attributes to set (defaults are usually OK)
# NOTEOPTS sets options controlling which NOTEs are generated
# PATCHVERSION must equal VK_HEADER_VERSION from vk.xml
# ATTRIBOPTS sets the API revision and enables KaTeX generation
# VERSIONATTRIBS sets attributes for enabled API versions (set above
#	     based on $(VERSIONS))
# EXTATTRIBS sets attributes for enabled extensions (set above based on
#	     $(EXTENSIONS))
# EXTRAATTRIBS sets additional attributes, if passed to make
# ADOCMISCOPTS miscellaneous options controlling error behavior, etc.
# ADOCEXTS asciidoctor extensions to load
# ADOCOPTS options for asciidoc->HTML5 output

NOTEOPTS     = -a editing-notes -a implementation-guide
PATCHVERSION = 136
ifneq (,$(findstring VK_VERSION_1_2,$(VERSIONS)))
SPECREVISION = 1.2.$(PATCHVERSION)
else
ifneq (,$(findstring VK_VERSION_1_1,$(VERSIONS)))
SPECREVISION = 1.1.$(PATCHVERSION)
else
SPECREVISION = 1.0.$(PATCHVERSION)
endif
endif

# Spell out ISO 8601 format as not all date commands support --rfc-3339
SPECDATE     = $(shell echo `date -u "+%Y-%m-%d %TZ"`)

# Generate Asciidoc attributes for spec remark
# Could use `git log -1 --format="%cd"` to get branch commit date
# This used to be a dependency in the spec html/pdf targets,
# but that's likely to lead to merge conflicts. Just regenerate
# when pushing a new spec for review to the sandbox.
# The dependency on HEAD is per the suggestion in
# http://neugierig.org/software/blog/2014/11/binary-revisions.html
SPECREMARK = from git branch: $(shell echo `git symbolic-ref --short HEAD 2> /dev/null || echo Git branch not available`) \
	     commit: $(shell echo `git log -1 --format="%H" 2> /dev/null || echo Git commit not available`)

# Base path to SPIR-V extensions on the web.
SPIRVPATH = https://htmlpreview.github.io/?https://github.com/KhronosGroup/SPIRV-Registry/blob/master/extensions

# Some of the attributes used in building all spec documents:
#   chapters - absolute path to chapter sources
#   appendices - absolute path to appendix sources
#   images - absolute path to images
#   generated - absolute path to generated sources
ATTRIBOPTS   = -a revnumber="$(SPECREVISION)" \
	       -a revdate="$(SPECDATE)" \
	       -a revremark="$(SPECREMARK)" \
	       -a apititle="$(APITITLE)" \
	       -a stem=latexmath \
	       -a imageopts="$(IMAGEOPTS)" \
	       -a appendices=$(CURDIR)/appendices \
	       -a chapters=$(CURDIR)/chapters \
	       -a images=$(IMAGEPATH) \
	       -a generated=$(GENERATED) \
	       -a spirv="$(SPIRVPATH)" \
	       $(VERSIONATTRIBS) \
	       $(EXTATTRIBS) \
	       $(EXTRAATTRIBS)
ADOCMISCOPTS = --failure-level ERROR
ADOCEXTS     = -r $(CURDIR)/config/spec-macros.rb -r $(CURDIR)/config/tilde_open_block.rb
ADOCOPTS     = -d book $(ADOCMISCOPTS) $(ATTRIBOPTS) $(NOTEOPTS) $(VERBOSE) $(ADOCEXTS)

ADOCHTMLEXTS = -r $(CURDIR)/config/katex_replace.rb

# ADOCHTMLOPTS relies on the relative runtime path from the output HTML
# file to the katex scripts being set with KATEXDIR. This is overridden
# by some targets.
# ADOCHTMLOPTS also relies on the absolute build-time path to the
# 'stylesdir' containing our custom CSS.
KATEXDIR     = katex
ADOCHTMLOPTS = $(ADOCHTMLEXTS) -a katexpath=$(KATEXDIR) \
	       -a stylesheet=khronos.css -a stylesdir=$(CURDIR)/config \
	       -a sectanchors

ADOCPDFEXTS  = -r asciidoctor-pdf -r asciidoctor-mathematical -r $(CURDIR)/config/asciidoctor-mathematical-ext.rb
ADOCPDFOPTS  = $(ADOCPDFEXTS) -a mathematical-format=svg \
	       -a imagesoutdir=$(PDFMATHDIR) \
	       -a pdf-stylesdir=config/themes -a pdf-style=pdf

ADOCVUEXTS = -r $(CURDIR)/config/vu-to-json.rb
ADOCVUOPTS = $(ADOCVUEXTS)

.PHONY: directories

# Images used by the spec. These are included in generated HTML now.
IMAGEPATH = $(CURDIR)/images
SVGFILES  = $(wildcard $(IMAGEPATH)/*.svg)

# Top-level spec source file
SPECSRC := vkspec.txt
# Static files making up sections of the API spec.
SPECFILES = $(wildcard chapters/[A-Za-z]*.txt appendices/[A-Za-z]*.txt chapters/*/[A-Za-z]*.txt appendices/*/[A-Za-z]*.txt)
# Shorthand for where different types generated files go.
# All can be relocated by overriding GENERATED in the make invocation.
GENERATED      = $(CURDIR)/gen
APIPATH        = $(GENERATED)/api
VALIDITYPATH   = $(GENERATED)/validity
HOSTSYNCPATH   = $(GENERATED)/hostsynctable
METAPATH       = $(GENERATED)/meta
# Dynamically generated markers when many generated files are made at once
APIDEPEND      = $(APIPATH)/timeMarker
VALIDITYDEPEND = $(VALIDITYPATH)/timeMarker
HOSTSYNCDEPEND = $(HOSTSYNCPATH)/timeMarker
METADEPEND     = $(METAPATH)/timeMarker
# All generated dependencies
GENDEPENDS     = $(APIDEPEND) $(VALIDITYDEPEND) $(HOSTSYNCDEPEND) $(METADEPEND)
# All non-format-specific dependencies
COMMONDOCS     = $(SPECFILES) $(GENDEPENDS)

# Script to add href to anchors
GENANCHORLINKS = $(SCRIPTS)/genanchorlinks.py

# Install katex in $(OUTDIR)/katex for reference by all HTML targets
# README.md is a proxy for all the katex files that need to be installed
katexinst: KATEXDIR = katex
katexinst: $(OUTDIR)/$(KATEXDIR)/README.md

$(OUTDIR)/$(KATEXDIR)/README.md: katex/README.md
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(RMRF)  $(OUTDIR)/$(KATEXDIR)
	$(QUIET)$(CP) -rf katex $(OUTDIR)

# Spec targets
# There is some complexity to try and avoid short virtual targets like 'html'
# causing specs to *always* be regenerated.
ROSWELL = ros
ROSWELLOPTS ?= dynamic-space-size=4000
CHUNKER = $(HOME)/common-lisp/asciidoctor-chunker/roswell/asciidoctor-chunker.ros
CHUNKINDEX = $(CURDIR)/config/chunkindex
# Only the $(ROSWELL) step is required unless the search index is to be
# generated and incorporated into the chunked spec.
#
# Dropped $(QUIET) for now
# Should set NODE_PATH=/usr/local/lib/node_modules or wherever, outside Makefile
# Copying chunked.js into target avoids a warning from the chunker
chunked: $(HTMLDIR)/vkspec.html $(SPECSRC) $(COMMONDOCS)
	$(QUIET)$(PATCH) $(HTMLDIR)/vkspec.html -o $(HTMLDIR)/prechunked.html $(CHUNKINDEX)/custom.patch
	$(QUIET)$(CP) $(CHUNKINDEX)/chunked.css $(CHUNKINDEX)/chunked.js \
	    $(CHUNKINDEX)/lunr.js $(HTMLDIR)
	$(QUIET)$(ROSWELL) $(ROSWELLOPTS) $(CHUNKER) \
	    $(HTMLDIR)/prechunked.html -o $(HTMLDIR)
	$(QUIET)$(RM) $(HTMLDIR)/prechunked.html
	$(QUIET)$(RUBY) $(CHUNKINDEX)/generate-index.rb $(HTMLDIR)/chap*html | \
	    $(NODEJS) $(CHUNKINDEX)/build-index.js > $(HTMLDIR)/search.index.js

html: $(HTMLDIR)/vkspec.html $(SPECSRC) $(COMMONDOCS)

$(HTMLDIR)/vkspec.html: KATEXDIR = ../katex
$(HTMLDIR)/vkspec.html: $(SPECSRC) $(COMMONDOCS) katexinst
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ $(SPECSRC)
	$(QUIET)$(PYTHON) $(GENANCHORLINKS) $@ $@

diff_html: $(HTMLDIR)/diff.html $(SPECSRC) $(COMMONDOCS)

$(HTMLDIR)/diff.html: KATEXDIR = ../katex
$(HTMLDIR)/diff.html: $(SPECSRC) $(COMMONDOCS) katexinst
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) -a diff_extensions="$(DIFFEXTENSIONS)" -r $(CURDIR)/config/extension-highlighter.rb --trace -o $@ $(SPECSRC)

pdf: $(PDFDIR)/vkspec.pdf $(SPECSRC) $(COMMONDOCS)

$(PDFDIR)/vkspec.pdf: $(SPECSRC) $(COMMONDOCS)
	$(QUIET)$(MKDIR) $(PDFDIR)
	$(QUIET)$(MKDIR) $(PDFMATHDIR)
	$(QUIET)$(ASCIIDOC) -b pdf $(ADOCOPTS) $(ADOCPDFOPTS) -o $@ $(SPECSRC)
ifndef GS_EXISTS
	$(QUIET) echo "Warning: Ghostscript not installed, skipping pdf optimization"
else
	$(QUIET)$(CURDIR)/config/optimize-pdf $@
	$(QUIET)rm $@
	$(QUIET)mv $(PDFDIR)/vkspec-optimized.pdf $@
endif
	$(QUIET)rm -rf $(PDFMATHDIR)

validusage: $(VUDIR)/validusage.json $(SPECSRC) $(COMMONDOCS)

$(VUDIR)/validusage.json: $(SPECSRC) $(COMMONDOCS)
	$(QUIET)$(MKDIR) $(VUDIR)
	$(QUIET)$(ASCIIDOC) $(ADOCOPTS) $(ADOCVUOPTS) --trace -a json_output=$@ -o $@ $(SPECSRC)

# Vulkan Documentation and Extensions, a.k.a. "Style Guide" documentation

STYLESRC = styleguide.txt
STYLEFILES = $(wildcard style/[A-Za-z]*.txt)

styleguide: $(OUTDIR)/styleguide.html

$(OUTDIR)/styleguide.html: KATEXDIR = katex
$(OUTDIR)/styleguide.html: $(STYLESRC) $(STYLEFILES) $(GENDEPENDS) katexinst
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ $(STYLESRC)


# Vulkan API Registry (XML Schema) documentation
# Currently does not use latexmath / KaTeX

REGSRC = registry.txt

registry: $(OUTDIR)/registry.html

$(OUTDIR)/registry.html: $(REGSRC)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ $(REGSRC)


# Reflow text in spec sources
REFLOW = $(SCRIPTS)/reflow.py
REFLOWOPTS = -overwrite

reflow:
	$(QUIET) echo "Warning: please verify the spec outputs build without changes!"
	$(PYTHON) $(REFLOW) $(REFLOWOPTS) $(SPECSRC) $(SPECFILES) $(STYLESRC) $(STYLEFILES)

# Clean generated and output files

clean: clean_html clean_pdf clean_man clean_checks clean_generated clean_validusage

clean_html:
	$(QUIET)$(RMRF) $(HTMLDIR) $(OUTDIR)/katex
	$(QUIET)$(RM) $(OUTDIR)/apispec.html $(OUTDIR)/styleguide.html \
	    $(OUTDIR)/registry.html

clean_pdf:
	$(QUIET)$(RMRF) $(PDFDIR) $(OUTDIR)/apispec.pdf

clean_man:
	$(QUIET)$(RMRF) $(MANHTMLDIR)

clean_checks:
	$(QUIET)$(RMRF) $(CHECKDIR)

MANTRASH = $(filter-out $(MANDIR)/copyright-ccby.txt $(MANDIR)/footer.txt,$(wildcard $(MANDIR)/*.txt)) $(LOGFILE)
clean_generated:
	$(QUIET)$(RMRF) $(APIPATH) $(HOSTSYNCPATH) $(VALIDITYPATH) $(METAPATH)
	$(QUIET)$(RMRF) include/vulkan/vulkan_*.h $(SCRIPTS)/vkapi.py
	$(QUIET)$(RM) config/extDependency.*
	$(QUIET)$(RM) $(MANTRASH)
	$(QUIET)$(RMRF) $(PDFMATHDIR)

clean_validusage:
	$(QUIET)$(RM) $(VUDIR)/validusage.json


# Ref page targets for individual pages
MANDIR	    := man
MANSECTION  := 3

# These lists should be autogenerated

# Ref page sources, split up by core API (CORE), KHR extensions (KHR), and
# other extensions (VEN). This is a hacky approach to ref page generation
# now that the single-branch model is in place, and there are outstanding
# issues to resolve it. For now, always build all reference pages.
# Changing MANSOURCES to e.g. $(CORESOURCES) will restore older behavior.

KHRSOURCES   = $(wildcard $(MANDIR)/*KHR.txt)
MACROSOURCES = $(wildcard $(MANDIR)/VK_*[A-Z][A-Z].txt)
VENSOURCES   = $(filter-out $(KHRSOURCES) $(MACROSOURCES),$(wildcard $(MANDIR)/*[A-Z][A-Z].txt))
CORESOURCES  = $(filter-out $(KHRSOURCES) $(VENSOURCES),$(wildcard $(MANDIR)/[Vv][Kk]*.txt $(MANDIR)/PFN*.txt))
MANSOURCES   = $(wildcard $(MANDIR)/[Vv][Kk]*.txt $(MANDIR)/PFN*.txt)
MANCOPYRIGHT = $(MANDIR)/copyright-ccby.txt $(MANDIR)/footer.txt

# Generation of ref page asciidoctor sources by extraction from the
# specification.
#
# Should have a proper dependency causing the man page sources to be
# generated by running genRef (once), but adding $(MANSOURCES) to the
# targets causes genRef to run once/target.
#
# Should pass in $(EXTOPTIONS) to determine which pages to generate.
# For now, all core and extension ref pages are extracted by genRef.py.
GENREF = $(SCRIPTS)/genRef.py
LOGFILE = man/logfile
man/apispec.txt: $(SPECFILES) $(GENREF) $(SCRIPTS)/reflib.py $(SCRIPTS)/vkapi.py
	$(PYTHON) $(GENREF) -log $(LOGFILE) -extpath $(CURDIR)/appendices $(EXTOPTIONS) $(SPECFILES)

# These targets are HTML5 ref pages
#
# The recursive $(MAKE) is an apparently unavoidable hack, since the
# actual list of man page sources isn't known until after
# man/apispec.txt is generated. $(GENDEPENDS) is generated before
# running the recursive make, so it doesn't trigger twice
manhtmlpages: man/apispec.txt $(GENDEPENDS)
	$(MAKE) -e buildmanpages

MANHTMLDIR  = $(OUTDIR)/man/html
MANHTML     = $(MANSOURCES:$(MANDIR)/%.txt=$(MANHTMLDIR)/%.html)
buildmanpages: $(MANHTML)

# Asciidoctor options to build reference pages
# cross-file-links makes custom macros link to other refpages
# refprefix includes the refpage (not spec) extension metadata
# isrefpage is for refpage-specific content
# html_spec_relative is where to find the full specification
ADOCREFOPTS = -a cross-file-links -a refprefix='refpage.' -a isrefpage -a html_spec_relative='../../html/vkspec.html'

$(MANHTMLDIR)/%.html: KATEXDIR = ../../katex
$(MANHTMLDIR)/%.html: $(MANDIR)/%.txt $(MANCOPYRIGHT) $(GENDEPENDS) katexinst
	$(QUIET)$(MKDIR) $(MANHTMLDIR)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) $(ADOCREFOPTS) -d manpage -o $@ $<

# The 'manhtml' and 'manpdf' targets are NO LONGER SUPPORTED by Khronos.
# They generate HTML5 and PDF single-file versions of the ref pages.
# The generated ref page sources are included by man/apispec.txt, and
# are always generated along with man/apispec.txt. Therefore there's no
# need for a recursive $(MAKE) or a $(MANHTML) dependency, unlike the
# manhtmlpages target.

manpdf: $(OUTDIR)/apispec.pdf

$(OUTDIR)/apispec.pdf: $(SPECVERSION) man/apispec.txt $(MANCOPYRIGHT) $(SVGFILES) $(GENDEPENDS)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(MKDIR) $(PDFMATHDIR)
	$(QUIET)$(ASCIIDOC) -b pdf -a html_spec_relative='html/vkspec.html' $(ADOCOPTS) $(ADOCPDFOPTS) -o $@ man/apispec.txt
ifndef GS_EXISTS
	$(QUIET) echo "Warning: Ghostscript not installed, skipping pdf optimization"
else
	$(QUIET)$(CURDIR)/config/optimize-pdf $@
	$(QUIET)rm $@
	$(QUIET)mv $(OUTDIR)/apispec-optimized.pdf $@
endif

manhtml: $(OUTDIR)/apispec.html

$(OUTDIR)/apispec.html: KATEXDIR = katex
$(OUTDIR)/apispec.html: ADOCMISCOPTS =
$(OUTDIR)/apispec.html: $(SPECVERSION) man/apispec.txt $(MANCOPYRIGHT) $(SVGFILES) $(GENDEPENDS) katexinst
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 -a html_spec_relative='html/vkspec.html' $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ man/apispec.txt

# Targets generated from the XML and registry processing scripts
#   $(SCRIPTS)/vkapi.py - Python encoding of the registry
# The $(...DEPEND) targets are files named 'timeMarker' in generated
# target directories. They serve as proxies for the multiple generated
# files written for each target:
#   apiinc / proxy $(APIDEPEND) - API interface include files in $(APIPATH)
#   hostsyncinc / proxy $(HOSTSYNCDEPEND) - host sync table include files in $(HOSTSYNCPATH)
#   validinc / proxy $(VALIDITYDEPEND) - API validity include files in $(VALIDITYPATH)
#   extinc / proxy $(METADEPEND) - extension appendix metadata include files in $(METAPATH)
#
# $(VERSIONOPTIONS) specifies the core API versions which are included
# in these targets, and is set above based on $(VERSIONS)
#
# $(EXTOPTIONS) specifies the extensions which are included in these
# targets, and is set above based on $(EXTENSIONS).
#
# $(GENVKEXTRA) are extra options that can be passed to genvk.py, e.g.
# '-diag diag'

REGISTRY   = xml
VKXML	   = $(REGISTRY)/vk.xml
GENVK	   = $(SCRIPTS)/genvk.py
GENVKOPTS  = $(VERSIONOPTIONS) $(EXTOPTIONS) $(GENVKEXTRA) -registry $(VKXML)
GENVKEXTRA =

$(SCRIPTS)/vkapi.py: $(VKXML) $(GENVK)
	$(PYTHON) $(GENVK) $(GENVKOPTS) -o scripts vkapi.py

apiinc: $(APIDEPEND)

$(APIDEPEND): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(APIPATH)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(APIPATH) apiinc

hostsyncinc: $(HOSTSYNCDEPEND)

$(HOSTSYNCDEPEND): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(HOSTSYNCPATH)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(HOSTSYNCPATH) hostsyncinc

validinc: $(VALIDITYDEPEND)

$(VALIDITYDEPEND): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(VALIDITYPATH)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(VALIDITYPATH) validinc

extinc: $(METAPATH)/timeMarker

$(METADEPEND): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(METAPATH)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(METAPATH) extinc

# Debugging aid - generate all files from registry XML
# This leaves out config/extDependency.sh intentionally as it only
# needs to be updated when the extension dependencies in vk.xml change.

generated: $(SCRIPTS)/vkapi.py $(GENDEPENDS)

# Extension dependencies derived from vk.xml
# Both Bash and Python versions are generated

config/extDependency.sh: config/extDependency.stamp
config/extDependency.py: config/extDependency.stamp

DEPSCRIPT = $(SCRIPTS)/make_ext_dependency.py
config/extDependency.stamp: $(VKXML) $(DEPSCRIPT)
	$(QUIET)$(PYTHON) $(DEPSCRIPT) -registry $(VKXML) \
	    -outscript config/extDependency.sh \
	    -outpy config/extDependency.py
	$(QUIET)touch $@
