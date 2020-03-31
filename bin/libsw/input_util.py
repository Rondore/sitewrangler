#!/usr/bin/env python3

import inquirer
import subprocess
import os
import random
import re
import string

def input_domain():
    """
    Prompt the user to input a domain name.
    """
    domain = False
    while not domain:
        domain = input('Enter Domain (without www): ')
        domain = domain.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        if not is_domain(domain):
            domain = False
            print('Invalid domain')
    return domain

def is_domain(text):
    """
    Determine if a text string is a valid domain name.

    Args:
        text - the string to test
    """
    if text.find('.') == -1 :
        return False
    if re.match('^[A-Za-z0-9][\.\-A-Za-z0-9]*[A-Za-z0-9]$', text) == None:
        return False
    return True

def input_ip():
    """
    Prompt the user to input a domain name.
    """
    ip = False
    while not ip:
        ip = input('Enter IP address: ')
        if not is_ip(ip):
            ip = False
            print('Invalid ip')
    return ip

def is_ip(text):
    text = text.strip()
    if ':' in text:
        # IPv6
        chunks = text.split(':')
        regex = re.compile('[0-9a-fA-F]*')
        for segment in chunks:
            length = len(segment)
            if length > 0:
                return False
            if length == 0:
                continue
            if not regex.match(segment):
                return False
    else:
        # IPv4
        chunks = text.split('.')
        if len(chunks) != 4:
            return False
        for segment in chunks:
            if not segment.isnumeric():
                return False
            octal = int(segment)
            if octal > 255 or octal < 0:
                return False
    return True

def confirm(text, default=True):
    """
    Simply ask the user a yes or no question.

    Args:
        text - The text to use in the prompt
        default - (optional) The value to use if nothing is given
    """
    questions = [
        inquirer.Confirm('confirm', message=text, default=True),
    ]
    return inquirer.prompt(questions)['confirm']

def edit_file(path):
    """
    Allow the user to edit a file. This method tries to detect the
    user's default editor with the environment variable $EDITOR. If
    that variable is blank, then nano is used.

    Args:
        path - The full path to the file to edit
    """
    editor = subprocess.getoutput('echo "$EDITOR"')
    if len(editor) == 0:
        find_nano = subprocess.getoutput("whereis nano | egrep ': /'")
        find_vi = subprocess.getoutput("whereis vi | egrep ': /'")
        find_vim = subprocess.getoutput("whereis vim | egrep ': /'")
        find_emacs = subprocess.getoutput("whereis emacs | egrep ': /'")
        if len(find_nano) > 0:
            editor = 'nano'
        elif len(find_vi) > 0:
            editor = 'vi'
        elif len(find_vim) > 0:
            editor = 'vim'
        elif len(find_emacs) > 0:
            editor = 'emacs'

    old_stamp = os.path.getmtime(path)
    subprocess.run([editor, path])
    new_stamp = os.path.getmtime(path)
    return old_stamp != new_stamp

def random_string(string_length=20, punctuation=True):
    """
    Create a random string that is quotable. Usable for basic passwords.

    Args:
        string_length - (optional) The number of characters to generate
        punctuation - (optional) True if the generated characters should include
            punctuation
    """
    chars = string.ascii_letters + string.digits
    if punctuation:
        chars += string.punctuation
    chars = chars.replace("'", '').replace('`', '').replace('$', '') # remove the ', `, and $ characters to avoid breaking quotes
    return ''.join(random.choice(chars) for i in range(string_length))

def prompt_value(key, value):
    #new_value = input('Enter ' + key + ' [' + value + ']: ')
    #if len(new_value) == 0:
    #    return value
    questions = [
        inquirer.Text('query', message='Enter ' + key, default=value),
    ]
    return inquirer.prompt(questions)['query']

def select_from(query_message, options):
    """
    Have the user select from an Array of Strings.

    Args:
        query_message - A query message to display to the user when selecting
        options - The options to select from
    """
    questions = [
        inquirer.List('s',
                    message=query_message,
                    choices=slug_list
                )
    ]
    return inquirer.prompt(questions)['s']

def select_multiple_from(query_message, options):
    """
    Have the user select multiple entries from an Array of Strings.

    Args:
        query_message - A query message to display to the user when selecting
        options - The options to select from
    """
    exit = ' ** Done ** '
    selected = []
    while True:
        display_options = [exit]
        for op in options:
            if op not in selected:
                display_options.append(op)
        questions = [
            inquirer.List('s',
                        message=query_message,
                        choices=display_options
                    )
        ]
        just_selected = inquirer.prompt(questions)['s']
        if just_selected == exit:
            break
        else:
            selected.append(just_selected)
    return selected