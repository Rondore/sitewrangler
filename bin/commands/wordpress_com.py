#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw wp list  # List WordPress websites')
    print('sw wp listinfo  # List WordPress websites along with basic information about each site')
    print('sw wp (add|create)  # Create WordPress website')
    print('sw wp clone  # Clone an existing WordpPress site to a new user and domain')
    print('sw wp login [example.com]  # Create a one-time use login link')
    print('sw wp cron [example.com]  # Create a real cron job for a WordPress site and disable the fake cron')
index = command_index.CategoryIndex('wp', _help)

def _list(domain):
    from libsw import wordpress
    sites = wordpress.list_installations()
    if len(sites) == 0:
        print('No WordPress sites found')
    else:
        print()
        for site in sites:
            print(site)
        print()
index.register_command('list', _list)

def _list_info(domain):
    from libsw import wordpress
    from tabulate import tabulate
    sites = wordpress.list_installations()
    if len(sites) == 0:
        print('No WordPress sites found')
    else:
        table = []
        for site in sites:
            version = wordpress.get_version(site)
            wp_cron_disabled = wordpress.wp_cron_disabled(site)
            sys_cron = wordpress.sys_cron_enabled(site)
            cron_status = 'Error'
            if wp_cron_disabled and sys_cron:
                cron_status = 'System'
            elif wp_cron_disabled:
                cron_status = 'Disabled'
            elif sys_cron:
                cron_status = 'Redundant'
            else:
                cron_status = 'WordPress'
            table.append([site, version, cron_status])
        print()
        print(tabulate(table, headers=['Domain', 'Version', 'Cron Type']))
        print()
index.register_command('listinfo', _list_info)

def _addwordpress():
    from libsw import wordpress
    wordpress.wizard_make_site()
index.register_command('add', _addwordpress)
index.register_command('create', _addwordpress)

def _clonewordpress():
    from libsw import wordpress
    wordpress.wizard_clone_site()
index.register_command('clonewp', _clonewordpress)
index.register_command('clonewordpress', _clonewordpress)

def _createlogin(domain):
    from libsw import wordpress
    if domain and not wordpress.is_wordpress_installation(domain):
        print(domain + ' is not a domain with a valid WordPress installation')
        domain = False
    if domain == False:
        domain = wordpress.select_installation('Select domain to log in to')
    wordpress.create_one_time_login(domain)
index.register_command('login', _createlogin)

def _cron(domain):
    from libsw import wordpress, nginx
    if domain and not wordpress.is_wordpress_installation(domain):
        print(domain + ' is not a domain with a valid WordPress installation')
        domain = False
    if domain == False:
        domain = wordpress.select_installation('Select domain to add receive the cron')
    sys_user = nginx.user_from_domain(domain)
    wordpress.add_cron(sys_user)
index.register_command('cron', _cron)
