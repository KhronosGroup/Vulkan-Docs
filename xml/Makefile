# Copyright 2013-2023 The Khronos Group Inc.
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
XML_CONSISTENCY = $(SCRIPTS)/xml_consistency.py
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
JSON	    = $(GENERATED)/out/json
SRC	    = ../src

VULKAN_API ?= vulkan
ifeq ($(VULKAN_API),vulkan)
API_SUFFIX :=
MISRACOPTS ?=
MISRACPPOPTS ?=
else
API_SUFFIX := _sc
# default options for generating MISRA C or MISRA C++ headers
# can be overridden from commandline
MISRACOPTS ?= -misracstyle
MISRACPPOPTS ?= -misracppstyle
endif

# Static files needed for a complete set of headers, cached in the
# repository
STATIC_HEADERS = $(VULKAN)/vulkan$(API_SUFFIX).h $(VULKAN)/vk_platform.h

# Where static headers are stored
STATIC				 = ../include/vulkan
STATIC_JSON_SRC			 = ../json

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

#@ vulkan_sci.h is Vulkan SC-specific
ifeq ($(VULKAN_API),vulkansc)
PLATFORM_HEADERS := $(PLATFORM_HEADERS) $(VULKAN)/vulkan_sci.h
endif

HEADERS_H = $(VULKAN)/vulkan$(API_SUFFIX)_core.h $(PLATFORM_HEADERS)
ifeq ($(VULKAN_API),vulkansc)
HEADERS_HPP = $(VULKAN)/vulkan$(API_SUFFIX)_core.hpp
STATIC_JSON = $(STATIC_JSON_SRC)/vkpcc.json
JSON_PCC    = $(JSON)/vkpcc.json
STATIC_CTS_COPY = \
	 $(JSON)/cts/vkjson_data_default.h \
	 $(JSON)/cts/vkjson_parser_default.h
JSON_SCHEMA = $(JSON)/vk.json
JSON_GENERATOR = $(JSON)/vulkan_json_data.hpp \
		 $(JSON)/vulkan_json_gen.h \
		 $(JSON)/vulkan_json_gen.c
JSON_PARSER = $(JSON)/vulkan_json_parser.hpp
JSON_CTS = $(JSON)/cts/vulkan_json_data.hpp  $(JSON)/cts/vulkan_json_parser.hpp
JSON_SCRIPTS = $(SCRIPTS)/json_parser.py $(SCRIPTS)/json_generator.py
endif
HEADERS = $(HEADERS_H) $(HEADERS_HPP)
JSON_FILES = $(JSON_SCHEMA) $(JSON_GENERATOR) $(JSON_PARSER)
JSON_CTS_FILES = $(JSON_CTS)

default: install

install: $(HEADERS) $(STATIC_HEADERS) $(CODEC_HEADERS) $(JSON_FILES) $(JSON_PCC) $(JSON_CTS_FILES) $(STATIC_CTS_COPY)

$(VULKAN)/vulkan$(API_SUFFIX).h: $(STATIC)/vulkan$(API_SUFFIX).h
	$(QUIET)$(MKDIR) $(VULKAN)
	$(CP) $? $@

$(VULKAN)/vulkan$(API_SUFFIX).hpp: $(STATIC)/vulkan$(API_SUFFIX).h
	$(QUIET)$(MKDIR) $(VULKAN)
	$(CP) $? $@

$(VULKAN)/vk_platform.h: $(STATIC)/vk_platform.h
	$(QUIET)$(MKDIR) $(VULKAN)
	$(CP) $? $@

################################################

# Autogenerate vulkan header from XML API description

# Python and XML files on which vulkan_core.h depends
GENSCRIPT   = $(SCRIPTS)/genvk.py
VKXML	    = vk.xml
VKH_DEPENDS = $(VKXML) $(GENSCRIPT) $(SCRIPTS)/reg.py $(SCRIPTS)/generator.py

$(HEADERS_H): $(VKH_DEPENDS)
	$(MKDIR) $(VULKAN)
	$(PYTHON) $(GENSCRIPT) $(MISRACOPTS) $(GENOPTS) -registry $(VKXML) \
	    -o $(VULKAN) $(notdir $@)

$(HEADERS_HPP): $(VKH_DEPENDS)
	$(MKDIR) $(VULKAN)
	$(PYTHON) $(GENSCRIPT) $(MISRACPPOPTS) $(GENOPTS) -registry $(VKXML) \
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
CODECXML = video.xml
# Do not build video headers for Vulkan SC
ifeq ($(VULKAN_API),vulkan)
CODEC_HEADERS = $(CODECS:%=$(VIDEO_INCLUDE)/%)
else
CODEC_HEADERS =
endif

codec_headers: $(CODEC_HEADERS)

$(VIDEO_INCLUDE)/%.h: $(CODECXML) $(GENSCRIPT) $(SCRIPTS)/reg.py $(SCRIPTS)/generator.py
	$(QUIET)$(MKDIR) $(VIDEO_INCLUDE)
	$(QUIET)$(PYTHON) $(GENSCRIPT) $(GENOPTS) -registry $(CODECXML) -o $(VIDEO_INCLUDE) $(notdir $@)

# Verify registry XML files against the schema
validate:
	jing -c registry.rnc $(VKXML)
	$(PYTHON) $(XML_CONSISTENCY) $(VKXML)
	jing -c registry.rnc $(CODECXML)

# Test that generated Vulkan headers compile

# Platforms to test
TESTDEFS = -DVK_USE_PLATFORM_XCB_KHR -DVK_USE_PLATFORM_XLIB_KHR

TESTFILE = $(TESTS)/htest$(API_SUFFIX).c

#@ -DUSE_HPP=1 is used only for Vulkan SC build
test: $(HEADERS) $(STATIC_HEADERS) $(CODEC_HEADERS)
	gcc -Wall -pedantic-errors -std=c99 -c -I$(INCLUDE) -I$(TESTS) $(TESTFILE)
	gcc -Wall -pedantic-errors -std=c11 -c -I$(INCLUDE) -I$(TESTS) $(TESTFILE)
	g++ -Wall -pedantic-errors -c -std=c++11 -I$(INCLUDE) -I$(TESTS) $(TESTFILE)
ifeq ($(VULKAN_API),vulkansc)
	g++ -Wall -pedantic-errors -c -std=c++98 -I$(INCLUDE) -I$(TESTS) $(TESTFILE)
	g++ -Wall -pedantic-errors -c -std=c++11 -I$(INCLUDE) -I$(TESTS) -DUSE_HPP=1 $(TESTFILE)
endif
	$(RM) htest.o $(TESTS)/test.o

# Test that generated video codec headers compile

vtest: $(CODEC_HEADERS)
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_CODECS_COMMON
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_CODEC_H264STD
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_CODEC_H264STD_DECODE
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_CODEC_H264STD_ENCODE
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_CODEC_H264STD -D VULKAN_VIDEO_CODEC_H264STD_DECODE -D VULKAN_VIDEO_CODEC_H264STD_ENCODE
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_CODEC_H265STD
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_CODEC_H265STD_DECODE
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_CODEC_H265STD_ENCODE
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_CODEC_H265STD -D VULKAN_VIDEO_CODEC_H265STD_DECODE -D VULKAN_VIDEO_CODEC_H265STD_ENCODE
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_ALL
	gcc -Wall -std=c99 -c -I$(INCLUDE) $(TESTS)/vtest.c -D VULKAN_VIDEO_ALL -D VK_NO_STDINT_H
	$(RM) vtest.o

################################################

# Autogenerate JSON Schema and utils from the XML API description
$(JSON_FILES): $(VKH_DEPENDS) $(JSON_SCRIPTS)
	$(QUIET)$(MKDIR) $(JSON)
	$(PYTHON) $(GENSCRIPT) $(GENOPTS) -registry $(VKXML) \
	    -o $(JSON) $(notdir $@)

$(JSON_CTS_FILES): $(VKH_DEPENDS) $(JSON_SCRIPTS)
	$(QUIET)$(MKDIR) $(JSON)/cts
	$(PYTHON) $(GENSCRIPT) $(GENOPTS) -registry $(VKXML) --iscts \
	    -o $(JSON)/cts $(notdir $@)

$(JSON)/cts/vkjson_data_default.h: $(STATIC_JSON_SRC)/vkjson_data_default.h
	$(QUIET)$(MKDIR) $(JSON)/cts
	$(CP) $? $@

$(JSON)/cts/vkjson_parser_default.h: $(STATIC_JSON_SRC)/vkjson_parser_default.h
	$(QUIET)$(MKDIR) $(JSON)/cts
	$(CP) $? $@

$(JSON_PCC): $(STATIC_JSON)
	$(QUIET)$(MKDIR) $(JSON)
	$(CP) $? $@

################################################

# Files to clean up
PYDIRT = diag.txt dumpReg.txt errwarn.txt *.pyc regdump.txt
DIRT = $(PYDIRT) ERRS *.o

# Clean intermediate files
clean_dirt:
	-$(RM) $(DIRT) \#*

# Clean generated targets and intermediates
clean clobber: clean_dirt
	-$(RMRF) $(INCLUDE) $(JSON)
	-$(RMRF) $(INCLUDE) $(VIDEO_INCLUDE)
