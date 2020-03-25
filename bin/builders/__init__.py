#!/usr/bin/env python3

import glob
import os
__all__ = []
directory = os.path.dirname(os.path.realpath(__file__)) + '/'
for name in glob.glob( directory + '*.py' ):
    fileslug = name[len(directory):-3]
    if fileslug != '__init__':
        __all__.append(fileslug)
