#!/bin/bash

domain_list=`cat /etc/dovecot/shadow | awk -F ':' '{print $1}' | sed 's/.*@//' | sort | uniq`

for domain in $domain_list; do
  username=`sw email getuser "$domain"`
  uid=`id -u "$username"|grep -E '^[0-9]+$'|head -1`
  gid=`id -g "$username"|grep -E '^[0-9]+$'|head -1`
  echo "$domain:$uid:$gid"
  search_domain=`echo "$domain" | sed 's/\./\\\\./'`
  sed -i "s/^\\([^:]\\+@$search_domain:[^:]*\\):[0-9]*:[0-9]*:/\\1:$uid:$gid:/" /etc/dovecot/shadow
done
