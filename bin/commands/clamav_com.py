#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw clamav offline-update  # Temporarily stop ClamAV daemon and update definitions')
    print('sw clamav offline  # Use offline-update in a cron job once a day instead of using the update damon to update clamav')
    print('sw clamav daemon  # Use the update damon instead of a cron job to update clamav')
index = command_index.CategoryIndex('clamav', _help)

def _update():
    from libsw import clamav, logger
    log = logger.Log()
    clamav.offline_update(log)
index.register_command('offline-update', _update)
index.register_command('offlineupdate', _update)

def _offline():
    from libsw import clamav, logger
    log = logger.Log()
    clamav.use_offline_update(log)
index.register_command('offline', _offline)

def _daemon():
    from libsw import clamav, logger
    log = logger.Log()
    clamav.use_daemon_update(log)
index.register_command('daemon', _daemon)