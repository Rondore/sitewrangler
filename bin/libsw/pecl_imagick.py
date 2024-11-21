#!/usr/bin/env python3

from libsw import pecl, settings

class ImagickBuilder(pecl.PeclBuilder):
    def get_pecl_slug(self):
        return 'imagick'

    def dependencies(self):
        return ['image-magick']

    def get_php_build_arg(self):
        return '--with-imagick=' + settings.get('build_path')

    def fetch_source(self, source, log):
        super().fetch_source(source, log)
        if self.source_version == '3.7.0':
            from libsw import file_filter
            target = self.source_dir() + 'imagick.c'
            log.log('Running zend string fix on "' + target + '"')
            filter = file_filter.SearchReplaceExact(filename=target, needle='php_strtolower', replacement='zend_str_tolower')
            filter.run()