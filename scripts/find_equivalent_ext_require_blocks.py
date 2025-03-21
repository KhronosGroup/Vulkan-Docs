#!/usr/bin/env python3
#
# Copyright 2024 Waffl3x
# SPDX-License-Identifier: Apache-2.0

import xml.etree.ElementTree as etree
import itertools

tree = etree.parse('vk.xml')
doc = tree.getroot()

extensions = doc.find('extensions')

def check_if_children_equal(req1, req2):
    if len(req1) != len(req2):
        return False
    for child1, child2 in zip(req1, req2):
        if child1.tag != child2.tag:
            return False
        if child1.attrib != child2.attrib:
            return False
    return True
# def check_if_children_equal

for ext in extensions:
    req_with_depends = []
    # put all candidates into a list
    for req, count in zip(ext, itertools.count()):
        if 'depends' in req.attrib:
            req_with_depends.append((req, count))
    
    # compare candidates in a pairwise manner
    for tup1, it2_start in zip(req_with_depends[:-1], range(1, len(req_with_depends))):
        for tup2 in req_with_depends[it2_start:]:
            req1, req_count1 = tup1
            req2, req_count2 = tup2
            all_match = check_if_children_equal(req1, req2)
            if all_match:
                print(f"Found matching require block in extension {ext.attrib['name']}:")
                print(f'blocks {req_count1} and {req_count2} are equal')
                print(f'require block {req_count1} attributes: {req1.attrib}')
                print(f'require block {req_count2} attributes: {req2.attrib}')
                print('  block children:')
                for child1, child2 in zip(req1, req2):
                    print('    ', req_count1, ': ', child1.attrib)
                    print('    ', req_count2, ': ', child2.attrib)
