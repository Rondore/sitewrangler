#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw nginx list [`disabled`]  # List nginx sites along with system usernames')
    print('sw nginx (add|create) [example.com [example_username]]  # Create a website, optionally specifying domain, system username')
    print('sw nginx addssl [example.com]  # Convert a non-ssl nginx vhost file to one that uses a certificate from Let\'s Encrypt')
    print('sw nginx enable [example.com]  # Enable an nginx vhost')
    print('sw nginx disable [example.com]  # Disable an nginx vhost')
    print('sw nginx edit [example.com]  # Edit an nginx vhost and reload the nginx configuration upon exit')
    print('sw nginx (delete|remove) [example.com]  # Delete an nginx vhost')
    print('sw nginx bypass[modsec] [example.com [0000]]  # Bypass a ModSecurity rule id')
    print('sw nginx unbypass[modsec] [example.com [0000]]  # Remove a bypass for a ModSecurity rule id')
    print('sw nginx listbypass[modsec] [example.com]  # List the rules bypassed for a given domain')
index = command_index.CategoryIndex('nginx', _help)

def _enable(domain):
    from libsw import nginx
    if domain == False:
        domain = nginx.select_disabled_conf('Select domain to enable')
    if nginx.enable_vhost(domain):
        print(domain + ' enabled')
    else:
        print('Unable to find disabled vhost file for ' + domain)
index.register_command('enable', _enable)

def _disable(domain):
    from libsw import nginx
    if domain == False:
        domain = nginx.select_conf('Select domain to disable')
    if nginx.disable_vhost(domain):
        print(domain + ' disabled')
    else:
        print('Unable to find enabled vhost file for ' + domain)
index.register_command('disable', _disable)

def _add(domain, more):
    from libsw import nginx, user, cert
    if domain == False:
        domain = input_util.input_domain()
    username = False
    template = False
    if more != False:
        username = more[0]
        if len(more) > 1:
            template = more[1]
    if username != False and not user.exists(username):
        username = False
    if username == False:
        username = user.select_user()
    hide_ssl = True
    if cert.has_cert(domain):
        hide_ssl = False
    if template == False:
        template = nginx.choose_template("Select a vhost template: ", hide_ssl)
    nginx.make_vhost(username, domain, template)
index.register_command('add', _add)
index.register_command('create', _add)

def _remove(domain):
    from libsw import nginx
    if domain == False:
        domain = nginx.select_conf('Select domain to delete')
    nginx.remove_vhost(domain)
index.register_command('remove', _remove)
index.register_command('delete', _remove)

def _bypass(domain, more):
    from libsw import nginx
    if domain == False:
        domain = nginx.select_conf('Select domain to add the bypass')
    rule_id = False
    if more != False:
        rule_id = more[0]
    if rule_id == False:
        rule_id = input('Enter Rule ID: ')
    nginx.bypass_modsec_rule(domain, rule_id)
index.register_command('bypass', _bypass)
index.register_command('bypassmodsec', _bypass)

def _unbypass(domain, more):
    from libsw import nginx
    if domain == False:
        domain = nginx.select_conf('Select domain to remove the bypass')
    rule_id = False
    if more != False:
        rule_id = more[0]
    if rule_id == False:
        rule_id = input('Enter Rule ID: ')
    nginx.unbypass_modsec_rule(domain, rule_id)
index.register_command('unbypass', _unbypass)
index.register_command('unbypassmodsec', _unbypass)

def _listbypass(domain):
    from libsw import nginx
    if domain == False:
        domain = nginx.select_conf('Select domain to list')
    rules = nginx.get_bypassed_modsec_rules(domain)
    for r in rules:
        print(r)
index.register_command('listbypass', _listbypass)
index.register_command('listbypassmodsec', _listbypass)

def _addssl(domain):
    from libsw import nginx
    if domain == False:
        domain = nginx.select_conf("Select config file")
    if not nginx.add_ssl_to_site_hosts(domain):
        print('Error. Unable to add SSL.')
index.register_command('addssl', _addssl)

def _edit(domain):
    from libsw import nginx
    if domain == False:
        domain = nginx.select_conf("Select config file")
    nginx.edit_vhost(domain)
index.register_command('edit', _edit)

def _list(disabled):
    from libsw import nginx
    from tabulate import tabulate
    if disabled:
        disabled = disabled.lower()
        if disabled != 'disabled':
            disabled = False
    nginx_list = []
    if disabled:
        nginx_list = nginx.disabled_sites()
    else:
        nginx_list = nginx.enabled_sites()
    table_array = []
    for domain in nginx_list:
        sys_user = nginx.user_from_domain(domain)
        table_array.append([domain, sys_user])
    if len(table_array) > 0:
        print()
        print(tabulate(table_array, headers=['Domain', 'System User']))
        print()
    else:
        print('No nginx sites found')
index.register_command('list', _list)
