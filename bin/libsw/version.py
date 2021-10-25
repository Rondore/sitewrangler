#!/usr/bin/env python3

import re

def first_is_higher(v1, v2, case_insensitive=True):
    """
    Return a boolean value to indicate if the first software version number is
    higher than the second.

    Args:
        v1 - The first version string to compare
        v2 - The second version string to compare
    """
    v1_split = v1.split('.')
    v2_split = v2.split('.')
    higher = len(v1_split) < len(v2_split)
    i = 0
    max = len(v1_split)
    if len(v2_split) < max:
        max = len(v2_split)
    while i < max:
        v1_node = v1_split[i]
        v2_node = v2_split[i]
        if v1_node.isdigit() and v2_node.isdigit():
            v1_node = int(v1_node)
            v2_node = int(v2_node)
        elif case_insensitive:
            v1_node = v1_node.lower()
            v2_node = v2_node.lower()
        if v1_node > v2_node:
            return True
        if v2_node > v1_node:
            return False
        i += 1
    return higher

def get_tree(version):
    """
    Break a version number up and create a dictionary that contains the version
    number to different levels.

    Return:
        The dictionary contains these values:
            full - The full version string
            major - The first number in the version string
            sub - The first two numbers in the version string
            segment_count - The number of "." separated segments in the full
                version
    """
    subversion = re.match(r'([0-9]*\.[0-9]*).*', version).group(1)
    major_version = re.match(r'([0-9]*).*', version).group(1)
    return {'full': version, 'major': major_version, 'sub': subversion, 'segment_count': len(version.split('.'))}

def is_search_in_version(search, version):
    """
    Determine if the given version is a valid member of the given version search
    text.
    """
    search_segments = search.split('.')
    seg_count = len(search_segments)
    version_segments = version['full'].split('.')
    full_version_count = len(version_segments)
    for i in range(0, seg_count):
        if i > full_version_count:
            return False
        install_ver = int(version_segments[i])
        search_ver = search_segments[i]
        if search_ver.find('-') != -1:
            r = search_ver.split('-')
            if r[0] == '':
                r[0] = -99999999
            if r[1] == '':
                r[1] = 99999999
            low = int(r[0])
            high = int(r[1])
            if low > high:
                # swap numbers
                low = low + high
                high = low - high
                low = low - high
            if install_ver >= low and install_ver <= high:
                continue
            else:
                return False
        else:
            if search_ver == str(install_ver):
                continue
            else:
                return False
    return True
