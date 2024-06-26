#!/usr/bin/env python3

from libsw import pecl, settings

class ImagickBuilder(pecl.PeclBuilder):
    def get_pecl_slug(self):
        return 'imagick'

    def dependencies(self):
        return ['image-magick']

    def get_php_build_arg(self):
        return '--with-imagick=' + settings.get('build_path')
