#!/bin/bash
# Change ownership from a synced cPanel user
# Run this from the user's home directory as root

lsline=$(ls -la logs | head -2 | tail -1)
oldName=$(echo "$lsline" | awk '{print $3}')
oldGroup=$(echo "$lsline" | awk '{print $4}')
newName="${PWD##*/}"
find . -group $oldGroup -exec chgrp $newName {} \;
find . -user $oldName -exec chown $newName {} \;
find . -group 99 -exec chgrp daemon {} \;
chgrp daemon public_html/
