#!/usr/bin/env python3

import os

def remove_extra_swap():
  os.system('swapoff -v /swapfile')
  os.remove('/swapfile')

if __name__ == "__main__":
  remove_extra_swap()
