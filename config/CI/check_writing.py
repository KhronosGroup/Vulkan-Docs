#!/usr/bin/env python3
#
# Copyright 2026 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# check_writing.py - search files to detect violations of some writing and
# markup rules, and give explanations thereof.
#
# Usage: config/CI/check_writing.py files / directories
#
# This is broken out as a separate script because trying to include the
# many complicated regular expressions and explanations / links in the
# Makefile would be too verbose.

import argparse
import subprocess
import sys

# The Vulkan "Style Guide" where writing rules are defined
styleguideURL = 'https://registry.khronos.org/vulkan/specs/latest/styleguide.html'

# Each rule has [ regular expression, text explanation, style guide anchor ]
Rules = [
    [
        r'(^|[^[:alnum:]])[Aa]n ename:[Vv]',
        'Use A/An correctly with markup macros',
        'writing-misc-a-an',
    ],
    [
        r'pname:sType is the type of this structure.',
        'Use boilerplate: "pname:sType is a elink:VkStructureType value identifying this structure."',
        'sample-command-sType-pNext',
    ],
    [
        r'pname:pNext is `NULL` or a pointer to an extension-specific structure.',
        'Use boilerplate: "pname:pNext is `NULL` or a pointer to a structure extending this structure"',
        'sample-command-sType-pNext',
    ],
    [
        r'pname:pNext(-chain|extension chain)|[^:>.]pNext chain',
        'Use markup macro and preferred spelling: "pname:pNext chain"',
        'spelling-exception-table',
    ],
    [
        r'pname:p[A-Z][[:alnum:]]+ is an array of',
        'Use "is a pointer to an array of"',
        'writing-pointers-instances',
    ],
    [
        r'present in.*the pname:pNext chain',
        'Use "included in the pname:pNext chain',
        'writing-pNext-chain',
    ],
    [
        r'(^|[^-_.&:<>\[[:alnum:]])(Github|[Aa]ny given element|[Cc]olorspace)($|[^-_.\[[:alnum:]])',
        'Use preferred orthography for compound words',
        'writing-compound-words',
    ],
    # One contraction in this regexp, 'app' in markup-avoid-contractions
    # section - can be caught by spellcheck?
    [
        r'(^|[^-_.&:<>\[[:alnum:]])([Aa]ny hit|[Aa]pp |[Ff]loating [Pp]oint|[Gg]eneral purpose|[Ii]mplementation dependent|is an optional pointer|[Ll]evel [Oo]f [Dd]etail|lod)($|[^-_.\[[:alnum:]])',  # codespell:ignore oint
        'Use preferred orthography for compound words',
        'writing-compound-words',
    ],
    [
        r'(^|[^-_.&:<>\[[:alnum:]])([Mm]iplevel|points to|[Rr]enderpass|[Rr]un time|[Ss]ide-effect|[Ss]ignalled|[Ss]wap chain|[Tt]esselation|[Uu]se-case)($|[^-_.\[[:alnum:]])',
        'Use preferred orthography for compound words',
        'writing-compound-words',
    ],
    [
        r'<<features-[^>]+>> (are|is|is not) (enabled|supported)',
        'Use markup "<<features-name, feature name>> feature is enabled / is not enabled / is disabled"',
        'markup-word-choices',
    ],
    [
        r'<<features-[^>]+ feature>>',
        'Use markup "<<features-name, feature name>> feature is enabled / is not enabled / is disabled"',
        'markup-word-choices',
    ],
    [
        r'must: (not |)be set to',
        'Use markup "must: be _value_"',
        'writing-mustbe',
    ],
    [
        r'\* ename:[^ ]+ (indicate|denote)',
        'Use markup "ename:NAME specifies"',
        'markup-word-choices',
    ],
    [
        r'the currently bound',
        'Use markup "bound" without "currently"',
        'markup-word-choices',
    ],
    [
        r'^\.Note$',
        'Do not use the ".Note" markup on [NOTE] blocks',
        'markup-informative-notes',
    ],
    [
        r'^or the equivalent',
        'Do not use "or the equivalent" when describing promoted or aliased APIs',
        'markup-word-choices',
    ],
    [
        r'equal to or (greater|less|larger|smaller) than|(larger|smaller) than or equal to',
        'Use "equal to or (greater/less) than"',
        'writing-math',
    ],
]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('files', metavar='filename', nargs='*',
                        help='File names to check for writing mistakes')

    args = parser.parse_args()

    # Did any of the pattern checks find matches (e.g. error)?
    error_return = 0

    for (pattern, explanation, anchor) in Rules:
        # Whitespace in rules is converted to allow multiline matches using ripgrep (rg)
        rgpattern = pattern.replace(' ', r'(\n| +)')

        testcase = 'testcase'
        command = [
            'rg',
            '-n',
            '-U',
            '-e',
            rgpattern,
        ] + args.files

        results = subprocess.run(command,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        if results.returncode == 0:
            # Matches were found. Print them with an explanation
            print(f'** Writing error(s) found: {explanation} - see {styleguideURL}#{anchor} for details')
            print(results.stdout.decode())

            error_return = 1
        elif results.returncode == 2:
            # ripgrep error
            print(f'rg (ripgrep) error found, exiting test script:', file=sys.stderr)
            print(results.stderr.decode())

            error_return = 1
        else:
            # ripgrep did not find matches
            True

    sys.exit(error_return)
