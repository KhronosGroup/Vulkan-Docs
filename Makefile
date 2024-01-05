# Copyright 2014-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Vulkan Specification makefile
#
# To build the spec with a specific version included, set the
# $(VERSIONS) variable on the make command line to a space-separated
# list of version names (e.g. VK_VERSION_1_3) *including all previous
# versions of the API* (e.g. VK_VERSION_1_1 must also include
# VK_VERSION_1_0 and VKSC_VERSION_1_0 must also include VK_VERSION_1_2,
# VK_VERSION_1_1 & VK_VERSION_1_0). $(VERSIONS) is converted into generator
# script arguments $(VERSIONOPTIONS) and into $(ATTRIBFILE)
#
# To build the specification / reference pages (refpages) with optional
# extensions included, set the $(EXTENSIONS) variable on the make
# command line to a space-separated list of extension names.
# $(EXTENSIONS) is converted into generator script
# arguments $(EXTOPTIONS) and into $(ATTRIBFILE)

# If a recipe fails, delete its target file. Without this cleanup, the leftover
# file from the failed recipe can falsely satisfy dependencies on subsequent
# runs of `make`.
.DELETE_ON_ERROR:

# Support building both Vulkan and Vulkan SC APIs
# Allow the API to be overridden by the VULKAN_API environment variable
# supported options are 'vulkan' and 'vulkansc' or unset
# default to 'vulkan'
VULKAN_API ?= vulkan
ifeq ($(VULKAN_API),vulkan)
VERSIONS := VK_VERSION_1_0 VK_VERSION_1_1 VK_VERSION_1_2 VK_VERSION_1_3
else
VERSIONS := VK_VERSION_1_0 VK_VERSION_1_1 VK_VERSION_1_2 VKSC_VERSION_1_0
endif
VERSIONOPTIONS := $(foreach version,$(VERSIONS),-feature $(version))

EXTS := $(sort $(EXTENSIONS) $(DIFFEXTENSIONS))
EXTOPTIONS := $(foreach ext,$(EXTS),-extension $(ext))

# APITITLE can be set to extra text to append to the document title,
# normally used when building with extensions included.
APITITLE =

# IMAGEOPTS is normally set to generate inline SVG images, but can be
# overridden to an empty string, since the inline option does not work
# well with our HTML diffs.
IMAGEOPTS = inline

# The default 'all' target builds the following sub-targets:
#  html - HTML single-page API specification
#  pdf - PDF single-page API specification
#  styleguide - HTML5 single-page "Documentation and Extensions" guide
#  registry - HTML5 single-page XML Registry Schema documentation
#  manhtml - HTML5 single-page reference guide - NOT SUPPORTED
#  manpdf - PDF reference guide - NOT SUPPORTED
#  manhtmlpages - HTML5 separate per-feature refpages
#  allchecks - checks for style guide compliance, XML consistency,
#   internal link validity, and other easy to catch errors.

all: alldocs allchecks

alldocs: allspecs allman proposals

allspecs: html pdf styleguide registry

allman: manhtmlpages

# Invokes all the automated checks, but CHECK_XREFS can be set to empty
# on the command line to avoid building an HTML spec target.
CHECK_XREFS = check-xrefs
ifeq ($(VULKAN_API),vulkansc)
CHECK_XREFS =
endif
allchecks: check-copyright-dates \
    check-contractions \
    check-spelling \
    check-writing \
    check-bullets \
    check-reflow \
    check-links \
    check-consistency \
    check-undefined \
    check-txtfiles \
    $(CHECK_XREFS)

QUIET	 ?= @
VERYQUIET?= @
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

# Where the repo root is
ROOTDIR        = $(CURDIR)
# Where the spec files are
SPECDIR        = $(CURDIR)

# Path to scripts used in generation
SCRIPTS  = $(ROOTDIR)/scripts
# Path to configs and asciidoc extensions used in generation
CONFIGS  = $(ROOTDIR)/config

# Target directories for output files
# HTMLDIR - 'html' target
# PDFDIR - 'pdf' target
OUTDIR	  = $(GENERATED)/out
HTMLDIR   = $(OUTDIR)/html
VUDIR	  = $(OUTDIR)/validation
PDFDIR	  = $(OUTDIR)/pdf
PROPOSALDIR = $(OUTDIR)/proposals
JSAPIMAP  = $(GENERATED)/apimap.cjs
PYAPIMAP  = $(GENERATED)/apimap.py
RBAPIMAP  = $(GENERATED)/apimap.rb

# PDF Equations are written to SVGs, this dictates the location to store those files (temporary)
PDFMATHDIR = $(OUTDIR)/equations_temp

# Set VERBOSE to -v to see what asciidoc is doing.
VERBOSE =

# asciidoc attributes to set (defaults are usually OK)
# NOTEOPTS sets options controlling which NOTEs are generated
# PATCHVERSION must equal VK_HEADER_VERSION from vk.xml
# SCPATCHVERSION is specific to the Vulkan SC spec
# ATTRIBOPTS sets the API revision and enables KaTeX generation
# EXTRAATTRIBS sets additional attributes, if passed to make
# ADOCMISCOPTS miscellaneous options controlling error behavior, etc.
# ADOCEXTS asciidoctor extensions to load
# ADOCOPTS options for asciidoc->HTML5 output

NOTEOPTS     = -a editing-notes -a implementation-guide
PATCHVERSION = 275
BASEOPTS     =

ifneq (,$(findstring VKSC_VERSION_1_0,$(VERSIONS)))
VKSPECREVISION := 1.2.$(PATCHVERSION)
SCPATCHVERSION = 14
SPECREVISION = 1.0.$(SCPATCHVERSION)
BASEOPTS = -a baserevnumber="$(VKSPECREVISION)"
else

ifneq (,$(findstring VK_VERSION_1_3,$(VERSIONS)))
SPECMINOR = 3
else
ifneq (,$(findstring VK_VERSION_1_2,$(VERSIONS)))
SPECMINOR = 2
else
ifneq (,$(findstring VK_VERSION_1_1,$(VERSIONS)))
SPECMINOR = 1
else
SPECMINOR = 0
endif
endif
endif

SPECREVISION = 1.$(SPECMINOR).$(PATCHVERSION)
endif

# Spell out ISO 8601 format as not all date commands support --rfc-3339
SPECDATE     = $(shell echo `date -u "+%Y-%m-%d %TZ"`)

# Generate Asciidoc attributes for spec remark
# Could use `git log -1 --format="%cd"` to get branch commit date
# This used to be a dependency in the spec html/pdf targets,
# but that is likely to lead to merge conflicts. Just regenerate
# when pushing a new spec for review to the sandbox.
# The dependency on HEAD is per the suggestion in
# http://neugierig.org/software/blog/2014/11/binary-revisions.html
SPECREMARK = from git branch: $(shell echo `git symbolic-ref --short HEAD 2> /dev/null || echo Git branch not available`) \
	     commit: $(shell echo `git log -1 --format="%H" 2> /dev/null || echo Git commit not available`)

# Some of the attributes used in building all spec documents:
#   chapters - absolute path to chapter sources
#   appendices - absolute path to appendix sources
#   proposals - absolute path to proposal sources
#   images - absolute path to images
#   generated - absolute path to generated sources
#   refprefix - controls which generated extension metafiles are
#	included at build time. Must be empty for specification,
#	'refprefix.' for refpages (see ADOCREFOPTS below).
ATTRIBOPTS   = -a revnumber="$(SPECREVISION)" $(BASEOPTS) \
	       -a revdate="$(SPECDATE)" \
	       -a revremark="$(SPECREMARK)" \
	       -a apititle="$(APITITLE)" \
	       -a stem=latexmath \
	       -a imageopts="$(IMAGEOPTS)" \
	       -a config=$(ROOTDIR)/config \
	       -a appendices=$(SPECDIR)/appendices \
	       -a proposals=$(SPECDIR)/proposals \
	       -a chapters=$(SPECDIR)/chapters \
	       -a images=$(IMAGEPATH) \
	       -a generated=$(GENERATED) \
	       -a refprefix \
	       $(EXTRAATTRIBS)
ADOCMISCOPTS = --failure-level ERROR
# Non target-specific Asciidoctor extensions and options
# Look in $(GENERATED) for explicitly required non-extension Ruby, such
# as apimap.rb
ADOCEXTS     = -I$(GENERATED) \
	       -r $(CONFIGS)/spec-macros.rb \
	       -r $(CONFIGS)/open_listing_block.rb \
	       -r $(CONFIGS)/ifdef-mismatch.rb
ADOCOPTS     = -d book $(ADOCMISCOPTS) $(ATTRIBOPTS) $(NOTEOPTS) $(VERBOSE) $(ADOCEXTS)

# HTML target-specific Asciidoctor extensions and options
ADOCHTMLEXTS = -r $(CONFIGS)/katex_replace.rb \
	       -r $(CONFIGS)/loadable_html.rb \
	       -r $(CONFIGS)/vuid-expander.rb \
	       -r $(CONFIGS)/rouge-extend-css.rb \
	       -r $(CONFIGS)/genanchorlinks.rb

# ADOCHTMLOPTS relies on the relative runtime path from the output HTML
# file to the katex scripts being set with KATEXDIR. This is overridden
# by some targets.
# KaTeX source is copied from KATEXSRCDIR in the repository to
# KATEXINSTDIR in the output directory.
# KATEXDIR is the relative path from a target to KATEXINSTDIR, since
# that is coded into CSS, and set separately for each HTML target.
# ADOCHTMLOPTS also relies on the absolute build-time path to the
# 'stylesdir' containing our custom CSS.
KATEXSRCDIR  = $(ROOTDIR)/katex
KATEXINSTDIR = $(OUTDIR)/katex
ADOCHTMLOPTS = $(ADOCHTMLEXTS) -a katexpath=$(KATEXDIR) \
	       -a stylesheet=khronos.css \
	       -a stylesdir=$(ROOTDIR)/config \
	       -a sectanchors

# PDF target-specific Asciidoctor extensions and options
ADOCPDFEXTS  = -r asciidoctor-pdf \
	       -r asciidoctor-mathematical \
	       -r $(CONFIGS)/asciidoctor-mathematical-ext.rb \
	       -r $(CONFIGS)/vuid-expander.rb
ADOCPDFOPTS  = $(ADOCPDFEXTS) -a mathematical-format=svg \
	       -a imagesoutdir=$(PDFMATHDIR) \
	       -a pdf-fontsdir=$(CONFIGS)/fonts,GEM_FONTS_DIR \
	       -a pdf-stylesdir=$(CONFIGS)/themes -a pdf-style=pdf

# Valid usage-specific Asciidoctor extensions and options
ADOCVUEXTS = -r $(CONFIGS)/vu-to-json.rb -r $(CONFIGS)/quiet-include-failure.rb
# {vuprefix} precedes some anchors which are otherwise encountered twice
# by the validusage extractor.
# {attribute-missing} overrides the global setting, since the extractor
# reports a lot of false-flag warnings otherwise.
ADOCVUOPTS = $(ADOCVUEXTS) -a vuprefix=vu- -a attribute-missing=skip

.PHONY: directories

# Images used by the spec. These are included in generated HTML now.
IMAGEPATH = $(SPECDIR)/images
SVGFILES  = $(wildcard $(IMAGEPATH)/*.svg)

# Top-level spec source file
SPECSRC        = $(SPECDIR)/vkspec.adoc
# Static files making up sections of the API spec.
SPECFILES = $(wildcard $(SPECDIR)/chapters/[A-Za-z]*.adoc $(SPECDIR)/chapters/*/[A-Za-z]*.adoc $(SPECDIR)/appendices/[A-Za-z]*.adoc)
# Shorthand for where different types generated files go.
# All can be relocated by overriding GENERATED in the make invocation.
GENERATED      = $(CURDIR)/gen
REFPATH        = $(GENERATED)/refpage
APIPATH        = $(GENERATED)/api
VALIDITYPATH   = $(GENERATED)/validity
HOSTSYNCPATH   = $(GENERATED)/hostsynctable
METAPATH       = $(GENERATED)/meta
INTERFACEPATH  = $(GENERATED)/interfaces
SPIRVCAPPATH   = $(GENERATED)/spirvcap
FORMATSPATH    = $(GENERATED)/formats
SYNCPATH       = $(GENERATED)/sync
PROPOSALPATH   = $(SPECDIR)/proposals
# timeMarker is a proxy target created when many generated files are
# made at once
APIDEPEND      = $(APIPATH)/timeMarker
VALIDITYDEPEND = $(VALIDITYPATH)/timeMarker
HOSTSYNCDEPEND = $(HOSTSYNCPATH)/timeMarker
METADEPEND     = $(METAPATH)/timeMarker
INTERFACEDEPEND = $(INTERFACEPATH)/timeMarker
SPIRVCAPDEPEND = $(SPIRVCAPPATH)/timeMarker
FORMATSDEPEND = $(FORMATSPATH)/timeMarker
SYNCDEPEND = $(SYNCPATH)/timeMarker
RUBYDEPEND     = $(RBAPIMAP)
ATTRIBFILE     = $(GENERATED)/specattribs.adoc
# All generated dependencies
GENDEPENDS     = $(APIDEPEND) $(VALIDITYDEPEND) $(HOSTSYNCDEPEND) $(METADEPEND) $(INTERFACEDEPEND) $(SPIRVCAPDEPEND) $(FORMATSDEPEND) $(SYNCDEPEND) $(RUBYDEPEND) $(ATTRIBFILE)
# All non-format-specific dependencies
COMMONDOCS     = $(SPECFILES) $(GENDEPENDS)

# Script to translate math on build time
TRANSLATEMATH = $(NODEJS) $(SCRIPTS)/translate_math.js $(KATEXSRCDIR)/katex.min.js

# Install katex in KATEXINSTDIR ($(OUTDIR)/katex) to be shared by all
# HTML targets.
# We currently only need the css and fonts, but copy all of KATEXSRCDIR anyway.
$(KATEXINSTDIR): $(KATEXSRCDIR)
	$(QUIET)$(MKDIR) $(KATEXINSTDIR)
	$(QUIET)$(RMRF)  $(KATEXINSTDIR)
	$(QUIET)$(CP) -rf $(KATEXSRCDIR) $(KATEXINSTDIR)

# Spec targets
# There is some complexity to try and avoid short virtual targets like 'html'
# causing specs to *always* be regenerated.

CHUNKER = $(SCRIPTS)/asciidoctor-chunker/asciidoctor-chunker.js
CHUNKINDEX = $(CONFIGS)/chunkindex
# Only the $(CHUNKER) step is required unless the search index is to be
# generated and incorporated into the chunked spec.
#
# Dropped $(QUIET) for now
# Should set NODE_PATH=/usr/local/lib/node_modules or wherever, outside Makefile
# Copying chunked.js into target avoids a warning from the chunker
chunked: $(HTMLDIR)/vkspec.html $(SPECSRC) $(COMMONDOCS)
	$(QUIET)$(CHUNKINDEX)/addscripts.sh $(HTMLDIR)/vkspec.html $(HTMLDIR)/prechunked.html
	$(QUIET)$(CP) $(CHUNKINDEX)/chunked.css $(CHUNKINDEX)/chunked.js \
	    $(CHUNKINDEX)/lunr.js $(HTMLDIR)
	$(QUIET)$(NODEJS) $(CHUNKER) $(HTMLDIR)/prechunked.html -o $(HTMLDIR)
	$(QUIET)$(RM) $(HTMLDIR)/prechunked.html
	$(QUIET)$(RUBY) $(CHUNKINDEX)/generate-index.rb $(HTMLDIR)/chap*html | \
	    $(NODEJS) $(CHUNKINDEX)/build-index.js > $(HTMLDIR)/search.index.js

# This is a temporary target while the new chunker is pre-release.
# Eventually we will either pull the chunker into CI, or permanently
# store a copy of the short JavaScript chunker in this repository.
CHUNKERVERSION = asciidoctor-chunker_v1.0.0
CHUNKURL = https://github.com/wshito/asciidoctor-chunker/releases/download/v1.0.0/$(CHUNKERVERSION).zip
getchunker:
	wget $(CHUNKURL) -O $(CHUNKERVERSION).zip
	unzip $(CHUNKERVERSION).zip
	mv $(CHUNKERVERSION)/* scripts/asciidoctor-chunker/
	$(RMRF) $(CHUNKERVERSION).zip $(CHUNKERVERSION)

html: $(HTMLDIR)/vkspec.html $(SPECSRC) $(COMMONDOCS)

$(HTMLDIR)/vkspec.html: KATEXDIR = ../katex
$(HTMLDIR)/vkspec.html: $(SPECSRC) $(COMMONDOCS) $(KATEXINSTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ $(SPECSRC)
	$(QUIET)$(TRANSLATEMATH) $@

diff_html: $(HTMLDIR)/diff.html $(SPECSRC) $(COMMONDOCS)

$(HTMLDIR)/diff.html: KATEXDIR = ../katex
$(HTMLDIR)/diff.html: $(SPECSRC) $(COMMONDOCS) $(KATEXINSTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) \
	    -a diff_extensions="$(DIFFEXTENSIONS)" \
	    -r $(CONFIGS)/extension-highlighter.rb --trace \
	    -o $@ $(SPECSRC)
	$(QUIET)$(TRANSLATEMATH) $@

# PDF optimizer - usage $(OPTIMIZEPDF) in.pdf out.pdf
# OPTIMIZEPDFOPTS=--compress-pages is slightly better, but much slower
OPTIMIZEPDF = hexapdf optimize $(OPTIMIZEPDFOPTS)

pdf: $(PDFDIR)/vkspec.pdf $(SPECSRC) $(COMMONDOCS)

$(PDFDIR)/vkspec.pdf: $(SPECSRC) $(COMMONDOCS)
	$(QUIET)$(MKDIR) $(PDFDIR)
	$(QUIET)$(MKDIR) $(PDFMATHDIR)
	$(QUIET)$(ASCIIDOC) -b pdf $(ADOCOPTS) $(ADOCPDFOPTS) -o $@ $(SPECSRC)
	$(QUIET)$(OPTIMIZEPDF) $@ $@.out.pdf && mv $@.out.pdf $@
	$(QUIET)$(RMRF) $(PDFMATHDIR)

validusage: $(VUDIR)/validusage.json $(SPECSRC) $(COMMONDOCS)

$(VUDIR)/validusage.json: $(SPECSRC) $(COMMONDOCS)
	$(QUIET)$(MKDIR) $(VUDIR)
	$(QUIET)$(ASCIIDOC) $(ADOCOPTS) $(ADOCVUOPTS) --trace \
	    -a json_output=$@ -o $@ $(SPECSRC)

# Vulkan Documentation and Extensions, a.k.a. "Style Guide" documentation

STYLESRC = styleguide.adoc
STYLEFILES = $(wildcard $(SPECDIR)/style/[A-Za-z]*.adoc)

styleguide: $(OUTDIR)/styleguide.html

$(OUTDIR)/styleguide.html: KATEXDIR = katex
$(OUTDIR)/styleguide.html: $(STYLESRC) $(STYLEFILES) $(GENDEPENDS) $(KATEXINSTDIR)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ $(STYLESRC)
	$(QUIET)$(TRANSLATEMATH) $@


# Vulkan API Registry (XML Schema) documentation
# Currently does not use latexmath / KaTeX

REGSRC = registry.adoc

registry: $(OUTDIR)/registry.html

$(OUTDIR)/registry.html: KATEXDIR = katex
$(OUTDIR)/registry.html: $(REGSRC) $(GENDEPENDS)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ $(REGSRC)
	$(QUIET)$(TRANSLATEMATH) $@

# Build proposal documents
PROPOSALSOURCES   = $(filter-out $(PROPOSALPATH)/template.adoc, $(wildcard $(PROPOSALPATH)/*.adoc))
PROPOSALDOCS	  = $(PROPOSALSOURCES:$(PROPOSALPATH)/%.adoc=$(PROPOSALDIR)/%.html)
proposals: $(PROPOSALDOCS) $(PROPOSALSOURCES)

# Proposal documents are built outside of the main specification
$(PROPOSALDIR)/%.html: $(PROPOSALPATH)/%.adoc
	$(QUIET)$(ASCIIDOC) --failure-level ERROR -b html5 -o $@ $<
	$(QUIET) if egrep -q '\\[([]' $@ ; then \
	    $(TRANSLATEMATH) $@ ; \
	fi

# Reflow text in spec sources
REFLOW = $(SCRIPTS)/reflow.py
REFLOWOPTS = -overwrite

reflow:
	$(QUIET) echo "Warning: please verify the spec outputs build without changes!"
	$(PYTHON) $(REFLOW) $(REFLOWOPTS) $(SPECSRC) $(SPECFILES) $(STYLESRC) $(STYLEFILES)

# Automated markup and consistency checks, invoked by 'allchecks' and
# 'ci-allchecks' targets or individually.

# Look for disallowed contractions
CHECK_CONTRACTIONS = git grep -i -F -f $(ROOTDIR)/config/CI/contractions | egrep -v -E -f $(ROOTDIR)/config/CI/contractions-allowed
check-contractions:
	if test `$(CHECK_CONTRACTIONS) | wc -l` != 0 ; then \
	    echo "Contractions found that are not allowed:" ; \
	    $(CHECK_CONTRACTIONS) ; \
	    exit 1 ; \
	fi

# Look for typos and suggest fixes
CODESPELL = codespell --config $(ROOTDIR)/config/CI/codespellrc -S '*.js' -S './antora*/*' -S 'ERRS*,*.pdf,*.html'
check-spelling:
	if ! $(CODESPELL) > /dev/null ; then \
	    echo "Found probable misspellings. Corrections can be added to config/CI/codespell-allowed:" ; \
	    $(CODESPELL) ; \
	    exit 1 ; \
	fi

# Look for old or unpreferred language in specification language.
# This mostly helps when we make global changes that also need to be
# made in outstanding extension branches for new text.
CHECK_WRITING = git grep -E -f $(ROOTDIR)/config/CI/writing $(SPECDIR)/registry.adoc $(SPECDIR)/vkspec.adoc $(SPECDIR)/chapters $(SPECDIR)/appendices
check-writing:
	if test `$(CHECK_WRITING) | wc -l` != 0 ; then \
	    echo "Found old style writing. Please refer to the style guide or similar language in current main branch for fixes:" ; \
	    $(CHECK_WRITING) ; \
	    exit 1 ; \
	fi

# Look for bullet list items not preceded by exactly two spaces, per styleguide
CHECK_BULLETS = git grep -E '^( |   +)[-*]+ ' $(SPECDIR)/chapters $(SPECDIR)/appendices $(SPECDIR)/style $(SPECDIR)/[a-z]*.adoc
check-bullets:
	if test `$(CHECK_BULLETS) | wc -l` != 0 ; then \
	    echo "Bullet list item found not preceded by exactly two spaces:" ; \
	    $(CHECK_BULLETS) ; \
	    exit 1 ; \
	fi

# Look for asciidoctor conditionals inside VU statements; and for
# duplicated VUID numbers, but only in spec sources.
check-reflow:
	$(PYTHON) $(SCRIPTS)/reflow.py -nowrite -noflow -check FAIL -checkVUID FAIL $(SPECFILES)

# Look for files whose Khronos copyright has not been updated to the
# current year
DATE_YEAR = $(shell date +%Y)
CHECK_DATES = git grep -z -l 'Copyright.*The Khronos' | xargs -0 git grep -L 'Copyright.*$(DATE_YEAR).*The Khronos'
check-copyright-dates:
	if test `$(CHECK_DATES) | wc -l` != 0 ; then \
	    echo "Files with out-of-date Khronos copyrights (must be updated to $(DATE_YEAR):" ; \
	    $(CHECK_DATES) ; \
	    exit 1 ; \
	 fi

# Look for proper use of custom markup macros
#   --ignore_count 0 can be incremented if there are unfixable errors
check-links:
	$(PYTHON) $(SCRIPTS)/check_spec_links.py -Werror --ignore_count 0

# Perform XML consistency checks
# Use '-warn' option to display warnings as well as errors
check-consistency:
	$(PYTHON) $(SCRIPTS)/xml_consistency.py

# Looks for untagged use of 'undefined' in spec sources
check-undefined:
	$(SCRIPTS)/ci/check_undefined

# Look for '.txt' files, which should almost all be .adoc now
CHECK_TXTFILES = find . -name '*.txt' | egrep -v -E -f $(ROOTDIR)/config/CI/txt-files-allowed
check-txtfiles:
	if test `$(CHECK_TXTFILES) | wc -l` != 0 ; then \
	    echo "*.txt files found that are not allowed (use .adoc):" ; \
	    $(CHECK_TXTFILES) ; \
	    exit 1 ; \
	fi

# Check for valid xrefs in the output html
check-xrefs: $(HTMLDIR)/vkspec.html
	$(SCRIPTS)/check_html_xrefs.py $(HTMLDIR)/vkspec.html

# Clean generated and output files

clean: clean_html clean_pdf clean_man clean_generated clean_validusage

clean_html:
	$(QUIET)$(RMRF) $(HTMLDIR) $(OUTDIR)/katex
	$(QUIET)$(RM) $(OUTDIR)/apispec.html $(OUTDIR)/styleguide.html \
	    $(OUTDIR)/registry.html

clean_pdf:
	$(QUIET)$(RMRF) $(PDFDIR) $(OUTDIR)/apispec.pdf

clean_man:
	$(QUIET)$(RMRF) $(MANHTMLDIR)

# Generated directories and files to remove
CLEAN_GEN_PATHS = \
    $(APIPATH) \
    $(HOSTSYNCPATH) \
    $(VALIDITYPATH) \
    $(METAPATH) \
    $(INTERFACEPATH) \
    $(SPIRVCAPPATH) \
    $(FORMATSPATH) \
    $(SYNCPATH) \
    $(REFPATH) \
    $(GENERATED)/include \
    $(GENERATED)/__pycache__ \
    $(PDFMATHDIR) \
    $(JSAPIMAP) \
    $(PYAPIMAP) \
    $(RBAPIMAP) \
    $(ATTRIBFILE)

clean_generated:
	$(QUIET)$(RMRF) $(CLEAN_GEN_PATHS)

clean_validusage:
	$(QUIET)$(RM) $(VUDIR)/validusage.json


# Generated refpage sources. For now, always build all refpages.
MANSOURCES   = $(filter-out $(REFPATH)/apispec.adoc, $(wildcard $(REFPATH)/*.adoc))

# Generation of refpage asciidoctor sources by extraction from the
# specification(s).
#
# Should have a proper dependency causing the man page sources to be
# generated by running genRef (once), but adding $(MANSOURCES) to the
# targets causes genRef to run once/target.
#
# Should pass in $(EXTOPTIONS) to determine which pages to generate.
# For now, all core and extension refpages are extracted by genRef.py.
GENREF = $(SCRIPTS)/genRef.py
LOGFILE = $(REFPATH)/refpage.log
refpages: $(REFPATH)/apispec.adoc
$(REFPATH)/apispec.adoc: $(SPECFILES) $(GENREF) $(SCRIPTS)/reflib.py $(PYAPIMAP)
	$(QUIET)$(MKDIR) $(REFPATH)
	$(PYTHON) $(GENREF) -genpath $(GENERATED) -basedir $(REFPATH) \
	    -log $(LOGFILE) -extpath $(SPECDIR)/appendices \
	    $(EXTOPTIONS) $(SPECFILES)

# These targets are HTML5 refpages
#
# The recursive $(MAKE) is an apparently unavoidable hack, since the
# actual list of man page sources is not known until after
# $(REFPATH)/apispec.adoc is generated. $(GENDEPENDS) is generated before
# running the recursive make, so it does not trigger twice
# $(SUBMAKEOPTIONS) suppresses the redundant "Entering / leaving"
# messages make normally prints out, similarly to suppressing make
# command output logging in the individual refpage actions below.
SUBMAKEOPTIONS = --no-print-directory
manhtmlpages: $(REFPATH)/apispec.adoc $(GENDEPENDS)
	$(QUIET) echo "manhtmlpages: building HTML refpages with these options:"
	$(QUIET) echo $(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) \
	    $(ADOCREFOPTS) -d manpage -o REFPAGE.html REFPAGE.adoc
	$(MAKE) $(SUBMAKEOPTIONS) -e buildmanpages

# Build the individual refpages, then the symbolic links from aliases
MANHTMLDIR  = $(OUTDIR)/man/html
MANHTML     = $(MANSOURCES:$(REFPATH)/%.adoc=$(MANHTMLDIR)/%.html)
buildmanpages: $(MANHTML)
	$(MAKE) $(SUBMAKEOPTIONS) -e manaliases

# Asciidoctor options to build refpages
#
# ADOCREFOPTS *must* be placed after ADOCOPTS in the command line, so
# that it can override spec attribute values.
#
# cross-file-links makes custom macros link to other refpages
# refprefix includes the refpage (not spec) extension metadata.
# isrefpage is for refpage-specific content
# html_spec_relative is where to find the full specification
ADOCREFOPTS = -a cross-file-links -a refprefix='refpage.' -a isrefpage \
	      -a html_spec_relative='../../html/vkspec.html'

# The refpage build process normally generates far too much output, so
# use VERYQUIET instead of QUIET
# Running translate_math.js on every refpage is slow and most of them
# do not contain math, so do a quick search for latexmath delimiters.
$(MANHTMLDIR)/%.html: KATEXDIR = ../../katex
$(MANHTMLDIR)/%.html: $(REFPATH)/%.adoc $(GENDEPENDS) $(KATEXINSTDIR)
	$(VERYQUIET)echo "Building $@ from $< using default options"
	$(VERYQUIET)$(MKDIR) $(MANHTMLDIR)
	$(VERYQUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) $(ADOCREFOPTS) \
	    -d manpage -o $@ $<
	$(VERYQUIET)if egrep -q '\\[([]' $@ ; then \
	    $(TRANSLATEMATH) $@ ; \
	fi

# The 'manhtml' and 'manpdf' targets are NO LONGER SUPPORTED by Khronos.
# They generate HTML5 and PDF single-file versions of the refpages.
# The generated refpage sources are included by $(REFPATH)/apispec.adoc,
# and are always generated along with that file. Therefore there is no
# need for a recursive $(MAKE) or a $(MANHTML) dependency, unlike the
# manhtmlpages target.

manpdf: $(OUTDIR)/apispec.pdf

$(OUTDIR)/apispec.pdf: $(SPECVERSION) $(REFPATH)/apispec.adoc $(SVGFILES) $(GENDEPENDS)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(MKDIR) $(PDFMATHDIR)
	$(QUIET)$(ASCIIDOC) -b pdf -a html_spec_relative='html/vkspec.html' \
	    $(ADOCOPTS) $(ADOCPDFOPTS) -o $@ $(REFPATH)/apispec.adoc
	$(QUIET)$(OPTIMIZEPDF) $@ $@.out.pdf && mv $@.out.pdf $@

manhtml: $(OUTDIR)/apispec.html

$(OUTDIR)/apispec.html: KATEXDIR = katex
$(OUTDIR)/apispec.html: ADOCMISCOPTS =
$(OUTDIR)/apispec.html: $(SPECVERSION) $(REFPATH)/apispec.adoc $(SVGFILES) $(GENDEPENDS) $(KATEXINSTDIR)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 -a html_spec_relative='html/vkspec.html' \
	    $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ $(REFPATH)/apispec.adoc
	$(QUIET)$(TRANSLATEMATH) $@

# Create links for refpage aliases

MAKEMANALIASES = $(SCRIPTS)/makemanaliases.py
manaliases: $(PYAPIMAP)
	$(PYTHON) $(MAKEMANALIASES) -genpath $(GENERATED) -refdir $(MANHTMLDIR)

# Targets generated from the XML and registry processing scripts
#   $(PYAPIMAP) (apimap.py) - Python encoding of the registry
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

REGISTRY   = $(ROOTDIR)/xml
VKXML	   = $(REGISTRY)/vk.xml
GENVK	   = $(SCRIPTS)/genvk.py
GENVKOPTS  = $(VERSIONOPTIONS) $(EXTOPTIONS) $(GENVKEXTRA) -registry $(VKXML)
GENVKEXTRA =

scriptapi: jsapi pyapi rubyapi

jsapi $(JSAPIMAP): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(GENERATED)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(GENERATED) apimap.cjs

pyapi $(PYAPIMAP): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(GENERATED)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(GENERATED) apimap.py

rubyapi $(RBAPIMAP): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(GENERATED)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(GENERATED) apimap.rb

apiinc: $(APIDEPEND)

$(APIDEPEND): $(VKXML) $(GENVK) $(PYAPIMAP)
	$(QUIET)$(MKDIR) $(APIPATH)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(APIPATH) -genpath $(GENERATED) apiinc

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

interfaceinc: $(INTERFACEPATH)/timeMarker

$(INTERFACEDEPEND): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(INTERFACEPATH)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(INTERFACEPATH) interfaceinc

# This generates a single file, so SPIRVCAPDEPEND is the full path to
# the file, rather than to a timeMarker in the same directory.
spirvcapinc: $(SPIRVCAPDEPEND)

$(SPIRVCAPDEPEND): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(SPIRVCAPPATH)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(SPIRVCAPPATH) spirvcapinc

# This generates a single file, so FORMATSDEPEND is the full path to
# the file, rather than to a timeMarker in the same directory.
formatsinc: $(FORMATSDEPEND)

$(FORMATSDEPEND): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(FORMATSPATH)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(FORMATSPATH) formatsinc

# This generates a single file, so FORMATSDEPEND is the full path to
# the file, rather than to a timeMarker in the same directory.
syncinc: $(SYNCDEPEND)

$(SYNCDEPEND): $(VKXML) $(GENVK)
	$(QUIET)$(MKDIR) $(SYNCPATH)
	$(QUIET)$(PYTHON) $(GENVK) $(GENVKOPTS) -o $(SYNCPATH) syncinc

# This generates a single file containing asciidoc attributes for each
# core version and extension in the spec being built.
# For use with Antora, it also includes a couple of document attributes
# otherwise passed on the asciidoctor command line.
# These should not use the asciidoctor attribute names (e.g. revnumber,
# revdate), so use the Makefile variable names instead (e.g.
# SPECREVISION, SPECDATE).

attribs: $(ATTRIBFILE)

$(ATTRIBFILE):
	$(QUIET)for attrib in $(VERSIONS) $(EXTS) ; do \
	    echo ":$${attrib}:" ; \
	done > $@
	$(QUIET)(echo ":SPECREVISION: $(SPECREVISION)" ; \
		 echo ":SPECDATE: $(SPECDATE)" ; \
		 echo ":SPECREMARK: $(SPECREMARK)" ; \
		 echo ":APITITLE: $(APITITLE)") >> $@

# Debugging aid - generate all files from registry XML
generated: $(PYAPIMAP) $(GENDEPENDS)
