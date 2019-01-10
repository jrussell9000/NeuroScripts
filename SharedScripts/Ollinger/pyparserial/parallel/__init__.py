#!/usr/bin/env python 


VERSION = '0.2'

import sys

import os
# chose an implementation, depending on os
if os.name == 'posix':
    from parallelppdev import *
else:
    raise Exception("Sorry: no implementation for your platform ('%s') available" % os.name)

