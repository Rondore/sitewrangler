#!/usr/bin/env python3

import subprocess
import re
import datetime
import glob
import dateutil.parser
import inquirer
import os
from libsw import file_filter, email, settings, input_util, service

zone_folder = '/etc/bind/zones/'

class SetSoa(file_filter.FileFilter):
    """
    SetSoa is a class that will filter though a DNS zone file and update the SOA
    serial number. The number will be updated to the number given unless the SOA
    is already at or below the given number, in which case it itterates the
    existing SOA serial by 1. If no value is given, the filter will run as
    though today's date was given.
    """
    def __init__(self, domain, soa=False):
        global zone_folder
        self.soa = soa
        super().__init__(zone_folder + domain + '.db')

    def filter_stream(self, in_stream, out_stream):
        if self.soa:
            print('Setting SOA in ' + self.filename + ' to ' + self.soa)
        else:
            print('Incrementing SOA in ' + self.filename)
        regex = re.compile(r'^(\s*)([0-9]+)(\s*;Serial Number.*)$')
        updated = False
        for line in in_stream:
            match = regex.match(line)
            if match == None:
                out_stream.write(regex.sub(r'\1', line))
            else:
                old_soa = match.group(2)
                new_soa = self.soa
                if not new_soa:
                    new_soa = get_todays_incremented_soa(old_soa)
                new_line = match.group(1) + new_soa + match.group(3) + '\n'
                out_stream.write(new_line)
                updated = True
        if not updated:
            print('Failed to find SOA line in ' + self.filename)
            print('Does the soa line end with ";Serial Number"?')
        return updated

def get_zone_file_slugs():
    """
    Return a list of all zone files excluding ".db" from the file name. Each
    slug matches the domain name the file is for.
    """
    zones = []
    for file in glob.glob(zone_folder + '*.db'):
        zones.append( file[len(zone_folder):-3] )
    zones = sorted(zones)
    return zones

def get_disabled_zone_file_slugs():
    """
    Return a list of all zone files excluding ".db" from the file name. Each
    slug matches the domain name the file is for.
    """
    zones = []
    for file in glob.glob(zone_folder + '*.db.disabled'):
        zones.append( file[len(zone_folder):-3] )
    zones = sorted(zones)
    return zones

def select_disabled_zone(query_message):
    """
    Have the user select a zone file from a list of disabled zone files. ".db"
    will not be included in the zone names.

    Args:
        query_message - The message to display to the user when asking for the
                    zone.
    """
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=get_disabled_zone_file_slugs()
                )
    ]
    conf_file_text = inquirer.prompt(questions)['f']
    return conf_file_text

def select_main_domain(query_message):
    """
    Have the user select a domain from a list that has an exisiting dedicated
    zone file.

    Args:
        query_message - The message to display to the user when asking for the
                    zone.
    """
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=get_zone_file_slugs()
                )
    ]
    conf_file_text = inquirer.prompt(questions)['f']
    return conf_file_text

def get_todays_incremented_soa(old_soa):
    """
    This generates the next SOA serial number to use after updating a zone file.
    It takes the current SOA as an argument. It will return either the existing
    SOA itterated by 1 or a fresh SOA from today\'s date. (Whichever is higher)

    Args:
        old_soa - The old SOA serial number to itterate if it matches today's date
    """
    old_soa = int(old_soa)
    today = get_todays_soa()
    if(int(today) > old_soa):
        return today
    else:
        return str(old_soa + 1)

def get_todays_soa():
    """
    Generates a fresh SOA serial number to use based on today's date.
    """
    now = datetime.datetime.now()
    soa = now.strftime('%Y%m%d01')
    return soa

def die_if_bad_soa(number):
    """
    This function takes an SOA serial number given by the user and exits if the
    input is not a valid, 10-digit SOA serial number.

    Args:
        number - The SOA serial to test
    """
    length = len(str(number))
    if length != 10:
        print('Error: SOA value does not have 10 digits. Use something like: ' + get_todays_soa())
        #TODO exit python with an error code

def set_soa(soa, domain=False):
    """
    This method bumps the SOA serial numbers in DNS zone files. If soa is False,
    today's date will be used. If domain is False or is not given, this method
    will apply to all zone files. Any zone files has an esiting SOA serial equal
    to or less than the given SOA value, it will be itterated by 1 instead of
    being set to the given SOA value.

    Args:
        soa - The new SOA value to set within the DNS zone file
        domain - The domain of the zone file you wish to update
    """
    if domain:
        SetSoa(domain, soa).run()
    else:
        for dom in get_zone_file_slugs():
            SetSoa(dom, soa).run()
    reload()

def increment_soa(domain=False):
    """
    This method increments the SOA serial number in the zone file of the given
    domain by 1. If a fresh SOA serial of today's date is higher, the fresh
    dated SOA serial is used instead.

    Args:
        domain - The primary domain of the zone file to update
    """
    if domain:
        SetSoa(domain).run()
    else:
        for dom in get_zone_file_slugs():
            SetSoa(dom).run()
    reload()

def restart():
    """
    Restart Bind.
    """
    #TODO use service.restart('bind9') instead
    subprocess.run(['/etc/init.d/bind9', 'restart'])

def reload():
    """
    Reload Bind configuration.
    """
    service.reload('bind9')

def write_zone_index_header(open_file):
	open_file.write('//\n')
	open_file.write('// Do any local configuration here\n')
	open_file.write('//\n')
	open_file.write('\n')
	open_file.write('// Consider adding the 1918 zones here, if they are not used in your\n')
	open_file.write('// organization\n')
	open_file.write('//include "/etc/bind/zones.rfc1918";\n')

def rebuild_zone_index():
    """
    Rebuild the list of zone files within the configuration file
    "/etc/bind/named.conf.local". All files ending in ".db" in the folder
    "/etc/bind/zones/" are included in the new index.
    Bind is reloaded to apply the new index.
    """
    #TODO update an area of the configuration file within START and END comments instead of replacing the whole thing
    save_file="/etc/bind/named.conf.local"
    with open(save_file, 'w') as output:
    	write_zone_index_header(output)
    	zone_files = glob.glob('/etc/bind/zones/*.db')
    	for file in zone_files:
    		domain = re.match(r'.*/([^/]*)\.db', file).group(1)
    		output.write('\n')
    		output.write('zone "' + domain + '" {\n')
    		output.write('	type master;\n')
    		output.write('	file "' + file + '";\n')
    		output.write('};\n')
    reload()

def zone_filename(domain):
    """
    Get the full path to use for a zone file for a given domain.

    Args:
        domain - The primary domain of the zone file
    """
    return zone_folder + domain + '.db'

def make_zone(domain):
    """
    Create a new zone file for the given domain name. The new zone file is
    populated with values for the new domain. The index of zone files is not
    rebuilt to include the new zone and Bind is not restarted or reloaded.

    Args:
        domain - The primary domain of the zone file
    """
    if not os.path.exists(zone_folder):
        os.mkdir(zone_folder)
    template = open(settings.get('install_path') + 'etc/zone-file', 'r')
    ns1 = settings.get('nameserver_one')
    ns2 = settings.get('nameserver_two')
    dns_authority = settings.get('dns_authority')
    ip = settings.get('public_ip')
    with open(zone_filename(domain), 'w') as zone:
        for line in template:
            line = line.replace('DOMAINNAMEE', domain, 10000)
            line = line.replace('NAMESERVER_ONEE', ns1, 10000)
            line = line.replace('NAMESERVER_TWOO', ns2, 10000)
            line = line.replace('DNS_AUTHORITYY', dns_authority, 10000)
            line = line.replace('PUBLIC_IPP', ip, 10000)
            zone.write(line)

def enable_zone(domain):
    """
    Enable a zone file that has previously been disabled.

    Args:
        domain - The primary domain of the zone file to enable
    """
    target = zone_filename(domain)
    source = target + '.disabled'
    os.rename(source, target)
    rebuild_zone_index()
    return True

def disable_zone(domain):
    """
    Disable a zone file. This will cause the site to go down if this server is the domain's nameserver

    Args:
        domain - The primary domain of the zone file to disable
    """

    source = zone_filename(domain)
    target = source + '.disabled'
    os.rename(source, target)
    rebuild_zone_index()
    return True

def remove_zone(domain):
    """
    Delete a zone file and all DNS records within it. This will cause the site to go down if this server is the domain's nameserver

    Args:
        domain - The primary domain of the zone file to delete
    """

    enabled_path = zone_filename(domain)
    disabled_path = enabled_path + '.disabled'
    removed = False
    if os.path.exists(enabled_path):
        os.remove(enabled_path)
        removed = True
    if os.path.exists(disabled_path):
        os.remove(disabled_path)
        removed = True
    if removed:
        rebuild_zone_index()
    return removed

def edit_zone(domain):
    """
    Open a DNS zone file in the system's defaut text editor. If the user makes any changes to the file, bind will be reloaded to apply the changes.

    Args:
        domain - The primary domain of the zone file to delete
    """
    path = zone_filename(domain)
    if input_util.edit_file(path):
        print('Incrementing SOA serial and reloading bind to apply changes. Allow up to 48 hours for changes to take effect.')
        increment_soa(domain)
        reload()

def check_expiration(email_admin=False):
    """
    Check all domains registed within bind to see if any expire within two
    weeks. For each domain expred or close to expiration, a warning is printed
    to the console and also included in the return value. An extra all-clear
    message is printed to the console if there are no issues found. If
    email_admin is set to True, warnings are emailed to the server administrator
    instead of being printed.

    Args:
        email_admin - A boolean flag to dictate wether or not to send an email to the system administrator of any domains that are expired or about to expire
    """
    domains = get_zone_file_slugs()
    now = datetime.datetime.now(datetime.timezone.utc)
    output = ''
    warning_count = 0
    for dom in domains:
        expire = subprocess.getoutput("whois " + dom + " | grep '[Ee]xpir' | grep '[0-9]T[0-9]' | sed 's/.*: //'")
        if len(expire) > 0:
            #print(dom + ': ' + expire)
            expire = dateutil.parser.parse(expire)
            delta = expire - now
            delta = delta.total_seconds()
            if delta < 0:
                output += dom + ' is expired!'
            elif delta < 604800: # 604800 = one week in seconds
                output += dom + ' will expire within one week! (' + str(expire) + ')'
            elif delta < 1209600: # 1209600 = two weeks in seconds
                output += dom + ' will expire within two weeks! (' + str(expire) + ')'

    if len(output) > 0:
        if email_admin:
            email.send_admin_message('VPS Domain Notification', output)
        print(output)
    elif not email_admin:
        print('All domains are up-to-date.')
    return output
