#!/usr/bin/env python

ID = "$Id: convert_file.py 572 2011-06-20 23:12:43Z jmo $"[1:-1]

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
import os
from os import F_OK, W_OK, R_OK

from numpy import zeros, identity, prod, dot, identity, array, reshape, \
                  fliplr, flipud, int32

from file_io import Wimage, make_to3d_cmd, modify_HEAD, write_nifti_header, \
                     write_analyze_header, modify_nifti_auxfile, writefile
from wbl_util import except_msg, execCmd, GetTmpSpace

from optparse import OptionParser
import traceback
from subprocess import Popen, PIPE

ID = "$Id: convert_file.py 572 2011-06-20 23:12:43Z jmo $"[1:-1]


iext = {'brik':'.tmp','ni1':'.img','ana':'.img','n+1':'.nii','tes':'.tes', \
        'ana2d':'.img', 'nii':'.nii'}
hext = {'brik':'.tmp','ni1':'.hdr','ana':'.hdr','n+1':'.nii','tes':'.tes', \
        'ana2d':'.hdr', 'nii':'.nii'}
datatype_to_afni_datum = {'bit':'byte','byte':'byte','short':'short', \
        'integer':'float', 'float32':'float','float':'float', \
        'complex':'complex','double':'float','int':'float'}
datatype_to_analyze_datum = {'bit':'byte','byte':'byte','short':'short', \
        'integer':'integer', 'float32':'float','float':'float32', \
        'complex':'complex','double':'double','int':'integer'}
dtypes = {'byte': 'byte', 'short':'short', 'int':'int', 'float':'float32', \
          'integer':'int', 'float32':'float32'}

threedcopy_ext = {'nii':'.nii', \
                  'ana':'.hdr', \
                  'n+1':'.nii', \
                  'ni1':'.img', \
                  'brik':'+orig'}

threedcopy_types = ['brik', 'nii', 'ni1', 'ana', 'n+1']

#'HEAD':'BRIK', 'orig', 'tlrc', 'hdr':'img', 'nii', 'ni1' 'n+1'


class ConvertFile():

    def __init__(self):
        self.tmp = None

    def ProcessCommandLine(self):
        self.ParseArgs()
        self.input_file = os.path.abspath(self.args[0])
        self.outfile = os.path.abspath(self.args[1])
        self.output_format = self.args[2]

#       Check for existing output file.
        if self.outfile.endswith('+orig'):
            checkfiles = ['%s.BRIK' % self.outfile, \
                         '%s.HEAD' % self.outfile]
        elif self.outfile.endswith('.HEAD'):
            checkfiles = ['%s.BRIK' % self.outfile[:-5], self.outfile]
        elif self.outfile.endswith('.BRIK'):
            checkfiles = ['%s.HEAD' % self.outfile[:-5], self.outfile]
        else:
            checkfiles = [self.outfile]
#        if self.outfile.endswith('tlrc'):
#            sys.stderr.write(\
#            '\nconvert_file: Cannot convert to <name>+tlrc.BRIK. ' + \
#            'Use 3dcopy instead.\n\n')
#            sys.exit(1)
#        else:
        for checkfile in checkfiles:
            if os.access(self.outfile, R_OK) and self.opts.warn:
                sys.stderr.write(\
                '\nconvert_file: ... File exists: %s, aborting ...\n\n')
                sys.exit(-1)
        self.outfile = self.outfile.replace('BRIK','')
        self.outfile = self.outfile.replace('HEAD','')
        self.outfile = self.outfile.replace('+orig','')
        self.outfile = self.outfile.replace('.nii','')

#       Check for output write access.
        self.dirname = os.path.abspath(os.path.dirname(self.outfile))
        if len(self.dirname) > 0:
#           Handle case where directory name contains a dot (an fsl feature)
            filestem = os.path.splitext(self.outfile[len(self.dirname):])[0]
            if filestem.startswith('/'):
                filestem = filestem[1:]
            self.filestem = "%s/%s" % (self.dirname,filestem)
        else:
            self.dirname = '.'
            self.filestem = self.outfile

        if not os.access(self.dirname, W_OK):
            sys.stderr.write(\
            "convert_file: No write access to output directory: %s\n" % self.dirname)
            sys.exit(-1)


    def ParseArgs(self):
        u1 =  "convert_file [options] <input_file> <output_file> " + \
              "<file_format>\n\nPurpose: Convert file formats and flip images\n"
        u2 =  "   <input_file>: The input data to be converted.\n" + \
              "   <output_file>: The output file name (without the extension.)\n" + \
              "   <file_format>: Output file format. It takes on values of" + \
              "'ana', 'ni1', 'n+1', or 'brik'\n"
        u9 =  "      ana: 4d analyze format. One file per frame in " + \
              "the input file\n"
        u11 = "      ni1: two-file nifti format (will convert 4D nifti containing Nframes to N 3D nifti files.)\n"
        u12 = "      nii or n+1: one-file nifti format\n"
        u13 = "      brik: afni format.\n\n"
        u14 = "Note: Dicom, and GE I-files are specified by\n"
        u15 = "      the directory they reside in rather than by a filename.\n\n"
        u16 = "\nExamples: convert_file T1High+orig T1High nii\n" + \
              "             convert_file S2_2DFAST fmap_data brik\n" + \
              "             convert_file -MS3_EPI epi.img epi n+1 " + \
              "   (Converts an analyze format\n" + \
              "             image to nifti format with the image " + \
              "   coordinates of S3_EPI) \n" + \
             '\n\nNote: convert_file only converts to brik files of " + \
                 "type "orig", i.e., <file_stem>+orig.BRIK\n' + \
                 '          Use 3dcopy to convert to type "tlrc"'
        
        usage = u1 + u2 + u9 + u11 + u12 + u13 + u14 + u15 + u16
        optparser = OptionParser(usage)
        
        optparser.add_option( "-v", "--verbose", action="store_true", \
                    dest="verbose",default=False, \
                    help='Print useless stuff to screen.')
        optparser.add_option( "-V", "--version", action="store_true",  \
                dest="show_version",default=None, help="Display svn version.")
        optparser.add_option( "-w", "--warn_no_overwrite", action="store_true", \
                    dest="warn",default=False, \
                    help='Do not overwrite existing files.  ' + \
                    'Print a warning to the screen.')
        optparser.add_option( "-t", "--flip_tb", action="store_true", \
                    dest="flipud",default=False, \
                    help='Flip top-to-bottom. (Does not affect " + \
                    coordinate system descriptor)')
        optparser.add_option( "-l", "--flip_lr", action="store_true", \
                    dest="fliplr",default=False, \
                    help='Flip left-to-right. (Does not affect " + \
                    coordinate system descriptor)')
        optparser.add_option( "-T", "--flip_TB", action="store_true", \
                    dest="flipUD",default=False, \
                    help='Flip top-to-bottom. (Also changes " + \
                    coordinate system descriptor, i.e., quaternion or ' + \
                    'transform matrix.)')
        optparser.add_option( "-L", "--flip_LR", action="store_true", \
                    dest="flipLR",default=False, \
                    help='Flip left-to-right. (Also changes " + \
                    coordinate system descriptor, i.e., quaternion or ' + \
                    'transform matrix.)')
        optparser.add_option( "-M", "--master", action="store", dest="master", \
                    type="string",default=None,\
                    help='Master in the same coordinate system as ' + \
                    'the image to be converted (its parameters will be ' + \
                    'copied as used. Useful if input image has not ' + \
                    'positional info).' )
        optparser.add_option( "-f", "--frame", action="store", dest="frame", \
                    type="string",default=None,\
                    help='Specifies that the single frame specified be ' + \
                    'converted. This option ' + \
                    'takes two forms. If -f "i-j" is entered, frames i ' + \
                    'to j inclusive will be converted.  ' + \
                    'If "-f i" is entered, only ' + \
                    'frame "i" will be converted.  Frames are numbered ' + \
                    'starting at zero.')
        optparser.add_option( "-m", "--mtype", action="store", dest="mtype", \
                    type="string",default=None,\
                    help='Specifies that only one image along the "mtype" ' + \
                    'dimension be converted.  The "type" dimension is ' + \
                    'most often encountered with fieldmap data, where ' + \
                    'magnitude, phase, real, and imaginary images ' + \
                    'are stored in the fifth dimension of the image. ' + \
                    'This option selects on of those images. Although ' + \
                    'the ordering depends on the type of image, types ' + \
                    'are usually stored as 0=magnitude, 1=phase, 2=real ' + \
                    'and 3=imaginary. The syntax is the same as for the ' + \
                    '-f, option.')
        optparser.add_option( "-s", "--skip", action="store", dest="skip", \
                    type="int",default=0,\
                    help="Number of frames to skip.")
        optparser.add_option( "-d", "--dtype", action="store", dest="dtype", \
                    type="string",default=None,\
                    help='Data-type written to disk.  Valid arguments ' + \
                    'are: "' + ''.join(datatype_to_afni_datum.keys()) + '" ' + \
                    'Data-types will be mapped to the shortest data-type ' + \
                    'supported by the requested file format that will ' + \
                    'not truncate or round the data.  For example, the ' + \
                    'int data-type would ordinarily refer to a 32-bit ' + \
                    'integer.  For formats such as afni that do not ' + \
                    'support 32-bit integers, the data will be saved ' + \
                    'as 32-bit floats')
        
        self.opts, self.args = optparser.parse_args()

        if self.opts.show_version:
            sys.stdout.write('%s\n' % ID) 
            sys.exit()
        self.verbose = self.opts.verbose
        
        if len(self.args) != 3:
            errstr = "\nExpecting 3 arguments:\n" + \
                               "Enter 'convert_file --help' for usage.\n\n"
            sys.stderr.write(errstr)
            sys.exit(1)

    def SplitFile(self, input_name):
        if input_name.endswith('.gz'):
            fname = input_name[:-3]
            compress = '.gz'
        else:
            fname = input_name
            compress = ''
        tmp = fname.split('+')
        if len(tmp) == 2:
            base = tmp[0]
            ext = tmp.split('.')[0]
        else:
            tmp = fname.split('.')
            if len(tmp) > 1 and tmp[-1] in threedcopy_types:
                ext = tmp[-1]
                base = fname[:-len(ext)-1]
            else:
                ext = ''
                base = fname
        return base, ext, compress

    def CleanOld(self, fname):
        fnames = []
        if fname.endswith('+orig') or fname.endswith('+tlrc'):
            fnames.append(fname + '.HEAD')
            fnames.append(fname + '.BRIK')
        elif fname.endswith('.hdr'):
            fnames.append(fname)
            fnames.append(fname[:-4] + '.img')
        elif fname.endswith('.img'):
            fnames.append(fname)
            fnames.append(fname[:-4] + '.hdr')
        else:
            fnames.append(fname)
        for fname in fnames:
            p = Popen('/bin/rm %s' % fname, shell=True)
            sts = os.waitpid(p.pid, 0)

    def Use3dcopy(self):
        instem, inext, incmprss = self.SplitFile(self.input_file)
        outstem, outext, outcmprss = self.SplitFile(self.outfile)
        if self.output_format == 'brik' and ('+tlrc' in inext or '+tlrc' in outext):
            output_ext = '+tlrc'
        else:
            output_ext = threedcopy_ext[self.output_format]

        outfile = '%s%s%s' % (outstem, output_ext, outcmprss)
        self.CleanOld(outfile)
        cmd = '3dcopy %s %s' % (self.input_file, outfile)
        if self.opts.verbose:
            print 'Executing %s' % cmd
        else:
            cmd = '%s >& /dev/null' % cmd
        p = Popen(cmd, shell=True)
        sts = os.waitpid(p.pid, 0)
        if sts[1] != 0:
            raise RuntimeError('Error executing cmd: %s' % cmd)
        sys.exit(0)

    def Initialize(self):
        """ 
        Read header and initialize data structures.
        """

#       Read input header. Scan image files if Dicom.
        self.imgin = Wimage(self.input_file, scan=True)
        if self.imgin.hdr is None:
            raise RuntimeError('Error while reading %s\n' % self.input_file)
         
        if self.imgin.hdr is None:
            if self.opts.master is not None:
                self.imgin = Wimage(self.opts.master, scan=True)
                if self.imgin.hdr is None:
                    raise RuntimeError('Error while reading %s\n' % self.input_file)
                self.imgin.hdr['filetype'] = 'unformatted'


        if self.imgin.hdr['filetype'] in threedcopy_types and \
            not self.opts.flipud and \
            not self.opts.fliplr and \
            not self.opts.flipUD and \
            not self.opts.flipLR and \
            not self.opts.master is None and \
            not self.opts.frame is None and \
            not self.opts.mtype is None and \
            not self.opts.dtype is None and \
            not self.opts.skip is None:
            self.Use3dcopy()

        if self.imgin.hdr['filetype'] == 'dicom' and \
           (not self.imgin.hdr['native_header'].has_key('DicomInfo') or \
            self.imgin.hdr['tdim'] != self.imgin.hdr['dims'][3]):
            self.imgin = Wimage(self.input_file, scan=True, ignore_yaml=True)

        self.hdrout = self.imgin.hdr.copy()
        max_required = (2*prod(self.hdrout['dims'])*4)/1e6 + 500
        self.tmp = GetTmpSpace(max_required)
        self.tmpdir = self.tmp()

#       Get output data type.
        self.datatype = dtypes.get(self.opts.dtype, None)

        if self.input_file.endswith('+orig'):
            checkfile = self.input_file + '.BRIK'
        elif self.input_file.endswith('.HEAD'):
            checkfile = self.input_file + '.BRIK.gz'
        if self.imgin.hdr['tdim'] > 2 and \
            os.access(self.input_file, R_OK) and self.input_file.endswith('.gz'):
#           This is a compressed, multi-frame file. It can be converted 
#           directly but it is extremely slow, so we will gunzip it on 
            self.Gunzip()

        if self.opts.skip > self.imgin.hdr['tdim']:
            raise RuntimeError(\
            'convert_file: Cannot skip %d frames in a file ' % self.opts.skip + \
            'containing %d frames' % (self.imgin.hdr['tdim']))

#       Determine frames to be converted.
        if self.opts.frame:
#           Frames to be converted were defined on the command line.
            if '-' in self.opts.frame:
                begend = self.opts.frame.split('-')
                self.frame_first = int(begend[0])
                self.frame_last = int(begend[1])
            else:
                self.frame_first = int(self.opts.frame)
                self.frame_last = int(self.opts.frame)
        else:
            self.frame_first = self.opts.skip
            self.frame_last = self.imgin.hdr['tdim'] - 1

        if self.opts.mtype:
            if '-' in self.opts.mtype:
                begend = self.opts.mtype.split('-')
                self.mtypes = range(int(begend[0]), int(begend[1])+1)
            else:
                m = int(self.opts.mtype)
                self.mtypes = range(m,m+1)
        else:
            self.mtypes = range(self.imgin.hdr['mdim'])
        self.mdim = len(self.mtypes)

#       Read and write the data frame by frame.
        self.frames = range(self.frame_first, self.frame_last+1)
        self.tdim = self.frame_last - self.frame_first + 1
        if self.output_format == 'brik' and \
            (self.imgin.hdr['filetype'] == 'ni1' or \
             self.imgin.hdr['filetype'] == 'nii' or \
             self.imgin.hdr['filetype'] == 'n+1')  and \
             self.imgin.hdr['datatype'] != 'float' and \
             self.imgin.hdr['scale_factor'] < 1.:
#           to3d will not correctly convert to short with the correct 
#           scale factor.  Write images as floats to be safe.
            dtype = dtypes['float']

#       Fix mistakes in header.
        if self.imgin.hdr['tdim'] == 0:
            self.imgin.hdr['tdim'] = 1
        if self.imgin.hdr['mdim'] == 0:
            self.imgin.hdr['mdim'] = 1
        self.Rin = self.imgin.hdr['R']

    def ProcessMaster(self,):
        """
        Read transformation matrix from master.
        """

        m = Wimage(self.opts.master,scan=True)
        if m.hdr is None:
            raise IOError(\
            "convert_file: Could not read header from master: %s" % \
            (self.opts.master))

#       Replace pertinent info in the output header.
        self.hdrout['x0'] = m.hdr['x0']
        self.hdrout['y0'] = m.hdr['y0']
        self.hdrout['z0'] = m.hdr['z0']
        self.hdrout['sizes'] = abs(m.hdr['sizes'])
        if m.hdr['filetype'] == 'dicom': 
#           Update tags hacked into the afni and nifti headers.
            if self.output_format == 'ni1' or self.output_format=='n+1' \
                                         or self.output_format == 'nii':
                modify_nifti_auxfile(m.hdr)
                self.hdrout['native_header']['aux_file'] =  \
                                m.hdr['native_header']['aux_file']
            elif output_format == 'brik':
                self.hdrout['native_header']['PEPolar'] =  \
                                m.hdr['native_header'].get('PEPolar','')
                self.hdrout['native_header']['EffEchoSpacing'] = \
                                m.hdr['native_header'].get('EffEchoSpacing','')
                self.hdrout['native_header']['PhaseEncDir'] =  \
                                m.hdr['native_header'].get('PhaseEncDir','')
        self.Rout = m.hdr['R']

    def SetupFlips(self):
        """
        Modify R matrix to reflect flip options.
        """
        Rflip = identity(3)
        if self.opts.flipLR:
            Rflip[0,0] = -1
        if self.opts.flipUD:
            Rflip[1,1] = -1
        if self.opts.flipUD or self.opts.flipLR:
#           Flip the transformation matrix as well as the image.
            self.Rout = identity(4)
            self.Rout[:3,:3] = dot(self.Rin[:3,:3], Rflip)
            sign = dot(self.Rout[:3,:3], self.Rin[:3,:3].transpose())
            which = (identity(3) - sign)/2.
            fovs = array([(self.imgin.hdr['xdim']-1.)*self.imgin.hdr['xsize'], \
                          (self.imgin.hdr['ydim']-1.)*self.imgin.hdr['ysize'], \
                          (self.imgin.hdr['zdim']-1.)*self.imgin.hdr['zsize']])
            self.Rout[:3,3] = self.Rin[:3,3] + \
                        (dot(-sign,dot(which,dot(self.Rin[:3,:3],fovs))))
        else:
            self.Rout = self.Rin.copy()

    def FlipImages(self, img):
        """
        Flip images physically.
        """
        if self.opts.fliplr or self.opts.flipud or \
           self.opts.flipLR or self.opts.flipUD:
#           Flip images
            img = reshape(img,[self.imgin.hdr['zdim'], \
                        self.imgin.hdr['ydim'], self.imgin.hdr['xdim']])
            jmg = zeros([self.imgin.hdr['zdim'], self.imgin.hdr['ydim'], \
                                                  self.imgin.hdr['xdim']],float)
            for z in range(self.imgin.hdr['zdim']):
                if self.opts.fliplr or self.opts.flipLR:
                    jmg[z,:,:] = fliplr(img[z,:,:])
                if self.opts.flipud or self.opts.flipUD:
                    jmg[z,:,:] = flipud(img[z,:,:])
            return jmg
        else:
            return img
 
    def GetOutfile(self):
        """
        Create output file name and get tmp directory.
        """
        self.hdrfile = self.filestem + hext[self.output_format]
        if self.output_format == 'brik':
#           Use /tmp for flat file, then use to3d to convert it.
            max_required = (2*prod(self.hdrout['dims'])*4)/1e6 + 500
            self.outfile = '%s/%s%s' % \
                    (self.tmpdir, os.path.basename(self.filestem), \
                            iext[self.output_format])
            self.hdrout['imgfile'] = '%s+orig' % self.filestem
        else:
            self.outfile = self.filestem + iext[self.output_format]
            self.hdrout['imgfile'] = self.outfile
            self.tmpdir = None

    def Gunzip(self):
        """Unzip gzipped input file. Save to tmp directory for speed."""
#       /tmp and then process it.
        print ' *** Unzip file before converting it.***'
        sys.exit()
        max_required = (2*prod(self.hdrout['dims'])*4)/1e6 + 500
        if self.tmpdir is None:
            self.tmp = GetTmpSpace(max_required)
            self.tmpdir = self.tmp()
        tmp_input_file = '%s/tmp_%s' % (self.tmpdir, os.path.basename(self.input_file[:-3]))
        cmd = 'gunzip --to-stdout %s > %s' % (self.input_file, tmp_input_file)
        try:
            os.system(cmd)
        except OSError, errstr:
            sys.stderr.write('Could not unzip file: %s\n' % self.input_file + \
                             except_msg(errstr)+'\n')
            sys.exit()
        self.imgin = Wimage(tmp_input_file)

    def WriteHeader(self):
#       Write the header.
        if self.output_format == 'n+1' or self.output_format == 'nii':
#           Leave room for nifti header.
            self.start_binary = 352
            self.f.seek(self.start_binary,0)  
        else:
            self.start_binary = 0

        self.afni_cmd = None
        if self.output_format == 'ana':
            self.hdrout['datatype'] = \
                datatype_to_analyze_datum.get(self.hdrout['datatype'], None)
            if self.hdrout['datatype'] is not None:
                write_analyze_header(self.hdrfile, self.hdrout)
            else:
                raise RuntimeError( \
                'convert_file: Invalid data-type specified. ' + \
                'Type convert_file --help for a list.\n')
                sys.exit()
        elif self.output_format == 'ni1' or \
             self.output_format == 'n+1' or \
             self.output_format == 'nii':
            write_nifti_header(self.hdrfile, self.hdrout)
        elif self.output_format == 'brik':
            self.afni_cmd, self.refit_cmd = make_to3d_cmd(self.outfile, \
                    os.path.basename(self.filestem), \
                    self.dirname, self.hdrout, self.datum_type)

    def WriteBrik(self):
#       Convert the tmp file to an afni brik.
        if os.access('%s+orig.HEAD' % self.filestem, W_OK):
            os.remove('%s+orig.HEAD' % self.filestem)
        if os.access('%s+orig.BRIK' % self.filestem, W_OK):
            os.remove('%s+orig.BRIK' % self.filestem)
        try:
            print self.afni_cmd
            execCmd(self.afni_cmd)
            if refit_cmd is not None:
                execCmd(refit_cmd)
        except:
#           Handle the seg fault that has always been in to3d.
            pass
        modify_HEAD(self.hdrout)
        if self.outfile.endswith('.tmp'):
            os.remove(self.outfile)
 
    def Convert(self):

        if self.imgin.hdr is None and self.opts.master is not None:
            try:
                self.imgin = Wimage(self.opts.master, scan=True)
            except RuntimeError, errmsg:
                sys.stderr.write('\n%s\n%s\n' % (errmsg, except_msg()))
                sys.exit(1)
            self.imgin.hdr['filetype'] = 'unformatted'
            f = open(input_file,'r')
            self.image = fromstring(f.read(),float32)
            f.close()
            try:
                image = reshape(image,imgin.hdr['dims'])
            except OSError:
                raise ValueError, \
                'convert_file: Image data is not compatible with ' % \
                ' the master file.\n'

        self.input_format = self.imgin.hdr['filetype']

#       Set data type in output header.
        if self.datatype is None:
            self.datum_type = self.imgin.hdr['datatype']
            if self.datum_type == 'float':
                self.datum_type = 'float32'
        else:
            self.datum_type = self.datatype

        if self.output_format == 'ni1':
            self.hdrout['dims'][3] = 1
            self.hdrout['dims'][4] = 1
        elif self.tdim == 1:
            self.hdrout['dims'][3] = self.tdim*self.mdim
            self.hdrout['dims'][4] = 1
        else:
            self.hdrout['dims'][3] = self.tdim
        self.hdrout['dims'][4] = self.mdim
        self.hdrout['swap'] = 0
        self.hdrout['filetype'] = self.output_format
        self.hdrout['datatype'] = self.datum_type
        self.hdrout['tdim'] = self.tdim
        self.hdrout['mdim'] = self.mdim
        self.hdrout['R'] = self.Rout

#       Make sure there won't be any precision loss.
        self.datum_type = self.hdrout['datatype']
        if self.output_format == 'brik':
            if (self.datum_type == 'short' or self.datum_type == 'byte') and \
                                       self.hdrout['scale_factor'] != 1.:
#               to3d can't handle scaled, integer data. 
                self.datum_type = 'float32'
                self.hdrout['scale_factor'] = 1.
                self.hdrout['datatype'] = 'float'

#       Open output file.
        if self.output_format != 'ni1':
            self.f =  open(self.outfile,'a+')
            self.f.seek(0)
            self.WriteHeader()
        else:
            self.f = None

        xdim = self.imgin.hdr['xdim']
        ydim = self.imgin.hdr['ydim']
        zdim = self.imgin.hdr['zdim']
        tdim = self.imgin.hdr['tdim']
        mdim = self.imgin.hdr['mdim']
        frame_durations = []
        jmg = zeros([ydim, xdim],float)
        if self.imgin.hdr['filetype'] == 'ge_ifile' and self.mdim > 1:
            try:
                image_in = self.imgin.readfile(dtype=self.datum_type)
                image_in = image_in.reshape((mdim, tdim, zdim, ydim, xdim))
            except RuntimeError, errmsg:
                sys.stderr.write('\n%s\n%s\n' % (errmsg, except_msg()))
                sys.exit(1)
        for im in xrange(self.imgin.hdr['mdim']):
            if im not in self.mtypes:
                continue
            for it in self.frames:
                if self.f is not None:
                    self.f.seek(self.start_binary + (self.hdrout['bitpix']/8)* \
                        (im*self.hdrout['dims'][3] + it)*prod(self.hdrout['dims'][:3]),0)
                if self.verbose:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                if self.input_format == 'unformatted':
                    img = image[im,it,:,:,:]
                else:
                    if self.mdim > 1 and \
                        self.imgin.hdr['filetype'] == 'ge_ifile':
                        img = image_in[im,it,:,:,:]
                    else:
                        img = self.imgin.readfile(frame=it, mtype=im, \
                                            dtype=self.datum_type)
                    if img is None:
                        sys.stderr.write(\
                        "convert_file: Could not read from %s\n\n" % input_file)
                        sys.exit(1)
                img = self.FlipImages(img)
                if (self.datum_type == 'short' or \
                    self.datum_type == 'byte') and img.dtype == 'float':
                    img = img.round()
                if self.datum_type == 'integer':
                    dtyp = int32
                else:
                    dtyp = self.datum_type
                if self.output_format == 'ni1':
                    fname = '%s_%04d' % (self.outfile, it+1)
                    writefile(fname, img, self.hdrout)
                else:
                    self.f.write(img.astype(dtyp).tostring())
        if self.f is not None:
            self.f.close()

        if self.imgin.hdr['native_header'].get('Modality','') == 'PT':
            sys.stderr.write(\
            '**** Temporal ordering of dynamic PET scan might be wrong. ****\n')

        if self.output_format == 'brik':
            self.WriteBrik()
        
        print 'File written to %s' % self.hdrout['imgfile']

    def CleanUp(self):
        """ Remove all of the temporary directories."""
        if self.tmp is not None:
            self.tmp.Clean()
#        cmd = "/bin/rm -rf %s" % self.tmpdir
#        os.system(cmd)


if __name__ == '__main__':
    try:
        conv = ConvertFile()
        conv.ParseArgs()
        conv.ProcessCommandLine()
        conv.Initialize()
        conv.SetupFlips()

        conv.hdrout = conv.imgin.hdr.copy()
        if conv.opts.master:
#           Update output header with info in master.
            conv.ProcessMaster()
#        if conv.input_file.endswith('.gz'):
#            conv.Gunzip()
        conv.GetOutfile()
        conv.Convert()
        conv.CleanUp()
    except SystemExit:
        conv.CleanUp()
    except RuntimeError, errstr:
        errstr = '%s\n%s' % (errstr,except_msg())
        sys.stderr.write(errstr)
        conv.CleanUp()
        sys.exit(1)
    except:
        errstr = except_msg('Error in convert_file')
        sys.stderr.write(errstr)
        conv.CleanUp()
        sys.exit(-1)
