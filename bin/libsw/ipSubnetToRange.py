#!/usr/bin/env python3

import sys
import ip

if __name__ == "__main__":
    try:
        ip_subnet = sys.argv[1]
    except IndexError as e:
        print('Please specify an IP subnet such as 192.168.0.0/24')
        sys.exit(1)

    if -1 == ip_subnet.find('/'):
        print('Error: No / character')
        sys.exit(1)

    low, high = ip.ip_subnet_to_range(ip_subnet)

    print(low)
    print(high)
