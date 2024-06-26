#!/usr/bin/env python3

import sys
import re
import iptc
import datetime
import subprocess
from libsw import file_filter, ip

deny_file = '/etc/csf/csf.deny'

def rule_matches_ip(rule, binary_ip):
    """
    Check if an iptables rule contains a given IP address.

    Args:
        rule - A raw iptables rule
        binary_ip - The IP address to check in a binary formated string
    """
    match_addr = ''
    if( rule.target.name == 'DROP' ):
        match_addr = rule.src
    elif( rule.target.name == 'LOGDROPOUT' ):
        match_addr = rule.dst
    else:
        return False
    base_ip, mask = ip.unmask_ip(match_addr)
    if base_ip == '0.0.0.0':
        return False
    binary_base_ip = ip.ip_to_binary(base_ip)
    masked_ip = binary_base_ip[:mask]
    masked_check_ip = binary_ip[:mask]
    if masked_ip == masked_check_ip:
        return match_addr
    else:
        return False

def check_ip_for_blocks(check_ip):
    """
    Check to see if an IP address is blocked by the system firewall.

    Args:
        check_ip - The IP address or masked IP address to check
    """
    base_ip, mask = ip.unmask_ip(check_ip)
    binary_ip = ip.ip_to_binary(base_ip)
    table = iptc.Table(iptc.Table.FILTER)
    block_range = ''
    print_help = True
    for chain in table.chains:
        for rule in chain.rules:
            matched_ip = rule_matches_ip(rule, binary_ip)
            if matched_ip != False:
                return matched_ip
    return False

def lift_ip_table_rules(check_ip):
    """
    Remove all rules in iptables that block the given IP.

    Args:
        check_ip - The IP address or masked IP address to check
    """
    base_ip, mask = ip.unmask_ip(check_ip)
    binary_ip = ip.ip_to_binary(base_ip)
    table = iptc.Table(iptc.Table.FILTER)
    block_range = ''
    print_head = True
    for chain in table.chains:
        for rule in chain.rules:
            match_addr = rule_matches_ip(rule, binary_ip)
            if match_addr:
                chain.delete_rule(rule)
                if print_head:
                    print_head = False
                    print('Deleting iptables rule(s):')
                print(match_addr)

def block_ip_addr(ip, note):
    """
    Block an IP address by manually adding it to both csf.deny and iptables.
    Using "csf -d $ip Note" is preferred.

    Args:
        check_ip - The IP address or masked IP address to block
    """
    # add netmask if missing
    if ip.find('/') == -1:
        print("No netmask indicated, assuming ' + ip + '/32 (an exact IP match)")
        ip = ip + '/32'

    now = datetime.datetime.now()
    subprocess.run(['iptables', '-A', 'DENYIN', '-s', ip, '!', '-i', 'lo', '-j', 'DROP'])
    subprocess.run(['iptables', '-A', 'DENYOUT', '-d', ip, '!', '-o', 'lo', '-j', 'LOGDROPOUT'])
    with open(deny_file, 'a+') as blockfile:
        blockfile.write(ip + ' # ' + note + ' - ' + now.strftime('%a %b %d %H:%M:%S %Y'))

def find_csf_block(ip_address):
    """
    Check if an IP address is blocked by the csf.deny file.

    Args:
        check_ip - The IP address or masked IP address to check
    """
    ip_search_string = ip_address.replace('.', r'\.')
    if ip_address.endswith('/32'):
        ip_search_string = ip_search_string[:-3] + '(/32)?'
    elif ip_address.find('/') == -1:
        ip_search_string = ip_search_string + '(/32)?'
    ip_search_string = '^' + ip_search_string + '( .*)?$'
    matches = []
    with open(deny_file) as deny_list:
        search = re.compile(ip_search_string)
        for line in deny_list:
            if search.match(line):
                matches.append(line)
    return matches

def convert_rules_to_removal(rule_array):
    """
    Convert existing iptables rules to the iptables arguments needed to remove
    the rules.

    Args:
        rule_array - An array of strings that each contain an iptables rule
    """
    removal = []
    for rule in rule_array:
        removal.append('-D' + rule[2:]) # replace -A with -D
    return removal

class LiftCsfRules(file_filter.FileFilter):
    """
    A FileFilter to remove any csf.deny rules that target any IP address in a
    list.
    """
    def __init__(self, rule_array):
        self.rules = rule_array
        super().__init__(deny_file)

    def filter_stream(self, inflow, outflow):
        found = False
        for line in inflow:
            found_in_line = False
            for rule in self.rules:
                if rule == line:
                    found_in_line = True
                    found = True
                    print('Deleted deny entry:')
                    print(line)
                    break
            if not found_in_line:
                outflow.write(line)
        return found

def unblock_ip(ip_address):
    """
    Unblock a given IP address or masked IP address.

    Args:
        check_ip - The IP address or masked IP address to check
    """
    csf_rules = find_csf_block(ip_address)

    lift_ip_table_rules(ip_address)
    LiftCsfRules(csf_rules).run()

def writepignore():
    from libsw import php, version, nginx
    import os
    if not os.path.exists('/etc/csf/'):
        # CSF is not installed, skip
        return False
    ignore = "# Do not edit this section\n"
    ignore += """exe:/bin/bash
exe:/lib/systemd/systemd
exe:/usr/sbin/uuidd
exe:/usr/bin/memcached
exe:/usr/bin/screen
exe:/usr/lib/dovecot/anvil
exe:/usr/lib/dovecot/imap
exe:/usr/lib/dovecot/imap-login
exe:/usr/lib/dovecot/auth
exe:/usr/lib/dovecot/stats
exe:/usr/sbin/atd
exe:/usr/sbin/rsyslogd
exe:/usr/lib/openssh/sftp-server
exe:/bin/nano
exe:/usr/bin/vi
exe:/usr/bin/vim
exe:/usr/bin/emacs
exe:/usr/bin/less
exe:/bin/less
exe:/usr/bin/spamc
exe:/usr/bin/spamd
cmd:spamd child
exe:/usr/bin/freshclam
exe:/usr/sbin/clamd
"""
    ignore += 'exe:' + nginx.binary_file + '\n'
    ignore += 'exe:' + nginx.binary_file + '.old\n'

    for ver in php.get_versions():
        ver = version.get_tree(ver)['sub']
        ignore += "exe:" + php.php_build_path(ver) + "sbin/php-fpm\n"
    start_text = '# Start Site Wrangler Rules'
    end_text = '# End Site Wrangler Rules'
    filename = '/etc/csf/csf.pignore'
    success = file_filter.UpdateSection(filename, start_text, end_text, ignore).run()
    return success

def reload():
    pass
    #subprocess.call('csf -r')

def get_blocked_ip_report():
    deny_file = '/etc/csf/csf.deny'
    report = ''
    ip_ranges = []
    ip_deny_lists = {}
    with open(deny_file) as deny_content:
        for block in deny_content:
            ip = block.split('#')[0].strip()
            if len(ip) == 0:
                continue
            split_ip = ip.split('/')[0].split('.')
            range = '.'.join(split_ip[:2])
            if range not in ip_ranges:
                ip_ranges.append(range)
                ip_deny_lists[range] = []
            ip_deny_lists[range].append(block)
    counted_ip_ranges = []
    for range in ip_ranges:
        counted_ip_ranges.append([range, len(ip_deny_lists[range])])
    counted_ip_ranges = sorted(counted_ip_ranges, key=lambda x: x[1], reverse=True)
    return counted_ip_ranges, ip_deny_lists

def get_printed_ip_report():
    report = ''
    counted_ip_ranges, ip_deny_list = get_blocked_ip_report()
    counted_ip_ranges = counted_ip_ranges[:10]
    counted_ip_ranges.reverse()
    for counted_range in counted_ip_ranges:
        range, count = counted_range
        deny_list = ip_deny_list[range]
        ip_list = list(map(lambda x: x.split('#')[0].strip(), deny_list))
        ip_match_pattern = get_common_ip_segment(ip_list)
        if len(report) > 0:
            report += '\n'
        report += ' ### ' + ip_match_pattern
        if len(deny_list) > 1:
            report += '*'
        report += ' ###\n'
        report += 'IP Count: ' + str(len(deny_list)) + '\n\n'
        for deny in deny_list[:10]:
            report += deny
    return report

def get_common_ip_segment(ip_array):
    if len(ip_array) == 0:
        return ''
    match = ''
    for i in range(0, len(ip_array[0])):
        match_char = ip_array[0][i]
        for ip in ip_array:
            if ip[i] != match_char:
                return match
        match += match_char
    return match
