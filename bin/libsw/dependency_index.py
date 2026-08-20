#!/usr/bin/env python3

from libsw import dependency

class Index():
    """
    A class for tracking all dependencies avaliable to Site Wrangler. Each
    dependency should have a corresponding file in bin/builders/dependencies.
    In said file, it should import this class and call register_dependency on
    itself.
    """
    index: list[dependency.Dependency] = []

    def register_dependency(self, dependency: dependency.Depenency):
        """
        Register a dependency within Site Wrangler.
        """
        for i in Index.index:
            if dependency.slug == i.slug:
                return
        Index.index.append(dependency)

    def dependent_name(self, name: str):
        """
        This method returns a package name as identified by the
        operating system's package manager
        """
        dependency = self.get_dependent(name)
        if dependency:
            return dependency.get_system_name()
        return False

    def dependent_dev_name(self, name: str):
        """
        This method returns a development package name as
        identified by the operating system's package manager
        """
        dependency = self.get_dependent(name)
        if dependency:
            return dependency.get_dev_system_name()
        return False

    def list_dependent_names(self, name_list: list[str]) -> list[str]:
        """
        This method returns a package name as identified by the
        operating system's package manager
        """
        output: list[str] = []
        for slug in name_list:
            name = self.dependent_name(slug)
            if name:
                output.append(name)
        return output

    def list_dependent_dev_names(self, name_list: list[str]) -> list[str]:
        """
        This method returns a development package name as
        identified by the operating system's package manager
        """
        output: list[str] = []
        for slug in name_list:
            name = self.dependent_dev_name(slug)
            if name:
                output.append(name)
        return output

    def is_system_dependent_installed(self, name):
        """
        Checks to see this package is already installed
        """
        for dependency in Index.index:
            if dependency.name() == name:
                return dependency.is_installed()
        return False

    def get_dependent(self, name: str) -> dependency.Dependency | False:
        """
        Retrieves the class that represents a system dependency
        """
        for dependency in Index.index:
            if dependency.name() == name:
                return dependency
        return False


# Since the dependencies we are importing import this
# file, this import line needs to be after the declaration
# for Index()
from dependencies import *
from libsw import logger

def install_missing_packages(package_list, log=False):
    if not log:
        log = logger.Log()
    index = Index()
    install_list = []
    for package_name in package_list:
        package_class = index.get_dependant(package_name)
        if not package_class.is_installed():
            install_list.append(package_class.get_system_name())
    if len(install_list) > 0:
        command = ['/usr/bin/env', \
            'apt' \
            'install', \
            '-qq']
        command += install_list
        log.run(command)