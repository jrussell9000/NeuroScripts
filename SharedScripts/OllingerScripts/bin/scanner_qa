#!/usr/bin/env python

ID = "$Id:$"[1:-1]

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

from numpy import zeros, ones, where, round, nonzero, arange, dot, outer, \
                  sqrt, float, float32, double
from numpy.linalg import inv

from scipy.ndimage.morphology import binary_erosion,binary_dilation
from scipy.signal import sepfir2d
from scipy.special import legendre
from scipy.ndimage.interpolation import zoom

from file_io import Wimage, writefile
from wbl_util import except_msg

from wbl_viewer import WblViewer

EXAMDB='/export/home1/waisman_software/exams/exam_index.pickle'

# Try to import library for ge database.
try:
    from gelib import GeDatabase
    have_gelib = True
except:
    have_gelib = False

RECT_FILT = 3. # Width of rect filter used in deviation computation.

class ScannerQA():
    """
    Compute QA metrics from MRI images.
    Metrics:
    1. TSNR: Ratio of temporal mean image to temporasl standard deviation. 
        Computed from an EPI time-series.

        Glover, G. (2004). Scanner Quality Assurance for Longitudinal or 
        Multicenter Studies. Proc. Int'l Soc Mag Reson Med Annual Meeting 
        11: 992.
=
    2. Deviation:The image is first eroded by 10 pixels to eliminate pixels 
        with edge and partial volume effects. It is then smoothed with a 
        3x3 rectangular filter and the value of the center voxel is defined 
        as c. Then the deviation at each voxel is computed as where di is the 
        deviation at voxel i, fi is the image value at voxel i, and denotes 
        the absolute value.

        Magnusson, P. and L. E. Olsson (2000). Image analysis methods for 
        assessing levels of image plane nonuniformity and stochastic noise 
        in a magnetic resonance image of a homogeneous phantom. 
        Med Phys 27(8): 1980-94.

    3. Polynomial fit: A set of  Legendre polynomials are fit to the data
        the fraction of variance for each is  printed.  (The 0th order 
        fit are subtracted first.
    """

    def __init__(self):
        self.deviation = None
        self.mean_deviation = None
        self.min_deviation = None
        self.max_deviation = None
        self.spinecho_snr = None
        self.GetOptions()
        self.Init()

    def Init(self):
        self.ReadEpiImage(self.epi_file)
        self.ComputeMask()
        self.mean_sfnr = -1.
        self.legndre_pct_label = ''

    def Process(self):
        self.FitLegendre()
        self.ComputeTSNR()
        self.ComputeMeanCorrected()
        if self.spinecho_file is not None:
            self.ReadSpinEcho()
            self.SpinEchoSNR()
            self.ComputeDeviation(self.spinecho, self.wse.hdr)
        self.WriteOutput()

    def GetOptions(self):
        usage = 'Usage: scanner_qa <epi_filename>\n' + \
                'The input EPI can be in dicom, nifti or brik format.\n' + \
                'Enter --help for more info.'
        optparser = OptionParser(usage)
        optparser.add_option( "-v", "--verbose", action="store_true", \
                dest="verbose", help='Print stuff to screen.')
        optparser.add_option( "", "--noshow", action="store_true", \
                dest="noshow", help="Don't write to GUI.")
#        optparser.add_option( "", "--write-images", action="store_true", \
#                dest="write_images", help='Write statistical images to prefix')
        optparser.add_option( "-q", "--quiet", action="store_true", \
                dest="quiet", help='Print stuff to screen.')
        optparser.add_option( "", "--terse", action="store_true",  \
                dest="terse", default=False, \
                help="Write results to stdout.")
        optparser.add_option( "-s", "--skip-frames", action="store",  \
                dest="skip",default=4, type=int, \
                help="Number of frames to skip. Defaults to 4.")
        optparser.add_option( "", "--spinecho", action="store",  \
                dest="spinecho_file",default=None, type=str, \
                help="File containing a two-frame spin-echo image.")
        optparser.add_option( "", "--legendre-order", action="store",  \
                dest="legendre_order",default=8, type=int, \
                help="Maximum order of legendre polynomial regressors.")
        optparser.add_option( "", "--prefix", action="store",  \
                dest="prefix",default=None, type=str, \
                help="Prefix for output file names.")
  #      optparser.add_option( "", "--epi", action="store",  \
  #              dest="epi_bases",default=None, type=str, \
  #              help='A comma-delimited list of basenames for epis.  If ' + \
  #              'this option is chosen, the input_file argument should ' + \
  #              'be the topmost directory of the tree to be searched. '  + \
  #              'All directories will be searched for time-series files ' + \
  #              'with names starting with one of the basenames specified ' + \
  #              'by this argument.')
        opts, args = optparser.parse_args()

        if len(args) != 1:
            print usage + '\n'
            sys.exit(1)

    #    if args[0].isdigit():
#   #        Must be running on the scanner.  Find the EPI data.
    #        examno = int(args[0])
#   #        Input argument is an exam number.
    #        self.input_file = self.GetExamPath(args[0])
#   #        Initialize database object.
    #        self.gedb = GeDatabase()
#   #        Read exams.
    #        self.gedb.ReadExamIndex()
    #        if not self.gedb.exams.has_key(examno):
    #            self.gedb.UpdateExamIndex(examno)
    #        seriesdirs = self.gedb.exams.get(examno, None)
    #        if seriesdirs is None:
    #            raise RuntimeError('Could not find exam number %d' % examno)
    #        self.epi_series = []
    #        for seriesdir in seriesdirs:
    #            w = Wimage(seriesdir)
    #            if 'epi' in w.hdr['native_header']['PulseSequenceName'].lower()\
    #                and w.hdr['tdim'] > 5:
    #                self.epi_series.append(seriesdir)
    #        if len(epi_series) == 0:
    #            raise RuntimeError('Could not find EPI time series for exam %d' % examno)
    #        elif len(epi_series) > 1:
    #            print 'Found %d EPI time-series, using first one.'
    #        else:
    #            print 'Found EPI time-series'
    #        self.input_file = epi_series[0]

    #    else:
        self.epi_file = args[0]
        self.topdir = os.path.dirname(self.epi_file)

        self.skip = opts.skip
        self.quiet = opts.quiet
        self.verbose = opts.verbose
        self.noshow = opts.noshow
        if self.noshow:
            import matplotlib
            matplotlib.use('Agg')
        self.terse = opts.terse
        self.legendre_order = opts.legendre_order
#        self.write_images = opts.write_images
        self.spinecho_file = opts.spinecho_file

        if opts.prefix is None:
            self.prefix = self.epi_file.replace('.nii.gz','')
            self.prefix = self.prefix.replace('.nii','')
            self.prefix = self.prefix.replace('+orig.BRIK','')
            self.prefix = self.prefix.replace('+orig.HEAD','')
            self.prefix = self.prefix.replace('+orig','')
        else:
            self.prefix = opts.prefix
        if self.prefix.endswith('/'):
            self.prefix = self.prefix[:-1]
 #       if opts.epi_bases is None:
 #           self.epi_bases = None
 #           self.topdir = None
 #           if opts.prefix is None:
 #               self.prefix = self.input_file.split('.nii')[0]
 #               self.prefix = self.prefix.split('+orig')[0]
 #               if self.prefix.endswith('/'):
 #                   self.prefix = self.prefix[:-1]
 #           else:
 #               self.prefix = opts.prefix
 #       else:
 #           if opts.prefix is None:
 #               sys.stderr.write('\nThe --prefix option must be given if the --epi option is used.\n')
 #               sys.exit(1)
 #           self.prefix = opts.prefix
 #           self.epi_bases = opts.epi_bases.split(',')

    def GetDicomDir(self, exam_number):
        gedb = GeDatabase(examdb=EXAMDB)
        gedb.ReadExamIndex()
        gedb.UpdateExamIndex()
        if not gedb.exams.haskey(examno):
            raise RuntimeError('Exam not found in database.')
        sernos = gedb.exams[examno]['series_dirs'].keys()
        sernos.sort
        for serno in sernos:
            dname = gedb.exams[examno]['series_dirs'][serno]
            if gedb.exams[examno]['series_lgths'][dname] > 49:
                print 'Found series # %d with %d frames.' % \
                        (serno, gedb.exams[examno]['series_lgths'][dname])
                return dname

    def ReadSpinEcho(self):
        self.wse = Wimage(self.spinecho_file)
        self.spinecho = self.wse.readfile()
        if self.wse.hdr['tdim'] != 2:
            raise RuntimeError('Spin echo data must containt two frames.')

    def ReadEpiImage(self, input_file):
        self.w = Wimage(input_file)
        self.hdr = self.w.hdr
        if self.hdr is None:
            raise RuntimeError('Could not read header from %s' % input_file)

        self.xdim = self.hdr['xdim']
        self.ydim = self.hdr['ydim']
        self.zdim = self.hdr['zdim']
        self.tdim = self.hdr['tdim']
        self.xydim = self.xdim*self.ydim
        self.xyzdim = self.xydim*self.zdim
        self.xsize = self.hdr['xsize']
        self.ysize = self.hdr['ysize']
        self.zsize = self.hdr['zsize']
        self.tdim -= self.skip
        self.img_shp = [self.zdim, self.ydim, self.xdim]

#       Compute mean and mask.
        self.ComputeMask()
#       Compute mask that covers the ghost.
        self.GhostMask(self.mask)

#       Read image and strip out image.
        if self.verbose:
            print 'Reading images ...'
        gscl = self.xyzdim/(self.ghost_mask.sum()*self.mean.sum())
        self.img_strip = zeros([self.tdim, self.zdim,self.nvox_slc], float32)
        ghost_out = []
        sum = zeros(self.xyzdim, float)
        for t in xrange(self.tdim):
            if self.verbose:
                sys.stdout.write('.')
                sys.stdout.flush()
            img = self.w.readfile(frame=t+self.skip, dtype=float32)
            self.ghost_frac[t] = 100.*gscl*(self.ghost_mask*img).sum()
            ghost_out.append('%s\t%6.3f\n' % (t, self.ghost_frac[t]))
            img = img.reshape([self.zdim, self.xydim])
            sum += img.reshape(self.xyzdim)
            for z in xrange(self.zdim):
                self.img_strip[t,z,:] = img[z,:].take(self.slc_voxels)
        sys.stdout.write('\n')
        if not self.terse:
            self.WriteText(ghost_out, '_ghost_frac')

#       Recompute the mask and mean from entire time-series.
#        self.mean = sum/self.tdim
#        self.ComputeMask()

    def ComputeMask(self):
#       First compute mean over first 20 frames.
        tmax = min(20, self.tdim)
        self.mean = self.w.readfile(frame=self.skip, dtype=float32)
        for t in xrange(tmax-1):
            self.mean += self.w.readfile(frame=self.skip+1, dtype=float32)
        self.mean /= tmax
        mean = self.mean.reshape([self.zdim, self.xydim])
        mask1 = where(mean < .20*mean.max(), 0., 1.)
        voxmean = (mean*mask1).sum()/mask1.sum()
        self.mask = where(mean < .25*voxmean, 0., 1.)
        self.mask = binary_erosion(self.mask.reshape(self.img_shp), \
                        ones([3, 3, 3]).astype(float))
        slice_mask = where(self.mask.sum(0) > 0, 1., 0.).ravel()
        self.slc_voxels = nonzero(slice_mask)[0]
        self.nvox_slc = slice_mask.sum()
        self.nvox = self.zdim*self.nvox_slc

        self.mask_strip = zeros([self.zdim, self.nvox_slc], float)
        tmp = ones(self.nvox_slc, float)
        self.mask = self.mask.reshape([self.zdim, self.xydim])
        for z in xrange(self.zdim):
            self.mask_strip[z,:] = self.mask[z,:].take(self.slc_voxels)
        self.mask_strip = self.mask_strip.ravel()
        self.mask_voxels = nonzero(self.mask_strip)[0]
        self.mask = self.mask.reshape([self.xyzdim])

    def ComputeTSNR(self):
        data = self.residuals
        data = data.reshape([self.tdim, self.zdim, self.nvox_slc])
        self.sdev = zeros([self.zdim, self.xydim], float)
        self.mean = zeros([self.zdim, self.xydim], float)
        for z in xrange(self.zdim):
            sdev1 = data[:,z,...].std(axis=0)
            mean1 = self.img_strip[:,z,...].mean(axis=0)
            self.sdev[z,...].put(self.slc_voxels, sdev1)
            self.mean[z,...].put(self.slc_voxels, mean1)
        self.sdev = self.sdev.reshape(self.xyzdim)
        self.mask = self.mask.reshape(self.xyzdim)
        self.mean = self.mean.reshape(self.xyzdim)
        mask = self.mask*where(self.sdev > 0, 1., 0.)
        self.sfnr = mask*self.mean/(self.sdev + 1. - mask)
        self.mean_value = (mask*self.mean).sum()/mask.sum()
        self.mean_sfnr = (mask*self.sfnr).sum()/mask.sum()
        print 'Mean TSNR: %7.2f' % self.mean_sfnr

    def ComputeMeanCorrected(self):
        self.mean_corrected = zeros(self.tdim, float)
        img_strip = self.img_strip.reshape([self.tdim, self.nvox])
        meanvox = img_strip.mean(0).take(self.mask_voxels)
        for t in xrange(self.tdim):
            img = img_strip[t,:].take(self.mask_voxels)
            self.mean_corrected[t] = 100.*((img - meanvox)/meanvox).mean()

    def SpinEchoSNR(self):
        if self.spinecho.ndim < 4 and self.spinecho.shape[0] != 2:
            raise RuntimeError( \
            'Fast spin-echo image must have to frames at the same position.')
        sumimg = self.spinecho.sum(0)
        mask = where(sumimg > .5*sumimg.max(), 1., 0.).squeeze()
        mask = binary_erosion(mask, ones([5, 5])).ravel()
        voxels = nonzero(mask)[0]
        diff = self.spinecho[1,:,:,:] - self.spinecho[0,:,:,:]
        self.spinecho_snr = sumimg.take(voxels).mean()/ \
            ((self.spinecho[1,...] - self.spinecho[0,...]).take(voxels).std())

    def ComputeDeviation(self, image, hdr):
        xdim, ydim, zdim, tdim = hdr['dims'][:4]
        xsize, ysize, zsize = hdr['sizes'][:3]
#       Extract central slice.
        if zdim == 1 and tdim == 2:
            img = image.mean(0)
            img_shp = img.shape
            mean_ctr = zeros(img_shp, float)
            mean_ctr[:,:,:] = img
        else: 
            mean_ctr = image[zdim/2, :, :]
        img_shp = mean_ctr.shape
        # Only look at the central 12 cm of the phantom.
        nskip = zdim - int(round(120./zsize))
#       Smooth each slice.
        mean_smooth = zeros(img_shp, float)
        krnl = ones(RECT_FILT).astype(float)/3.
        for z in xrange(nskip/2, zdim-nskip/2):
            mean_smooth[z] = sepfir2d(img[z,:,:], krnl, krnl)/RECT_FILT**2
        sm_nvox = (where(mean_smooth > 0, 1., 0.)).sum()
        sm_mean = mean_smooth.sum()/sm_nvox
#       Threshold image at 25% of the mean image value then dilate and erode.
        dev_mask = where(mean_smooth > .25*sm_mean, 1., 0.)
        eroded_dev_mask = zeros(img_shp, int)
        for z in xrange(nskip/2, zdim-nskip/2):
            eroded_dev_mask[z,...] = binary_erosion(dev_mask[z,...], ones([5, 5]))
        x0, y0 = self.FindCenter(mean_ctr.squeeze())
        meanval = mean_smooth[zdim/2, y0, x0]
        self.deviation = abs(100.*eroded_dev_mask*\
                                    (mean_smooth - meanval)/meanval).squeeze()
        nzvox = nonzero(eroded_dev_mask.ravel())[0]
        devs_nonzero = self.deviation.ravel().take(nzvox)
        self.mean_deviation = devs_nonzero.mean()
        self.min_deviation = devs_nonzero.min()
        self.max_deviation = devs_nonzero.max()
        self.WriteFile(self.deviation, '_deviation')

    def GhostMask(self, image_mask):
        """
        Compute ratio of the integral over the region of the Nyquist ghost
        not covered by the image to the integral over the image.
        """
#        if self.verbose:
#            print 'Computing ghost fraction ...'
        eroded_mask = binary_erosion(image_mask.reshape(self.img_shp), \
                        ones([5, 5, 5]).astype(float)).reshape([self.xyzdim])
        dilated_mask = binary_dilation(image_mask.reshape(self.img_shp), \
                        ones([9, 9, 9]).astype(float)).reshape([self.xyzdim])
        if self.hdr['plane'] == 'sagittal':
            dim = self.xdim
            axis = 'row'
        else:
            dim = self.ydim
            axis = 'col'
        self.ghost_mask = self.Shift(eroded_mask, dim/2, axis)*(1. - dilated_mask)
        self.ghost_mask = self.ghost_mask.reshape([self.zdim, self.ydim, self.xdim])
        self.ghost_frac = zeros(self.tdim, float)
#        self.WriteFile(ghost_mask, '_ghost_mask')

  #  def GhostFraction(self, image):
  #      """
  #      Compute ratio of the integral over the region of the Nyquist ghost
  #      not covered by the image to the integral over the image.
  #      """
  #      scl = self.nvox_tot/(self.ghost_mask.sum()*self.mean.sum())
  #      lines = []
  #      for t in xrange(self.tdim):
  #          self.ghost_frac[t] = 100.*scl*(self.ghost_mask*self.image[t,:]).sum()
  #          lines.append('%s\t%6.3f\n' % (t, self.ghost_frac[t]))
  #      if not self.terse:
  #          self.WriteText(lines, '_ghost_frac')

    def Shift(self, image, shft, axis='row'):
        new = zeros(self.img_shp, float)
        image = image.reshape(self.img_shp)
        if(axis == 'row'):
            new[:, :, shft:] = image[:, :, :-shft]
            new[:, :, :shft] = image[:, :, -shft:]
        elif(axis == 'col'):
            new[:, shft:, :] = image[:, :-shft, :]
            new[:, :shft, :] = image[:, -shft:, :]
        return new.reshape([self.xyzdim])


    def FitLegendreSlice(self, image): #, mask):
        """
        Fit Legendre polynomials up to and including max_order.
        """
        M = self.legendre_order + 1
        self.poly_order = self.legendre_order
        self.A = zeros([self.tdim, M], float)
        c = (self.tdim-1.)/2.
        x = 2.*(arange(self.tdim).astype(float))/(self.tdim - 1.) - 1.
        for m in xrange(M):
            xpow = ones(self.tdim)
            coeffs = legendre(m)
            for i in xrange(m+1):
                self.A[:,m] += coeffs[i]*xpow
                xpow *= x
        ATAm1 = inv(dot(self.A.transpose(),self.A))
        ATAm1AT = dot(ATAm1, self.A.transpose())
        self.beta_lgndr = zeros([M, self.nvox_slc], float)
        legndre_frac = zeros([M-1, self.nvox_slc], float)
        data = zeros(image.shape, float)
        data[...] = image[...]
        self.legndre_frac_str = []
        self.legndre_frac_mean = zeros([M-1], float)
        self.legndre_pct_label = ''
        for m in xrange(M):
            self.beta_lgndr[m,:] = dot(ATAm1AT[m, :], image)
            residual1 = data - outer(self.A[:,m], self.beta_lgndr[m,:])
            if m == 0:
                Spartial = (residual1**2).sum(axis=0)
                data = residual1
                residuals = data - outer(self.A[:,m], self.beta_lgndr[m,:])
            else:
                Scomplete = (residual1**2).sum(axis=0)
                msk = where(Spartial > 0., 1., 0.)
                legndre_frac[m-1,:] = 100.*msk*(Spartial - Scomplete)/(Spartial+1-msk)
                residuals = residuals - outer(self.A[:,m], self.beta_lgndr[m,:])
                lfrac = self.legndre_frac[m-1,:].sum()/self.nvox
#                print 'Order: %d, Pct zero-mean variance: %6.3f' % (m, lfrac)
        return legndre_frac, residuals

    def FitLegendre(self):
        if self.verbose:
            print 'Fitting Legendre polynomials ...'
        self.residuals = zeros([self.tdim, self.zdim, self.nvox_slc], float)
        self.legndre_frac = zeros([self.legendre_order, self.zdim, self.nvox_slc], float)
        for z in xrange(self.zdim):
            x = self.FitLegendreSlice(self.img_strip[:,z,...]) #, msk[z,...])
            self.legndre_frac[:,z,...] = x[0]
            self.residuals[:,z,...] = x[1]
        self.residuals = self.residuals.reshape([self.tdim, self.zdim*self.nvox_slc])

        for m in xrange(self.legendre_order):
            lfrac = self.legndre_frac[m,:].sum()/self.nvox - \
                            100./(float(self.tdim) + self.legendre_order)
            print 'Order: %d, Excess zero-mean variance: %6.3f' % (m, lfrac)
            self.legndre_frac_str.append('%d %6.2f  ' % (m+1, lfrac))
            self.legndre_frac_mean[m] = lfrac
            self.legndre_pct_label += '%5.2f%%, ' % lfrac
        self.legndre_pct_label.replace('  ',' ')
        self.legndre_pct_label.replace('  ',' ')
        self.legndre_pct_label =  self.legndre_pct_label[:-2]

       

    def FindCenter(self, image):
#       Define center of phantom as its center of mass.
        sumimg = sum(image.flat)
        s = image.shape
        ydim = s[0]
        xdim = s[1]
        sumx = 0
        for x in range(xdim):
            sumx = sumx + x*sum(image[:,x])
        x0 = int(round(sumx/sumimg))
        sumy = 0
        for y in range(ydim):
            sumy = sumy + y*sum(image[y,:])
        y0 = int(round(sumy/sumimg))
        return (x0,y0)

    def WriteText(self, lines, tag):
        print 'Writing to %s%s.txt' % (self.prefix, tag)
        f = open('%s%s.txt' % (self.prefix, tag), 'w')
        f.writelines(lines)
        f.close()

    def WriteFile(self, image, tag):
        print 'Writing image to %s%s.nii' % (self.prefix, tag)
        hdr = self.hdr.copy()
        if image.ndim == 2:
            xdim = image.shape[1]
            ydim = image.shape[0]
            zdim = 1
            tdim = 1
        elif image.ndim == 3:
            xdim = image.shape[2]
            ydim = image.shape[1]
            zdim = image.shape[0]
            tdim = 1
        else:
            xdim = image.shape[3]
            ydim = image.shape[2]
            zdim = image.shape[1]
            tdim = image.shape[0]
        hdr['tdim'] = tdim; hdr['zdim'] = zdim
        hdr['ydim'] = ydim; hdr['xdim']=xdim
        hdr['dims'] = [xdim, ydim, zdim, tdim, 1]
        hdr['filetype'] = 'nii'
        writefile(self.prefix+tag, image, hdr)

    def PackAndWrite(self):
        qa_images = zeros([3] + self.img_shp, float)
        qa_images[0,...] = self.mean.reshape(self.img_shp)
        qa_images[1,...] = self.sdev.reshape(self.img_shp)
        qa_images[2,...] = self.sfnr.reshape(self.img_shp)
#        qa_images[3,...] = self.deviation.reshape(self.img_shp)
        self.WriteFile(qa_images, '_stats')

    def Zoom(self, image, output_dim, xpad=False):
        """
        Zoom a 2D image.
        """
        dim_in = image.shape[0]
        zoom_factor = output_dim/dim_in
        if xpad > 0:
            yd = image.shape[0]
            xd = image.shape[1]
            xpad = (yd - xd)/2
            img = zeros([image.shape[0], image.shape[0]])
            img[:,xpad:xpad+xd] = image
        else:
            img = image
        img = zoom(img, [zoom_factor, zoom_factor], order = 2)
        return img

    def Display(self):
        """
        Display mean, standard deviation, temporal SNR, and deviation 
        (Magnusson, P. and L. E. Olsson (2000)). Mid-axial views are displayed in
        the top row, mid-sagittal views the lower row.   Plot the percentage ghost
        vs. frame, deviation from the temporal mean vs. frame, and fraction of the
        variance accounted for by each of the first five terms of a series of 
        Legendre polynomials.
        """
        qa_images = zeros([8, 256, 256], float)
        z = self.zdim/2
        x = self.xdim/2
        xpad = (256 - self.zdim)/2
        qa_images[0,...] = self.Zoom(self.mean.reshape(self.img_shp)[z,...],256)
        qa_images[1,...] = self.Zoom(self.sdev.reshape(self.img_shp)[z,...],256)
        qa_images[2,...] = self.Zoom(self.sfnr.reshape(self.img_shp)[z,...],256)
        qa_images[3,...] = self.deviation.reshape([256, 256])
        qa_images[4,...] = self.Zoom(self.mean.reshape( \
                                self.img_shp)[:,:,x].transpose(), 256, True)
        qa_images[5,...] = self.Zoom(self.sdev.reshape( \
                                self.img_shp)[:,:,x].transpose(), 256, True)
        qa_images[6,...] = self.Zoom(self.sfnr.reshape( \
                                self.img_shp)[:,:,x].transpose(), 256, True)
#        qa_images[7,:,xpad:xpad+self.zdim] = self.deviation.reshape([256,256])

        self.disp = WblViewer(redirect=False)
        self.disp.InitViewer(qa_images, ncol=4, title=self.epi_file, colors='gray')
        colormin = 0.
        colormax = .9*qa_images[2].max()
        self.disp.SetColorRange(colormin, colormax)
        annotations = {1:{'xpos': 20,'ypos':100,'text':'testing'}}
        annotations = { 0:{'text':'Axial: Mean'}, \
                        1:{'text':'Standard Deviation'}, \
                        2:{'text':'TSNR (mean=%6.2f)' % self.mean_sfnr}, \
                        3:{'text':'Deviation: mean: %4.1f%%, max: %4.1f%%' % \
                                (self.mean_deviation, self.max_deviation)}, \
                        4:{'text':'Sagittal: Mean'}, \
                        5:{'text':'Standard Deviation'}, \
                        6:{'text':'TSNR'}}
        lstr = 'Excess variance accounted for\nby each Legendre polynomial:\n'
        nl = 0
        for i in  xrange(len(self.legndre_frac_mean)):
            lstr += '    %d:  %4.2f%%\n' % (i, self.legndre_frac_mean[i])
            nl += 1
        if self.spinecho_snr is not None:
            lstr += '\nStatic SNR: %6.1f' % self.spinecho_snr
            nl += 1
#            annotations[7] = {'text':'Static SNR: %6.1f' % self.spinecho_snr}
        annotations[7] = {'text':lstr, 'ypos':10}
        self.disp.Annotate(annotations)
        if not self.noshow:
            self.disp.Show()
        self.disp.ScreenDump('%s_snr.png' % self.prefix)
#        self.disp.CopyToClipboard()
#        self.disp.MainLoop()

    def Plot(self, dt0, data0, label):
        from pylab import plot, xlabel, ylabel, show, subplot, title, \
                                                                axis, savefig
        x0 = dt0*arange(data0.shape[0]).astype(float)
        subplot(3,1,1)
        title(self.prefix)
        plot(x0, data0,  marker = 'o', c='r', markersize=3)
        xlabel("Frame")
        ylabel(label)
        axis([0, x0.max(), 0., 1.1*data0.max()])
        subplot(3,1,2)
        x1 = arange(self.tdim).astype(float)
        plot(x1, self.mean_corrected,  marker = 'o', c='r', markersize=3)
        xlabel("Frame")
        ylabel("Percent Variation from Mean.")
        axis([0, x1.max(), self.mean_corrected.min(), self.mean_corrected.max()])
        subplot(3,1,3)
        x1 = arange(self.poly_order).astype(float) + 1.
        plot(x1, self.legndre_frac_mean,  marker = 'o', c='r', markersize=3)
        xlabel("Excess variance of Legendre terms: %s" % self.legndre_pct_label)
        ylabel("Fraction of Variance.")
        lmin = self.legndre_frac_mean.min()
        if lmin < 0:
            lmin = 1.1*lmin
        axis([0, x1.max(), lmin, 1.1*self.legndre_frac_mean.max()])
#       Save to png.
        savefig('%s_plots.png' % self.prefix)
        if not self.quiet and not self.noshow:
            show()

    def WriteOutput(self):
#        if self.write_images:
#            self.PackAndWrite()
        stats_str = '%s' % self.epi_file
        if self.spinecho_snr is not None:
            stats_str += ' Static SNR:%6.1f' % self.spinecho_snr
        if self.terse:
            stats_str += ' %f %f ' % (self.mean_sfnr, self.mean_value)
            for lfrac in self.legndre_frac_mean:
                stats_str += '%f ' % lfrac
            stats_str += '\n'
            sys.stdout.write(stats_str)
        else:
            stats_str += ' Mean TSNR: %6.2f Mean: %8.2f\nLegendre pcts:' % \
                                            (self.mean_sfnr, self.mean_value)
            if self.mean_deviation is not None:
                stats_str += \
                  ' Mean deviation: %5.2f ' % self.mean_deviation + \
                  'Max deviation %5.2f Legendre pcts: ' % self.max_deviation
            for lfrac in self.legndre_frac_mean:
                stats_str += '%6.3f ' % lfrac
            stats_str += '\n'
            sys.stdout.write(stats_str)
            self.PackAndWrite()
            self.Display()
            self.Plot(1., self.ghost_frac, 'Percent Ghost')
            self.WriteText(stats_str, '_stats')

    def ComputeEpiSnrs(self):
#        self.topdir = self.epi_file
        self.epi_frame = 0
        epi_files = [self.epi_files]
        hdr = None
        tdim = len(epi_files)
        nsnr = 0
        self.sfnrtxt = '%s.txt' % self.prefix
        f = open(self.sfnrtxt, 'w')
        entry = 'Frame\tTemporal SNR\tFilename\n' % (nsnr, self.mean_sfnr, fname)
        f.write(entry)
        sys.stdout.write(entry)
        for fname in epi_files:
            w = Wimage(fname)
            if w.hdr is None or w.hdr['tdim'] < 3:
                continue
            else:
                hdr = w.hdr
                shp = (w.hdr['zdim'], w.hdr['ydim'], w.hdr['xdim'])
                hdrout = hdr.copy()
                hdrout['tdim'] = tdim
                hdrout['dims'][3] = tdim
                hdrout['datatype'] = 'float'
                hdrout['filetype'] = 'nii'
            self.ReadEpiImage(fname)
            self.ComputeMask()
            self.ComputeTSNR()
            if fname != epi_files[-1]:
                writefile(self.prefix, self.sfnr, hdrout, frame=nsnr, last=False)
            else:
                hdrout['tdim'] = nsnr
                hdrout['dims'][3] = nsnr
                writefile(self.prefix, self.sfnr, hdrout, frame=nsnr, last=True)
            entry = '%04d\t%f\t%s\n' % (nsnr, self.mean_sfnr, fname)
            f.write(entry)
            sys.stdout.write(entry)
            nsnr += 1
        f.close()


def scanner_qa():
    try:
        qa = ScannerQA()
        qa.Process()
#        else:
#            qa.ComputeEpiSnrs()
        sys.exit(0)
    except RuntimeError, errstr:
        sys.stderr.write('%s\n%s\n' % (errstr, except_msg()))
#        if qa is not None:
#            qa.CleanUp()
        sys.exit(1)

if __name__ == '__main__':
    scanner_qa()
