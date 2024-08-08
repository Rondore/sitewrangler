#!/usr/bin/env python3

import sys
import os
from libsw import command_index, settings

index = command_index.Index()
def _help_help():
    print('sw help [category|all]  # This help page')
index.register_help('help', _help_help)

install_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '/'
settings.install_path = install_path
if install_path != settings.get('install_path'):
    settings.set('install_path', install_path)

def run_main():
    count = len(sys.argv)
    if count < 2:
        index.run_help(False)
    else:
        primary = sys.argv[1].lower()
        secondary = False
        tertiary = False
        more = False
        if count > 2:
            secondary = sys.argv[2].lower()
        if count > 3:
            tertiary = sys.argv[3].lower()
        if count > 4:
            more = sys.argv[4:]
        if primary == 'help':
            index.run_help(secondary)
        if primary == 'selfupdate' or primary == 'self-update':
            from libsw import recursion
            recursion.self_update()
        else:
            index.run_command(primary, secondary, tertiary, more)

if __name__ == '__main__':
    run_main();
