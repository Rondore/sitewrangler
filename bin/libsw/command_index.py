#!/usr/bin/env python3

import inquirer
import inspect
import os

def sorted_category_list():
    """
    Compile a list of all command categories from all registered commands.
    """
    slug_list = []
    for command in Index.help_index:
        cat = command[0]
        if cat not in slug_list:
            slug_list.append(cat)
    return sorted(slug_list)

class Index():
    index = []
    help_index = []

    def register_command(self, category, command, function, rootonly=True):
        """
        Register a new CLI command.

        Args:
            category - The name of the command's category
            command - The command name
            function - When the command is called by the user, this function is
                called passed CLI arguments. The fist argument is passed as a
                stand-alone argument and all subsequent arguments are passed as
                an array.
        """
        category = category.strip().lower()
        command = command.strip().lower()
        for i in Index.index:
            if category == i[0] and category == i[1]:
                return False
        Index.index.append([category, command, function, rootonly])
        return True

    def register_help(self, category, help_function):
        """
        Register the help function for a new CLI category.

        Args:
            category - The name of the category
            help_function - The function to print the help message for the given
                category
        """
        category = category.strip().lower()
        for i in Index.index:
            if category == i[0] and category == i[1]:
                return False
        Index.help_index.append([category, help_function])
        Index.help_index = sorted(Index.help_index, key=lambda k: k[0])
        return True

    def run_command(self, category, command, tertiary, more):
        """
        Run a registered command.

        Args:
            category - The name of the category
            command - The name of the command
            tertiary - The first CLI argument (False if absent)
            more - An array of the remaining CLI arguments
        """
        if command == False:
            self.run_help(category)
            return False
        category = category.strip().lower()
        command = command.strip().lower()
        for com in Index.index:
            if com[0] == category and com[1] == command:
                function = com[2]
                rootonly = com[3]
                if rootonly and os.getuid() != 0:
                    print('"' + command + ' ' + category + '" can only be run as root')
                    return False
                sig = inspect.signature(function)
                params = len(sig.parameters)
                if params == 0:
                    function()
                elif params == 1:
                    function(tertiary)
                elif params == 2:
                    function(tertiary, more)
                return True
        print()
        print(command + ' is not a valid ' + category + ' command')
        self.run_help(category)
        return False


    def run_help(self, category):
        """
        Print help output.

        Args:
            category - Print help for this category (False for all categories)
        """
        extra_help = True
        from libsw import settings
        if settings.get_bool('compact_help') and category:
            extra_help = False

        if extra_help:
            print()
            print('Commands have this syntax:')
            print('sw category command arguments')
            print('[example] - optional argument that will trigger a multi-select prompt when omitted')
            print('[`example`] - optional argument that will not trigger a prompt and can only be specified in the command')
            print('[one [another]] - optional arguments where the second argument can only be specified along with the first in the command')
            print('(one|another) - an either or option')
            print('Omitted optional arguments will trigger a multi-select prompt unless quoted like this: `no prompt`')
        print()
        has_printed = False
        if category != False:
            category = category.strip().lower()
            for entry in Index.help_index:
                if category == 'all' or entry[0] == category:
                    # print help entry
                    entry[1]()
                    has_printed = True
        if not has_printed:
            cat_list = sorted_category_list()
            print('Categories:')
            print()
            for cat in cat_list:
                print(cat)
            print()
            print('To get help with a category, simply type "sw" followed by the category. For example:')
            print('sw ' + cat_list[0])
            print('  or')
            print('sw help ' + cat_list[0])
        print()
        return has_printed

    def category_exists(self, category):
        """
        Check if a command category name exists amongst registered commands.

        Args:
            category - Check this category name
        """
        category = category.strip().lower()
        for com in Index.index:
            if com[0] == category:
                return True
        return False

class CategoryIndex(Index):
    """
    A convinience class for registering multiple commands from the same
    category, while also requiring a help string for the category.
    """
    def __init__(self, category, help_text):
        """
        Create a new category along with it's help string.

        Args:
            category - The name of the new category
            help_text - The help output string for the category
        """
        self.category = category
        self.register_help(category, help_text)

    def register_command(self, command, function, rootonly=True):
        """
        Register a new command in the already set category.

        Args:
            command - The command name
            function - When the command is called by the user, this function is
                called passed CLI arguments. The fist argument is passed as a
                stand-alone argument and all subsequent arguments are passed as
                an array.
        """
        return super().register_command(self.category, command, function, rootonly)

# Since the commands we are importing import this file,
# this import line needs to be after the declaration
# for Index()
from commands import *
