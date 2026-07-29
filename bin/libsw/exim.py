#!/usr/bin/env python3

import os
import re
import requests
import subprocess
from libsw import version, builder, settings

build_path = settings.get('build_path')
binary_path = build_path + 'sbin/exim'

class EximBuilder(builder.AbstractArchiveBuilder):
    """A class to build Exim from source."""
    def __init__(self):
        super().__init__('exim')

    def get_installed_version(self):
        about_text = subprocess.getoutput(builder.set_sh_ld + binary_path + ' --version')
        match = re.match(r'Exim version ([0-9a-z\.]*)', about_text.splitlines()[0])
        if match == None:
            return '0'
        return match.group(1)

    def get_updated_version(self):
        request = requests.get('https://downloads.exim.org/exim4/')
        regex = re.compile(r'exim-[0-9\.]+\.tar\.bz2')
        newest = '0.0.0a'
        for line in request.text.splitlines():
            match = regex.search(line)
            if match == None:
                continue
            ver = re.sub(r'.*href="exim-([^"]*)\.tar\.bz2".*', r'\1', line)
            if ver[:1].isnumeric(): # skip fips links
                if(version.first_is_higher(ver, newest)):
                    newest = ver
        return newest

    def get_source_url(self):
        return f'https://downloads.exim.org/exim4/exim-{self.source_version}.tar.bz2'

    def populate_config_args(self, log):
        return super().populate_config_args(log, ['./config'])

    def dependencies(self):
        return ['openssl']
    
    def system_dependencies(self) -> list[str]:
        """
        Get a list of all system packages needed to run the built software (apt install)
        """
        return [
            'libpcre',
            'certificates',
            'berkeley-db'
        ]
    
    def get_build_env(self) -> dict[str, str]:
        env = super().get_build_env()
        env['CFLAGS'] = '-I/opt/sitewrangler/usr/include/'
        return env

    def run_pre_config(self, log):
        create_system_user(log)
        sw_path = '/opt/sitewrangler/'
        source_dir = sw_path + 'usr/src/exim/'
        if not settings.use_containers:
            install_dir = settings.get('install_path')
            source_dir = self.source_dir()
        install_dir = sw_path + 'usr/bin/'
        config_file = sw_path + 'etc/exim/configuration'
        log.run([
            'cp',
            f'{source_dir}src/EDITME',
            f'{source_dir}Local/Makefile'
        ])
        log.run(['sed', '-i',
            '-e', f's~BIN_DIRECTORY=.*$~BIN_DIRECTORY={install_dir}~',
            '-e', f's~CONFIGURE_FILE=.*$~CONFIGURE_FILE={config_file}~',
            '-e', f's/.*EXIM_USER=.*$/EXIM_USER={get_dovecot_user()}/',
            '-e', f's/.*EXIM_GROUP=.*$/EXIM_GROUP={get_dovecot_group()}/',
            '-e', f's/.*USE_OPENSSL=.*$/USE_OPENSSL=yes/',
            '-e', f's~.*TLS_LIBS=.*$~TLS_LIBS=-L{sw_path}usr/lib64/ -lssl -lcrypto~',
            '-e', f's~.*TLS_INCLUDE=.*$~TLS_INCLUDE={sw_path}usr/include~',
            '-e', f's~.*PKG_CONFIG_PATH=.*$~PKG_CONFIG_PATH=-{sw_path}usr/lib/pkgconfig~',
            f'{source_dir}Local/Makefile'])
    
    def add_container_config(self, output):
        # output.write('COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt\n')
        output.write(r'ENV PATH="/opt/sitewrangler/usr/bin:${PATH}"' + '\n')
        output.write('ENV LD_LIBRARY_PATH="/opt/sitewrangler/usr/lib64:/opt/sitewrangler/usr/lib"\n')

    def populate_config_args(self, log, command=False):
        """
        Populates a configure command with it's proper arguments from the
        matching configuration file.

        Args:
            command - A default configure command array
        """
        return []

    def standalone_container(self):
        return True

def get_dovecot_user():
    #TODO try detect the typical user for the distro when not using containers
    return 'exim'

def get_dovecot_group():
    #TODO try detect the typical group for the distro when not using containers
    return get_dovecot_user()

def create_system_user(log):
    username = get_dovecot_user()
    groupname = get_dovecot_group()
    response = 1
    if not settings.use_containers:
        response = subprocess.run(['id',
                                '-u',
                                username]).returncode
    if response != 0:
        log.run(['groupadd',
                '--system',
                groupname])
        log.run(['useradd',
                '--system',
                '--gid',
                groupname,
                '--no-create-home',
                username])
        
match_border = re.compile('[#]+')

class EximConfigSplitter():
    def __init__(self, source_file: str, destination_folder: str):
        self.source_file = source_file
        self.destination_folder = destination_folder
        self.header_buffer = []
        self.header_section_count = 0
        self.document_section_count = 0
        self.section_output = None

    def split_file(self):
        if not os.path.exists(self.destination_folder):
            os.makedirs(self.destination_folder)
            with open(self.source_file, 'r') as input:
                self.header_buffer = []
                self.header_section_count = 0
                self.document_section_count = 0
                for line in input.readlines():
                    trimmed = line.strip()
                    is_header = trimmed[0] == '#' and trimmed[-1] == '#'
                    if is_header:
                        if match_border.match(trimmed):
                            header_section_count += 1
                        self.header_buffer.append(line)
                    else:
                        if len(self.header_buffer) > 0:
                            self._open_section_output()
                        self.section_output.write(line + '\n')

    def _open_section_output(self):
        pass

    def _get_section_name(self):
        pass