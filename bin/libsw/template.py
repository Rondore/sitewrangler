#!/usr/bin/env python3

import os
import re
from libsw import settings

def append_missing_variable(variable_array, key, value):
    """
    Add a value that is used for populating a vhost file if not already present.
    Each value is stored as [name, value] within the parent array.

    Args:
        variable_array - The parrent array into which the value is added if missing
        key - The name of the variable
        value - The value of the variable
    """
    found = False
    for ke, val in variable_array:
        if key == ke:
            found = True
            break
    if not found:
        variable_array.append([key, value])
    return variable_array

def get_template_vars(existing_fields=[]):
    """
    Add any missing standard values that are used for populating a template file.
    Each value is stored as [name, value] within the parent array.

    Args:
        existing_fields - The parrent array into which any missing values are added
    """
    local_ip = settings.get('local_ip')
    public_ip = settings.get('public_ip')
    ip6 = settings.get('ip6')
    install_path = settings.get('install_path')
    if not ip6 or ip6 == 'False':
        ip6 = '::'
    if not local_ip or local_ip == 'False':
        local_ip = '0.0.0.0'
    existing_fields = append_missing_variable(existing_fields, 'LOCALIPP', local_ip)
    existing_fields = append_missing_variable(existing_fields, 'PUBLICIPP', public_ip)
    existing_fields = append_missing_variable(existing_fields, 'IPV66', ip6)
    existing_fields = append_missing_variable(existing_fields, 'INSTALLPATHH', install_path)
    return existing_fields

def replace_template_line(line, needle, replacement, is_header=False):
    """
    Filter a line read from a template file replacing any instances of a variable name
    with its value. While filtering a header line. Field names are only replaced after
    the second colin to avoid replacing the first use of the name. This is to ensure
    that both the name and values of these extra values can still be interpreted by code.

    Args:
        line - The line of text that needs to be filtered 
        needle - The variable name that needs to be replaced
        replacement - The value of the varable used to replace the name
        is_header - True only if the line is part of the template header
    """
    custom_field = False
    if is_header:
        if re.search('^# Field', line):
            first_colin = line.find(":")
            if first_colin != -1:
                second_colin = line.find(":", first_colin + 1)
                if second_colin != -1:
                    key = line[first_colin+1:second_colin].strip()
                    if key == needle:
                        line = line[0:second_colin] + ': ' + replacement + '\n'
                    custom_field = True
    if not custom_field:
        line = line.replace(needle, replacement)
    return line

def write_template_with_variables(template_filename, target_filename, variable_array):
    """
    Write a vhost file using a template to read from and an array of values to replace.

    Args:
        open_template_file - The already open template file from which to read 
        open_vhost_file - The already open vhost file for writing
        variable_array - Template values stored as [name, value] within a parent array
    """
    header = True
    header_needle = re.compile(r'^#')
    parent = os.path.dirname(target_filename)
    os.makedirs(parent, exist_ok=True)
    with open(target_filename, 'w') as output:
        with open(template_filename, 'r') as input:
            for line in input:
                if header:
                    if header_needle.search(line) == None:
                        header = False
                for key, value in variable_array:
                    line = replace_template_line(line, key, value, header)
                output.write(line)