#!/usr/bin/env python3

import os
import shutil
import glob
from libsw import builder, settings
from abc import ABC, abstractmethod

def get_enabled_ruleset_builders():
    """
    Get all ModSecurity ruleset builders
    """
    from libsw import build_index
    builders = []
    for i in build_index.Index().index:
        if isinstance(i, AbstractRuleset):
            builders.append(i)
    return builders

def get_enabled_rulesets():
    """
    Get the slugs for all ModSecurity ruleset builders
    """
    names = []
    for builder in get_enabled_ruleset_builders():
        names.append(builder.slug)
    return names

def logrotate_file():
    return settings.get('install_path') + 'etc/logrotate.d/modsecurity.conf'

def write_logrotate():
    """
    Write out a configuration file for logrotated to rotate the global php log
    files. Also add an include directive that will include all website
    logrotated files.
    """
    from libsw import nginx
    install_path = settings.get('install_path')
    filename = logrotate_file()
    os.makedirs(os.path.dirname(filename))
    with open(filename, 'w+') as output:
        output.write(settings.get('install_path') + 'var/log/modsec_*.log {\n\
    rotate 15\n\
    size=300M\n\
    missingok\n\
    compress\n\
    postrotate\n\
	/bin/kill -USR1 `cat ' + nginx.nginx_dir + 'logs/nginx.pid 2>/dev/null` 2>/dev/null || true\n\
    endscript\n\
}\n\n')

class AbstractRuleset(builder.AbstractBuilder):
    def get_rule_file(self):
        """
        Get the settings and rules from a particular source compiled into a
        single file.
        """
        return self.source_dir() + '/'

    def clean(self, log):
        return True

    def rule_output_file(self):
        base_slug = self.slug
        if base_slug.startswith('modsec-'):
            base_slug = base_slug[7:]
        return settings.get('install_path') + 'etc/raw-modsec-rulesets/' + base_slug + '.conf'

    def rule_output_dir(self):
        return self.rule_output_file()[:-5] + '/'

class ModSecurityBuilder(builder.AbstractGitBuilder):
    """A class to build ModSecurity from source."""
    def __init__(self):
        super().__init__('modsec', branch='v3/master')

    # def check_build(self):
    #     check_path = self.source_dir() + 'tools/rules-check/modsec_rules_check-rules-check.o'
    #     print('Checking path: ' + check_path)
    #     return os.path.exists(check_path)

    def get_source_url(self):
        return 'https://github.com/SpiderLabs/ModSecurity.git'

    def dependencies(self):
        return ['curl', 'maxmind']

    # def install(self, log):
    #     log.run(['make', 'install'])

    def run_pre_config(self, log):
        log.run([self.source_dir() + 'build.sh'])

    def source_dir(self):
        return self.build_dir + 'ModSecurity/'

    def fetch_source(self, source, log):
        old_pwd = os.getcwd()
        super().fetch_source(source, log)
        os.chdir(self.source_dir())
        log.run(['git', 'submodule', 'init'])
        log.run(['git', 'submodule', 'update'])
        os.chdir(old_pwd)

    def install(self, log):
        build_path = settings.get('build_path')
        super().install(log)
        lib_dir = build_path + 'modsecurity/lib'
        lib64_dir = build_path + 'modsecurity/lib64'
        if os.path.isdir(lib64_dir) and not os.path.exists(lib_dir):
            os.symlink(lib64_dir, lib_dir, target_is_directory=True)
        if not os.path.isfile(logrotate_file()):
            write_logrotate()
        from libsw import nginx
        nginx.reload()

class ModSecurityRulesetBuilder(builder.AbstractBuilder):
    """A class to compile multiple ModSecurity rulesets into one file."""
    def __init__(self):
        super().__init__('modsec-rules')

    def get_source_url(self):
        return ''

    def version_reference(self):
        version = 0
        builders = get_enabled_ruleset_builders()
        for b in builders:
            ver = b.version_reference()
            if '.' in ver:
                base = 1
                vsub_array = ver.split('.')
                vsub_array.reverse()
                ver = 0
                for vsub in vsub_array:
                    ver += base + int(vsub)
                    base *= 1000
            version += int(ver)
        return version

    def dependencies(self):
        rules = get_enabled_rulesets()
        rules.append('modsec')
        return rules

    def populate_config_args(self, log):
        return []

    def source_dir(self):
        return self.build_dir

    def fetch_source(self, source, log):
        return True

    def make(self, log):
        output_dir = settings.get('install_path') + 'etc/modsec/'
        output_file = output_dir + 'rules.conf'
        # if os.path.exists(output_dir):
        #     shutil.rmtree(output_dir)
        filelist = glob.glob(os.path.join(output_dir, "*.data"))
        filelist.extend(glob.glob(os.path.join(output_dir, "*.mapping")))
        filelist.extend(glob.glob(os.path.join(output_dir, "*.conf")))
        for f in filelist:
            os.remove(f)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(output_file, 'w+') as output:
            with open(self.build_dir + 'ModSecurity/modsecurity.conf-recommended') as base_config:
                for line in base_config:
                    if line.startswith('SecRuleEngine '):
                        output.write('SecRuleEngine On\n')
                    elif line.startswith('SecAuditLog '):
                        output.write('SecAuditLog ' + settings.get('install_path') + 'var/log/modsec_audit.log\n')
                    else:
                        output.write(line)
            for builder in get_enabled_ruleset_builders():
                input_file = builder.rule_output_file()
                input_dir = builder.rule_output_dir()
                with open(input_file) as input:
                    for line in input:
                        output.write(line)
                for data_file in glob.glob(input_dir + '*.data'):
                    shutil.copy(data_file, output_dir)
        source_map = self.build_dir + 'ModSecurity/unicode.mapping'
        target_map = output_dir + 'unicode.mapping'
        shutil.copy(source_map, target_map)
        return 0 # 0 = successful bash command

    def install(self, log):
        from libsw import nginx
        nginx.reload()
        return True

    def cleanup_old_versions(self, log):
        return True

    def update_needed(self):
        return False

class OwaspBuilder(builder.AbstractGitBuilder, AbstractRuleset):
    """A class to fetch the OWASP ModSecurity rules."""
    def __init__(self):
        branch = settings.get('owasp-modsec-branch')
        super().__init__('modsec-owasp', branch=branch)

    def get_source_url(self):
        return 'https://github.com/SpiderLabs/owasp-modsecurity-crs.git'

    def dependencies(self):
        return []

    def populate_config_args(self, log):
        return []

    def source_dir(self):
        return self.build_dir + 'owasp-modsecurity-crs/'

    # def fetch_source(self, source, log):
    #     old_pwd = os.getcwd()
    #     super().fetch_source(source, log)
    #     os.chdir(self.source_dir())
    #     log.run(['git', 'submodule', 'init'])
    #     log.run(['git', 'submodule', 'update'])
    #     os.chdir(old_pwd)

    def make(self, log):
        raw_rule_dir = self.source_dir() + 'rules/'
        base_rules = self.source_dir() + 'crs-setup.conf.example'
        output_file = self.rule_output_file()
        output_dir = self.rule_output_dir()
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        if os.path.exists(output_file):
            os.remove(output_file)
        os.makedirs(output_dir)
        for file in glob.glob(raw_rule_dir + '*.data'):
            shutil.copy(file, output_dir)
        shutil.copy(base_rules, output_file)
        with open(output_file, 'a') as output:
            for data_file in glob.glob(raw_rule_dir + '*.conf'):
                with open(data_file) as input:
                    for line in input:
                        output.write(line)
        return 0 # 0 = successful bash command

    def install(self, log):
        return True
