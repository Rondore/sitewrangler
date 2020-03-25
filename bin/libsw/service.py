#!/usr/bin/env python3

import subprocess
from libsw import logger

use_systemctl = True

def reload_init(log=logger.Log(False)):
    """
    Reload services in systemd.

    Args:
        log - An open logger
    """
    if use_systemctl:
        log.run(['systemctl', 'daemon-reload'])
    else:
        pass
        #TODO
        #log.run(['service', 'daemon-reload'])

def enable(service_name, log=logger.Log(False)):
    """
    Enable a system service.

    Args:
        service_name - The name of the service to enable
        log - An open logger
    """
    if use_systemctl:
        log.run(['systemctl', 'enable', service_name + '.service'])
    else:
        log.run(['service', service_name, 'enable'])

def disable(service_name, log=logger.Log(False)):
    """
    Disable a system service.

    Args:
        service_name - The name of the service to enable
        log - An open logger
    """
    if use_systemctl:
        log.run(['systemctl', 'disable', service_name + '.service'])
    else:
        log.run(['service', service_name, 'disable'])

def start(service_name, log=logger.Log(False)):
    """
    Start a system service.

    Args:
        service_name - The name of the service to enable
        log - An open logger
    """
    if use_systemctl:
        log.run(['systemctl', 'start', service_name + '.service'])
    else:
        log.run(['service', service_name, 'start'])

def stop(service_name, log=logger.Log(False)):
    """
    Stop a system service.

    Args:
        service_name - The name of the service to enable
        log - An open logger
    """
    if use_systemctl:
        log.run(['systemctl', 'stop', service_name + '.service'])
    else:
        log.run(['service', service_name, 'stop'])

def restart(service_name, log=logger.Log(False)):
    """
    Restart a system service.

    Args:
        service_name - The name of the service to enable
        log - An open logger
    """
    if use_systemctl:
        log.run(['systemctl', 'restart', service_name + '.service'])
    else:
        log.run(['service', service_name, 'restart'])

def reload(service_name, log=logger.Log(False)):
    """
    Reload a system service.

    Args:
        service_name - The name of the service to enable
        log - An open logger
    """
    if use_systemctl:
        log.run(['systemctl', 'reload', service_name + '.service'])
    else:
        log.run(['service', service_name, 'reload'])

def status(service_name):
    return subprocess.getoutput("service " + service_name + " status | grep '\s*[Aa]ctive:\s' | sed -E 's/\s*[Aa]ctive:\s//'")