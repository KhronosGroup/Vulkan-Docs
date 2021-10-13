# Copyright 2013-2021 The Khronos Group Inc.
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
VULKAN_VIDEO_CODECS_STD_H = $(INCLUDE)/vk_video

# Static files needed for a complete set of headers, cached in the
# repository
STATIC_HEADERS = $(VULKAN)/vulkan.h $(VULKAN)/vk_platform.h \
                 $(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codecs_common.h \
                 $(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h264std.h \
                 $(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h264std_decode.h \
                 $(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h264std_encode.h \
                 $(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h265std.h \
                 $(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h265std_decode.h \
                 $(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h265std_encode.h
# Where static headers are stored
STATIC	                         = ../include/vulkan
STATIC_VULKAN_VIDEO_CODECS_STD_H = ../include/vk_video

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

default install: $(HEADERS) $(STATIC_HEADERS)

$(VULKAN)/vulkan.h: $(STATIC)/vulkan.h
	$(QUIET)$(MKDIR) $(VULKAN)
	$(CP) $? $@

$(VULKAN)/vk_platform.h: $(STATIC)/vk_platform.h
	$(QUIET)$(MKDIR) $(VULKAN)
	$(CP) $? $@

$(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codecs_common.h: $(STATIC_VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codecs_common.h
	$(QUIET)$(MKDIR) $(VULKAN_VIDEO_CODECS_STD_H)
	$(CP) $? $@

$(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h264std.h: $(STATIC_VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h264std.h
	$(QUIET)$(MKDIR) $(VULKAN_VIDEO_CODECS_STD_H)
	$(CP) $? $@

$(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h264std_decode.h: $(STATIC_VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h264std_decode.h
	$(QUIET)$(MKDIR) $(VULKAN_VIDEO_CODECS_STD_H)
	$(CP) $? $@

$(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h264std_encode.h: $(STATIC_VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h264std_encode.h
	$(QUIET)$(MKDIR) $(VULKAN_VIDEO_CODECS_STD_H)
	$(CP) $? $@

$(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h265std.h: $(STATIC_VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h265std.h
	$(QUIET)$(MKDIR) $(VULKAN_VIDEO_CODECS_STD_H)
	$(CP) $? $@

$(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h265std_decode.h: $(STATIC_VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h265std_decode.h
	$(QUIET)$(MKDIR) $(VULKAN_VIDEO_CODECS_STD_H)
	$(CP) $? $@

$(VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h265std_encode.h: $(STATIC_VULKAN_VIDEO_CODECS_STD_H)/vulkan_video_codec_h265std_encode.h
	$(QUIET)$(MKDIR) $(VULKAN_VIDEO_CODECS_STD_H)
	$(CP) $? $@

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

# Verify registry XML file against the schema
validate:
	jing -c registry.rnc $(VKXML)
	$(PYTHON) $(GENSCRIPT) -validate -registry $(VKXML)

# Test that vulkan_core.h compiles

# Platforms to test
TESTDEFS = -DVK_USE_PLATFORM_XCB_KHR -DVK_USE_PLATFORM_XLIB_KHR

test: $(HEADERS) $(STATIC_HEADERS)
	gcc -Wall -std=c99 -c -I$(INCLUDE) -I$(TESTS) $(TESTS)/htest.c
	gcc -Wall -std=c11 -c -I$(INCLUDE) -I$(TESTS) $(TESTS)/htest.c
	g++ -Wall -c -std=c++98 -I$(INCLUDE) -I$(TESTS) $(TESTS)/htest.c
	g++ -Wall -c -std=c++11 -I$(INCLUDE) -I$(TESTS) $(TESTS)/htest.c
	$(RM) $(TESTS)/test.o

################################################

# Files to clean up
PYDIRT = diag.txt dumpReg.txt errwarn.txt *.pyc regdump.txt
DIRT = $(PYDIRT) ERRS \#*

# Clean intermediate files
clean_dirt:
	-$(RM) $(DIRT)

# Clean generated targets and intermediates
clean clobber: clean_dirt
	-$(RMRF) $(INCLUDE)
