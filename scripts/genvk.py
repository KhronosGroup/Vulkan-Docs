#!/usr/bin/python3
#
# Copyright 2013-2022 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import pdb
import re
import sys
import time
import xml.etree.ElementTree as etree

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from cgenerator import CGeneratorOptions, COutputGenerator

from docgenerator import DocGeneratorOptions, DocOutputGenerator
from extensionmetadocgenerator import (ExtensionMetaDocGeneratorOptions,
                                       ExtensionMetaDocOutputGenerator)
from interfacedocgenerator import InterfaceDocGenerator
from generator import write
from spirvcapgenerator import SpirvCapabilityOutputGenerator
from hostsyncgenerator import HostSynchronizationOutputGenerator
from formatsgenerator import FormatsOutputGenerator
from pygenerator import PyOutputGenerator
from rubygenerator import RubyOutputGenerator
from reflib import logDiag, logWarn, logErr, setLogFile
from reg import Registry
from validitygenerator import ValidityOutputGenerator
from apiconventions import APIConventions

# Simple timer functions
startTime = None


def startTimer(timeit):
    global startTime
    if timeit:
        startTime = time.process_time()


def endTimer(timeit, msg):
    global startTime
    if timeit and startTime is not None:
        endTime = time.process_time()
        logDiag(msg, endTime - startTime)
        startTime = None


def makeREstring(strings, default=None, strings_are_regex=False):
    """Turn a list of strings into a regexp string matching exactly those strings."""
    if strings or default is None:
        if not strings_are_regex:
            strings = (re.escape(s) for s in strings)
        return '^(' + '|'.join(strings) + ')$'
    return default


def makeGenOpts(args):
    """Returns a directory of [ generator function, generator options ] indexed
    by specified short names. The generator options incorporate the following
    parameters:

    args is an parsed argument object; see below for the fields that are used."""
    global genOpts
    genOpts = {}

    # Default class of extensions to include, or None
    defaultExtensions = args.defaultExtensions

    # Additional extensions to include (list of extensions)
    extensions = args.extension

    # Extensions to remove (list of extensions)
    removeExtensions = args.removeExtensions

    # Extensions to emit (list of extensions)
    emitExtensions = args.emitExtensions

    # SPIR-V capabilities / features to emit (list of extensions & capabilities)
    emitSpirv = args.emitSpirv

    # Vulkan Formats to emit
    emitFormats = args.emitFormats

    # Features to include (list of features)
    features = args.feature

    # Whether to disable inclusion protect in headers
    protect = args.protect

    # Output target directory
    directory = args.directory

    # Path to generated files, particularly apimap.py
    genpath = args.genpath

    # Generate MISRA C-friendly headers
    misracstyle = args.misracstyle;

    # Generate MISRA C++-friendly headers
    misracppstyle = args.misracppstyle;

    # Descriptive names for various regexp patterns used to select
    # versions and extensions
    allFormats = allSpirv = allFeatures = allExtensions = r'.*'

    # Turn lists of names/patterns into matching regular expressions
    addExtensionsPat     = makeREstring(extensions, None)
    removeExtensionsPat  = makeREstring(removeExtensions, None)
    emitExtensionsPat    = makeREstring(emitExtensions, allExtensions)
    emitSpirvPat         = makeREstring(emitSpirv, allSpirv)
    emitFormatsPat       = makeREstring(emitFormats, allFormats)
    featuresPat          = makeREstring(features, allFeatures)

    # Copyright text prefixing all headers (list of strings).
    # The SPDX formatting below works around constraints of the 'reuse' tool
    prefixStrings = [
        '/*',
        '** Copyright 2015-2022 The Khronos Group Inc.',
        '**',
        '** SPDX-License-Identifier' + ': Apache-2.0',
        '*/',
        ''
    ]

    # Text specific to Vulkan headers
    vkPrefixStrings = [
        '/*',
        '** This header is generated from the Khronos Vulkan XML API Registry.',
        '**',
        '*/',
        ''
    ]

    # Defaults for generating re-inclusion protection wrappers (or not)
    protectFile = protect

    # An API style conventions object
    conventions = APIConventions()

    defaultAPIName = conventions.xml_api_name

    # API include files for spec and ref pages
    # Overwrites include subdirectories in spec source tree
    # The generated include files do not include the calling convention
    # macros (apientry etc.), unlike the header files.
    # Because the 1.0 core branch includes ref pages for extensions,
    # all the extension interfaces need to be generated, even though
    # none are used by the core spec itself.
    genOpts['apiinc'] = [
          DocOutputGenerator,
          DocGeneratorOptions(
            conventions       = conventions,
            filename          = 'timeMarker',
            directory         = directory,
            genpath           = genpath,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = None,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            prefixText        = prefixStrings + vkPrefixStrings,
            apicall           = '',
            apientry          = '',
            apientryp         = '*',
            alignFuncParam    = 48,
            expandEnumerants  = False)
        ]

    # Python and Ruby representations of API information, used by scripts
    # that do not need to load the full XML.
    genOpts['apimap.py'] = [
          PyOutputGenerator,
          DocGeneratorOptions(
            conventions       = conventions,
            filename          = 'apimap.py',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = None,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            reparentEnums     = False)
        ]

    genOpts['apimap.rb'] = [
          RubyOutputGenerator,
          DocGeneratorOptions(
            conventions       = conventions,
            filename          = 'apimap.rb',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = None,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            reparentEnums     = False)
        ]


    # API validity files for spec
    #
    # requireCommandAliases is set to True because we need validity files
    # for the command something is promoted to even when the promoted-to
    # feature is not included. This avoids wordy includes of validity files.
    genOpts['validinc'] = [
          ValidityOutputGenerator,
          DocGeneratorOptions(
            conventions       = conventions,
            filename          = 'timeMarker',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = None,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            requireCommandAliases = True,
            )
        ]

    # API host sync table files for spec
    genOpts['hostsyncinc'] = [
          HostSynchronizationOutputGenerator,
          DocGeneratorOptions(
            conventions       = conventions,
            filename          = 'timeMarker',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = None,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            reparentEnums     = False)
        ]

    # Extension metainformation for spec extension appendices
    # Includes all extensions by default, but only so that the generated
    # 'promoted_extensions_*' files refer to all extensions that were
    # promoted to a core version.
    genOpts['extinc'] = [
          ExtensionMetaDocOutputGenerator,
          ExtensionMetaDocGeneratorOptions(
            conventions       = conventions,
            filename          = 'timeMarker',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = None,
            defaultExtensions = defaultExtensions,
            addExtensions     = addExtensionsPat,
            removeExtensions  = None,
            emitExtensions    = emitExtensionsPat)
        ]

    # Version and extension interface docs for version/extension appendices
    # Includes all extensions by default.
    genOpts['interfaceinc'] = [
          InterfaceDocGenerator,
          DocGeneratorOptions(
            conventions       = conventions,
            filename          = 'timeMarker',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = None,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            reparentEnums     = False)
        ]

    genOpts['spirvcapinc'] = [
          SpirvCapabilityOutputGenerator,
          DocGeneratorOptions(
            conventions       = conventions,
            filename          = 'timeMarker',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = None,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            emitSpirv         = emitSpirvPat,
            reparentEnums     = False)
        ]

    # Used to generate various format chapter tables
    genOpts['formatsinc'] = [
          FormatsOutputGenerator,
          DocGeneratorOptions(
            conventions       = conventions,
            filename          = 'timeMarker',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = None,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            emitFormats       = emitFormatsPat,
            reparentEnums     = False)
        ]

    # Platform extensions, in their own header files
    # Each element of the platforms[] array defines information for
    # generating a single platform:
    #   [0] is the generated header file name
    #   [1] is the set of platform extensions to generate
    #   [2] is additional extensions whose interfaces should be considered,
    #   but suppressed in the output, to avoid duplicate definitions of
    #   dependent types like VkDisplayKHR and VkSurfaceKHR which come from
    #   non-platform extensions.

    # Track all platform extensions, for exclusion from vulkan_core.h
    allPlatformExtensions = []

    # Extensions suppressed for all WSI platforms (WSI extensions required
    # by all platforms)
    commonSuppressExtensions = [ 'VK_KHR_display', 'VK_KHR_swapchain' ]

    # Extensions required and suppressed for beta "platform". This can
    # probably eventually be derived from the requires= attributes of
    # the extension blocks.
    betaRequireExtensions = [
        'VK_KHR_portability_subset',
        'VK_KHR_video_encode_queue',
        'VK_EXT_video_encode_h264',
        'VK_EXT_video_encode_h265',
    ]

    betaSuppressExtensions = [
        'VK_KHR_video_queue'
    ]

    platforms = [
        [ 'vulkan_android.h',     [ 'VK_KHR_android_surface',
                                    'VK_ANDROID_external_memory_android_hardware_buffer'
                                                                  ], commonSuppressExtensions +
                                                                     [ 'VK_KHR_format_feature_flags2',
                                                                     ] ],
        [ 'vulkan_fuchsia.h',     [ 'VK_FUCHSIA_imagepipe_surface',
                                    'VK_FUCHSIA_external_memory',
                                    'VK_FUCHSIA_external_semaphore',
                                    'VK_FUCHSIA_buffer_collection' ], commonSuppressExtensions ],
        [ 'vulkan_ggp.h',         [ 'VK_GGP_stream_descriptor_surface',
                                    'VK_GGP_frame_token'          ], commonSuppressExtensions ],
        [ 'vulkan_ios.h',         [ 'VK_MVK_ios_surface'          ], commonSuppressExtensions ],
        [ 'vulkan_macos.h',       [ 'VK_MVK_macos_surface'        ], commonSuppressExtensions ],
        [ 'vulkan_vi.h',          [ 'VK_NN_vi_surface'            ], commonSuppressExtensions ],
        [ 'vulkan_wayland.h',     [ 'VK_KHR_wayland_surface'      ], commonSuppressExtensions ],
        [ 'vulkan_win32.h',       [ 'VK_.*_win32(|_.*)', 'VK_.*_winrt(|_.*)', 'VK_EXT_full_screen_exclusive' ],
                                                                     commonSuppressExtensions +
                                                                     [ 'VK_KHR_external_semaphore',
                                                                       'VK_KHR_external_memory_capabilities',
                                                                       'VK_KHR_external_fence',
                                                                       'VK_KHR_external_fence_capabilities',
                                                                       'VK_KHR_get_surface_capabilities2',
                                                                       'VK_NV_external_memory_capabilities',
                                                                     ] ],
        [ 'vulkan_xcb.h',         [ 'VK_KHR_xcb_surface'          ], commonSuppressExtensions ],
        [ 'vulkan_xlib.h',        [ 'VK_KHR_xlib_surface'         ], commonSuppressExtensions ],
        [ 'vulkan_directfb.h',    [ 'VK_EXT_directfb_surface'     ], commonSuppressExtensions ],
        [ 'vulkan_xlib_xrandr.h', [ 'VK_EXT_acquire_xlib_display' ], commonSuppressExtensions ],
        [ 'vulkan_metal.h',       [ 'VK_EXT_metal_surface',
                                    'VK_EXT_metal_objects'        ], commonSuppressExtensions ],
        [ 'vulkan_screen.h',      [ 'VK_QNX_screen_surface'       ], commonSuppressExtensions ],
        [ 'vulkan_beta.h',        betaRequireExtensions,             betaSuppressExtensions ],
    ]

    for platform in platforms:
        headername = platform[0]

        allPlatformExtensions += platform[1]

        addPlatformExtensionsRE = makeREstring(
            platform[1] + platform[2], strings_are_regex=True)
        emitPlatformExtensionsRE = makeREstring(
            platform[1], strings_are_regex=True)

        opts = CGeneratorOptions(
            conventions       = conventions,
            filename          = headername,
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = None,
            defaultExtensions = None,
            addExtensions     = addPlatformExtensionsRE,
            removeExtensions  = None,
            emitExtensions    = emitPlatformExtensionsRE,
            prefixText        = prefixStrings + vkPrefixStrings,
            genFuncPointers   = True,
            protectFile       = protectFile,
            protectFeature    = False,
            protectProto      = '#ifndef',
            protectProtoStr   = 'VK_NO_PROTOTYPES',
            apicall           = 'VKAPI_ATTR ',
            apientry          = 'VKAPI_CALL ',
            apientryp         = 'VKAPI_PTR *',
            alignFuncParam    = 48,
            misracstyle       = misracstyle,
            misracppstyle     = misracppstyle)

        genOpts[headername] = [ COutputGenerator, opts ]

    # Header for core API + extensions.
    # To generate just the core API,
    # change to 'defaultExtensions = None' below.
    #
    # By default this adds all enabled, non-platform extensions.
    # It removes all platform extensions (from the platform headers options
    # constructed above) as well as any explicitly specified removals.

    removeExtensionsPat = makeREstring(
        allPlatformExtensions + removeExtensions, None, strings_are_regex=True)

    genOpts['vulkan_core.h'] = [
          COutputGenerator,
          CGeneratorOptions(
            conventions       = conventions,
            filename          = 'vulkan_core.h',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = defaultExtensions,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            prefixText        = prefixStrings + vkPrefixStrings,
            genFuncPointers   = True,
            protectFile       = protectFile,
            protectFeature    = False,
            protectProto      = '#ifndef',
            protectProtoStr   = 'VK_NO_PROTOTYPES',
            apicall           = 'VKAPI_ATTR ',
            apientry          = 'VKAPI_CALL ',
            apientryp         = 'VKAPI_PTR *',
            alignFuncParam    = 48,
            misracstyle       = misracstyle,
            misracppstyle     = misracppstyle)
        ]

    # Unused - vulkan10.h target.
    # It is possible to generate a header with just the Vulkan 1.0 +
    # extension interfaces defined, but since the promoted KHR extensions
    # are now defined in terms of the 1.1 interfaces, such a header is very
    # similar to vulkan_core.h.
    genOpts['vulkan10.h'] = [
          COutputGenerator,
          CGeneratorOptions(
            conventions       = conventions,
            filename          = 'vulkan10.h',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = 'VK_VERSION_1_0',
            emitversions      = 'VK_VERSION_1_0',
            defaultExtensions = None,
            addExtensions     = None,
            removeExtensions  = None,
            emitExtensions    = None,
            prefixText        = prefixStrings + vkPrefixStrings,
            genFuncPointers   = True,
            protectFile       = protectFile,
            protectFeature    = False,
            protectProto      = '#ifndef',
            protectProtoStr   = 'VK_NO_PROTOTYPES',
            apicall           = 'VKAPI_ATTR ',
            apientry          = 'VKAPI_CALL ',
            apientryp         = 'VKAPI_PTR *',
            alignFuncParam    = 48,
            misracstyle       = misracstyle,
            misracppstyle     = misracppstyle)
        ]

    # Video header target - combines all video extension dependencies into a
    # single header, at present.
    genOpts['vk_video.h'] = [
          COutputGenerator,
          CGeneratorOptions(
            conventions       = conventions,
            filename          = 'vk_video.h',
            directory         = directory,
            genpath           = None,
            apiname           = 'vulkan',
            profile           = None,
            versions          = None,
            emitversions      = None,
            defaultExtensions = defaultExtensions,
            addExtensions     = addExtensionsPat,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            prefixText        = prefixStrings + vkPrefixStrings,
            genFuncPointers   = True,
            protectFile       = protectFile,
            protectFeature    = False,
            protectProto      = '#ifndef',
            protectProtoStr   = 'VK_NO_PROTOTYPES',
            apicall           = '',
            apientry          = '',
            apientryp         = '',
            alignFuncParam    = 48,
            misracstyle       = misracstyle,
            misracppstyle     = misracppstyle)
    ]

    # Video extension 'Std' interfaces, each in its own header files
    # These are not Vulkan extensions, or a part of the Vulkan API at all,
    # but are treated in a similar fashion for generation purposes.
    #
    # Each element of the videoStd[] array is an extension name defining an
    # interface, and is also the basis for the generated header file name.

    videoStd = [
        'vulkan_video_codecs_common',
        'vulkan_video_codec_h264std',
        'vulkan_video_codec_h264std_decode',
        'vulkan_video_codec_h264std_encode',
        'vulkan_video_codec_h265std',
        'vulkan_video_codec_h265std_decode',
        'vulkan_video_codec_h265std_encode',
    ]

    addExtensionRE = makeREstring(videoStd)
    for codec in videoStd:
        headername = f'{codec}.h'

        # Consider all of the codecs 'extensions', but only emit this one
        emitExtensionRE = makeREstring([codec])

        opts = CGeneratorOptions(
            conventions       = conventions,
            filename          = headername,
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = None,
            emitversions      = None,
            defaultExtensions = None,
            addExtensions     = addExtensionRE,
            removeExtensions  = None,
            emitExtensions    = emitExtensionRE,
            prefixText        = prefixStrings + vkPrefixStrings,
            genFuncPointers   = False,
            protectFile       = protectFile,
            protectFeature    = False,
            alignFuncParam    = 48,
            )

        genOpts[headername] = [ COutputGenerator, opts ]

    # Unused - vulkan11.h target.
    # It is possible to generate a header with just the Vulkan 1.0 +
    # extension interfaces defined, but since the promoted KHR extensions
    # are now defined in terms of the 1.1 interfaces, such a header is very
    # similar to vulkan_core.h.
    genOpts['vulkan11.h'] = [
          COutputGenerator,
          CGeneratorOptions(
            conventions       = conventions,
            filename          = 'vulkan11.h',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = '^VK_VERSION_1_[01]$',
            emitversions      = '^VK_VERSION_1_[01]$',
            defaultExtensions = None,
            addExtensions     = None,
            removeExtensions  = None,
            emitExtensions    = None,
            prefixText        = prefixStrings + vkPrefixStrings,
            genFuncPointers   = True,
            protectFile       = protectFile,
            protectFeature    = False,
            protectProto      = '#ifndef',
            protectProtoStr   = 'VK_NO_PROTOTYPES',
            apicall           = 'VKAPI_ATTR ',
            apientry          = 'VKAPI_CALL ',
            apientryp         = 'VKAPI_PTR *',
            alignFuncParam    = 48,
            misracstyle       = misracstyle,
            misracppstyle     = misracppstyle)
        ]

    genOpts['alias.h'] = [
          COutputGenerator,
          CGeneratorOptions(
            conventions       = conventions,
            filename          = 'alias.h',
            directory         = directory,
            genpath           = None,
            apiname           = defaultAPIName,
            profile           = None,
            versions          = featuresPat,
            emitversions      = featuresPat,
            defaultExtensions = defaultExtensions,
            addExtensions     = None,
            removeExtensions  = removeExtensionsPat,
            emitExtensions    = emitExtensionsPat,
            prefixText        = None,
            genFuncPointers   = False,
            protectFile       = False,
            protectFeature    = False,
            protectProto      = '',
            protectProtoStr   = '',
            apicall           = '',
            apientry          = '',
            apientryp         = '',
            alignFuncParam    = 36)
        ]


def genTarget(args):
    """Create an API generator and corresponding generator options based on
    the requested target and command line options.

    This is encapsulated in a function so it can be profiled and/or timed.
    The args parameter is an parsed argument object containing the following
    fields that are used:

    - target - target to generate
    - directory - directory to generate it in
    - protect - True if re-inclusion wrappers should be created
    - extensions - list of additional extensions to include in generated interfaces"""

    # Create generator options with parameters specified on command line
    makeGenOpts(args)

    # Select a generator matching the requested target
    if args.target in genOpts:
        createGenerator = genOpts[args.target][0]
        options = genOpts[args.target][1]

        logDiag('* Building', options.filename)
        logDiag('* options.versions          =', options.versions)
        logDiag('* options.emitversions      =', options.emitversions)
        logDiag('* options.defaultExtensions =', options.defaultExtensions)
        logDiag('* options.addExtensions     =', options.addExtensions)
        logDiag('* options.removeExtensions  =', options.removeExtensions)
        logDiag('* options.emitExtensions    =', options.emitExtensions)
        logDiag('* options.emitSpirv         =', options.emitSpirv)
        logDiag('* options.emitFormats       =', options.emitFormats)

        gen = createGenerator(errFile=errWarn,
                              warnFile=errWarn,
                              diagFile=diag)
        return (gen, options)
    else:
        logErr('No generator options for unknown target:', args.target)
        return None


# -feature name
# -extension name
# For both, "name" may be a single name, or a space-separated list
# of names, or a regular expression.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-defaultExtensions', action='store',
                        default=APIConventions().xml_api_name,
                        help='Specify a single class of extensions to add to targets')
    parser.add_argument('-extension', action='append',
                        default=[],
                        help='Specify an extension or extensions to add to targets')
    parser.add_argument('-removeExtensions', action='append',
                        default=[],
                        help='Specify an extension or extensions to remove from targets')
    parser.add_argument('-emitExtensions', action='append',
                        default=[],
                        help='Specify an extension or extensions to emit in targets')
    parser.add_argument('-emitSpirv', action='append',
                        default=[],
                        help='Specify a SPIR-V extension or capability to emit in targets')
    parser.add_argument('-emitFormats', action='append',
                        default=[],
                        help='Specify Vulkan Formats to emit in targets')
    parser.add_argument('-feature', action='append',
                        default=[],
                        help='Specify a core API feature name or names to add to targets')
    parser.add_argument('-debug', action='store_true',
                        help='Enable debugging')
    parser.add_argument('-dump', action='store_true',
                        help='Enable dump to stderr')
    parser.add_argument('-diagfile', action='store',
                        default=None,
                        help='Write diagnostics to specified file')
    parser.add_argument('-errfile', action='store',
                        default=None,
                        help='Write errors and warnings to specified file instead of stderr')
    parser.add_argument('-noprotect', dest='protect', action='store_false',
                        help='Disable inclusion protection in output headers')
    parser.add_argument('-profile', action='store_true',
                        help='Enable profiling')
    parser.add_argument('-registry', action='store',
                        default='vk.xml',
                        help='Use specified registry file instead of vk.xml')
    parser.add_argument('-time', action='store_true',
                        help='Enable timing')
    parser.add_argument('-genpath', action='store', default='gen',
                        help='Path to generated files')
    parser.add_argument('-o', action='store', dest='directory',
                        default='.',
                        help='Create target and related files in specified directory')
    parser.add_argument('target', metavar='target', nargs='?',
                        help='Specify target')
    parser.add_argument('-quiet', action='store_true', default=True,
                        help='Suppress script output during normal execution.')
    parser.add_argument('-verbose', action='store_false', dest='quiet', default=True,
                        help='Enable script output during normal execution.')
    parser.add_argument('-misracstyle', dest='misracstyle', action='store_true',
                        help='generate MISRA C-friendly headers')
    parser.add_argument('-misracppstyle', dest='misracppstyle', action='store_true',
                        help='generate MISRA C++-friendly headers')

    args = parser.parse_args()

    # This splits arguments which are space-separated lists
    args.feature = [name for arg in args.feature for name in arg.split()]
    args.extension = [name for arg in args.extension for name in arg.split()]

    # create error/warning & diagnostic files
    if args.errfile:
        errWarn = open(args.errfile, 'w', encoding='utf-8')
    else:
        errWarn = sys.stderr

    if args.diagfile:
        diag = open(args.diagfile, 'w', encoding='utf-8')
    else:
        diag = None

    if args.time:
        # Log diagnostics and warnings
        setLogFile(setDiag = True, setWarn = True, filename = '-')

    # Create the API generator & generator options
    (gen, options) = genTarget(args)

    # Create the registry object with the specified generator and generator
    # options. The options are set before XML loading as they may affect it.
    reg = Registry(gen, options)

    # Parse the specified registry XML into an ElementTree object
    startTimer(args.time)
    tree = etree.parse(args.registry)
    endTimer(args.time, '* Time to make ElementTree =')

    # Load the XML tree into the registry object
    startTimer(args.time)
    reg.loadElementTree(tree)
    endTimer(args.time, '* Time to parse ElementTree =')

    if args.dump:
        logDiag('* Dumping registry to regdump.txt')
        reg.dumpReg(filehandle=open('regdump.txt', 'w', encoding='utf-8'))

    # Finally, use the output generator to create the requested target
    if args.debug:
        pdb.run('reg.apiGen()')
    else:
        startTimer(args.time)
        reg.apiGen()
        endTimer(args.time, '* Time to generate ' + options.filename + ' =')

    if not args.quiet:
        logDiag('* Generated', options.filename)
