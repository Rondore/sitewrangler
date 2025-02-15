#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw email (list|listdomain[s])  # List domains registered in the email system and their associated system users')
    print('sw email listuser[s]  # List all email accounts')
    print('sw email (add|create) [user@example.com]  # Add an email account')
    print('sw email setpass[word] [user@example.com]  # Change an email account password')
    print('sw email checkpass[word] [user@example.com]  # Check an email account password')
    print('sw email setdomain [example.com [example_username]]  # Associate a domain with a system account in the email system')
    print('sw email unsetdomain [example.com]  # Remove a domain from the email system')
    print('sw email getuser [example.com]  # Print the system account associated with a domain in the email system')
    print('sw email (delete|remove) [user@example.com [`dropfiles`]]  # Delete an email account and optionally it\'s files')
    print('sw email dkim [example.com]  # Generates a new dkim pair and installs them')
    print('sw email sastatus [[user@]example.com]  # Check if SpamAssassin is enabled for a domain or email address')
    print('sw email enablesa [[user@]example.com]  # Enable SpamAssassin for a domain or email address')
    print('sw email disablesa [[user@]example.com]  # Disable SpamAssassin for a domain or email address')
    print('sw email status  # Get the service status output for all mail-related services')
index = command_index.CategoryIndex('email', _help)

def _add_autocomplete(args, end_with_space):
    if end_with_space or len(args) > 1 or '@' not in args[0]:
        return
    address = args[0]
    user, domain = address.split('@', 1)
    dom_len = len(domain)
    from libsw import email
    for full_domain in email.get_mail_domains():
        if full_domain[:dom_len] == domain:
            print(user + '@' + full_domain)

def _add(address):
    from libsw import email
    from getpass import getpass
    user = False
    domain = False
    if address != False:
        user, domain = address.split('@')
    if domain == False:
        domain = email.select_domain()
    if user == False:
        user = input('Enter email name without "@' + domain + '": ')
    email.create_account(user, domain)
    password = email.hash_password( getpass('Email Password: ') )
    if email.SetPassword(user + '@' + domain, password).run():
        print('Account Created.')
    else:
        from libsw import settings
        print('Error while creating email account. Check to see if the account exists in ' + settings.get('mail_shadow_file'))
index.register_command('add', _add, autocomplete=_add_autocomplete)
index.register_command('create', _add)

def _address_autocomplete(args, end_with_space):
    if len(args) > 1:
        return
    if end_with_space and len(args) == 1 and len(args[0]) > 1:
        return
    address = args[0]
    length = len(address)
    from libsw import email
    for full_address in email.get_email_addrs():
        if full_address[:length] == address:
            print(full_address)

def _address_or_domain_autocomplete(args, end_with_space):
    if len(args) > 1:
        return
    if end_with_space and len(args) == 1 and len(args[0]) > 1:
        return
    argument = args[0]
    length = len(argument)
    from libsw import email
    for full_address in email.get_email_addrs():
        if full_address[:length] == argument:
            print(full_address)
    for full_domain in email.get_mail_domains():
        if full_domain[:length] == argument:
            print(full_domain)

def _domain_autocomplete(args, end_with_space):
    if len(args) > 1:
        return
    if end_with_space and len(args) == 1 and len(args[0]) > 1:
        return
    domain = args[0]
    length = len(domain)
    from libsw import email
    for full_domain in email.get_mail_domains():
        if full_domain[:length] == domain:
            print(full_domain)

def _remove(account, more):
    from libsw import email
    drop_files = more and more[0].lower() == 'dropfiles'
    if '@' not in account:
        print('Invalid email address. Did you mean "sw email unsetdomain ' + account + '"?')
    if account == False:
        account = email.select_email()
    drop_files = False
    if more and more[0].lower() == 'dropfiles':
        drop_files = True
    email.remove_account(account, drop_files)
index.register_command('remove', _remove, autocomplete=_address_autocomplete)
index.register_command('delete', _remove, autocomplete=_address_autocomplete)

def _setpass(address):
    from libsw import email
    from getpass import getpass
    if address != False and not email.account_exists(address):
        print(address + ' does not exist on this server.')
        address = False
    if address == False:
        address = email.select_email()
    password = email.hash_password( getpass('Email Password: ') )
    if email.SetPassword(address, password).run():
        print('Password Updated.')
    else:
        from libsw import settings
        print('Error. Password Not Updated. Check ' + settings.get('mail_shadow_file') + ' for syntax errors.')
index.register_command('setpass', _setpass, autocomplete=_address_autocomplete)
index.register_command('setpassword', _setpass, autocomplete=_address_autocomplete)

def _checkpass(address):
    from libsw import email
    from getpass import getpass
    if address != False and not email.account_exists(address):
        print(address + ' does not exist on this server.')
        address = False
    if not address:
        address = email.select_email()
    password = getpass('Email Password: ')
    error_message = email.check_pass(address, password)
    if error_message:
        print('Incorrect: ' + error_message)
    else:
        print('Correct')
index.register_command('checkpass', _checkpass, autocomplete=_address_autocomplete)
index.register_command('checkpassword', _checkpass, autocomplete=_address_autocomplete)

def _setdomain_autocomplete(args, end_with_space):
    if len(args) > 2:
        return
    if end_with_space and len(args) == 2 and len(args[-1]) > 1:
        return
    if len(args) == 1 and (not end_with_space or len(args[0]) == 0):
        _domain_autocomplete(args, end_with_space)
        return
    username = args[-1]
    if(end_with_space and len(args) == 1):
        username = ""
    length = len(username)
    from libsw import user
    for full_user in user.get_user_list():
        if full_user[:length] == username:
            print(full_user)

def _setdomain(domain, more):
    from libsw import email, user, cert
    sys_user = False
    if domain == False:
        domain = email.select_domain()
    elif more != False:
        sys_user = more[0]
        if not user.exists(sys_user):
            sys_user = False
    if sys_user == False:
        sys_user = user.select_user()
    email.add_mail_domain(domain, sys_user)
    if cert.has_cert(domain):
        cert.deploy_exim_domain(domain)
        cert.update_dovecot_ssl()

index.register_command('setdomain', _setdomain, autocomplete=_setdomain_autocomplete)

def _unsetdomain(domain):
    from libsw import email, cert
    if domain == False:
        domain = email.select_domain()
    email.remove_mail_domain(domain)
    cert.deploy_exim_domain(domain)
    cert.update_dovecot_ssl()
index.register_command('unsetdomain', _unsetdomain, autocomplete=_domain_autocomplete)

def _validate_domain_or_email(domain, domain_vs_email_string):
    from libsw import email
    user = False
    if domain == False:
        if _select_domain_over_user('Do you want to ' + domain_vs_email_string + ' for a domain or email user?'):
            domain = email.select_domain()
        else:
            account = email.select_email()
            user, domain = account.split('@')
        return user, domain
    print(domain)
    if '@' in domain:
        user, domain = domain.split('@')
        if not email.account_exists(user + '@' + domain):
            print(domain + ' is not an email account')
            account = email.select_email()
            user, domain = account.split('@')
    elif domain and not email.is_domain(domain):
        print(domain + ' is not a domain registered for email')
        domain = False
    if not domain:
        domain = email.select_domain()
    return user, domain

def _select_domain_over_user(query_message):
    """
    Returns True for a domain and False for a user
    """
    import inquirer
    options = [
        'Domain',
        'User'
    ]
    questions = [
        inquirer.List('o',
                    message=query_message,
                    choices=options
                )
    ]
    return 'Domain' == inquirer.prompt(questions)['o']

def _enablesa(domain_or_email):
    from libsw import email
    user, domain = _validate_domain_or_email(domain_or_email, 'enable SpamAssassin')
    dom_or_email = domain
    if user:
        dom_or_email = user + '@' + domain
    if email.enable_spamassassin(dom_or_email):
        print('Enabled SpamAssassin for ' + dom_or_email)
    else:
        print('SpamAssassin already enabled for ' + dom_or_email)
index.register_command('enablesa', _enablesa, autocomplete=_address_or_domain_autocomplete)

def _disablesa(domain_or_email):
    from libsw import email, input_util
    user, domain = _validate_domain_or_email(domain_or_email, 'disable SpamAssassin')
    dom_or_email = domain
    if user:
        dom_or_email = user + '@' + domain
    if email.disable_spamassassin(dom_or_email):
        print('Disabled SpamAssassin for ' + dom_or_email)
        if user and email.spamassassin_status(domain):
            if input_util.confirm('Do you also want to disable SpamAssassin for ' + domain + '?'):
                _disablesa(domain)
    else:
        print('SpamAssassin already disabled for ' + dom_or_email)
index.register_command('disablesa', _disablesa, autocomplete=_address_or_domain_autocomplete)

def _sastatus(domain_or_email):
    from libsw import email
    user, domain = _validate_domain_or_email(domain_or_email, 'get the SpamAssassin status')
    dom_or_email = domain
    if user:
        dom_or_email = user + '@' + domain
    domain_flag = email.spamassassin_status(domain)
    if domain_flag:
        print('SpamAssassin flag for ' + domain + ' is Enabled')
    else:
        print('SpamAssassin flag for ' + domain + ' is Disabled')
    user_flag = email.spamassassin_status(dom_or_email)
    if user:
        if user_flag:
            print('SpamAssassin flag for ' + dom_or_email + ' is Enabled')
        else:
            print('SpamAssassin flag for ' + dom_or_email + ' is Disabled')
        if user_flag or domain_flag:
            print('Therefore SpamAssassin is Enabled for ' + dom_or_email)
        else:
            print('Therefore SpamAssassin is Disabled for ' + dom_or_email)
index.register_command('sastatus', _sastatus, autocomplete=_address_or_domain_autocomplete)

def _dkim(domain):
    from libsw import email
    if domain and not email.is_domain(domain):
        print(domain + ' is not a domain registered for email')
        domain = False
    if not domain:
        domain = email.select_domain()
    email.create_and_install_dkim(domain)
index.register_command('dkim', _dkim, autocomplete=_domain_autocomplete)

def _list():
    from libsw import email
    from tabulate import tabulate
    domain_list = email.get_mail_domains()
    if len(domain_list) > 0:
        domain_table = []
        for domain in domain_list:
            username = email.get_account_from_domain(domain)
            domain_table.append([domain, username])
        print()
        print(tabulate(domain_table, ['Domain', 'System User']))
        print()
    else:
        print('No domains registered for email')
index.register_command('list', _list)
index.register_command('listdomain', _list)
index.register_command('listdomains', _list)

def _listusers():
    from libsw import email
    email_list = email.get_email_addrs()
    if len(email_list) > 0:
        print()
        for address in email_list:
            print(address)
        print()
    else:
        print('No accounts are registered for email')
index.register_command('listuser', _listusers)
index.register_command('listusers', _listusers)

def _get_user(domain):
    from libsw import email
    account = email.get_account_from_domain(domain)
    if account:
        print(account)
index.register_command('getuser', _get_user)

def _status(subversion):
    from libsw import email
    length = 0
    for slug, status in email.get_status_array():
        s_length = len(slug)
        if s_length > length:
            length = s_length
    for slug, status in email.get_status_array():
        spaces = length - len(slug)
        while spaces > 0:
            spaces -= 1
            slug = slug + ' '
        print(slug + ': ' + status)
index.register_command('status', _status)
