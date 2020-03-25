#!/usr/bin/env python3

import os

cronpath = '/etc/cron.daily/update_clamav'

def offline_update(log):
    '''
    Stop the clamav daemon, update the clamav definitions, then
    start the damon.  This can avoid OOMs on some systems with
    less RAM capacity.
    '''
    log.run(['service', 'clamav-daemon', 'stop'])
    log.run(['/usr/bin/env', 'freshclam'])
    log.run(['service', 'clamav-daemon', 'start'])

def use_offline_update(log):
    log.run(['service', 'clamav-daemon', 'stop'])
    with open(cronpath, 'w+') as cron:
        cron.write("#!/bin/sh\n")
        cron.write("\n")
        cron.write("/usr/bin/env sw clamav offline-update\n")
    log.run(['chmod', '+x', cronpath])
    log.run(['service', 'cron', 'reload'])

def use_daemon_update(log):
    if os.path.exists(cronpath):
        os.remove(cronpath)
    log.run(['service', 'cron', 'reload'])
    log.run(['service', 'clamav-daemon', 'start'])