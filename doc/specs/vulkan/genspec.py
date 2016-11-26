#!/usr/bin/python3
#
# Copyright (c) 2016 The Khronos Group Inc.
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

import time
from datetime import timedelta, date

# This script builds a full release package including XHTML and PDF
# versions of the specification, including an optional list of
# extensions. Other files in the release directory are removed,
#including man pages, XHTML chunked, HTML, validity output, etc.

# The current branch must be fully committed and up to date when the
# script is run, with no outstanding un-added / un-committed files.
# After completing the build, suggestions for creating tags are made.

# Khronos extensions
KHRextensions = [
    'VK_KHR_android_surface',
    'VK_KHR_display',
    'VK_KHR_display_swapchain',
    'VK_KHR_mir_surface',
    'VK_KHR_surface',
    'VK_KHR_swapchain',
    'VK_KHR_wayland_surface',
    'VK_KHR_win32_surface',
    'VK_KHR_xcb_surface',
    'VK_KHR_xlib_surface'
    ]

# All published extensions
allExtensions = KHRextensions + [
    'VK_AMD_draw_indirect_count',
    'VK_AMD_gcn_shader',
    'VK_AMD_negative_viewport_height',
    'VK_AMD_rasterization_order',
    'VK_AMD_shader_ballot',
    'VK_AMD_shader_explicit_vertex_parameter',
    'VK_AMD_shader_trinary_minmax',
    'VK_EXT_debug_marker',
    'VK_EXT_debug_report',
    'VK_IMG_filter_cubic',
    'VK_NV_dedicated_allocation',
    'VK_NV_external_memory',
    'VK_NV_external_memory_capabilities',
    'VK_NV_external_memory_win32',
    'VK_NV_win32_keyed_mutex',
    'VK_NV_glsl_shader',
    'VK_NVX_device_generated_commands'
    ]

# Return the Vulkan release number, used for tags
def releaseNum():
    return '$REVISION'

# Return a date for the current, or upcoming if not already, Friday,
# which is when releases happen
def buildOnFriday():
    today = date.today()
    friday = today + timedelta((4 - today.weekday()) % 7)
    return friday

# label = textual label to use for target being generated
# extensions = list of extension names to include
# outdir = directory to generate specs in
# apititle = extra title to apply to the specification
# xmlDir = directory containing registry XML
# xmlTargets = targets to build in src/spec/
# specDir = directory containing spec source & Makefile
# specTargets = targets to build in doc/specs/vulkan/
# miscSrc = path to copy misc files from, if non-None
# miscDst = path to copy misc files to, if non-None
# needRefSources = True if ref pages must be extracted from the spec sources
def buildRelease(label, extensions, outdir,
                 apititle,
                 xmlDir, xmlTargets,
                 specDir, specTargets,
                 miscSrc = None, miscDst = None, needRefSources = False):
    print('echo Info: Generating target=', label,
          'outdir=' + outdir)

    outarg = 'OUTDIR=' + outdir

    if (extensions != None and len(extensions) > 0):
        extarg = 'EXTENSIONS="' + ' '.join(extensions) + '"'
    else:
        extarg = ''

    if (apititle != None):
        titlearg = 'APITITLE="' + apititle + '"'
    else:
        titlearg = ''

    # print('echo Info: Cleaning spec in', outdir)
    print('(cd ', outdir, '&& rm -rf',
          'xhtml chunked pdf',
          'man config checks',
          'vkspec.html styleguide.html apispec.html apispec.pdf registry.html',
          ')')

    # print('echo Info: Generating specversion.txt')
    print('cd', specDir)
    print('rm specversion.txt ; make specversion.txt')

    # print('echo Info: Generating headers and spec include files')
    print('cd', xmlDir)
    print('make', outarg, xmlTargets)

    # print('echo Info: Generating ref pages sources and spec targets')
    print('cd', specDir)
    print('make', outarg, 'clean')
    # This is a temporary workaround for a dependency bug - if any of the
    # specTargets require ref page sources, and they aren't already present
    # at the time the make is invoked, that target will not be built.
    if needRefSources:
        print('make', outarg, extarg, 'man/apispec.txt')
    # Now make the actual targets.
    print('make -O -k -j 8',
          outarg,
          extarg,
          titlearg,
          'NOTEOPTS="-a implementation-guide"',
          specTargets)

    if (miscSrc != None and miscDst != None):
        print('cp', miscSrc + '/*.txt', miscDst + '/')

    print('')

# Build all target documents
# repoDir = path to the Vulkan git repo containing the specs
# outDir = path to the output base directory in which targets are generated
def buildBranch(targetDir, extensions, apititle,
                xmlTargets, specTargets,
                repoDir, outDir, needRefSources = False):
    # Directory with vk.xml and generation tools
    xmlDir = repoDir + '/src/spec'
    # Directory with spec sources
    specDir = repoDir + '/doc/specs/vulkan'
    # Src/dst directories with misc. GLSL extension specs
    miscSrc = repoDir + '/doc/specs/misc'
    miscDst = outDir + '/misc'

    buildRelease(targetDir, extensions, outDir + '/' + targetDir,
                 apititle,
                 xmlDir, xmlTargets, specDir, specTargets,
                 miscSrc, miscDst, needRefSources)

# Commands to tag the git branches
# releaseNum = release number of this spec update, to tag the tree with
# tagdate = date (used to be used to tag the tree with)
def createTags(releaseNum, tagdate):
    # Tag date in YYYYMMDD format
    now = tagdate.strftime('%Y%m%d')

    print('echo To tag the spec branch for this release, execute the command:')
    print('echo git tag -a -m \\"Tag Vulkan API specification for 1.0.' +
          releaseNum, 'release\\"', 'v1.0.' + releaseNum + '-core')
    #print('echo git tag -a -m \\"Tag Vulkan API specification for', now,
    #      'release\\"', 'v1.0-core-' + now)

