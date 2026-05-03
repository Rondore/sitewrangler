#!/usr/bin/env python3

import os

from libsw import builder

default_builder_image_slug = 'builder'
default_builder_image = 'sitewrangler/' + default_builder_image_slug
default_builder_version = 'latest'

class BuildContainer(builder.AbstractBuilder):
    """A class to build the compile container."""
    def __init__(self):
        super().__init__(default_builder_image_slug)
        self.source_version = default_builder_version

    def get_source_url(self) -> str:
        """
        This method returns the download path for the software wich often
        includes the version number.
        """
        return ''

    def update_needed(self) -> bool:
        """
        Checks to see if an update is needed and returns a boolean indicating if
        it does need an update.
        """
        #TODO
        return False

    def version_reference(self):
        """
        A version number that can be compared to a remote build server.
        """
        return default_builder_version

    def cleanup_old_versions(self, log):
        """
        Remove build logs and source folders for older versions of the software
        build built.

        Args:
            log - An open log to write to.
        """
        pass

    def fetch_source(self, source, log):
        """
        Fetch the source code of the software and extracts it if needed.

        Args:
            source - The source URL
            log - An open log file or null
        """
        os.makedirs(self.source_dir(), exist_ok=True)

    def needs_deploy(self, remote_address, log, force=False):
        """
        Check if a package needs to be pushed from a buid server to a production server.
        """
        return False
    
    def standalone_container(self) -> bool:
        """
        Determins if this software package is put into it's own container
        """
        return True
    
    def system_dependencies(self) -> list[str]:
        """
        Get a list of all system packages needed to run the built software (apt install)
        """
        return []