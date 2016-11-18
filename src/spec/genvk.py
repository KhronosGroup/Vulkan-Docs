#!/usr/bin/python3
#
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

import argparse, cProfile, pdb, string, sys, time
from reg import *
from generator import write
from cgenerator import CGeneratorOptions, COutputGenerator
from docgenerator import DocGeneratorOptions, DocOutputGenerator
from pygenerator import PyOutputGenerator
from validitygenerator import ValidityOutputGenerator
from hostsyncgenerator import HostSynchronizationOutputGenerator
from extensionStubSource import ExtensionStubSourceOutputGenerator

# Simple timer functions
startTime = None

def startTimer(timeit):
    global startTime
    startTime = time.clock()

def endTimer(timeit, msg):
    global startTime
    endTime = time.clock()
    if (timeit):
        write(msg, endTime - startTime, file=sys.stderr)
        startTime = None

# Turn a list of strings into a regexp string matching exactly those strings
def makeREstring(list):
    return '^(' + '|'.join(list) + ')$'

# Returns a directory of [ generator function, generator options ] indexed
# by specified short names. The generator options incorporate the following
# parameters:
#
# extensions - list of extension names to include.
# protect - True if re-inclusion protection should be added to headers
# directory - path to directory in which to generate the target(s)
def makeGenOpts(extensions = [], protect = True, directory = '.'):
    global genOpts
    genOpts = {}

    # Descriptive names for various regexp patterns used to select
    # versions and extensions
    allVersions     = allExtensions = '.*'
    noVersions      = noExtensions = None

    addExtensions     = makeREstring(extensions)
    removeExtensions  = makeREstring([])

    # Copyright text prefixing all headers (list of strings).
    prefixStrings = [
        '/*',
        '** Copyright (c) 2015-2016 The Khronos Group Inc.',
        '**',
        '** Licensed under the Apache License, Version 2.0 (the "License");',
        '** you may not use this file except in compliance with the License.',
        '** You may obtain a copy of the License at',
        '**',
        '**     http://www.apache.org/licenses/LICENSE-2.0',
        '**',
        '** Unless required by applicable law or agreed to in writing, software',
        '** distributed under the License is distributed on an "AS IS" BASIS,',
        '** WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.',
        '** See the License for the specific language governing permissions and',
        '** limitations under the License.',
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
    protectFeature = protect
    protectProto = protect

    # Vulkan 1.0 - header for core API + extensions.
    # To generate just the core API,
    # change to 'defaultExtensions = None' below.
    genOpts['vulkan.h'] = [
          COutputGenerator,
          CGeneratorOptions(
            filename          = 'vulkan.h',
            directory         = directory,
            apiname           = 'vulkan',
            profile           = None,
            versions          = allVersions,
            emitversions      = allVersions,
            defaultExtensions = 'vulkan',
            addExtensions     = None,
            removeExtensions  = None,
            prefixText        = prefixStrings + vkPrefixStrings,
            genFuncPointers   = True,
            protectFile       = protectFile,
            protectFeature    = False,
            protectProto      = '#ifndef',
            protectProtoStr   = 'VK_NO_PROTOTYPES',
            apicall           = 'VKAPI_ATTR ',
            apientry          = 'VKAPI_CALL ',
            apientryp         = 'VKAPI_PTR *',
            alignFuncParam    = 48)
        ]

    # Vulkan 1.0 draft - API include files for spec and ref pages
    # Overwrites include subdirectories in spec source tree
    # The generated include files do not include the calling convention
    # macros (apientry etc.), unlike the header files.
    # Because the 1.0 core branch includes ref pages for extensions,
    # all the extension interfaces need to be generated, even though
    # none are used by the core spec itself.
    genOpts['apiinc'] = [
          DocOutputGenerator,
          DocGeneratorOptions(
            filename          = 'timeMarker',
            directory         = directory,
            apiname           = 'vulkan',
            profile           = None,
            versions          = allVersions,
            emitversions      = allVersions,
            defaultExtensions = None,
            addExtensions     = addExtensions,
            removeExtensions  = removeExtensions,
            prefixText        = prefixStrings + vkPrefixStrings,
            apicall           = '',
            apientry          = '',
            apientryp         = '*',
            alignFuncParam    = 48,
            expandEnumerants  = False)
        ]

    # Vulkan 1.0 draft - API names to validate man/api spec includes & links
    genOpts['vkapi.py'] = [
          PyOutputGenerator,
          DocGeneratorOptions(
            filename          = 'vkapi.py',
            directory         = directory,
            apiname           = 'vulkan',
            profile           = None,
            versions          = allVersions,
            emitversions      = allVersions,
            defaultExtensions = None,
            addExtensions     = addExtensions,
            removeExtensions  = removeExtensions)
        ]

    # Vulkan 1.0 draft - core API validity files for spec
    genOpts['validinc'] = [
          ValidityOutputGenerator,
          DocGeneratorOptions(
            filename          = 'timeMarker',
            directory         = directory,
            apiname           = 'vulkan',
            profile           = None,
            versions          = allVersions,
            emitversions      = allVersions,
            defaultExtensions = None,
            addExtensions     = addExtensions,
            removeExtensions  = removeExtensions)
        ]

    # Vulkan 1.0 draft - core API host sync table files for spec
    genOpts['hostsyncinc'] = [
          HostSynchronizationOutputGenerator,
          DocGeneratorOptions(
            filename          = 'timeMarker',
            directory         = directory,
            apiname           = 'vulkan',
            profile           = None,
            versions          = allVersions,
            emitversions      = allVersions,
            defaultExtensions = None,
            addExtensions     = addExtensions,
            removeExtensions  = removeExtensions)
        ]

    genOpts['vulkan_ext.c'] = [
          ExtensionStubSourceOutputGenerator,
          CGeneratorOptions(
            filename          = 'vulkan_ext.c',
            directory         = directory,
            apiname           = 'vulkan',
            profile           = None,
            versions          = allVersions,
            emitversions      = None,
            defaultExtensions = None,
            addExtensions     = '.*',
            removeExtensions  = None,
            prefixText        = prefixStrings + vkPrefixStrings,
            alignFuncParam    = 48)
        ]


# Generate a target based on the options in the matching genOpts{} object.
# This is encapsulated in a function so it can be profiled and/or timed.
# The args parameter is an parsed argument object containing the following
# fields that are used:
#   target - target to generate
#   directory - directory to generate it in
#   protect - True if re-inclusion wrappers should be created
#   extensions - list of additional extensions to include in generated
#   interfaces
def genTarget(args):
    global genOpts

    # Create generator options with specified parameters
    makeGenOpts(extensions = args.extension,
                protect = args.protect,
                directory = args.directory)

    if (args.target in genOpts.keys()):
        createGenerator = genOpts[args.target][0]
        options = genOpts[args.target][1]

        write('* Building', options.filename, file=sys.stderr)

        startTimer(args.time)
        gen = createGenerator(errFile=errWarn,
                              warnFile=errWarn,
                              diagFile=diag)
        reg.setGenerator(gen)
        reg.apiGen(options)
        write('* Generated', options.filename, file=sys.stderr)
        endTimer(args.time, '* Time to generate ' + options.filename + ' =')
    else:
        write('No generator options for unknown target:',
              args.target, file=sys.stderr)

# -extension name - may be a single extension name, a a space-separated list
# of names, or a regular expression.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-extension', action='append',
                        default=[],
                        help='Specify an extension or extensions to add to targets')
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
    parser.add_argument('-validate', action='store_true',
                        help='Enable group validation')
    parser.add_argument('-o', action='store', dest='directory',
                        default='.',
                        help='Create target and related files in specified directory')
    parser.add_argument('target', metavar='target', nargs='?',
                        help='Specify target')

    args = parser.parse_args()

    # This splits arguments which are space-separated lists
    args.extension = [name for arg in args.extension for name in arg.split()]

    # Load & parse registry
    reg = Registry()

    startTimer(args.time)
    tree = etree.parse(args.registry)
    endTimer(args.time, '* Time to make ElementTree =')

    startTimer(args.time)
    reg.loadElementTree(tree)
    endTimer(args.time, '* Time to parse ElementTree =')

    if (args.validate):
        reg.validateGroups()

    if (args.dump):
        write('* Dumping registry to regdump.txt', file=sys.stderr)
        reg.dumpReg(filehandle = open('regdump.txt','w'))

    # create error/warning & diagnostic files
    if (args.errfile):
        errWarn = open(args.errfile, 'w')
    else:
        errWarn = sys.stderr

    if (args.diagfile):
        diag = open(args.diagfile, 'w')
    else:
        diag = None

    if (args.debug):
        pdb.run('genTarget(args)')
    elif (args.profile):
        import cProfile, pstats
        cProfile.run('genTarget(args)', 'profile.txt')
        p = pstats.Stats('profile.txt')
        p.strip_dirs().sort_stats('time').print_stats(50)
    else:
        genTarget(args)
