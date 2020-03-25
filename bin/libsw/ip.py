#!/usr/bin/env python3

import re

debug = False
def _debug_print(string):
    """
    Print a debug message only if debug is set to True.

    Args:
        string - The debug output
    """
    if debug:
        print(string)

def ip_to_binary(ip):
    """
    Convert an IPv4 address to a string containing the binary conversion of the
    IP address.

    Args:
        ip - The ip address to convert
    """
    return "".join([bin(int(x)+256)[3:] for x in ip.split('.')])

def binary_to_ip(binary):
    """
    Convert an IPv4 address in a binary format to a string containing the IP in
    base 10.

    Args:
        ip - The ip address in binary format to convert
    """
    dec_ip = ''
    dot = False
    for i in range(0, 4):
        start_pos = i * 8
        binary_chunk = binary[ start_pos : (start_pos+8) ]
        if dot:
            dec_ip += '.'
        else:
            dot = True
        dec_ip += str(int(binary_chunk, 2))
    return dec_ip

def ip_subnet_to_range(ip_subnet):
    """
    Convert a masked IP to a tuple containg the lowest and highest IP addresses
    in that range.

    Args:
        ip_subnet - The masked IP
    """
    split_index = ip_subnet.index('/')

    base = ip_subnet[:split_index]
    subnet = int(ip_subnet[split_index+1:])

    base_binary = ip_to_binary(base)[:subnet]

    high = base_binary
    low = base_binary
    for i in range(0, (32-subnet)):
        high += '1'
        low += '0'

    high_ip = binary_to_ip(high)
    low_ip = binary_to_ip(low)
    return low_ip, high_ip

def is_ip_in_range(ip, range):
    """
    Determin if an IP address is contained in an IP address range.

    Args:
        ip - The IP address to check
        range - The masked IP
    """
    split_range = range.split('/')
    range_mask = int(split_range[1])
    base_range = split_range[0]
    binary_base_range = ip_to_binary(base_range)
    masked_range = binary_base_range[:range_mask]
    masked_test_ip = ip_to_binary(ip)[:range_mask]
    return masked_range == masked_test_ip

def make_octal_regex(low, high):
    """
    Generate a regular expression that matches a given IPv4 address segment
    range.

    Args:
        low - The lowest IP segment that will match the generated regex (0-255)
        high - The highest IP segment that will match the generated regex
            (0-255)
    """
    high = str( high )
    low = str( low )

    if debug:
        print('Creating range for ' + low + ' - ' + high)
    if len(low) > 0 and int(low) > int(high):
        raise Exception('High lower than Low. Low: ' + low + ' High: ' + high)
    if len(low) > 0 and int(low)==0 and int(high)==255:
        return full_range
    if low == high:
        return low

    digits = len( high )
    low_digits = len( low )

    regex = ''

    if low_digits == 0:
        # Only reachable as prefix to a '[0-9]'
        if digits > 1:
            high_single = high[-1:]
            high = high[:-1]

            if high_single == '9':
                _debug_print('Form 1A')
                regex = '(' + make_octal_regex(low, high) + '[0-9])?'
            else:
                _debug_print('Form 1B')
                #high = high[:-1]
                #regex = '(' + make_octal_regex(low, int(high)-1) + '[0-9]|' + high + '[0-' + high_single + '])?'
                regex = '([0-9]|' + high + '[0-' + high_single + '])?'
        else:
            if high == '1':
                _debug_print('Form 1C')
                regex = '1?'
            else:
                high_single = high[-1:]
                _debug_print('Form 1D')
                regex = '[1-' + high_single + ']?'
    else:

        high_single = high[-1:]
        low_single = low[-1:]
        high = high[:-1]
        low = low[:-1]

        if low == high:
            _debug_print('Form 2')
            regex = low + '[' + low_single + '-' + high_single + ']'
        else:
            low_numeric = 0
            if len(low) > 0:
                low_numeric = int(low)
            if low_single == '0' and high_single == '9':
                _debug_print('Form 3A')
                regex = make_octal_regex(low, high) + '[0-9]'
            elif low_single == '0':
                if int(high) == 1:
                    _debug_print('Form 3B')
                    regex = '(' + '[0-9]' + '|' + high + '[0-' + high_single + '])'
                else:
                    _debug_print('Form 3C')
                    regex = '(' + make_octal_regex(low, int(high) - 1) + '[0-9]' + '|' + high + '[0-' + high_single + '])'
            elif high_single == '9':
                _debug_print('Form 3D')
                regex = '(' + low + '[' + low_single + '-9]|' + make_octal_regex(low_numeric + 1, high) + '[0-9])'
            elif low_numeric == (int(high) - 1):
                _debug_print('Form 3E')
                regex = '(' + low + '[' + low_single + '-9]|' + high + '[0-' + high_single + '])'
            else:
                _debug_print('Form 3F')
                regex = '(' + low + '[' + low_single + '-9]|' + make_octal_regex(low_numeric + 1, int(high) - 1) + '[0-9]|' + high + '[0-' + high_single + '])'
    return regex

def optimize_regex(regex):
    """
    Reduce overly verbose parts of a generated regex expression.

    Args:
        regex - The regex expressio to optimize
    """
    regex = str(regex)
    for n in range(9):
        regex = regex.replace('[' + str(n) + '-' + str(n+1) + ']','[' + str(n) + str(n+1) + ']')
    for n in range(10):
        regex = regex.replace('[' + str(n) + '-' + str(n) + ']', str(n))
    return regex

def ip_range_to_regex(low_ip, high_ip, strict=False):
    """
    Generate a regular expression that matches a given IPv4 address segment
    range.

    Args:
        low_ip - The lowest IP segment that will match the generated regex
            (0-255)
        high_ip - The highest IP segment that will match the generated regex
            (0-255)
        strict - (optional) If set to True, the generated regex will only match
            proper IP addresses where each section is in the range 0-255
    """
    if low_ip == high_ip:
        return '\.'.join(low_ip.split('.'))

    full_range = '[0-9]*'
    if(strict):
        full_range = '(1?[0-9]?[0-9]|2([0-4][0-9]|5[0-5]))'
    split_low = low_ip.split('.')
    split_high = high_ip.split('.')

    regex = ""
    regex_octets = 0
    for o in range(4):
        regex_octets += 1
        if split_low[o] == split_high[o]:
            regex += split_low[o] + '\.'
        else:
            regex += optimize_regex( make_octal_regex(split_low[o], split_high[o]) )
            break

    while(regex_octets < 4):
        regex += '\.' + full_range
        regex_octets += 1
    return regex

def unmask_ip(masked_ip):
    """
    Convert an IP address that optionally contains a netmask to a seperate IP
    address and mask.

    Args:
        The IP address to unmask

    Return:
        A tuple containing the IP address followed by the mask
    """
    mask = 32
    base_ip = masked_ip
    slash = masked_ip.find('/')
    if slash != -1:
        mask = masked_ip[slash+1:]
        base_ip = masked_ip[:slash]
    if '.' in str(mask):
        mask_map = ip_to_binary(mask)
        mask = len(re.match(r'(^1*)(.*)', mask_map).group(1))
    else:
        mask = int(mask)
    return base_ip, mask
