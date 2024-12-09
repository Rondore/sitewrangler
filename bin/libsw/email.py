#!/usr/bin/env python3

import re
import os
import inquirer
import subprocess
import platform
import pwd
import grp
import shutil
from email.mime.text import MIMEText
from libsw import file_filter, user, bind, service, settings

def get_detected_exim_user():
    user = 'Mail'
    group = 'Mail'

    test_group = subprocess.getoutput("sed -n '/^[^:]*[Ee]xim/ s/:.*//gp' /etc/group")
    test_user = subprocess.getoutput("sed -n '/^[^:]*[Ee]xim/ s/:.*//gp' /etc/passwd")
    if len(test_group) > 0:
        group = test_group
    if len(test_user) > 0:
        user = test_user

    return user, group

# functions that autodetect settings must come before importing settings
from libsw import settings

class SetPassword(file_filter.FileFilter):
    """Update the password for an email account."""
    def __init__(self, email, password_hash):
        self.password = password_hash
        self.email = email + ':'
        self.elen = len(self.email)
        super().__init__(settings.get('mail_shadow_file'))

    def filter_stream(self, in_stream, out_stream):
        updated = False
        for line in in_stream:
            if line[:self.elen] == self.email:
                new_line = line.split(':')
                new_line[1] = self.password
                new_line = ':'.join(new_line)
                out_stream.write(new_line)
                updated = True
            else:
                out_stream.write(line)
        return updated

def get_email_addrs(sort_by_user=False):
    """
    Get a list of all email addresses in the system sorted by domain
    alphabetically.

    Args:
        sort_by_user - (optional) Sort by user instead of domain
    """
    addrs = []
    regex = re.compile('^([^:]+):.*$')
    shadow_filename = settings.get('mail_shadow_file')
    if not os.path.exists(shadow_filename):
        return []
    with open(shadow_filename) as shadow:
        for line in shadow:
            match = regex.match(line)
            if match != None:
                addr = match.group(1)
                addrs.append(addr)
    if sort_by_user:
        addrs = sorted(addrs)
    else:
        addrs = sorted(addrs, key=lambda k: k.split('@')[1])
    return addrs

def select_email():
    """
    Have the user select from a list of all email addresses in the system sorted
    alphabetically.
    """
    versions = get_email_addrs()
    questions = [
        inquirer.List('addr',
                    message="Select Email Address",
                    choices=versions
                )
    ]
    return inquirer.prompt(questions)['addr']

def _get_spamassassin_flag_path(domain_or_user):
    """
    Get the full path of the file who's existence is used as a flag to turn
    SpamAssassin on.

    Args:
        domain_or_user - A full email address or a domain name
    """
    domain = domain_or_user.lower()
    user = False
    if '@' in domain:
        user, domain = domain.split('@')
    sys_user = get_account_from_domain(domain)
    if user:
        return '/home/' + sys_user + '/etc/' + domain + '/' + user + '/enable_spamassassin'
    else:
        return '/home/' + sys_user + '/etc/' + domain + '/enable_spamassassin'

def enable_spamassassin(domain_or_user):
    """
    Turn on SpamAssassin for either an entire domain or a single email account.

    Args:
        domain_or_user - A full email address or a domain name
    """
    path = _get_spamassassin_flag_path(domain_or_user)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    if not os.path.exists(path):
        with open(path, 'w+') as sa:
            pass
        return True
    return False

def disable_spamassassin(domain_or_user):
    """
    Turn on SpamAssassin for a domain or a single email account. If you disable
    SpamAssassin for a given email address with this function and the domain for
    that email address has SpamAssassin enabled, emails to the email address
    will still be filtered by SpamAssassin until SpamAssassin is disabled for
    the domain as well.

    Args:
        domain_or_user - A full email address or a domain name
    """
    path = _get_spamassassin_flag_path(domain_or_user)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False

def spamassassin_status(domain_or_user):
    """
    If a domain is passed, this method returns True if SpamAssassin is enabled
    domain-wide for the given domain and False otherwise. If an email address
    is passed, this method returns True if SpamAssassin is enabled for the email
    address specifically and false otherwise. When checking if an email address
    uses SpamAssassin, you should check the domain and email address seperatly.

    Args:
        domain_or_user - A full email address or a domain name
    """
    path = _get_spamassassin_flag_path(domain_or_user)
    return os.path.exists(path)

def system_from_addr():
    """
    Get the email address that should be used as the sender for all system
    messages.
    """
    return 'root@' + platform.node() # node() gets the local hostname

def send_admin_message(subject, message_content):
    """
    Send and email address to the System Administrator.

    Args:
        subject - The subject line for the email
        message_content - The body of the email message
    """
    line_limit = 900
    clean_output = ""
    for line in message_content.splitlines():
        while len(line) > line_limit:
            clean_output += line[:line_limit - 5] + '[...]\n'
            line = line[line_limit - 5:]
        clean_output += line + '\n'
    message = MIMEText(clean_output)
    message["From"] = system_from_addr()
    message["To"] = settings.get('system_admin_email')
    message["Subject"] = subject
    if os.path.exists('/usr/sbin/sendmail'):
        process = subprocess.Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=subprocess.PIPE)
        process.communicate( message.as_string().encode() )
        return True
    else:
        return False

def send_admin_logfile(subject, log_name):
    """
    Send the System Administrator a log file, using the contents of the log file
    as the body of the email.

    Args:
        subject - The subject line for the email
        log_name - The name of the log file
    """
    #TODO safty check the log size and send only the head, tail and log location if the log is over 4M
    with open(log_name) as email_file:
        send_admin_message(subject, email_file.read())

def send_admin_log_clip(subject, log_name):
    """
    Send the System Administrator the last 15 lines of a log file, using the
    contents of the log file as the body of the email.

    Args:
        subject - The subject line for the email
        log_name - The name of the log file
    """
    tail = subprocess.getoutput('tail -15 "' + log_name + '"')
    send_admin_message(subject, tail)

def hash_password(password, salt=False):
    """
    Generate a password hash with the given password.

    Args:
        password - The password to use in the hash
        salt (optional) - The password salt to use in the hash. A new salt will
            be generated if no salt is given.
    """
    command = "mkpasswd -m sha-512 '" + password + "'"
    if salt:
        command += ' "' + salt + '"'
    return subprocess.getoutput(command)

def get_hash(email_address):
    """
    Get the existing password hash for an email address.

    Args:
        email_address - The email address for which to get the salt.
    """
    hash = False
    regex = re.compile('^[^:]+:([^:]+):.*$')
    length = len(email_address) + 1
    email_with_seperator = email_address + ':'
    with open(settings.get('mail_shadow_file')) as shadow:
        for line in shadow:
            if line[:length] == email_with_seperator:
                match = regex.match(line)
                if match != None:
                    hash = match.group(1)
    return hash

def get_salt(hash):
    """Extract the encryption salt from a given password hash."""
    return re.match(r'\$6\$([^\$]+)\$', hash).group(1)

def check_pass(username, password):
    """Confirm if a given password is the given user's current password."""
    current_hash = get_hash(username)
    salt = get_salt(current_hash)
    new_hash = hash_password(password, salt)
    if new_hash != current_hash:
        return "Password does not match."
    output = subprocess.getoutput("doveadm auth test '" + username + "' '" + password + "'")
    output = output.split("\n")[0]
    if output.find('auth succeeded') == -1:
        return "Password is correct but dovecot is not accepting it. Contact your system administrator."
    return False

def get_mail_domains():
    """Get an array of all domains registered in the mail system."""
    domains = []
    with open(settings.get('mail_domain_file')) as file:
        for line in file:
            segments = line.split(':')
            domain = segments[0].strip().lower()
            if domain != '*':
                domains.append(domain)
    return sorted(domains)

def select_domain():
    """
    Prompt the user to select a domain from a list of all domains registered in
    the mail system.
    """
    versions = get_mail_domains()
    questions = [
        inquirer.List('dom',
                    message="Select Domain",
                    choices=versions
                )
    ]
    return inquirer.prompt(questions)['dom']

def is_domain(domain):
    """
    Check if a domain is registered in the mail system.

    Args:
        domain - The domain to check
    """
    return domain.lower() in get_mail_domains()

def get_account_from_domain(domain):
    """
    Get the username of the system user that stores email for the given domain.

    Args:
        domain - The domain to check
    """
    domain = domain.lower()
    with open(settings.get('mail_domain_file')) as file:
        for line in file:
            segments = line.split(':')
            if segments[0].strip().lower() == domain:
                return segments[1].strip()
    return False

def configuration_directory(domain, email_user, sys_user=False):
    """
    Get the directory to used to store configuration files for an email address.

    Args:
        domain - The domain of the email address
        email_user - The email username exluding the "@" and domain
        sys_user - (optional) The system user's username
    """
    if sys_user == False:
        sys_user = get_account_from_domain(domain)
    return user.home_dir(sys_user) + 'etc/' + domain + '/' + email_user + '/'

def mail_directory(domain, email_user, sys_user=False):
    """
    Get the directory used to store email messages for an email address.

    Args:
        domain - The domain of the email address
        email_user - The email username exluding the "@" and domain
        sys_user - (optional) The system user's username
    """
    if sys_user == False:
        sys_user = get_account_from_domain(domain)
    return user.home_dir(sys_user) + 'mail/' + domain + '/' + email_user + '/'

def create_account(email_user, domain):
    """
    Register a new email address in the mail system.

    Args:
        user - The email username exluding the "@" and domain
        domain - The domain of the email address
    """
    sys_user = get_account_from_domain(domain)
    pwd_user = pwd.getpwnam(sys_user)
    shadow_line = email_user + "@" + domain + '::'
    shadow_line += str(pwd_user.pw_uid) + ':' + str(pwd_user.pw_gid) + '::' + user.home_dir(sys_user) + '::'
    shadow_line += 'userdb_mail=maildir:~/mail/%Ld/%Ln\n'
    with open(settings.get('mail_shadow_file'), 'a+') as shadow:
        shadow.write(shadow_line)
    user.make_user_dir(configuration_directory(domain, email_user, sys_user), pwd_user.pw_uid, pwd_user.pw_gid) # for filters
    user.make_user_dir(mail_directory(domain, email_user, sys_user), pwd_user.pw_uid, pwd_user.pw_gid) # for maildir

def remove_account(account, delete_files=False):
    """
    Unregister an email address in the mail system, optionally removing it's
    files.

    Args:
        account - The email address to remove including the user, "@", and domain
        delete_files - (optional) Set to True to also remove ALL files for the
            email address as well including all settings and messages.
    """
    user, domain = account.lower().split('@')
    RemoveMailAccount(account).run()
    if delete_files:
        sys_user = get_account_from_domain(domain)
        shutil.rmtree(configuration_directory(domain, user, sys_user)) # for filters
        shutil.rmtree(mail_directory(domain, user, sys_user)) # for maildir

def account_exists(account):
    """Check if an email address is registered in the email system."""
    account = account.lower() + ':'
    length = len(account)
    found = False
    with open(settings.get('mail_shadow_file')) as shadow:
        for line in shadow:
            if line[:length].lower() == account:
                found = True
                break
    return found

class RemoveMailAccount(file_filter.FileFilter):
    """
    A FileFilter that removes a given email account from the shadow (password)
    file. Use this syntax: RemoveMailAccount('user@example.com').run()
    """
    def __init__(self, account):
        self.start = account + ':'
        self.len = len(self.start)
        super().__init__(settings.get('mail_shadow_file'))

    def filter_stream(self, in_stream, out_stream):
        removed = False
        for line in in_stream:
            if line.startswith(self.start):
                removed = True
            else:
                out_stream.write(line)
        return removed


class SetMailDomain(file_filter.AppendUnique):
    """
    A FileFilter that associates a domain with a system user. This must be run
    for a domain before you can register email addresses for the domain. Use
    this syntax: SetMailDomain('example.com', 'systemuser').run()
    """
    def __init__(self, domain, nix_account):
        domain = domain.lower().strip()
        nix_account = nix_account.strip()
        line = domain + ': ' + nix_account
        super().__init__(settings.get('mail_domain_file'), line, True, True)

class RemoveMailDomain(file_filter.RemoveRegex):
    """
    A FileFilter that removes the association of a domain with any system user.
    Use this syntax: ('example.com', 'systemuser').run()
    """
    def __init__(self, domain):
        domain = domain.lower().strip()
        reg = re.compile('^[ \s]*' + domain.replace('.','\.') + '[ \s]*:')
        super().__init__(settings.get('mail_domain_file'), reg)

def make_dkim_pair(domain):
    """
    Generate a new DKIM public key and private key. Then give EXIM access to
    those files.

    Args:
        domain - generate the keys for this domain
    """
    pem_file = settings.get('dkim_folder') + domain + '.pem'
    pub_file = settings.get('dkim_folder') + domain + '.pub'
    pwd_user = pwd.getpwnam(settings.get('exim_user')).pw_uid
    grp_group =  grp.getgrnam(settings.get('exim_group')).gr_gid
    subprocess.run(['openssl', 'genrsa', '-out', pem_file, '2048'])
    subprocess.run(['openssl', 'rsa', '-in', pem_file, '-pubout', '-out', pub_file])
    os.chown(pem_file, pwd_user, grp_group)
    os.chown(pub_file, pwd_user, grp_group)
    os.chmod(pem_file, 0o640)
    os.chmod(pub_file, 0o640)

def get_public_dkim_key(domain):
    """
    Get the contents of a public DKIM key with no line breaks.

    Args:
        domain - Get the public key for this domain
    """
    key = ''
    with open(settings.get('dkim_folder') + domain + '.pub') as pub:
        for line in pub:
            if line.startswith('-----'):
                continue
            key += line.replace('\n','').replace('\r','')
    return key

def make_dkim_dns_value(domain):
    """
    Generate a new DKIM public key and private key, give EXIM access to those
    files and encodes the public DKIM into chunks.

    Args:
        domain - generate the keys for this domain

    Return:
        The DKIM public key encoded for use in a DNS TXT record.
    """
    key = 'v=DKIM1; k=rsa; p='
    key += get_public_dkim_key(domain)
    chunks = int( len(key) / 255 )
    max_space = chunks * 255
    if max_space < len(key) :
        chunks += 1

    encoded_dkim = ""
    for i in range(0, chunks):
        start_char = (i*255)
        end_char = start_char + 255
        chunk = key[start_char:end_char]
        print('Adding chunk "' + chunk + '"')
        encoded_dkim += '"' + chunk + '" '
    return encoded_dkim.strip()

class DkimZoneUpdater(file_filter.FileFilter):
    """
    Update/Add a DKIM key to a DNS zone file. The DKIM key must already be
    encoded for a DNS TXT record.
    """
    def __init__(self, domain, encoded_dkim):
        self.domain = domain
        self.encoded_dkim = encoded_dkim
        super().__init__(bind.zone_folder + domain + '.db')

    def filter_stream(self, in_stream, out_stream):
        added = False
        for line in in_stream:
            if line.startswith('default._domainkey'):
                new_line = re.sub('TXT[\t \s]*.*', 'TXT	' + self.encoded_dkim, line)
                out_stream.write(new_line)
                added = True
            else:
                out_stream.write(line)
        if not added:
            out_stream.write('default._domainkey	900	IN	TXT	' + self.encoded_dkim)
        return True

def create_and_install_dkim(domain):
    """
    Create a new DKIM key pair and apply them to the DNS and mail system
    configuration for a domain.

    Args:
        domain - The domain to update with a new DKIM key pair
    """
    if domain and not os.path.exists(bind.zone_folder + domain + '.db'):
        print('No zone file for ' + domain + ' found.')
        domain = False
    if not domain:
        domain = bind.select_main_domain('Select site to add DKIM to: ')[:-3]
    dkim_folder = settings.get('dkim_folder')
    if not os.path.exists(dkim_folder + domain + '.pub'):
        if not os.path.exists(dkim_folder):
            os.makedirs(dkim_folder)
        make_dkim_pair(domain)
    dkim = make_dkim_dns_value(domain)
    print('TXT Encoded DKIM: ' + dkim)

    DkimZoneUpdater(domain, dkim).run()
    bind.increment_soa(domain)

    print('Reloading nameserver to apply changes...')
    bind.reload()
    print('Done.')

def restart_dovecot():
    """Restart the IMAP and POP server Dovecot."""
    service.restart('dovecot')

def restart_exim():
    """Restart the SMTP server Dovecot."""
    service.restart('exim4')

def reload_dovecot():
    """Reload the IMAP and POP server Dovecot."""
    service.reload('dovecot')

def reload_exim():
    """Reload the SMTP server Dovecot."""
    service.reload('exim4')

def get_status_array():
    """
    Get the status output for all mail-related services.

    Return:
        A two-dimensional array where each child element contains the following:
            A service name
            The status output for the assicated service
    """
    statuses = []
    for slug in ['dovecot', settings.get('exim_service'), 'spamassassin', 'clamav-daemon']:
        status = service.status(slug)
        statuses.append([slug, status])
    return statuses
