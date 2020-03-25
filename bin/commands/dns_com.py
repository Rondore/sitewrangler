#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    from libsw import bind
    print('sw dns list  # List domains with a dedicated zone file')
    print('sw dns (add|create) [example.com]  # Add a new domain to the DNS system, reindexes zones, and restart bind')
    print('sw dns edit [example.com]  # Edit a DNS zone file and if modified, inrement the SOA and restart bind')
    print('sw dns reindex  # Reindex dns zone files (Only needed after you modify zone files outside Site Wrangler)')
    print('sw dns soa [`example.com`] [`' + bind.get_todays_soa() + '`]  # Updates the SOA for selected domain (for all domains if no domain is given)')
    print('sw dns checkexpire [`emailadmin`]  # Check for soon to expire domains in the DNS system')
    print('sw dns disable [example.com]  # Disable a zone record for a domain')
    print('sw dns enable [example.com]  # Enable a disabled zone record for a domain')
    print('sw dns (delete|remove) [example.com]  # Delete the zone record for a domain')
index = command_index.CategoryIndex('dns', _help)

def _soa(tertiary, more):
    from libsw import bind
    domain = False
    soa = False
    if tertiary != False:
        if input_util.is_domain(tertiary):
            domain = tertiary
            if more != False:
                soa = more[0]
        else:
            soa = tertiary
            if more != False:
                if input_util.is_domain(more[0]):
                    domain = more[0]
                else:
                    print('Invalid domain: ' + more[0])
                    return
    if soa != False:
        bind.die_if_bad_soa(soa)
    bind.set_soa(soa, domain)
index.register_command('soa', _soa)

def _add(domain):
    from libsw import bind
    if not domain:
        domain = input_util.input_domain()
    bind.make_zone(domain)
    bind.rebuild_zone_index()
index.register_command('add', _add)
index.register_command('create', _add)

def _enable(domain):
    from libsw import bind
    if not domain:
        domain = bind.select_disabled_zone('Select domain to enable')
    bind.enable_zone(domain)
index.register_command('enable', _enable)

def _disable(domain):
    from libsw import bind
    if not domain:
        domain = bind.select_main_domain('Select domain to disable')
    bind.disable_zone(domain)
index.register_command('disable', _disable)

def _remove(domain):
    from libsw import bind
    if not domain:
        domain = bind.select_main_domain('Select domain to remove')
    bind.remove_zone(domain)
index.register_command('remove', _remove)
index.register_command('delete', _remove)

def _list():
    from libsw import bind
    start_space = False
    for slug in sorted(bind.get_zone_file_slugs()):
        if not start_space:
            start_space = True
            print()
        print(slug)
    for slug in sorted(bind.get_disabled_zone_file_slugs()):
        if not start_space:
            start_space = True
            print()
        print(slug + ' (disabled)')
    if start_space:
        print()
    else:
        print('No DNS zone files found')
index.register_command('list', _list)

def _edit(domain):
    from libsw import bind
    if domain == False:
        domain = bind.select_main_domain("Select zone to edit")
    bind.edit_zone(domain)
index.register_command('edit', _edit)

def _reindex():
    from libsw import bind
    bind.rebuild_zone_index()
index.register_command('reindex', _reindex)

def _checkexpire(flag):
    from libsw import bind
    if flag:
        flag = flag.strip().lower()
    bind.check_expiration(flag == 'emailadmin')
index.register_command('checkexpire', _checkexpire)
