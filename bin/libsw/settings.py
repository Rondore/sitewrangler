#!/usr/bin/env python3

install_path = '/opt/sitewrangler/'

import os
from libsw import file_filter

_settings_dict = False

def get(setting_name):
    """
    Get the setting value for a given key.
    The value is stripped of head and tail white space.
    The settings file is only read the first time this function is called.
    Subsequent calls reach into a cached dictionary of values.

    Args:
        setting_name - The index key to look up the setting.
    """
    if(_settings_dict == False):
        _populate_settings()
    return _settings_dict[setting_name]

def set(setting_name, value):
    """
    Set the setting value for a given key.

    Args:
        setting_name - The index key for the setting.
        value - The new value for the setting.
    """
    global _settings_dict
    if(_settings_dict != False):
        _settings_dict[setting_name] = value
    UpdateSetting(setting_name, value).run()

def get_bool(setting_name):
    """
    Same as get(setting_name), but converts the return value to a boolean value.

    Args:
        setting_name - The index key to look up the setting.
    """
    setting = get(setting_name)
    if setting == True:
        return True
    if setting == False:
        return False
    setting = setting.lower()
    return setting == 'true' \
        or setting == '1' \
        or setting == 'on' \
        or setting == 'yes'

def get_num(setting_name):
    """
    Same as get(setting_name), but converts the return value to a Integer value.

    Args:
        setting_name - The index key to look up the setting.
    """
    return int(get(setting_name))

class UpdateSetting(file_filter.FileFilter):
    """A FileFilter to change a setting."""
    def __init__(self, name, value):
        self.setting_name = name
        self.setting_value = value
        super().__init__(install_path + 'etc/config')

    def filter_stream(self, in_stream, out_stream):
        added_line = False
        new_line = self.setting_name + ': ' + self.setting_value + '\n'
        for line in in_stream:
            index = line.find(':')
            if index != -1:
                name = line[:index].lower().strip()
                if name == self.setting_name:
                    line = new_line
                    added_line = True
            out_stream.write(line)
        if not added_line:
            out_stream.write(new_line)
        return True

def _populate_settings():
    """
    Returns a dictionary populated with the current settings.
    """
    global _settings_dict
    _settings_dict = _get_default_settings()
    config_file = install_path + 'etc/config'
    if os.path.exists(config_file):
        with open(config_file) as config:
            for line in config:
                index = line.find(':')
                if index != -1:
                    name = line[:index].lower().strip()
                    value = line[index+1:].strip()

                    # skip comments
                    if not name.startswith('#'):

                        # apply the setting from the line
                        _settings_dict[name] = value
    else:
        _autodetect_defaults()

def _autodetect_defaults():
    # Detect the Exim system user
    from libsw import email
    user, group = email.get_detected_exim_user()
    set('exim_user', user)
    set('exim_group', group)

    ## imap distro detection relies on builder which in turn relies on settings
    # detected_distro = php.detect_distro_code()
    # if detected_distro:
    #     distro = detected_distro
    #     set('imap_distro', distro)

    # detect the number of CPUs to set the build load limits
    import subprocess
    cpu_count = subprocess.getoutput('nproc')
    if len(cpu_count):
        cpu_count = int(cpu_count)
        if cpu_count > 0:
            set('max_build_load', str(cpu_count) + '.0')

    set('ssh_key', detect_identity_file())

def detect_identity_file() -> str:
    import subprocess
    ssh_dir = '/root/.ssh/'
    ideal_file = ssh_dir + 'id_ed25519'
    check_list = [
            ideal_file,
            ssh_dir + 'id_ed25519_sk',
            ssh_dir + 'id_rsa',
            ssh_dir + 'id_rsa_sk',
            ssh_dir + 'id_ecdsa',
            ssh_dir + 'id_ecdsa_sk'
        ]
    for file in check_list:
        if os.path.exists(file):
            return file
    os.makedirs(ssh_dir, exist_ok=True)
    subprocess.run(['ssh-keygen', '-t', 'ed25519', '-N', '', '-f', ideal_file])
    return ideal_file

def _get_default_settings():
    """
    Returns a dictionary populated with the default settings.
    """
    return {
        'install_path': '/opt/sitewrangler/',
        'build_path': '/opt/sitewrangler/usr/',
        'nameserver_one': 'ns1.example.com',
        'nameserver_two': 'ns2.example.com',
        'dns_authority': 'dns-admin.example.com',

        'email_admin_on_build_success': True,
        'mail_shadow_file': '/etc/dovecot/shadow',
        'mail_domain_file': '/etc/maildomains',
        'dkim_folder': "/etc/exim4/dkim/",
        'exim_folder': "/etc/exim4/",
        'exim_service': "exim4",
        'system_admin_email': 'root@localhost',
        'exim_user': 'Mail',
        'exim_group': 'Mail',
        'imap_distro': 'unset',
        'openssl_libs': 'unset',
        'curl_libs': 'unset',
        'owasp-modsec-branch': 'v3.0/master',

        'deploy_openssl': False,
        'deploy_curl': False,
        'build_system': 'podman',
        'build_cache_age': 43200,

        'enable_php_legacy_versions': False,
        'enable_php_super_legacy_versions': False,
        'shared_php_container': True,

        'local_ip': '',
        'public_ip': '',
        'ip6': False,
        'max_build_load': '1.0',
        'db_root_requires_password': False,
        'mysql_socket': '/var/run/mysqld/mysqld.sock',
        'build_server': False,
        'enable_php_prerelease_version': False,
        'debug_build_queue': False,

        'compact_help': False,

        'swap_size': '1.5G',
        'ssh_key': ''
    }

use_containers = get('build_system') != 'system'