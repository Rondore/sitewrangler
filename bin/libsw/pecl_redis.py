#!/usr/bin/env python3

from libsw import pecl

class RedisBuilder(pecl.PeclBuilder):
    def get_pecl_slug(self):
        return 'redis'
