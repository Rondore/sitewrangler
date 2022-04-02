#!/usr/bin/env python3

import os
import platform
import subprocess

def get_package_manager():
    if os.path.exists('/usr/bin/apt-get'):
        return 'apt'
    if os.path.exists('/usr/bin/dnf'):
        return 'dnf'
    if os.path.exists('/usr/bin/yum'):
        return 'yum'
    if os.path.exists('/usr/sbin/pkg'):
        return 'pkg'

def get_distro():
    """
    Get the name of the OS distrobution of the installed system.
    """
    os_name = platform.system()
    if os_name == 'Linux':
        distro = subprocess.getoutput("cat /etc/*release | grep '^ID=' | head -1")[3:].strip()
        if ( distro.startswith('"') and distro.endswith('"') ) or \
                ( distro.startswith("'") and distro.endswith("'") ):
            distro = distro[1:-1]
        return distro
    elif os_name == 'Darwin':
        return 'macos'
    elif os_name.startswith('CYGWIN'):
        return 'cygwin'
    elif os_name.startswith('MINGW'):
        return 'mingw'
    elif os_name == 'FreeBSD':
        return 'FreeBSD'
    return os_name

def get_distro_version():
    """
    Get the major OS version of the host system.
    """
    os_name = platform.system()
    if os_name == 'Linux':
        distro = subprocess.getoutput("cat /etc/*release | grep '^VERSION_ID=' | head -1")[11:].strip()
        if ( distro.startswith('"') and distro.endswith('"') ) or \
                ( distro.startswith("'") and distro.endswith("'") ):
            distro = distro[1:-1]
        return distro
    elif os_name == 'Darwin':
        return ''
    elif os_name.startswith('CYGWIN'):
        return ''
    elif os_name.startswith('MINGW'):
        return ''
    elif os_name =='FreeBSD':
        return ''
    return False

def get_system_info():
    return { 'package_manager' : get_package_manager(),\
        'distro' : get_distro(),\
        'version' : get_distro_version()}