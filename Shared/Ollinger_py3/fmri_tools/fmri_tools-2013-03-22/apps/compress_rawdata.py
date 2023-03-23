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
from file_io import Header, file_type, exec_cmd
from wbl_util import except_msg, GetTmpSpace
from optparse import OptionParser

ID = "$Id: compress_rawdata.py 352 2010-10-07 18:27:46Z jmo $"[1:-1]

#ROOT_UID = 1184
MRI_UID = 202
MRI_GID = 1000
SINGLE_FILE = 0
MANY_FILES = 1
raw_filetypes = {\
                'ge_data': SINGLE_FILE, \
                'ge_ifile': MANY_FILES, \
                'dicom': MANY_FILES}

MAX_FILESIZE = 3000 #MB

class CompressRawdata():

    def __init__(self):
        self.ParseOptions()
        self.compress_fcn = {SINGLE_FILE: self.CompressFile, \
                             MANY_FILES: self.CompressDir}

        os.umask(0133) # Ensure group write access.
#        self.access_mode = 0644
#        os.setuid(self.uid)

#       Find tmp space.
#        self.tmpdir = GetTmpSpace(MAX_FILESIZE)()
#        self.tmpfile = '%s/compress_rawdata.tmp' % self.tmpdir

    def ParseOptions(self):
        usage = 'compress_rawdata <options> <top-directory>\n' + \
                '\tEnter --help for more information.\n\n'
        optparser = OptionParser(usage)

        optparser.add_option( "", "--nossh", action="store_true", \
                    dest="nossh",default=False, \
                    help="Don't use ssh to create yaml files.")
        optparser.add_option( "", "--uid", action="store", \
                    dest="uid",default=None, type='int', \
                    help="User will own compressed files.")
        optparser.add_option( "", "--gid", action="store", \
                    dest="gid",default=None, type='int', \
                    help="Group ID of compressed files.")
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

        self.topdir = args[0]
        self.nossh = self.opts.nossh
        if self.opts.uid:
            self.uid = self.opts.uid
        elif os.getuid() == 0:
            self.uid = MRI_UID
        else:
            self.uid = os.getuid()
            self.uid = MRI_UID
        if self.opts.gid:
            self.gid = self.opts.gid
        else:
            self.gid = MRI_GID

    def FindFiles(self):
        for dirpath, dnames, fnames in os.walk(self.topdir):
            self.dirpath = os.path.abspath(dirpath)
            for fname in fnames:
                if fname.endswith('.bz2'):
                    continue
                if fname == 'DICOMDIR':
                    continue
                fullname = '%s/%s' % (self.dirpath, fname)
                if os.path.islink(fullname):
                    continue
                self.ftype = file_type(fullname)
                if raw_filetypes.has_key(self.ftype):
                    apply(self.compress_fcn[raw_filetypes[self.ftype]], \
                          [fullname])
                else:
                    continue
                if raw_filetypes.get(self.ftype, None) == MANY_FILES:
                    break

    def CompressFile(self, fullname):
#        print 'Compressing file: %s' % fullname
        if fullname.endswith('.bz2') or fullname.endswith('.gz'):
            return
        st1 = os.stat(fullname)
        try:
#           Compress but keep original
            cmd = 'bzip2 -k %s' % fullname 
            if self.uid == 0:
                self.ExecRootCmd(cmd, '%s.bz2' % fullname)
            else:
                self.ExecCmd(cmd, '%s.bz2' % fullname)

            st2 = os.stat('%s.bz2' % fullname)
            if st1.st_mtime == st2.st_mtime:
#               Original hasn't been modified, so remove it
                os.remove(fullname)
        except KeyboardInterrupt:
            self.CleanUp()
            sys.exit(1)
        except OSError:
            sys.stderr.write( \
            '\n*** Error compressing %s with command: \n%s***\n\n%s\n' % \
                            (fullname, cmd, except_msg()))
            return

    def ChangeDirPerms(self, dname):
        #cmd = 'su - -c "chown mri %s; chgrp dusers %s; chmod 0755 %s"' % \
        cmd = 'chown mri %s; chgrp dusers %s; chmod 0755 %s' % \
                                                    (dname, dname, dname)
        try:
            self.ExecCmd(cmd)
        except KeyboardInterrupt:
            self.CleanUp()
            sys.exit(1)
        except OSError, err:
            sys.stderr.write('\n%s\n%s\n' % (err, except_msg()))

    def ExecCmd(self, cmd):
        print cmd
        errmesg = 'Error executing cmd: %s' % cmd
        try:
            status = exec_cmd(cmd)
            if status:
                raise OSError(errmesg)
        except KeyboardInterrupt:
            self.CleanUp()
            sys.exit(1)
        except:
            raise OSError(errmesg)

    def ExecRootCmd(self, command, fname):
#        cmd = 'su - -c "chown mri %s; chgrp dusers %s;"' % (fname, fname)
#        self.ExecCmd(cmd)
#        'su - -c "%s; chown mri %s; chgrp dusers %s; chmod 0664 %s;"' % \
        cmd = \
        '%s; chown mri %s; chgrp dusers %s; chmod 0664 %s;' % \
                                            (command, fname, fname, fname)
        self.ExecCmd(cmd)
            

    def CompressDir(self, fullname):
        print 'Compressing directory: %s' % self.dirpath
        try:
#           First read the header. This takes forever on compressed files.
            if self.ftype == 'ge_ifile' and 'sunos' in sys.platform:
                self.WriteYamlRemote(self.dirpath)
            elif self.ftype == 'dicom' or self.ftype == 'ge_ifile':
                try:
                    hd = Header(fullname, scan=True)
                except KeyboardInterrupt:
                    self.CleanUp()
                    sys.exit(1)
                except:
                    sys.stderr.write('*** Error reading header from %s ***\n' \
                                                                % fullname)
                    hd = None
                try:
                    if self.ftype == 'dicom' and hd:
#                       Write the header in ASCII.
                        yaml_file = '%s/%s.yaml' % \
                                (self.dirpath,os.path.basename(self.dirpath))
                        hd.write_hdr_to_yaml('%s/%s.yaml' % \
                                (self.dirpath,os.path.basename(self.dirpath)))
                except KeyboardInterrupt:
                    self.CleanUp()
                    sys.exit(1)
                except:
                    sys.stderr.write('Error writing file to %s\n' % yaml_file)
                    return
#               Now we can compress each file.
            try:
                for fname in os.listdir(self.dirpath):
                    ftype = file_type('%s/%s' % (self.dirpath, fname))
                    if raw_filetypes.has_key(ftype):
                        self.CompressFile('%s/%s' % (self.dirpath, fname))
            except KeyboardInterrupt:
                self.CleanUp()
                sys.exit(1)
            except RuntimeError, err:
                sys.stderr.write(err.errmsg + '\n')
                print '\ncompress_rawdata is continuing.\n\n'
            except OSError, err:
                sys.stderr.write('\n%s\n%s\n' % (err, except_msg()))
        except KeyboardInterrupt:
            self.CleanUp()
            sys.exit(1)
        except OSError, err:
            sys.stderr.write('\n%s\n%s\n' % (err, except_msg()))
        except:
#           Ignore directories that can't be read with standard software.
            print except_msg()
#            self.CleanUp()
#            sys.exit()
            pass

    def WriteYamlRemote(self, dirpath):
        if self.nossh:
            return
        cmd = 'ssh pasilla write_yaml_header %s' % dirpath
        fname = '%s/%s.yaml' % (dirpath, dirpath)
        try:
            if self.uid == 0:
                self.ExecRootCmd(cmd, fname)
            else:
                self.ExecCmd(cmd)
        except KeyboardInterrupt:
            self.CleanUp()
            sys.exit(1)
        except OSError, errmesg:
            sys.stderr.write('\n%s\n%s\n' % (errmesg, except_msg()))

    def CleanUp(self):
#        cmd = "/bin/rm -r %s" % self.tmpdir
#        os.system(cmd)
        pass

def compress_rawdata():
    cr = CompressRawdata()
    cr.FindFiles()
    cr.CleanUp()

if __name__ == '__main__':
    compress_rawdata()
