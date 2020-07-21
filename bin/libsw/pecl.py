#!/usr/bin/env python3

import glob
import re
import requests
from abc import abstractmethod
from libsw import builder

up_to_date_version = False

class PeclBuilder(builder.AbstractArchiveBuilder):
    def __init__(self, build_dir="/usr/local/src/pecl/"):
        slug = self.get_pecl_slug()
        super().__init__('pecl-' + slug, build_dir)

    @abstractmethod
    def get_pecl_slug(self):
        """
        Get the name of the PECL package as capitlized in it's download path at pecl.php.net.
        """
        pass

    def get_source_url(self):
        return 'https://pecl.php.net/get/' + self.get_pecl_slug() + '-' + self.get_updated_version() + '.tgz'

    def get_installed_version(self):
        name = self.build_dir + self.slug[5:] + '-' + '*/'
        current = False
        current_version = '0'
        for entry in glob.glob(name):
            skip_chars = len(name) - 2
            this_version = entry[skip_chars:-1]
            if not current:
                current = entry
                current_version = this_version
            else:
                if version.first_is_higher(this_version, current_version):
                    current = entry
                    current_version = this_version
        return current_version

    def get_updated_version(self):
        global up_to_date_version
        if up_to_date_version != False :
            return up_to_date_version
        url = 'https://pecl.php.net/get/' + self.get_pecl_slug()
        response = requests.head(url)
        field_data = response.headers['Content-Disposition']
        data_array = field_data.split(';')
        for data in data_array:
            data = data.strip()
            if( data[:9] == 'filename='):
                filename = data[9:]
                version = re.match(r'.*-([0-9\.]+)', filename).group(1)
                if( version[-1:] == '.' ):
                    version = version[:-1]
                up_to_date_version = version
                if self.source_version == False:
                    self.source_version = version
                return version
        return '0'

    def source_dir(self, version=False):
        """
        Returns the path of the source code directory following a download.

        Args:
            version - The software version to use for the source path
        """
        if version == False:
            version = self.source_version
        if version == False:
            version = self.get_installed_version()
        return self.build_dir + self.slug[5:] + '-' + version + '/'

    def make(self, log):
        return False

    def install(self, log):
        pass

    def populate_config_args(self, log):
        return ''
