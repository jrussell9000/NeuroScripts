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
import tarfile
from tarfile import TarFile, TarInfo, REGTYPE
from subprocess import Popen, PIPE
import pwd
import grp
import time
import socket

from numpy import ndarray

from wbl_util import Timer, except_msg, send_email, ismounted
from file_io import add_ndarray_to_yaml, yaml_magic_code, write_yaml
from wisc_dicom import ScanDicomSlices

ID = "$Id: unpack_data.py 584 2011-07-08 18:48:00Z jmo $"[1:-1]
TMPDIR='/tmp'

SITE='waisman'
RECIPIENTS = ['ollinger@gmail.com', 'mjanderle@gmail.com']


class UnpackDicoms():
    def __init__(self):

#       Setup site-specific info.
        full_hostname = socket.gethostname()
        self.hostname = full_hostname.split('.')[0]
        if 'mri.psychiatry.wisc.edu' in full_hostname:
            site = 'heri'
            self.group = 'admin'
            self.logfile = None
            self.no_dicomtars = True
        elif 'waisman.wisc.edu' in full_hostname:
            site = 'waisman'
            self.group = 'rawdata'
            self.logfile = '/study/scanner/unpacked_exams.txt'
            if not ismounted(self.logfile):
                self.logfile = None
            self.no_dicomtars = None
        else:
            site = 'wimr'
            self.logfile = None
            self.group = None
            self.no_dicomtars = None

#       Parse command line.
        self.ParseOptions()

        self.gid = grp.getgrnam(self.group)[2]
        self.uid = os.getuid()

        self.data_ok = True

#       Variables used when creating dicom-tarfiles.
        self.tarfiles = {}
        self.uname = pwd.getpwuid(os.getuid())[0]
        self.gname = grp.getgrgid(os.getgid())[0]
        self.mtime = time.time()

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

    def ParseOptions(self):
        usage = '\nExpecting two arguments\n' + \
                '\tUsage: unpack_data <input_file> <destination_dir>\n' + \
                '\tType unpack_data --help for more usage info.\n'
        optparser = OptionParser(usage)
#               Write yaml version of header.
        optparser.add_option( "-v", "--verbose", action="store_true", \
                dest="verbose",default=False, \
                help='Print useless stuff to screen.')
        optparser.add_option( "", "--no-dicomtars", action="store_true", \
                dest="no_dicomtars",default=False, \
                help='Store dicom files individually, not in tar archives.')
        opts, args = optparser.parse_args()
        
        if len(args) != 2:
            sys.stderr.write(usage)
            sys.exit(1)

        if os.path.exists(args[0]):
            self.infile = args[0]
        else:
            self.infile = '%s/%s' % (TMPDIR, os.path.basename(args[0]))
        if len(args) > 1:
            self.outdir = (os.path.abspath(args[1]))
            self.outdir = self.outdir.replace('//','/')
            self.outdir = self.outdir.replace('//','/')
        else:
            self.outdir = None
        self.found_cardiac = False
        if self.no_dicomtars is None:
            self.no_dicomtars = opts.no_dicomtars


    def LogStudy(self):
        """
        Log the fact that unpack_data was run.
        """
        if self.logfile is not None:
            date_tod = datetime.today().strftime('%a %b %d, %Y; %X')
            f = open(self.logfile, 'a')
            f.write('%s: %s %s\n' % (date_tod, self.infile, self.outdir))
            f.close()

    def GetHostType(self):
        """
        Return the hostname as specified by "uname"
        """
        output, errs = self.ExecCmd('uname')
        if errs:
            raise RuntimeError('Error determining host type.')
        return output.strip().lower()

    def SetupDirs(self):
        """
        Create the output directories.
        """
        self.CreateDir(self.rawdir, group=self.group)
        if self.linkdir is not None:
            self.CreateDir(self.linkdir, linkdir=None, group=self.group)
        self.CreateDir('%s/dicoms' % self.rawdir)
        if self.linkdir is not None:
            self.CreateDir('%s/dicoms' % self.linkdir, group=self.group)

    def CreateDir(self, dname, linkdir=None, group=None):
        """
        Create a single directory.
        """
        if not os.path.exists(dname):
            os.makedirs(dname)
        if os.stat(dname)[5] != self.gid:
            try:
                os.chown(dname, self.uid, self.gid)
            except:
                sys.stderr.write( \
                '\n*** Attempt to change permissions of %s failed.\n' % dname)
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
        """
        Load the table-of-contents.  The last ten bytes of the file are a ten-digit string specifying the start of the table of contents.  The 32 prior bytes are the md5 checksum.  
        """
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
        if self.outdir is  None:
            self.rawdir = toc['rawdir']
        else:
            self.rawdir = self.outdir

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
        If present, write the prescription read from review.out to both a yaml file.
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
        """
        Decompress and create a dicom object to verify that data are in a valid dicom format.
        """
        try:
            udata = bz2.decompress(data)
        except AttributeError():
            errstr = \
                '\n****** Error decompressing data for %s ******\n\n' % odir
            sys.stderr.write(errstr)
            sys.exit(1)
        try:
            dcm =  ScanDicomSlices(udata)
        except RuntimeError, errstr:
            sys.stderr.write('\n%s\n%s\n' % (errstr, except_msg()))

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
                self.CreateDir(fulldir, linkdir=linkdir, group=self.group)

            if 'cardiac' not in odir and 'raw' not in odir:
                self.nfiles_packed[odir] = self.toc['series_toc'][odir]['nfiles']
                if not self.nfiles_unpacked.has_key(odir):
                    self.nfiles_unpacked[odir] = 0

#               Write yaml and pickle versions of header. The yaml version
#               is human-readable but the pickle version is shorter and can
#               be read faster.
                if isinstance(self.toc[odir], dict):
#                   Skip non-dicom directories such as cardiac.
                    prefix = ('%s/%s.yaml' % \
                                    (outdir_list[odir], odir)).replace(' ','')
                    f1 = open(prefix, 'w')
                    f1.write(yaml_magic_code)
                    f1.write(self.toc[odir]['hdr'])
                    f1.close()

#                   Now write the pickled version. 
                    hdr = yaml.load(self.toc[odir]['hdr'])
                    f = open(prefix.replace('.yaml', '.pickle'), 'w')
                    pickler = cPickle.Pickler(f)
                    pickler.dump(hdr)
                    f.close()
#                    write_yaml(prefix, self.toc[odir]['hdr'])
            else:
                self.found_cardiac = True

    def Unpack(self):
        """ Unpack data from the entire data file."""

#       Write prescription info to log file.
##        self.WritePrescription()
        toc_keys = self.toc['keylist']
        slice_toc = self.toc['slice_toc']
        self.nfiles_unpacked = {}
        self.nfiles_packed = {}

#       Create output directories.
        self.UnpackDirs(toc_keys)

#       Unpack the dicoms
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
            if self.no_dicomtars:
                self.UnpackDicom(entry, odir, self.toc['series_toc'][odir]['nfiles'])
            else:
                self.UnpackTarDicom(entry, odir, self.toc['series_toc'][odir]['nfiles'])
            self.nfiles_unpacked[odir] += 1

        if 'cardiac' in toc_keys:
#           Unpack cardiac data last.
            self.UnpackOther('cardiac', self.toc['cardiac'])
        os.close(self.fd)

        if  not self.no_dicomtars:
#           Compare checksums for tar files.
            self.CheckTarValidity()

#       Check for correct number of files.
        keys = self.nfiles_packed.keys()
        keys.sort()
        for key in keys:
            if self.nfiles_unpacked[odir] != self.nfiles_packed[odir]\
                and 'localizer' not in odir:
                errstr = '\n*** Error during upload ***\n*** Only %d files out of %d files were found ***\n' % (self.nfiles_unpacked, self.nfiles_packed)
                sys.stderr.write(errstr)

    def UnpackDicom(self, toc_entry, odir, nfiles):
        """
        Unpack a single file.
        """
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

    def UnpackTarDicom(self, toc_entry, odir, nfiles):
        """
        Unpack a single member in a dicom tar object.
        """
#       A single series can be stored in multiple directories 
#       on the scanner. The table of contents has one entry per
#       scanner directory per series. (more than one series might
#       be stored in a single scanner directory.
        fname = ('%s/dicoms/%s' % (self.rawdir, \
                                       toc_entry[3])).replace(' ','')
        if 'screensave' in fname:
#           Screenshot in jpeg format, convert to jpeg.
            f1 = open(fname, 'w')
            f1.write(data)
            f1.close()
            self.ConvertToJpeg(fname)
        else:
#           Regular dicom file, tar them.
            dname = os.path.dirname(toc_entry[3])
            fname = os.path.basename(toc_entry[3])
            if self.tarfiles.has_key(dname):
                tar = self.tarfiles[dname][0]
                tarname = self.tarfiles[dname][1]
                md5sum = self.tarfiles[dname][2]
            else:
                tarname = '%s/dicoms/%s/%s.tar' % \
                                    (self.rawdir, dname, dname)
                tar = tarfile.open(tarname, 'w')
                md5sum = hashlib.md5()
                self.tarfiles[dname] = (tar, tarname, md5sum)

#           Retrieve the data.
            data, lgth = self.ReadSlice(toc_entry)
            md5sum.update(data)

#           Create a sting buffer from the data.
            sio = StringIO(data)
            t = TarInfo(fname) # Create a tar entry
            t.type = REGTYPE
            t.mode = 0664
            t.size = len(data)
            t.gid = self.gid
            t.uid =  self.uid
            t.uname = self.uname
            t.gname = self.gname
            t.mtime = self.mtime
            tar.addfile(t, fileobj=sio)
            sio.close()

    def CheckTarValidity(self):
        """
        Check the md5 checksum for the tarfile containing the pulse-ox and respriatory data.
        """
        keys =  self.tarfiles.keys()
        keys.sort()
        errmsg = ''
        okmsg = ''
        for key in  keys:
            tar, tarname, md5sum = self.tarfiles[key]
            tar.close()
            if 'linux' in sys.platform:
                cmd = 'tar xfO %s |  md5sum'  %  tarname
            else:
                cmd = 'tar xfO %s |  md5'  %  tarname
            output, errs = self.ExecCmd(cmd)
            md5_tar = output.strip().split()[0]
            md5_data = md5sum.hexdigest()
            msg = '\nSeries %s:\n' % tarname + \
                  '__%s__ computed from tarfile\n' % md5_tar + \
                  '__%s__ computed from input data\n' % md5_data
            if md5_tar != md5_data:
                errmsg += msg
                self.data_ok = False
            else:
                okmsg += msg

        if len(errmsg) > 0:
            subject = '\tError while uploading data to %s'%self.rawdir
            errmsg = "\tChecksum error during data unpacking" + errmsg
            sys.stderr.write('\n%s\n%s\n' % (subject, errmsg))
            self.EmailErrorMessage(subject, errmsg)
            return False
        else:
            print '\n\tChecksums verified for dicom to tar step'#+okmsg
        return True

    def EmailErrorMessage(self, subject, mesg):
        for recipient in RECIPIENTS:
            sender = 'unpack_data'
            send_email(recipient, subject, mesg, sender)

    def ReadSlice(self, toc_entry):
        """
        Read a single slice from the uploaded data file.
        """
        lgth = toc_entry[1] - toc_entry[0]
        if self.fd_ptr != toc_entry[0]:
#           Noncontiguous location, seek to the right position
            self.fd_ptr = toc_entry[0]
            os.lseek(self.fd, self.fd_ptr, 0)
        data = os.read(self.fd, lgth)
        self.fd_ptr += lgth
        if lgth != len(data):
            raise IOError('Failure reading %s, tried ' % fname + \
            'to read %d bytes, got %d bytes' % (lgth, len(data)))
        self.md5.update(data)
        return data, lgth

    def UnpackOther(self, odir, (position, lgth)):
        """
        Unpack tarfile object containing miscellaneous data.
        """
        sys.stdout.write('Unpacking %s\n' % odir)
        sys.stdout.flush()
        os.lseek(self.fd, position, 0)
        data = os.read(self.fd, lgth)
        self.md5.update(data)

#       Extract the files.
        sio = StringIO(data)
        tarfile = TarFile(odir, 'r', sio)
        fnames = tarfile.getnames()
        tarfile.extractall(self.rawdir)
        tarfile.close()
        sio.close()

#       Change permissions.
        for fname in fnames:
            path = '%s/%s' % (self.rawdir, fname)
            if os.path.isdir(path):
                os.chmod(path, 0775)
            else:
                os.chmod(path, 0664)
        if self.linkdir is not None:
            self.CreateLink('%s/%s' % (self.rawdir, odir), \
                            '%s/%s' % (self.linkdir, odir), self.group)

    def CheckMd5(self):
        """
        Verify that the md5 checksum computed during unpacking matches the md5 computed during upload.  Print an error message and set the exit status to one if they don't match.
        """
        self.md5.update(self.toc_serialized)
        self.md5.update(self.start_toc_str)
        new_md5 = self.md5.hexdigest()
        if new_md5 != self.scanner_md5:
            sys.stderr.write( \
            '\n\t*** Checksum error on scanner to %s transfer ***\n' \
                                                    % self.hostname)
            sys.stderr.write( \
            '\t\tChecksum on scanner:   \t%s\n' % self.scanner_md5)
            sys.stderr.write( \
            '\t\tChecksum after upload: \t%s\n\n' % new_md5)
            sys.exit(1)
        elif self.data_ok:
            sys.stdout.write(
            '\n\tChecksum verified for scanner to %s transfer:\n' % \
                                                    self.hostname)
            ns = len('scanner')
            if len(self.hostname) > ns:
                hname = self.hostname + ':'
                scanner = 'scanner:' + ' '*(len(hname) - ns)
            else:
                scanner = 'scanner'
                hname = self.hostname + ':' + ' '*(ns - len(self.hostname))
            sys.stdout.write('\t\tChecksum on %s %s\n' % (scanner, self.scanner_md5))
            sys.stdout.write('\t\tChecksum on %s %s\n' % (hname, new_md5))
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
        msg = '\nError unpacking data: %s\n%s\n\n'%(err, except_msg())
        sys.stderr.write(msg)
        subject = 'Error unpacking data for %s' % u.rawdir
        u.EmailErrorMessage(subject, msg)
    except (KeyboardInterrupt, SystemExit):
        pass
    except:
        msg = '\n%s\n' % except_msg()
        sys.stderr.write(msg)
        subject = 'Error unpacking data for %s' % u.rawdir
        u.EmailErrorMessage(subject, msg)
    sys.stderr.write('\n')

if __name__ == '__main__':
    unpack()
