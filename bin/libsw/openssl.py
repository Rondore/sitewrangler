#!/usr/bin/env python3

import os
import re
import requests
import subprocess
from libsw import version, file_filter, builder, settings

class OpensslBuilder(builder.AbstractArchiveBuilder):
    """A class to build OpenSSL from source."""
    def __init__(self):
        super().__init__('openssl')

    def get_installed_version(self):
        about_text = subprocess.getoutput('/usr/local/bin/openssl version')
        match = re.match(r'OpenSSL ([0-9a-z\.]*)', about_text)
        if match == None:
            return '0'
        return match.group(1)

    def get_updated_version(self):
        request = requests.get('https://www.openssl.org/source/')
        regex = re.compile(r'\.tar\.gz')
        antiregex = re.compile(r'alpha|beta')
        newest = '0.0.0a'
        for line in request.text.splitlines():
            match = regex.search(line)
            if match == None:
                continue
            antimatch = antiregex.search(line)
            if antimatch != None:
                continue
            ver = re.sub(r'.*href="openssl-([^"]*)\.tar\.gz".*', r'\1', line)
            if ver[:1].isnumeric(): # skip fips links
                if(version.first_is_higher(ver, newest)):
                    newest = ver
        return newest

    def get_source_url(self):
        return 'https://www.openssl.org/source/openssl-' + self.source_version + '.tar.gz'

    def populate_config_args(self, log):
        return super().populate_config_args(log, ['./config'])

    def install(self, log):
        super().install(log)
        deploy_environment(log)

def libs_path():
    path = settings.get('openssl_libs')
    if path == 'unset':
        paths = ['/usr/local/ssl/lib', '/usr/local/lib64', '/usr/local/lib']
        at = -1
        while path == 'unset' or not os.path.exists(path + '/libssl.so.1.1'):
            at += 1
            if at >= len(paths):
                return False
            path = paths[at]
        settings.set('openssl_libs', path)
    return path

def deploy_environment(log):
    """
    Configure the system linker to use the new copy of openssl if the setting
    'deploy_openssl' is set to True.

    Args:
        log - An open log to write to
    """
    if settings.get_bool('deploy_openssl'):
        filename = '/etc/ld.so.conf.d/openssl.conf'
        log.log('Making sure ' + filename + ' exists')
        ld_filter = file_filter.AppendUnique(filename, libs_path())
        ld_filter.run()
    subprocess.run(['ldconfig'])
