#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import cmd
import tools
import logging
from constants import LOG_LEVEL_VERBOSE

__version__ = 0.01

NO_EXIT_CONFIRMATION = True
LOG_LEVEL = logging.INFO

class DataMan(cmd.Cmd):
    """Command line tool for quick data documentation."""

    prompt = "dm> "
    intro = "Data Manager\n --Ronny's way of avoiding having to stare at spreadsheets."

    def preloop(self):
        pass
        # process command line arguments etc.

    def do_greet(self, user):
        """greet [user name]
        Simple user greeting. When used in combination with a parameter, will
        respond with personalized greeting. Yay."""
        if user:
            print("hello ", user)
        else:
            print("hi there!")

    def do_stats(self, path):
        if not len(path):
            path = '.'
        import folderstats as fs
        fs.print_table(fs.gather(path))

    def do_EOF(self, line):
        "Exit"
        return True

    def postloop(self):
        print("Done.")

if __name__ == "__main__":
    # Command line parsing
    import argparse
    parser = argparse.ArgumentParser(prog="DataMan")
    parser.add_argument('-d', '--debug', action='store_true',
            help='Debug mode -- verbose output, no confirmations.')
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))

    # sub-parsers
    subparsers = parser.add_subparsers(help='sub commands', dest='command')

    parser_cli = subparsers.add_parser('cli', help='Interactive CLI session')
    parser_stats = subparsers.add_parser('stats', help='Directory statistics')
    parser_stats.add_argument('path', help='Relative or absolute path to directory',
            default='.', nargs='?')
    parser_proc = subparsers.add_parser('proc', help='Data processing')
    parser_doc = subparsers.add_parser('doc', help='Data documentation')
    parser_check = subparsers.add_parser('check', help='Check/verify data and documentation integrity')

    cli_args = parser.parse_args()

    if cli_args.debug:
        NO_EXIT_CONFIRMATION = True

    logging.addLevelName(LOG_LEVEL_VERBOSE, "VERBOSE")
    logging.basicConfig(level=LOG_LEVEL_VERBOSE if cli_args.debug else LOG_LEVEL,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log = logging.getLogger(__name__)

    if cli_args.command == 'cli':
        DataMan().cmdloop()
    else:
        DataMan().onecmd(' '.join(sys.argv[1:]))

