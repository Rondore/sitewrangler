#!/bin/bash

if [ ! -e /usr/local/bin/sw ]; then
  ln -s /opt/sitewrangler/bin/sitewrangler.py /usr/local/bin/sw
fi

if [ ! -e /etc/bash_completion.d/sw ]; then
  echo "complete -C 'sw complete' sw" > /etc/bash_completion.d/sw
fi

pip="pip3"
if [ -e /usr/bin/apt-get ]; then
  # Debian/Ubuntu
  if fuser /var/lib/dpkg/lock &>/dev/null; then
    echo "Waiting for another package manager to complete..."
    sleep 1
    while fuser /var/lib/dpkg/lock &>/dev/null; do
      sleep 1
    done
  fi

  /usr/bin/apt-get install -y gcc make automake autoconf wget git bind9 screen build-essential libfcgi-dev libxml2-dev libbz2-dev libjpeg-dev libpng-dev libfreetype6-dev libxslt1-dev libzip-dev python3-pip libreadline-dev libtool certbot letsencrypt libkrb5-dev libpam0g-dev libmemcached-dev pkg-config mariadb-client mariadb-server libpcre3-dev libsqlite3-dev libonig-dev sysstat clamav clamav-daemon libgd-dev webp libwebp-dev libheif-dev libpsl-dev
  # for php 7.4 libsqlite3-dev libonig-dev

  release=$(cat /etc/*release)
  if [ "$(echo "$release" | grep '^ID=')" == "ID=debian" ]; then
    if [ "$(echo "$release" | grep '^VERSION_ID=')" == "VERSION_ID=\"10\"" ]; then
      # Debian 10 is missing freetype-config which causes php builds to fail
      old_dir="$PWD"
      cd /usr/bin/
      wget https://sitewrangler.org/download/debian-freetype-config
      mv debian-freetype-config freetype-config
      chmod +x freetype-config
      cd "$old_dir"
    fi
  elif [ "$(echo "$release" | grep '^ID=')" == "ID=ubuntu" ]; then
    /usr/bin/apt-get install -y libmysqlclient-dev
  fi
elif [ -e /usr/bin/zypper ]; then
  /usr/bin/zypper --non-interactive install gcc gcc-c++ make automake autoconf wget git bind python3 python3-pip libxml2-devel libzip-devel libpng16-devel libxslt-devel libjpeg62-devel libtool pcre-devel krb5-devel pam-devel libmemcached-devel mariadb mariadb-client pkgconf readline6-devel clamav sqlite3-devel libbz2-devel oniguruma-devel sysstat python3-devel perl-FindBin-Real perl-IPC-Run3 logrotate libpsl-devel libicu-devel
elif [ -e /usr/bin/dnf ]; then
  # Fedora / RHEL
  /usr/bin/dnf install -y epel-release
  /usr/bin/crb enable
  /usr/bin/dnf install -y gcc gcc-c++ make automake autoconf wget git bind python3 python3-pip libxml2-devel libzip-devel libpng-devel libxslt-devel libjpeg-turbo-devel libtool pcre pcre-devel krb5-devel pam-devel libmemcached-libs mariadb mariadb-server pkgconf-pkg-config readline-devel clamd clamav-update clamav sqlite-devel bzip2-devel oniguruma-devel platform-python-devel sysstat perl-FindBin perl-IPC-Cmd logrotate libpsl-devel libicu-devel
  # libfcgi-dev libfreetype6-dev certbot letsencrypt GeoIP-devel python-mysql3.connector screen
elif [ -e /usr/bin/yum ]; then
  # CentOS 7
  /usr/bin/yum install epel-release -y
  /usr/bin/yum update -y
  /usr/bin/yum install -y gcc gcc-c++ make automake autoconf wget git bind screen python36 python36-pip libxml2-devel libzip-devel libpng-devel libxslt1-devel libjpeg-turbo-devel MySQL-python libtool certbot pcre pcre-devel GeoIP-devel krb5-devel pam-devel libmemcached-dev mariadb mariadb-server readline-devel clamd clamav-update clamav sqlite-devel sysstat perl-FindBin perl-IPC-Cmd logrotate libpsl-devel libicu-devel
  # build-essential libfcgi-dev libbz2-dev libfreetype6-dev libreadline-dev letsencrypt pkg-config
elif [ -e /usr/sbin/pkg ]; then
  # FreeBSD / Solaris
  if [ "$(echo "$release" | grep '^ID=')" == "ID=solaris" ]; then
    pip="pip-3.5"
    /usr/sbin/pkg install -y gcc make automake autoconf wget git python-35 pip-35 pkg://solaris/service/network/dns/bind screen logrotate mysql-57 libtool pcre2
  else
    /usr/sbin/pkg install -y gcc make++ automake autoconf wget git python36 py36-pip bind914 screen logrotate
    # MAYBE: rndc-confgen -a
  fi
fi

cd /usr/include

#python
#$pip install --upgrade pip
$pip install argcomplete
$pip install fallocate
$pip install inquirer
$pip install python-iptables
$pip install python-dateutil
$pip install tabulate

$pip install requests
$pip install mysql-connector

#cron jobs
cat > /etc/cron.daily/check_domain_expiration <<THEEND
#!/bin/sh
/usr/bin/env sw dns checkexpire emailadmin &> /dev/null
THEEND
chmod +x /etc/cron.daily/check_domain_expiration

cat > /etc/cron.daily/update_software <<THEEND
#!/bin/sh
/usr/bin/env sw build update &> /dev/null
THEEND
chmod +x /etc/cron.daily/update_software

cat > /etc/cron.d/certbot <<THEEND
0 */12 * * * root /usr/bin/env sw cert update &> /dev/null
THEEND
chmod +x /etc/cron.d/certbot

#setup wp-cli
mkdir -p /opt/wp-cli/
wget https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar -O /opt/wp-cli/wp-cli.phar
chmod +x /opt/wp-cli/wp-cli.phar
test -e /usr/local/bin || mkdir -p /usr/local/bin
test -e /usr/local/bin/wp || ln -s /opt/wp-cli/wp-cli.phar /usr/local/bin/wp

mkdir -p /usr/local/ssl
if [ ! -e /usr/local/ssl/certs ]; then
  ln -s /etc/ssl/certs/ /usr/local/ssl/certs
fi

echo 'include /opt/sitewrangler/etc/logrotate.d' > /etc/logrotate.d/sitewrangler.conf

if [ -e /etc/default/sysstat ]; then
  sed -i 's/^ENABLED=.*/ENABLED="true"/' /etc/default/sysstat
else
  systemctl enable --now sysstat 
fi
