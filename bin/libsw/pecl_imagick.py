#!/usr/bin/env python3

from libsw import pecl

class ImagickBuilder(pecl.PeclBuilder):
    def get_pecl_slug(self):
        return 'imagick'

    def dependencies(self):
        return ['image-magic']

    def get_php_build_arg(self):
        return '--with-imagick'
