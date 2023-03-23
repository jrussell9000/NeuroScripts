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
# Copyright (c) 2006-2007, John Ollinger, University of Wisconsin
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
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
sys.path.insert(0, '/Users/jdrussell3/NeuroScripts/Shared/Ollinger/lib')
import warnings
warnings.simplefilter("ignore", UserWarning)
import sys
import os
from os import R_OK,W_OK,F_OK
import string
from math  import pi

import numpy
from numpy import *
from numpy.linalg import inv 
import file_io
from file_io import isIfile, Wimage, writefile, DicomTar
from wbl_util import execCmd, except_msg,  chg_perm, GetTmpSpace
import scipy
# from scipy.stats.stats import histogram2
from numpy import histogram2d
from scipy.ndimage.morphology import binary_erosion, binary_dilation, \
                                     grey_dilation
from scipy.ndimage.filters import median_filter

import math_bic
from math_bic import print_matrix, erode, fit_legendre, whisto
from optparse import OptionParser
from wisc_dicom import isdicom, IsDicom
import time
from stat import S_IRWXU, S_IRWXG, S_IRWXO
import constants as c

ID = "$Id: make_fmap.py 560 2011-06-04 00:00:00Z jmo $"[1:-1]

FMAP_DIM = 256  # Desired resolution of field map images.

"""
Program: make_fmap

Purpose: Use the FSL program "prelude" to compute a field map that can 
         be used to correct for distortion.  

Inputs: Images acquired with gradient echo  sequence at two TE's.  It 
        is assumed that phase, magnitude, real and imaginary parts are stored.
        Data are specified by the name of the directory in which the 
        dicom files or GE I-files are stored.

Outputs: A single field map in analyze format.  The field map is stored in 
         in units of radians.  The pixel shifts are given by 
         N*tau*fm/(2*pi) where N is the number of voxels in the phase encode
         direction, tau is the time from the center of one readout to the next, 
         .i.e, the time it takes to readout one line of k-space including the 
         ramps (the echo spacing).

Written by John Ollinger

University of Wisconsin

Modified for the GE scanner on 3/26/05.

"""


class MakeFieldmap():

    def __init__(self):

        # Set default permission to 0775
        os.umask(0002)

        usage = \
            "Usage: make_fmap fmap_data_dir field_map_file [anatomical] " + \
            "[-nocleanup -v]\n" + \
            "    fmap_data_dir: Directory containing the field map data.\n" + \
            "    field_map_file: Output file name.\n" + \
            "    anatomical: Name of anatomical image (BRIK or dicom). " + \
            "This is optional.\n" + \
            "    -v: verbose mode.\n"

        optparser = OptionParser(usage)

        optparser.add_option( "-v", "--verbose", action="store_true", \
            dest="verbose",default=False, help='Verbose mode.')
        optparser.add_option( "", "--force-slicecorr", action="store_true", \
            dest="force_slicecorr",default=False, \
            help='Force correction for 180 degree phase shifts across slices.')
        optparser.add_option( "", "--omit-slicecorr", action="store_true", \
            dest="omit_slicecorr",default=False, \
            help='Skip correction for 180 degree phase shifts across slices even if it is automatically detected.')
        optparser.add_option( "-d", "--debug", action="store_true", \
            dest="debug",default=False, \
            help='Keep intermediate files in /tmp/fmap_debug. " + \
            "Otherwise delete them.')
        optparser.add_option( "-f", "--fast", action="store_true", \
            dest="fast",default=False, \
            help='Skip calls to bet and prelude.')
        optparser.add_option( "", "--TE1", action="store", \
            dest="TE1", default=0, type=float, \
            help='First (shortest) echo time.')
        optparser.add_option( "", "--TE2", action="store", \
            dest="TE2", default=0, type=float, \
            help='Second (longest) echo time.')
        optparser.add_option( "", "--mag", action="store", \
            dest="save_magfile", default=None, type=str, \
            help='Prefix where magnitude image at shortest TE should be saved.')
        optparser.add_option( "", "--anat", action="store", \
            dest="anatfile", default=None, type=str, \
            help='Anatomical image, target for registration of the first magnitude image.')
        optparser.add_option( "-m", "--mask", action="store", type="string", \
            dest="usermask",default=None, help=\
            "Use user supplied mask rather " + \
            "than bet. This must be used for nonhuman subjects.")
        self.opts, args = optparser.parse_args()

        # First print out the path for bug reports.
        print os.getcwd()
        for argh in sys.argv:
            sys.stdout.write("%s " % argh)
        sys.stdout.write("\n")

        if len(args) < 2:
            sys.stderr.write(usage)
            raise SyntaxError(\
            "*** Expecting 2 arguments, got %d ***\n" % len(args))

#       Get file names.
        self.fmapdata = os.path.abspath(args[0])
        sys.stdout.flush()
        if isIfile(self.fmapdata):
            self.file_type = 'ge_Ifile'
        elif IsDicom(self.fmapdata)():
            self.file_type = 'dicom'
        else:
            raise RuntimeError('Invalid file type for fieldmap data: %s' % \
                               self.fmapdata)
        self.fullpath = self.fmapdata
        prefix = args[-1]
        self.TE1 = self.opts.TE1
        self.TE2 = self.opts.TE2
        self.save_magfile = self.opts.save_magfile
        self.anatfile = self.opts.anatfile
        self.omit_slicecorr = self.opts.omit_slicecorr
        self.force_slicecorr = self.opts.force_slicecorr

#       Output file name
        self.fmap_file, fmap_ext = os.path.splitext(prefix)
        self.fmap_file = self.fmap_file.split('+')[0]

        self.outdir = os.path.dirname(os.path.abspath(self.fmap_file))
        basename = os.path.basename(self.fmap_file)
        basename, fmap_ext = os.path.splitext(prefix)
        self.basename = self.fmap_file.split('+')[0]

        self.coarse_mask_file = '%s/%s_mask' % (self.outdir, self.basename)

#       Get path to anatomical, if any.
        if self.anatfile is not None:
            self.anatfile = opts.anatfile
            if self.anatfile.endswith('+orig'):
                testname = self.anatfile + '.HEAD'
            elif self.anatfile.endswith('.nii'):
                testname = self.anatfile
            else:
                testname = self.anatfile + '.nii'
            if not os.access(testname, R_OK):
                raise RuntimeError(\
                'Anatomical image (%s) is not readable.'%self.anatfile, \
                name='__init__')

        self.zoomfactor = 1.
        self.verbose = self.opts.verbose
        if self.opts.verbose:
            self.fsl_verbose = '-v'
        else:
            self.fsl_verbose = ''

    def CheckPaths(self):
#       Create a directory for temporary data.
        if not self.opts.fast:
            if self.opts.debug:
                self.tmp = GetTmpSpace(300, '/tmp/debug')
            else:
                self.tmp = GetTmpSpace(300)
            self.tmpdir = self.tmp()
        else:
            self.tmpdir = os.getcwd()

#       Check for access to input and output data paths.
   #     for fmapdir in self.fmapdirs:
   #         if not os.access(fmapdir, R_OK):
   #             raise RuntimeError(\
   #             "\nmake_fmap: Could not access fieldmap data: %s\n\n" % fmapdir)
   #     if not os.access(self.outdir,W_OK):
   #         raise RuntimeError(\
   #         "\nmake_fmap: Output path is not writeable: %s\n\n" % self.outdir)

    def SetupFSL(self):
#       Setup path to latest version of fsl.
        topdir = "" 
        fsldir = c.FSLDIR
        if fsldir is None:
            fd = os.popen('which fsl')
            lines = fd.read()
            fd.close()
            print 'Using FSL version:\n',lines
            if len(lines) == 0:
                raise OSError( \
                "Could not find fsl. Check your path environment variable.\n")
            fsldir = os.path.basename(lines.strip())
        if len(fsldir) > 0:
            os.putenv('FSLDIR',fsldir)
            os.putenv('PATH',"%s/bin:%s" % (fsldir,os.environ['PATH']))
            os.putenv('FSLOUTPUTTYPE','NIFTI')

    def SetupAFNI(self):
#       Get AFNI version.
        cmd = "3dinfo -verb 2>/dev/null"
        f = os.popen(cmd)
        lines = f.readlines()
        f.close()
        for line in lines:
            if 'version=' in line.lower():
#               This line has version information.
                words = line.split()
                while 'version=' not in word:
                    pass
                version = int(word[8:].replace('_',''))
                if version < 200705291644:
#                   Need version that handles nifti files correctly.
                    afni_dir = '/apps/linux/afni-latest'
                    os.putenv('AFNI_PLUGINPATH',afni_dir)
                    os.putenv('PATH',"%s:%s" % (afni_dir,os.environ['PATH']))

   # def FindFieldmapData(self):
#  #     Find the field map data (images acquired with 2dfast).
   #     searchdirs = []
   #     if len(self.fmapdata) > 1:
   #         return
#  #     First search all subdirectories for the data.
   #     fmapdirs = []
   #     for dir, subdirs, fnames in os.walk(self.fmapdirs[0]):
#  #          print 100, dir
   #         for fname in fnames:
   #             self.fullpath = "%s/%s" % (dir,fname)
   #             print 111, os.path.abspath(self.fullpath)
   #             print 112, isdicom(self.fullpath), isIfile(self.fullpath), DicomTar(self.fullpath).isTar
   #             if isdicom(self.fullpath):
   #                 self.file_type = 'dicom'
   #                 break
   #             elif isIfile(self.fullpath):
   #                 self.file_type = 'ge_Ifile'
   #                 break
   #             elif DicomTar(self.fullpath).isTar:
   #                 self.file_type = 'dicom'
   #                 break
   #         else:
   #             continue
   #         break
   #     else:
   #         raise ValueError("make_fmap: Could not find field map data")
   #     self.fmapdirs.append([dir])

    def ReadFieldmapData(self):

        print "Reading data."
        if self.file_type == 'ge_Ifile':
#            Wdata = Wimage("%s/I.001" % (self.fmapdirs[0]), scan=True)
            Wdata = Wimage(self.fmapdata, scan=True)
            self.hdr = Wdata.hdr
#            sys.stdout.write('201, data read\n')
#            sys.stdout.flush()
            self.image = Wdata.readfile(dtype=float)
#            sys.stdout.write('202, data read\n')
#            sys.stdout.flush()
            num_echos = 1
            nhdr = self.hdr['native_header']
            fnames = os.listdir(self.fmapdata)
            nf = int(len(fnames))/self.hdr['zdim']
            if nf == 9:
                self.image = self.image[1:,...]
                sys.stderr.write(\
                '\n\t******************************************************\n\n'+ \
                '\t9 frames were collected rather than 8.  Assuming that \n'+ \
                '\tacquisition was rerun after initial error.\n' + \
                '\tCheck results carefully !!!.\n' + \
                '\t******************************************************\n\n')
            elif nf < 8:
                raise ValueError("Fieldmap data are incomplete")
            elif nf > 8:
                raise ValueError("Fieldmap data are invalid: too many frames")
            hdr2 = file_io.readheader("%s/I.%03d" % \
                                (self.fmapdata,8*self.hdr['zdim']))
            self.EchoTimes = [self.hdr['native_header']['EchoTime'], \
                                  hdr2['native_header']['EchoTime']]
            self.format = 'rimprimp'
#            sys.stdout.write('200, data read\n')
#            sys.stdout.flush()
        elif self.file_type == 'dicom':
#           Data in dicom format.
            if self.verbose:
                print "%s" % (self.fmapdata)
            Wdata = Wimage(self.fmapdata, scan=True)
            self.hdr = Wdata.hdr
            if self.hdr is None:
                raise IOError("make_fmap: Could not read %s" % self.fmapdata)
            else:
                image1 = Wdata.readfile(dtype=float)
            nhdr = self.hdr['native_header']
            self.image = image1
            self.format = 'rimprimp'
            self.EchoTimes = nhdr['EchoTimes']
        else:
#           Assume that the data are in either brik or nifti stored
#           as follows:
#           frame 1: magnitude, short TE
#           frame 2: phase, short TE
#           frame 3: magnitude, long TE
#           frame 4: phase, long TE
            if self.verbose:
                print "%s" % (self.fmapdir)
            Wdata = Wimage(self.fmapdir, scan=True)
            self.hdr = Wdata.hdr
            if self.hdr is not None:
                self.image = Wdata.readfile(dtype=float)
            else:
                raise IOError(\
                "make_fmap: Could not read %s" % "%s/%s" % (self.fmapdir,test))
            nhdr = self.hdr['native_header']
            self.format = 'mpmp'
            self.EchoTimes = [self.TE1, self.TE2]

        self.fmap_dims = self.hdr['dims'][:3]
        self.fmap_shape = self.hdr['dims'][:3].tolist()
        self.fmap_shape.reverse()
        self.xdim = self.hdr['xdim']
        self.ydim = self.hdr['ydim']
        self.zdim = self.hdr['zdim']
        self.tdim = self.hdr['tdim']
        self.mdim = self.hdr['mdim']
        self.fmap_stem = "%s/%s" % (self.fmapdata, \
                                        os.path.splitext(self.fullpath)[0])

        self.R_fmap = self.hdr['R']
        print_matrix(self.R_fmap,'Field map data transformation matrix:')

        self.whdr = self.hdr['native_header']

#       Image contains, real, imag, mag, phase components. */
        self.xsize = self.hdr['xsize']
        self.ysize = self.hdr['ysize']
        self.zsize = self.hdr['zsize']
        self.xdim_out = FMAP_DIM
        self.ydim_out = FMAP_DIM
        self.zdim_out = self.zdim 
        self.GetHdrout()
    

    def CheckEchoTimes(self):
        if isinstance(self.EchoTimes, list):
            if len(self.EchoTimes) >= 2:
                self.delay = self.EchoTimes[1] - self.EchoTimes[0]
            else:
                raise ValueError(\
                'Images at %d TE(s) were found.' % len(self.EchoTimes) + \
                'Two and only two echo-times are required.')
        else:
            self.delay = self.hdr2['te'] - self.hdr['te']

        if abs(self.delay) < 1:
            raise ValueError(\
            "make_fmap: Both field map series used the same " + \
            "TE.  Field map cannot be computed. %s\n" % self.fullpath)

        print '\nDelay time: %4.1f ms' % (self.delay)

        if self.hdr.has_key('plane'):
            print 'Orientation: %s' % self.hdr['plane']

    def FixSlicePhaseFlips(self, mag, phs):
        """
        Fix 180 degree phase shifts across slices. These are artifactual and 
        occur in fieldmap acquired with version ESE20 of the scanner OS.
        """
        if self.omit_slicecorr:
            return phs

#       Detect 180 phase shifts across slices.
        mask = where(mag > .25*mag.max(), 1., 0.)
        mask = binary_erosion(mask, ones([3,3,3]))
   #     xmg = zeros([self.ydim, self.xdim], complex)
   #     jmg = zeros([self.zdim, self.ydim, self.xdim], float)
   #     flip = -ones([self.ydim, self.xdim], complex)
   #     for z in xrange(self.zdim):
   #         xmg.real = cos(phs[z,...])
   #         xmg.imag = sin(phs[z,...])
   #         if (z % 2) > 0:
   #             jmg[z,...] = angle(flip*xmg)
   #         else:
   #             jmg[z,...] = angle(xmg)
#       For smoothly varying phase, subtracting 
#        kmg = mask*jmg
        phs1 = mask*phs

#        if not self.force_slicecorr:
#            if self.opts.verbose:
#                print 'No through-slice phase precorrection applied.'
#            return jmg

#       a should be big.
#        a = (kmg[2*arange(self.zdim/2),...] - \
#                            kmg[2*arange(self.zdim/2)+1,...]).sum()/mask.sum()
#       First compute sum of phase in even and odd slices.  Should be big.
        a = 2*(phs1[2*arange(self.zdim/2),...] + \
                            phs1[2*arange(self.zdim/2)+1,...]).sum()/mask.sum()
#       Mean phase difference between even and odd slices.  Shold be near zero.
        b = 2*(phs1[2*arange(self.zdim/2),...] - \
                            phs1[2*arange(self.zdim/2)+1,...]).sum()/mask.sum()
        if abs(b/a) > 10. and b > pi/8. or self.force_slicecorr:
#           Phase flips are present, return corrected phase.
            xmg = zeros([self.ydim, self.xdim], complex)
            jmg = zeros([self.zdim, self.ydim, self.xdim], float)
            flip = -ones([self.ydim, self.xdim], complex)
            for z in xrange(self.zdim):
                xmg.real = cos(phs[z,...])
                xmg.imag = sin(phs[z,...])
                if (z % 2) > 0:
                    jmg[z,...] = angle(flip*xmg)
                else:
                    jmg[z,...] = angle(xmg)
            sys.stderr.write('\n*** 180 degree phase errors across slices were detected and corrected. ***\n\n')
            return jmg
#        elif self.force_slicecorr:
#            sys.stderr.write('\n*** 180 degree phase errors across slices were not detected but were corrected per command line option. ***\n\n')
#            return jmg
        else:
            print 'No phase correction applied.'
            return phs

    def GetRawPhase(self):
#       Get the real and imaginary parts.
        mag1 =  zeros((self.fmap_shape),float)
        real1 = zeros((self.fmap_shape),float)
        imag1 = zeros((self.fmap_shape),float)
        mag2 =  zeros((self.fmap_shape),float)
        real2 = zeros((self.fmap_shape),float)
        imag2 = zeros((self.fmap_shape),float)
        if self.file_type == 'ge_Ifile':
          #  self.image = reshape(self.image,\
          #                  [2, self.zdim, 4, self.ydim, self.xdim])
          #  mag1  = self.image[0,:,0,:,:]
          #  mag2  = self.image[1,:,0,:,:]
          #  real1 = self.image[0,:,2,:,:]
          #  real2 = self.image[1,:,2,:,:]
          #  imag1 = self.image[0,:,3,:,:]
          #  imag2 = self.image[1,:,3,:,:]
          #  phs1, phs2 = self.ComputePhase(imag1, real1, imag2, real2)
            self.image = reshape(self.image,[self.hdr['mdim'], \
                        self.hdr['tdim'],self.hdr['zdim'], \
                        self.hdr['ydim'], self.hdr['xdim']])
            mag1  = self.image[0,0,:,:,:]
            mag2  = self.image[0,1,:,:,:]
            real1 = self.image[2,0,:,:,:]
            real2 = self.image[2,1,:,:,:]
            imag1 = self.image[3,0,:,:,:]
            imag2 = self.image[3,1,:,:,:]
            phs1, phs2 = self.ComputePhase(imag1, real1, imag2, real2)
        elif self.file_type == 'dicom':
            self.image = reshape(self.image,[self.hdr['mdim'], \
                        self.hdr['tdim'],self.hdr['zdim'], \
                        self.hdr['ydim'], self.hdr['xdim']])
            mag1  = self.image[0,0,:,:,:]
            mag2  = self.image[0,1,:,:,:]
            real1 = self.image[2,0,:,:,:]
            real2 = self.image[2,1,:,:,:]
            imag1 = self.image[3,0,:,:,:]
            imag2 = self.image[3,1,:,:,:]
            phs1, phs2 = self.ComputePhase(imag1, real1, imag2, real2)
        else:
            mag1  = self.image[0,:,:,:]
            phs1  = self.image[1,:,:,:]
            mag2 = self.image[2,:,:,:]
            phs2 = self.image[3,:,:,:]

#       Write magnitude images for use by prelude.
        self.WriteMagFiles(mag1, mag2)
        if self.opts.usermask is None:
            self.StripBrain()
        else:
            self.mask_file = self.opts.usermask
        self.CreateMask()
        phs1 *= self.fmap_mask
        phs2 *= self.fmap_mask
        phs1 = self.FixSlicePhaseFlips(mag1, phs1)
        phs2 = self.FixSlicePhaseFlips(mag2, phs2)
        self.WritePhase(phs1, phs2)

        return phs1, phs2


    def GetHdrout(self):
        self.hdr['datatype'] = 'float'
        self.hdr_out = self.hdr.copy()
        self.hdr_out['dims'][0] = self.xdim_out
        self.hdr_out['dims'][1] = self.ydim_out
        self.hdr_out['dims'][2] = self.zdim_out
        self.hdr_out['dims'][3] = 1
        self.hdr_out['dims'][4] = 1
        self.hdr_out['sizes'][0] = self.xsize*self.zoomfactor
        self.hdr_out['sizes'][1] = self.ysize*self.zoomfactor
        self.hdr_out['sizes'][2] = self.zsize
        self.hdr_out['sizes'][3] = 1.
        self.hdr_out['sizes'][4] = 1.
        self.hdr_out['num_voxels'] = prod(array(self.hdr_out['dims']))
        self.hdr_out['datatype'] = "float32"
        self.hdr_out['swap'] = 0

        self.hdr_out['x0'] = self.R_fmap[0,3]
        self.hdr_out['y0'] = self.R_fmap[1,3]
        self.hdr_out['z0'] = self.R_fmap[2,3]
        self.hdr_out['R'] = self.R_fmap
        self.hdr_out['datatype'] = 'float'
        self.hdr_out['filetype'] = 'n+1'

    def RegisterFmapToT1High(self):
#           Register shortest TE magnitude image with anatomical.
#        compute_xform_to_anat(self.anatfile, self.mag1_file,  \
#                        self.mag1, self.tmpdir,self.hdr_out, self.opts)

        hdr = self.hdr.copy()
        hdr['filetype'] = 'n+1'

        if os.path.isdir(self.anatfile):
            anat_file = '%s/anat_file' % self.tmpdir
            cmd = 'convert_file %s %s brik' (self.anatfile, anat_file)
            execCmd(cmd)
            anat_file = anat_stem + '+orig'
        else:
#           Make sure file has full path and correct extensions.
            anat_dir = os.path.dirname(os.path.abspath(self.anatfile))
            anat_base = os.path.basename(self.anatfile)
            anat_stem = os.path.splitext(anat_base)[0].split('+')[0]
            anat_file = '%s/%s' % (anat_dir, anat_stem)
            if self.anatfile.endswith('.BRIK') or \
               self.anatfile.endswith('.HEAD'):
                self.anatfile = self.anatfile[:-5]

        mag1_file = "%s/mag1_tmp" % self.tmpdir
        anat_resamp = "%s/%s_resamp" % (self.tmpdir,anat_stem)

#       Resample the anatomical data to the fieldmap image size.
        if os.access('%s.nii' % anat_resamp,R_OK):
            os.remove('%s.nii' % anat_resamp)
        cmd = "3dresample -prefix %s.nii -inset %s -master %s" % \
                                    (anat_resamp, self.anatfile, self.mag1_file)
        if self.verbose:
            print cmd
        execCmd(cmd)
        chg_perm("%s.nii" % self.mag1_file)

        if os.access('%s_reg.nii' % anat_resamp,R_OK):
            os.remove('%s_reg.nii' % anat_resamp)

#       Register the field-map magnitude to the anatomical.
        cmd = "3dvolreg -rotcom -Fourier -twopass -prefix %s_reg.nii" % \
              anat_resamp + \
              " -verbose -base %s.nii %s" % (anat_resamp, self.mag1_file)
        if self.verbose:
            print cmd
        fd = os.popen(cmd)
        lines = fd.read()
        fd.close()
        lines = lines.split('\n')
        chg_perm("%s_reg.nii" % anat_resamp)

#       Extract the rotate command from the 3dvolreg output.
        for line in lines:
            if "3drotate" in line and len(line.split()) > 3:
                tmpfile = "%s/3drotate_%s_cmd.txt" % (self.outdir,hdr['plane'])
                i = 0
                while os.access(tmpfile,F_OK):
                    i = i + 1
                    tmpfile = "%s/3drotate_%s_cmd_%d.txt" % \
                                                (self.outdir,hdr['plane'],i)
                sys.stdout.write(\
                "Fragmentary rotate command written to: %s\n" % tmpfile)
                ftmp = open(tmpfile,"w")
                ftmp.write(line.strip())
                ftmp.close()
                break

    def StripBrain(self):
#       Create brain mask.

#       First write magnitude and phase images to disk.
#        self.WriteMagFiles()

        os.path.splitext(self.fmap_file)[0]
        self.mask_file  = '%s/%s_strip_mask.nii' % \
                        (self.tmpdir, os.path.basename(self.fmap_stem))
        strip_file1 = '%s/%s_strip' % \
                        (self.tmpdir, os.path.basename(self.fmap_stem))
        if not self.opts.fast or not os.path.exists(self.mask_file):
        #   Don't skip call to bet.
            cmd = "bet2 %s %s -m -f .3" % \
                            (self.mag1_file, strip_file1)
            if self.opts.verbose:
                print cmd
            execCmd(cmd)
        else:
            print "Skipping brain extraction."

    def WriteMagFiles(self, mag1, mag2):
        self.mag1_file = '%s/mag1_tmp'  % self.tmpdir
        self.mag2_file = '%s/mag2_tmp'  % self.tmpdir
        writefile(self.mag1_file, mag1, self.hdr_out)
        writefile(self.mag2_file, mag2, self.hdr_out)
        chg_perm(self.mag1_file)
        chg_perm(self.mag2_file)
        if self.save_magfile is not None:
            writefile(self.save_magfile, mag1, self.hdr_out)
            chg_perm(self.save_magfile)

    def CreateMask(self):
#       Read mask created by bet.
        Wbet = Wimage(self.mask_file)
#        mhdr = Wbet.hdr
        bet_mask = Wbet.readfile(dtype=float32)
        if bet_mask is None:
            raise RuntimeError(\
            'make_fmap: Error while reading brain-stripped mask: %s\n' \
            % self.mask_file, name='CreateMask')

        if not allclose(Wbet.hdr['dims'], self.hdr_out['dims']):
            bet_mask = self.RegisterMask()
        struct = ones([1, 3, 3],float)
        self.fmap_mask = binary_dilation(bet_mask, struct, 1)

#       Write mask to disk for use by prelude.
        mhdr = self.hdr_out.copy()
        mask_file = '%s/%s_mask_tmp.nii' % \
                        (self.tmpdir,os.path.basename(self.fmap_file))
        mhdr['filetype'] = 'n+1'
        mhdr['datatype'] = 'short'
        mhdr['mdim'] = 1
        mhdr['tdim'] = 1
        mhdr['swap'] = 0
        writefile(mask_file, self.fmap_mask, mhdr)
        chg_perm(mask_file)

    def RegisterMask(self):
        mask_infile = self.mask_file
        self.mask_file = '%s/%s.tmp.nii' % \
                            (self.tmpdir, os.path.basename(self.mask_file))
        cmd = '3dresample -master %s -prefix %s -inset %s' % \
                    (self.mag1_file, self.mask_file, mask_infile)
        if self.verbose:
            print "Registering mask with field-map data"
            print cmd
        execCmd(cmd)
        Wbet = Wimage(self.mask_file)
        return Wbet.readfile(dtype=float32)

    def ComputePhase(self, imag1, real1, imag2, real2):
#       Compute phase. Mask so we don't unwrap noise.
        phs1 = scipy.arctan2(imag1, real1)
        phs2 = scipy.arctan2(imag2, real2)
        return phs1, phs2

    def WritePhase(self, phs1, phs2):
#       Write phase images to disk.
        self.phase1_file = '%s/phase1_tmp' % self.tmpdir
        self.phase2_file = '%s/phase2_tmp' % self.tmpdir
        writefile(self.phase1_file, phs1, self.hdr_out)
        writefile(self.phase2_file, phs2, self.hdr_out)
        chg_perm(self.phase1_file)
        chg_perm(self.phase2_file)

    def UnwrapPhase(self):
        if self.opts.verbose:
            print "Unwrapping phase images."

#       Unwrap phases with prelude.
        phs1_unw_file = '%s/%s_phase1_unw_tmp.nii' %  \
                        (self.tmpdir, os.path.basename(self.fmap_file))
        phs2_unw_file = '%s/%s_phase2_unw_tmp.nii' %  \
                        (self.tmpdir, os.path.basename(self.fmap_file))

#       First acquistion.
        if not self.opts.fast or not os.path.exists(phs1_unw_file):
            cmd = "prelude -a %s -p %s -u %s %s -m %s" %  \
                    (self.mag1_file, self.phase1_file, phs1_unw_file, \
                                        self.fsl_verbose, self.mask_file)
            if self.verbose:
                print "Unwrapping first phase image."
                print cmd
            execCmd(cmd)

#       Second acquistion.
        if not self.opts.fast or not os.path.exists(phs2_unw_file):
            cmd = "prelude -a %s -p %s -u %s %s -m %s" %  \
                    (self.mag2_file, self.phase2_file, phs2_unw_file, \
                                         self.fsl_verbose, self.mask_file)
            if self.verbose:
                print "Unwrapping second phase image."
                print cmd
            execCmd(cmd)
        else:
            print "Skipping calls to prelude."

#       Read unwraped phase images from disk.
        Wphs1 = Wimage(phs1_unw_file)
        if Wphs1 is not None:
            self.phs1 = Wphs1.readfile(dtype=float32)
        else:
            raise IOError("make_fmap: Could not read %s\n" % phs1_unw_file)

        Wphs2 = Wimage(phs2_unw_file)
        if Wphs2 is not None:
            self.phs2 = Wphs2.readfile(dtype=float32)
        else:
            raise IOError("make_fmap: Could not read %s\n" % phs2_unw_file)

    def EditMask(self):
#       Delete voxels that violate the Nyquist criterion, i.e., 
#       that change by more than pi/2 in one pixel.

#       First create a mask identifying voxels that exceed the Nyquist rate.
        mask = zeros(self.fmap_shape, bool)
        for z in range(self.zdim):
            mask1 = self.NyquistMask(self.phs1[z,...])
            mask2 = self.NyquistMask(self.phs2[z,...])
            mask[z,:,:] = mask1.astype(bool)| mask2.astype(bool)


#       Fill in-plane holes in the initial mask.
        ORDER = 7
        struct = ones([1, ORDER, ORDER], bool)
        mask = binary_dilation(mask,struct, 1)
        struct = ones([1, ORDER, ORDER], bool)
        mask = binary_erosion(mask, struct, 1)


#       Fill interior of mask.
#       Start with eroded mask from bet, then fill between known
#       cortical edges.
        struct = ones([1, 3, 3], int)
        mask_fill = binary_erosion(self.fmap_mask.astype(int), struct, 1)
        
        mask_exterior = ((1 - mask_fill) | mask) #.clip(0, 1)

#       Erode and dilate to eliminate interior islands.
        ORDER = 7
        struct = ones([1, ORDER, ORDER], int)
        mask_exterior = binary_erosion( mask_exterior, struct, 1)
        mask_exterior = binary_dilation(mask_exterior, struct, 1)
        ORDER = 5
        struct = ones([1, ORDER, ORDER], int)
        mask_exterior = binary_dilation(mask_exterior, struct, 1)
        mask_exterior = binary_erosion( mask_exterior, struct, 1)

#       Erode the interior boundary of the mask.
        ORDER = 3
        struct = ones([1, ORDER, ORDER], int)
        mask_exterior = binary_erosion( mask_exterior, struct, 1)

#       Multiply eroded exterior mask and the "reject" mask to ensure that
#       we aren't throwing away brain voxels.
        mask = (mask*mask_exterior).astype(float)
        mask= binary_erosion( mask, struct, 1)
        mask= binary_dilation( mask, struct, 1)

#       Edit out voxels with phase shifts exceeding Nyquist rate as well as
#       regions added in edge slices by 3D dilation.
        hdr_fmap_mask = self.hdr_out.copy()
        hdr_fmap_mask['datatype'] = 'float'
#        writefile("fmap_mask", self.fmap_mask.astype(float), hdr_fmap_mask)

    def CreateFieldmap(self):
        """ Subtract unwrapped phase maps, scale, set centroid to zero."""
#        mask = where(abs(self.fmap) > 0.,1.,0.)
        self.fmap = self.fmap_mask*(self.phs2 - self.phs1)

        self.fmap = 1000.*self.fmap/self.delay # Phase change in radians/sec.

#       Create coarse mask guaranteed not to remove brain voxels.
        self.coarse_mask = where(self.fmap_mask + \
                            where(self.fmap!=0., 1, 0), 1., 0.)

#       Filter with a median filter 3 pixels square.  This removes 
#       single-pixel outliers.   
        median_filter(self.fmap, size=3,mode='constant',cval=0.)

        # Set correction to zero at the centroid of the image.
        msk = where(abs(self.fmap) > 0.,1.,0.)
        sumall = sum(msk.flat) # Collapse over z dimension.
        tmp = sum(msk,0) # Collapse over z dimension.
        x_centroid = dot(arange(self.xdim).astype(float),sum(tmp,0))/sumall
        y_centroid = dot(arange(self.ydim).astype(float),sum(tmp,1))/sumall
        z_centroid = dot(arange(self.zdim).astype(float),sum(reshape(msk,\
                                [self.zdim, self.ydim*self.xdim]),1))/sumall
        ix_centroid = int(x_centroid + .5)
        iy_centroid = int(y_centroid + .5)
        iz_centroid = int(z_centroid + .5)

        print "XYZ centers of mass: %f, %f, %f" % \
                                (x_centroid,y_centroid,z_centroid)
        print "XYZ centers of mass coordinates: %d, %d, %d" % \
                                (ix_centroid,iy_centroid,iz_centroid)
#        print "Value of phase difference at center of mass: %f" % \
#                        self.fmap[iz_centroid,iy_centroid,ix_centroid]
        ctr_value = self.fmap[iz_centroid,iy_centroid,ix_centroid]
        self.fmap = msk*(self.fmap - ctr_value)

    def NyquistMask(self, data):
        ydim, xdim = data.shape
        difx = zeros([ydim,xdim], float)
        dify = zeros([ydim,xdim], float)
        difxy = zeros([ydim,xdim], float)
        difx[1:,:] = diff(data, 1, 0)
        dify[:,1:] = diff(data, 1, 1)
        difxy[:,1:] = diff(difx, 1, 1)
        deriv = difx + dify + difxy

        mask = where(abs(deriv) > math.pi, 1, 0)
        ORDER = 9
        struct = ones([ORDER, ORDER], float)
        mask = binary_dilation(mask,struct, 1)
        mask = binary_erosion(mask, struct, 1)

        return mask

    def WriteFieldmap(self):
        self.hdr_out['filetype'] = 'n+1'
        self.hdr_out['mdim'] = 1

#        self.hdr['num_voxels'] = prod(hdr['dims'][:hdr['ndim']])
        writefile(self.fmap_file, self.fmap, self.hdr_out)
        print "Field map written to fmap_file: %s" % self.fmap_file

#       Write coarse mask.
#        hdr_mask = self.hdr_out.copy()
#        hdr_mask['datatype'] = 'short'
#        writefile(self.coarse_mask_file, self.coarse_mask, hdr_mask)


    def CleanUp(self):
        if not self.opts.debug:
            self.tmp.Clean()
#            cmd = "rm -rf %s" % self.tmpdir
#            execCmd(cmd)

def make_fieldmap():

    try:
        fmap = MakeFieldmap()
    except (RuntimeError, SyntaxError), errmsg:
        sys.stderr.write('\n%s\n%s\n' % (errmsg, except_msg()))
        sys.exit(1)

    try:
        fmap.CheckPaths()
        fmap.SetupFSL()
        fmap.SetupAFNI()
#        fmap.FindFieldmapData()
        fmap.ReadFieldmapData()
        fmap.CheckEchoTimes()
        fmap.GetRawPhase()

        # Register magnitude images to anatomical.
        if fmap.anatfile is not None:
            fmap.RegisterFmapToT1High()
        fmap.UnwrapPhase()
        fmap.EditMask()
        fmap.CreateFieldmap()
        fmap.WriteFieldmap()
        if not fmap.opts.debug:
            fmap.CleanUp()
    except RuntimeError, err:
#        sys.stderr.write(err.errmsg)
        errstr = except_msg()
        sys.stderr.write(errstr)
        fmap.CleanUp()
        sys.exit(1)
    except:
        sys.stderr.write(except_msg('make_fmap'))
        fmap.CleanUp()
        sys.exit(1)
    

if __name__ == '__main__':
    make_fieldmap()
