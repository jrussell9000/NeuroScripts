#!/usr/bin/env python

ID = "$Id: jmo $"[1:-1]

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
import time
from optparse import OptionParser
from subprocess import Popen, PIPE

from numpy import zeros, float, where, sqrt, array, nonzero, ones
from scipy.ndimage import gaussian_filter

from file_io import Wimage, writefile
from wbl_glm import Data, DesignMatrix, MotionData
from wbl_util import GetTmpSpace, except_msg
import constants as c
#from gelib import GeDatabase


class SNR():

    def __init__(self):
        self.GetOptions()

    def GetOptions(self):
        usage = 'Usage: get_snr epi_filename1, epi_filename2 ...\n' + \
                'The input EPI can be in dicom, nifti or brik format.\n' + \
                'Enter --help for more info.'
        optparser = OptionParser(usage)
        optparser.add_option( "-v", "--verbose", action="store_true", \
                dest="verbose", help='Print stuff to screen.')
        optparser.add_option( "", "--cross-slice", action="store_true", \
                dest="cross_slice", \
                help='Compute through-slice component of motion variance.')
        optparser.add_option( "", "--mean-only", action="store_true", \
                dest="mean_only", \
                help='Only save the mean SNR, not the entire SNR image.')
        optparser.add_option( "", "--correct-motion", action="store_true", \
                dest="correct_motion", help='Correct motion using 3dvolreg.')
        optparser.add_option( "-s", "--skip", action="store",  \
                dest="skip",default=0, type=int, \
                help="Number of frames to skip. Default=3")
        optparser.add_option( "", "--fwhm", action="store",  \
                dest="fwhm",default=0., type=float, \
                help="FWHM of Gaussian smoothing filter.")
        optparser.add_option( "", "--min-SNR", action="store",  \
                dest="min_SNR",default=25., type=float, \
                help="Minimum SNR to consider as part of image.")
        optparser.add_option( "", "--percentile-min", action="store",  \
                dest="min_percentile",default=0., type=float, \
                help="Mask out voxels with SNRs of percentile rank lower than this value. Range: 0-100, default=0 (no mercentile mask)  ")
        optparser.add_option( "", "--max-legendre", action="store",  \
                dest="max_legendre",default=1, type=int, \
                help="Maximum order of Legendre polynomial. Default=1")
        optparser.add_option( "", "--prefix", action="store",  \
                dest="prefix",default=None, type=str, \
                help="Prefix for output file names.")
        optparser.add_option( "", "--filetype", action="store",  \
                dest="filetype",default='nii', type=str, \
                help='Output file type. Takes value of "brik" or "nii".')
        optparser.add_option( "", "--save-all", action="store_true", \
                dest="save_all", help='Write mean and std. dev. images too.')
        optparser.add_option( "", "--sdevz", action="store_true", \
                dest="save_sdevz", help='Save standard deviation of motion.')
        optparser.add_option( "", "--censor-file", action="store", \
                dest="censor_file", type=str, default=None, \
                help='Save standard deviation of motion.')
        optparser.add_option( "", "--tmpdir", action="store", type='str', \
                dest="tmpdir", default=None, help='tmp directory.')
        optparser.add_option( "", "--mtnfile", action="store",  \
                dest="mtnfile",default=None, type=str, \
                help='File to which motion covariates are stored.')
        opts, args = optparser.parse_args()

        if len(args) != 1:
            print usage + '\n'
            sys.exit(1)

        self.input_file = args[0]
        self.skip = opts.skip
        self.correct_motion = opts.correct_motion
        self.mean_only = opts.mean_only
        self.verbose = opts.verbose
        self.cross_slice = opts.cross_slice
        self.max_legendre = opts.max_legendre
        self.fwhm = opts.fwhm
        self.min_percentile = opts.min_percentile
        self.save_all = opts.save_all
        self.filetype = opts.filetype
        self.save_sdevz = opts.save_sdevz
        self.censor_file = opts.censor_file
        self.min_SNR = opts.min_SNR
        if opts.tmpdir is None:
            self.tmpdir = None
            self.noclean = False
        else:
            self.tmpdir = opts.tmpdir
            self.noclean = True
        if opts.mtnfile is None:
            self.mtnfile = None
        else:
            self.mtnfile = os.path.abspath(opts.mtnfile)
            self.mtnfile = self.mtnfile.replace('_mtn.txt','')
            self.mtnfile = self.mtnfile.replace('.txt','')
            self.mtnfile += '_mtn.txt'
#        if opts.mtnfile.endswith('.txt'):
#            self.mtnfile = os.path.abspath(opts.mtnfile)
#        else:
#            self.mtnfile = '%s.txt' % os.path.abspath(opts.mtnfile)

        if opts.prefix is None:
            self.prefix = self.input_file.split('.nii')[0]
            self.prefix = self.prefix.split('+orig')[0]
            self.prefix = self.prefix.split('.img')[0]
            self.prefix = self.prefix.split('.hdr')[0]
            self.prefix += '_snr'
        else:
            self.prefix = opts.prefix

        if self.censor_file is not None:
            f = open(self.censor_file, 'r')
            self.censor = array(f.read().split()).astype(float)
            f.close()
        else:
            self.censor = None

        self.tmp = GetTmpSpace(500)
        self.tmpdir = self.tmp.tmpdir

    def ReadData(self):
#       Read images from disk
        if self.verbose:
            print 'Reading data'
        self.data = Data(self.input_file, correct_motion=self.correct_motion, \
             tshift=False, verbose=self.verbose, tmpdir=self.tmpdir, \
             mask_thresh=.01, mtnfile=self.mtnfile, skip=self.skip, \
             censor=self.censor)
        self.xsize = self.data.xsize

    def ComputeSnr(self):
        self.ReadData()
        self.mean_rawsnr, self.mean_maskedsnr, self.signal, self.sdev, \
        self.snr = self.data.ComputeSnr(self.fwhm, self.min_SNR, \
                        self.min_percentile, max_legendre=self.max_legendre)

    def GetMotionSdev(self):
        fname = self.data.epifiles[0]
        if self.correct_motion:
            if self.mtnfile is None:
                self.mtnfile = self.data.mtnfile
            elif self.mtnfile !=  self.data.mtnfile:
#               Put motion parameters in the right place
                cmd = 'cp %s %s' % (self.data.mtnfile, self.mtnfile)
                p = Popen(cmd, shell=True)
                sts = os.waitpid(p.pid, 0)
        else:
            mtnfile = fname.replace('.nii','')
            mtnfile = mtnfile.replace('+orig','')
            self.mtnfile = '%s_mtn.txt' % mtnfile.replace('+orig','')
            self.data.Volreg(self.data.epifiles[0], mtnfile=self.mtnfile)

#       Now compute the variance from the motion estimates.
        md = MotionData(self.mtnfile, cross_slice=self.cross_slice)
        self.gradient_mag = sqrt((md.gradient**2).sum(axis=1))
        self.sigmaz = md.gradient.std()
        

    def WriteSnr(self):
        hdr = self.data.w[0].hdr.copy()
        if self.save_all:
            hdr['tdim'] = 3
            hdr['dims'][3] = 3
            out = zeros([3, self.data.xyzdim], float)
            out[0,...] = self.data.PutVoxels(self.signal)
            out[1,...] = self.data.PutVoxels(self.sdev)
            out[2,...] = self.data.PutVoxels(self.snr)
        else:
            hdr['tdim'] = 1
            hdr['dims'][3] = 1
            out = self.data.PutVoxels(self.snr)
        hdr['filetype'] = self.filetype
        hdr['datatype'] = 'float'
        writefile(self.prefix, out, hdr)
        if self.verbose:
            print 'SNR written to %s' % self.prefix 

    def Cleanup(self):
        if not self.noclean:
            self.tmp.Clean()

def snr():
    sn = SNR()
    try:
        sn.ComputeSnr()
        if not sn.mean_only or sn.save_all:
            sn.WriteSnr()
        if sn.verbose:
            output_text = 'raw_snr:\t%f\tmasked_snr: %f' % (sn.mean_rawsnr, sn.mean_maskedsnr)
        else:
            output_text = '%f\t%f' % (sn.mean_rawsnr, sn.mean_maskedsnr)
        if sn.save_sdevz:
            sn.GetMotionSdev()
            output_text = '%s\t%f' % (output_text, sn.sigmaz)
            if sn.verbose:
                print output_text
        if sn.prefix is None:
            sys.stdout.write(output_text)
        else:
            f = open('%s.txt' % sn.prefix, 'w')
            f.write(output_text)
            f.close()
    except KeyboardInterrupt:
        sn.Cleanup()
        sys.exit(0)
    finally:
        sn.Cleanup()

if __name__ == '__main__':
    snr()

