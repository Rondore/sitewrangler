#!/usr/bin/env python3

import sys
import ip

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Error: Too Few Arguments')
        sys.exit(1)

    addr = sys.argv[1]
    range = sys.argv[2]

    if '/' not in range:
        print('Error: no mask in range')
        sys.exit(1)

    if ip.is_ip_in_range(addr,range):
        print 'true'
    else:
        print 'false'
