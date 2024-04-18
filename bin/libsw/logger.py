#!/usr/bin/env python3

import os
import subprocess

class Log():
    """
    Create an output stream that logs both to the CLI and optionally to a file.
    """
    def __init__(self, open_log_file=False):
        """
        Create an output stream that logs both to the CLI and optionally to a
        file.

        Args:
            open_log_file - A file that has already been opened with 'w' or 'a'.
                Set this to False to prevent logging to a file.
        """
        self.open_log_file = open_log_file

    def run(self, command, print_log=True, env=dict(os.environ)):
        """
        A convenience method to run CLI commands that steam their output to both
        the screen and to the open log file at the same time.

        Args:
            command - An array containing the command and each of it's arguments
            print_log - (optional) You can set this to False to have the output
                log to the screen but not to the log file
        """
        process = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, env=env)
        while True:
            line = process.stdout.readline()
            if not line and process.returncode is not None:
                break
            if len(line) == 0:
                break
            log_line = line.decode("utf-8").rstrip()
            if print_log:
                print(log_line)
            if self.open_log_file != False:
                self.open_log_file.write(log_line + '\n')
        process.communicate()
        return process.returncode

    def log(self, line, print_log=True):
        """
        Output a string to the screen and log file.

        Args:
            line - The string to print to the screen and log file
            print_log - (optional) You can set this to False to have the output
                log to the screen but not to the log file
        """
        if print_log:
            print(line)
        if self.open_log_file:
            self.open_log_file.write(line + '\n')
