#!/usr/bin/env python

ID = "$Id: wbl_glm.py 216 2009-11-18 01:43:09Z jmo $"[1:-1]

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


# Methods useful for analyzing motion.


import os
import sys
from math import log10, sqrt

from numpy import zeros, float, array, diff, sqrt, dot, arange, sin, cos, \
                  prod, ones, where, nonzero, cumsum, inner, double, float32, \
                  short
from numpy.linalg import inv
from scipy.stats import median, histogram2

from file_io import Wimage
from wimage_lib import get_tmp_space
import constants as c
from wbl_viewer import WblViewer
from scipy.ndimage.interpolation import zoom
from scipy.special import legendre
from subprocess import Popen, PIPE

ID = "$Id: wbl_glm.py 216 2009-11-18 01:43:09Z jmo $"[1:-1]

class MotionData():

    def __init__(self, fname, cross_slice=False, censor=None):
        self.fname = fname
        self.ReadMotionFile()
        self.ComputeMotionStats(cross_slice=cross_slice, censor=censor)

    def ReadMotionFile(self):
        f = open(self.fname, 'r')
        self.motlines = f.readlines()
        f.close()
        self.tdim = len(self.motlines)
        ncol = len(self.motlines[0].split())
        if ncol == 6:
            i0 = 0
        else:
            i0 = 1

        self.motion_parameters = zeros([6, self.tdim], float)
        t = 0
        for line in self.motlines:
            wds = line.split()
            for j in xrange(6):
                self.motion_parameters[j, t] = float(wds[j+i0])
            t += 1

    def Orthogonalize(self):
        """
        Orthogonalize motion parameters w.r.t. affine term.
        """
        A = zeros([self.tdim, 2], float)
        A[:,0] = 2.*arange(self.tdim) - 1.
        A[:,1] = 1
        ATAm1 = inv(dot(A.transpose(),A))
        ATAm1AT = dot(ATAm1, A.transpose())
        for j in xrange(6):
            x = self.motion_parameters[j, :]
            beta0 = dot(ATAm1AT[0, :], x)
            beta1 = dot(ATAm1AT[1, :], x)
            self.motion_parameters[j, :] -= beta0*A[:,0] + beta1

    def WriteMotionParamsCrt(self):
        for t in xrange(self.tdim):
            sys.stdout.write('%5.4f' % self.motion_parameters[0, t])
            for j in xrange(5):
                sys.stdout.write(' %5.4f' % self.motion_parameters[j+1, t])
            sys.stdout.write('\n')


    def ComputeMotionStats(self, cross_slice=False, censor=None):
        """
        Compute position of a point at [50, 50, 50] mm from the brains
        center of rotation at each point in the time series.  Also compute
        the distance from the center and the total path length.
        If censor is present, only values of the censor array not equal to one
        will be included in the computation.
        """
        if censor is not None:
            idcs = nonzero(1. - censor)[0]
        else:
            idcs = range(self.tdim)
        tdim = len(idcs)
        self.pos_5cm = zeros([tdim, 3], float)

        for t in idcs:
            tht = c.deg2rad*self.motion_parameters[0, t]
            phi = c.deg2rad*self.motion_parameters[1, t]
            psi = c.deg2rad*self.motion_parameters[2, t]
            ctht = cos(tht)
            stht = sin(tht)
            cphi = cos(phi)
            sphi = sin(phi)
            cpsi = cos(psi)
            spsi = sin(psi)
            R = zeros([3,3],float)
            if cross_slice:
                R[0,0] =  cpsi
                R[0,1] =  spsi
                R[0,2] =  0.
                R[1,0] = -spsi*ctht
                R[1,1] =  cpsi*ctht
                R[1,2] =  stht
                R[2,0] =  spsi*stht
                R[2,1] = -cpsi*stht
                R[2,2] =  ctht
                translation = array([0., self.motion_parameters[4, t], 0.])
            else:
                R[0,0] =  ctht*cphi
                R[0,1] =  stht*cpsi - ctht*spsi*sphi
                R[0,2] =  ctht*sphi*cpsi + stht*spsi
                R[1,0] = -stht*cphi
                R[1,1] =  ctht*cpsi - stht*spsi*sphi
                R[1,2] = -stht*sphi*cpsi + ctht*spsi
                R[2,0] = -sphi
                R[2,1] = -spsi*cphi
                R[2,2] =  cphi*cpsi
                translation = array([self.motion_parameters[4, t], \
                              self.motion_parameters[5, t], \
                              self.motion_parameters[3, t]])
            x = array([50., 50., 50.])
            posn = dot(R, x) + translation
            self.pos_5cm[t,:] = posn

        self.gradient = diff(self.pos_5cm, axis=0)
        self.path_length = 100.*sqrt((self.gradient**2).sum(1)).mean()
        self.sigmaz =  self.gradient.std()
#        self.path_length = 100.*(abs(self.gradient).sum(1)).mean()
        return self.sigmaz, self.gradient


    def RewriteMotionData(self, fname):
        """
        Write motion parameters to a file.  
        motlines is an existing motion parameter file.
        fname is the file to be written.
        """
        self.mot_out = []
        t = 0
        for line in motlines:
            wds = line.strip().split()
            for i in xrange(6):
                wds[i+1] = '%f' % self.motion_parameters[i,t]
            self.mot_out.append('\t'.join(wds) + '\n')
            t += 1
        f = open(fname, 'w')
        for line in self.mot_out:
            f.write(line)
        f.close()

class DesignMatrix():
    """
    Purpose: Create design matrix.  The constructor builds a design matrix
        modeling task-related effects.  Methods add other models to the matrix.
    Attributes:
        Adsgn: List containing design matrices.
        Azdim: Number of design matrices (equal to either 1 or the number of 
               slices specified by zdim.)
    """
    def __init__(self, tdims, TR, stim_file=None, zdim=1, model='fir', lgth_TRs=8, nruns=1):
        """
        zdim: Number of slices
        tdim: Number of frames
        nruns: Number of EPI runs to be modeled.
        TR: Frame duration in seconds.
        stim_file: 1D file specifying stimulus onset times.
        model: Type of model: (fir)
        lgth_TRs: Length of HRF in TRs (lgth_TR*TR = length in seconds)
        """
        self.zdim = zdim
        if not isinstance(tdims, list):
            self.tdims = [tdims]
        else:
            self.tdims = tdims
        self.TR = TR
        self.nruns = nruns
        self.stim_file = stim_file
        self.model = model
        self.lgth_TRs = lgth_TRs

#       Compute total number of frames.
        self.tdim = array(self.tdims).sum()
        if self.stim_file is not None:
            self.ReadStimFile()
        self.Adsgn = None
        self.Neff = 0
        self.beta = None
        self.n_baseline = None

    def ReadStimFile(self):
        """
        Read AFNI 1D file and create submatrix defining task-related regressors.        A "FIR" design is used, i.e., one covariate for time-point in the 
        assumed response.
        Attributes:
            stim_times: array of stimulus onset times.
            n_offsets: Number of offsets.  If stimuli occur on frame
                       boundaries, n_offsets = 1.  If they also occur
                       on half-frame boundaries, n_offsets=2.
        """
        f = open(self.stim_file)
        lines = f.readlines()
        f.close()

        n_offsets = 2
        self.Adsgn_task = zeros([self.tdim, n_offsets*self.lgth_TRs], float)
        self.stim_times = []
        for line in lines:
            wds = line.split()
            for wd in wds:
                if '*' in wd:
#                   End of run marker. Stop here.
                    break
                self.stim_times.append(int(round(float(wd))))

        test = zeros(2)
        for t in self.stim_times:
            test[t % 2] += 1
        if test[0]*test[1] == 0:
            self.n_offsets = 1
        else:
            self.n_offsets = 2


    def AddStimulusRegressors(self):
        """
        Purpose: Create design matrix for a specified model.
        Attributes:
            Neff_task: Actual length of hrf model (number of columns)
            Adsgn_task: Computed design matrix.
        """
        if self.model == 'fir':
            self.Neff_task = self.n_offsets*self.lgth_TRs
            self.n_task = self.Neff
            self.Neff += self.Neff_task
            if self.Adsgn is not None:
                Adsgn[:, :self.n_task] = self.Adsgn[0]
            Adsgn = zeros([self.tdim, self.Neff_task], float)
            for time in self.stim_times:
                offset = time % self.TR
                frame = time/self.TR
                for i in xrange(self.lgth_TRs):
                    if frame+i < self.tdim:
                        Adsgn[frame+i, self.n_offsets*i+offset] = 1.
#                        Adsgn[frame+i, offset*self.lgth_TRs + i] = 1.
        self.Adsgn = [Adsgn]
        self.Azdim = 1
        self.Neff_affine = 0
        self.Neff_legendre = 0
        self.Neff_hpf = 0

    def DisplayDesignMatrix(self, title='Design Matrix'):
        zoom_factor = 2
        x_scl = 5.
        xdim = x_scl*self.Neff
        ydim = self.tdim
        dsgn_picture = zeros([ydim, xdim], float)
        for frm in xrange(self.tdim):
            for neff in xrange(self.Neff):
                dsgn_picture[frm, x_scl*neff:x_scl*(neff+1)-1] = \
                                                    self.Adsgn[0][frm,neff]

        imgout = zoom(dsgn_picture, zoom_factor, order=0)
        self.dsgn_disp = WblViewer(redirect=False)
        self.dsgn_disp.InitViewer(imgout, title=title, \
                pane_size=(zoom_factor*ydim, zoom_factor*xdim), \
                colors='gray', interp='linear', left_is_left=False)
        colormin = -1.
        colormax =  1.
        self.dsgn_disp.SetColorRange(colormin, colormax)
#        self.dsgn_disp.Annotate(annotations)
        self.dsgn_disp.Show()

    def AddAffineRegressors(self):
        """
        Add affine terms (constant and slope) to design matrix. One
        set of terms per run is added.
        Attributes:
            Adsgn: Design matrix
            Neff_affine: Number of regressors
            n_baseline: Column of the first baseline regressor.
        """
        self.n_baseline = self.Neff
        self.Neff_affine = 2*self.nruns
        self.Neff += self.Neff_affine
        Adsgn = zeros([self.tdim, self.Neff],float)
        if self.Adsgn is not None:
            Adsgn[:, :self.n_baseline] = self.Adsgn[0]
        t = 0
        for run in xrange(self.nruns):
            tdim = self.tdims[run]
            Adsgn[t:t + tdim, self.n_baseline + 2*run] = 1.
            Adsgn[t:t + tdim, self.n_baseline + 2*run+1] = \
                        2*arange(tdim).astype(float)/float(tdim) - 1
            t = t + tdim
        self.Adsgn = [Adsgn]
        self.Azdim = 1

    
    def AddHighPassFilter(self, nfreq):
        """ 
        Implement High-pass filter by adding sinusoids to design matrix. 
        nfreq: Number of frequency components.
        Attributes:
            Adsgn: Design matrix.
            Neff_hpf: Number of regressors used.
        """
        n_hpf = self.Neff
        self.Neff_hpf = 2*nfreq*self.nruns
        self.Neff += self.Neff_hpf
        Adsgn = zeros([self.tdim, self.Neff], float)
        Adsgn[:, :n_hpf] = self.Adsgn[0]
        t = 0
        ieff = 0
        for run in xrange(self.nruns):
            tdim = self.tdims[run]
            for ifrq in xrange(1, nfreq+1, 1):
                w = ifrq*2*c.pi*arange(tdim)/float(tdim)
                Adsgn[t:t + tdim, n_hpf+ieff]   = cos(w)
                Adsgn[t:t + tdim, n_hpf+ieff+1] = sin(w)
                ieff += 2
            t = t + tdim
        self.Adsgn = [Adsgn]
        self.Azdim = 1

    def AddLegendre(self, max_order=1):
        """
        Add Legendre terms up to max-order to design matrix. One
        set of terms per run is added.
        Attributes:
            Adsgn: Design matrix
            Neff_legendre: Number of regressors
            Legendre: Column of the first baseline regressor.
        """
        M = max_order + 1
        self.n_baseline = self.Neff
        self.Neff_legendre = M
        n0 = self.Neff
        self.Neff += self.Neff_legendre
        Adsgn = zeros([self.tdim, self.Neff],float)
        if self.Adsgn is not None:
            Adsgn[:, :self.n_baseline] = self.Adsgn[0]
        t = 0
        for run in xrange(self.nruns):
            tdim = self.tdims[run]
            x = 2.*(arange(tdim).astype(float))/(tdim - 1.) - 1.
            for m in xrange(M):
                xpow = ones(self.tdim)
                coeffs = legendre(m)
                for i in xrange(m+1):
                    Adsgn[t:t+tdim, n0+m] += coeffs[i]*xpow
                    xpow *= x
                if m == 0:
                    self.n_baseline = n0+m
            t = t + tdim
        self.Adsgn = [Adsgn]
        self.Azdim = 1

    def AddMotionRegressor(self, regressors):
        shp = regressors.shape
        if shp[0] == 1 and regressors.ndim == 2:
            regressors = regressors.reshape(shp[1])
        if regressors.ndim == 1:
            Azdim = 1
            regressors = regressors.reshape([Azdim, shp[0], 1])
        elif shp[0] == 6 and shp[1] == self.tdim:
            Azdim = 1
            regressors = regressors.reshape([Azdim, shp[0], shp[1]])
        elif shp[1] == self.tdim:
            self.zdim == shp[0]
            Azdim = self.zdim
            regressors = regressors.reshape([Azdim, shp[1], 1])
        else:
            raise RuntimeError, 'Did not recognize shape of regressor.'

        self.Neff_motion = regressors.shape[1]
        self.n_motion = self.Neff
        self.Neff += self.Neff_motion
        Adsgn_new = []
        for z in xrange(Azdim):
            Adsgn = zeros([self.tdim, self.Neff], float)
            if self.Adsgn is not None:
                Adsgn[:, :self.n_motion] = self.Adsgn[0]
            for n in xrange(self.Neff_motion):
                Adsgn[:,n + self.n_motion] = regressors[z, n, :]
            Adsgn_new.append(Adsgn)
        self.Adsgn = Adsgn_new
        self.Azdim = len(self.Adsgn)

    def ComputeEstimator(self):
        self.ATAm1AT = []
        for z in xrange(self.Azdim):
            Adsgn = self.Adsgn[z]
            self.ATAm1 = inv(dot(Adsgn.transpose(), Adsgn))
            self.ATAm1AT.append(dot(self.ATAm1, Adsgn.transpose()))

    def ComputeBeta(self, inData):
        """
        Compute estimates (betas) of linear model.
        Data: Instance of the Data class.
        """

        self.ComputeEstimator()

#       Compute estimates.
        if isinstance(self.Azdim, int):
            self.volume = True
            self.beta = zeros([self.Neff, inData.nvox], float)
            for t in xrange(self.tdim):
                for n in xrange(self.Neff):
                    self.beta[n,:] += self.ATAm1AT[0][n, t]*inData.data[t,:]
        else:
            self.volume = False
            self.beta = []
            nzm1 = 0
            nz = 0
            for z in xrange(self.Azdim):
                nz += inData.nzvox[z]
                beta = zeros([self.Neff, inData.nzvox[z]], float)
                for t in xrange(self.tdim):
                    for n in xrange(self.Neff):
                        beta[n,:] += self.ATAm1AT[z][n, t]*inData.data[t,nzm1:nz]
                self.beta.append(beta)
                nzm1 = nz
        return self.beta

    def ComputeResiduals(self, inData):
        if self.beta is None:
            self.ComputeBeta(inData)
        if self.volume:
            residuals = zeros([self.tdim, inData.nvox], float)
            residuals[:,:] = inData.data[:,:]
            for t in xrange(self.tdim):
                for n in xrange(self.Neff):
                    residuals[t,:] -= self.Adsgn[0][t,n]*self.beta[n,:] 
        return residuals

    def GetBaseline(self):
        if self.beta is None:
            raise RuntimeError('Must compute beta before calling GetBaseline()')
        return self.beta[self.n_baseline,...]

    def WriteDesignMatrix(self, fname, z=0):
        """
        Write design matrix to a text file.
        fname: filename to be written.
        z: Slice index. Slice-specific design matrices only.
        """
        Adsgn = self.Adsgn[z]
        nx = Adsgn.shape[0]
        ny = Adsgn.shape[1]
        f = open(fname, 'w')
        for i in xrange(nx):
            f.write('%d' % i)
            for j in xrange(ny):
                f.write('\t%f' % Adsgn[i, j])
            f.write('\n')
        f.close()

class Data():

    def __init__(self, fnames=None, data=None, TR=None, skip=3, \
               correct_motion=False, tshift=True, verbose=False, tmpdir=None, mask_thresh=True):
        self.clean_files = []
        self.verbose = verbose
        self.skip = skip
        if tmpdir is None:
            self.tmpdir = '.'
        else:
            self.tmpdir = tmpdir
        if data is not None:
            self.data = data
            self.tdim = data.shape[0]
            self.TR = TR
            if data.ndim == 1:
                self.xyzdim = 1
            elif data.ndim > 1:
                self.xyzdim = prod(array(data)[1:])
        elif fnames is not None:
            self.epifiles = []
            self.w = []
            if not isinstance(fnames, list):
                fnames = [fnames]
            for fname in fnames:
                if correct_motion:
                    mtnfile = fname.replace('.nii','')
                    mtnfile = mtnfile.replace('+orig','')
                    self.mtnfile = os.path.abspath('%s_mtn.txt' % mtnfile.replace('+orig',''))
                    fname = self.Volreg(fname, base=fnames[0], savemtn=self.mtnfile)
                    self.epifiles.append(fname)
                else:
                    self.epifiles.append(fname)
                w = Wimage(fname)
                self.w.append(w)
                if w.hdr is None:
                    raise RuntimeError('Could not read header from %s' % fname)
            self.hdr = self.w[0].hdr

            self.xdim = self.hdr['xdim']
            self.ydim = self.hdr['ydim']
            self.zdim = self.hdr['zdim']
            self.zdim = self.hdr['zdim']
            self.tdims = []
            self.tdim = 0
            for w in self.w:
                self.tdims.append(w.hdr['tdim'])
                self.tdim += w.hdr['tdim']
            self.xsize = self.hdr['xsize']
            self.ysize = self.hdr['ysize']
            self.zsize = self.hdr['zsize']
            self.TR = self.hdr['sizes'][3]/1000.
            self.xyzdim = prod(self.hdr['dims'][:3])
            self.xydim = prod(self.hdr['dims'][:2])
            self.img_shp = (self.tdim, self.xyzdim)
            self.nzvox = (self.xyzdim*ones(self.zdim)).astype(int).tolist()

            t0 = 0
            t1 = 0
            image = zeros([self.tdim - skip, self.xyzdim], float32)
            for w in self.w:
                t1 += w.hdr['tdim'] - skip
                image[t0:t1, :] = (w.readfile()).\
                                    reshape([self.tdim, self.xyzdim])[skip:,:]
                t0 = t1
                self.tdim -= skip

            self.imgin = image
            self.mean = (self.imgin.mean(0)).reshape([self.xyzdim])
            self.mask = where(self.mean < mask_thresh*self.mean.max(), 0., 1.)
            self.GetVoxels(self.mask)
        else:
            raise RuntimeError('No data supplied to "Data" object.')

    def PercentileMask(self, snrs, percentile):
        """
        Create a mask that is one for values that are greater than the 
        spceficied percentile.  Outliers are rejected by only considering the 
        lower 98th percentile of values.
        """

#       First find the 95th percentile SNR.
        nbins = 100
        bins = snrs.max()*arange(nbins)/float(nbins-1)
        histo = (histogram2(snrs.flat,bins)).astype(float)
        pctile_98 = bins[array(nonzero(\
                where(cumsum(histo/histo.sum()) < .98, 0., 1.))).min()]

        bins = pctile_98*arange(nbins)/float(nbins-1)
        histo = (histogram2(snrs.flat,bins)).astype(float)
        cutoff_bin = array(nonzero(\
                where(cumsum(histo/histo.sum()) < percentile, 0., 1.))).min()
        pctile_out = bins[array(nonzero(\
                where(cumsum(histo/histo.sum()) < percentile, 0., 1.))).min()]
#        print \
#        '98th percentile SNR: %5.1f ' % pctile_98 + \
#        'Cutoff percentile:%5.0f,  Minimum SNR: %5.2f' % \
#                                    (100*percentile, pctile_out)
        return where(snrs < pctile_out, 0., 1.)

    def SNRMask(self, snr_image=None, min_SNR=25, min_percentile=.25):
        """
        Compute mask that removes low SNR regions.
        Attributes:
            snr_mask: 1 for voxels with SNR>min_SNR and in above 25th percentile
            mean_snr: SNR averaged over the snr mask.
        """
        if self.imgin.ndim == 1:
            return ones(self.tdim)
        elif snr_image is None:
#           Compute SNR. Omit pixels with mean < 20% of maximum.
            self.mean = (self.imgin[3:,...].mean(0)).reshape([self.xyzdim])
            self.sdev = (self.imgin[3:,...].std(0)).reshape([self.xyzdim])
            msk = where(self.mean < .20*self.mean.max(), 0., 1.)
            self.snr = msk*self.mean/(self.sdev + (1 - msk))
        else:
            self.snr = snr_image
            msk = where(snr_image > 0., 1., 0.)

#       First create a mask to remove the lowest quartile of SNRs.
        idx = nonzero(msk)
        pixels = self.PercentileMask(self.snr.take(idx), min_percentile)
        self.snr_mask = zeros(self.snr.shape, float)
        self.snr_mask.put(idx, pixels)
        self.snr_mask = self.snr_mask.reshape(self.snr.shape)

#       Require SNR > min_SNR.
        self.snr_mask *= (where(self.snr < min_SNR, 0., 1.))#. #\
#                                            reshape(self.xyzdim)
#        self.mean_snr = (self.snr_mask*self.snr).sum()/self.snr_mask.sum()
#        print 'Mean SNR: %f' % self.mean_snr
#        self.GetVoxels(self.snr_mask)
        return self.snr_mask


    def GetVoxels(self, mask):
        self.voxels = nonzero(mask.reshape(self.xyzdim))[0]
        self.nvox = len(self.voxels)
        self.has_brain = []
        self.nzvox = []
        for z in xrange(self.zdim):
            if mask[z,...].sum() > 0:
                self.has_brain.append(True)
            else:
                self.has_brain.append(False)
            self.nzvox.append(int(mask[z,...].sum()))
        self.ExtractVoxels()

    def ExtractVoxels(self):
        self.data = self.imgin.take(self.voxels, axis=1)

    def PutVoxels(self, data):
        if len(data.shape) > 1:
            tdim = data.shape[0]
            image = zeros([data.shape[0], self.xyzdim], float)
            for t in xrange(tdim):
                image[t,:].put(self.voxels, data[t,:])
        else:
            image = zeros(self.xyzdim, float)
            image.put(self.voxels, data)
        return image

    def RemoveTrend(self):
        sumxy = zeros(self.nvox, float)
        sumy = zeros(self.nvox, float) 
        x = arange(self.tdim).astype(float)
        for t in xrange(self.tdim):
            sumxy += float(t)*self.data[t,:]
            sumy += self.data[t,:]
        slope = (self.tdim*sumxy - sumy*x.sum())/ \
                    (self.tdim*(x**2).sum() - (x.sum())**2)
        for t in xrange(self.tdim):
            self.data -= slope*float(t - (self.tdim-1.)/2.)

        self.mean_snr_notrend = (self.data.mean(0)/self.data.std(0)).mean()

    def Volreg(self, fname, base=None, savemat=False, savemtn=None, tshift=True):
        w = Wimage(fname)
        if '3dvolreg' in w.hdr['native_header'].get('history_note',''):
#           Input file has been motion-corrected.
#            print 'Found motion corrected data'
            return fname
        prefix = '%s/%s' % (self.tmpdir, os.path.basename(fname))
        prefix = prefix.split('+orig')[0]
        prefix = prefix.split('.nii')[0]
        prefix = prefix + '_m'
        if base is None:
            base = fname
        if os.path.exists(prefix+'+orig.BRIK'):
            os.remove(prefix+'+orig.BRIK')
            os.remove(prefix+'+orig.HEAD')
        opts = ''
        if savemat:
            opts += ' -1Dmatrix_save %s.aff12.1D' % prefix
        if savemtn is not None:
            opts += ' -dfile %s' % savemtn
        if tshift:
            opts += ' -tshift %d' % self.skip
        mtnfile = '%s_mtn.txt' % prefix
        if self.verbose:
            devnull = ''
        else:
            devnull = ' >& /dev/null'
        cmd = \
        '3dvolreg -prefix %s  -Fourier -twopass -base %s[0] %s %s %s' % \
                                        (prefix, base, opts, fname, devnull)
#        print cmd
        p = Popen(cmd, shell=True)
        sts = os.waitpid(p.pid, 0)
        self.clean_files.append(prefix+'+orig.HEAD')
        self.clean_files.append(prefix+'+orig.BRIK')
        return prefix + '+orig'

    def Clean(self):
        for fname in self.clean_files:
            os.remove(fname)

class AfniDsgnMatrix():

    def __init__(self, input_file):
        self.input_file = input_file
        if os.path.exists(input_file):
            f = open(self.input_file)
            self.input_lines = f.readlines()
            f.close()
        else:
            raise RuntimeError('Input file does not exist: %s' % input_file)

        if not self.input_lines[0].startswith('# <matrix'):
            raise RuntimeError('Input file is not a matrix file: %s' % input_file)
        self.input_lines = self.input_lines[1:]

        self.datatypes = {'double':double, 'float':float32, 'short':short}
        self.func_map = { \
            'ni_type':self._Number, \
            'ni_dimen':self._Number, \
            'ColumnLabels':self._List, \
            'ColumnGroups':self._Number, \
            'RowTR':self._Number, \
            'GoodList':self._Number, \
            'NRowFull':self._Number, \
            'RunStart':self._Number, \
            'Nstim':self._Number, \
            'StimBots':self._Number, \
            'StimTops':self._Number, \
            'StimLabels':self._List, \
            'Nglt':self._Number, \
            'GltLabels': self._List}
        self.dsgn_matrix = None
        self.ReadDsgnMatrix()

    def _Number(self, string_in):
        fields = string_in.replace('"','').split(',')
        result = []
        datatype = int
        for field in fields:
            if '..' in field:
                result += (apply(self._DotDot, [field]))
            elif '@' in field:
                result += (apply(self._AtSign, [field]))
            elif '*' in field:
                wds = field.split('*')
                if '.' in wds[0]:
                    result += [float(wds[0])]
                else:
                    result += [int(wds[0])]
                datatype = self.datatypes.get(wds[1],None)
            else:
                if '.' in field:
                    result += [float(field)]
                else:
                    result += [int(field)]
        if len(result) == 1:
            result = result[0]
        return result, datatype


    def _Null(self):
        return None

    def _List(self, string_in):
        input = string_in[1:-1]
        return input.replace(';',' ').split(), None

    def _AtSign(self, string_in):
        wds = string_in.split('@')
        if '.' in wds[1]:
            x = float(wds[1])
        else:
            x = int(wds[1])
        return int(wds[0])*[x]

    def _DotDot(self, string_in):
        wds = string_in.split('..')
        return arange(int(wds[0]), int(wds[1])).tolist()

    def ProcLine(self, line):
        if self.dsgn_matrix is None:
            self.dsgn_matrix = \
                zeros([self.header['ni_dimen'], self.header['ni_type']], float)
        x = map(float, line.strip().split())
        self.dsgn_matrix[self.row,:] = array(x)
        self.row += 1

    def ReadDsgnMatrix(self):
        self.header = {}
        self.row = 0
        for line in self.input_lines:
            if len(line.strip()) == 0:
                continue
            wds = line.split()
            if wds[0] == '#':
                if wds[1] == '>' or wds[1] == '</matrix>':
                    continue
                arg = ' '.join(wds[3:])
                self.header[wds[1]] = \
                        apply(self.func_map.get(wds[1], self._List), [arg])[0]
            else:
                self.ProcLine(line)
        self.Nfrm = self.header['ni_dimen']
        self.Neff = self.header['ni_type']
        self.effects = self.header['ColumnLabels']
        self.contrast_names = self.header['StimLabels']+self.header['GltLabels']
        self.num_contrasts = self.header['Nglt']
        self.num_contrasts = len(self.contrast_names)
        self.contrasts = zeros([self.num_contrasts, self.Neff], float)
        for nc in xrange(len(self.header['StimLabels'])):
            for idx in xrange(len(self.effects)):
                if self.effects[idx].startswith( \
                                        '%s#' % self.header['StimLabels'][nc]):
                    self.contrasts[nc, idx] = 1.
                    break
        ic = len(self.header['StimLabels'])
        for nc in xrange(len(self.header['GltLabels'])):
            key = 'GltMatrix_%06d' % nc
            srow = apply(self._Number, self.header[key])[0]
            self.contrasts[ic,:] = array(srow[2:]).astype(float)
            ic += 1
#        print self.contrasts
#        print self.dsgn_matrix
#        print self.contrast_names
        self.ATAm1 = inv(dot(self.dsgn_matrix.transpose(), self.dsgn_matrix))
        self.ATAm1AT = dot(self.ATAm1, self.dsgn_matrix.transpose())

    def ContrastScaleFactors(self):
        self.root_ctATAm1c = {}
    #    print '  Contrast        Std. Dev.Scale Factor'
    #    print '  --------        ---------------------'
        for ic in xrange(self.num_contrasts):
            x = dot(self.ATAm1, self.contrasts[ic, :])
            root_ctATAm1c = sqrt(dot(self.contrasts[ic, :].transpose(), x))
    #        pad = 20 - len(self.contrast_names[ic])
    #        print '  %s%s%7.4f' % \
    #                            (self.contrast_names[ic], pad*' ', root_ctATAm1c)
            self.root_ctATAm1c[self.contrast_names[ic]] = root_ctATAm1c
#            print self.contrasts[ic, :]
#        print self.root_ctATAm1c
        return self.root_ctATAm1c

class AfniGlm():

    def __init__(self, glm_file):
        self.glm_file = glm_file
        self.w = Wimage(self.glm_file)
        self.hdr = self.w.hdr
        self.xdim, self.ydim, self.zdim, self.tdim = self.hdr['dims'][:4]
        self.shp = [self.zdim, self.ydim, self.xdim]

        brick_labs = self.hdr['native_header']['brick_labs']
        self.effects = brick_labs.split('~')
        self.baseline = None
        self.beta = None

    def GetEffectFrame(self, effect_name, eff_type='Tstat'):
        """
        eff_type takes on values of "Tstat", "Coef", or "Fstat"
        """ 
        cnt = 0
        i = 0
        frame = None
        for effect in self.effects:
            if eff_type in effect and effect_name in effect:
                if cnt > 0:
                    raise RuntimeError(\
                            'Non-unique effect_name supplied to GetTstatFrame')
                else:
                    cnt += 1
                    frame = i
            i += 1
#        print 20,effect_name,frame
        return  frame

    def GetBaseline(self):
        if self.baseline is not None:
            return self.baseline
        baseline_names = []
        run = 1
        while True:
            eff_name = 'Run#%dPol#0' % run
            frame = self.GetEffectFrame(eff_name, eff_type='Coef')
            if frame is None:
                break
            else:
                baseline_names.append(eff_name)
            run += 1
        self.baseline = zeros([self.zdim, self.ydim, self.xdim], float)
        for bname in baseline_names:
            self.baseline += self.GetBeta(bname)
        self.baseline /= len(baseline_names)
        self.mask = where(self.baseline < 500., 0., 1.)
        return self.baseline

    def GetTstat(self, effect_name):
        frame = self.GetEffectFrame(effect_name, eff_type='Tstat')
        return self.w.readfile(frame=frame)

    def GetFstat(self, effect_name):
        frame = self.GetEffectFrame(effect_name, eff_type='Fstat')
        return self.w.readfile(frame=frame)

    def GetBeta(self, effect_name):
        frame = self.GetEffectFrame(effect_name, eff_type='Coef')
        return self.w.readfile(frame=frame)

    def GetPctChg(self, effect_name, baseline=None):
        if baseline is None:
            baseline = self.GetBaseline()
            mask = self.mask
        else:
            mask = where(baseline < 500., 0., 1.)
        beta = self.GetBeta(effect_name)
        return 100.*mask*beta/(baseline + 1. - mask)

    def ReadBetas(self, dm):
        self.beta = zeros([len(dm.effects)] + self.shp, float)
        ieff = 0
        for effect in dm.effects:
            img = self.GetBeta(effect)
            self.beta[ieff,...] = img
#            self.beta[ieff,...] = self.GetBeta(effect)
            ieff += 1

    def GetEstimatedFrame(self, frame, dm):
        """
        frame is the frame of the epi data to be estimated.
        dm is an AfniDsgnMatrix object.
        """
        if self.beta is None:
            self.ReadBetas(dm)
        modeled_frm = zeros(self.shp, float)
        for eff in xrange(dm.Neff):
            modeled_frm += dm.dsgn_matrix[frame, eff]*self.beta[eff,...]
        return modeled_frm

def read_afni_dsgn_matrix():
    ra = AfniDsgnMatrix(sys.argv[1])
    ra.ReadDsgnMatrix()
    ra.ContrastScaleFactors()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        sys.stdout.write('%s\n' % ID)
        sys.exit()
    else:
        read_afni_dsgn_matrix()      
