#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw wp list  # List WordPress websites')
    print('sw wp listinfo  # List WordPress websites along with basic information about each site')
    print('sw wp (add|create)  # Create WordPress website')
    print('sw wp clone  # Clone an existing WordpPress site to a new user and domain')
    print('sw wp login [example.com]  # Create a one-time use login link')
    print('sw wp cron [example.com]  # Create a real cron job for a WordPress site and disable the fake cron')
    print('sw wp listupdate [example.com]  # List needed updates to WordPress core, plugin, and theme files')
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

def _listupdate(domain):
    from libsw import wordpress
    sites = [domain]
    all_up_to_date = True
    single = False
    if domain == False:
        sites = wordpress.list_installations()
    else:
        single = True
    if len(sites) == 0:
        print('No WordPress sites found')
    else:
        print()
        for site in sites:
            outdated = wordpress.get_outdated(site)
            core = len(outdated[0]) > 0
            theme_count = len(outdated[1])
            plugin_count = len(outdated[2])
            if theme_count + plugin_count > 0 or core:
                all_up_to_date = False
                space = ''
                if not single:
                    print('== ' + site + ' ==')
                    space = '  '
                if core:
                    print(space + '-- Core Wordpress --')
                    print(space + '   ' + outdated[0])
                if theme_count > 0:
                    print(space + '-- Themes --')
                    for theme in outdated[1]:
                        print(space + '   ' + theme)
                if plugin_count > 0:
                    print(space + '-- Plugins --')
                    for plugin in outdated[2]:
                        print(space + '   ' + plugin)
        print()
    if all_up_to_date:
        if single:
            print(domain + ' is up-to-date')
        else:
            print('Everything WordPress is up-to-date')
index.register_command('listupdate', _listupdate)
index.register_command('list-update', _listupdate)

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
        domain = wordpress.select_installation('Select a domain to log in to')
    wordpress.create_one_time_login(domain)
index.register_command('login', _createlogin)

def _cron(domain):
    from libsw import wordpress, nginx
    if domain and not wordpress.is_wordpress_installation(domain):
        print(domain + ' is not a domain with a valid WordPress installation')
        domain = False
    if domain == False:
        domain = wordpress.select_installation('Select a domain to add a cron job')
    sys_user = nginx.user_from_domain(domain)
    wordpress.add_cron(sys_user)
index.register_command('cron', _cron)

def _installcli():
    from libsw import wordpress
    wordpress.install_wp_cli()
    print()
    print('Up-to-date Wordpress CLI Installed')
index.register_command('install-cli', _installcli)
index.register_command('installcli', _installcli)
index.register_command('update-cli', _installcli)
index.register_command('updatecli', _installcli)
