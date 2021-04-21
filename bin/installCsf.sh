#!/bin/bash

#setup CSF
old_pwd=$(pwd)
cd /usr/local/src/
rm -fv csf.tgz
wget https://download.configserver.com/csf.tgz
tar -xzf csf.tgz
cd csf
sh install.sh
rm -fv csf.tgz
cd "$old_pwd"

if [ -e /usr/bin/apt-get ]; then
  # Debian/Ubuntu
  /usr/bin/apt-get install -y libwww-perl
elif [ -e /usr/bin/dnf ]; then
  # Fedora / CentOS 8
  /usr/bin/dnf install -y perl-libwww-perl net-tools perl-LWP-Protocol-https
elif [ -e /usr/bin/yum ]; then
  # CentOS 7
  /usr/bin/yum install perl-libwww-perl net-tools perl-LWP-Protocol-https -y
elif [ -e /usr/sbin/pkg ]; then
  # FreeBSD / Solaris
  # TODO install perl dependencies for csf
fi

echo 'Conforming CSF to Site Wrangler'

sed -Ei 's/^([ \s]*)TESTING[ \s]*=.*/\1TESTING = "0"/' /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)TCP_IN[ \s]*=.*/\1TCP_IN = "25,53,80,443,465,993"/' /etc/csf/csf.conf
sed -Ei 's/^([ \s]*)TCP6_IN[ \s]*=.*/\1TCP6_IN = "25,53,80,443,465,993"/' /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)TCP_OUT[ \s]*=.*/\1TCP_OUT = "1:65535"/' /etc/csf/csf.conf
sed -Ei 's/^([ \s]*)TCP6_OUT[ \s]*=.*/\1TCP6_OUT = "1:65535"/' /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)UDP_IN[ \s]*=.*/\1UDP_IN = "53,67,68"/' /etc/csf/csf.conf
sed -Ei 's/^([ \s]*)UDP6_IN[ \s]*=.*/\1UDP6_IN = "53,546,547"/' /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)UDP_OUT[ \s]*=.*/\1UDP_OUT = "53,113,123,67,68"/' /etc/csf/csf.conf
sed -Ei 's/^([ \s]*)UDP6_OUT[ \s]*=.*/\1UDP6_OUT = "53,113,123,546,547"/' /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)DENY_IP_LIMIT[ \s]*=.*/\1DENY_IP_LIMIT = "300"/' /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)SMTP_PORTS[ \s]*=.*/\1SMTP_PORTS = "25,465"/' /etc/csf/csf.conf

exim_user=$(sw setting get exim_user)
sed -Ei "s/^([ \\s]*)SMTP_ALLOWUSER[ \\s]*=.*/\\1SMTP_ALLOWUSER = \"$exim_user\"/" /etc/csf/csf.conf
sed -Ei "s/^([ \\s]*)SMTP_ALLOWGROUP[ \\s]*=.*/\\1SMTP_ALLOWGROUP = \"mail,mailman,$exim_user\"/" /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)LF_NETBLOCK[ \s]*=.*/\1LF_NETBLOCK = "1"/' /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)LF_POP3D[ \s]*=.*/\1LF_POP3D = "1"/' /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)LF_IMAPD[ \s]*=.*/\1LF_IMAPD = "1"/' /etc/csf/csf.conf

sed -Ei 's/^([ \s]*)1LF_CXS[ \s]*=.*/\1LF_CXS = "5"/' /etc/csf/csf.conf

sed -Ei 's~^([ \s]*)SMTPAUTH_LOG[ \s]*=.*~\1SMTPAUTH_LOG = "/var/log/exim4/mainlog"~' /etc/csf/csf.conf

sed -Ei 's~^([ \s]*)MODSEC_LOG[ \s]*=.*~\1MODSEC_LOG = "/opt/sitewrangler/log/modsec_audit.log"~' /etc/csf/csf.conf

sed -Ei 's~^([ \s]*)CUSTOM1_LOG[ \s]*=.*~\1CUSTOM1_LOG = "/var/log/exim4/rejectlog"~' /etc/csf/csf.conf

sed -Ei 's~^([ \s]*)CUSTOM2_LOG[ \s]*=.*~\1CUSTOM2_LOG = "/usr/local/nginx/logs/error.log"~' /etc/csf/csf.conf

sed -Ei 's~^([ \s]*)CUSTOM3_LOG[ \s]*=.*~\1CUSTOM3_LOG = "/var/local/nginx/logs/access.log"~' /etc/csf/csf.conf

echo "Enter the two-letter country code(s) you would like to have access \
to reading and sending email. See this link for codes: \
https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes Follow \
this format:"
echo 'US,CA,JP,GB,DE,IT,ES,RU,CN,UA,BR'
read -p '(leave blank to allow all countries): ' codes
if [ ! -z "$codes" ]; then
    sed -Ei '/^([ \s]*)(TCP_IN6?|SMTP_PORTS)/ s/,465//' /etc/csf/csf.conf
    sed -Ei '/^([ \s]*)(TCP_IN6?|SMTP_PORTS)/ s/,993//' /etc/csf/csf.conf
    sed -Ei '/^([ \s]*)(TCP_IN6?|SMTP_PORTS)/ s/465,?//' /etc/csf/csf.conf
    sed -Ei '/^([ \s]*)(TCP_IN6?|SMTP_PORTS)/ s/993,?//' /etc/csf/csf.conf

    sed -Ei "s/^([ \\s]*)CC_ALLOW_PORTS[ \\s]*=.*/\\1CC_ALLOW_PORTS = \"$codes\"/" /etc/csf/csf.conf
    sed -Ei 's/^([ \s]*)CC_ALLOW_PORTS_TCP[ \s]*=.*/\1CC_ALLOW_PORTS_TCP = "465,993"/' /etc/csf/csf.conf
    #CC_ALLOW_PORTS = "US"
fi

echo
echo "Enter the country code(s) for which you would like to block all traffic in the same format."
read -p '(leave blank to allow all countries): ' codes
sed -Ei "s/^([ \\s]*)CC_DENY[ \\s]*=.*/\\CC_DENY = \"$codes\"/" /etc/csf/csf.conf

nginx_log="/usr/local/nginx/logs/error.log"
syslog="/etc/csf/csf.syslogs"
if [ -z "$(grep "$nginx_log" $syslog)" ]; then
  sed -i "s~/var/log/nginx/error_log~/var/log/nginx/error_log\n$nginx_log~" $syslog
  if [ -z "$(grep "$nginx_log" $syslog)" ]; then
    echo "" >> $syslog
    echo "# Nginx:" >> $syslog
    echo "$nginx_log" >> $syslog
  fi
fi

admin_ip="${SSH_CLIENT%% *}"
echo "Whitelisting your IP $admin_ip to access all ports."
csf -a $admin_ip

echo 'Done.'
