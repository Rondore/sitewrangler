#!/usr/bin/env python3

import glob
import os
import inquirer
import subprocess
from libsw import curl, nginx, openssl, php, postgresql

class Index():
    """
    A class for tracking all builders avaliable to Site Wrangler. Each builder
    should have a corresponding file in bin/builders. In said file, it should
    import this class and call register_builder on itself.
    """
    index = []

    def register_builder(self, builder):
        """
        Register a builder within Site Wrangler.
        """
        for i in Index.index:
            if builder.slug == i.slug:
                return
        Index.index.append(builder)

    def populate_builders(self, build_queue):
        """
        Add all registered builders to a given BuildQueue.
        """
        for b in Index.index:
            build_queue.append_missing(b)
        build_queue.optimize()


# Since the builders we are importing import this file,
# this import line needs to be after the declaration
# for Index()
from builders import *

def enabled_slugs():
    """
    Get a list of all enabled software slugs.
    """
    slug_list = []
    for builder in Index().index:
        slug_list.append(builder.slug)
    return slug_list

def select_slugs(query_message):
    """
    Have the user select multiple software slugs from software installed by Site
    Wrangler.

    Args:
        query_message - A query message to display to the user when selecting.
    """
    exit = ' ** Done ** '
    selected = []
    enabled = enabled_slugs()
    while True:
        options = [exit]
        for op in enabled:
            if op not in selected:
                options.append(op)
        questions = [
            inquirer.List('s',
                        message=query_message,
                        choices=options
                    )
        ]
        just_selected = inquirer.prompt(questions)['s']
        if just_selected == exit:
            break
        else:
            selected.append(just_selected)
    return selected

def select_slug(query_message):
    """
    Have the user select a software slug from software installed by Site
    Wrangler.

    Args:
        query_message - A query message to display to the user when selecting.
    """
    enabled = enabled_slugs()
    questions = [
        inquirer.List('s',
                    message=query_message,
                    choices=enabled
                )
    ]
    return inquirer.prompt(questions)['s']

def get_builder(slug):
    """
    Get the Builder object for a given slug name.

    Args:
        slug - The slug name of the installable software.
    """
    for builder in Index().index:
        if builder.slug == slug:
            return builder
    return False

def view_log(builder):
    """
    Display a build log in the program less.

    Args:
        builder - Display the log from this builder.
    """
    if type(builder) is str:
        builder = get_builder(builder)
    path = builder.log_name()
    if os.path.exists(path):
        subprocess.run(['less', '-R', path])
        return True
    return False


def populate_slug(build_queue, slug):
    """
    Fetch a builder from the index and add it to the given queue.

    Args:
        build_queue - The BuildQueue to hold the fetched builder
        slug - The slug name of the builder to return
    """
    success = True
    builder = get_builder(slug)
    if builder == False:
        print('Error: unable to find "' + slug + '"')
        success = False
    else:
        build_queue.append(builder)
    return success

def _populate_dependants_of_builder(build_queue, builder):
    """
    Analize a BuildQueue to find any missing depenencies for a single builder,
    then add those missing depencencies to that BuildQueue and run this
    function recursively.
    """
    success = True
    for dependant in builder.dependencies():
        found = build_queue.find(dependant)
        if found == False:
            # dependant is not in queue, add it
            if populate_slug(build_queue, dependant):
                deb_builder = build_queue.find(dependant)
                success = ( _populate_dependants_of_builder(build_queue, deb_builder) and success )
            else:
                success = False
                print('Error: unable to find "' + dependant + '" (dependant of "' + builder.slug + '")')
    return success

def populate_slug_list(build_queue, list):
    """
    Add all registered builders to a given BuildQueue.
    """
    success = True
    for slug in list:
        found = build_queue.find(slug)
        if found == False:
            success = ( populate_slug(build_queue, slug) and success )
    return success

def populate_dependant_builders(build_queue):
    """
    Analize a BuildQueue to find all missing depenencies, then add those
    missing depencencies to that BuildQueue.
    """
    success = True
    for builder, status in build_queue.queue:
        success = ( _populate_dependants_of_builder(build_queue, builder) and success )
    build_queue.optimize()
    return success