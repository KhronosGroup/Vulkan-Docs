#!/usr/bin/python3
#
# Copyright 2016-2024 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

"""Detect duplicate consecutive words in spec markup.

Usage: `find_duplicate.py [-warn] files`

Displays duplicates and (with -warn) near-duplicates found.
Exits with error status if any duplicates are found.

Tries to handle cases like operator names ("OR or AND") and spec macros
("the device pname:device").

- `files` are asciidoc source files from the spec to reflow.
"""

# For error and file-loading interfaces only
import argparse
import os
import re
import string
import sys
from reflib import loadFile

# Find asciidoc macro prefixes in a 'word'
prefixPat = re.compile(r'^(?P<prefix>([defpst](link|text|name)|basetype|code|tag|attr):|)(?P<word>[A-Za-z].*)')

# Asciidoctor directives to skip
adocDirectives = (('include::', 'ifdef::', 'ifndef::', 'endif::'))

def findDuplicateWords(filename, args):
    """Detect and report duplicate, consecutive words in filename.
       Returns count of duplicates found."""

    lines, _ = loadFile(filename)
    if lines is None:
        return 0

    duplicateCount = 0
    lastWord = lastWordNormalized = lastWordPrefix = None
    lineNumber = 1

    for line in lines:
        line = line.rstrip()

        # Early termination conditions
        skipLine = False

        # Empty lines
        if len(line) == 0:
            skipLine = True

        # Asciidoctor directives
        if not skipLine:
            for pat in adocDirectives:
                if line.startswith(pat):
                    skipLine = True
                    break

        # Ignore this line, and reset tracking of the previous word
        if skipLine is True:
            lastWord = lastWordNormalized = lastWordPrefix = None
            lineNumber += 1
            continue

        line = line.rstrip()
        words = line.strip().split()

        numWords = len(words) - 1
        for word in words:
            # Strip out leading asciidoc macro prefixes and just look at the
            # remaining leading alphanumeric portion of the string.
            matches = prefixPat.search(word)
            if matches is not None:
                wordNormalized = matches.group('word')

                # Decapitalize words, but leave all upper case words alone
                if wordNormalized[0].isupper() and wordNormalized[1:2].islower():
                    wordNormalized = wordNormalized[0].lower() + wordNormalized[1:]

                wordPrefix = matches.group('prefix')
            else:
                wordNormalized = ''
                wordPrefix = ''

            if wordNormalized == lastWordNormalized and wordNormalized != '':
                # Allow the case where 'word macro:word' or vice-versa is present
                if wordPrefix == lastWordPrefix:
                    print(f'ERROR: {filename} line {lineNumber}: Found duplicate "{lastWord}" ~= "{word}"')
                    duplicateCount += 1
                elif args.warn:
                    print(f'WARNING: {filename} line {lineNumber}: Found very similar words "{lastWord}" "{word}"')

            # If this word ends in punctuation, the following can be a duplicate
            if word[-1:] in string.punctuation:
                lastWord = lastWordNormalized = lastWordPrefix = None
            else:
                lastWord = word
                lastWordNormalized = wordNormalized
                lastWordPrefix = wordPrefix

        lineNumber += 1

    return duplicateCount

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-warn', action='store_true',
                        help='Report nearly-identical successive words')
    parser.add_argument('files', metavar='filename', nargs='*',
                        help='a filename to reflow text in')

    args = parser.parse_args()

    # Count of markup check warnings encountered
    duplicateCount = 0

    for file in args.files:
        duplicateCount += findDuplicateWords(file, args)

    if duplicateCount > 0:
        print(f'{duplicateCount} duplicate consecutive words found, failing')
        sys.exit(1)
