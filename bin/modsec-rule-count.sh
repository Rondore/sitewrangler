#/bin/bash

field="$1"
if [ -z "$field" ]; then
    field="id"
fi

regex="$2"
if [ -z "$regex" ]; then
    regex=".*"
fi

limit="cat"
if [ ! -z "$3" ]; then
    limit="tail -$3"
fi

folder=$(sw settings list install_path)

grep '^ModSecurity: ' ${folder}log/modsec_audit.log \
    | grep "$regex" \
    | $limit \
    | sed -r "s/^.*\\[$field \"([^\"]*)\".*\$/\\1/" \
    | awk '{count[$1]+=1;}END{for (c in count){print c ": " count[c]}}' \
    | sort -rn -t: -k2
