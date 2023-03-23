#!/usr/bin/env python

# Written by John Ollinger
#
# University of Wisconsin, 8/16/09

#Copyright (c) 2006-2007, John Ollinger, University of Wisconsin
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are
#met:
#
#    * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ** This software was designed to be used only for research purposes. **
# ** Clinical uses are not recommended, and have never been evaluated. **
# ** This software comes with no warranties of any kind whatsoever,    **
# ** and may not be useful for anything.  Use it at your own risk!     **
# ** If these terms are not acceptable, you aren't allowed to use the code.**


import os
import sys
from file_io import Header, file_type
from wbl_util import except_msg, GetTmpSpace
from optparse import OptionParser

ID = "$Id: write_yaml_header.py 352 2010-10-07 18:27:46Z jmo $"[1:-1]

ROOT_UID = 1184
MRI_UID = 202
MRI_GID = 1000

class WriteYamlHeader():

    def __init__(self):
        self.ParseOptions()

        self.uid = os.getuid()
        os.umask(0113) # Ensure group write access.
        self.access_mode = 0664

        self.WriteHdr()


    def ParseOptions(self):
        usage = 'compress_rawdata <options> <top-directory>\n' + \
                '\tEnter --help for more information.\n\n'
        optparser = OptionParser(usage)

        optparser.add_option( "-v", "--verbose", action="store_true", \
                    dest="verbose",default=False, \
                    help='Print useless stuff to screen.')
        optparser.add_option( "-V", "--version", action="store_true",  \
                dest="show_version",default=None, help="Display svn version.")

        self.opts, args = optparser.parse_args()

        if self.opts.show_version:
            sys.stdout.write('%s\n' % ID)
            sys.exit()

        if len(args) != 1:
            errstr = "\nExpecting 1 argument:\n" + usage
            sys.stderr.write(errstr)
            sys.exit(1)

        self.dname = args[0]
        while self.dname.endswith('/'):
            self.dname = self.dname[:-1]

    def WriteHdr(self):
        yaml_file = '%s/%s.yaml' % (self.dname,os.path.basename(self.dname))
        try:
            hd = Header(self.dname, scan=True)
            if hd.hdr:
                hd.write_hdr_to_yaml(yaml_file)
            else:
                sys.stderr.write('Error writing yaml file: %s\n' % yaml_file)
                sys.exit(1)
        except RuntimeError, err:
            sys.stderr.write('\n%s\n%s\n' % (err.errmsg, except_msg()))
            sys.exit(1)
        except IOError, err:
            sys.stderr.write('\n%s\n%s\n' % (err, except_msg()))
            sys.exit(1)
        try:
            os.chown(yaml_file, MRI_UID, MRI_GID)
        except OSError, err:
            sys.stderr.write('\n%s\n%s\n\n' % (err, except_msg()))
            os.remove(yaml_file)

def write_yaml_header():
    cr = WriteYamlHeader()

if __name__ == '__main__':
    write_yaml_header()
