#!/bin/bash

if [ ! -e /usr/local/bin/sw ]; then
  ln -s /opt/sitewrangler/bin/sitewrangler.py /usr/local/bin/sw
fi

if [ ! -e /etc/bash_completion.d/sw ]; then
  echo "complete -C 'sw complete' sw" > /etc/bash_completion.d/sw
fi

#TODO allow user to set FQDN for mail server hostname
mail_hostname=$(hostname)
#TODO allow user to select main domain to use for non-SNI connections
non_sni_cert_domain="thegreatdivide.info"

if [ ! -e /etc/maildomains ]; then
  echo "*: nobody" > /etc/maildomains
fi

exim="exim"
eximConfig="monolithic"

echo 'Stage 1: Installing prerequsites'

pip="pip3"
if [ -e /usr/bin/apt-get ]; then
  # Debian/Ubuntu
  eximConfig="split"
  if fuser /var/lib/dpkg/lock &>/dev/null; then
    echo "Waiting for another package manager to complete..."
    sleep 1
    while fuser /var/lib/dpkg/lock &>/dev/null; do
      sleep 1
    done
  fi
  exim="exim4"
  /usr/bin/apt-get install -y bind9 dovecot-core dovecot-imapd python3-pip screen certbot letsencrypt exim4 exim4-daemon-heavy spamassassin sysstat
elif [ -e /usr/bin/dnf ]; then
  # Fedora / CentOS 8
  /usr/bin/dnf install -y bind dovecot-core dovecot-imapd python3-pip certbot letsencrypt exim exim4-daemon-heavy spamassassin platform-python-devel
  # screen
elif [ -e /usr/bin/yum ]; then
  # CentOS 7
  /usr/bin/yum install epel-release -y
  /usr/bin/yum update -y
  /usr/bin/yum install -y bind dovecot python36 python36-pip screen certbot exim spamassassin
  # exim4-daemon-heavy dovecot-imapd letsencrypt
elif [ -e /usr/sbin/pkg ]; then
  # FreeBSD
  if [ "$(echo "$release" | grep '^ID=')" == "ID=solaris" ]; then
    pip="pip-3.5"
    /usr/sbin/pkg install -y python36 pip-35 pkg://solaris/service/network/dns/bind screen exim dovecot logrotate ca_root_nss
  else
    /usr/sbin/pkg install -y python36 py36-pip bind914 screen exim dovecot logrotate ca_root_nss
  fi
  # MAYBE: rndc-confgen -a
  ln -s /usr/local/bin/pip-3.6 /usr/local/bin/pip3
  ln -s /usr/local/bin/python3.6 /usr/local/bin/python3
fi

echo 'Stage 2: Install Python Dependancies'

cd /usr/include

#python
#$pip install --upgrade pip
$pip install argcomplete
$pip install fallocate
$pip install inquirer
$pip install python-iptables
$pip install wget
$pip install python-dateutil
$pip install tabulate

echo 'Stage 3: Add crons'

#cron jobs
cat > /etc/cron.daily/check_domain_expiration << 'THEEND'
#!/bin/sh
/usr/bin/env sw dns checkexpire emailadmin &> /dev/null
THEEND
chmod +x /etc/cron.daily/check_domain_expiration

cat > /etc/cron.d/certbot << 'THEEND'
0 */12 * * * root /usr/bin/env sw cert update &> /dev/null
THEEND
chmod +x /etc/cron.d/certbot

#
# new exim config files
#

echo 'Stage 4: Add new exim config files'

mkdir -p /etc/$exim/certs/certs
mkdir -p /etc/$exim/certs/private

#if [ "$eximConfig" == "split" ]; then

cat > /etc/exim4/conf.d/router/320_exim4-config_spamassassin << 'THEEND'
#####################################################
### router/320_exim4-config_spamassassin
#####################################################

virtual_domain_spam:
  driver = accept
  condition = ${if eq{$h_X-Spam_Status:}{Yes}{true}{false}}
  require_files = "+/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/etc/$domain/enable_spamassassin:+/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part/"
  transport = dovecot_spam_transport

#####################################################
### end router/320_exim4-config_spamassassin
#####################################################
THEEND

cat > /etc/exim4/conf.d/router/321_exim4-config_spamassassin_user << 'THEEND'
#####################################################
### router/321_exim4-config_spamassassin_user
#####################################################

virtual_user_spam:
  driver = accept
  condition = ${if eq{$h_X-Spam_Status:}{Yes}{true}{false}}
  require_files = "+/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/etc/$domain/$local_part/enable_spamassassin:+/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part/"
  transport = dovecot_spam_transport

#####################################################
### end router/321_exim4-config_spamassassin_user
#####################################################
THEEND

cat > /etc/exim4/conf.d/router/330_exim4-config_domain_filter << 'THEEND'
#####################################################
### router/330_exim4-config_domain_filter
#####################################################

central_filter:
    driver = redirect
    allow_filter
    allow_fail
    forbid_filter_run
    forbid_filter_perl
    forbid_filter_lookup
    forbid_filter_readfile
    forbid_filter_readsocket
    no_check_local_user
    domains = !$primary_hostname
    require_files = "+/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/etc/$domain/filter:+/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part/"
    condition = "${extract{size}{${stat:/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/etc/$domain/filter}}}"
    file = /home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/etc/$domain/filter
    file_transport = address_file
    directory_transport = address_directory
#    pipe_transport = ${if forall{/bin/cagefs_enter:/usr/sbin/cagefsctl}{exists{$item}}{cagefs_virtual_address_pipe}{${if match{${extract{6}{:}{${lookup passwd{${lookup{$domain}lsearch{/etc/maildomains}{$value}}}{$value}}}}}{\N(jail|no)shell\N}{jailed_virtual_address_pipe}{virtual_address_pipe}}}}
    pipe_transport = address_pipe
    reply_transport = address_reply
    router_home_directory = /home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part/
    user = "${lookup{$domain}lsearch{/etc/maildomains}{$value}}"
    no_verify

#####################################################
### end router/330_exim4-config_domain_filter
#####################################################
THEEND

cat > /etc/exim4/conf.d/router/340_exim4-config_user_filter << 'THEEND'
#####################################################
### router/340_exim4-config_user_filter
#####################################################

virtual_user_filter:
    driver = redirect
    allow_filter
    allow_fail
    forbid_filter_run
    forbid_filter_perl
    forbid_filter_lookup
    forbid_filter_readfile
    forbid_filter_readsocket
    no_check_local_user
    domains = !$primary_hostname
    require_files = "+/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/etc/$domain/$local_part/filter:+/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part/"
    router_home_directory = /home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part/
#    router_home_directory = /home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/
    condition = "${extract{size}{${stat:/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/etc/$domain/$local_part/filter}}}"
    file = "/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/etc/$domain/$local_part/filter"
    directory_transport = address_directory
    file_transport = address_file
#    pipe_transport = ${if forall{/bin/cagefs_enter:/usr/sbin/cagefsctl}{exists{$item}}{cagefs_virtual_address_pipe}{${if match{${extract{6}{:}{${lookup passwd{${lookup{$domain}lsearch{/etc/maildomains}{$value}}}{$value}}}}}{\N(jail|no)shell\N}{jailed_virtual_address_pipe}{virtual_address_pipe}}}}
    pipe_transport = address_pipe
    reply_transport = address_reply
    user = "${lookup{$domain}lsearch{/etc/maildomains}{$value}}"
    local_part_suffix = +*
    local_part_suffix_optional
    retry_use_local_part
    no_verify

#####################################################
### end router/340_exim4-config_user_filter
#####################################################
THEEND

cat > /etc/exim4/conf.d/router/380_exim4-config_dovecot_router << 'THEEND'
#####################################################
### router/380_exim4-config_dovecot_router
#####################################################

# This router delivers mail to any dovecot virtual
# user who has a directory under /home/vmail/
# Place after remote router and before localuser router
# + addressing support requires uncommenting
dovecot_router:
  driver = accept
  require_files = +/home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part/
  transport = dovecot_transport

#####################################################
### end router/380_exim4-config_dovecot_router
#####################################################
THEEND

cat > /etc/exim4/conf.d/transport/30_exim4-config_maildir_home << 'THEEND'
#################################
### transport/30_exim4-config_maildir_home
#################################

# Use this instead of mail_spool if you want to to deliver to Maildir in
# home-directory - change the definition of LOCAL_DELIVERY
#
maildir_home:
  debug_print = "T: maildir_home for $local_part@$domain"
  driver = appendfile
  .ifdef MAILDIR_HOME_MAILDIR_LOCATION
  directory = MAILDIR_HOME_MAILDIR_LOCATION
  .else
  directory = /home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part
  .endif
  .ifdef MAILDIR_HOME_CREATE_DIRECTORY
  create_directory
  .endif
  .ifdef MAILDIR_HOME_CREATE_FILE
  create_file = MAILDIR_HOME_CREATE_FILE
  .endif
  delivery_date_add
  envelope_to_add
  return_path_add
  maildir_format
  .ifdef MAILDIR_HOME_DIRECTORY_MODE
  directory_mode = MAILDIR_HOME_DIRECTORY_MODE
  .else
  directory_mode = 0700
  .endif
  .ifdef MAILDIR_HOME_MODE
  mode = MAILDIR_HOME_MODE
  .else
  mode = 0600
  .endif
  mode_fail_narrower = false
  # This transport always chdirs to $home before trying to deliver. If
  # $home is not accessible, this chdir fails and prevents delivery.
  # If you are in a setup where home directories might not be
  # accessible, uncomment the current_directory line below.
  # current_directory = /
THEEND

cat > /etc/exim4/conf.d/transport/30_exim4-config_remote_smtp << 'THEEND'
#################################
### transport/30_exim4-config_remote_smtp
#################################
# This transport is used for delivering messages over SMTP connections.

DKIM_DOMAIN = ${lc:${domain:$h_from:}}
DKIM_FILE = /etc/exim4/dkim/${lc:${domain:$h_from:}}.pem
DKIM_PRIVATE_KEY = ${if exists{DKIM_FILE}{DKIM_FILE}{0}}
DKIM_SELECTOR = default
DKIM_CANON = relaxed

remote_smtp:
  debug_print = "T: remote_smtp for $local_part@$domain"
  driver = smtp
.ifdef REMOTE_SMTP_HOSTS_AVOID_TLS
  hosts_avoid_tls = REMOTE_SMTP_HOSTS_AVOID_TLS
.endif
.ifdef REMOTE_SMTP_HEADERS_REWRITE
  headers_rewrite = REMOTE_SMTP_HEADERS_REWRITE
.endif
.ifdef REMOTE_SMTP_RETURN_PATH
  return_path = REMOTE_SMTP_RETURN_PATH
.endif
.ifdef REMOTE_SMTP_HELO_DATA
  helo_data=REMOTE_SMTP_HELO_DATA
.endif
.ifdef DKIM_DOMAIN
dkim_domain = DKIM_DOMAIN
.endif
.ifdef DKIM_SELECTOR
dkim_selector = DKIM_SELECTOR
.endif
.ifdef DKIM_PRIVATE_KEY
dkim_private_key = DKIM_PRIVATE_KEY
.endif
.ifdef DKIM_CANON
dkim_canon = DKIM_CANON
.endif
.ifdef DKIM_STRICT
dkim_strict = DKIM_STRICT
.endif
.ifdef DKIM_SIGN_HEADERS
dkim_sign_headers = DKIM_SIGN_HEADERS
.endif
.ifdef TLS_DH_MIN_BITS
tls_dh_min_bits = TLS_DH_MIN_BITS
.endif
.ifdef REMOTE_SMTP_TLS_CERTIFICATE
tls_certificate = REMOTE_SMTP_TLS_CERTIFICATE
.endif
.ifdef REMOTE_SMTP_PRIVATEKEY
tls_privatekey = REMOTE_SMTP_PRIVATEKEY
.endif
THEEND

cat > /etc/exim4/conf.d/transport/40_exim4-config_dovecot_transport << 'THEEND'
#####################################################
### transport/40_exim4-config_dovecot_transport
#####################################################

# Transport to send any mail for virtual dovecot users to correct maildir box
dovecot_transport:
  debug_print = "T: dovecot_virtual appendfile for $local_part@$domain"
  driver = appendfile
#  file = /var/mail/$local_part@$domain
  directory = /home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part/
  delivery_date_add
  envelope_to_add
  return_path_add
  maildir_format
  user = "${lookup{$domain}lsearch{/etc/maildomains}{$value}}"
  group = mail
  mode = 0660
  mode_fail_narrower = false

#####################################################
### end transport/40_exim4-config_dovecot_transport
#####################################################
THEEND

cat > /etc/exim4/conf.d/transport/41_exim4-config_dovecot_spam_transport << 'THEEND'
#####################################################
### transport/41_exim4-config_dovecot_spam_transport
#####################################################

# Transport to send any mail for virtual dovecot users to correct maildir box
dovecot_spam_transport:
  debug_print = "T: dovecot_virtual_spam appendfile for $local_part@$domain"
  driver = appendfile
#  file = /var/mail/$local_part@$domain
  directory = /home/${lookup{$domain}lsearch{/etc/maildomains}{$value}}/mail/$domain/$local_part/.spam/
  delivery_date_add
  envelope_to_add
  return_path_add
  maildir_format
  user = "${lookup{$domain}lsearch{/etc/maildomains}{$value}}"
  group = mail
  mode = 0660
  mode_fail_narrower = false

#####################################################
### end transport/41_exim4-config_dovecot_spam_transport
#####################################################
THEEND

cat > /etc/exim4/conf.d/main/03_exim4-config_tlsoptions << 'THEEND'
#################################
### main/03_exim4-config_tlsoptions
#################################

# TLS/SSL configuration for exim as an SMTP server.
# See /usr/share/doc/exim4-base/README.Debian.gz for explanations.

.ifdef MAIN_TLS_ENABLE
# Defines what hosts to 'advertise' STARTTLS functionality to. The
# default, *, will advertise to all hosts that connect with EHLO.
#.ifndef MAIN_TLS_ADVERTISE_HOSTS
#MAIN_TLS_ADVERTISE_HOSTS = *
#.endif
#tls_advertise_hosts = MAIN_TLS_ADVERTISE_HOSTS
tls_advertise_hosts = *
tls_on_connect_ports = 465

# Full paths to Certificate and Private Key. The Private Key file
# must be kept 'secret' and should be owned by root.Debian-exim mode
# 640 (-rw-r-----). exim-gencert takes care of these prerequisites.
# Normally, exim4 looks for certificate and key in different files:
#   MAIN_TLS_CERTIFICATE - path to certificate file,
#                          CONFDIR/exim.crt if unset
#   MAIN_TLS_PRIVATEKEY  - path to private key file
#                          CONFDIR/exim.key if unset
# You can also configure exim to look for certificate and key in the
# same file, set MAIN_TLS_CERTKEY to that file to enable. This takes
# precedence over all other settings regarding certificate and key file.
#.ifdef MAIN_TLS_CERTKEY
#tls_certificate = MAIN_TLS_CERTKEY
#.else
#.ifndef MAIN_TLS_CERTIFICATE
#MAIN_TLS_CERTIFICATE = CONFDIR/exim.crt
#.endif
#tls_certificate = MAIN_TLS_CERTIFICATE

#.ifndef MAIN_TLS_PRIVATEKEY
#MAIN_TLS_PRIVATEKEY = CONFDIR/exim.key
#.endif
#tls_privatekey = MAIN_TLS_PRIVATEKEY

tls_certificate = ${if exists{/etc/exim4/ssl/certs/${tls_sni}.pem}{/etc/exim4/ssl/certs/${tls_sni}.pem}{/etc/exim4/ssl/certs/thegreatdivide.info.pem}}
tls_privatekey = ${if exists{/etc/exim4/ssl/private/${tls_sni}.pem}{/etc/exim4/ssl/private/${tls_sni}.pem}{/etc/exim4/ssl/private/thegreatdivide.info.pem}}

#.endif

# Pointer to the CA Certificates against which client certificates are
# checked. This is controlled by the `tls_verify_hosts' and
# `tls_try_verify_hosts' lists below.
# If you want to check server certificates, you need to add an
# tls_verify_certificates statement to the smtp transport.
# /etc/ssl/certs/ca-certificates.crt is generated by
# the "ca-certificates" package's update-ca-certificates(8) command.
.ifndef MAIN_TLS_VERIFY_CERTIFICATES
MAIN_TLS_VERIFY_CERTIFICATES = ${if exists{/etc/ssl/certs/ca-certificates.crt}\
                                    {/etc/ssl/certs/ca-certificates.crt}\
                                    {/dev/null}}
.endif
tls_verify_certificates = MAIN_TLS_VERIFY_CERTIFICATES


# A list of hosts which are constrained by `tls_verify_certificates'. A host
# that matches `tls_verify_host' must present a certificate that is
# verifyable through `tls_verify_certificates' in order to be accepted as an
# SMTP client. If it does not, the connection is aborted.
.ifdef MAIN_TLS_VERIFY_HOSTS
tls_verify_hosts = MAIN_TLS_VERIFY_HOSTS
.endif

# A weaker form of checking: if a client matches `tls_try_verify_hosts' (but
# not `tls_verify_hosts'), request a certificate and check it against
# `tls_verify_certificates' but do not abort the connection if there is no
# certificate or if the certificate presented does not match. (This
# condition can be tested for in ACLs through `verify = certificate')
# By default, this check is done for all hosts. It is known that some
# clients (including incredimail's version downloadable in February
# 2008) choke on this. To disable, set MAIN_TLS_TRY_VERIFY_HOSTS to an
# empty value.
.ifdef MAIN_TLS_TRY_VERIFY_HOSTS
tls_try_verify_hosts = MAIN_TLS_TRY_VERIFY_HOSTS
.endif

.endif
THEEND

cat > /etc/exim4/conf.d/main/50_exim4-config_clamav << 'THEEND'
#################################
### main/50_exim4-config_clamav
#################################
CHECK_DATA_LOCAL_ACL_FILE = /etc/exim4/conf.d/local-acl
av_scanner = clamd:/var/run/clamav/clamd.ctl
THEEND

cat > /etc/exim4/conf.d/local-acl << 'THEEND'
deny
  malware = *
  message = This message is suspected of conatining malware ($malware_name).
THEEND

usermod -a -G Debian-exim clamav
service clamav-daemon stop
service clamav-daemon start

#else

#TODO deploy monolithic configuration

#fi # end eximConfig == split, else statement

#
# new dovecot config files
#

echo 'Stage 5: Add Dovecot configuration files'

if [ ! -e /etc/dovecot/shadow ]; then
  touch /etc/dovecot/shadow
fi

if [ -z "$(grep subscribe /etc/dovecot/conf.d/15-mailboxes.conf | egrep -v '^#')" ]; then
  cat > /etc/dovecot/conf.d/15-mailboxes.conf << 'THEEND'
##
## Mailbox definitions
##

# Each mailbox is specified in a separate mailbox section. The section name
# specifies the mailbox name. If it has spaces, you can put the name
# "in quotes". These sections can contain the following mailbox settings:
#
# auto:
#   Indicates whether the mailbox with this name is automatically created
#   implicitly when it is first accessed. The user can also be automatically
#   subscribed to the mailbox after creation. The following values are
#   defined for this setting:
#
#     no        - Never created automatically.
#     create    - Automatically created, but no automatic subscription.
#     subscribe - Automatically created and subscribed.
#
# special_use:
#   A space-separated list of SPECIAL-USE flags (RFC 6154) to use for the
#   mailbox. There are no validity checks, so you could specify anything
#   you want in here, but it's not a good idea to use flags other than the
#   standard ones specified in the RFC:
#
#     \All      - This (virtual) mailbox presents all messages in the
#                 user's message store.
#     \Archive  - This mailbox is used to archive messages.
#     \Drafts   - This mailbox is used to hold draft messages.
#     \Flagged  - This (virtual) mailbox presents all messages in the
#                 user's message store marked with the IMAP \Flagged flag.
#     \Junk     - This mailbox is where messages deemed to be junk mail
#                 are held.
#     \Sent     - This mailbox is used to hold copies of messages that
#                 have been sent.
#     \Trash    - This mailbox is used to hold messages that have been
#                 deleted.
#
# comment:
#   Defines a default comment or note associated with the mailbox. This
#   value is accessible through the IMAP METADATA mailbox entries
#   "/shared/comment" and "/private/comment". Users with sufficient
#   privileges can override the default value for entries with a custom
#   value.

# NOTE: Assumes "namespace inbox" has been defined in 10-mail.conf.
namespace inbox {
  # These mailboxes are widely used and could perhaps be created automatically:
  mailbox Drafts {
    special_use = \Drafts
    auto = subscribe
  }
  mailbox spam {
    special_use = \Junk
    auto = no
  }
  mailbox Trash {
    special_use = \Trash
    auto = subscribe
  }

  # For \Sent mailboxes there are two widely used names. We'll mark both of
  # them as \Sent. User typically deletes one of them if duplicates are created.
  mailbox Sent {
    special_use = \Sent
    auto = subscribe
  }
  mailbox "Sent Messages" {
    special_use = \Sent
    auto = no
  }

  mailbox Archive {
    special_use = \Archive
    auto = create
  }                                                                                                                                                             #mailbox virtual/All {
                                                                                                                                                                #  special_use = \All
  mailbox "Archives" {
    special_use = \Archive
    auto = no
  }
}
THEEND
fi

#
# updates to existing exim config files
#

echo 'Stage 6: Updating exim files'

#echo 'Stage 6A'

macrofile="/etc/exim4/conf.d/main/01_exim4-config_listmacrosdefs"

if [ -z "$(grep '^CHECK_RCPT_IP_DNSBLS =' "$macrofile")" ]; then
  echo 'CHECK_RCPT_IP_DNSBLS = zen.spamhaus.org' >> $macrofile
else
  sed -Ei 's/^CHECK_RCPT_IP_DNSBLS =.*$/CHECK_RCPT_IP_DNSBLS = zen.spamhaus.org/' $macrofile
fi

#echo 'Stage 6B'

if [ -z "$(grep '^MAIN_TLS_ENABLE =' "$macrofile")" ]; then
  echo 'MAIN_TLS_ENABLE = yes' >> $macrofile
else
  sed -Ei 's/^MAIN_TLS_ENABLE =.*$/MAIN_TLS_ENABLE = yes/' $macrofile
fi

#echo 'Stage 6C'

if [ -z "$(grep '^MAIN_HARDCODE_PRIMARY_HOSTNAME =' "$macrofile")" ]; then
  echo "MAIN_HARDCODE_PRIMARY_HOSTNAME = $mail_hostname" >> $macrofile
else
  sed -Ei "s/^MAIN_HARDCODE_PRIMARY_HOSTNAME =.*\$/MAIN_HARDCODE_PRIMARY_HOSTNAME = $mail_hostname/" $macrofile
fi

#echo 'Stage 6D'

if [ -z "$(grep '^CHECK_RCPT_DOMAIN_DNSBLS =' "$macrofile")" ]; then
  echo "CHECK_RCPT_DOMAIN_DNSBLS = dbl.spamhaus.org/$sender_address_domain" >> $macrofile
else
  sed -Ei "s/^CHECK_RCPT_DOMAIN_DNSBLS =.*\$/CHECK_RCPT_DOMAIN_DNSBLS = dbl.spamhaus.org\/\$sender_address_domain/" $macrofile
fi

#echo 'Stage 6E'

# enable SpamAssassin
sed -Ei 's/^(#\s*)?spamd_address =.*$/spamd_address = 127.0.0.1 783/' /etc/exim4/conf.d/main/02_exim4-config_options

#echo 'Stage 6F'

config_check_data="/etc/exim4/conf.d/acl/40_exim4-config_check_data"
if [ -z "$(egrep '^\s*add_header = X-Spam_status.*$' $config_check_data)" ]; then
  line=$(egrep -n 'X-Spam' $config_check_data | tail -1 | cut -f1 -d:)
  let 'line+=1'
  sed -i -e "${line}i\\  warn" \
    -e "${line}i\\    spam = Debian-exim:true" \
    -e "${line}i\\    add_header = X-Spam_status: \${if >{\$spam_score_int}{50}{Yes}{No}}\\\\n\\\\" \
    -e "${line}i\\              X-Spam_score: \$spam_score\\\\n\\\\" \
    -e "${line}i\\              X-Spam_score_int: \$spam_score_int\\\\n\\\\" \
    -e "${line}i\\              X-Spam_bar: \$spam_bar\\\\n\\\\" \
    -e "${line}i\\              X-Spam_report: \$spam_report" "$config_check_data"
fi

#echo 'Stage 6G'

config_check_rcpt="/etc/exim4/conf.d/acl/30_exim4-config_check_rcpt"
rbl_response=$(grep -A 1 '\.ifdef CHECK_RCPT_DOMAIN_DNSBLS' $config_check_rcpt | tail -1)
if [ ! -z "$(echo "$rbl_response" | egrep '\s*warn')" ]; then
  line=$(grep -n '\.ifdef CHECK_RCPT_DOMAIN_DNSBLS' $config_check_rcpt | cut -f1 -d:)
  let 'line+=1'
  sed -Ei "${line}s/(\s*)warn/\\1deny/" $config_check_rcpt
fi

#echo 'Stage 6H'

rbl_response=$(grep -A 1 '\.ifdef CHECK_RCPT_IP_DNSBLS' $config_check_rcpt | tail -1)
if [ ! -z "$(echo "$rbl_response" | egrep '\s*warn')" ]; then
  line=$(grep -n '\.ifdef CHECK_RCPT_IP_DNSBLS' $config_check_rcpt | cut -f1 -d:)
  let 'line+=1'
  sed -Ei "${line}s/(\s*)warn/\\1deny/" $config_check_rcpt
fi

#echo 'Stage 6I'

confconf="/etc/exim4/update-exim4.conf.conf"

if [ -z "$(grep '^dc_use_split_config=' "$confconf")" ]; then
  echo "dc_use_split_config='true'" >> $confconf
else
  sed -Ei "s/^dc_use_split_config=.*\$/dc_use_split_config='true'/" $confconf
fi

#echo 'Stage 6J'

if [ -z "$(grep '^dc_localdelivery=' "$confconf")" ]; then
  echo "dc_localdelivery='maildir_home'" >> $confconf
else
  sed -Ei "s/^dc_localdelivery=.*\$/dc_localdelivery='maildir_home'/" $confconf
fi

#echo 'Stage 6K'

if [ -z "$(grep '^dc_eximconfig_configtype=' "$confconf")" ]; then
  echo "dc_eximconfig_configtype='internet'" >> $confconf
else
  sed -Ei "s/^dc_eximconfig_configtype=.*\$/dc_eximconfig_configtype='internet'/" $confconf
fi

#echo 'Stage 6L'

if [ -z "$(grep '^dc_local_interfaces=' "$confconf")" ]; then
  echo "dc_local_interfaces='[0.0.0.0]:25 ; [0.0.0.0]:465 ; ::1'" >> $confconf
else
  sed -Ei "s/^dc_local_interfaces=.*\$/dc_local_interfaces='[0.0.0.0]:25 ; [0.0.0.0]:465 ; ::1'/" $confconf
fi

#echo 'Stage 6M'

if [ -z "$(grep '^dc_other_hostnames=' "$confconf")" ]; then
  echo "dc_other_hostnames='$mail_hostname'" >> $confconf
else
  sed -Ei "s/^dc_other_hostnames=.*\$/dc_other_hostnames='$mail_hostname'/" $confconf
fi


#
# updates to existing dovecot config files
#

echo 'Stage 7: Modify dovecot configuration'

#echo 'Stage 7A'

# switch dovecot to passwd file authentication
sed -Ei \
  -e 's/^(\!include auth-.*)$/#\1/' \
  -e 's/#(\!include auth-passwdfile\.conf\.ext)/\1/' \
  /etc/dovecot/conf.d/10-auth.conf

#echo 'Stage 7B'

# set hierarchy seperator to '.' and the Prefix to 'INBOX.'
namespace_start=$(egrep -n '^namespace inbox {' /etc/dovecot/conf.d/10-mail.conf | head -1 | cut -f1 -d:)
namespace_end=$(tail -n +$namespace_start /etc/dovecot/conf.d/10-mail.conf | egrep -n '^}' | head -1 | cut -f1 -d:)
let 'namespace_end+=namespace_start'
sed -Ei \
  -e "$namespace_start,$namespace_end s/^(\\s*)#?(separator =).*/\\1\\2 ./" \
  -e "$namespace_start,$namespace_end s/^(\\s*)#?(prefix =).*/\\1\\2 INBOX./" \
  /etc/dovecot/conf.d/10-mail.conf

#echo 'Stage 7C'
sed -Ei \
  -e 's/^([ \s]*)#?(mail_uid =).*/\1\2 mail/' \
  -e 's/^([ \s]*)#?(mail_gid =).*/\1\2 mail/' \
  -e 's/^([ \s]*)#?(mail_privileged_group =).*/\1\2 mail/' \
  /etc/dovecot/conf.d/10-mail.conf

#echo 'Stage 7D'
if [ -z "$(grep 'unix_listener auth-client' /etc/dovecot/conf.d/10-master.conf)" ]; then
  userdb_line=$(egrep -n '[ \s]*unix_listener auth-userdb {' /etc/dovecot/conf.d/10-master.conf | cut -f1 -d:)
  sed -i \
    -e "${userdb_line}i\\  unix_listener auth-client {" \
    -e "${userdb_line}i\\    group = Debian-exim" \
    -e "${userdb_line}i\\    mode = 0600" \
    -e "${userdb_line}i\\    user = Debian-exim" \
    -e "${userdb_line}i\\  }" \
    -e "${userdb_line}i\\  " \
    /etc/dovecot/conf.d/10-master.conf
fi

#echo 'Stage 7E'
userdb_line=$(egrep -n '[ \s]*unix_listener auth-userdb {' /etc/dovecot/conf.d/10-master.conf | cut -f1 -d:)
userdb_end=$(tail -n +$userdb_line /etc/dovecot/conf.d/10-master.conf | grep -n '}' | head -1 | cut -f1 -d:)
let 'userdb_end+=userdb_line'
sed -Ei \
  -e "$userdb_line,$userdb_end s/^(\\s*)#?(mode =).*/\\1\\2 0666/" \
  -e "$userdb_line,$userdb_end s/^(\\s*)#?(user =).*/\\1\\2 mail/" \
  -e "$userdb_line,$userdb_end s/^(\\s*)#?(group =).*/\\1\\2 mail/" \
  /etc/dovecot/conf.d/10-master.conf

#echo 'Stage 7F'
worker_line=$(egrep -n '[ \s]*service auth-worker {' /etc/dovecot/conf.d/10-master.conf | cut -f1 -d:)
worker_end=$(tail -n +$worker_line /etc/dovecot/conf.d/10-master.conf | grep -n '}' | head -1 | cut -f1 -d:)
let 'worker_end+=worker_line'
sed -Ei \
  "$worker_line,$worker_end s/^(\\s*)#?(user =).*/\\1\\2 root/" \
  /etc/dovecot/conf.d/10-master.conf

#echo 'Stage 7G'
dict_line=$(egrep -n '[ \s]*unix_listener dict {' /etc/dovecot/conf.d/10-master.conf | cut -f1 -d:)
dict_end=$(tail -n +$dict_line /etc/dovecot/conf.d/10-master.conf | grep -n '}' | head -1 | cut -f1 -d:)
let 'dict_end+=dict_line'
sed -Ei \
  -e "$dict_line,$dict_end s/^(\\s*)#?(mode =).*/\\1\\2 0660/" \
  -e "$dict_line,$dict_end s/^(\\s*)#?(user =).*/\\1\\2 mail/" \
  -e "$dict_line,$dict_end s/^(\\s*)#?(group =).*/\\1\\2 mail/" \
  /etc/dovecot/conf.d/10-master.conf

#echo 'Stage 7H'
sed -Ei \
  -e 's/^([ \s]*)#?(ssl =).*/\1\2 required/' \
  -e 's/^([ \s]*)#?(ssl_prefer_server_ciphers =).*/\1\2 yes/' \
  -e 's/^([ \s]*)#?(ssl_protocols =).*/\1\2 !SSLv2/' \
  -e 's/^([ \s]*)#?(ssl_cipher_list =).*/\1\2 ALL:!LOW:!SSLv2:!EXP:!aNULL/' \
  -e "s~^#?(ssl_cert =).*~\\1 </etc/letsencrypt/live/$non_sni_cert_domain/fullchain.pem~" \
  -e "s~^#?(ssl_key =).*~\\1 </etc/letsencrypt/live/$non_sni_cert_domain/privkey.pem~" \
  /etc/dovecot/conf.d/10-ssl.conf

#echo 'Stage 7I'
# if missing, add a section for SNI SSL entries that python will later populate
if [ -z "$(egrep '^# START Generated SNI Entries' /etc/dovecot/conf.d/10-ssl.conf)" ]; then

  ssl_cert_line=$(egrep -n '\s*ssl_cert\s=' /etc/dovecot/conf.d/10-ssl.conf | cut -f1 -d:)
  ssl_key_line=$(egrep -n '\s*ssl_key\s=' /etc/dovecot/conf.d/10-ssl.conf | cut -f1 -d:)
  if [ "$ssl_cert_line" -lt "$ssl_key_line" ]; then
    ssl_cert_line="$ssl_key_line"
  fi
  rewind_count=$(head -n +$ssl_cert_line /etc/dovecot/conf.d/10-ssl.conf | tac | sed '/^$/q' | wc -l)
  let "ssl_cert_line-=(rewind_count-1)"
  let "blank_line=ssl_cert_line-1"
  sed -i \
    -e "${blank_line}G" \
    -e "${ssl_cert_line}i # START Generated SNI Entries" \
    -e "${ssl_cert_line}i # END Generated SNI Entries" \
    /etc/dovecot/conf.d/10-ssl.conf
fi

#echo 'Stage 7J'
sed -Ei 's/^(\s*)#?(mail_max_userip_connections =).*/\1\2 10/' /etc/dovecot/conf.d/20-imap.conf

#echo 'Stage 7K'
sed -i 's~/etc/dovecot/users~/etc/dovecot/shadow~' /etc/dovecot/conf.d/auth-passwdfile.conf.ext

#echo 'Stage 7L'
sed -i 's~\([ \s]*\)mail[ \s]*=[ \s]*maildir:.*$~\1mail = maildir:%{dict:userdb.home}/mail~' /etc/dovecot/dovecot-dict-auth.conf.ext

#
# add logrotate entry
#

echo 'Stage 8: Add master logrotate entry'
echo 'include /opt/sitewrangler/etc/logrotate.d' > /etc/logrotate.d/sitewrangler.conf

echo 'Stage 8: Add dkim folder to settings'
# set mail settings
sw setting set 'dkim_folder' "/etc/$exim/dkim/"
sw setting set 'exim_folder' "/etc/$exim/"

# enable sysstat
sed -i 's/^ENABLED=.*/ENABLED="true"/' /etc/default/sysstat

echo 'Stage 9: Start mail services'
#
# (re)start mail services
#
systemctl enable spamassassin
systemctl enable dovecot
systemctl enable  $exim

service dovecot restart
service $exim restart
