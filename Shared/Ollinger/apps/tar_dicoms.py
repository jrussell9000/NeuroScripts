#!/usr/bin/env python

import sys
import os
from file_io import Wimage
from subprocess import Popen, PIPE
import tarfile
from dicom import DicomTar
from wimage_lib import except_msg
import bz2
from optparse import OptionParser
from hashlib import md5

class TarDicoms():

    def __init__(self):
        self.ParseOptions()
        try:
            self.flog = open(self.logfile, 'w')
        except IOError, errmsg:
            sys.stderr.write('\nCould not open logfile: %s\n' % self.logfile)
            sys.exit(1)

    def ParseOptions(self):
        usage = 'tar_dicoms [options] <top-directory>'
        optparser = OptionParser(usage)
        optparser.add_option( "-v", "--verbose", action="store_true",  \
            dest="verbose",default=None, help="Verbose mode.")
        optparser.add_option( "", "--tar-threshold", action="store",  \
            type='int', dest="tar_thresh",default=150, \
            help='Minimum number of files that will be converted.')
        optparser.add_option( "", "--logfile", action="store",  \
            type='str', dest="logfile",default='/tmp/tar_dicoms.log', \
            help='Name of logfile.')
        opts, args = optparser.parse_args()

        if len(args) != 1:
            sys.stderr.write('Usage: %s\n' % usage)
            sys.exit(0)

        self.topdir = os.path.realpath(args[0])
        self.verbose = opts.verbose
        self.tar_thresh = opts.tar_thresh
        self.logfile = opts.logfile

    def Verify(self, dname, tarname):
        """
        Verify tar archive by computing a combined checksum for the original
        files and comparing it to the combined checksum for those in the tar
        archive.
        """
        if self.verbose:
            print 'Verifying %s' % dname
        dt = DicomTar(tarname)
        if not dt.isTar:
            return False
        fnames = dt.GetNames()
        for fname in fnames:
            fullfile = '%s/%s' % (dname, fname)
            md5_orig = md5()
            try:
                f = open(fullfile,'r')
                if fullfile.endswith('.bz2'):
                    md5_orig.update(bz2.decompress(f.read()))
                else:
                    md5_orig.update(f.read())
                f.close()
            except IOError, errmsg:
                sys.stderr.write('\n%s\n%s\n%s\n' % \
                                        (errmsg, fullfile, except_msg()))
                sys.exit(1)

            md5_tar = md5()
            md5_tar.update(dt.GetSlice(fname))

            if md5_orig.digest() !=  md5_tar.digest():
                errstr = ("md5 digests don't match for %s:\n" % tarname + \
                          'Original: %s\n' % md5_orig.hexdigest() + \
                          'Tarfile:  %s\n' % md5_tar.hexdigest())
                raise RuntimeError(errstr)
        dt.Close()
        self.Log(' Verified %s\n' % dname)
        return True

    def GetNfiles(self, dicom_dir):
        cmd = 'cd %s && ls *.[0-9][0-9][0-9][0-9]* | wc' %  dicom_dir
        output, errs = self.ExecCmd(cmd)
        if 'too long' in errs:
            nfiles = 100000
        else:
            nfiles = int(output.split()[0])
        return nfiles

    def CreateTar(self, dicom_dir, tarname):
        cmd = 'cd %s && ls | grep \.[0-9][0-9][0-9][0-9]* > tmp.tmp' % dicom_dir
        self.ExecCmd(cmd)
        cmd = 'cd %s && tar cf %s  -T tmp.tmp' %  \
                                (dicom_dir, os.path.basename(tarname))
        self.ExecCmd(cmd)
        if self.verbose:
            print 'Creating tar file for %s' % (os.path.abspath(dicom_dir))
        cmd = '/bin/rm %s/tmp.tmp' % dicom_dir
        self.ExecCmd(cmd)

    def DeleteFiles(self, dicom_dir, nfiles):
        N = nfiles
        self.Log('Cleanin\g %s ...\n' % dicom_dir)
        n = 1
        while N > 10000:
#           Can't exceed number of files rm can handle.
            cmd = 'cd %s && /bin/rm *.%d[0-9][0-9][0-9][0-9]*' %  (dicom_dir,n)
            self.ExecCmd(cmd)
            N = self.GetNfiles(dicom_dir)
            n += 1
        cmd = 'cd %s && /bin/rm *.[0-9][0-9][0-9][0-9]*' %  dicom_dir
        self.ExecCmd(cmd)

    def CompressFiles(self):
        """
        Top level processing function.  Walks through directories finding
        those named "dicom" or "anatomical, and then processing them.
        """
        for root, dnames, fnames in os.walk(self.topdir, topdown=True):
            subdir = os.path.basename(root)
#            print 10,subdir
            if subdir == 'anatomicals' or subdir == 'dicoms':
                for dname in dnames:
                    dicom_dir = '%s/%s' % (root, dname)
#                    print 11,dicom_dir
                    if not os.path.islink(dicom_dir):
                        self.ProcessDir(dicom_dir)
                    elif self.verbose:
                        print 'Skipping link : %s' % dicom_dir

    def ProcessDir(self, dicom_dir):
        """
        Create tar file, verify contents, and delete individual dicoms.
        """

        tarname = '%s/%s.tar' % (dicom_dir, os.path.basename(dicom_dir))

        nfiles = self.GetNfiles(dicom_dir)
        if nfiles < self.tar_thresh:
#           Skip small directories
            msg = 'Skipping %s, %d files\n' % (os.path.abspath(dicom_dir), nfiles)
            self.Log(msg)
            return
        if self.verbose:
            print 'Processing %s' % dicom_dir

#       Make the tarfile.
        self.CreateTar(dicom_dir, tarname)

#       Check it.
        if self.Verify(dicom_dir, tarname):

#           It verifies.  Remove individual dicom files.
            self.DeleteFiles(dicom_dir, nfiles)
#        sys.exit()

    def ExecCmd(self, cmd):
#        if self.verbose:
#            print cmd
        try:
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            output, errs = p.communicate()
            if errs:
#                print 10,cmd, output,'\n', errs
                if ' | wc' in cmd and output.split()[0] == '0':
#                   wc generates an error if there is nothing to count.
                    return output, errs
                raise OSError('Command output: \n%s\n%s\n' % (output, errs))
        except OSError, errmsg:
            raise RuntimeError('Error while executing command: \n%s' % cmd)
        return output, errs

    def Log(self, msg):
        if self.logfile is not None:
            self.flog.write(msg)
        if self.verbose:
            sys.stdout.write(msg)

if __name__ == '__main__':

    try:
        td = TarDicoms()
    except IOError:
        sys.stderr.write('\n%s\n' % except_msg())
        sys.exit(1)
    try:
        td.CompressFiles()
    except RuntimeError, errstr:
        msg = '\n%s\n%s\n' % (errstr, except_msg())
        sys.stderr.write(msg)
        td.Log(msg)
    except SystemExit:
        pass
    except:
        sys.stderr.write('\n%s\n' % except_msg())
        msg = '\n%s\n' % except_msg()
        sys.stderr.write(msg)
        td.Log(msg)
        sys.exit(1)
