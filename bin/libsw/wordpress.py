#!/usr/bin/env python3

import os
import time
import subprocess
import random
import inquirer
import stat
import requests
from libsw import builder, php, nginx, user, bind, cert, db, settings, input_util
from getpass import getpass
from mysql import connector
from pwd import getpwnam

def list_installations():
    """
    List all domains with a valid WordPress installation
    """
    sites = nginx.enabled_sites()
    wp_sites = []
    for site in sites:
        if is_wordpress_installation(site):
            wp_sites.append(site)
    return wp_sites

def select_installation(query_message):
    """
    Have the user select from a list of all domains with enabled vhost files.

    Args:
        query_message - The message to display to the user in the prompt
    """
    domain_list = list_installations()
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=domain_list
                )
    ]
    domain = inquirer.prompt(questions)['f']
    return domain

def is_wordpress_installation(domain):
    """
    Check if a domain has a valid WordPress installation

    Args:
        domain - The domain associated with the installation
    """
    sys_user = nginx.user_from_domain(domain)
    webroot = user.webroot(sys_user)
    if os.path.exists(webroot + 'wp-content') and \
            os.path.exists(webroot + 'wp-includes') and \
            os.path.exists(webroot + 'wp-config.php'):
        return True
    return False

def wp_cron_disabled(domain):
    """
    Check if a domain has it's built in cron disabled

    Args:
        domain - The domain associated with the installation
    """
    sys_user = nginx.user_from_domain(domain)
    webroot = user.webroot(sys_user)
    run_cli(sys_user, webroot, 'config get DISABLE_WP_CRON')
    output = output.lower()
    if output == 'true':
        return True
    return False

def sys_cron_enabled(domain):
    """
    Check if a domain has a system cron

    Args:
        domain - The domain associated with the installation
    """
    sys_user = nginx.user_from_domain(domain)
    output = subprocess.getoutput('su - "' + sys_user + '" -c \'crontab -l 2>/dev/null | grep -Ev "^[ \s]*#"\'')
    if output.find('/wp-cron.php') == -1:
        return False
    return True
    # for line in output:
    #     if line.endswith('/wp-cron.php'):
    #         return True
    # return False

def get_version(domain):
    """
    Check the WordPress version for a domain

    Args:
        domain - The domain associated with the installation
    """
    sys_user = nginx.user_from_domain(domain)
    webroot = user.webroot(sys_user)
    return run_cli(sys_user, webroot, 'core version')

def get_db_info(sys_user, webroot=False):
    """
    Get the database name, user and password for an existing WordPress
    installation.

    Args:
        sys_user - The system user that the WorpPress site is stored in
        webroot - (optional) the webroot for the WordPress installation
    """
    if webroot == False:
        webroot = user.webroot(sys_user)
    db_user = get_site_option(sys_user, webroot, 'DB_USER')
    name = get_site_option(sys_user, webroot, 'DB_NAME')
    password = get_site_option(sys_user, webroot, 'DB_PASSWORD')
    return (name, db_user, password)

def update_config(sys_user, db_name, db_user, db_password, path=False):
    """
    Update the database name, user and password for a WordPress installation.

    Args:
        sys_user - The system user that the WorpPress site is stored in
        db_name - The new database name
        db_user - The new database user
        db_password - The new database password
        path - (optional) the webroot for the WordPress installation
    """
    if path == False:
        path = user.home_dir(sys_user) + 'public_html/'

    set_config_value('DB_USER', db_user, sys_user, path)
    set_config_value('DB_PASSWORD', db_password, sys_user, path)
    set_config_value('DB_NAME', db_name, sys_user, path)

def set_config_value(name, value, sys_user, path):
    """
    Update a text value in a WordPress installation's configuraiton file.

    Args:
        sys_user - The system user that the WorpPress site is stored in
        db_name - The new database name
        db_user - The new database user
        db_password - The new database password
        path - (optional) the webroot for the WordPress installation
    """
    if path == False:
        path = user.home_dir(sys_user) + 'public_html/'
    run_cli(sys_user, path, 'config set "' + name + '" "' + value + '"')

def install_files(sys_user, db_name, db_user, db_password, path=False):
    """
    Download Wordpress for a given system user. Then set the database name, user
    and password for the new WordPress installation.

    Args:
        sys_user - The system user that the WorpPress site is stored in
        db_name - The existing  database name
        db_user - The existing database user
        db_password - The existing database password
        path - (optional) the webroot for the WordPress installation
    """
    if path == False:
        path = user.home_dir(sys_user) + 'public_html/'

    # Set environment
    pwd = os.getcwd()
    whoami = os.geteuid()
    os.seteuid(getpwnam(sys_user).pw_uid)
    os.chdir(path)

    # Download WordPress
    run_cli(sys_user, path, 'core download')
    # Configure WordPress
    run_cli(sys_user, path, "config create --skip-check" + \
            ' --path="' + path + '"' + \
            ' --dbname="' + db_name + '"' + \
            ' --dbuser="' + db_user + '"' + \
            ' --dbpass="' + db_password + '"')

    # Reset environment
    os.seteuid(whoami)
    os.chdir(pwd)

def cert_try_loop(domain, username):
    """
    Try up to 5 times to get a certificate for a domain.

    Args:
        domain - The domain to generate the certificate for
        username - The system user the domain belongs to
    """
    cert_try = 0
    no_cert = True
    time.sleep(2)
    while no_cert and cert_try < 5:
        cert_try += 1
        no_cert = not cert.create_std_le_certs(domain, username)
        if no_cert:
            wait = 30 * cert_try
            print('Cert Failed. Waiting ' + str(wait) + ' seconds and then trying again...')
            time.sleep(wait)
    if no_cert:
        cert_try += 1
        no_cert = not cert.create_std_le_certs(domain, username)
        if no_cert:
            print('Cert Failed. Investigate, then wait at least 30 seconds; then to try again run: sw nginx addssl ' + domain)
    return not no_cert

def make_site(username, domain, php_version, db_conn):
    """
    Create a new WordPress website.

    Args:
        username - The existing system user for the site
        domain - The domain name for the site
        php_version - The php version to user for the site (subversion)
        db_conn - An open database connection with rights to create the database
            and user
    """
    user.make_user(username)
    bind.make_zone(domain)
    bind.rebuild_zone_index()
    nginx.make_vhost(username, domain)
    php.make_vhost(username, domain, php_version)
    database_name = username[:18]
    database_user = database_name
    database_pass = input_util.random_string()
    print("Setting db password to: " + database_pass)
    db.create_database_with_user(database_name, database_user, database_pass, db_conn)
    install_files(username, database_name, database_user, database_pass)
    has_cert = cert_try_loop(domain, username)
    if has_cert:
        nginx.add_ssl_to_site_hosts(domain)
    return has_cert

def clone_site(old_site, new_user, new_domain, db_conn):
    """
    Create a new WordPress website cloned from an existing site.

    Args:
        old_site - The domain name for the site to be cloned from
        new_user - The non-existing system user for the cloned site
        new_domain - The domain name for the cloned site
        db_conn - An open database connection with rights to create the database
            and user
    """
    php_version = php.get_site_version(old_site)
    old_user = php.user_from_domain(old_site)
    user.make_user(new_user)
    bind.make_zone(new_domain)
    bind.rebuild_zone_index()
    nginx.make_vhost(new_user, new_domain)
    for rule_id in nginx.get_bypassed_modsec_rules(old_site):
        nginx.bypass_modsec_rule(new_domain, rule_id)
    php.make_vhost(new_user, new_domain, php_version)
    db_name = new_user[:18]
    db_user = db_name
    db_pass = input_util.random_string(20, False)
    print("Setting db password to: " + db_pass)
    db.create_database_with_user(db_name, db_user, db_pass, db_conn)
    old_db_user, old_db, old_pass = get_db_info(old_user)
    db.clone(old_db, db_name, db_conn)
    old_dir = user.webroot(old_user)
    new_dir = user.webroot(new_user)
    print('Copying site files...')
    os.system("cp -a '" + old_dir + ".' '" + new_dir + "'")
    print('Copy complete, fixing permissions...')
    os.system("find '" + new_dir + "' -user '" + old_user + "' -exec chown '" + new_user + "' {} \;")
    os.system("find '" + new_dir + "' -group '" + old_user + "' -exec chgrp '" + new_user + "' {} \;")
    print('Permissions fixed')
    os.system("sed -i 's~" + old_dir + "~" + new_dir + "~g' " + new_dir + "wp-config.php")
    update_config(new_user, db_name, db_user, db_pass)
    run_cli(new_user, new_dir, 'search-replace "' + old_site + '" "' + new_domain + '"')
    run_cli(new_user, new_dir, 'cache flush')
    has_cert = cert_try_loop(new_domain, new_user)
    if has_cert:
        nginx.add_ssl_to_site_hosts(new_domain)
    return has_cert

def wizard_make_site():
    """
    Create a new WordPress site, promting the user for all needed information.
    """
    print('Your domain should already be using this server as it\'s nameservers.')
    print('Wait at least five minutes after changing nameservers to continue with this script.')
    username = user.select_new_username()
    domain = input('New Domain: ')
    php_version = php.select_version()
    mydb = db.get_connection()
    is_ssl = make_site(username, domain, php_version, mydb)
    add_cron(username)
    protocol = 'http'
    if is_ssl:
        protocol = 'https'
    print('Now go to ' + protocol + '://' + domain + ' to complete the WordPress setup wizard.')

def wizard_clone_site():
    """
    Clone an existing WordPress site, promting the user for all needed
    information.
    """
    print('Enter information for new site:')
    new_user = user.select_new_username()
    new_domain = input('New Domain: ')
    old_site = php.select_conf('Select site to clone from: ')['file']
    mydb = db.get_connection()
    is_ssl = clone_site(old_site, new_user, new_domain, mydb)
    add_cron(new_user)
    protocol = 'http'
    if is_ssl:
        protocol = 'https'
    print('Now go to ' + protocol + '://' + new_domain + ' to check the cloned site.')

def add_cron(sys_user):
    """
    Disable the fake cron job in WordPress and create a real one with the system
    cron daemon. (speeds up page loads)
    """
    user_info = getpwnam(sys_user)
    crons = subprocess.getoutput("su - " + sys_user + " -c 'crontab -l 2>/dev/null'")
    found = False
    for line in crons:
        if line.startswith('#'):
            continue
        if line.find('wp-cron.php') != -1:
            found = True
            break
    if not found:
        minute = random.randint(0,59)
        cron = str(minute) + ' 0 * * * ' + builder.set_sh_ld + '~/.local/bin/php ~/public_html/wp-cron.php'
        command = "su - " + sys_user + " -c \"crontab -l 2>/dev/null | { cat; echo '" + cron + "'; } | crontab -\" "
        #print(command)
        subprocess.getoutput(command)
        print('Created system cron')
    set_config_value('DISABLE_WP_CRON', 'true', sys_user, user_info.pw_dir + "public_html/")
    print('Disabled WordPress cron')
    return not found

def create_one_time_login(domain):
    """
    Create a PHP file to give a one-time login into a WordPress site without a
    password. There is no safty measure to remove this link if it is not used.

    Args:
        domain - The domain that needs a one-time login
    """
    sys_user = nginx.user_from_domain(domain)
    passcode = input_util.random_string(40, False)
    passname = input_util.random_string(40, False)
    docroot = nginx.docroot_from_domain(domain)
    target_file = docroot + 'wp-admin/wp-autologin-' + passname + '.php'
    site_url = get_site_url(sys_user, docroot)

    # Set environment
    whoami = os.geteuid()
    os.seteuid(getpwnam(sys_user).pw_uid)

    with open(settings.get('install_path') + 'etc/wp-autologin.php', 'r') as template:
        with open(target_file, 'w') as php_file:
            for line in template:
                line = line.replace('PASSWORDD', passcode, 10000)
                php_file.write(line)

    # Reset environment
    os.seteuid(whoami)
    print('Go to: ' + site_url + 'wp-admin/wp-autologin-' + passname + '.php?pass=' + passcode)

def get_outdated(domain):
    wp_path = settings.get('build_path') + 'wp-cli/wp-cli.phar'
    docroot = nginx.docroot_from_domain(domain)
    sys_user = nginx.user_from_domain(domain)
    command_start = "su - " + sys_user + " -c '" + builder.set_sh_ld + 'php ' + wp_path + " "
    command_end = " --format=csv 2>/dev/null | tail -n +2'"
    core = subprocess.getoutput(command_start + "core check-update --path=\"" + docroot + "\" --fields=update_type" + command_end)
    themes = subprocess.getoutput(command_start + "theme list --path=\"" + docroot + "\" --update=available --fields=name" + command_end)
    plugins =  subprocess.getoutput(command_start + "plugin list --path=\"" + docroot + "\" --update=available --fields=name" + command_end)
    return [core, themes.splitlines(), plugins.splitlines()]

def get_site_option(sys_user, docroot, option):
    value = run_cli(sys_user, docroot, "option get " + option)
    return value

def get_site_url(sys_user, docroot):
    url = get_site_option(sys_user, docroot, 'siteurl')
    if url[-1] != '/':
        url += '/'
    return url

def get_site_home(sys_user, docroot):
    home = get_site_option(sys_user, docroot, 'home')
    if home[-1] != '/':
        home += '/'
    return home

def install_wp_cli():
    install_directory = settings.get('build_path') + 'wp-cli/'
    download_url = 'https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar'
    save_file = install_directory + 'wp-cli.phar'
    if not os.path.exists(install_directory):
        os.makedirs(install_directory)
    response = requests.get(download_url)
    with open(save_file, "wb") as f:
        f.write(response.content)
    old_mode = os.stat(save_file)
    os.chmod(save_file, old_mode.st_mode | stat.S_IEXEC)

def run_cli(user, docroot, cli_args):
    """
    Run a command with wp-cli. The arguments should be provided as a string containing the terminal command after "wp"
    """
    wp_path = settings.get('build_path') + 'wp-cli/wp-cli.phar'
    cli_args = cli_args.replace('\\', '\\\\').replace("'", "\\'").replace('$', '\\$').replace('`', '\\`')
    command = "su - " + user + " -c '" + builder.set_sh_ld + 'php ' + wp_path + ' --path="' + docroot + '" ' + cli_args + "'"
    return subprocess.getoutput(command, errors=os.devnull)