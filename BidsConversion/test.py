#!/usr/bin/env python3
# coding: utf-8

import inspect
import sys
from pathlib import Path

lib_folder = Path.resolve(Path(inspect.getfile(inspect.currentframe())).parent / 'lib')
if not lib_folder.exists():
    sys.stderr.write('Unable to locate python libraries')
    sys.exit(1)
sys.path.insert(0, lib_folder)

print(lib_folder)
