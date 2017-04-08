# Copyright (c) 2014-2017 The Khronos Group Inc.
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
#  html - HTML single-page API specification
#  pdf - PDF single-page API specification
#  styleguide - HTML5 single-page "Documentation and Extensions" guide
#  registry - HTML5 single-page XML Registry Schema documentation
#  manhtml - HTML5 single-page reference guide
#  manpdf - PDF reference guide
#  manhtmlpages - HTML5 separate per-feature reference pages
#  checkinc - validator script for asciidoc include files
#  checklinks - validator script for asciidoc xrefs

all: alldocs allchecks

alldocs: allspecs allman

allspecs: html pdf styleguide registry

allman: manhtml manpdf manhtmlpages

allchecks: checkinc checklinks

# Note that the := assignments below are immediate, not deferred, and
# are therefore order-dependent in the Makefile

QUIET	 ?= @
PYTHON	 ?= python3
ASCIIDOC ?= asciidoctor
RM	 = rm -f
RMRF	 = rm -rf
MKDIR	 = mkdir -p
CP	 = cp
ECHO	 = echo
GS_EXISTS := $(shell command -v gs 2> /dev/null)

# Target directories for output files
# HTMLDIR - 'html' target
# PDFDIR - 'pdf' target
# CHECKDIR - 'allchecks' target
OUTDIR	  := $(CURDIR)/../../../out/1.0
HTMLDIR   := $(OUTDIR)/html
PDFDIR	  := $(OUTDIR)/pdf
CHECKDIR  := $(OUTDIR)/checks

# PDF Equations are written to SVGs, this dictates the location to store those files (temporary)
PDFMATHDIR:=$(OUTDIR)/equations_temp

# Set VERBOSE to -v to see what asciidoc is doing.
VERBOSE =

# asciidoc attributes to set.
# NOTEOPTS   sets options controlling which NOTEs are generated
# ATTRIBOPTS sets the api revision and enables MathJax generation
# EXTATTRIBS sets attributes for enabled extensions (set above based on
#	     $(EXTENSIONS))
# ADOCOPTS   options for asciidoc->HTML5 output
NOTEOPTS     = -a editing-notes -a implementation-guide
SPECREVISION = 1.0.47
# Spell out RFC2822 format as not all date commands support -R
SPECDATE     = $(shell echo `date -u "+%a, %d %b %Y %T %z"`)

# Generate Asciidoc attributes for spec remark
GITHEAD := ../../../.git/logs/HEAD
ifeq ($(wildcard $(GITHEAD)),)
# If GITHEAD does not exist, don't include branch info.
SPECREMARK = Git branch information not available
else
# Could use `git log -1 --format="%cd"` to get branch commit date
# This used to be a dependency in the spec html/pdf targets,
# but that's likely to lead to merge conflicts. Just regenerate
# when pushing a new spec for review to the sandbox.
# The dependency on HEAD is per the suggestion in
# http://neugierig.org/software/blog/2014/11/binary-revisions.html
SPECREMARK = from git branch: $(shell echo `git symbolic-ref --short HEAD`) \
	     commit: $(shell echo `git log -1 --format="%H"`)
endif

ATTRIBOPTS   = -a revnumber="$(SPECREVISION)" \
	       -a revdate="$(SPECDATE)" \
	       -a revremark="$(SPECREMARK)" \
	       -a apititle="$(APITITLE)" \
	       -a stem=latexmath \
	       $(EXTATTRIBS)

ADOCEXTS     = -r $(CURDIR)/config/vulkan-macros.rb
ADOCOPTS     = -d book $(ATTRIBOPTS) $(NOTEOPTS) $(VERBOSE) $(ADOCEXTS)

ADOCHTMLEXTS = -r $(CURDIR)/config/katex_replace.rb

# ADOCHTMLOPTS relies on the relative KATEXDIR path being set correctly
# for each target using the variable.
KATEXDIR     = katex
ADOCHTMLOPTS = $(ADOCHTMLEXTS) -a katexpath=$(KATEXDIR)

ADOCPDFEXTS  = -r asciidoctor-pdf -r asciidoctor-mathematical
ADOCPDFOPTS  = $(ADOCPDFEXTS) -a mathematical-format=svg \
	       -a imagesoutdir=$(PDFMATHDIR)

.PHONY: directories

# Images used by the spec. These are included in generated HTML now.
IMAGEPATH :=images
SVGFILES  := $(wildcard $(IMAGEPATH)/*.svg)

# Top-level spec source file
SPECSRC := vkspec.txt
# Files making up sections of the API spec. The wildcard expression
# should work in extension branches to pull in those files as well.
SPECFILES = $(wildcard chapters/[A-Za-z]*.txt appendices/[A-Za-z]*.txt chapters/*/[A-Za-z]*.txt appendices/*/[A-Za-z]*.txt)
GENINCLUDE = $(wildcard api/*/[A-Za-z]*.txt validity/*/[A-Za-z]*.txt hostsynctable/*.txt)
GENDEPENDS = api/timeMarker validity/timeMarker hostsynctable/timeMarker
# All non-format-specific dependencies
COMMONDOCS = $(SPECFILES) $(GENINCLUDE) $(GENDEPENDS)

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
html: $(HTMLDIR)/vkspec.html $(SPECSRC) $(COMMONDOCS)

$(HTMLDIR)/vkspec.html: KATEXDIR = ../katex
$(HTMLDIR)/vkspec.html: $(SPECSRC) $(COMMONDOCS) katexinst
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ $(SPECSRC)

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


# Vulkan Documentation and Extensions, a.k.a. "Style Guide" documentation

STYLESRC = styleguide.txt
STYLEFILES = $(wildcard style/[A-Za-z]*.txt)

styleguide: $(OUTDIR)/styleguide.html

$(OUTDIR)/styleguide.html: KATEXDIR = katex
$(OUTDIR)/styleguide.html: $(STYLESRC) $(STYLEFILES) $(GENINCLUDE) $(GENDEPENDS) katexinst
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
REFLOW = reflow.py
REFLOWOPTS = -overwrite

reflow:
	$(QUIET) echo "Warning: please verify the spec outputs build without changes!"
	$(PYTHON) $(REFLOW) $(REFLOWOPTS) $(SPECSRC) $(SPECFILES) $(STYLESRC) $(STYLEFILES)

# Clean generated and output files

clean: clean_html clean_pdf clean_man clean_checks clean_generated

clean_html:
	$(QUIET)$(RMRF) $(HTMLDIR) $(OUTDIR)/katex
	$(QUIET)$(RM) $(OUTDIR)/apispec.html $(OUTDIR)/styleguide.html \
	    $(OUTDIR)/registry.html

clean_pdf:
	$(QUIET)$(RM) $(PDFDIR)/vkspec.pdf $(OUTDIR)/apispec.pdf

clean_man:
	$(QUIET)$(RMRF) $(MANHTMLDIR)

clean_checks:
	$(QUIET)$(RMRF) $(CHECKDIR)

clean_generated:
	$(QUIET)$(RMRF) api/* hostsynctable/* validity/* vkapi.py
	$(QUIET)$(RM) man/apispec.txt man/[Vv][Kk]*.txt man/PFN*.txt
	$(QUIET)$(RMRF) $(PDFMATHDIR)


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
CORESOURCES  = $(filter-out $(KHRSOURCES) $(VENSOURCES),$(wildcard $(MANDIR)/[Vv][Kk]*.txt $(MANDIR)/PFN*.txt))
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
man/apispec.txt: $(SPECFILES) genRef.py reflib.py vkapi.py
	$(PYTHON) genRef.py $(SPECFILES)

# These dependencies don't take into account include directives

# These targets are HTML5 ref pages

MANHTMLDIR  := $(OUTDIR)/man/html
MANHTML     = $(MANSOURCES:$(MANDIR)/%.txt=$(MANHTMLDIR)/%.html)

manhtmlpages: man/apispec.txt $(MANHTML)

$(MANHTMLDIR)/%.html: KATEXDIR = ../../katex
$(MANHTMLDIR)/%.html: $(MANDIR)/%.txt $(MANCOPYRIGHT) $(GENINCLUDE) $(GENDEPENDS) katexinst
	$(QUIET)$(MKDIR) $(MANHTMLDIR)
	$(QUIET)$(ASCIIDOC) -b html5 -a cross-file-links $(ADOCOPTS) $(ADOCHTMLOPTS) -d manpage -o $@ $<

# These targets are HTML5 and PDF single-file versions of the ref pages

manpdf: $(OUTDIR)/apispec.pdf

$(OUTDIR)/apispec.pdf: $(SPECVERSION) man/apispec.txt $(MANSOURCES) $(MANCOPYRIGHT) $(SVGFILES) $(GENINCLUDE) $(GENDEPENDS)
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(MKDIR) $(PDFMATHDIR)
	$(QUIET)$(ASCIIDOC) -b pdf $(ADOCOPTS) $(ADOCPDFOPTS) -o $@ man/apispec.txt
ifndef GS_EXISTS
	$(QUIET) echo "Warning: Ghostscript not installed, skipping pdf optimization"
else
	$(QUIET)$(CURDIR)/config/optimize-pdf $@
	$(QUIET)rm $@
	$(QUIET)mv $(OUTDIR)/apispec-optimized.pdf $@
endif

manhtml: $(OUTDIR)/apispec.html

$(OUTDIR)/apispec.html: KATEXDIR = katex
$(OUTDIR)/apispec.html: $(SPECVERSION) man/apispec.txt $(MANSOURCES) $(MANCOPYRIGHT) $(SVGFILES) $(GENINCLUDE) $(GENDEPENDS) katexinst
	$(QUIET)$(MKDIR) $(OUTDIR)
	$(QUIET)$(ASCIIDOC) -b html5 $(ADOCOPTS) $(ADOCHTMLOPTS) -o $@ man/apispec.txt

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
	$(QUIET)cat $(SPECFILES) | \
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
	$(QUIET)$(PYTHON) checkLinks.py -follow $(SPECFILES) > $(CHECKDIR)/specErrs.txt

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
# This leaves out config/extDependency.sh intentionally as it only
# needs to be updated when the extension dependencies in vk.xml change,
# and requires networkx, a non-standard Python package.

generated: vkapi.py api/timeMarker hostsynctable/timeMarker validity/timeMarker

# Extension dependencies derived from vk.xml
# Both Bash and Python versions are generated

DEPSCRIPT = $(REGISTRY)/extDependency.py
config/extDependency.sh: $(VKXML) $(DEPSCRIPT)
	$(PYTHON) $(DEPSCRIPT) -registry $(VKXML) \
	    -outscript config/extDependency.sh \
	    -outpy config/extDependency.py
