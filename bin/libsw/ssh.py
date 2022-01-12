#!/bin/bash

import re
import os
import inquirer
from pwd import getpwnam
from grp import getgrnam
from libsw import file_filter, user

disabled_prefix = '''no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding,command="echo 'This key is disabled for this user';echo;sleep 1"'''

def get_keyfile_name(username, home_dir=False):
    """
    Get the file used to hold authorized ssh keys.

    Args:
        username - The local sytem user
        home_dir - (optional) The local system user's home directory
    """
    if not home_dir:
        home_dir = user.home_dir(username)
    return home_dir + '.ssh/authorized_keys'

def ensure_keyfile_exists(username):
    """
    Create the file used to hold authorized ssh keys if it does not already
    exist.

    Args:
        username - The local sytem user
    """
    home = user.home_dir(username)
    keyfile_name = get_keyfile_name(username, home)
    uid = getpwnam(username).pw_uid
    gid = getgrnam(username).gr_gid
    if not os.path.isdir(home + '.ssh'):
        os.mkdir(home + '.ssh')
        os.chown(home + '.ssh', uid, gid)
        os.chmod(home + '.ssh', 0o700)

    if not os.path.exists(keyfile_name):
        with open(keyfile_name, 'a+') as ak:
            pass
        os.chown(keyfile_name, uid, gid)
        os.chmod(keyfile_name, 0o600)
    return home + '.ssh/authorized_keys'

def is_key_in_file(key, file):
    """
    Check if a key is already held in the file used to hold authorized ssh keys.

    Args:
        key - The key to compare
        file - The autorized keys file to search
    """
    found = False
    if not os.path.exists(file):
        return False
    with open(file, 'r') as list:
        for entry in list:
            if entry.find('ssh-rsa ' + key) != -1:
                found = True
                break
    return found

def is_key_line_disabled(line):
    """
    Determine if a line from an authroized key file is set to kick the user off
    after connecting.

    Args:
        line - The line to check
    """
    prefix = line[:line.index('ssh-rsa ')]
    return prefix.find('command=') != -1

def is_key_disabled(key, file):
    """
    Determine if a key is set to kick the user off after connecting in an
    authroized key file.

    Args:
        key - The key to check
        file - The authroized key file to check
    """
    disabled = False
    if not os.path.exists(file):
        return False
    with open(file, 'r') as list:
        for entry in list:
            if entry.find('ssh-rsa ' + key) != -1 and \
                    is_key_line_disabled(entry):
                disabled = True
                break
    return disabled

def add(key, username):
    """
    Add an SSH public key the authroized keys file for a system user.

    Args:
        key - The key to add
        username - The system user the key will be able to login as
    """
    key_file = ensure_keyfile_exists(username)
    if is_key_in_file(key, key_file):
        return 'Key already athorized for ' + username
    with open(key_file, 'a') as auth:
            auth.write(key + '\n')
    return False

def get_user_keys(username):
    """
    Get an array of keys authroized to login as a system user.

    Args:
        username - The system user

    Return:
        An array of dictionaries with the folling keys:
            type - The hashing algorithm
            key - The public key
            signature - The signature (label) for the key
            disabled - A boolean that indicates if the key will kick the user
                off after login
    """
    key_list = []
    filename = get_keyfile_name(username)
    if os.path.exists(filename):
        with open(filename) as key_file:
            for key_line in key_file:
                disabled = is_key_line_disabled(key_line)
                start = key_line.find('ssh-rsa')
                key_line = key_line[start:]
                entry = {}
                split_line = key_line.split()
                entry['type'] = split_line[0]
                entry['key'] = split_line[1]
                entry['signature'] = ''
                entry['disabled'] = disabled
                if len(split_line) > 0:
                    entry['signature'] = ' '.join(split_line[2:])
                key_list.append(entry)
    return key_list

def get_full_key_list():
    """
    Get a 2 dimensional dictionary of all SSH keys that are authorized to access
    any system user.

    Return:
        A 2 dimensional dictionary. The first dimension uses the ssh key as the
        dictionary key. The second demension has these values:
            type - The hashing algorithm
            signature - The signature (label) for the key
            user - The system user
    """
    key_entries = {}
    for username in user.get_user_list(include_root=True):
        key_list = get_user_keys(username)
        for entry in key_list:
            if entry['disabled']:
                continue
            key = entry['key']
            new_entry = {
                    'type': entry['type'],
                    'signature': entry['signature'],
                    'user': username
                }
            if key in key_entries:
                key_entries[key].append(new_entry)
            else:
                key_entries[key] = [new_entry]
    return key_entries

def select_key(query_message, username, enabled='any'):
    """
    Prompt the user to select a key from the SSH keys that are already
    authorized to access a given system user.

    Args:
        query_message - The message to display to the user in the prompt
        username - The system user
        enabled - (optional) You can set this value to True or False to restrict
            the selection to enabled or disabled keys respectivly.
    """
    key_dicts = get_user_keys(username)
    key_array = []
    display_array = []
    for dic in key_dicts:
        if enabled == 'any' or \
                bool(enabled) != dic['disabled']:
            key_array.append(dic['key'])
            display_array.append(dic['key'][-15:] + ' ' + dic['signature'])
    if len(key_array) == 0:
        return False
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=display_array
                )
    ]
    choice = inquirer.prompt(questions)['f']
    return key_array[display_array.index(choice)]

class KeyRemover(file_filter.FilterIfExists):
    """A FileFilter to remove an SSH key from an authroized keys file."""
    def __init__(self, username, key):
        self.user = user
        self.key = key
        key_file = get_keyfile_name(username)
        super().__init__(key_file)

    def filter_stream(self, in_stream, out_stream):
        self.count = 0
        for line in in_stream:
            if line.find('ssh-rsa ' + self.key) == -1:
                out_stream.write(line)
            else:
                self.count += 1
        return self.count > 0

class KeyEnabler(file_filter.FilterIfExists):
    """A FileFilter to enable an SSH key already in an authroized keys file."""
    def __init__(self, username, key):
        self.user = user
        self.key = key
        key_file = get_keyfile_name(username)
        super().__init__(key_file)

    def filter_stream(self, in_stream, out_stream):
        self.count = 0
        for line in in_stream:
            key_pos = line.find('ssh-rsa ' + self.key)
            if key_pos > 0:
                line = line[key_pos:]
                self.count += 1
            out_stream.write(line)
        return self.count > 0

class KeyDisabler(file_filter.FilterIfExists):
    """A FileFilter to disable an SSH key already in an authroized keys file."""
    def __init__(self, username, key):
        self.user = user
        self.key = key
        key_file = get_keyfile_name(username)
        super().__init__(key_file)

    def filter_stream(self, in_stream, out_stream):
        self.count = 0
        for line in in_stream:
            key_pos = line.find('ssh-rsa ' + self.key)
            if key_pos != -1 \
                    and not line.startswith(disabled_prefix):
                line = disabled_prefix + line[key_pos:]
                self.count += 1
            out_stream.write(line)
        return self.count > 0
