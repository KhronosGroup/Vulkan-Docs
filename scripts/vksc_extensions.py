#!/usr/bin/env python3
#
# Copyright 2023-2024 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

import argparse
import xml.etree.ElementTree as etree
import pdb

def extensionInfoByName(name, extensionInfoList):

    for ext in extensionInfoList:
        if ext.get('name') == name:
            return ext

    return None


XMLFields = ['name', 'number', 'type', 'supported', 'depends', 'platform', 'ratified', 'author', 'contact', 'specialuse', 'promotedto', 'deprecatedby', 'obsoletedby', 'sortorder', 'provisional', 'comment']

def printHeader():
    sep = ";"
    for f in XMLFields:
        print(f, end=sep)
    print("")

def printExtXML(ext):
    sep = ";"
    for f in XMLFields:
        print(ext.get(f), end=sep),
    print("")


def printRatifiedHeader():
    print("name;number;xmlfield;vulkan;vulkansc;promotedto;deprecatedby")

def printRatified(ext):
    name = ext.get('name')
    number = ext.get('number')
    ratified = ext.get('ratified')
    vkrat = ratified is not None and 'vulkan' in ratified.split(',')
    vkscrat = ratified is not None and 'vulkansc' in ratified.split(',')

    promotedto = ext.get('promotedto')
    deprecatedby = ext.get('deprecatedby')
    if deprecatedby is None:
        deprecatedby = ext.get('obsoletedby')

    print(f'{name};{number};{ratified};{vkrat};{vkscrat};{promotedto};{deprecatedby}')

def dprint(*argv):
    if args.verbose:
        for arg in argv:
            print(arg, end=" ")
        print("")

def printExtnSorted(extnSet, printFunc=printExtXML):

    # dictionary of extensions, indexed by vendor prefix
    extnDict = {}

    for ext in extnSet:
        (vk, vendor) = ext.split('_')[0:2]

        if not vendor in extnDict:
            extnDict[vendor] = []
        extnDict[vendor].append(ext)

    # print KHR and EXT extensions first (sorted)
    for vendor in ['KHR', 'EXT']:
        if vendor in extnDict:
            for ext in sorted(extnDict[vendor]):
                printFunc(extensionInfoByName(ext, all_extensions))
            del extnDict[vendor]

    # print remaining extensions by vendor (sorted)
    for vendor in sorted(extnDict.keys()):
        for ext in sorted(extnDict[vendor]):
            printFunc(extensionInfoByName(ext, all_extensions))
        del extnDict[vendor]



if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='vksc_extensions',
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description='''\
Loads VK/VKSC extensions from the API XML.
Filters out elements with non-matching explicit 'api' attributes from API XML.
Print various lists of extensions with attributes in semicolon separated lists.
    ''')

    parser.add_argument('-input', action='store',
                        required=True,
                        help='Specify input registry XML')
    parser.add_argument('-verbose', '-v', action='count', default=0,
                        help='print debug output')
    parser.add_argument('-candidates', action='store_true',
                        help="Print Vulkan SC candidate extension lists")
    parser.add_argument('-list-vksc', action='store_true',
                        help="Print Vulkan SC current extension list")
    parser.add_argument('-ratify', action='store_true',
                        help="Print Vulkan SC ratification status lists")
#    parser.add_argument('-output', action='store',
#                        required=True,
#                        help='Specify output registry XML')
#    parser.add_argument('-keepAPI', action='store',
#                        default=None,
#                        help='Specify API name whose \'api\' tags are kept')

    args = parser.parse_args()
#    print(args)

    tree = etree.parse(args.input)

    root = tree.getroot()
    all_extensions = list()
    vk_extensions = list()
    vksc_extensions = list()
    candidate_set = set()
    already_in_set = set()
    platform_set = set()

    for extension in root.find('extensions'):
        #print(extension.tag, extension.attrib)
        supported = extension.attrib.get('supported')
        #print(supported)

        all_extensions.append(extension.attrib)

        if 'vulkan' in supported.split(','):
            vk_extensions.append(extension.attrib)
            candidate_set.add(extension.attrib.get('name'))
        if 'vulkansc' in supported.split(','):
            vksc_extensions.append(extension.attrib)
            already_in_set.add(extension.attrib.get('name'))

        platform = extension.attrib.get('platform')
        if platform is not None:
            #print(platform)
            platform_set.add(platform)

        for field in extension.attrib.items():
            if field[0] not in XMLFields:
                print("WARNING unhandled XML extension attribute field:", field[0])

    print("all vulkan extensions:", len(vk_extensions))
    print("all vulkan sc extensions:", len(vksc_extensions))
    print("platforms", platform_set)

    #for ext in vk_extensions: print(ext)

    # generate set of extensions that are in Vulkan but not in Vulkan SC
    vksc_candidates = candidate_set - already_in_set
    if args.verbose:
        print("initial candidate list", len(vksc_candidates))
        print("-----------------")
        for ext in vksc_candidates: print(ext)
        print("-----------------")

    promoted_cores = ['VK_VERSION_1_0', 'VK_VERSION_1_1', 'VK_VERSION_1_2']
    future_cores = ['VK_VERSION_1_3']
    unsupported_platforms = ['xlib', 'xcb', 'wayland', 'win32', 'xlib_xrandr',
                             'android', 'ggp', 'vi', 'fuchsia', 'directfb',
                             'provisional', 'macos', 'ios', 'metal']
    removals = set()
    future_core = set()
    for ext in vksc_candidates:
        info = extensionInfoByName(ext, vk_extensions)
        promotedto = info.get('promotedto')
        deprecatedby = info.get('deprecatedby')
        if deprecatedby is None:
            deprecatedby = info.get('obsoletedby')
        platform = info.get('platform')

        # remove any that are promoted to a core version included in VKSC
        if promotedto in promoted_cores:
            removals.add(ext)
            dprint("removing promoted core extension:", ext)
        # remove any that are promoted to another candidate
        elif promotedto in vksc_candidates:
            removals.add(ext)
            dprint("removing promoted to another candidate", ext)
        # separate list for any promoted to a future core
        elif promotedto in future_cores:
            future_core.add(ext)
            dprint("promoted to future core", ext)
        # exceptional promotions
        elif promotedto is not None:
            # remove any that are promoted to an existing VKSC extension
            vksc_info = extensionInfoByName(promotedto, vksc_extensions)
            if vksc_info is not None:
                removals.add(ext)
                dprint("removing promoted to other VKSC extn", ext)
            else:
                print("unhandled promotedto", ext)

        # remove any that are deprecated by a core version included in VKSC
        elif deprecatedby in promoted_cores:
            removals.add(ext)
            dprint("removing deprecated by core extension:", ext)
        # remove any that are deprecated by another candidate
        elif deprecatedby in vksc_candidates:
            removals.add(ext)
            dprint("removing deprecated by another candidate", ext)
        # remove any that are deprecated without replacement
        elif deprecatedby == '':
            removals.add(ext)
            dprint("removing deprecated without replacement", ext)
        # exceptional deprecations
        elif deprecatedby is not None:
            vksc_info = extensionInfoByName(deprecatedby, vksc_extensions)
            # remove any that are deprecated by an existing VKSC extension
            if vksc_info is not None:
                removals.add(ext)
                dprint("removing deprecated by other VKSC extn", ext)
            else:
                print("unhandled deprecated", ext)

        # remove any that require a platform that is not supported for VKSC
        elif platform in unsupported_platforms:
            removals.add(ext)
            dprint("removing due to unsupported platform:", ext, platform)

        #else:
            #print("keeping candidate:", ext, info)

    vksc_candidates -= removals
    vksc_candidates -= future_core

    if args.candidates:
        print("-----------------")
        print("future core promotion candidates", len(future_core))
        print("-----------------")
        printHeader()
        printExtnSorted(future_core)

        print("-----------------")
        print("vulkansc extension candidates", len(vksc_candidates))
        print("-----------------")
        printExtnSorted(vksc_candidates)

    if args.ratify:
        print("-----------------")
        print("ratification status for all vulkansc extensions:", len(vksc_extensions))
        print("-----------------")
        printRatifiedHeader()
        printExtnSorted(already_in_set, printRatified)

    if args.list_vksc:
        print("-----------------")
        print("all vulkansc extensions:", len(vksc_extensions))
        print("-----------------")
        printHeader()
        printExtnSorted(already_in_set)


