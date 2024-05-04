#!/usr/bin/env python3

import os
from fallocate import fallocate
from libsw import settings

def make_extra_swap():
  size = settings.get('swap_size')
  if size[-1] == 'B' or size[-1] == 'b': size = size[:-1]
  if size[-1] == 'K' or size[-1] == 'k': size = float(size[:-1]) * 1024
  elif size[-1] == 'M' or size[-1] == 'm': size = float(size[:-1]) * (1024**2)
  elif size[-1] == 'G' or size[-1] == 'g': size = float(size[:-1]) * (1024**3)
  elif size[-1] == 'T' or size[-1] == 't': size = float(size[:-1]) * (1024**4)

  with open("/swapfile", "w+b") as f:
    fallocate(f, 0, int(size))
  os.chmod( '/swapfile', 0o600)
  os.system('mkswap /swapfile')
  os.system('swapon /swapfile')

if __name__ == "__main__":
  make_extra_swap()
