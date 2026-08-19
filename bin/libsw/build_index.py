#!/usr/bin/env python3

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

import os
import subprocess
from libsw import file_filter, input_util, settings, container


def registered_slugs():
    """
    Get a list of all registered software slugs.
    """
    slug_list = []
    for builder in Index().index:
        slug_list.append(builder.slug)
    return slug_list

def select_slugs(query_message, slug_list=registered_slugs()):
    """
    Have the user select multiple software slugs from software avaliable in Site
    Wrangler.

    Args:
        query_message - A query message to display to the user when selecting
        options (optional) - The software slugs to select from
    """
    return input_util.select_multiple_from(query_message, slug_list)

def select_slug(query_message, slug_list=registered_slugs()):
    """
    Have the user select a software slug from software installed by Site
    Wrangler.

    Args:
        query_message - A query message to display to the user when selecting
        options (optional) - The software slugs to select from
    """
    return input_util.select_from(query_message, slug_list)

def get_builder(slug):
    """
    Get the Builder object for a given slug name.

    Args:
        slug - The slug name of the installable software
    """
    for builder in Index().index:
        if builder.slug == slug:
            return builder
    return False

def view_log(builder):
    """
    Display a build log in the program less.

    Args:
        builder - Display the log from this builder
    """
    if type(builder) is str:
        builder = get_builder(builder)
    path = builder.log_name()
    if os.path.exists(path):
        subprocess.run(['less', '-R', path])
        return True
    return False

def get_list_with_dependants(slug_array):
    """
    Populate a list of slugs with the slugs of all dependant software slugs

    Args:
        slug_array -  A list of software slugs
    """
    new_slug_array = []
    new_slug_array += slug_array
    for slug in slug_array:
        if slug not in new_slug_array:
            new_slug_array.append(slug)
        builder = get_builder(slug)
        for dependant in builder.dependencies():
            if dependant not in new_slug_array:
                added_slugs = get_list_with_dependants([dependant])
                for new_slug in added_slugs:
                    if new_slug not in slug_array:
                        new_slug_array.append(new_slug)
    return new_slug_array

class QueuePopulator():
    def __init__(self, build_queue):
        self.build_queue = build_queue

    def populate_slug(self, slug):
        """
        Fetch a builder from the index and add it to the given queue.

        Args:
            self - The BuildQueue to hold the fetched builder
            slug - The slug name of the builder to return
        """
        success = True
        builder = get_builder(slug)
        if builder == False:
            print('Error: unable to find "' + slug + '"')
            success = False
        else:
            self.build_queue.append(builder)
        return success

    def _populate_dependants_of_builder(self, builder):
        """
        Analize the BuildQueue to find any missing depenencies for a single builder,
        then add those missing depencencies to that BuildQueue and run this
        function recursively.
        """
        success = True
        for dependant in builder.dependencies():
            found = self.build_queue.find(dependant)
            if found == False:
                # dependant is not in queue, add it
                if self.populate_slug(dependant):
                    deb_builder = self.build_queue.find(dependant)
                    success = ( self._populate_dependants_of_builder(deb_builder) and success )
                else:
                    success = False
                    print('Error: unable to find "' + dependant + '" (dependant of "' + builder.slug + '")')
        return success

    def populate_enabled(self):
        """
        Add all enabled builders to a given BuildQueue.

        Args:
            build_queue - The BuildQueue to hold the enabled builders
        """
        slug_list = enabled_slugs()
        if slug_list != False:
            self.populate_slug_list(slug_list)

    def populate_slug_list(self, list):
        """
        Add all registered builders to a given BuildQueue.

        Args:
            build_queue - The BuildQueue to hold the builders
            slug_list - An Array of slug names that correlate to software packages
        """
        success = True
        for slug in list:
            found = self.build_queue.find(slug)
            if found == False:
                success = ( self.populate_slug(slug) and success )
        return success

    def populate_dependant_builders(self):
        """
        Analize a BuildQueue to find all missing depenencies, then add those
        missing depencencies to that BuildQueue.

        Args:
            build_queue - The BuildQueue to hold the dependant builders
        """
        success = True
        for builder, status in self.build_queue.queue:
            success = ( self._populate_dependants_of_builder(builder) and success )
        self.optimize()
        return success
    
    def depopulate_extraneous(self):
        pass

    def optimize(self):
        self.build_queue.optimize()
    
class ContainerQueuePopulator(QueuePopulator):
    def populate_slug(self, slug):
        """
        Fetch a builder from the index and add it to the given queue.

        Args:
            self - The BuildQueue to hold the fetched builder
            slug - The slug name of the builder to return
        """
        success = True
        builder = get_builder(slug)
        if builder == False:
            print('Error: unable to find "' + slug + '"')
            success = False
        else:
            image = container.ContainerImage(builder)
            container_dependencies = []
            base_image = image.get_base_image()
            if base_image != container.default_base_image:
                container_dependencies.append(container.get_image_slug(base_image))
            container_dependencies.extend([i.slug for i in image.added_images])
            self.populate_slug_list(container_dependencies)
            self.build_queue.append(image)
        return success
    
    def depopulate_extraneous(self):
        for image, status in self.build_queue.queue:
            if image.builder.standalone_container(): continue
            needs_own_image = True
            for compare_image, s in self.build_queue.queue:
                if image.slug in compare_image.builder.dependencies():
                    needs_own_image = False
                    break
            if not needs_own_image:
                self.build_queue.remove(image)

    
def get_preferred_populator(build_queue):
    if settings.use_containers:
        return ContainerQueuePopulator(build_queue)
    else:
        return QueuePopulator(build_queue)

def get_dependant_upon(slug):
    """
    Get software that depends upon the given software slug.
    """
    dependant_slugs = [];
    for dex in Index.index:
        if slug in dex.dependencies():
            dependant_slugs.append(dex.slug)
            dependant_slugs.extend(get_dependant_upon(dex.slug))
    return dependant_slugs

def get_installed(excluded_array=False) -> list[str]:
    """
    Get an array of installed software packages.

    Args:
        excluded_array - (optional) An array of software slugs to exclude from the array
    """
    if excluded_array == False:
        excluded_array=[]
    names = []
    save_file = _get_enabled_slugs_file()
    if os.path.exists(save_file):
        with open(save_file) as version_file:
            for line in version_file:
                line = line.replace("\n", "").replace("\r", "")
                if line not in excluded_array:
                    names.append(line)
    return names

def _get_enabled_slugs_file():
    """The file path to the enabled slugs file."""
    from libsw import settings
    return settings.get('install_path') + 'etc/enabled-packages'

def enable_slug(slug):
    """
    Add a slug to the list of enabled software packages.

    Args:
        slug - The slug name the represents the package
    """
    slug = slug.lower()
    save_file = _get_enabled_slugs_file()
    return file_filter.AppendUnique(save_file, slug, ignore_trim=True, ignore_case=True).run()

def disable_slug(slug):
    """
    Remove a slug from the list of enabled software packages.

    Args:
        slug - The slug name the represents the package
    """
    save_file = _get_enabled_slugs_file()
    return file_filter.RemoveExact(save_file, slug, ignore_trim=True, ignore_case=True).run()

def enabled_slugs():
    """
    Get a list of all enabled software slugs.
    """
    save_file = _get_enabled_slugs_file()
    return file_filter.get_trimmed_lower_file_as_array(save_file)

def get_digest() -> str:
    """
    Get a machine-readable list of all software that is installed along with
    the corresponding version number.
    """
    installed = get_installed()
    output = ''
    for slug in installed:
        builder = get_builder(slug)
        version: str = builder.version_reference()
        output += slug + " " + version + "\n"
    return output