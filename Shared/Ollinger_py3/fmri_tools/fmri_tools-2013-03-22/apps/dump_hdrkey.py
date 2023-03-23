#!/usr/bin/env python

ID = "$Id: dump_hdrkey.py 507 2011-05-13 23:39:23Z jmo $"[1:-1]

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

import sys
from file_io import Wimage
#import types
#import string
from datetime import datetime
import time
from optparse import OptionParser
from types import DictType
from wbl_util import except_msg

ID = "$Id: dump_hdrkey.py 507 2011-05-13 23:39:23Z jmo $"[1:-1]

#***********************************************
def key_callback(option,opt_str,value,parser):
#***********************************************

#   Create lists for multiple arguments of same type

    if "-k" in opt_str:
        parser.values.keys.append(value)


#************************************************
# Main

def get_key(hdr, key):
    if hdr.has_key(key):
        out = hdr[key]
    elif hdr['subhdr'].has_key(key):
        out = hdr['subhdr'][key]
    else:
        out = hdr['native_header'].get(key,'Not Found')
    return out

def dump_hdrkey_main():

    u1 = "\nUsage: dump_hdrkey -k key filename1 filename2 ...\n"
    usage = u1
    optparser = OptionParser(usage)
    optparser.add_option( "-K", "--dump_keys", action="store_true", \
                          dest="keysonly",default=False, help='Dump list of keys ("key" argument is ignored.')
    optparser.add_option( "-k", "--key", action="callback",callback=key_callback, \
                          dest="keys",type="string",default=[], help='A key to be extracted. This argument can be entered multiple times.')
    optparser.add_option( "-v", "--verbose", action="store_true", \
                          dest="verbose",default=False, help='Print filename, key, value if true. Otherwise only print value.')
    optparser.add_option( "-s", "--scan", action="store_true", \
                          dest="scan",default=False, help='Read all dicom files to accurately determine the R matrix.')
    optparser.add_option( "-f", "--print_fname", action="store_true", \
                          dest="printfname",default=False, help='Print filename at beginning of line.')
    optparser.add_option( "-l", "--line_feed", action="store_true", \
                          dest="linefeed",default=False, help='Print return at end of each line.')
    optparser.add_option( "-V", "--version", action="store_true",  \
                    dest="show_version",default=None, help="Display svn version.")
    optparser.add_option( "-y", "--ignore_yaml", action="store_true",  \
            dest="ignore_yaml",default=None, help="Ignore yaml file and re-read original data.")
    opts, args = optparser.parse_args()
    
    if opts.show_version:
        sys.stdout.write('%s\n' % ID) 
        sys.exit()
    
    if len(args) < 1:
        optparser.error( "\n\nThe keys depend on the type of file, so you have to enter a filename.\n*** Expecting 2 arguments, got %d ***,%s\nEnter dump_hdrkey --help for help\n" % (len(args),usage))
    
    filenames = args[:]

    must_scan = False
    for key in opts.keys:
        if key == 'R':
            must_scan = True
    
    for fname in filenames:
        wimg = Wimage(fname, scan=opts.scan, ignore_yaml=opts.ignore_yaml)
        hdr = wimg.hdr
        if hdr is None:
            raise RuntimeError('Could not read header from %s' % fname)
        if hdr['filetype'] == 'dicom' and must_scan and not opts.scan:
#           Must scan input for R to be accurate.
            sys.stderr.write(\
            '\n\t*************************** Warning **************************\n'+\
            '\tThe R matrix is may be incorrect for dicom files unless the\n'+\
            '\t--scan option is used.  (Each dicom file defines the 2D \n'+ \
            '\tposition of a single slice.  The third axis must be inferred\n'+\
            '\tfrom the slice-locations and ordering\n'
            '\t**************************************************************\n\n')
                            
        if not isinstance(hdr,DictType):
            continue
        if opts.keysonly:
            keys = hdr.keys()
            if hdr.has_key('native_header'):
                keys = keys + hdr['native_header'].keys()
            if hdr.has_key('subhdr'):
                keys = keys + hdr['subhdr'].keys()
            keys.sort()
            i = 1
            for key in keys:
                print "%d\t%s" % (i,key)
                i = i + 1
            sys.exit(1)
        if hdr['subhdr'].has_key('AcqTime'):
            sct = hdr['subhdr']['AcqTime']
            if isinstance(sct, str) and sct.isdigit():
                if  len(sct) > 6:
                    hdr['subhdr']['AcqTime'] = datetime.fromtimestamp(float(sct))
                else:
                    hdr['subhdr']['AcqTime'] = '%s:%s:%s' % \
                                            (sct[:2], sct[2:4], sct[4:])
        elif hdr['subhdr'].has_key('StudyDate'):
            hdr['subhdr']['StudyDate'] = datetime.fromtimestamp(float(hdr['subhdr']['StudyDate']))
    
        strout = ''
        wrote_fname = False
        oname = '%s\t' % fname
        if opts.printfname or opts.verbose:
            strout = oname
            if opts.verbose:
                strout = strout + '\n'
        else:
            strout = ''
        for key in opts.keys:
            if opts.verbose:
                strout += '%s\t%s' % (key, get_key(hdr, key))
            else:
                strout += '\t%s' % get_key(hdr, key)
            if opts.verbose:
                strout = strout + '\n'
            else:
                strout = strout.strip()
        if opts.linefeed:
            strout = strout + '\n'
        sys.stdout.write(strout)


if __name__ == '__main__':
    try:
        dump_hdrkey_main()
    except RuntimeError, err:
        sys.stderr.write('Error in dump_hdrkey: %s\n%s\n' % (err,except_msg()))
