#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw firewall writepignore  # Update the ignored processes in the firewall and reload the firewall rules')
index = command_index.CategoryIndex('firewall', _help)

def _writepignore(force):
    from libsw import firewall
    firewall.writepignore()
    firewall.reload()
index.register_command('writepignore', _writepignore)