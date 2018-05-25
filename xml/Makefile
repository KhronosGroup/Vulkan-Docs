# Copyright (c) 2013-2018 The Khronos Group Inc.
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

# If a recipe fails, delete its target file. Without this cleanup, the leftover
# file from the failed recipe can falsely satisfy dependencies on subsequent
# runs of `make`.
.DELETE_ON_ERROR:

# Generator scripts and options
# GENOPTS can be e.g. '-noprotect'

PYTHON ?= python3
PYFILES = genheaders.py reg.py
GENOPTS =

# Generate Vulkan header from XML. Many other files can be generated
# from vk.xml using the scripts, but they are all generated in ../ as
# part of the process of building the Specification.
#
# Targets:
#
# default / install - regenerate headers in ../include/vulkan/.
# validate - run XML validator on vk.xml against the schema.
# test - check if vulkan_core.h compiles.
# clean_dirt - remove intermediate files.
# clean - remove installed and intermediate files.

INCLUDE     = ../include
VULKAN	    = $(INCLUDE)/vulkan
SRC	    = ../src

# Vulkan platform-specific headers
PLATFORM_HEADERS = \
    $(VULKAN)/vulkan_android.h \
    $(VULKAN)/vulkan_ios.h \
    $(VULKAN)/vulkan_macos.h \
    $(VULKAN)/vulkan_mir.h \
    $(VULKAN)/vulkan_vi.h \
    $(VULKAN)/vulkan_wayland.h \
    $(VULKAN)/vulkan_win32.h \
    $(VULKAN)/vulkan_xcb.h \
    $(VULKAN)/vulkan_xlib.h \
    $(VULKAN)/vulkan_xlib_xrandr.h
HEADERS     = $(VULKAN)/vulkan_core.h $(PLATFORM_HEADERS)

default install: $(HEADERS)

################################################

# Autogenerate vulkan header from XML API description

# Python and XML files on which vulkan_core.h depends
VKH_DEPENDS = vk.xml genvk.py reg.py generator.py

$(HEADERS): $(VKH_DEPENDS)
	$(PYTHON) genvk.py -registry vk.xml -o $(VULKAN) $(notdir $@)

platform: $(PLATFORM_HEADERS)

# Verify registry XML file against the schema
validate:
	jing -c registry.rnc vk.xml

# Test that vulkan_core.h compiles

# Platforms to test
TESTDEFS = -DVK_USE_PLATFORM_XCB_KHR -DVK_USE_PLATFORM_XLIB_KHR

test: $(HEADERS) $(VULKAN)/vulkan.h $(VULKAN)/vk_platform.h
	gcc -Wall -pedantic -std=c99 -c -I$(INCLUDE) test.c
	g++ -Wall -c -std=c++98 -I$(INCLUDE) test.c
	g++ -Wall -c -std=c++11 -I$(INCLUDE) test.c
	gcc $(TESTDEFS) -Wall -pedantic -std=c99 -c -I$(INCLUDE) test.c
	rm test.o

################################################

# Autogenerate extension loader from XML API description
# Also generates $(EXTLOADER)/vulkan_ext.h
# No longer supported.

EXTLOADER   = $(SRC)/ext_loader
EXTSRCS     = $(EXTLOADER)/vulkan_ext.c
extloader $(EXTSRCS): $(VKH_DEPENDS)
	$(PYTHON) genvk.py -registry vk.xml -o $(EXTLOADER) vulkan_ext.c

################################################

# Files to clean up
PYDIRT = diag.txt dumpReg.txt errwarn.txt *.pyc regdump.txt
DIRT = $(PYDIRT) ERRS \#*

# Clean intermediate files
clean_dirt:
	-rm -f $(DIRT)

# Clean generated targets as well as intermediates.
clean clobber: clean_dirt
	-rm -f $(HEADERS) $(PLATFORM_HEADERS)
