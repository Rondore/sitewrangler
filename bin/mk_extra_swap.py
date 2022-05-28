#!/usr/bin/env python3

import os
from fallocate import fallocate
from libsw import settings

def make_extra_swap():
  size = settings.get('swap_size')
  with open("/swapfile", "w+b") as f:
    fallocate(f, 0, size)
  os.chmod( '/swapfile', 0o600)
  os.system('mkswap /swapfile')
  os.system('swapon /swapfile')

if __name__ == "__main__":
  make_extra_swap()
