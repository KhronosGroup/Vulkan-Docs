#!/usr/bin/env python3
# Copyright 2026 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

"""nextfreebits.py - display free bits in one or all bitmask types

   Usage: nextfreebits.py [flagbitsname]"""

import argparse
import errno
import sys
import xml.etree.ElementTree as etree
from pathlib import Path
from apiconventions import APIConventions

# Mask types which have corresponding 64-bit versions.
# This is not tagged in the XML yet, and requires gymnastics to infer.
PROMOTED_MASK_TYPES = set((
    'VkAccessFlagBits',
    'VkPipelineStageFlagBits',
    'VkFormatFeatureFlagBits',
    'VkPipelineCreateFlagBits',
    'VkBufferUsageFlagBits',
))

class MaskInfo:
    """Information about free bits for a given bitmask type"""

    def __init__(self, name, bitwidth):
        self.name = ''
        self.usedBits = set()
        self.bitwidth = int(bitwidth)
        self.msg = ''
        self.numFree = 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-registry', action='store',
                        default=APIConventions().registry_path,
                        help=f'Use specified registry XML instead of {APIConventions().registry_path}')
    parser.add_argument('target', metavar='target', nargs='*',
                        default=[],
                        help='Specify flag bits type to report on')
    parser.add_argument('-minbits', action='store', type=int,
                        default = 64,
                        help='Only report on types with this many bits or fewer free')

    args = parser.parse_args()

    conventions = APIConventions()

    tree = etree.parse(args.registry)

    # Create dictionary with empty set of reserved bits for each "bitmask"
    # enums type, and track whether this is a 32- or 64-bit mask.
    enums = {}

    for elem in tree.findall('.//enums[@type="bitmask"]'):
        # Create a MaskInfo for each bitmask type found
        name = elem.get('name')
        bitwidth = elem.get('bitwidth', '32')

        enums[name] = MaskInfo(name, bitwidth)

        # Fill in initially allocated bits for the enum
        for enum in elem.findall('enum[@bitpos]'):
            bitpos = int(enum.get('bitpos'))
            enums[name].usedBits.add(bitpos)

    # Add each separately defined bit position
    for enum in tree.findall('.//require/enum'):
        bitpos = enum.get('bitpos')
        if bitpos is None:
            continue

        bitpos = int(bitpos)
        extends = enum.get('extends')
        name = enum.get('name', 'UNKNOWN')

        if bitpos is not None and extends is not None:
            if extends not in enums.keys():
                print('Unknown <enums extends="{extends}">', file=sys.stderr)
                sys.exit(1)

            enums[extends].usedBits.add(bitpos)

    # Validate specified mask names
    for name in args.target:
        if name not in enums:
            print(f'Specified target {name} is not a non-aliased bitmask type', file=sys.stderr)
            sys.exit(1)

    # For each type, determine the number of free bits and a text description of them
    for key in sorted(enums):
        # Only report on explicitly requested masks
        if len(args.target) > 0 and key not in args.target:
            # We do not care about this mask, so remove it
            del enums[key]
            continue

        # Track free bit ranges
        lastUsed = -1
        enums[key].msg = ''

        def reportFree(lastUsed, used):
            # Returns (number of free bits, descriptive string)

            if used == lastUsed + 1:
                # This is a contiguous range of used bits, and the lastUsed
                # free range, if any, has already been found.
                return (0, '')
            elif used == lastUsed + 2:
                # There is a single bit free, report it
                return (1, f'{lastUsed+1} ')
            else:
                # There are multiple bits free, report the range
                return (used - lastUsed -1, f'{lastUsed+1}-{used-1} ')

        for used in sorted(enums[key].usedBits):
            (freeBits, msg) = reportFree(lastUsed, used)
            if freeBits > 0:
                enums[key].numFree += freeBits
                enums[key].msg += msg
            lastUsed = used

        # Report bits following the last used bit
        used = enums[key].bitwidth
        # 32-bit masks cannot use the sign bit
        if used == 32:
            used = 31

        (freeBits, msg) = reportFree(lastUsed, used)
        if freeBits > 0:
            enums[key].numFree += freeBits
            enums[key].msg += msg
            # print(f'{key}: adding {freeBits} bits for free range ({lastUsed+1},{used-1})')

    # Generate summary report
    # Only display selected masks, if any were explicitly selected (already
    #   handled by removing non-selected masks from enums[])
    # Sort by number of free bits in each mask
    # Only display masks with <= specified minimum number of bits

    for name in sorted(enums.keys(), key = lambda k: enums[k].numFree):
        enum = enums[name]

        if enum.numFree <= args.minbits:
            if enum.numFree == 0:
                print(f'NO free bits for {name}')
            else:
                print(f'{enum.numFree} free bits for {name}: {enum.msg}')

            if name in PROMOTED_MASK_TYPES:
                print(f'    NOTE: {name} is a legacy 32-bit mask with a corresponding 64-bit type')

