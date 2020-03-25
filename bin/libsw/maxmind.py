#!/usr/bin/env python3

import os
from libsw import builder

class MaxMindBuilder(builder.AbstractGitBuilder):
    """A class to build ModSecurity from source."""
    def __init__(self):
        super().__init__('maxmind', branch='master')

    def get_source_url(self):
        return 'https://github.com/maxmind/libmaxminddb.git'

    # def dependencies(self):
    #     return []

    # def install(self, log):
    #     log.run(['make', 'install'])

    # def run_pre_config(self, log):
    #     log.run([self.source_dir() + 'build.sh'])

    def source_dir(self):
        return self.build_dir + 'libmaxminddb/'

    def fetch_source(self, source, log):
        old_pwd = os.getcwd()
        super().fetch_source(source, log)
        os.chdir(self.source_dir())
        log.run('./bootstrap')
        os.chdir(old_pwd)

    def install(self, log):
        super().install(log)
        log.run('ldconfig')

    def get_clone_args(self):
        return ['--recursive']