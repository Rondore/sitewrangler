#/bin/bash

folder=$(sw settings list install_path)

grep '^Host: ' ${folder}var/log/modsec_audit.log \
    | sed 's/^Host://' \
    | awk '{count[$1]+=1;}END{for (c in count){print c ": " count[c]}}' \
    | sort -rn -t: -k2
