#!/usr/bin/python3

import time
from datetime import timedelta, date

# These can be changed to tags, etc.
coreBranch = '1.0'
wsiBranch = '1.0-wsi_extensions'

# This script builds a full release package including XHTML and PDF
# versions of the specified branches (usually 1.0 and 1.0-wsi_extensions,
# but tags or commits can be used as well). Other files in the release
# directory are removed, including man pages, XHTML chunked, HTML,
# validity output, etc.
#
# Both branches must be fully committed and up to date when the script
# is run, with no outstanding un-added / un-committed files. Both
# branches must have fully regenerated all automatically generated
# files. After completing the build, the current branch is set to
# the first (core) branch and suggestions for creating tags are printed out.

# Return a date for the current, or upcoming if not already, Friday,
# which is when releases happen
def buildOnFriday():
    today = date.today()
    friday = today + timedelta((4 - today.weekday()) % 7)
    return friday

# branch = branch or commit or tag name
# label = textual label to apply
# outdir = directory to generate specs in
# xmlDir = directory containing registry XML
# xmlTargets = targets to build in src/spec/
# specDir = directory containing spec source & Makefile
# specTargets = targets to build in doc/specs/vulkan/
# miscSrc = path to copy misc files from, if non-None
# miscDst = path to copy misc files to, if non-None
def buildRelease(branch, label, outdir,
                 xmlDir, xmlTargets,
                 specDir, specTargets,
                 miscSrc = None, miscDst = None):
    print('echo Info: Generating branch=' + branch,
          'label=' + label,
          'outdir=' + outdir)
    print('git checkout', branch)

    print('echo Info: Cleaning spec in', outdir)
    print('cd', specDir)
    print('rm -rf',
          outdir + '/man',
          outdir + '/xhtml',
          outdir + '/pdf',
          outdir + '/chunked',
          outdir + '/style',
          outdir + '/vkspec.html',
          outdir + '/styleguide.html',
          outdir + '/apispec.*',
          outdir + '/readme.pdf',
          'specversion.txt')

    print('echo Info: Generating headers and spec include files')
    print('cd', xmlDir)
    print('make OUTDIR=' + outdir, xmlTargets)

    print('echo Info: Generating spec')
    print('cd', specDir)
    print('make specversion.txt')
    print('make -j 4 OUTDIR=' + outdir, ' NOTEOPTS="-a implementation-guide"',
          specTargets)
    print('rm', outdir + '/pdf/vkspec.xml')
    print('echo Reverting vkapi.py to prevent churn')
    print('git checkout -- vkapi.py')

    if (miscSrc != None and miscDst != None):
        print('cp', miscSrc + '/*.txt', miscDst + '/')


# Build all target branches
# repoDir = path to the Vulkan git repo containing the specs
# outDir = path to the output base directory in which each branch is generated
def buildBranch(branch, xmlTargets, specTargets, repoDir, outDir):
    # Directory with vk.xml and generation tools
    xmlDir = repoDir + '/src/spec'
    # Directory with spec sources
    specDir = repoDir + '/doc/specs/vulkan'
    # Src/dst directories with misc. GLSL extension specs
    miscSrc = repoDir + '/doc/specs/misc'
    miscDst = outDir + '/misc'

    buildRelease(branch, branch, outDir + '/' + branch,
                 xmlDir, xmlTargets, specDir, specTargets,
                 miscSrc, miscDst)

# Commands to tag the git branches
# tagdate = date to tag the tree with when done
def createTags(tagdate):
    global coreBranch, wsiBranch

    # Tag date in YYYYMMDD format
    now = tagdate.strftime('%Y%m%d')

    print('echo To tag the spec branches, execute these commands:')
    print('echo git checkout', coreBranch)
    print('echo git tag -a -m \\"Tag core API specification for', now,
          'release\\"', 'v1.0-core-' + now)

    print('echo git checkout', wsiBranch)
    print('echo git tag -a -m \\"Tag core+WSI API specification for', now,
          'release\\"', 'v1.0-core+wsi-' + now)


