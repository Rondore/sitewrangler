#!/usr/bin/env python3

from libsw import command_index

def _help():
    print('sw ssh list [`example_username`]  # List all enabled SSH keys with access to the system; however, if a user is given, disabled keys are shown as well')
    print('sw ssh import [example_username]  # Import an SSH key')
    print('sw ssh disable [example_username [key]]  # Disable an SSH key')
    print('sw ssh enable [example_username [key]]  # Enable a disabled SSH key')
    print('sw ssh (delete|remove) [example_username [key]]  # Remove an SSH key')
index = command_index.CategoryIndex('ssh', _help)

def _import(username):
    from libsw import ssh, user
    if not username or not user.exists(username):
        username = user.select_user(True)
    print('If you are using Unix or a Unix-like system such as Linux or OSX, you can copy this code into your local terminal to get your SSH key including the decorators you need for this command:')
    print('''mkdir -p ~/.ssh; if [ ! -f ~/.ssh/id_rsa ]; then ssh-keygen -N "" -f ~/.ssh/id_rsa >/dev/null; fi; echo "Your full public key:"; cat ~/.ssh/id_rsa.pub''')
    print()
    key = input('Enter the full public key lines as it appears in id_rsa.pub (or similar): ')
    error = ssh.add(key, username)
    if error:
        print('Error: ' + error)
    else:
        print('Added Key for ' + username)
index.register_command('import', _import)

def _remove(username, more):
    from libsw import ssh, user
    if not username or not user.exists(username):
        username = user.select_user(True)
    key = False
    if more:
        key = more[0]
    else:
        print('If you are using Unix or a Unix-like system such as Linux or OSX, you can copy this code into your local terminal to get your naked SSH key:')
        print('''mkdir -p ~/.ssh; if [ ! -f ~/.ssh/id_rsa ]; then ssh-keygen -N "" -f ~/.ssh/id_rsa >/dev/null; fi; echo "Your naked public key:"; cat ~/.ssh/id_rsa.pub''')
        key = ssh.select_key('Select a key to delete', username)
        if not key:
            print(username + ' has no authorized SSH keys')
            return
    removed = ssh.KeyRemover(username, key).run()
    if removed:
        print('Successfully removed key')
    else:
        print('Key was not authorized for ' + username)
index.register_command('remove', _remove)
index.register_command('delete', _remove)

def _enable(username, more):
    from libsw import ssh, user
    if not username or not user.exists(username):
        username = user.select_user(True)
    key = False
    if more:
        key = more[0]
    else:
        key = ssh.select_key('Select a key to enable', username, enabled=False)
        if not key:
            print(username + ' has no authorized SSH keys')
            return
    removed = ssh.KeyEnabler(username, key).run()
    if removed:
        print('Successfully enabled key')
    else:
        print('Key was not authorized for ' + username)
index.register_command('enable', _enable)

def _disable(username, more):
    from libsw import ssh, user
    if not username or not user.exists(username):
        username = user.select_user(True)
    key = False
    if more:
        key = more[0]
    else:
        key = ssh.select_key('Select a key to disable', username, enabled=True)
        if not key:
            print(username + ' has no authorized SSH keys')
            return
    removed = ssh.KeyDisabler(username, key).run()
    if removed:
        print('Successfully disabled key')
    else:
        print('Key was not authorized for ' + username)
index.register_command('disable', _disable)

def _list(username):
    from libsw import ssh
    from tabulate import tabulate
    print()
    if username:
        key_dicts = ssh.get_user_keys(username)
        key_array = []
        for dic in key_dicts:
            status = 'Enabled'
            if dic['disabled']:
                status = 'Disabled'
            entry = [dic['key'][-15:], dic['signature'], status]
            key_array.append(entry)
        print('All keys for ' + username + ':')
        print(tabulate(key_array, ['Key', 'Signature', 'Status']))
    else:
        key_dicts = ssh.get_full_key_list()
        key_array = []
        for key in key_dicts:
            user_list = ''
            signature = False
            for sub_entry in key_dicts[key]:
                if len(user_list) > 0:
                    user_list += ', '
                user_list += sub_entry['user']
                sig = sub_entry['signature']
                if not signature and len(sig) > 0:
                    signature = sig
            if not signature:
                signature = ''
            entry = [key[-15:], user_list, signature]
            key_array.append(entry)
        print('All enabled keys:')
        print(tabulate(key_array, ['Key', 'System Users', 'Signature']))
    print()
index.register_command('list', _list)
