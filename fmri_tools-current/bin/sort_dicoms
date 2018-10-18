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
from wbl_util import except_msg
from optparse import OptionParser
from subprocess import Popen, PIPE

ID = "$Id: sort_dicoms.py 493 2011-05-05 14:43:31Z jmo $"[1:-1]

class SortDicoms():

    def __init__(self):
        self.ParseOptions()
        os.umask(0002) # Ensure group write access.

    def ParseOptions(self):
        usage = 'sort_dicoms <options> <top-directory> <output_directory>\n' + \
                '\tEnter --help for more information.\n\n'
        optparser = OptionParser(usage)

        optparser.add_option( "-v", "--verbose", action="store_true", \
                    dest="verbose",default=False, \
                    help='Print useless stuff to screen.')
        optparser.add_option( "-f", "--force", action="store_true", \
                    dest="force",default=False, \
                    help='Delete existing links.')

        self.opts, args = optparser.parse_args()

        if len(args) != 2:
            errstr = "\nExpecting 2 arguments:\n" + usage
            sys.stderr.write(errstr)
            sys.exit(1)

        self.topdir = args[0]
        self.outdir = os.path.abspath(args[1])
        self.nfail = 0
        self.N = 0
        self.force = self.opts.force

    def FindFiles(self, topdir):
        self.exams = {}
        h = None
        for dirpath, dnames, fnames in os.walk(topdir):
#            print 'Directory %s contains %d files.' % (dirpath, len(fnames))
            self.dirpath = os.path.abspath(dirpath)
            N = len(fnames)
            if N > 0:
                print 'Processing %d files in %s/%s' % (N, topdir, dirpath)
            delta = float(N)/80.
            if delta < 1:
                delta = 1
            n = 0.
            for fname in fnames:
                if fname.startswith('.'):
#                   Skip macosx resource forks.
                    continue
                self.N += 1
                if (n % delta) < 1.:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                n += 1
                if fname == 'DICOMDIR':
                    continue
                fullname = os.path.abspath('%s/%s' % (dirpath, fname))
                ftype = file_type(fullname)
                if ftype is not 'dicom':
                    continue
                try:
                    h = Header(fullname)
                    if isinstance(h, Header) and h.hdr is not None:
                        self.hdr = h.hdr
                    else:
                        raise RuntimeError('Header could not be read from %s' % fullname)
                except ZeroDivisionError, errstr:
                    sys.stderr.write('%s: %s\n' % (errstr, fullname))
                    self.nfail += 1
                    h = None
#                    continue
                    sys.exit()
                except (KeyError, AttributeError), errstr:
                    sys.stderr.write('%s, %s\n%s\n' % (errstr, fullname, except_msg()))
                    self.nfail += 1
                    h = None
#                    continue
                    sys.exit()
                except (TypeError, RuntimeError), errstr:
                    sys.stderr.write('%s, %s\n%s\n' % (errstr, fullname, except_msg()))
                    sys.exit()

                pulse_sequence = ''
                scan_seq = self.hdr['native_header']['ScanningSequence']
                if isinstance(scan_seq, list):
                    for word in scan_seq:
                        pulse_sequence += '_%s' % word
                elif scan_seq is not None:
                    pulse_sequence = '_' + scan_seq
                else:
                    print 'skipping %s/%s' % (dirpath, fname)
                    continue
                pulse_sequence = pulse_sequence.replace(' ','')
                examno = self.hdr['subhdr']['ExamNumber']
                self.full_outdir = ('%s/E%s' % \
                                    (self.outdir, examno)).replace(' ','')
                if os.path.exists(self.full_outdir):
#                   Abort if output path already exists.
                    if self.force:
                        print '\n ***Output directory already exists. Deleting it. ***'
                        p = Popen('/bin/rm -r %s' % self.full_outdir, shell=True)
                        sts = os.waitpid(p.pid, 0)
                    else:
                        print '\n ***Output directory already exists. ***\n'
                        return None
                series = self.hdr['subhdr']['SeriesNumber']
                name = 'S%d%s' % (series, pulse_sequence)
                name = name.replace(' ','')
                dname = 'E%s/%s' % (examno, name)
                dname = dname.replace(' ','')
                serdir = '%s/%s' % (self.outdir, dname)
                instance = self.hdr['native_header']['InstanceNumber']
                acqtime = self.hdr['native_header']['AcquisitionTime']
                outfile = '%s/%s' %  (serdir, name)
                outfile = os.path.abspath(outfile.replace(' ',''))
                if not self.exams.has_key(examno):
                    self.exams[examno] = {}
                if not self.exams[examno].has_key(serdir):
                    self.exams[examno][serdir] = {}
                item = {'sourcefile': fullname, \
                        'outfile': outfile, \
                        'acqtime': acqtime}
                if self.exams[examno][serdir].has_key(instance):
                    self.exams[examno][serdir][instance].append(item)
                else:
                    self.exams[examno][serdir][instance] = [item]
            sys.stdout.write('\n')
        return True

    def MakeLinks(self):
        for examno in self.exams.keys():
            for serdir in self.exams[examno].keys():
                if not os.path.exists(serdir):
                    os.makedirs(serdir)
                keys = self.exams[examno][serdir].keys()
                nkeys = len(keys)
                for instance in keys:
                    items = self.exams[examno][serdir][instance]
                    if len(items) == 1:
                        idcs = [0]
                    else:
                        idcs = range(len(items))
                        idcs.sort(lambda x,y: \
                                cmp(items[x]['acqtime'], items[y]['acqtime']))
                    for idx in idcs:
                        inst = instance + idx*nkeys
                        outfile = '%s.%05d' % (items[idx]['outfile'], inst)
                        outfile = outfile.replace(' ','')
                        if not os.path.exists(outfile):
                            os.symlink(items[idx]['sourcefile'], outfile)

def sort_dicoms():
    cr = SortDicoms()
    fnames = os.listdir(cr.topdir)
    dnames = []
    for fname in fnames:
        fullpath = '%s/%s' % (cr.topdir, fname)
        if os.path.isdir(fullpath):
            dnames.append(fullpath)
    if len(dnames) < 2:
        dnames = [cr.topdir]
    dnames.sort()
    for dname in dnames:
        if os.path.isdir(dname):
#            sys.stdout.write('Processing %s ...' % dname)
#            sys.stdout.flush()
            if cr.FindFiles(dname):
                sys.stdout.write('Creating links.\n')
                sys.stdout.flush()
                cr.MakeLinks()
        print 'Total files: %d, Number unreadable: %d' % (cr.N,cr.nfail)

if __name__ == '__main__':
    sort_dicoms()
