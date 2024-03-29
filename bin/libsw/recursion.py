#!/usr/bin/env python3

import subprocess
from libsw import logger, settings

def self_update():
    '''
    Update Site Wrangler to the latest version
    '''
    install_path = settings.get('install_path')
    log = logger.Log()
    command = [
            'git',
            '-C',
            install_path,
            'pull'
        ]
    log.run(command)