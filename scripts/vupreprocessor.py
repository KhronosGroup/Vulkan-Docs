#!/usr/bin/python3
#
# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Spawned by the vu-formatter asciidoctor extension, reads codified VUs from
stdin and outputs formatted VUs in stdout.

The following commands are accepted:

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

followed by either `FORMAT-VU-SUCCESS` or `FORMAT-VU-FAIL` based on whether the
VU formatting (and type checking) passed or failed.

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
from vuAST import isCodifiedVU, formatStrippedVU

def readCommand(end):
    result = []

    for line in sys.stdin:
        if line.rstrip() == end:
            break
        result.append(line.rstrip())

    return result

def processFormatCommand(command, registry):
    assert(len(command) >= 5)

    api = command[0]
    filename = command[1]
    lineNumber = int(command[2])
    attributes = command[3].split('$')
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
    formatted, passed = formatStrippedVU(vuText, api, filename, lineNumber, 4,
                                         registry, macros)

    print('FORMAT-VU')
    print(formatted)
    print('FORMAT-VU-SUCCESS' if passed else 'FORMAT-VU-FAIL')
    sys.stdout.flush()

if __name__ == '__main__':

    # Create the registry once at the beginning
    registryFile = os.path.join(Path(__file__).resolve().parent.parent, 'xml', 'vk.xml')
    registry = Registry()
    registry.loadFile(registryFile)

    for line in sys.stdin:
        if line.rstrip() == 'EXIT':
            break

        if line.rstrip() == 'FORMAT-VU':
            command = readCommand('FORMAT-VU-END')
            processFormatCommand(command, registry)
        else:
            print('Internal error: invalid command "' + line.rstrip() + '"')
            sys.stdout.flush()
            sys.exit(1)
