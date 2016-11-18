# Copyright (c) 2013-2016 The Khronos Group Inc.
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

# Generator scripts and options
# GENOPTS can be e.g. '-noprotect'

PYTHON ?= python3
PYFILES = genheaders.py reg.py
GENOPTS =
OUTDIR	= ../../out/1.0

# Generate Vulkan header from XML. Many other files can be generated
# from vk.xml using the scripts, but they are all generated in
# ../../doc/specs/vulkan/ as part of the process of building the
# Specification.
#
# Targets:
#
# default / install - regenerate ../vulkan/vulkan.h .
# validate - run XML validator on vk.xml against the schema.
# test - check if vulkan.h compiles.
# doc_install - generate schema / HOWTO readme documentation in
#   $(OUTDIR)/registry.html . Usually done only by the registry
#   maintainer when updating these docs.
# clean_dirt - remove intermediate files.
# clean - remove installed and intermediate files.

VULKAN	    = ../vulkan
HEADERS     = $(VULKAN)/vulkan.h
EXTLOADER   = ../ext_loader
EXTSRCS     = $(EXTLOADER)/vulkan_ext.c

default install: $(HEADERS) $(EXTSRCS)

doc_install: $(OUTDIR)/registry.html

################################################

# Autogenerate vulkan header from XML API description

# Python and XML files on which vulkan.h depends
VKH_DEPENDS = vk.xml genvk.py reg.py generator.py

$(VULKAN)/vulkan.h: $(VKH_DEPENDS)
	$(PYTHON) genvk.py -registry vk.xml -o $(VULKAN) vulkan.h

# Verify registry XML file against the schema
validate:
	jing -c registry.rnc vk.xml

# Test that vulkan.h compiles
test: $(VULKAN)/vulkan.h $(VULKAN)/vk_platform.h
	gcc -Wall -pedantic -std=c99 -c -I.. test.c
	g++ -Wall -c -std=c++98 -I.. test.c
	g++ -Wall -c -std=c++11 -I.. test.c
	rm test.o

################################################

# Autogenerate extension loader from XML API description
# This also generates $(EXTLOADER)/vulkan_ext.h

#$(EXTLOADER)/vulkan_ext.c: $(VKH_DEPENDS)
$(EXTSRCS): $(VKH_DEPENDS)
	$(PYTHON) genvk.py -registry vk.xml -o $(EXTLOADER) vulkan_ext.c

################################################

# Documentation targets
ASCIIDOC = asciidoc
SPECDIR = ../../doc/specs/vulkan
SPECVERSION = $(SPECDIR)/specversion.txt

$(OUTDIR)/registry.html: registry.txt registry.conf Makefile $(SPECVERSION)
	mkdir -p $(OUTDIR)
	$(ASCIIDOC) -b html5 -f registry.conf -o $@ registry.txt

$(SPECVERSION):
	$(MAKE) -C $(SPECDIR) specversion.txt

################################################

# Administrative stuff

# Add entries from function_properties.xls (encoded into a Python
# dictionary) to vk.xml

addProps:
	$(PYTHON) rewrite.py vk.xml | $(PYTHON) realign.py > new.xml

################################################

# Files to clean up
PYDIRT = diag.txt dumpReg.txt errwarn.txt *.pyc regdump.txt
DIRT = $(PYDIRT) ERRS \#*

# Clean intermediate files
clean_dirt:
	-rm -f $(DIRT)

# Clean generated targets as well as intermediates.
clean clobber: clean_dirt
	-rm -f $(HEADERS) $(EXTSRCS) $(OUTDIR)/registry.html
