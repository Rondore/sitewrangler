#!/usr/bin/env python3

import inquirer
from mysql import connector
from getpass import getpass
from libsw import settings

#TODO create a read-only user
# GRANT SELECT ON database_name.* TO 'user_name'@'localhost' IDENTIFIED BY '';

def get_connection():
    """
    Cet a connected MySQL connection.
    """
    root_needs_pass = settings.get_bool('db_root_requires_password')
    socket = settings.get('mysql_socket')
    if(root_needs_pass):
        bitpass = getpass('Enter the MySQL root password: ')
        print()
        return connector.connect(unix_socket=socket, user='root', passwd=bitpass)
    else:
        return connector.connect(unix_socket=socket, user='root')

def create_database(database, mydb):
    """
    Create a new database with the given name.

    Args:
        database - The name of the new database
        mydb - A connected MySQL connection
    """
    mydb.cursor().execute('CREATE DATABASE `' + database + '`;')

def create_database_user(database, user, userpass, mydb, host='localhost'):
    """
    Create a MySQL user with permission to access a database.

    Args:
        database - The name of the database to grant rights over
        user - The username of the new user to create
        userpass - The password for the new user
        mydb - A connected MySQL connection
        host - The hostname/IP that can access the database with the new user
    """
    mydb.cursor().execute('GRANT ALL ON `' + database + '`.* TO `' + user + '`@`' + host + "` IDENTIFIED BY '" + userpass + "';")
    mydb.cursor().execute('flush privileges;')

def create_database_with_user(database, user, userpass, mydb):
    """
    Create a new database and corresponding user to access the database from the localhost.

    Args:
        database - The name of the new database
        user - The username of the new user
        userpass - The password for the new user
        mydp - A connected MySQL connection
    """
    create_database(database, mydb)
    create_database_user(database, user, userpass, mydb)

def remove_database(database, mydb):
    """
    Delete a database and all of it's contents.

    Args:
        database - The name of the database to delete
        mydb - A connected MySQL connection
    """
    mydb.cursor().execute('DROP DATABASE `' + database + '`;')

def remove_database_user(user, mydb):
    """
    Delete a database user.

    Args:
        user - The username of the user to delete
        mydb - A connected MySQL connection
    """
    host_cursor = mydb.cursor()
    host_cursor.execute('Select host from mysql.user where user="' + user + '";')
    while True:
        rows = host_cursor.fetchmany(10)
        if not rows:
            break
        for row in rows:
            host = row[0].decode("utf-8")
            mydb.cursor().execute('DROP USER `' + user + '`@`' + host + '`;')
    mydb.cursor().execute('flush privileges;')

def clone(from_db, to_db, mydb):
    """
    Copy the contents of a database into another database. This will destroy any
    tables in the "to" database that matchies the name of a table in the "from"
    database.

    Args:
        from_db - The name of the source database
        to_db - The name of the target database
        mydb - An open database connection
    """
    overwrite_dbs = list_database_tables(to_db, mydb)
    for table in list_database_tables(from_db, mydb):
        if table in overwrite_dbs:
            mydb.cursor().execute("DROP TABLE `" + to_db + "`.`" + table + "`;")
        mydb.cursor().execute("CREATE TABLE `" + to_db + "`.`" + table + "` LIKE `" + from_db + "`.`" + table + "`;")
        mydb.cursor().execute("INSERT INTO `" + to_db + "`.`" + table + "` SELECT * FROM `" + from_db + "`.`" + table + "`;")

def list_databases(mydb):
    """
    Get an array of all databases.

    Args:
        mydb - A connected MySQL connection
    """
    databases = []
    cursor = mydb.cursor()
    cursor.execute('SHOW DATABASES;')
    while True:
        rows = cursor.fetchmany(20)
        if not rows:
            break
        for entry in rows:
            name = entry[0]
            if name != 'information_schema' \
                    and name != 'performance_schema' \
                    and name != 'mysql':
                databases.append(name)
    return databases

def list_database_tables(database, mydb):
    """
    Get an array of all tables in a database.

    Args:
        database - The name of the database to list out
        mydb - A connected MySQL connection
    """
    tables = []
    cursor = mydb.cursor()
    cursor.execute('SHOW TABLES FROM `' + database + '`;')
    while True:
        rows = cursor.fetchmany(20)
        if not rows:
            break
        for entry in rows:
            name = entry[0]
            tables.append(name)
    return tables

def check_table(database, table, mydb):
    cursor = mydb.cursor()
    cursor.execute('CHECK TABLE `' + database + '`.`' + table + '`;')
    while True:
        rows = cursor.fetchmany(20)
        if len(rows) == 0:
            break
        for db in rows:
            return db[3]

def repair_table(database, table, mydb):
    cursor = mydb.cursor()
    cursor.execute('REPAIR TABLE `' + database + '`.`' + table + '`;')
    while True:
        rows = cursor.fetchmany(20)
        if len(rows) == 0:
            break
        for db in rows:
            return db[3]

def list_users(mydb):
    """
    Get an array of all database users.

    Args:
        mydb - A connected MySQL connection
    """
    databases = []
    cursor = mydb.cursor()
    cursor.execute('SELECT DISTINCT(User) FROM mysql.user WHERE User<>"root";')
    while True:
        rows = cursor.fetchmany(20)
        if not rows:
            break
        for db in rows:
            user = db[0].decode("utf-8")
            databases.append( user )
    return databases

def list_users_with_grants(mydb):
    """
    Get an array of tuples containing database users and their databases.

    Args:
        mydb - A connected MySQL connection

    Return:
        An array of tuples ( user, host, database )
    """
    databases = []
    cursor = mydb.cursor()
    cursor.execute('SELECT User, Host, Db FROM mysql.db WHERE User<>"root";')
    while True:
        rows = cursor.fetchmany(20)
        if not rows:
            break
        for rowset in rows:
            user = rowset[0].decode("utf-8")
            host = rowset[1].decode("utf-8")
            database = rowset[2].decode("utf-8")
            databases.append(( user, host, database ))
    return databases

def list_database_users(database, mydb):
    """
    Get an array of all users with rights over a database.

    Args:
        database - The name of the database that listed users can access
        mydb - A connected MySQL connection
    """
    databases = []
    cursor = mydb.cursor()
    cursor.execute('SELECT DISTINCT(User) FROM mysql.db WHERE User<>"root" AND `Db`="' + database + '";')
    while True:
        rows = cursor.fetchmany(20)
        if not rows:
            break
        for rowset in rows:
            user = rowset[0].decode("utf-8")
            databases.append(user)
    return databases

def select_database(query_message, mydb):
    """
    Prompt the user to select from a list of all databases.

    Args:
        query_message - The messages to display in the prompt
        mydb - A connected MySQL connection
    """
    questions = [
        inquirer.List('d',
                    message=query_message,
                    choices=list_databases(mydb)
                )
    ]
    return inquirer.prompt(questions)['d']

def select_user(query_message, mydb):
    """
    Prompt the user to select from a list of all database users.

    Args:
        query_message - The messages to display in the prompt
        mydb - A connected MySQL connection
    """
    questions = [
        inquirer.List('u',
                    message=query_message,
                    choices=list_users(mydb)
                )
    ]
    return inquirer.prompt(questions)['u']
