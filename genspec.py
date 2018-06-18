#!/usr/bin/python3
#
# Copyright (c) 2016-2018 The Khronos Group Inc.
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
# versions = list of core API versions to include
# extensions = list of extension names to include
# ratified = True if this is a ratified spec (one built without non-KHR
#            extensions)
# outdir = directory to generate specs in
# apititle = extra title to apply to the specification
# xmlDir = directory containing registry XML
# xmlTargets = targets to build in xml/
# specDir = directory containing spec source & Makefile
# specTargets = targets to build
# miscSrc = path to copy misc files from, if non-None
# miscDst = path to copy misc files to, if non-None
# needRefSources = True if ref pages must be extracted from the spec sources
def buildRelease(label,
                 versions,
                 extensions,
                 ratified,
                 outdir,
                 apititle,
                 xmlDir, xmlTargets,
                 specDir, specTargets,
                 miscSrc = None, miscDst = None, needRefSources = False):

    print('echo Info: Generating target=' + label,
          'outdir=' + outdir)

    outarg = 'OUTDIR=' + outdir

    if (versions != None and len(versions) > 0):
        versarg = 'VERSIONS="' + ' '.join(versions) + '"'
    else:
        versarg = ''

    if (extensions != None and len(extensions) > 0):
        extarg = 'EXTENSIONS="' + ' '.join(extensions) + '"'
    else:
        extarg = ''

    if ratified:
        ratifiedarg = 'EXTRAATTRIBS="-a ratified_core_spec"'
    else:
        ratifiedarg = ''

    if (apititle != None):
        titlearg = 'APITITLE="' + apititle + '"'
    else:
        titlearg = ''

    # print('echo Info: Creating directory and cleaning spec in', outdir)
    print('mkdir -p', outdir)
    print('(cd ', outdir, '&& rm -rf',
          'html chunked pdf',
          'man config checks',
          'vkspec.html styleguide.html apispec.html apispec.pdf registry.html',
          ')')

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
        print('make', outarg, versarg, extarg, 'man/apispec.txt')
    # Now make the actual targets.
    print('make -O -k -j 8',
          outarg, versarg, extarg, ratifiedarg, titlearg,
          'NOTEOPTS="-a implementation-guide"',
          specTargets)

    if (miscSrc != None and miscDst != None):
        print('mkdir -p', miscDst)
        print('cp', miscSrc + '/*.txt', miscDst + '/')

    print('')

# Build all target documents
# repoDir = path to the Vulkan git repo containing the specs
# outDir = path to the output base directory in which targets are generated
def buildBranch(targetDir,
                versions,
                extensions,
                ratified,
                apititle,
                xmlTargets,
                specTargets,
                repoDir,
                outDir,
                needRefSources = False):

    # Directory with vk.xml and generation tools
    xmlDir = repoDir + '/xml'
    # Directory with spec sources
    specDir = repoDir
    # Directory containing misc. files to copy to registry.
    # At present there are none, since GLSL extensions have moved to the
    # GLSL repository and are redirected from the Vulkan registy website.
    # These should be relative to repoDir and outDir, respectively
    miscSrc = None
    miscDst = None

    buildRelease(targetDir,
                 versions,
                 extensions,
                 ratified,
                 outDir + '/' + targetDir,
                 apititle,
                 xmlDir, xmlTargets,
                 specDir, specTargets,
                 miscSrc, miscDst,
                 needRefSources)

# Commands to tag the git branches
# releaseNum = release number of this spec update, to tag the tree with
# tagdate = date (used to be used to tag the tree with)
def createTags(releaseNum, tagdate):
    # Tag date in YYYYMMDD format
    now = tagdate.strftime('%Y%m%d')

    print('echo To tag the spec branch for this release, execute the command:')
    print('echo git tag -a -m \\"Tag Vulkan API specification for 1.1.' +
          releaseNum, 'release\\"', 'v1.1.' + releaseNum)
