#!/usr/bin/env python3

import sys
import os
import re
from libsw import ip, firewall

if __name__ == '__main__':
    check_ip = ''
    if len(sys.argv) > 1:
        check_ip = sys.argv[1]
    else:
        check_ip = input("Enter IP Address: " )
    blocked_ip = firewall.check_ip_for_blocks(check_ip)
    csf_lines = firewall.find_csf_block(check_ip)

    if blocked_ip == False and len(csf_lines) == 0:
        print("\nNo block found\n")
    else:
        print('')
        if blocked_ip != False:
            print(check_ip + ' found blocked in ip range ' + blocked_ip + ' in iptables')
        if len(csf_lines) > 0:
            print('Listed deny entries:')
            # grep_ip = blocked_ip.replace('.', r'\.')
            # try:
            #     slash = grep_ip.index('/32')
            #     grep_ip = '^' + grep_ip[:slash] + '(/32)?( .*)?$'
            # except ValueError:
            #     pass
            # ip_regex = re.compile(grep_ip)
            # with open('/etc/csf/csf.deny') as blocklist:
            #     for line in blocklist:
            #         if ip_regex.match(line):
            #             print(line)

            for line in csf_lines:
                print(line)
        input('\nPress enter to unblock ' + check_ip + ' or Ctrl + C to cancel\n')
        firewall.unblock_ip(check_ip)
