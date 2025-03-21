#!/usr/bin/env python3
#
# Copyright (c) 2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Rylie Pavlik <rylie.pavlik@collabora.com>
#
# Purpose:      This script converts leading comments on some Python
#               classes and functions into docstrings.
#               It doesn't attempt to deal with line continuations, etc.
#               so you may want to "join line" on your def statements
#               temporarily before running.

import re

from spec_tools.file_process import LinewiseFileProcessor

COMMENT_RE = re.compile(r" *#(!.*| (?P<content>.*))?")
CONVERTIBLE_DEF_RE = re.compile(r"(?P<indentation> *)(def|class) .*:")


class CommentConverter(LinewiseFileProcessor):
    def __init__(self, single_line_quotes=False, allow_blank_lines=False):
        super().__init__()
        self.comment_lines = []
        "Temporary storage for contiguous comment lines."

        self.trailing_empty_lines = []
        "Temporary storage for empty lines following a comment."

        self.output_lines = []
        "Fully-processed output lines."

        self.single_line_quotes = single_line_quotes
        "Whether we generate simple, single-line quotes for single line comments."

        self.allow_blank_lines = allow_blank_lines
        "Whether we allow blank lines between a comment and the thing it's considered to document."

        self.done_with_initial_comment = False
        "Have we read our first non-comment line yet?"

    def output_line(self, line=None):
        if line:
            self.output_lines.append(line)
        else:
            self.output_lines.append("")

    def output_normal_line(self, line):
        # flush any comment lines we had stored and output this line.
        self.dump_comment_lines()
        self.output_line(line)

    def dump_comment_lines(self):
        # Early out for empty
        if not self.comment_lines:
            return

        for line in self.comment_lines:
            self.output_line(line)
        self.comment_lines = []

        for line in self.trailing_empty_lines:
            self.output_line(line)
        self.trailing_empty_lines = []

    def dump_converted_comment_lines(self, indent):
        # Early out for empty
        if not self.comment_lines:
            return

        for line in self.trailing_empty_lines:
            self.output_line(line)
        self.trailing_empty_lines = []

        indent = f"{indent}    "

        def extract(line):
            match = COMMENT_RE.match(line)
            content = match.group('content')
            if content:
                return content
            return ""

        # Extract comment content
        lines = [extract(line) for line in self.comment_lines]

        # Drop leading empty comments.
        while lines and not lines[0].strip():
            lines.pop(0)

        # Drop trailing empty comments.
        while lines and not lines[-1].strip():
            lines.pop()

        # Add single- or multi-line-string quote
        if self.single_line_quotes \
            and len(lines) == 1 \
                and '"' not in lines[0]:
            quote = '"'
        else:
            quote = '"""'
        lines[0] = quote + lines[0]
        lines[-1] = lines[-1] + quote

        # Output lines, indenting content as required.
        for line in lines:
            if line:
                self.output_line(indent + line)
            else:
                # Don't indent empty comment lines
                self.output_line()

        # Clear stored comment lines since we processed them
        self.comment_lines = []

    def queue_comment_line(self, line):
        if self.trailing_empty_lines:
            # If we had blank lines between comment lines, they are separate blocks
            self.dump_comment_lines()
        self.comment_lines.append(line)

    def handle_empty_line(self, line):
        """Handle an empty line.

        Contiguous empty lines between a comment and something documentable do not
        disassociate the comment from the documentable thing.
        We have someplace else to store these lines in case there isn't something
        documentable coming up."""
        if self.comment_lines and self.allow_blank_lines:
            self.trailing_empty_lines.append(line)
        else:
            self.output_normal_line(line)

    def is_next_line_doc_comment(self):
        next_line = self.next_line_rstripped
        if next_line is None:
            return False

        return next_line.strip().startswith('"')

    def process_line(self, line_num, line):
        line = line.rstrip()
        comment_match = COMMENT_RE.match(line)
        def_match = CONVERTIBLE_DEF_RE.match(line)

        # First check if this is a comment line.
        if comment_match:
            if self.done_with_initial_comment:
                self.queue_comment_line(line)
            else:
                self.output_line(line)
        else:
            # If not a comment line, then by definition we're done with the comment header.
            self.done_with_initial_comment = True
            if not line.strip():
                self.handle_empty_line(line)
            elif def_match and not self.is_next_line_doc_comment():
                # We got something we can make a docstring for:
                # print the thing the docstring is for first,
                # then the converted comment.

                indent = def_match.group('indentation')
                self.output_line(line)
                self.dump_converted_comment_lines(indent)
            else:
                # Can't make a docstring for this line:
                self.output_normal_line(line)

    def process(self, fn, write=False):
        self.process_file(fn)

        if write:
            with open(fn, 'w', encoding='utf-8') as fp:
                for line in self.output_lines:
                    fp.write(line)
                    fp.write('\n')

        # Reset state
        self.__init__(self.single_line_quotes, self.allow_blank_lines)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', metavar='filename',
                        type=str, nargs='+',
                        help='A Python file to transform.')
    parser.add_argument('-b', '--blanklines', action='store_true',
                        help='Allow blank lines between a comment and a define and still convert that comment.')

    args = parser.parse_args()

    converter = CommentConverter(allow_blank_lines=args.blanklines)
    for fn in args.filenames:
        print("Processing", fn)
        converter.process(fn, write=True)


if __name__ == "__main__":
    main()
