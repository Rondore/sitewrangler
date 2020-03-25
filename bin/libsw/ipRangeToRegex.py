#!/usr/bin/env python3

import sys
import ip

if __name__ == "__main__":
    if len(sys.argv) == 2:
        try:
            arg = sys.argv[1]
            index = arg.index('/')
            low, high = ip.ip_subnet_to_range(arg)
            sys.argv = (sys.argv[0], low, high)
            #print 'Converted subnet to ' + range[0] + ' and ' + range[1]
        except ValueError:
            pass

    if len(sys.argv) < 3:
        print "Not enough arguments"
        sys.exit(1)

    low_ip = sys.argv[1]
    high_ip = sys.argv[2]
    #print 'Creating regex for IP range ' + low_ip + ' - ' + high_ip

    #TODO add command line argument for strict match
    print( ip.ip_range_to_regex(low_ip,high_ip) )
