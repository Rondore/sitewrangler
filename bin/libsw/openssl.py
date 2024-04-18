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

    def cleanup_old_versions(self, log):
        super().cleanup_old_versions(log)
        if(int(self.source_version.split('.')[0]) >= 3):
            setup_lib32(log)

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

def setup_lib32(log):
    """
    Update the lib directory by pointing pkg-config files to lib64 for openssl 3

    Args:
        log - An open log to write to
    """
    files = ['libcrypto.a', 'libcrypto.so', 'libcrypto.so.1.1', 'libssl.a', 'libssl.so', 'libssl.so.1.1']
    links = ['pkgconfig/libssl.pc', 'pkgconfig/openssl.pc', 'pkgconfig/libcrypto.pc']
    for f in files:
        file = '/usr/local/lib/' + f
        if os.path.exists(file):
            os.remove(file)
            log.log('Deleted ' + file)
    for l in links:
        link = '/usr/local/lib/' + l
        target = '/usr/local/lib64/' + l
        if not os.path.islink(link):
            if os.path.exists(link):
                os.remove(link)
                log.log('Deleted ' + file)
            os.symlink(target, link)
            log.log('Created link ' + link + ' -> ' + target)
