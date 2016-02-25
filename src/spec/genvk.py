#!/usr/bin/env python
#
# Copyright (c) 2013-2016 The Khronos Group Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and/or associated documentation files (the
# "Materials"), to deal in the Materials without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Materials, and to
# permit persons to whom the Materials are furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Materials.
#
# THE MATERIALS ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.

import sys, time, pdb, string, cProfile
from reg import *
from generator import write, CGeneratorOptions, COutputGenerator, DocGeneratorOptions, DocOutputGenerator, PyOutputGenerator, ValidityOutputGenerator, HostSynchronizationOutputGenerator

# debug - start header generation in debugger
# dump - dump registry after loading
# profile - enable Python profiling
# protect - whether to use #ifndef protections
# registry <filename> - use specified XML registry instead of gl.xml
# target - string name of target header, or all targets if None
# timeit - time length of registry loading & header generation
# validate - validate return & parameter group tags against <group>
debug   = False
dump    = False
profile = False
protect = True
target  = None
timeit  = False
validate= False
# Default input / log files
errFilename = None
diagFilename = 'diag.txt'
regFilename = 'vk.xml'

if __name__ == '__main__':
    i = 1
    while (i < len(sys.argv)):
        arg = sys.argv[i]
        i = i + 1
        if (arg == '-debug'):
            write('Enabling debug (-debug)', file=sys.stderr)
            debug = True
        elif (arg == '-dump'):
            write('Enabling dump (-dump)', file=sys.stderr)
            dump = True
        elif (arg == '-noprotect'):
            write('Disabling inclusion protection in output headers', file=sys.stderr)
            protect = False
        elif (arg == '-profile'):
            write('Enabling profiling (-profile)', file=sys.stderr)
            profile = True
        elif (arg == '-registry'):
            regFilename = sys.argv[i]
            i = i+1
            write('Using registry ', regFilename, file=sys.stderr)
        elif (arg == '-time'):
            write('Enabling timing (-time)', file=sys.stderr)
            timeit = True
        elif (arg == '-validate'):
            write('Enabling group validation (-validate)', file=sys.stderr)
            validate = True
        elif (arg[0:1] == '-'):
            write('Unrecognized argument:', arg, file=sys.stderr)
            exit(1)
        else:
            target = arg
            write('Using target', target, file=sys.stderr)

# Simple timer functions
startTime = None
def startTimer():
    global startTime
    startTime = time.clock()
def endTimer(msg):
    global startTime
    endTime = time.clock()
    if (timeit):
        write(msg, endTime - startTime)
        startTime = None

# Load & parse registry
reg = Registry()

startTimer()
tree = etree.parse(regFilename)
endTimer('Time to make ElementTree =')

startTimer()
reg.loadElementTree(tree)
endTimer('Time to parse ElementTree =')

if (validate):
    reg.validateGroups()

if (dump):
    write('***************************************')
    write('Performing Registry dump to regdump.txt')
    write('***************************************')
    reg.dumpReg(filehandle = open('regdump.txt','w'))

# Turn a list of strings into a regexp string matching exactly those strings
def makeREstring(list):
    return '^(' + '|'.join(list) + ')$'

# Descriptive names for various regexp patterns used to select
# versions and extensions
allVersions     = allExtensions = '.*'
noVersions      = noExtensions = None

# Copyright text prefixing all headers (list of strings).
prefixStrings = [
    '/*',
    '** Copyright (c) 2015-2016 The Khronos Group Inc.',
    '**',
    '** Permission is hereby granted, free of charge, to any person obtaining a',
    '** copy of this software and/or associated documentation files (the',
    '** "Materials"), to deal in the Materials without restriction, including',
    '** without limitation the rights to use, copy, modify, merge, publish,',
    '** distribute, sublicense, and/or sell copies of the Materials, and to',
    '** permit persons to whom the Materials are furnished to do so, subject to',
    '** the following conditions:',
    '**',
    '** The above copyright notice and this permission notice shall be included',
    '** in all copies or substantial portions of the Materials.',
    '**',
    '** THE MATERIALS ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,',
    '** EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF',
    '** MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.',
    '** IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY',
    '** CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,',
    '** TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE',
    '** MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.',
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

buildList = [
    # Vulkan 1.0 - header for core API + extensions.
    # To generate just the core API,
    # change to 'defaultExtensions = None' below.
    [ COutputGenerator,
      CGeneratorOptions(
        filename          = '../vulkan/vulkan.h',
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
    ],
    # Vulkan 1.0 draft - API include files for spec and ref pages
    # Overwrites include subdirectories in spec source tree
    # The generated include files do not include the calling convention
    # macros (apientry etc.), unlike the header files.
    # Because the 1.0 core branch includes ref pages for extensions,
    # all the extension interfaces need to be generated, even though
    # none are used by the core spec itself.
    [ DocOutputGenerator,
      DocGeneratorOptions(
        filename          = 'vulkan-docs',
        apiname           = 'vulkan',
        profile           = None,
        versions          = allVersions,
        emitversions      = allVersions,
        defaultExtensions = None,
        addExtensions     =
            makeREstring([
                'VK_KHR_surface',
            ]),
        removeExtensions  =
            makeREstring([
            ]),
        prefixText        = prefixStrings + vkPrefixStrings,
        apicall           = '',
        apientry          = '',
        apientryp         = '*',
        genDirectory      = '../../doc/specs/vulkan',
        alignFuncParam    = 48,
        expandEnumerants  = False)
    ],
    # Vulkan 1.0 draft - API names to validate man/api spec includes & links
    [ PyOutputGenerator,
      DocGeneratorOptions(
        filename          = '../../doc/specs/vulkan/vkapi.py',
        apiname           = 'vulkan',
        profile           = None,
        versions          = allVersions,
        emitversions      = allVersions,
        defaultExtensions = None,
        addExtensions     =
            makeREstring([
                'VK_KHR_surface',
            ]),
        removeExtensions  =
            makeREstring([
            ]))
    ],
    # Vulkan 1.0 draft - core API validity files for spec
    # Overwrites validity subdirectories in spec source tree
    [ ValidityOutputGenerator,
      DocGeneratorOptions(
        filename          = 'validity',
        apiname           = 'vulkan',
        profile           = None,
        versions          = allVersions,
        emitversions      = allVersions,
        defaultExtensions = None,
        addExtensions     =
            makeREstring([
                'VK_KHR_surface',
            ]),
        removeExtensions  =
            makeREstring([
            ]),
        genDirectory      = '../../doc/specs/vulkan')
    ],
    # Vulkan 1.0 draft - core API host sync table files for spec
    # Overwrites subdirectory in spec source tree
    [ HostSynchronizationOutputGenerator,
      DocGeneratorOptions(
        filename          = 'hostsynctable',
        apiname           = 'vulkan',
        profile           = None,
        versions          = allVersions,
        emitversions      = allVersions,
        defaultExtensions = None,
        addExtensions     =
            makeREstring([
                'VK_KHR_surface',
            ]),
        removeExtensions  =
            makeREstring([
            ]),
        genDirectory      = '../../doc/specs/vulkan')
    ],
    None
]

# create error/warning & diagnostic files
if (errFilename):
    errWarn = open(errFilename,'w')
else:
    errWarn = sys.stderr
diag = open(diagFilename, 'w')

def genHeaders():
    # Loop over targets, building each
    generated = 0
    for item in buildList:
        if (item == None):
            break
        createGenerator = item[0]
        genOpts = item[1]
        if (target and target != genOpts.filename):
            # write('*** Skipping', genOpts.filename)
            continue
        write('*** Building', genOpts.filename)
        generated = generated + 1
        startTimer()
        gen = createGenerator(errFile=errWarn,
                              warnFile=errWarn,
                              diagFile=diag)
        reg.setGenerator(gen)
        reg.apiGen(genOpts)
        write('** Generated', genOpts.filename)
        endTimer('Time to generate ' + genOpts.filename + ' =')
    if (target and generated == 0):
        write('Failed to generate target:', target)

if (debug):
    pdb.run('genHeaders()')
elif (profile):
    import cProfile, pstats
    cProfile.run('genHeaders()', 'profile.txt')
    p = pstats.Stats('profile.txt')
    p.strip_dirs().sort_stats('time').print_stats(50)
else:
    genHeaders()
