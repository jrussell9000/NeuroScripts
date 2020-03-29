#!/usr/bin/env python

ID = "$Id: spm_norm.py 352 2010-10-07 18:27:46Z jmo $"[1:-1]

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
from os import F_OK,W_OK,R_OK
import sys
from optparse import OptionParser
from file_io import Wimage, writefile, exec_cmd
from numpy import shape, array, where, isnan, zeros, float, fliplr, ubyte, \
                  short, float32, isfinite
from stat import S_IRWXU, S_IRWXG, S_IRWXO
import constants as c
from wbl_util import execCmd, GetTmpSpace, except_msg, chg_perm
import traceback

ID = "$Id: spm_norm.py 352 2010-10-07 18:27:46Z jmo $"[1:-1]

#SPM_NORM_PATH='/apps/spm5'
#SPM_BATCH_PATH='/apps/spm5/toolbox'
#TEMPLATE_PATH='/apps/templates'

datatype_to_dtype = {'byte':ubyte, 'short':short, 'float':float32, 'float32':float32}

class SpmNorm():
    def __init__(self, input_image=None, input_file=None, matfile=None, \
                       output_file=None, scale_factor=1., w_in=None, \
                       verbose=False, voxsize=2, estimate_only=False, \
                        template="%s/spm_T1.nii"%c.TEMPLATE_PATH):
        os.umask(0113)
        if __name__ == '__main__':
            self.ParseOptions()
            self.input_image = None
        else:
            self.input_file = input_file
            if self.input_file is not None:
                self.input_file = os.path.abspath(input_file)
            self.input_image = input_image
            self.matfile = matfile
            self.output_stem = output_file
            self.scale_factor = scale_factor
            self.verbose = verbose
            self.template = os.path.abspath(template)
            self.estimate_only = estimate_only
            self.nifti_output = False
            self.matoutfile = None
            self.norm_only = False
            self.voxsize = voxsize
            self.w_in = w_in

        self.tmp = GetTmpSpace(500)
        self.tmpdir = self.tmp()

    def Initialize(self):
        if self.afni_output and self.nifti_output:
            sys.stderr.write(\
                    '\nOnly one of -a, -n, --afni, or --nifti can be present.\n')
            sys.exit(1)
        if self.afni_output:
            self.filetype = 'brik'
        elif self.nifti_output:
            self.filetype = 'nii'
        else:
            self.filetype = 'brik'

        if self.output_stem is not None:
            output_base = os.path.basename(self.output_stem)
        else:
            output_base = 'spm_norm_junk'

#        if output_base.endswith('.nii'):
#            self.output_stem = output_base.split('.nii')[0]
#        elif '+orig' in output_base:
#            self.output_stem = output_base.split('+orig')[0]
#        elif '+tlrc' in output_base:
#            self.output_stem = output_base.split('+tlrc')[0]
        self.outfile = '%s/%s' % (self.output_dir, self.output_stem)
        if not self.outfile.endswith('.nii'):
            self.outfile += '.nii'

        if self.matfile is None:
            self.norm_only = False
            self.matfile = ''
        else:
            self.matfile = os.path.abspath(self.matfile)
            self.norm_only = True

#       Read header template from disk
        self.wt = Wimage(self.template)
        if self.wt.hdr is None:
            raise RuntimeError(\
                    'Could not read template from %s' % self.template)

        self.tmpfile = '%s/tmpxxx.m' % self.tmpdir

        if self.input_image is not None:
            self.hdr = self.w_in.hdr.copy()
            if self.input_image.ndim == 4:
                self.tdim, self.zdim, self.ydim, self.xdim = self.input_image.shape
            else:
                self.tdim = 1
                self.zdim, self.ydim, self.xdim = self.input_image.shape
            self.hdr['tdim'] = self.tdim
            self.hdr['dims'][3] = self.tdim
            self.spm_imgfile = '%s/spm_tmp' % self.tmpdir
            self.SaveTmpFile(self.input_image, self.spm_imgfile)
            self.spm_imgfile += '.nii'
        elif self.input_file is not None:
#           Input specified by image file.
            self.w_in = Wimage(self.input_file)
            if self.w_in.hdr is None:
                raise RuntimeError(\
                'Failure while reading header from %s' % self.input_file)
            self.hdr = self.w_in.hdr.copy()
            self.xdim, self.ydim, self.zdim, self.tdim = self.hdr['dims'][:4]
            if self.w_in.hdr['filetype'] == '.nii':
#               SPM can use the input file if is nifti.
                self.xdim, self.ydim, self.zdim, self.tdim = self.w_in.hdr['dims']
                self.spm_imgfile = input_file
            else:
#               SPM won't recognize input, rewrite it in nifti format.
                input_image = self.w_in.readfile()
                self.spm_imgfile = '%s/spm_tmp' % self.tmpdir
                self.SaveTmpFile(input_image, self.spm_imgfile)
                self.spm_imgfile += '.nii'
                del input_image

        else:
            raise RuntimeError( \
                    'Neither input image nor input file were provided.')



    def ParseOptions(self):
        usage = "\nUsage: spm_norm [options] <filename>"
        optparser = OptionParser(usage)
        optparser.add_option( "-t", "--template", action="store",\
            default="%s/spm_T1.nii" % c.TEMPLATE_PATH, \
            dest="template", help='Template to be used. Templates are ' + \
            'stored in /apps/templates, and must be in nifti format. )')
        optparser.add_option( "-s", "--voxel_size", action="store",default=2, \
            type=int, dest="voxsize", \
            help='Voxel size.  Should be set to 1 or 2')
        optparser.add_option( "-m", "--matfile", action="store", \
            default=None, dest="matfile", help= \
            'File containing transformation matrix. Supply this argument to '+\
            'apply an existing tranformation.')
        optparser.add_option( "", "--scale-factor", action="store", \
            default=None, type=float, dest="scale_factor", help= \
            'Scale factor to be applied to input image.')
        optparser.add_option( "", "--prefix", action="store", \
            default=None, type=str, dest="prefix", help= \
            'Output file.')
        optparser.add_option( "-c", "--compute_only", action="store_true", \
          default=False, dest="estimate_only", help= \
            'Compute transformation only..')
#        optparser.add_option( "-n", "--norm_only", action="store_true", \
#            default=False, dest="norm_only", help=\
#            'Normalize image file using precomputed transformation.')
        optparser.add_option( "-V", "--version", action="store_true",  \
                dest="show_version",default=None, help="Display svn version.")
        optparser.add_option( "-v", "--verbose", action="store_true",  \
                dest="verbose",default=None, help="Write stuff to screen.")
        optparser.add_option( "-a", "--afni", action="store_true",  \
                dest="afni_output",default=None, \
                help="Write output to an AFNI +tlrc file.")
        optparser.add_option( "-n", "--nifti", action="store_true",  \
                dest="nifti_output",default=None, \
                help="Write output to a nifti file.")
        opts, args = optparser.parse_args()

        if opts.show_version:
            sys.stdout.write('%s\n' % ID) 
            sys.exit()

        if len(args) < 1:
            sys.stderr.write(
            "%s\nEnter spm_norm --help for more help\n\n" % usage)
            sys.exit()

        self.verbose = opts.verbose
        self.input_file = os.path.abspath(args[0])
        self.matfile = opts.matfile
        self.template = os.path.abspath(opts.template)
        self.afni_output = opts.afni_output
        self.nifti_output = opts.nifti_output
        self.voxsize = opts.voxsize
        self.estimate_only = opts.estimate_only
        if opts.prefix is None:
            self.output_dir = os.path.dirname(os.path.abspath(self.input_file))
            stem = os.path.basename(self.input_file.replace('.nii',''))
            stem = stem.replace('+orig','')
            stem = stem.replace('+tlrc','')
            self.output_stem = '%s_sn' % stem
        else:
            self.output_dir = os.path.dirname(os.path.abspath(opts.prefix))
            self.output_stem = os.path.basename(opts.prefix)
        self.scale_factor = opts.scale_factor
        self.nifti_output = opts.nifti_output
        self.matoutfile = None
        self.norm_only = False

    def ReadInput(self):

        self.wimg = Wimage(self.input_file)
        self.input_filetype = self.hdr['filetype']
        if self.input_filetype == 'brik':
            img = self.wimg.readfile()
            if self.scale_factor is not None:
                img *= self.scale_factor
            elif img.max() < 100:
                sys.stderr.write('Input images values are very low. ' + \
                                 'Try using hte --scale-factor option.\n')
#            self.SaveTmpFile(img)
        else:
            self.nifti_input_file = self.input_file

    def SaveTmpFile(self, image, tmp_imgfile):
        """
        Save image to /tmp in nifti format.
        """
        hdr = self.hdr
        hdr['filetype'] = 'n+1'
        writefile(tmp_imgfile,image,hdr)
        chg_perm(tmp_imgfile)
        tmp_imgfile = tmp_imgfile + '.nii'
        self.nifti_input_file = tmp_imgfile

    def SetupVariables(self):
        """Setup options variable for SPM."""
        if self.estimate_only:
            self.spm_options = 1
        elif self.norm_only:
            self.spm_options = 2
        else:
#           Compute transform and use it.
            self.spm_options = 3
        self.object_filename = self.input_file

     #   x0 = -90
     #   y0 = -126
     #   z0 = -72
     #   x1 = round(x0 + (self.wt.hdr['xdim']-1)*self.wt.hdr['xsize'])
     #   y1 = round(y0 + (self.wt.hdr['ydim']-1)*self.wt.hdr['ysize'])
     #   z1 = round(z0 + (self.wt.hdr['zdim']-1)*self.wt.hdr['zsize'])
        x0 = -90
        y0 = -126
        z0 = -72
        x1 = round(x0 + (self.wt.hdr['xdim']-1)*self.wt.hdr['xsize'])
        y1 = round(y0 + (self.wt.hdr['ydim']-1)*self.wt.hdr['ysize'])
        z1 = round(z0 + (self.wt.hdr['zdim']-1)*self.wt.hdr['zsize'])

        self.bounding_box = "[%d %d;  %d %d; %d %d]" % (x0, x1, y0, y1, z0, z1)
        self.vox_sizes = "[%f %f %f]" % (float(self.voxsize),\
                                         float(self.voxsize),\
                                         float(self.voxsize))

    def CreateScriptFile(self):
        """ Create script file for spm2_batch. """
        f = open(self.tmpfile,'w')
        os.chmod(self.tmpfile,S_IRWXU | S_IRWXG | S_IRWXO)

        f.write('addpath  %s\n' % self.tmpdir)
        f.write('addpath  %s\n' % c.SPM_NORM_PATH)
        f.write("addpath  %s\n\n" % c.SPM_BATCH_PATH)
        f.write("addpath  %s/spm2_batch\n\n" % c.SPM_BATCH_PATH)
        f.write("addpath  %s\n\n" % self.tmpdir)

# order = Vector of Integers, indicating order of operations.
#    Default: [1 2 3 4 5 6]
#    codes: AFFINE TRANSFORMATION=1; COREGISTER=2; SLICE TIMING = 3;
#          REALIGN=4; NORMALIZE=5; SMOOTH=6
        f.write("SPMBATCH.preproc(1).order=[5];\n\n")

        f.write("SPMBATCH.preproc(1).normalize = struct(...\n")
# 1: estimate only; 2: normalize and write; 3: estimate, normalize and write.
        f.write("'option', %d, ...       \n" % self.spm_options)
        f.write("'object_masking', 0, ....\n")
# Image to determine parameters for normalisation to template .
        f.write("'object', ['%s'], ...\n" % self.nifti_input_file)
        f.write("'objmask', '', ....\n")
# Mat file with normalisation parameters (for option 2 only).
        f.write("'matname', '%s', ...\n" % self.matfile)
# Only useful within full spm processing stream.
        f.write("'prev', 0, ...\n")
# Images to be normalized and written.
        f.write("'P', '%s' , ...\n" % self.nifti_input_file)

#f.write("'P', '' , ... %% Images to be normalized and written.\n")
# Normalisation template.
        f.write("'template', '%s', ...\n" % self.template)
# Default normalisation.
        f.write("'type', 0, ... \n")
# Custom normalization: default brain mask (SPM default).
        f.write("'mask_brain', 1, ...\n")
# Custom write normalized: bounding box, SPM default = default.
        f.write("'bounding_box_default', 0, ...\n")
# Custom write normalized: invoker custom bounding box.
        f.write("'bounding_box', %s, ...\n" % self.bounding_box)
# Custom voxel size: 2*2*2 = SPM default.
        f.write("'voxel_size', %s); \n\n" % self.vox_sizes)

# BatchSpecs.Todo is a vector of integers defining tasks.
#     [ANALYSIS CONTRASTS PREPROCESSING GROUPANALYSIS] 
#     Set element to 1 to perform task.\n")
# Always set to one here since normalization is preprocessing.
        f.write("SPMBATCH.Todo=[0 0 1 0];\n") 
        f.write("workdir{1} = ['./',''];\n")
        f.write("PMBATCH.dirs=workdir;\n")
        f.write("spm_batch(SPMBATCH);\n")
        f.write("exit\n")
        f.write("\n")
        f.close()


    def Normalize(self):
        """Start matlab and execute script."""

#       First, add the temporary directory to the search path.
        matlabpath = os.getenv('MATLABPATH')
        if matlabpath.endswith(':'):
            matlabpath = matlabpath[:-1]
        if matlabpath is None:
            matlabpath = "%s" %  self.tmpdir
        else:
            matlabpath = "%s:%s" % (matlabpath, self.tmpdir)
        if self.verbose:
            print 'matlabpath: ',matlabpath
        os.putenv('MATLABPATH', matlabpath)

        if self.verbose:
            devnull=''
        else:
            devnull=' >& /dev/null'
        cmd = "matlab -nodisplay -nodesktop -nojvm -nosplash -r %s %s" % \
                    (os.path.basename(self.tmpfile).split('.')[0], devnull)
        self.outfile_spm = '%s/w%s' % (os.path.dirname(self.nifti_input_file), \
                                       os.path.basename(self.nifti_input_file))
        execCmd(cmd,verbose=self.verbose)
        if not os.access(self.outfile_spm, R_OK):
            raise RuntimeError('SPM did not write normalized image %s' % \
                                                            self.outfile_spm)

    def RenameOutput(self):
        if not self.norm_only:
            matbase = '%s_sn.mat' % \
                        (os.path.basename(self.nifti_input_file)).split('.')[0]
            self.matoutfile = '%s/w%s.mat' % \
                        (self.output_dir, self.output_stem)
            matdir = os.path.dirname(self.nifti_input_file)
            if matdir != self.output_dir:
                matfile_spm = '%s/%s' % (matdir, matbase)
                self.RenameMatfile(matfile_spm, self.matoutfile)
        else:
            matdir = None

    def CopyOutput(self):
        """
        Copies spm's output either directly or with 3dcopy. Unfortunately,
        the output file will have NaNs in it.
        """
        if self.filetype == 'brik':
            cmd = '3dcopy %s %s+tlrc' % (self.outfile_spm, self.outfile)
        else:
            cmd = 'mv %s %s.nii' % (self.outfile_spm, self.outfile)
        print cmd
        execCmd(cmd,verbose=self.verbose)
        

    def ReadSpmOutput(self, frame=None, datatype=float32):
        try:
            self.wspm = Wimage(self.outfile_spm)
        except RuntimeError, errstr:
            sys.stderr.write('\nError while reading %s.\n%s\n%s\n' %
                                (self.outfile_spm, errstr, except_msg()))
            sys.exit(-1)
        dims = self.wt.hdr['dims']
        shp = [self.tdim, dims[2], dims[1], dims[0]]
        imgout = zeros(shp, float)
        for t in xrange(self.tdim):
            imgin = self.wspm.readfile(frame=t, dtype=datatype)
            imgout[t,...] = where(isnan(imgin), 0., imgin)

        return imgout.squeeze()
        
    def WriteOutput(self):
        prefix = self.outfile.replace('.BRIK','')
        prefix = prefix.replace('.HEAD','')
        prefix = prefix.replace('+orig','')
        prefix = prefix.replace('.nii','')
        if self.filetype == 'nii':
            cmd = 'cp %s %s.nii' % (self.outfile_spm, prefix)
        else:
            cmd = '3dcopy %s %s+tlrc' % (self.outfile_spm, prefix)
        if self.verbose:
            print cmd
        exec_cmd(cmd)
        
      #  self.wspm = Wimage(self.outfile_spm)
      #  datatype = datatype_to_dtype[self.wspm.hdr['datatype']]
      #  hdrout = self.wspm.hdr.copy()
      #  hdrout['filetype'] = self.filetype
      #  for t in xrange(hdrout['tdim']):
      #      imgin =self.wspm.readfile(frame=t, dtype=datatype)
      #      print 111,self.outfile_spm, t, datatype, imgin.shape, self.outfile, t==hdrout['tdim']-1
      #      imgout = where(isfinite(imgin), imgin, 0.)
      #      if hdrout['tdim'] > 1:
      #          writefile(self.outfile, imgout, hdrout, frame=t, \
      #                                      last=(t==hdrout['tdim']-1))
      #      else:
      #          writefile(self.outfile, imgout, hdrout)

    def RenameMatfile(self, matfile_old, matfile_new):
#       os.rename won't work across file systems, so copy it.
        f = open(matfile_old,'r')
        mat = f.read()
        f.close()
        f = open(matfile_new,'w')
        f.write(mat)
        f.close()
        os.remove(matfile_old)

    def CleanUp(self):
        self.tmp.Clean()
#            if os.path.exists(self.tmpdir):
#                print 'spm_norm: Skip cleanup of %s' % self.tmpdir
#                exec_cmd("/bin/rm -r %s" % self.tmpdir)

def spm_norm():
    sn = SpmNorm()
    try:
        sn.Initialize()
        try:
#            sn.ReadInput()
            sn.SetupVariables()
        except:
            print except_msg("spm_norm")
            sn.CleanUp()
            sys.exit(1)
        try:
            sn.CreateScriptFile()
        except IOError, err:
            sys.stderr.write("spm_norm: I/O Error writing script file. Verify that you have write access.\n")
            sn.CleanUp()
            sys.exit(1)
        sn.Normalize()
        sn.RenameOutput()
        if sn.matoutfile is not None:
            print "Matrix written to %s" % (sn.matoutfile)
        sn.WriteOutput()
#        if sn.filetype == 'brik':
#            sn.WriteOutput()
#        else:
#            sn.CopyOutput()
        if sn.outfile is not None and sn.verbose:
            print "Normalized image file written to %s\n" % sn.outfile
        sn.CleanUp()
        sys.exit(0)
    except RuntimeError, errstr:
        sys.stderr.write('\n%s\n%s\n' % (errstr, except_msg()))
        sn.CleanUp()
        sys.exit(1)
    except SystemExit:
        sn.CleanUp()
        sys.exit(0)
    except:
        errstr = except_msg('Error in spm_norm')
        sys.stderr.write(errstr)
        sn.CleanUp()
        sys.exit(1)


if __name__ == '__main__':
    spm_norm()
