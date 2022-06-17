# Copyright 2013-2022 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# If a recipe fails, delete its target file. Without this cleanup, the leftover
# file from the failed recipe can falsely satisfy dependencies on subsequent
# runs of `make`.
.DELETE_ON_ERROR:

QUIET	 ?= @
MKDIR	 = mkdir -p
CP	 = cp
RM	 = rm -f
RMRF	 = rm -rf

# Generator scripts and options
# GENOPTS can be e.g. '-noprotect'

PYTHON ?= python3
SCRIPTS = ../scripts
GENOPTS =

# Generate Vulkan headers from XML. Many other files can be generated
# from vk.xml using the scripts, but they are all generated from
# ../Makefile as part of the process of building the Specification.
#
# Targets:
#
# default / install - regenerate headers in ../include/vulkan/.
# validate - run XML validator on vk.xml against the schema.
# test - check if vulkan_core.h compiles.
# clean_dirt - remove intermediate files.
# clean - remove installed and intermediate files.

GENERATED   = ../gen
INCLUDE     = $(GENERATED)/include
TESTS	    = ../tests
VULKAN	    = $(INCLUDE)/vulkan
SRC	    = ../src

# Static files needed for a complete set of headers, cached in the
# repository
STATIC_HEADERS = $(VULKAN)/vulkan.h $(VULKAN)/vk_platform.h
# Where static headers are stored
STATIC				 = ../include/vulkan

# Vulkan platform-specific headers
PLATFORM_HEADERS = \
    $(VULKAN)/vulkan_android.h \
    $(VULKAN)/vulkan_fuchsia.h \
    $(VULKAN)/vulkan_ggp.h \
    $(VULKAN)/vulkan_ios.h \
    $(VULKAN)/vulkan_macos.h \
    $(VULKAN)/vulkan_vi.h \
    $(VULKAN)/vulkan_wayland.h \
    $(VULKAN)/vulkan_win32.h \
    $(VULKAN)/vulkan_xcb.h \
    $(VULKAN)/vulkan_xlib.h \
    $(VULKAN)/vulkan_directfb.h \
    $(VULKAN)/vulkan_xlib_xrandr.h \
    $(VULKAN)/vulkan_metal.h \
    $(VULKAN)/vulkan_screen.h \
    $(VULKAN)/vulkan_beta.h
HEADERS     = $(VULKAN)/vulkan_core.h $(PLATFORM_HEADERS)

default: install

################################################

# Autogenerate vulkan header from XML API description

# Python and XML files on which vulkan_core.h depends
GENSCRIPT   = $(SCRIPTS)/genvk.py
VKXML	    = vk.xml
VKH_DEPENDS = $(VKXML) $(GENSCRIPT) $(SCRIPTS)/reg.py $(SCRIPTS)/generator.py

$(HEADERS): $(VKH_DEPENDS)
	$(MKDIR) $(VULKAN)
	$(PYTHON) $(GENSCRIPT) $(GENOPTS) -registry $(VKXML) \
	    -o $(VULKAN) $(notdir $@)

platform: $(PLATFORM_HEADERS)

# Autogenerate video codec headers from XML

VIDEO_INCLUDE = $(INCLUDE)/vk_video
CODECS = vulkan_video_codecs_common.h \
	 vulkan_video_codec_h264std.h \
	 vulkan_video_codec_h264std_decode.h \
	 vulkan_video_codec_h264std_encode.h \
	 vulkan_video_codec_h265std.h \
	 vulkan_video_codec_h265std_decode.h \
	 vulkan_video_codec_h265std_encode.h
CODEC_HEADERS = $(CODECS:%=$(VIDEO_INCLUDE)/%)
CODECXML = video.xml

codec_headers: $(CODEC_HEADERS)

$(VIDEO_INCLUDE)/%.h: $(CODECXML) $(GENSCRIPT) $(SCRIPTS)/reg.py $(SCRIPTS)/generator.py
	$(QUIET)$(MKDIR) $(VIDEO_INCLUDE)
	$(QUIET)$(PYTHON) $(GENSCRIPT) $(GENOPTS) -registry $(CODECXML) -o $(VIDEO_INCLUDE) $(notdir $@)

# Verify registry XML files against the schema
validate:
	jing -c registry.rnc $(VKXML)
	$(PYTHON) $(GENSCRIPT) -validate -registry $(VKXML)
	jing -c registry.rnc $(CODECXML)

# Test that generated Vulkan headers compile

# Platforms to test
TESTDEFS = -DVK_USE_PLATFORM_XCB_KHR -DVK_USE_PLATFORM_XLIB_KHR

test: $(HEADERS) $(STATIC_HEADERS) $(CODEC_HEADERS)
	gcc -Wall -std=c99 -c -I$(INCLUDE) -I$(TESTS) $(TESTS)/htest.c
	gcc -Wall -std=c11 -c -I$(INCLUDE) -I$(TESTS) $(TESTS)/htest.c
	g++ -Wall -c -std=c++98 -I$(INCLUDE) -I$(TESTS) $(TESTS)/htest.c
	g++ -Wall -c -std=c++11 -I$(INCLUDE) -I$(TESTS) $(TESTS)/htest.c
	$(RM) htest.o

# Test that generated video codec headers compile

vtest: $(CODEC_HEADERS)
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c
	$(RM) vtest.o

################################################

install: $(HEADERS) $(STATIC_HEADERS) $(CODEC_HEADERS)

$(VULKAN)/vulkan.h: $(STATIC)/vulkan.h
	$(QUIET)$(MKDIR) $(VULKAN)
	$(CP) $? $@

$(VULKAN)/vk_platform.h: $(STATIC)/vk_platform.h
	$(QUIET)$(MKDIR) $(VULKAN)
	$(CP) $? $@

################################################

# Files to clean up
PYDIRT = diag.txt dumpReg.txt errwarn.txt *.pyc regdump.txt
DIRT = $(PYDIRT) ERRS *.o $(wildcard #*)

# Clean intermediate files
clean_dirt:
	-$(RM) $(DIRT)

# Clean generated targets and intermediates
clean clobber: clean_dirt
	-$(RMRF) $(INCLUDE) $(VIDEO_INCLUDE)
