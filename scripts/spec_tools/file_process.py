#!/usr/bin/python3
#
# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>
"Utilities for processing files."

from pathlib import Path


class LinewiseFileProcessor:
    """A base class for code that processes an input file (or file handle) one line at a time."""

    def __init__(self):
        self._lines = []
        self._line_num = 0
        self._next_line = None
        self._line = ''
        self._filename = Path()

    @property
    def filename(self):
        """The Path object of the currently processed file"""
        return self._filename

    @property
    def relative_filename(self):
        """The current file's Path relative to the current working directory"""
        return self.filename.relative_to(Path('.').resolve())

    @property
    def line(self):
        """The current line, including any trailing whitespace and the line ending."""
        return self._line

    @property
    def line_number(self):
        """Get 1-indexed line number."""
        return self._line_num

    @property
    def line_rstripped(self):
        """The current line without any trailing whitespace."""
        if self.line is None:
            return None
        return self.line.rstrip()

    @property
    def trailing_whitespace(self):
        """The trailing whitespace of the current line that gets removed when accessing rstrippedLine"""
        non_whitespace_length = len(self.line_rstripped)
        return self.line[non_whitespace_length:]

    @property
    def next_line(self):
        """Peek at the next line, if any."""
        return self._next_line

    @property
    def next_line_rstripped(self):
        """Peek at the next line, if any, without any trailing whitespace."""
        if self.next_line is None:
            return None
        return self.next_line.rstrip()

    def get_preceding_line(self, relative_index=-1):
        """Retrieve the line at an line number at the given relative index, if one exists. Returns None if there is no line there."""
        if relative_index >= 0:
            raise RuntimeError(
                'relativeIndex must be negative, to retrieve a preceding line.')
        if relative_index + self.line_number <= 0:
            # There is no line at this index
            return None
        return self._lines[self.line_number + relative_index - 1]

    def get_preceding_lines(self, num):
        """Get *up to* the preceding num lines. Fewer may be returned if the requested number aren't available."""
        return self._lines[- (num + 1):-1]

    def process_line(self, line_num, line):
        """Implement in your subclass to handle each new line."""
        raise NotImplementedError

    def _process_file_handle(self, file_handle):
        # These are so we can process one line earlier than we're actually iterating thru.
        processing_line_num = None
        processing_line = None

        def do_process_line():
            self._line_num = processing_line_num
            self._line = processing_line
            if processing_line is not None:
                self._lines.append(processing_line)
                self.process_line(processing_line_num, processing_line)

        for line_num, line in enumerate(file_handle, 1):
            self._next_line = line
            do_process_line()
            processing_line_num = line_num
            processing_line = line

        # Finally process the left-over line
        self._next_line = None
        do_process_line()

    def process_file(self, filename, file_handle=None):
        """Main entry point - call with a filename and optionally the file handle to read from."""
        if isinstance(filename, str):
            filename = Path(filename).resolve()

        self._filename = filename

        if file_handle:
            self._process_file_handle(file_handle)
        else:
            with self._filename.open('r', encoding='utf-8') as f:
                self._process_file_handle(f)
