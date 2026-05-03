#!/usr/bin/env python3

from abc import ABC, abstractmethod

class Dependency(ABC):
    """
    A class to interact with a system package.
    """
    def __init__(self, slug):
        self.slug = slug

    def name(self):
        return self.slug

    @abstractmethod
    def get_system_name(self) -> str:
        """
        This method returns the package name as identified by the
        operating system's package manager
        """
        pass

    @abstractmethod
    def get_dev_system_name(self) -> str:
        """
        This method returns the package name of the development
        library for this package as identified by the operating
        system's package manager
        """
        pass