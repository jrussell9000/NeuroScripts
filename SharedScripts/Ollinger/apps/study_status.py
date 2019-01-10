#!/usr/bin/env python

import os
import wbl_util
import socket

for partition in ('/study1', '/study2', '/study3', '/study4'):
    if wbl_util.ismounted(partition):
        print '%s is alive.' % partition
    else:
        print '%s is offline.' % partition
