#!/usr/bin/env python3
# $1 = ip, $2 (optional) = block note

import sys
from libsw import firewall

if __name__ == "__main__":
  blocked_ip = ''
  note = ''
  if len(sys.argv) > 1:
    blocked_ip = sys.argv[1]
    if len(sys.argv) > 2:
        note = sys.argv[2]
  else:
    blocked_ip = input("Enter IP Address: ")
    note = input("Note for block (optional): ")
  if len(note) == 0:
    note = "Manually denied"
  firewall.block_ip_addr(blocked_ip, note)
