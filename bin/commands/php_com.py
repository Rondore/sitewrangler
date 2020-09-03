#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw php list [`disabled`]  # List PHP sites along with PHP versions and system usernames')
    print('sw php (add|create) [example.com [example_user [7.3]]]  # Create a PHP site, optionally specifying domain, system username, and PHP version')
    print('sw php change [example.com [7.3]]  # Change the PHP version of a site, optionally specifying domain, and PHP version')
    print('sw php disable [example.com]  # Disable a PHP vhost')
    print('sw php enable [example.com]  # Enable a PHP vhost')
    print('sw php edit [example.com]  # Edit a PHP vhost and restart the appropriate PHP version upon exit')
    print('sw php (delete|remove) [example.com]  # Delete a PHP vhost')
    print('sw php status  # Get the service status output for all enabled PHP versions')
index = command_index.CategoryIndex('php', _help)

def _add(domain, more):
    from libsw import php
    if not domain:
        domain = input_util.input_domain()
    sys_user = False
    php_version = False
    if more:
        sys_user = more[0]
        if len(more) > 1:
            php_version = more[1]
        else:
            php_version = php.select_version()
    else:
        from libsw import user
        sys_user = user.select_user()
        php_version = php.select_version()
    php.make_vhost(sys_user, domain, php_version)
index.register_command('add', _add)
index.register_command('create', _add)

def _enable(domain):
    from libsw import php
    if not domain:
        conf = php.select_disabled_conf('Select website to enable.')
        domain = conf['file']
    php.enable_vhost(domain)
index.register_command('enable', _enable)

def _disable(domain):
    from libsw import php
    if not domain:
        conf = php.select_conf('Select website to disable.')
        domain = conf['file']
    php.disable_vhost(domain)
index.register_command('disable', _disable)

def _remove(domain):
    from libsw import php
    if not domain:
        domain = php.select_conf('Select website to remove.')['file']
    php.remove_vhost(domain)
index.register_command('remove', _remove)
index.register_command('delete', _remove)

def _edit(domain):
    from libsw import php
    if domain == False:
        domain = php.select_conf('Select website to edit.')
    php.edit_vhost(domain['file'])
index.register_command('edit', _edit)

def _list(disabled):
    from libsw import php
    from tabulate import tabulate
    if disabled:
        disabled = disabled.lower()
        if disabled != 'disabled':
            disabled = False
    php_list = []
    if disabled:
        php_list = php.get_disabled_conf_files()
    else:
        php_list = php.get_conf_files()
    table_array = []
    for conf_file in php_list:
        sys_user = php.user_from_domain(conf_file['file'], conf_file['version'])
        table_array.append([conf_file['file'], conf_file['version'], sys_user])
    if len(table_array) > 0:
        print()
        print(tabulate(table_array, headers=['Domain', 'Version', 'System User']))
        print()
    else:
        print('No PHP sites found')
index.register_command('list', _list)

#TODO Move this to a universal uninstall function
# def _uninstall(subversion):
#     from libsw import php, version
#     if subversion:
#         subversion = version.get_tree(subversion)['sub']
#     else:
#         subversion = php.select_version()
#     php.DisableVersion(subversion).run()
#     php.remove_environment(subversion)
# index.register_command('uninstall', _uninstall)

def _change(domain, more):
    from libsw import php
    if domain != False:
        domain = domain.lower()
    file_entry = False
    if domain != False:
        for entry in php.get_conf_files():
            if entry['file'].lower() == domain:
                file_entry = entry
                break
        print('Unable to locate ' + domain)
    if file_entry == False:
        file_entry = php.select_conf("Select PHP site to change")
    old_version = file_entry['version']
    domain = file_entry['file']
    old_file = file_entry['fullPath']

    print('Selected ' + domain + ' which is currently using ' + old_version)

    new_version = False
    if more == False:
        new_version = php.select_version([old_version])
    else:
        new_version = more[0]

    php.change_version(domain, old_version, new_version)
index.register_command('change', _change)

def _status(subversion):
    from libsw import php
    for ver, status in php.get_status_array():
        print(ver + ': ' + status)
index.register_command('status', _status)
