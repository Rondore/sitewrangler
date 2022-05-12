#!/usr/bin/env python3

from libsw import input_util, command_index

def _help():
    print('sw cert list  # List all Let\'s Encrypt certificates indicating their expiration and if they are used in email')
    print('sw cert (add|create) [example.com [example_username] [`nomail`]]  # Get an SSL certificate for a domain')
    print('sw cert deploylocal [example.com]  # Deploy a copy of new certificaets into the user\'s "ssl" folder')
    print('sw cert nolocal [example.com [`dropfiles`]]  # Stop deploying certificates into the users home directory and optinally delete the ones there')
    print('sw cert deployexim [example.com]  # Copy SSL certificates from Let\'s Encrypt to exim')
    print('sw cert update  # Run a check to make sure all certificates are up-to-date')
    print('sw cert (delete|remove) [example.com [`dropfiles`]]  # Remove a domain from certificate updates and deployments and optionally the certificate files')
index = command_index.CategoryIndex('cert', _help)

def _add(domain, more):
    from libsw import cert, user, nginx, email
    sys_user = False
    nomail = False
    if domain == False:
        domain = input_util.input_domain()
    if more != False:
        if user.exists(more[0]):
            sys_user = more[0]
        if len(more) > 1 and more[1].lower() == 'nomail':
            nomail = True
        elif sys_user.lower() == 'nomail':
            sys_user = False
            nomail = True
    if sys_user == False:
        sys_user = nginx.user_from_domain(domain)
    if sys_user == False:
        sys_user = user.select_user()
    if nomail:
        cert.create_nomail_le_certs(domain, sys_user)
    else:
        cert.create_std_le_certs(domain, sys_user)
    if email.is_domain(domain):
        cert.deploy_exim_domain(domain)
        cert.update_dovecot_ssl()
        email.reload_exim()
index.register_command('add', _add)
index.register_command('create', _add)

def _deployexim(domain):
    from libsw import cert, email
    count = 0
    if domain == False:
        count = cert.deploy_all_exim_domains()
    else:
        if cert.deploy_exim_domain(domain):
            count = 1
    if count > 0:
        email.reload_dovecot()
        email.reload_exim()
index.register_command('deployexim', _deployexim)

def _deploylocal(domain):
    from libsw import cert
    if domain == False or not cert.has_cert(domain):
        domain = cert.select_domain("Select domain to deploy local certs for")
    updated = cert.add_local_deploy(domain)
    if updated:
        print('Added ' + domain + ' to local certificate deployments')
    else:
        print(domain + ' already gets local certificate deployments')
index.register_command('deploylocal', _deploylocal)

def _removelocal(domain, more):
    from libsw import cert
    if domain == False or not cert.has_cert(domain):
        domain = cert.select_domain("Select domain to stop deploying locally")
    dropped = cert.remove_local_deploy(domain)
    if dropped:
        print('Removed ' + domain + ' from local certificate deployments')
    else:
        print(domain  + ' was not registered to get local certificate deployments')
    if more and len(more) > 0 and more[0] == 'dropfiles':
        count = cert.remove_local_certificates(domain)
        print('Deleted ' + str(count) + ' .pem files')
index.register_command('nolocal', _removelocal)

def _remove(domain):
    from libsw import cert
    if not domain:
        domain = cert.select_domain("Select certificate to remove")
    if not cert.has_cert(domain):
        print(domain + ' is not covered by a certificate.')
        return
    if cert.remove_le_cert(domain) > 0:
        print('Removed certificate for ' + domain)
index.register_command('remove', _remove)
index.register_command('delete', _remove)

def _update():
    from libsw import cert
    cert.check()
index.register_command('update', _update)

def _list():
    from libsw import cert
    from tabulate import tabulate
    cert_list = cert.list()
    if len(cert_list) == 0:
        print('No certificates found')
    else:
        print()
        print(tabulate(cert_list, ['Domain', 'Issued', 'Expires']))
        print()
index.register_command('list', _list)
