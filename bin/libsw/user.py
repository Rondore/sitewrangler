#!/usr/bin/env python3

import subprocess
import inquirer
import pwd
import os
from pwd import getpwnam
from grp import getgrnam

def get_user_list(include_root=False):
    """
    Get a list of users with home directories.

    Args:
        include_root - (optional) Include the root user in the list (True or False)
    """
    output = subprocess.getoutput('cut -d: -f1 /etc/passwd')
    system_users = []
    for line in output.split('\n'):
        system_users.append(line)
    output = subprocess.getoutput('ls /home/')
    user_list = []
    for line in output.split('\n'):
        if line in system_users:
            user_list.append(line)
    if include_root:
        user_list.insert(0, 'root')
    return user_list

def get_user_group(username, numerical=False):
    """
    Get the name of main group that a user belongs to.

    Args:
        username - The name of the system user
        numberical - (optional) If True, return the group id instead of group name
    """
    if numerical: return subprocess.getoutput("id -g '" + username + "'")
    return subprocess.getoutput("id -gn '" + username + "'")

def select_user(allow_root=False):
    """
    Have the user select from a list of users with home directories.

    Args:
        allow_root - (optional) Include the root user in the list (True or False)
    """
    user_list = get_user_list(allow_root)
    questions = [
        inquirer.List('u',
                    message='Select User',
                    choices=user_list
                )
    ]
    user = inquirer.prompt(questions)['u']
    return user

def home_dir(user):
    """
    Get the home directory of the given user.

    Args:
        user - The system user
    """
    if user == 'root':
        return '/root/'
    return '/home/' + user + '/'

def webroot(user):
    """
    Get the directory to host website file from for the given user.

    Args:
        user - The system user
    """
    return home_dir(user) + 'public_html/'

def exists(user):
    """
    Check if the given user exists.

    Args:
        user - The system user
    """
    try:
        getpwnam(user)
    except KeyError:
        return False
    return True

def make_user_dir(dir, uid, gid):
    """
    Create directory owned by a user.

    Args:
        dir - The directory path
        uid - The system user's numerical ID
        gid - The system group's numerical ID
    """
    if not os.path.exists(dir):
        os.makedirs(dir)
    os.chown(dir, uid, gid)

def make_user_file(file, uid, gid):
    """
    Create a file owned by a user.

    Args:
        file - The filepath
        uid - The system user's numerical ID
        gid - The system group's numerical ID
    """
    if not os.path.exists(file):
        with open(file, 'a+'):
            pass
    os.chown(file, uid, gid)

def make_user(username):
    """
    Create a new user with the given username.

    Args:
        username - The system user
    """
    home_directory = home_dir(username)
    bash_profile = home_directory + '.bash_profile'
    fix_home = False
    if os.path.exists(home_directory):
        fix_home = True
    os.system('useradd --home-dir "' + home_directory + '" -s /bin/bash --create-home --user-group "' + username + '"')
    uid = getpwnam(username).pw_uid
    gid = getgrnam(username).gr_gid
    if fix_home:
        os.chown(home_directory , uid, gid)
    os.chmod(home_directory, 0o711)
    make_user_dir(home_directory + 'public_html/', uid, getgrnam('daemon').gr_gid)
    make_user_dir(home_directory + 'mail/', uid, gid)
    make_user_dir(home_directory + 'tmp/', uid, gid)
    make_user_dir(home_directory + 'logs/', uid, gid)
    make_user_dir(home_directory + 'etc/', uid, gid)
    make_user_file(bash_profile, uid, gid)
    with open(bash_profile, 'a+') as profile:
        profile.write('''
if [ -f ~/.bashrc ]; then
        . ~/.bashrc
fi

# User specific environment and startup programs
export PATH=$PATH:$HOME/.local/bin:$HOME/bin

''')

def remove_user(username, deletefiles):
    """
    Removes a system user from the system.

    username - the system username to be removed
    deletefiles - a boolean value to determin if the users home directory should
    be deleted
    """
    if username.lower() == 'root':
        return False

    userdel = ['userdel']
    if deletefiles:
        userdel.append('-r')
    userdel.append(username)
    output = subprocess.run(userdel)
    return output.returncode == 0

def select_new_username():
    """
    Prompt the user input a username that does not yet exist in the system.
    """
    keep_trying = True
    username = False
    while keep_trying:
        if username:
            print('Sorry, that user already exists.')
        username = input('Username: ')
        keep_trying = exists(username)
    return username
