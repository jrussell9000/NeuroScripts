#!/usr/bin/env python
 
import sys
import os
from numpy import fromstring, float32

from file_io import exec_cmd

ID = "$Id: print_header.py 188 2009-09-01 22:27:23Z jmo $"[1:-1]

def print_main():
    if(len(sys.argv) < 2):
        print "print_header P-file_name [-all -print_name]"
        print "    -all: Print all known header entries."
        print "    -print_name: Print file name on each line.\n"
        sys.exit(1)
    elif sys.argv[1] == '--version':
        sys.stdout.write('%s\n' % ID)
        sys.exit()

    filename = sys.argv[1]

    f = open(filename,"r")
    revision = fromstring(f.read(4),float32)
    f.close

    if (revision[0] < 5.) or (revision[0] > 50.):
    #   byteswap it.
        if numpy:
            version = revision.byteswap()
            print version
        else:
            version = revision.byteswapped()
        print "version: %3.1f" % version[0]
    else:
        version = revision[0]
        print "version: %3.1f" % version

    if version == 7.:
        cmd = "print_header_ge9"
    #    print "print_header_ge9"
    elif version == 9.:
        cmd = "print_header_ge11"
    #    print "print_header_ge11"
    elif version == 11.:
        cmd = "print_header_ge12"
    #    print "print_header_ge12"
    else:
        print "Unsupperted revision of P-file: %s" % filename
        sys.exit(1)

    for arg in sys.argv[1:]:
        cmd = "%s %s" % (cmd,arg)
    exec_cmd(cmd,0,1)

if __name__ == '__main__':
    print_main()
