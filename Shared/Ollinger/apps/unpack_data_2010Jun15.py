#!/usr/bin/env python

# Purpose: Unpack compressed data file uploaded from scanner.

# By: John Ollinger

# June 11, 2008

import sys
import os
from os import O_RDONLY
import yaml
import cPickle
from optparse import OptionParser
from datetime import datetime
from cStringIO import StringIO
import bz2
import hashlib
from tarfile import TarFile
from subprocess import Popen, PIPE

from numpy import ndarray

from wimage_lib import Timer, except_msg
from file_io import add_ndarray_to_yaml, yaml_magic_code
from dicom import ScanDicomSlices

ID = "$Id: unpack_data.py 283 2010-05-14 16:47:10Z jmo $"[1:-1]
TMPDIR='/tmp'

SITE='waisman'


class UnpackDicoms():
    def __init__(self):
#       Setup site-specific info.
        if SITE == 'waisman':
            self.group = 'dusers'
            self.logfile = '/study/scanner/unpacked_exams.txt'
#            self.logfile = None #***********************
        else:
            self.group = 'admin'
            self.logfile = None

        usage = '\nExpecting two arguments\n' + \
                '\tUsage: unpack_data <input_file> <destination_dir>\n' + \
                '\tType unpack_data --help for more usage info.\n'
        optparser = OptionParser(usage)
        optparser.add_option( "-v", "--verbose", action="store_true", \
                dest="verbose",default=False, \
                help='Print useless stuff to screen.')
        optparser.add_option( "-V", "--version", action="store_true",  \
                dest="show_version",default=None, help="Display svn version.")
        opts, args = optparser.parse_args()
        
        if len(args) != 2:
            sys.stderr.write(usage)
            sys.exit(1)

        if os.path.exists(args[0]):
            self.infile = args[0]
        else:
            self.infile = '%s/%s' % (TMPDIR, os.path.basename(args[0]))
        self.outdir = (os.path.abspath(args[1]))
        self.outdir = self.outdir.replace('//','/')
        self.outdir = self.outdir.replace('//','/')
        self.found_cardiac = False

#       Log unpack action for future reference.
        self.LogStudy()

#        self.timer = Timer()
        self.md5 = hashlib.md5()
        self.host_type = self.GetHostType()

#       Setup yaml for reading numpy arrays.
        add_ndarray_to_yaml()

#       Load table of contents from uploaded data.
        self.toc = self.LoadToc()

#       Load the table of contents.
        self.SetupDirs()

    def LogStudy(self):
        if self.logfile is not None:
            date_tod = datetime.today().strftime('%a %b %d, %Y; %X')
            f = open(self.logfile, 'a')
            f.write('%s: %s %s\n' % (date_tod, self.infile, self.outdir))
            f.close()

    def GetHostType(self):
        output, errs = self.ExecCmd('uname')
        if errs:
            raise RuntimeError('Error determining host type.')
        return output.strip().lower()

    def SetupDirs(self):
#       Create raw-data directory and link directory.
  #      wds = self.outdir.split('/')
  #      if wds[1] == 'study':
  #          self.rawdir = '/%s/%s/raw-data/%s' % (wds[1], wds[2], wds[-1])
  #          self.linkdir = self.outdir
  #      elif wds[1] == 'Volumes':
  #          self.rawdir = '%s' % (self.outdir)
  #          self.linkdir = '%s' % (self.outdir)
  #      else:
  #          self.rawdir = '%s' % (self.outdir)
  #          self.linkdir = '%s/links' % (self.outdir)
        if not os.path.exists(os.path.dirname(self.rawdir)):
#           Directory named /study/mystudy/raw-data does not exist, write to 
#           user-specified directory.
            self.rawdir = self.outdir
        self.CreateDir(self.rawdir)
        if self.linkdir is not None:
            self.CreateDir(self.linkdir, linkdir=None, group=self.group)
        self.CreateDir('%s/dicoms' % self.rawdir)
        if self.linkdir is not None:
            self.CreateDir('%s/dicoms' % self.linkdir, group=self.group)
#        self.CreateLink('dicoms', 'anatomicals', self.group, self.rawdir)
#        if self.linkdir is not None:
#            self.CreateLink('dicoms', 'anatomicals', self.group, self.linkdir)

    def CreateDir(self, dname, linkdir=None, group=None):
        if not os.path.exists(dname):
            os.makedirs(dname)
            if group is not None:
                cmd = 'chgrp %s %s' % (group, dname)
                self.ExecCmd(cmd)
        if linkdir is not None:
            linkname = '%s/%s' % (linkdir, os.path.basename(dname))
            if not os.path.exists(linkname):
                self.CreateLink(dname, linkname, group)

    def CreateLink(self, srcname, linkname, group, relpath=None):
        """
        If relpath is set to a directory name, a local link will be created
        in relpath.
        """
        if relpath is None:
            if not os.path.lexists(linkname):
                os.symlink(srcname, linkname)
        else:
#           Create a relative link
            if os.path.exists('%s/%s' % (relpath, linkname)):
                return
            if not os.path.exists(relpath):
                raise RuntimeError('Relative path cannot be created in non-existent directory: %s' % relpath)
            src = os.path.basename(srcname)
            lnk = os.path.basename(linkname)
            cmd = 'cd %s && ln -s %s %s' % (relpath, src, lnk)
            self.ExecCmd(cmd)
            if group is not None:
                cmd = 'chgrp -P %s %s' % (group, lnk)
                self.ExecCmd(cmd)

    def LoadToc(self):
        sys.stdout.write('Loading table-of-contents ...')
        sys.stdout.flush()

        self.fd = os.open(self.infile, O_RDONLY)
        st = os.fstat(self.fd)
        os.lseek(self.fd, -42, 2)
        self.start_toc_str = os.read(self.fd, 10)
        self.scanner_md5 = os.read(self.fd, 32)
        self.start_toc = int(self.start_toc_str)
        lgth_toc = st.st_size - self.start_toc - 42
        os.lseek(self.fd, self.start_toc, 0)
        self.toc_serialized = os.read(self.fd, lgth_toc)
        os.lseek(self.fd, 0, 0)
        self.fd_ptr = 0

#       Convert table-of-contents. Rename npycore to core becase workaround
#       for GE's core-renaming issue isn't needed here.
        toc = cPickle.loads(self.toc_serialized)
        sys.stdout.write('\n')
        sys.stdout.flush()
        self.rawdir = toc['rawdir']
        self.linkdir = toc['linkdir']
#       ******* Patch  5/6/10 *****
        self.linkdir = None
#       *******************
        print 'Saving data to %s' % self.rawdir
        if self.linkdir is not None:
            print 'Creating links in %s' % self.linkdir
        return toc

    def WritePrescription(self):
        """
        Write the prescription read from review.out to both a yaml file.
        containing a dictionary holding the prescripton and a text file
        in a formatted human-readable form.
        """
        if not self.toc.has_key('prescription'):
#           Return immediately for old version without review data.
            return
        self.logdir = '%s/log' % self.rawdir
        self.CreatDir(self.logdir)
        f= open('%s/presciption.yaml' % self.logdir, 'w')
        f.write(self.toc['prescription'])
        f.close()
#       Write the prescription in text
        f= open('%s/presciption.txt' % self.logdir, 'w')
        f.write(self.toc['presc_fmt'])
        f.close()

    def CheckValidity(self, data, odir):
        try:
            udata = bz2.decompress(data)
        except AttributeError():
            errstr = \
                '\n****** Error decompressing data for %s ******\n\n' % odir
            sys.stderr.write(errstr)
            sys.exit(1)
        try:
            dcm =  ScanDicomSlices(udata)
            tsyntx = dcm.get_value('TransferSyntax',('undefined'))
        except RuntimeError, errstr:
            sys.stderr.write('\n%s\n%s\n' % (errstr, except_msg()))
            tsyntx = ''
       # if tsyntx != '1.2.840.10008.1.2.1':
#      #     Invalid transfer syntax, not a GE dicom file.
       #     errstr =  'Error: Invalid transfer syntax for %s: %s' % \
       #                                             (odir, tsyntx)
       #     sys.stderr.write('\n****** %s ******\n' % errstr)
       #     sys.exit(1)

    def ConvertToJpeg(self, fname):
        """
        Convert a dicom file saved in screen save syntax to jpeg.
        """
        cmd = 'bunzip2 %s' % fname
        self.ExecCmd(cmd)
        fname_bun = fname.replace('.bz2','')
        cmd = 'convert %s %s.jpg' % (fname_bun, fname_bun)
        print cmd
        try:
            self.ExecCmd(cmd)
        except OSError, errstr:
            sys.stderr.write( \
            '\n*** Non-fatal exception: ' + \
            'Error while converting dicom to jpeg. ***\n\tInput: %s\n%s\n' % \
                (fname_bun, except_msg()))
            

    def ExecCmd(self, cmd):
        f = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        output, errs = f.communicate()
        errs = f.wait()
        if errs < 0:
            raise OSError('Error while executing %s\n%s\n' % (cmd,except_msg()))
        return output, errs

    def UnpackDirs(self, toc_keys):
        """
        Setup output directories.
        """
        outdir_list = {}
        for odir in toc_keys:
            if odir not in outdir_list:
                fulldir = '%s/dicoms/%s' % (self.rawdir, odir)
                if self.linkdir is not None:
                    linkdir = '%s/dicoms' % self.linkdir
                else:
                    linkdir = None
                outdir_list[odir] = fulldir
                self.CreateDir(fulldir, linkdir=linkdir)

            if 'cardiac' not in odir and 'raw' not in odir:
                self.nfiles_packed[odir] = self.toc['series_toc'][odir]['nfiles']
                if not self.nfiles_unpacked.has_key(odir):
                    self.nfiles_unpacked[odir] = 0

#               Write yaml version of header.
                if isinstance(self.toc[odir], dict):
#                   Skip non-dicom directories such as cardiac.
                    fname = ('%s/%s.yaml' % \
                                    (outdir_list[odir], odir)).replace(' ','')
                    f1 = open(fname, 'w')
                    f1.write(yaml_magic_code)
                    f1.write(self.toc[odir]['hdr'])
                    f1.close()
            else:
                self.found_cardiac = True

    def Unpack(self):
        """ Unpack data from the entire data file."""

#       Write prescription info to log file.
        self.WritePrescription()
        toc_keys = self.toc['keylist']
        slice_toc = self.toc['slice_toc']
        self.nfiles_unpacked = {}
        self.nfiles_packed = {}

#       Create output directories.
        self.UnpackDirs(toc_keys)

#       Unpack the dicoms
        print self.toc['outdirs'].keys()
        for entry in slice_toc:
#           Unpack every dicom file.
            odir = self.toc['outdirs'].get(entry[2], None)
            if odir is None:
                print 'In Unpack, entry: ',entry
                raise RuntimeError(\
                'Entry not found in table of contents. key=%s' % entry[2])
            if self.nfiles_unpacked[odir] == 0:
                sys.stdout.write('Unpacking %d files in %s ...\n' % \
                                             (self.nfiles_packed[odir], odir))
                sys.stdout.flush()
            self.UnpackDicom(entry, odir, self.toc['series_toc'][odir]['nfiles'])
            self.nfiles_unpacked[odir] += 1

        if 'cardiac' in toc_keys:
#           Unpack cardiac data last.
            self.UnpackOther('cardiac', self.toc['cardiac'])
        os.close(self.fd)

#       Check for correct number of files.
        keys = self.nfiles_packed.keys()
        keys.sort()
        for key in keys:
            if self.nfiles_unpacked[odir] != self.nfiles_packed[odir] and \
                                               'localizer' not in odir:
                errstr = '\n*** Error during upload ***\n*** Only %d files out of %d files were found ***\n' % (self.nfiles_unpacked, self.nfiles_packed)
                sys.stderr.write(errstr)

    def UnpackDicom(self, toc_entry, odir, nfiles):
#       Unpack a single entry.
#       A single series can be stored in multiple directories 
#       on the scanner. The table of contents has one entry per
#       scanner directory per series. (more than one series might
#       be stored in a single scanner directory.
        data, lgth = self.ReadSlice(toc_entry)
        fname = ('%s/dicoms/%s' % (self.rawdir, \
                                   toc_entry[3])).replace(' ','')
        f1 = open(fname, 'w')
        f1.write(data)
        f1.close()
        if 'screensave' in fname:
            self.ConvertToJpeg(fname)

        if self.nfiles_unpacked[odir] == nfiles-2:
#           Check validity of last slice in this directory.
            self.CheckValidity(data, odir)

    def ReadSlice(self, toc_entry):
        lgth = toc_entry[1] - toc_entry[0]
        if self.fd_ptr != toc_entry[0]:
#           Noncontiguous location, seek to the right position
            self.fd_ptr = toc_entry[0]
            os.lseek(self.fd, self.fd_ptr, 0)
        data = os.read(self.fd, lgth)
        self.fd_ptr += lgth
        if lgth != len(data):
            raise IOError( \
            'Failure reading %s, tried to read %d bytes, got %d bytes' % \
                                                    (fname,lgth, len(data)))
        self.md5.update(data)
        return data, lgth

    def UnpackOther(self, odir, (position, lgth)):
        sys.stdout.write('Unpacking %s\n' % odir)
        sys.stdout.flush()
        os.lseek(self.fd, position, 0)
        data = os.read(self.fd, lgth)
        self.md5.update(data)
        sio = StringIO(data)
        tarfile = TarFile(odir, 'r', sio)
        tarfile.extractall(self.rawdir)
        tarfile.close()
        sio.close()
        if self.linkdir is not None:
            self.CreateLink('%s/%s' % (self.rawdir, odir), \
                            '%s/%s' % (self.linkdir, odir), self.group)

    def CheckMd5(self):
        self.md5.update(self.toc_serialized)
        self.md5.update(self.start_toc_str)
        new_md5 = self.md5.hexdigest()
        if new_md5 != self.scanner_md5:
            sys.stderr.write( \
            '\n\t*** Checksum Error ***\n')
            sys.stderr.write( \
            '\t\tChecksum on scanner:   \t%s\n' % self.scanner_md5)
            sys.stderr.write( \
            '\t\tChecksum after upload: \t%s\n\n' % new_md5)
            sys.exit(1)
        else:
            sys.stdout.write(
            '\n\tChecksum verified:\n')
            sys.stdout.write( \
            '\t\tChecksum on scanner:  \t%s\n' % self.scanner_md5)
            sys.stdout.write( \
            '\t\tChecksum after upload:\t%s\n' % new_md5)
            sys.stdout.flush()
            sys.exit(0)
        if not self.found_cardiac:
            print '*** No cardiac data were found in the uploaded file. ***'
            print '*** Check /usr/g/mrraw/Trash for a backup copy       ***' 

def unpack():
    try:
        u = UnpackDicoms()
        u.Unpack()
        u.CheckMd5()
    except (RuntimeError, OSError), err:
        sys.stderr.write('\nError unpacking data: %s\n%s\n\n' % \
                        (err, except_msg()))
    sys.stderr.write('\n')

if __name__ == '__main__':
    unpack()
