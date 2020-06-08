"""Provides a re-usable command-line interface to a MacroChecker."""

# Copyright (c) 2018-2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>


import argparse
import logging
import re
from pathlib import Path

from .shared import MessageId


def checkerMain(default_enabled_messages, make_macro_checker,
                all_docs, available_messages=None):
    """Perform the bulk of the work for a command-line interface to a MacroChecker.

    Arguments:
    default_enabled_messages -- The MessageId values that should be enabled by default.
    make_macro_checker -- A function that can be called with a set of enabled MessageId to create a
      properly-configured MacroChecker.
    all_docs -- A list of all spec documentation files.
    available_messages -- a list of all MessageId values that can be generated for this project.
      Defaults to every value. (e.g. some projects don't have MessageId.LEGACY)
    """
    enabled_messages = set(default_enabled_messages)
    if not available_messages:
        available_messages = list(MessageId)

    disable_args = []
    enable_args = []

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scriptlocation",
        help="Append the script location generated a message to the output.",
        action="store_true")
    parser.add_argument(
        "--verbose",
        "-v",
        help="Output 'info'-level development logging messages.",
        action="store_true")
    parser.add_argument(
        "--debug",
        "-d",
        help="Output 'debug'-level development logging messages (more verbose than -v).",
        action="store_true")
    parser.add_argument(
        "-Werror",
        "--warning_error",
        help="Make warnings act as errors, exiting with non-zero error code",
        action="store_true")
    parser.add_argument(
        "--include_warn",
        help="List all expected but unseen include files, not just those that are referenced.",
        action='store_true')
    parser.add_argument(
        "-Wmissing_refpages",
        help="List all entities with expected but unseen ref page blocks. NOT included in -Wall!",
        action='store_true')
    parser.add_argument(
        "--include_error",
        help="Make expected but unseen include files cause exiting with non-zero error code",
        action='store_true')
    parser.add_argument(
        "--broken_error",
        help="Make missing include/anchor for linked-to entities cause exiting with non-zero error code. Weaker version of --include_error.",
        action='store_true')
    parser.add_argument(
        "--dump_entities",
        help="Just dump the parsed entity data to entities.json and exit.",
        action='store_true')
    parser.add_argument(
        "--html",
        help="Output messages to the named HTML file instead of stdout.")
    parser.add_argument(
        "file",
        help="Only check the indicated file(s). By default, all chapters and extensions are checked.",
        nargs="*")
    parser.add_argument(
        "--ignore_count",
        type=int,
        help="Ignore up to the given number of errors without exiting with a non-zero error code.")
    parser.add_argument("-Wall",
                        help="Enable all warning categories.",
                        action='store_true')

    for message_id in MessageId:
        enable_arg = message_id.enable_arg()
        enable_args.append((message_id, enable_arg))

        disable_arg = message_id.disable_arg()
        disable_args.append((message_id, disable_arg))
        if message_id in enabled_messages:
            parser.add_argument('-' + disable_arg, action="store_true",
                                help="Disable message category {}: {}".format(str(message_id), message_id.desc()))
            # Don't show the enable flag in help since it's enabled by default
            parser.add_argument('-' + enable_arg, action="store_true",
                                help=argparse.SUPPRESS)
        else:
            parser.add_argument('-' + enable_arg, action="store_true",
                                help="Enable message category {}: {}".format(str(message_id), message_id.desc()))
            # Don't show the disable flag in help since it's disabled by
            # default
            parser.add_argument('-' + disable_arg, action="store_true",
                                help=argparse.SUPPRESS)

    args = parser.parse_args()

    arg_dict = vars(args)
    for message_id, arg in enable_args:
        if args.Wall or (arg in arg_dict and arg_dict[arg]):
            enabled_messages.add(message_id)

    for message_id, arg in disable_args:
        if arg in arg_dict and arg_dict[arg]:
            enabled_messages.discard(message_id)

    if args.verbose:
        logging.basicConfig(level='INFO')

    if args.debug:
        logging.basicConfig(level='DEBUG')

    checker = make_macro_checker(enabled_messages)

    if args.dump_entities:
        with open('entities.json', 'w', encoding='utf-8') as f:
            f.write(checker.getEntityJson())
            exit(0)

    if args.file:
        files = (str(Path(f).resolve()) for f in args.file)
    else:
        files = all_docs

    for fn in files:
        checker.processFile(fn)

    if args.html:
        from .html_printer import HTMLPrinter
        printer = HTMLPrinter(args.html)
    else:
        from .console_printer import ConsolePrinter
        printer = ConsolePrinter()

    if args.scriptlocation:
        printer.show_script_location = True

    if args.file:
        printer.output("Only checked specified files.")
        for f in args.file:
            printer.output(f)
    else:
        printer.output("Checked all chapters and extensions.")

    if args.warning_error:
        numErrors = checker.numDiagnostics()
    else:
        numErrors = checker.numErrors()

    check_includes = args.include_warn
    check_broken = not args.file

    if args.file and check_includes:
        print('Note: forcing --include_warn off because only checking supplied files.')
        check_includes = False

    printer.outputResults(checker, broken_links=(not args.file),
                          missing_includes=check_includes)

    if check_broken:
        numErrors += len(checker.getBrokenLinks())

    if args.file and args.include_error:
        print('Note: forcing --include_error off because only checking supplied files.')
        args.include_error = False
    if args.include_error:
        numErrors += len(checker.getMissingUnreferencedApiIncludes())

    check_missing_refpages = args.Wmissing_refpages
    if args.file and check_missing_refpages:
        print('Note: forcing -Wmissing_refpages off because only checking supplied files.')
        check_missing_refpages = False

    if check_missing_refpages:
        missing = checker.getMissingRefPages()
        if missing:
            printer.output("Expected, but did not find, ref page blocks for the following {} entities: {}".format(
                len(missing),
                ', '.join(missing)
            ))
            if args.warning_error:
                numErrors += len(missing)

    printer.close()

    if args.broken_error and not args.file:
        numErrors += len(checker.getBrokenLinks())

    if checker.hasFixes():
        fixFn = 'applyfixes.sh'
        print('Saving shell script to apply fixes as {}'.format(fixFn))
        with open(fixFn, 'w', encoding='utf-8') as f:
            f.write('#!/bin/sh -e\n')
            for fileChecker in checker.files:
                wroteComment = False
                for msg in fileChecker.messages:
                    if msg.fix is not None:
                        if not wroteComment:
                            f.write('\n# {}\n'.format(fileChecker.filename))
                            wroteComment = True
                        search, replace = msg.fix
                        f.write(
                            r"sed -i -r 's~\b{}\b~{}~g' {}".format(
                                re.escape(search),
                                replace,
                                fileChecker.filename))
                        f.write('\n')

    print('Total number of errors with this run: {}'.format(numErrors))

    if args.ignore_count:
        if numErrors > args.ignore_count:
            # Exit with non-zero error code so that we "fail" CI, etc.
            print('Exceeded specified limit of {}, so exiting with error'.format(
                args.ignore_count))
            exit(1)
        else:
            print('At or below specified limit of {}, so exiting with success'.format(
                args.ignore_count))
            exit(0)

    if numErrors:
        # Exit with non-zero error code so that we "fail" CI, etc.
        print('Exiting with error')
        exit(1)
    else:
        print('Exiting with success')
        exit(0)
