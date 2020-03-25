#!/usr/bin/env python3

import sys
from libsw import firewall

if __name__ == '__main__':
	ip = ''
	if len(sys.argv) > 1:
		ip = sys.argv[1]
	else:
		ip = input('Enter IP Address: ')

	# add netmask if missing
	if ip.find('/') == -1:
		print('No netmask indicated, assuming ' + ip + '/32 (an exact IP match)')
		ip = ip + '/32'

	firewall.unblock_ip(ip)
