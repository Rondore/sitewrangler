#!/usr/bin/env python3

import re
import requests
import subprocess
from libsw import version, builder, settings

major_version = '2.4'
download_server_folder = f'https://dovecot.org/releases/{major_version}/'
build_path = settings.get('build_path')
binary_path = build_path + 'sbin/dovecot'

class DovecotBuilder(builder.AbstractArchiveBuilder):
    """A class to build Dovecot from source."""
    def __init__(self):
        super().__init__('dovecot')

    def get_installed_version(self):
        about_text = subprocess.getoutput(builder.set_sh_ld + binary_path + ' --version')
        match = re.match(r'([0-9a-z\.]*) ', about_text.splitlines()[0])
        if match == None:
            return '0'
        return match.group(1)

    def get_updated_version(self):
        request = requests.get(download_server_folder)
        regex = re.compile(r'dovecot-[0-9\.]+\.tar\.gz"')
        newest = '0.0.0a'
        for line in request.text.splitlines():
            match = regex.search(line)
            if match == None:
                continue
            ver = re.sub(r'.*href="dovecot-([^"]*)\.tar\.gz".*', r'\1', line)
            if(version.first_is_higher(ver, newest)):
                newest = ver
        return newest

    def get_source_url(self):
        return download_server_folder + f'dovecot-{self.source_version}.tar.gz'

    def populate_config_args(self, log):
        return super().populate_config_args(log, ['./config'])

    def dependencies(self):
        return ['openssl']
    
    def system_dependencies(self) -> list[str]:
        """
        Get a list of all system packages needed to run the built software (apt install)
        """
        return []

    def populate_config_args(self, log, command=False):
        """
        Populates a configure command with it's proper arguments from the
        matching configuration file.

        Args:
            command - A default configure command array
        """
        return ['./configure']

    def standalone_container(self):
        return True