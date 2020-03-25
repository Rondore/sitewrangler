#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw db list  # List databases in the system')
    print('sw db (add|create) [database_name [database_user]]  # Create a new database and corresponding user')
    print('sw db listuser[s]  # List database users')
    print('sw db listgrant[s]  # List database users and over which databases they have some rights granted')
    print('sw db (delete|remove) [database_name]  # Delete a database and optionally corresponding user(s)')
    print('sw db check [database_name|+]  # Run a check on all tables in a database (+=all)')
    print('sw db repair [database_name]  # Run a repair on all tables in a database')
index = command_index.CategoryIndex('db', _help)

def _add(database_name, more):
    from libsw import db
    from getpass import getpass
    if database_name == False:
        database_name = input('Database: ')
    database_user = False
    if more and len(more) > 1:
        database_user = more[0]
    if database_user == False:
        database_user = input('DB User: ')
    userpass = getpass('DB User Password: ')
    print()
    mydb = db.get_connection()
    db.create_database_with_user(database_name, database_user, userpass, mydb)
index.register_command('add', _add)
index.register_command('create', _add)

def _remove(database_name):
    from libsw import db, input_util
    mydb = db.get_connection()
    if database_name == False:
        database_name = db.select_database("Select a database to delete. ALL IT'S DATA WILL BE LOST!", mydb)
    user_list = db.list_database_users(database_name, mydb)
    print('Users that use this table:')
    for user in user_list:
        print('    ' + user)
    if input_util.confirm('Delete all the above users as well?', default=False):
        for user in user_list:
            db.remove_database_user(user, mydb)
    db.remove_database(database_name, mydb)
index.register_command('remove', _remove)
index.register_command('delete', _remove)

def _list():
    from libsw import db
    mydb = db.get_connection()
    for database in db.list_databases(mydb):
        print(database)
index.register_command('list', _list)

def _listusers():
    from libsw import db
    mydb = db.get_connection()
    for user in db.list_users(mydb):
        print(user)
index.register_command('listuser', _listusers)
index.register_command('listusers', _listusers)

def _listgrants():
    from libsw import db
    from tabulate import tabulate
    mydb = db.get_connection()
    user_list = db.list_users_with_grants(mydb)
    print(tabulate(user_list, headers=['User','Host', 'Database']))
index.register_command('listgrant', _listgrants)
index.register_command('listgrants', _listgrants)

def _check(database_name):
    from libsw import db, input_util
    from tabulate import tabulate
    mydb = db.get_connection()
    if database_name == '+':
        results = []
        for database in db.list_databases(mydb):
            for table in db.list_database_tables(database, mydb):
                status = db.check_table(database, table, mydb)
                results.append([database, table, status])
        print(tabulate(results, headers=['Database', 'Table', 'Status']))
    else:
        if database_name == False:
            database_name = db.select_database("Select a database to check.", mydb)
        results = []
        for table in db.list_database_tables(database_name, mydb):
            status = db.check_table(database_name, table, mydb)
            results.append([table, status])
        print(tabulate(results, headers=['Table','Status']))
index.register_command('check', _check)

def _repair(database_name):
    from libsw import db, input_util
    from tabulate import tabulate
    mydb = db.get_connection()
    if database_name == False:
        database_name = db.select_database("Select a database to repair.", mydb)
    results = []
    for table in db.list_database_tables(database_name, mydb):
        status = db.repair_table(database_name, table, mydb)
        results.append([table, status])
    print(tabulate(results, headers=['Table','Status']))
index.register_command('repair', _repair)
