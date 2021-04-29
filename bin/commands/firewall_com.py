#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw firewall writepignore  # Update the ignored processes in the firewall and reload the firewall rules')
    print('sw firewall denyreport  # Print a report on which IP blocks have the most denied IPs')
index = command_index.CategoryIndex('firewall', _help)

def _writepignore(force):
    from libsw import firewall
    firewall.writepignore()
    firewall.reload()
index.register_command('writepignore', _writepignore)

def _print_deny_report():
    from libsw import firewall
    print(firewall.get_printed_ip_report())
index.register_command('deny-report', _print_deny_report)
index.register_command('denyreport', _print_deny_report)
