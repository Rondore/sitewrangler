#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw user list  # List system users along with domains associated with them')
    print('sw user (add|create) [example_username]  # Create a system user')
    print('sw user (delete|remove) [example_username [`dropfiles`]]  # Delete a system user and optionally it\'s files')
index = command_index.CategoryIndex('user', _help)

def _add(sys_user):
    from libsw import user
    if sys_user:
        if user.exists(sys_user):
            print('Error. ' + sys_user + ' already exists.')
            return
    else:
        sys_user = user.select_new_username()
    user.make_user(sys_user)
index.register_command('add', _add)
index.register_command('create', _add)

def _remove(sys_user, more):
    from libsw import user
    deletefiles = False
    if more != False and more[0].lower() == 'dropfiles':
        deletefiles = True
    if sys_user == False:
        sys_user =  user.select_user()
    user.remove_user(sys_user, deletefiles)
    #TODO remove mail domain associations for user
    #TODO remove nginx vhosts associatiated with the user
    #TODO maybe remove certs that have no DNS entries and are only assiciated this user's mail and site domains
index.register_command('remove', _remove)
index.register_command('delete', _remove)

def _list():
    from libsw import user
    for username in user.get_user_list():
        print(username)
index.register_command('list', _list)
