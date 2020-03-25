#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw setting (list|get) [exampe_key] # List out all settings or just the value of one setting')
    print('sw setting set exampe_key exampe_value # Set the value of a setting')
index = command_index.CategoryIndex('setting', _help)

def _list(setting_name):
    from libsw import settings
    if settings._settings_dict == False:
        settings._populate_settings()
    if setting_name:
        print(str(settings.get(setting_name)))
    else:
        from tabulate import tabulate
        table = []
        for key in settings._settings_dict:
            table.append([ key, settings._settings_dict[key] ])
        print()
        print(tabulate(table, ['Key', 'Value']))
        print()
index.register_command('list', _list)
index.register_command('get', _list)

def _set(setting_key, more):
    if not setting_key:
        print('Please provide a key and value')
        return
    if len(more) == 0:
        print('Please provide the new value')
        return
    value = more[0]
    from libsw import settings
    settings.set(setting_key, value)
index.register_command('set', _set)
