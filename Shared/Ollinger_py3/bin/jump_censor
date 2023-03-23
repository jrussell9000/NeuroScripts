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


import os
import sys
from numpy import zeros, float, int, short, float32, arange, prod, array, \
            dot, sqrt, prod, arccos, sin, ones, where
from optparse import OptionParser
import matplotlib
#try:
#    matplotlib.use('WxAgg')
#except:
matplotlib.use('Agg')
from matplotlib.pylab import subplot, show, plot, xlabel, ylabel, connect, \
            savefig, xlim, ylim, ioff, isinteractive
from math import log10

from file_io import Wimage, writefile
from wbl_glm import  MotionData
from wbl_util import GetTmpSpace
from subprocess import Popen, PIPE

def mat2R(mat1d):

    R = zeros(16, float)
    for i in range(12):
        R[i] = float(mat1d[i])
    R = R.reshape([4,4])
    R[3,:] = array([0., 0., 0., 1.])
    return R

def write_line(fall, time, line):
    fall.write('%9.3f' % time)
    params = []
    for value in line:
        if isinstance(value, str):
            value = float(value)
        params.append(value)
        fall.write('\t%9.4f' % value)
    fall.write('\n')
    return params

class JumpMotion():

    def __init__(self):
        self.image = None
        self.GetOptions()
        self.gradient_mag = None
        self.censor = None
        self.Init()

    def GetOptions(self):
        usage = '\njump_censor [options] <input_file>\n' + \
            '\t<input_file> has two forms: (1) an EPI time-series in either\n'+\
            '\t    brik or nifti format; or (2) a text file of the motion \n' +\
            '\t    parameters written by 3dvolreg that ends with the \n' + \
            '\t    substring "_mtn.txt"\n'  \
            '\tTwo files are written by default:\n' + \
            '\t    <stem>_censor.1D: A censor file compatible with AFNI\n' + \
            '\t    <stem>_censor_stats.txt: A one line text file containing ' +\
            'the std. dev.\n' + \
            '\t    of the motion and the fraction of frames censored\n' + \
            '\tIf the --interleave present, the following file is written:\n'+ \
            '\t    <stem>_il_mtn.txt: A file containing the interleaved ' + \
            '\tmotion parameters in the same\n\t        format as ' + \
            '\tfiles created withe -dfile option in AFNI.\n' + \
            '\tIf the --show-plot or --store-plot is present, the ' + \
            'following file is written:\n' + \
            '\t    <stem>_censor.png: A png file containing a plot of the ' + \
            '\tcensor file.\n' + \
            '\t<stem> is the file specified by <input_file> with the suffix stripped away.\n'+\
                '\nEnter jump_censor --help for options.\n'
        optparser = OptionParser(usage)
        optparser.add_option( "-c", "--cross-slice", action="store_true",  \
            dest="cross_slice",default=False, \
            help="Only consider motion across slices. Neglect in-plane motion.")
        optparser.add_option( "", "--interleave", action="store_true",  \
            dest="interleave",default=False, \
            help="De-interleave odd and even numbered slices to create" + \
            "frames with half as many slices at twice the time-intervals.")
        optparser.add_option( "-v", "--verbose", action="store_true",  \
            dest="verbose",default=None, help="Verbose mode.")
        optparser.add_option( "", "--store-plot", action="store_true",  \
            dest="store_plot",default=False, \
            help="Create plot of results and store as a png.")
        optparser.add_option( "", "--show-plot", action="store_true",  \
            dest="show_plot",default=False, \
            help="Create plot of results, store as a png, and " + \
                 "display to screen.")
        optparser.add_option( "-k", "--keep", action="store_true",  \
            dest="keep",default=None, help="Keep intermediate files.")
        optparser.add_option( "", "--threshold", action="store",  \
            type='float', dest="threshold",default=2., \
            help="Threshold for censoring in mm/half-frame. Default=2mm")
        optparser.add_option( "", "--prefix", action="store",  \
            type='str', dest="prefix",default=None, \
            help="Prefix for output files.")
        optparser.add_option( "", "--save-epi", action="store",  \
            type='str', dest="epi_fname",default='NULL', \
            help="Save motion-corrected EPI to filename.")
        optparser.add_option( "", "--label", action="store",  \
            type='str', dest="label", default=None, \
            help='Label identifying the data, e.g., "gonogo_run1".')
        opts, args = optparser.parse_args()

        if len(args) != 1:
#            optparser.error(usage)
            sys.stderr.write(usage)
            sys.exit(1)

        self.fname = args[0]
        if opts.prefix is None:
            self.prefix = self.fname.replace('_mtn.txt','')
            self.prefix = self.prefix.replace('.txt','')
            self.prefix = self.prefix.replace('.nii','')
            self.prefix = self.prefix.replace('.BRIK','')
            self.prefix = self.prefix.replace('.HEAD','')
            self.prefix = self.prefix.replace('+orig','')
        else:
            self.prefix = opts.prefix
        self.cross_slice = opts.cross_slice
        self.verbose = opts.verbose
        self.keep = opts.keep
        self.store_plot = opts.store_plot
        self.show_plot = opts.show_plot
        self.threshold = opts.threshold
        self.epi_fname = opts.epi_fname
        self.outdir = os.path.dirname(os.path.abspath(self.prefix))
        self.interleave = opts.interleave
        if opts.label is None:
            self.label = self.fname
        else:
            self.label = opts.label

    def Init(self):
        if self.fname.endswith('.txt'):
            self.text_file = True
            self.mtn_file = self.fname
            self.tmpdir = None
            self.tdim = None
            if self.fname.endswith('_il_mtn.txt') and \
                                    not self.interleave:
                sys.stderr.write('*** The data appear to be interleaved. Specify the --interleave option if it is. ***\n')
        else:
#           Use 3dvolreg to compute motion files.
            self.text_file = False
            self.tmp = GetTmpSpace(500)
            self.tmpdir = self.tmp()
            self.w = Wimage(self.fname)
            if self.w.hdr is None:
                raise RuntimeError('Could not open %s' % self.fname)
            self.xdim = self.w.hdr['xdim']
            self.ydim = self.w.hdr['ydim']
            self.zdim = self.w.hdr['zdim']
            self.tdim = self.w.hdr['tdim']
            self.xsize = self.w.hdr['xsize']
            self.ysize = self.w.hdr['ysize']
            self.zsize = self.w.hdr['zsize']
            self.TR = 2.

            if self.fname.endswith('.txt'):
                self.mtn_file = self.fname
            else:
                self.mtn_file = '%s/%s_mtn.txt' % \
                                  (self.outdir, os.path.basename(self.prefix))

    def Split(self):
        even = zeros([self.tdim,self.zdim/2,self.ydim,self.xdim],short)
        odd = zeros([self.tdim,self.zdim/2,self.ydim,self.xdim],short)
        even_slices = (2*arange(self.zdim/2)).tolist()
        odd_slices  = (2*arange(self.zdim/2) +1).tolist()
        if self.verbose:
            print 'Reading data ...'
        self.image = self.w.readfile(dtype=short)
        if self.image is None:
            raise RuntimeError('Could not open image.')
        for t in xrange(self.tdim):
            even[t,...] = self.image[t, even_slices,...]
            odd[t,...]  = self.image[t, odd_slices,...]

        hdr = self.w.hdr.copy()
        hdr['zdim'] = self.zdim/2
        hdr['tdim'] = self.tdim
        hdr['dims'][2] = self.zdim/2
        hdr['dims'][3] = self.tdim
#        hdr['numvox'] = prod(hdr['dims'])

        fname_even = '%s/%s_even' % (self.tmpdir, os.path.basename(self.prefix))
#        print 'Writing %s' % fname_even
        writefile(fname_even, even, hdr)
        self.mtn_file_even = self.VolReg(fname_even)

        fname_odd  = '%s/%s_odd' % (self.tmpdir, os.path.basename(self.prefix))
#        print 'Writing %s' % fname_odd
        writefile(fname_odd, odd, hdr)
        self.mtn_file_odd = self.VolReg(fname_odd)

    def VolReg(self, fname, fname_save='NULL'):
        matfile = '%s.aff12.1D' % fname
        mtnfile = '%s/%s_mtn.txt' % (self.tmpdir, os.path.basename(fname))
        if self.verbose:
            devnull = '>&/dev/null'
        else:
            devnull = ''
        cmd = '3dvolreg -prefix %s -twopass -verbose ' % fname_save + \
          '-base %s+orig[0] -dfile %s -1Dmatrix_save %s %s+orig %s' % \
                      (fname, mtnfile, matfile, fname, devnull)
        if self.verbose:
            print cmd
        p = Popen(cmd, shell=True)
        sts = os.waitpid(p.pid, 0)
        return mtnfile


    def GetMotionData(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()
        if self.tdim is None:
            if self.interleave:
                self.tdim = len(lines)/2
            else:
                self.tdim = len(lines)

        data = []
        for idx in xrange(len(lines)):
            words = lines[idx].split()
            for i in xrange(6):
                if idx == 0:
                    data.append([float(words[i+1])])
                else:
                    data[i].append(float(words[i+1]))
        for i in xrange(6):
            data[i] = array(data[i])
        return data

    def GetOffsets(self):
        """
        Find offset introduced by constant difference between the two 
        sets of parameters.
        """
        self.offsets = zeros(6, float)
        for i in xrange(6):
#           Interpolate even slices to odd slice times.
            xinterp = (self.even_data[i][:-1] + self.even_data[i][1:])/2.
            xdiff = self.odd_data[i][:-1] - xinterp
            mask = where(abs(xdiff-xdiff.mean()) < xdiff.std(), 1., 0.)
            self.offsets[i] = (mask*xdiff).sum()/mask.sum()

    def Interleave(self):
#       Read motion parameters and store in arrays.
        self.Split()
        self.even_data = self.GetMotionData(self.mtn_file_even)
        self.odd_data = self.GetMotionData(self.mtn_file_odd)
        self.GetOffsets()

        dt = self.TR/2.
        time = 0

        n_even = self.even_data[0].shape[0]
        n_odd = self.odd_data[0].shape[0]
        self.mtn_file = '%s_il_mtn.txt' % self.prefix
        if self.verbose:
            print 'Interleaved result: %s' % self.mtn_file
        fall = open(self.mtn_file, 'w')
        for idx in range(n_even):
            values = []
            for i in xrange(6):
                values.append(self.even_data[i][idx])
            params = write_line(fall, time, values)
            time += dt
            if idx < n_odd:
#                wds = odd_lines[idx].split()
                values = []
                for i in xrange(6):
                    values.append(self.odd_data[i][idx] - self.offsets[i])
                params = write_line(fall, time, values)
                time += dt
        fall.close()

    def PlotResults(self, data):
        tdim = data.shape[-1]
        if self.interleave:
            x0 = .5*arange(tdim)
        else:
            x0 = arange(tdim)
#       Top plot
        ioff()
        subplot(211)
        plot(x0, data,  marker = 'o', c='r', markersize=3)
        xlabel("Frame")
        ylabel("Gradient Magnitude (mm/second at 5cm radius)")

        subplot(212)
        tdim = self.censor.shape[-1]
        plot(arange(tdim), self.censor,  marker = 'o', c='r', markersize=3)
        xlabel("Frame")
        ylabel("Censor Mask")
        ylim(0., 1.1)

#       Save to png.
        savefig('%s_censor.png' % self.prefix, format='png')
        if self.show_plot:
            show()

    def ResliceSagToAxlCoefs(self):
        xydim = self.xdim*self.ydim
        xyzdim = xydim*self.zdim
        xzoom = self.zsize/self.ysize
        self.xdim_axl = int(self.zdim*xzoom)
        self.ydim_axl = self.xdim
        self.zdim_axl = self.ydim
        self.shp_axl = [self.zdim_axl, self.ydim_axl, self.xdim_axl]
        x1 = xyzdim - (((arange(self.xdim_axl)/xzoom).astype(int) + 1.)*xydim)
        x1 = x1.repeat(self.ydim_axl).reshape( \
                                [self.xdim_axl, self.ydim_axl]).transpose()
        y1 = arange(self.ydim_axl).repeat(self.xdim_axl).reshape(\
                                [self.ydim_axl, self.xdim_axl])
        self.axl_voxels = \
                    zeros([self.zdim_axl, self.ydim_axl, self.xdim_axl], int)
        xy = x1 + y1
        for z in xrange(self.zdim_axl):
            self.axl_voxels[z, :, :] = xy + (xydim - (z+1)*self.xdim)
        self.axl_voxels = self.axl_voxels.ravel().tolist()

    def ResliceSagToAxl(self, image):
        img = image.ravel().take(self.axl_voxels).reshape(self.shp_axl)[self.slice, :, :]
        x = image.ravel().take(self.axl_voxels).reshape(self.shp_axl)
        img = x[self.slice,:,:]
        return img

    def Display(self, slice, frame):
        if self.image is None:
            return
        self.slice = slice
        self.frame = frame
        img_slice = self.ResliceSagToAxl(self.image[frame, ...])
        shp = img_slice.shape
        try:
            from wbl_viewer import WblViewer
            self.have_wx = True
        except:
            self.have_wx = False
            return
        self.disp = WblViewer(redirect=False)
        self.disp.InitViewer(img_slice, ncol=1, title=self.fname, \
                        colors='gray')
        colormin = 0.
        colormax = .95*img_slice.max()
        self.disp.SetColorRange(colormin, colormax)
        annotations = { 0:{'text':'t: %d, z: %d' % (self.frame, self.slice)}}
        self.disp.Annotate(annotations)
        self.disp.Show()

    def Censor(self, threshold=1.):
        if self.verbose:
            print 'Threshold: %5.2f' % threshold
        if self.gradient_mag is None:
            raise RuntimeError(\
                    'gradient_mag must be computed before calling "Censor"')
        self.censor = ones(self.tdim)
        for t in xrange(self.gradient_mag.shape[0]):
            if self.gradient_mag[t] > threshold:
                if self.interleave:
                    t0 = t/2
                else:
                    t0 = t
                if t0+3 < self.tdim:
                    self.censor[t0:t0+3] = 0
                else:
                    self.censor[t0:] = 0
        censor_file = '%s_censor.1D' % self.prefix
        f = open(censor_file, 'w')
        for t in xrange(self.tdim):
            f.write('%d\n' % self.censor[t])
        f.close()
        self.censor_pct = 100.*(1. - self.censor.sum()/float(self.censor.shape[0]))
        if self.verbose:
            print 'Censor percentage: %5.2f%%' % self.censor_pct
            print 'Censor file written to %s' % censor_file

    def MotionStats(self):
        """
        Compute path length and the path derivative.
        """
        md = MotionData(self.mtn_file)
        self.path_length, self.gradient = md.ComputeMotionStats(cross_slice=self.cross_slice)
        self.gradient_mag = sqrt((md.gradient**2).sum(axis=1))
        self.sigmaz = self.gradient.std()

    def WriteResults(self):
        f = open('%s_censor_stats.txt' % self.prefix.replace('.txt',''), 'w')
        results = '%s\tsigmaz:\t%f\tFraction:\t%f' % \
                            (self.label, self.sigmaz, self.censor_pct/100.)
        f.write(results)
        if self.verbose:
            sys.stdout.write('%s\n\n' % results)
        f.close()
        if self.store_plot or self.show_plot:
            try:
                self.PlotResults(self.gradient_mag)
            except:
                sys.stderr.write('Plot not created in jump_censor\n')

    def Cleanup(self):
        if self.tmpdir is not None and not self.keep:
#            print '*** Did not clean up. ***'
            self.tmp.Clean()
#            cmd = '/bin/rm -r %s' % self.tmpdir
#            p = Popen(cmd, shell=True)
#            sts = os.waitpid(p.pid, 0)

    def GetMotionFiles(self):
        if self.text_file:
            self.GetMotionData(self.fname)
        elif self.interleave:
#           De-interleave odd and even slices, then re-interleave motion params.
            self.Interleave()
        else:
            self.VolReg(self.fname.replace('+orig',''), \
                                            fname_save=self.epi_fname)

def jump_censor():
    try:
        sm = JumpMotion()
        sm.GetMotionFiles()
        sm.MotionStats()
        sm.Censor(sm.threshold)
        sm.WriteResults()
    except (IOError, OSError), errmsg:
        sys.stderr.write('\n%s\n%s\n' % (errmsg, except_msg()))
        sm.CleanUp()
        sys.exit(1)

#    if sm.verbose:
#        sm.ResliceSagToAxlCoefs()
#        sm.Display(sm.zdim_axl/2, sm.tdim/2)
    sm.Cleanup()


if __name__ == '__main__':
    jump_censor()

