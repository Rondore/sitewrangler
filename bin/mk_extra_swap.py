#!/usr/bin/env python3

import os
from fallocate import fallocate

def make_extra_swap():
  #os.system('fallocate -l 1G /swapfile')
  with open("/swapfile", "w+b") as f:
    fallocate(f, 0, 1610612736) # 1610612736 = 1.5Gig
  os.chmod( '/swapfile', 0o600)
  os.system('mkswap /swapfile')
  os.system('swapon /swapfile')

if __name__ == "__main__":
  make_extra_swap()
