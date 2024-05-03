#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw php list [`disabled`]  # List PHP sites along with PHP versions and system usernames')
    print('sw php (add|create) [example_user [7.3]]  # Create a PHP site, optionally specifying system username, and PHP version')
    print('sw php change [example_user [7.3]]  # Change the PHP version of a site, optionally specifying username, and PHP version')
    print('sw php disable [example_user]  # Disable a PHP vhost')
    print('sw php enable [example_user]  # Enable a PHP vhost')
    print('sw php edit [example_user]  # Edit a PHP vhost and restart the appropriate PHP version upon exit')
    print('sw php (delete|remove) [example_user]  # Delete a PHP vhost')
    print('sw php status  # Get the service status output for all enabled PHP versions')
index = command_index.CategoryIndex('php', _help)

def _add(username, more):
    from libsw import php
    if not username:
        from libsw import user
        username = user.select_user()
    php_version = False
    if more:
        php_version = more[0]
    else:
        php_version = php.select_version()
    php.make_vhost(username, php_version)
index.register_command('add', _add)
index.register_command('create', _add)

def _enable(username):
    from libsw import php
    if not username:
        conf = php.select_disabled_conf('Select user to enable.')
        username = conf['file']
    php.enable_vhost(username)
index.register_command('enable', _enable)

def _disable(username):
    from libsw import php
    if not username:
        conf = php.select_conf('Select user to disable.')
        username = conf['file']
    php.disable_vhost(username)
index.register_command('disable', _disable)

def _remove(username):
    from libsw import php
    if not username:
        username = php.select_conf('Select user to remove.')['file']
    php.remove_vhost(username)
index.register_command('remove', _remove)
index.register_command('delete', _remove)

def _edit(username):
    from libsw import php
    if username == False:
        username = php.select_conf('Select user to edit.')['file']
    php.edit_vhost(username)
index.register_command('edit', _edit)

def _list(disabled):
    from libsw import php, nginx
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
        sys_user = conf_file['file']
        domain_list = nginx.get_user_domains(sys_user)
        enabled_domains = domain_list[0]
        disabled_domains = []
        for site in domain_list[1]:
            disabled_domains.append('(' + site + ')')
        domain_list = ','.join(enabled_domains)
        if len(domain_list) > 0 and len(disabled_domains) > 0:
            domain_list += ','
        domain_list += ','.join(disabled_domains)
        table_array.append([sys_user, conf_file['version'], domain_list])
    if len(table_array) > 0:
        print()
        print(tabulate(table_array, headers=['System User', 'Version', 'Domain(s)']))
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

def _change(username, more):
    from libsw import php
    if username != False:
        username = username.lower()
    file_entry = False
    if username != False:
        for entry in php.get_conf_files():
            if entry['file'].lower() == username:
                file_entry = entry
                break
    if file_entry == False:
        if username != False:
            print('Unable to locate ' + username)
        file_entry = php.select_conf("Select PHP site to change")
    old_version = file_entry['version']
    username = file_entry['file']

    print('Selected ' + username + ' which is currently using ' + old_version)

    new_version = False
    if more == False:
        new_version = php.select_version([old_version])
    else:
        new_version = more[0]

    php.change_version(username, old_version, new_version)
index.register_command('change', _change)

def _status(subversion):
    from libsw import php
    for ver, status in php.get_status_array():
        print(ver + ': ' + status)
index.register_command('status', _status)
