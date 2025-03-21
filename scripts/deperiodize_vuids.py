#!/usr/bin/env python3
#
# Copyright 2020 Petr Kraus
#
# SPDX-License-Identifier: Apache-2.0

# Removes periods after Valid Usage sentence in the spec
#
# Usage:
# cd <root of Vulkan-Docs repo>
# ./scripts/deperiodize_vuids.py

import os,re

def deperiodizeFile(filename):
    print(f'    Deperiodizing = {filename}')

    with open(filename, 'r', encoding='utf8', newline='\n') as f:
        data = f.read()

    # Remove periods from VUs
    data = re.sub( r'(  \* \[\[VUID\-[\s\S]+?)\.?(?=(\n  \* \[\[VUID\-)|(\n\*\*\*\*)|(\n// )|(\ninclude::)|(\nendif::)|(\nifdef::)|(\nifndef::))', r'\g<1>', data )

    with open(filename, 'w', encoding='utf8', newline='\n') as f:
        data = f.write(data)

def deperiodizeFolder(folder):
    print(f'  Parsing = {folder}')
    for root, subdirs, files in os.walk(folder):
        for file in files:
            if file.endswith(".adoc"):
                file_path = os.path.join(root, file)
                deperiodizeFile(file_path)
        for subdir in subdirs:
            sub_folder = os.path.join(root, subdir)
            deperiodizeFolder(sub_folder)

if __name__ == '__main__':
    deperiodizeFolder(f"{os.getcwd()}/chapters")
    deperiodizeFolder(f"{os.getcwd()}/appendices")
