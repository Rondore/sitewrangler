#!/usr/bin/env python3

from libsw import builder, settings

class NagiosBuilder(builder.AbstractGitBuilder):
    """A class to build ModSecurity from source."""
    def __init__(self):
        super().__init__('nagios', branch='master')

    # def check_build(self):
    #     check_path = self.source_dir() + 'tools/rules-check/modsec_rules_check-rules-check.o'
    #     print('Checking path: ' + check_path)
    #     return os.path.exists(check_path)

    def get_source_url(self):
        return 'https://github.com/NagiosEnterprises/nagioscore.git'

    # def dependencies(self):
    #     return []

    def make_args(self):
        return []

    def source_dir(self):
        return self.build_dir + 'nagioscore/'

    def install(self, log):
        log.run(['make', 'install-groups-users'])
        super().install(log)
        log.run(['make', 'install-daemoninit'])
        log.run(['make', 'install-commandmode'])