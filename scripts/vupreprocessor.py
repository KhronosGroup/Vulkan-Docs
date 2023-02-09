#!/usr/bin/env python3
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Spawned by the vu-formatter asciidoctor extension, reads codified VUs from
stdin and outputs formatted VUs in stdout.

The following commands are accepted:

- The list of versions and extensions to build:

```
VERSIONS
version version ...
extension extension ...
VERSIONS-END

In response to the above, the following is returned:

```
VERSIONS-SUCCESS
```

This command is not expected to fail.

- A request to format a VU:

```
FORMAT-VU
api
filename
lineNumber
attr1$value1$attr2$value2$...
vu text
FORMAT-VU-END
```

In response to the above, the following is returned:

```
messages (warnings/errors)
FORMAT-VU
formatted vu text
```

followed by either `FORMAT-VU-SUCCESS`, `FORMAT-VU-FAIL`, or
`FORMAT-VU-ELIMINATED` based on whether the VU formatting (and type checking)
passed or failed and whether the VU is eliminated for this build.

- A request to end the process:

```
EXIT
```

After this message, the process exits.
"""

import os
from pathlib import Path
import sys

from reg import Registry
from reflib import logDiag, logWarn, logErr
from vuAST import createAliasMap, createSymbolAvailabilityMap
from vuAST import isCodifiedVU, parseAndVerifyVU, VuFormat, VuFormatter, VuSourceStyler
from vubuildstrip import VuStripDeadCode, stripVUForBuild


def readCommand(end):
    result = []

    for line in sys.stdin:
        if line.rstrip() == end:
            break
        result.append(line.rstrip())

    return result


def verifyNoDeadCode(vu, vuText):
    dce = VuStripDeadCode(vu.astExpanded)
    stripped, anyDCE = dce.strip()

    if not anyDCE:
        return

    logWarn(vu.filename + ':' + str(vu.fileline) + ': VU has dead code')
    logWarn('Original VU:')
    logWarn('\n' + '\n'.join(vuText))
    logWarn('VU after dead code elimintation:')
    if stripped is None:
        logWarn('<empty>')
    else:
        formatter = VuFormatter(VuSourceStyler('', 0))
        logWarn('\n' + formatter.format(stripped))


def respondFormat(result, status):
    return ['FORMAT-VU'] + result + ['FORMAT-VU-' + status]


def processVersionsCommand(command, registry):
    assert(len(command) == 2)

    versions = command[0].split(' ')
    extensions = command[1].split(' ') if len(command[1]) > 0 else []

    return ['VERSIONS-SUCCESS'], versions, extensions


def processFormatCommand(command, registry, versions, extensions, featureAvailability, structAvailability, enumAvailability):
    assert(len(command) >= 5)

    api = command[0]
    filename = command[1]
    lineNumber = int(command[2])
    attributes = command[3].split('$') if len(command[3]) > 0 else []
    vuText = command[4:]

    # Turn the `attr1 value1 attr2 value2 ...` list into a dictionary
    assert(len(attributes) % 2 == 0)
    macros = {attributes[i]: attributes[i+1]
                  for i in range(0, len(attributes), 2)}

    # Only codified VUs should be passed here.  The VUID tag, if any, is
    # stripped by vu-formatter.rb
    assert(isCodifiedVU(vuText))

    # Note: VUs have 4 characters of spacing in the source.  That is
    # communicated so that error messages would have the correct "column".
    vu = parseAndVerifyVU(vuText, api, filename, lineNumber, 4,
                                         registry, macros)
    if vu is None:
        return respondFormat(vuText, 'FAIL')

    # Run dead code elimination on the original VU.  If any eliminations,
    # complain that the VU has dead code.
    verifyNoDeadCode(vu, vuText)

    stripped = stripVUForBuild(vu, versions, extensions, featureAvailability, structAvailability, enumAvailability)

    # If nothing left of the VU, signify that
    if stripped is None:
        return respondFormat([], 'ELIMINATED')

    vu.astExpanded = stripped
    formatted = vu.format(VuFormat.OUTPUT, registry)
    formattedText = vu.formatText(registry)

    return respondFormat([formatted, 'FORMAT-VU-TEXT', formattedText], 'SUCCESS')


if __name__ == '__main__':

    # Create the registry once at the beginning
    registryFile = os.path.join(Path(__file__).resolve().parent.parent, 'xml', 'vk.xml')
    registry = Registry()
    registry.loadFile(registryFile)

    aliasMap = createAliasMap(registry)
    featureAvailability, structAvailability, enumAvailability = createSymbolAvailabilityMap(registry, aliasMap)

    for line in sys.stdin:
        if line.rstrip() == 'EXIT':
            break

        if line.strip() == 'VERSIONS':
            command = readCommand('VERSIONS-END')
            response, versions, extensions = processVersionsCommand(command, registry)

        elif line.rstrip() == 'FORMAT-VU':
            command = readCommand('FORMAT-VU-END')
            response = processFormatCommand(command, registry, versions, extensions, featureAvailability, structAvailability, enumAvailability)

        else:
            print('Internal error: invalid command "' + line.rstrip() + '"')
            sys.stdout.flush()
            sys.exit(1)

        print('\n'.join(response))
        sys.stdout.flush()
