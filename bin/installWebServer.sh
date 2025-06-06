#!/bin/bash

SW_DIR="$( cd -- "$(dirname "$0")/.." >/dev/null 2>&1 ; pwd -P )"

if [ -e /usr/bin/apt-get ]; then
  # Debian/Ubuntu
  if fuser /var/lib/dpkg/lock &>/dev/null; then
    echo "Waiting for another package manager to complete..."
    sleep 1
    while fuser /var/lib/dpkg/lock &>/dev/null; do
      sleep 1
    done
  fi

  /usr/bin/apt-get install -y gcc make automake autoconf wget git bind9 screen build-essential libfcgi-dev libxml2-dev libbz2-dev libjpeg-dev libpng-dev libfreetype6-dev libxslt1-dev libzip-dev python3-pip libreadline-dev libtool certbot letsencrypt libkrb5-dev libpam0g-dev libmemcached-dev pkg-config mariadb-client mariadb-server libpcre3-dev libsqlite3-dev libonig-dev sysstat clamav clamav-daemon libgd-dev webp libwebp-dev libheif-dev libpsl-dev bison flex
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
  # OpenSUSE
  /usr/bin/zypper --non-interactive install gcc gcc-c++ make automake autoconf wget git bind python3 python3-pip libxml2-devel libzip-devel libpng16-devel libxslt-devel libjpeg62-devel libtool pcre-devel krb5-devel pam-devel libmemcached-devel mariadb mariadb-client pkgconf readline6-devel clamav sqlite3-devel libbz2-devel oniguruma-devel sysstat python3-devel perl-FindBin-Real perl-IPC-Run3 logrotate libpsl-devel libicu-devel python3-certbot bison flex
elif [ -e /usr/bin/dnf ]; then
  # Fedora / RHEL
  /usr/bin/dnf install -y epel-release
  /usr/bin/crb enable
  /usr/bin/dnf install -y gcc gcc-c++ make automake autoconf wget git bind python3 python3-pip libxml2-devel libzip-devel libpng-devel libxslt-devel libjpeg-turbo-devel libtool pcre pcre-devel krb5-devel pam-devel libmemcached-libs mariadb mariadb-server pkgconf-pkg-config readline-devel clamd clamav-update clamav sqlite-devel bzip2-devel oniguruma-devel platform-python-devel sysstat perl-FindBin perl-IPC-Cmd logrotate libpsl-devel libicu-devel bison flex
  # libfcgi-dev libfreetype6-dev certbot letsencrypt GeoIP-devel python-mysql3.connector screen
elif [ -e /usr/bin/yum ]; then
  # CentOS 7
  /usr/bin/yum install epel-release -y
  /usr/bin/yum update -y
  /usr/bin/yum install -y gcc gcc-c++ make automake autoconf wget git bind screen python36 python36-pip libxml2-devel libzip-devel libpng-devel libxslt1-devel libjpeg-turbo-devel MySQL-python libtool certbot pcre pcre-devel GeoIP-devel krb5-devel pam-devel libmemcached-dev mariadb mariadb-server readline-devel clamd clamav-update clamav sqlite-devel sysstat perl-FindBin perl-IPC-Cmd logrotate libpsl-devel libicu-devel bison flex
  # build-essential libfcgi-dev libbz2-dev libfreetype6-dev libreadline-dev letsencrypt pkg-config
elif [ -e /usr/sbin/pkg ]; then
  # FreeBSD / Solaris
  if [ "$(echo "$release" | grep '^ID=')" == "ID=solaris" ]; then
    /usr/sbin/pkg install -y gcc make automake autoconf wget git python-35 pip-35 pkg://solaris/service/network/dns/bind screen logrotate mysql-57 libtool pcre2
  else
    /usr/sbin/pkg install -y gcc make++ automake autoconf wget git python36 py36-pip bind914 screen logrotate
    # MAYBE: rndc-confgen -a
  fi
fi

cd /usr/include

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

mkdir -p $SW_DIR/ssl
if [ ! -e $SW_DIR/ssl/certs ]; then
  ln -s /etc/ssl/certs/ $SW_DIR/ssl/certs
fi

#setup wp-cli
sw wp install-cli
