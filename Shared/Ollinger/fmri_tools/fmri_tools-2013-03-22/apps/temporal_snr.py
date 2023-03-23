#!/usr/bin/env python

import sys
import os
import time
from optparse import OptionParser
from numpy import zeros, float, where, sqrt, median, nonzero, arange, ones, \
                  dot, identity, nan_to_num
from numpy.linalg import inv
from scipy.special import legendre
from file_io import Wimage, writefile
from plotlib import PlotImage

MAX_LEGENDRE_DFLT = 4

class TemporalSnr():
    """
    Create and display temporal SNR of EPI images.
    """

    def __init__(self, epifile=None, prefix=None, max_legendre=MAX_LEGENDRE_DFLT):
        matplotlibrc = '%s/%s' % (os.getenv('HOME'), os.getenv('USER'))
        if not os.path.exists(matplotlibrc) or \
            (os.stat(matplotlibrc).st_mode & 0300) == 0:
            self.mplconfigdir = '/tmp/%s_%d_%d' % \
                                (os.getenv('USER'), time.time(), os.getpid())
            os.putenv('MPLCONFIGDIR', self.mplconfigdir)
        else:
            self.mplconfigdir = None
        self.verbose = False
        self.skip = 5
        self.prefix = prefix
        self.beta = None
        self.max_legendre = max_legendre
        if __name__ == '__main__':
            self.GetOptions()
        else:
            self.epifile = epifile

        if self.prefix is None:
            self.prefix = self.epifile.replace('.nii','')
            self.prefix = self.prefix.replace('.HEAD','')
            self.prefix = self.prefix.replace('.BRIK','')
            self.prefix = self.prefix.replace('+orig','')
            self.prefix += '_snr'

        self.LoadData()


    def GetOptions(self):
        usage = 'temporal_snr <epi_time_series>\n' + \
                '\tEnter temporal_snr --help for options\n' + \
                'Computes temporal SNR from residuals after baseline ' + \
                'fluctuations are removed. Baseline is modeled as an nth ' + \
                'order Legendre polynomial series where n defaults to %d.' % \
                MAX_LEGENDRE_DFLT
        optparser = OptionParser(usage)
        optparser.add_option( "-v", "--verbose", action="store_true",  \
            dest="verbose",default=False, help="Verbose mode.")
        optparser.add_option( "", "--max-legendre", action="store",  \
            dest="max_legendre",default=MAX_LEGENDRE_DFLT, type=int, \
            help="Maximum order of Legendre polynomial series used to model " + \
                 "baseline fluctuations. " + \
                 "Default = %d. Set to zero to omit baseline model." % \
                 MAX_LEGENDRE_DFLT)
        optparser.add_option( "", "--prefix", action="store", type=str,  \
            dest="prefix",default=None, help="Output filename prefix.")
        optparser.add_option( "", "--skip", action="store", type=int,  \
            dest="skip",default=5, help="Frames to skip. Default=5.")
        opts, args = optparser.parse_args()

        if len(args) != 1:
            sys.stderr.write(usage)
            sys.exit(1)

        self.epifile = args[0]
        self.prefix = opts.prefix
        self.verbose = opts.verbose
        self.skip = opts.skip
        self.max_legendre = opts.max_legendre

    def LoadData(self):
        """
        Read the header and initialize stuff.
        """
        self.w = Wimage(self.epifile)
        self.hdr = self.w.hdr
        self.xdim, self.ydim, self.zdim, self.tdim = self.hdr['dims'][:4]
        self.xyzdim = self.xdim*self.ydim*self.zdim
        self.xsize, self.ysize, self.zsize = self.hdr['sizes'][:3]

    def ComputeTsnr(self):
        """
        Compute the temporal SNR. Optionally remove baseline terms modeled
        by a series of Legendre polynomials.
        """
        sumx = zeros((self.zdim, self.ydim, self.xdim), float)
        sumxsq = zeros((self.zdim, self.ydim, self.xdim), float)

        delta = float(self.tdim)/80.
        dm1 = 1
        N = self.tdim - self.skip
        if self.verbose:
            sys.stdout.write('Computing stats: ')
        for t in xrange(N):
            if (t/delta) > dm1 and self.verbose:
#                sys.stdout.write('%d-'%t)
                sys.stdout.write('.')
                sys.stdout.flush()
                dm1 += 1.
            img = self.w.readfile(frame=t+self.skip).astype(float)
            if self.max_legendre > 0:
#               Compute residuals by subtracting off Legendre polynomial
#               terms of order one and higher.
                for m in xrange(1, self.beta.shape[0]):
                    img -= self.Adsgn[t, m]*self.beta[m,...]
            sumx += img
            sumxsq += img**2
        if self.verbose:
            sys.stdout.write('\n')
        sumx = sumx.reshape((self.zdim, self.ydim, self.xdim))
        sumxsq = sumxsq.reshape((self.zdim, self.ydim, self.xdim))

        imgout = zeros((3, self.zdim, self.ydim, self.xdim), float)
        imgout[0,...] = sumx/N
        
        imgout[1,...] = sqrt((N*sumxsq - sumx**2)/(N*(N - 1.)))
        imgout[1,...] = nan_to_num(imgout[1,...])
        snr_mean = imgout[0,...]
        mask = where(snr_mean > .1*snr_mean.max(), 1., 0.)
        meanval = (mask*snr_mean).sum()/mask.sum()
        mask = where(snr_mean > .5*meanval.max(), 1., 0.)
        mask *=  where(imgout[1,...] > 0., 1., 0.)

#       Don't mask off low snr values in the image
        msk = where(imgout[1,...] > 0, 1., 0.)
        imgout[2,...] = msk*imgout[0,...]/(imgout[1,...] + 1. - msk)

#       Omit low SNR values (which are mostly outside the brain) from the
#       mean snr calculation.
        self.mean_snr = (mask*imgout[2,...]).sum()/mask.sum()
        self.max_snr = (mask*imgout[2,...]).max()
        voxels = nonzero(mask.ravel())
        self.median_snr =median(imgout[2,...].ravel().take(voxels))
        self.stats_txt = ['Mean TSNR: %5.1f' %  self.mean_snr, \
                          'Max TSNR: %5.1f' % self.max_snr, \
                          'Median TSNR: %5.1f' % self.median_snr]
        f = open('%s.txt' % self.prefix, 'w')
        for line in self.stats_txt:
            if self.verbose:
                sys.stdout.write(line + '\n')
            f.write(line + '\n')
        f.close()
        return imgout

    def CreateDesignMatrix(self, N):
        """
        Create design matrix for model that includes Legendre polynomials of
        order zero through N.
        """
        tdim = self.tdim - self.skip
        x = 2.*(arange(tdim).astype(float))/(tdim - 1.) - 1.
        self.Adsgn = zeros([tdim, N],float)
        for n in xrange(N):
            xpow = ones(tdim)
            coeffs = legendre(n)
            for i in xrange(n+1):
                self.Adsgn[:, n] += coeffs[i]*xpow
                xpow *= x
        self.ATAm1AT = dot(inv(dot(self.Adsgn.T, self.Adsgn)), self.Adsgn.T)
#        f = open('/tmp/tmp.txt', 'w')
#        for t in xrange(tdim):
#            f.write('%f' % self.Adsgn[t, 0])
#            for n in xrange(1,N):
#                f.write('\t%f' % self.Adsgn[t, n])
#            f.write('\n')
#        f.close()

    def ComputeBeta(self):
        """
        Estimate the coefficients of the polynomial series.
        """
        M = self.Adsgn.shape[1]
        delta = float(self.tdim-self.skip)/80.
        dm1 = 1
        self.beta = zeros((M, self.xyzdim), float)
        if self.verbose:
            sys.stdout.write('Computing beta: ')
        for t in xrange(self.tdim - self.skip):
            if (t/delta) > dm1 and self.verbose:
                sys.stdout.write('.')
                sys.stdout.flush()
                dm1 += 1
            img = self.w.readfile(frame=t+self.skip).astype(float).\
                                                        reshape(self.xyzdim)
            for m in xrange(M):
                self.beta[m, :] += self.ATAm1AT[m, t]*img
        if self.verbose:
            sys.stdout.write('\n')
        self.beta = self.beta.reshape((M, self.zdim, self.ydim, self.xdim))
#        self.Write(self.beta, prefix='beta')

    def Write(self, image, prefix=None):
        """
        Write the mean, standard deviation, and tsnr images in nifti format.
        """
        hdrout = self.hdr.copy()
        hdrout['dims'][3] = image.shape[0]
        hdrout['datatype'] = 'float'
        hdrout['filetype'] = 'nii'
        writefile(prefix, image, hdrout)

        if self.verbose:
            print 'Mean/Std. Dev/SNR images written to %s.nii' % self.prefix

    def CreatePng(self, stats_img):
        """
        Write a summary png to disk.
        """
        p = PlotImage(width=9,height=9, colormap='gray', \
                                                    visible=self.verbose)
        imgslices = [('axial',.5,0),     ('axial',.5, 1),   ('axial',.5,2)]
        imgslices += [('sagittal',.5,0), ('sagittal',.5,1), ('sagittal',.5,2)]
        imgslices += [('coronal',.5,0),  ('coronal',.5,1),  ('coronal',.5,2)]

        fig_title = os.path.abspath(self.epifile)
        fig_title = '.../' + '/'.join(fig_title.split('/')[-4:])
        p.DrawReslice(3, 3, stats_img, self.hdr['orientation'], imgslices, \
                      xyzsize=self.hdr['sizes'][:3], \
                      xlabels=('Mean', 'Std. Dev.', 'TSNR'), \
                      fig_title=fig_title, scaling='column', \
                      middle96=True)
        maxval = 255./p.scale_factors[-1]
        tickvals = (50.*arange(int(maxval/50) + 1)).tolist()
        p.ColorBar(tickvals=tickvals, minval=0., maxval=maxval, \
                   tick_fmt='%3.0f', label='Temporal SNR')
        p.Footnote(self.stats_txt)
        p.WriteImage(self.prefix)
        if self.verbose:
            print 'Summary image written to %s.pdf' % self.prefix
            p.Show()

    def __call__(self):
        self.Process()

    def Process(self):
        if self.max_legendre > 0:
            self.CreateDesignMatrix(self.max_legendre)
            self.ComputeBeta()
        stats_image = self.ComputeTsnr()
        self.Write(stats_image, prefix=self.prefix)
        self.CreatePng(stats_image)
        self.Clean()

    def Clean(self):
        if self.mplconfigdir.startswith('/tmp') and \
                                    os.path.exists(self.mplconfigdir):
#       First delete all ordinary files and links.
            for dname, dnames, fnames in os.walk(self.mplconfigdir):
                for fname in fnames:
#                    print 100, 'Removing %s/%s' % (dname, fname)
                    os.remove('%s/%s' % (dname, fname))
#           Now remove all of the directories.
            os.removedirs(self.mplconfigdir)


def temporal_snr():
    ts = TemporalSnr()
    ts.Process()
    ts.Clean()

if __name__ == '__main__':
    temporal_snr()
