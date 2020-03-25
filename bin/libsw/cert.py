#!/usr/bin/env python3

import os
import glob
import inquirer
import subprocess
import re
from pwd import getpwnam
from grp import getgrnam
from shutil import copyfile, rmtree
from libsw import email, nginx, settings, logger, file_filter, user

le_directory = '/etc/letsencrypt/'
source_cert_dir = le_directory + 'live'
source_key_dir = le_directory + 'live'
target_cert_dir = settings.get('exim_folder') + 'ssl/certs'
target_key_dir = settings.get('exim_folder') + 'ssl/private'

def get_mail_domain_list(domain):
    """
    Get an array of domains that should be covered for a given primary domain
    that uses email.

    Args:
        domain - The primary domain to use to create the list of
            domains/subdomains
    """
    return [domain, 'www.' + domain, 'mail.' + domain, 'webmail.' + domain]

def create_le_certs(domains, username):
    """
    Create a certificate for the given array of domains, using the given user's
    public_html folder for validation.

    Args:
        domains - An array of domains that will be covered by the new
            certificate
        username - The system user assigned to the domain
    """
    domain_string = ''
    for dom in domains:
        domain_string += ' -d ' + dom.lower().strip()
    command = 'letsencrypt certonly --noninteractive --webroot' + domain_string + ' --webroot-path "' + user.home_dir(username.strip()) + '/public_html/"'
    print(command)
    return 0 == os.system(command)

def remove_le_cert(domain):
    """
    Delete the certificate for the given domain from Let's Encrypt and exim.
    This will not invalidate the certificate.

    Args:
        domain - The primary domain on the certificate to be removed
    """
    path_list = [
        le_directory + 'archive/' + domain + '/',
        le_directory + 'live/' + domain + '/',
        le_directory + 'renewal/' + domain + '.conf'
    ]
    delete_count = 0
    for path in path_list:
        if os.path.isdir(path):
            rmtree(path)
            delete_count += 1
        elif os.path.isfile(path):
            os.remove(path)
            delete_count += 1
    if remove_exim_domain(domain):
        delete_count += 1
    return delete_count

def has_cert(domain):
    """
    Tests to see if a given domain is a primary domain on a certificate.

    Args:
        domain - The primary domain presumed to be on the certificate
    """
    target = source_cert_dir + '/' + domain + '/cert.pem'
    return os.path.exists(target)

def select_domain(query_message):
    """
    Have the user select a domain from a list of domains with a Let's Encrypt
    certificate.

    Args:
        query_message - The message to display in the prompt
    """
    files = []
    for filename in glob.glob(source_cert_dir + '/*/cert.pem'):
        domain = filename[ len(source_cert_dir)+1 : -9 ]
        files.append(domain)
    questions = [
        inquirer.List('f',
                    message=query_message,
                    choices=sorted(files)
                )
    ]
    domain = inquirer.prompt(questions)['f']
    return domain

def create_std_le_certs(domain, username):
    """
    Create a certificate for the given array of domains, using the given user's
    public_html folder for validation.

    Args:
        domain - The primary domain to use for the new certificate
        username - The system user associated with the domain
    """
    return create_le_certs(get_mail_domain_list(domain), username)

def create_nomail_le_certs(domain, username):
    """
    Create a certificate for the given array of domains, using the given user's
    public_html folder for validation.

    Args:
        domain - The primary domain to use for the new certificate
        username - The system user associated with the domain
    """
    return create_le_certs([domain, 'www.' + domain], username)

def deploy_file(source_file, target_file, uid=False, gid=False):
    """
    Copy a file but only if the source is newer than the target. While uid and
    gid are optional, you must specify both, for them to work.

    Args:
        source_file - The file to be copied.
        target_file - The path to copy the file to.
        uid - the system user id to own the new file
        gid - the system group id to own the new file

    Return:
        True if the file is copied. False if it is not.
    """
    if ( not os.path.exists(target_file) or
            os.path.getmtime(source_file) > os.path.getmtime(target_file) ):
        target_dir = os.path.dirname(target_file)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        copyfile(source_file, target_file)
        if uid and gid:
            os.chown(target_file, uid, gid)
        return True
    return False

def deploy(source_dir, target_dir, uid=False, gid=False):
    """
    Run deploy_file() for both the public and private keys.

    Args:
        source_dir - The folder to copy from
        target-dir - The folder to copy to
        uid - The numerical ID of the system user who should own the deployed file(s)
        gid - The numerical ID of the system group who should own the deployed file(s)
    """
    deployed_privkey = deploy_file(source_dir + 'privkey.pem', target_dir + 'privkey.pem', uid, gid)
    deployed_fullchain = deploy_file(source_dir + 'fullchain.pem', target_dir + 'fullchain.pem', uid, gid)
    return deployed_privkey or deployed_fullchain

def check():
    """
    Check for updates to certificates with Let's Encrypt and then push any
    updated files to exim as well as any users that require locally stored
    certificates.
    """
    with open(settings.install_path + 'log/letsencrypt', 'w+') as log_file:
        log = logger.Log(log_file)
        log.run(['letsencrypt', 'renew'])
        local_count = deploy_locals()
        count = deploy_all_exim_domains(log)
        if count > 0:
            update_dovecot_ssl()
            nginx.reload()
            log.log('Deployed ' + str(count) + ' certificates')

def deploy_locals():
    """
    Deploy certificates to local system users' "cert" folder
    """
    count = 0
    for domain in get_local_deploy_domains():
        username = nginx.user_from_domain(domain)
        target_dir = user.home_dir(username) + 'certs/'
        uid = getpwnam(username).pw_uid
        gid = getgrnam(username).gr_gid
        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
        if deploy('/etc/letsencrypt/live/' + domain + '/', target_dir, uid, gid):
            print('Deployed ' + username + ' certificate to ~/certs/')
            count += 1
    return count

def deploy_exim_cert(source_domain, target_domain, log=logger.Log(False)):
    """
    Run deploy_file() on the key and certificate paths for the given domains.
    This needs to be run for each domain listed in a certificate as the target
    domain.

    Args:
        source_domain - The main domain of the certificate
        target_domain - A list of domains covered by the certificate
        log - An open log file
    """
    deployed_cert = False
    deployed_key = False

    # Public Certificate
    source = source_cert_dir + '/' + source_domain + '/fullchain.pem'
    target = target_cert_dir + '/' + target_domain + '.pem'
    if not os.path.exists(source):
        log.log('Warning: no certificate found at ' + source)
    else:
        deployed_cert = deploy_file(source, target)

    # Private Key
    source = source_key_dir + '/' + source_domain + '/privkey.pem'
    target = target_key_dir + '/' + target_domain + '.pem'
    if not os.path.exists(source):
        log.log('Warning: no private key found at ' + source)
    else:
        deployed_key = deploy_file(source, target)
    return deployed_cert or deployed_key

def deploy_exim_domain(domain, log=logger.Log(False)):
    """
    Copies the certificate from Let's Encrypt to exim for each subdomain in the
    mail subdomain list.

    Args:
        domain - The main domain of the certificate
        log - An open log file
    """
    deployed = False
    #TODO - read covered domains instead of using a set list
    for sub in get_mail_domain_list(domain):
        if deploy_exim_cert(domain, sub, log):
            deployed = True
    return deployed

def remove_exim_domain(domain):
    """
    Delete the certificate and private key from exim for a given domain.

    Args:
        domain - The domain of the certificate
    """
    deleted = False
    #TODO - read covered domains instead of using a set list
    for sub in get_mail_domain_list(domain):
        cert = target_cert_dir + '/' + sub + '.pem'
        if os.path.exists(cert):
            os.path.remove(cert)
            deleted = True
        key = target_key_dir + '/' + sub + '.pem'
        if os.path.exists(key):
            os.path.remove(key)
            deleted = True
    return deleted

def has_exim_certs(domain):
    """
    Check if a given primary domain is covered by a certificate in
    Let's Encrypt.

    Args:
        domain - The primary domain to check
    """
    for sub in get_mail_domain_list(domain):
        cert = target_cert_dir + '/' + sub + '.pem'
        if os.path.exists(cert):
            return True
        key = target_key_dir + '/' + sub + '.pem'
        if os.path.exists(key):
            return True
    return False

def deploy_all_exim_domains(log=logger.Log(False)):
    """
    Check each certificate in Let's Encrypt against the corresponding exim. If
    the one in LE is newer or if the one in exim does not yet exist, the
    certificate and private key are copied once for each mail subdomain into
    exim's certificate and key folders.

    Args:
        log - An open log file
    """
    count = 0
    for dom in email.get_mail_domains():
        if deploy_exim_domain(dom, log):
            count += 1
    return count

def add_local_deploy(domain):
    """
    Register a domain to recieve copies of new certificates in the matching
    user's ~/cert directory.

    Args:
        domain - The domain to register
    """
    domain = domain.strip().lower()
    if not has_cert(domain):
        return False
    filename = settings.get('install_path') + 'etc/local-cert-deploy'
    updated = file_filter.AppendUnique(
            filename,
            domain,
            ignore_trim=True,
            ignore_case=True
        ).run()
    if updated:
        deploy_locals()
    return updated

def remove_local_deploy(domain):
    """
    Unregister a domain to recieve copies of new certificates in the matching
    user's ~/cert directory.

    Args:
        domain - The domain to unregister
    """
    domain = domain.strip()
    filename = settings.get('install_path') + 'etc/local-cert-deploy'
    return file_filter.RemoveExact(
                filename,
                domain,
                ignore_trim=True,
                ignore_case=True
            ).run()

def remove_local_certificates(domain):
    """
    Remove any certificates that were deployed to the matching user's ~/cert
    folder.

    Args:
        domain - The domain to unregister
    """
    domain = domain.strip()
    username = nginx.user_from_domain(domain)
    target_dir = user.home_dir(username) + 'certs/'
    count = 0
    for file in glob.glob(target_dir + '*.pem'):
        os.remove(file)
        count += 1
    return count

def get_local_deploy_domains():
    """
    Returns an array of domains that should have a copy of new certificates
    placed in ~/certs/ after renewal.
    """
    local_deploy = []
    local_filename = settings.get('install_path') + 'etc/local-cert-deploy'
    if os.path.exists(local_filename):
        with open(local_filename) as domain_list:
            for domain in domain_list:
                domain = domain.lower().strip()
                if not domain.startswith('#'):
                    local_deploy.append(domain.lower().strip())
    return local_deploy

def get_dovcot_section(domain, primary_domain):
    """
    Get the dovecot configuration file contents of a single domain's SSL
    certificate entry.

    Args:
        domain - The exact domain the entry is for (is equal to primary_domain or
            a subdomain of primary_domain)
        primary_domain - The primary domain on the certificate
    """
    return 'local_name ' + domain + ' {\n' \
        + '    ssl_cert = <' + source_cert_dir + '/' + primary_domain + '/fullchain.pem\n' \
        + '    ssl_key = <' + source_key_dir + '/' + primary_domain + '/privkey.pem\n' \
        + '}\n'

def update_dovecot_ssl():
    """
    Edit the dovecot configuration file to update the list of SSL certificates.
    """
    new_content = ''
    for domain in email.get_mail_domains():
        if os.path.exists(source_cert_dir + '/' + domain + '/fullchain.pem'):
            for sub in get_certificate_names(domain):
                new_content += get_dovcot_section(sub, domain)
    file_filter.UpdateSection(
            '/etc/dovecot/conf.d/10-ssl.conf',
            '# START Generated SNI Entries',
            '# END Generated SNI Entries',
            new_content
        ).run()
    email.restart_dovecot()

def get_certificate_names(domain):
    """
    Get an array of domains that are covered by the domain's Let's Enctrypt
    certificate.

    Args:
        domain - The domain to check
    """
    subject_re = re.compile('[ \s]*Subject:')
    alternate_re = re.compile('[ \s]*DNS:')

    valid_names = []

    filepath = source_cert_dir + '/' + domain + '/cert.pem'
    readout = subprocess.getoutput("openssl x509 -noout -text -in '" + filepath + "'")
    for line in readout.splitlines():
        if subject_re.match(line):
            main_domain = line.split(':')[1].strip().lower()
            eq_index = main_domain.find('=')
            if eq_index != -1:
                main_domain = main_domain[eq_index+1:]
            if main_domain not in valid_names:
                valid_names.append(main_domain)
        elif alternate_re.match(line):
            domain_list = line.split(',')
            for alternate in domain_list:
                alternate = alternate.split(':')[1].strip().lower()
                if alternate not in valid_names:
                    valid_names.append(alternate)
    return valid_names


def get_dates(domain):
    """
    Get an array of dates that are covered by the domain's Let's Enctrypt
    certificate. The first entry is the start date and the second entry is the
    end date.

    Args:
        domain - The domain to check
    """
    certname = source_key_dir + '/' + domain + '/cert.pem'
    output = subprocess.getoutput('openssl x509 -noout -dates -in "' + certname + '"').split('\n')
    retval = ['notfound', 'notfound']
    for line in output:
        line = line.strip()
        if line.startswith('notBefore='):
            retval[0] = line.split('=')[1].strip()
        elif line.startswith('notAfter='):
            retval[1] = line.split('=')[1].strip()
    return retval

def list():
    """
    Get a 2D array of domains registered in Let's Encrypt. Each row contains the
    domain, valid start date, and valid end date; in that order.
    """
    domains = []
    for filename in glob.glob(le_directory + 'renewal/*.conf'):
        dom = filename[len(le_directory)+8:-5]
        dates = get_dates(dom)
        domains.append([dom, dates[0], dates[1]])
    return sorted(domains, key=lambda k: k[0])
