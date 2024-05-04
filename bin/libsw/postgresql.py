#!/usr/bin/env python3

import re
import requests
import subprocess
from libsw import builder, settings

class PostgresqlBuilder(builder.AbstractArchiveBuilder):
    """A class to build PostgreSQL from source."""
    def __init__(self):
        super().__init__('postgresql')

    def get_installed_version(self):
        about_text = subprocess.getoutput(builder.set_sh_ld + settings.get('build_path') + 'bin/postgres -V')
        match = re.match(r'postgres \(PostgreSQL\) ([0-9\.]*)', about_text)
        if match == None:
            return '0'
        return match.group(1)

    def get_updated_version(self):
        request = requests.get('https://www.postgresql.org/ftp/source/')
        regex = re.compile(r'a href="v')
        wrong_regex = re.compile(r'[Bb][Ee][Tt][Aa]')
        link_line = False
        for line in request.text.splitlines():
            match = regex.search(line)
            if match == None:
                continue
            if wrong_regex.search(line) != None: #skip betas
                continue
            link_line = line
            break
        if not link_line:
            return link_line
        return re.sub(r'.*href="v([^"]*)/".*', r'\1', link_line)

    def get_source_url(self):
        return 'https://ftp.postgresql.org/pub/source/v' + self.source_version + '/postgresql-' + self.source_version + '.tar.bz2'

    def dependencies(self):
        return ['openssl']