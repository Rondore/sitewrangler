#!/bin/bash

SW_DIR="$( cd -- "$(dirname "$0")/.." >/dev/null 2>&1 ; pwd -P )"
echo "Site Wrangler directory: $SW_DIR"

VENV_PATH="$SW_DIR/.venv"

SYS_PIP="pip3"
if [ -e /usr/bin/apt-get ]; then
  # Debian/Ubuntu
  if fuser /var/lib/dpkg/lock &>/dev/null; then
    echo "Waiting for another package manager to complete..."
    sleep 1
    while fuser /var/lib/dpkg/lock &>/dev/null; do
      sleep 1
    done
  fi

  /usr/bin/apt-get install -y python3-pip sysstat screen
elif [ -e /usr/bin/zypper ]; then
  # OpenSUSE
  /usr/bin/zypper --non-interactive install python3 python3-pip sysstat python3-devel logrotate screen
elif [ -e /usr/bin/dnf ]; then
  # Fedora / RHEL
  /usr/bin/dnf install -y epel-release
  /usr/bin/crb enable
  /usr/bin/dnf install -y python3 python3-pip sysstat logrotate screen
elif [ -e /usr/bin/yum ]; then
  # CentOS 7
  /usr/bin/yum install epel-release -y
  /usr/bin/yum update -y
  /usr/bin/yum install -y screen python36 python36-pip sysstat logrotate screen
elif [ -e /usr/sbin/pkg ]; then
  # FreeBSD / Solaris
  if [ "$(echo "$release" | grep '^ID=')" == "ID=solaris" ]; then
    SYS_PIP="pip-3.5"
    /usr/sbin/pkg install -y gccpython-35 pip-35 screen logrotate
  else
    /usr/sbin/pkg install -y python36 py36-pip screen logrotate
  fi
fi

python3 -m venv "$VENV_PATH"
VENV_PIP="$VENV_PATH/bin/$SYS_PIP"
$VENV_PIP install -r $SW_DIR/requirements.txt

SW_MAIN="$SW_DIR/bin/sitewrangler_venv.py"

echo "#!$VENV_PATH/bin/python3" > "$SW_MAIN"
cat >> "$SW_MAIN" <<THEEND
import sitewrangler
if __name__ == '__main__':
    sitewrangler.run_main();
THEEND
chmod +x "$SW_MAIN"

if [ ! -e /usr/local/bin/sw ]; then
  ln -s /opt/sitewrangler/bin/sitewrangler_venv.py /usr/local/bin/sw
fi

if [ ! -e /etc/bash_completion.d/sw ]; then
  echo "complete -C 'sw complete' sw" > /etc/bash_completion.d/sw
fi

echo 'include /opt/sitewrangler/etc/logrotate.d' > /etc/logrotate.d/sitewrangler.conf

systemctl enable --now sysstat
