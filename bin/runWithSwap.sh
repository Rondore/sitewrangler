#!/bin/bash

#swapon
if [ -z "$(swapon | grep '/swapfile')" ]; then
  ~/bin/mkExtraSwap.py
fi

#ps aux | grep runWithSwap | grep -v grep |wc -l

exec "$@"

count="$(ps aux | grep runWithSwap | grep -v grep | wc -l)"
echo "$count"
if [ "$count" -lt "3" ]; then
  #swapoff
  ~/bin/rmExtraSwap.py
fi
echo "$(ps aux | grep runWithSwap | grep -v grep | wc -l)"
