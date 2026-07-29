#!/usr/bin/env python3

from libsw import command_index

def _help():
    print('sw system onboot  # Run tasks that must run whenever the system boots up')
    print('sw system makeswap  # Create a swap file according to swap size settings')
    print('sw system selfupdate  # Update Site Wrangler')
    print('sw system healthcheck  # Restarts any services that are no longer running')
index = command_index.CategoryIndex('system', _help)

def _onboot():
    from libsw import system, compose
    system.make_extra_swap()
    #TODO check if we need to wait for network
    compose.compose_up()
index.register_command('onboot', _onboot)

def _make_swap():
    from libsw import system
    system.make_extra_swap()
index.register_command('makeswap', _make_swap)
index.register_command('make-swap', _make_swap)

def _self_update():
    from libsw import recursion
    recursion.self_update()
index.register_command('selfupdate', _self_update)
index.register_command('self-update', _self_update)

def _health_check():
    from libsw import system, settings, compose
    if settings.use_containers:
        compose.check_up()
    else:
        system.check_up()
index.register_command('healthcheck', _health_check)
index.register_command('health-check', _health_check)