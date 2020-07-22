#!/usr/bin/env python3

from libsw import pecl

class MemcachedBuilder(pecl.PeclBuilder):
    def get_pecl_slug(self):
        return 'memcached'
