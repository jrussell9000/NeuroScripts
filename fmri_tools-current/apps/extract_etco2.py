#!/usr/bin/env python

import sys
import os
import logging

import numpy as np

import bioread
from scipy.io import savemat
from scipy.ndimage import gaussian_filter, uniform_filter1d
from plotlib import ScatterPlot
from optparse import OptionParser
from wbl_util import except_msg, GetTmpSpace

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
window_len = 50000
start_pos = 110000
DEFAULT_SUBSAMPLE_RATE = 2


class ExtractETC02():

    def __init__(self):
        if __name__ == '__main__':
             self.GetOptions()

    def GetOptions(self):
        usage = 'extract_synced_etco2 [options] <biopac_file>\n' + \
                'Examples: \n' + \
                'extract_etco2 extract_etco2 <biopac_file>--TR=2000 --nframes=166\n' + \
                'extract_etco2 <biopac_file> --TR=2000 --nframes=166 -v --write-subsampled --prefix=tmp\n' + \
                'extract_etco2 <biopac_file> --TR=2000 --nframes=166 -v --read-subsampled=tmp_subsamp.txt --prefix=tmp\n' + \
                '\tEnter --help for options.'
        optparser = OptionParser(usage)
        optparser.add_option( "-v", "--verbose", action="store_true",  \
            dest="verbose",default=False, help="Verbose mode.")
        optparser.add_option( "", "--plot", action="store_true",  \
            dest="plot",default=False, help="Plot results.")
        optparser.add_option( "", "--write-mat", action="store_true",  \
            dest="write_mat",default=False, \
            help="Write temporally aligned data as a Matlab .mat file.")
        optparser.add_option( "", "--prefix", action="store", type=str,  \
            dest="prefix",default=None, help="Prefix for output files.")
        optparser.add_option( "", "--read-subsampled", action="store", \
            type=str,  dest="subsampled_file",default=None, \
            help="Read data from tab-delimited text file stored with the " + \
                 "--store_subsampled option.")
#        optparser.add_option( "", "--subsampled-file", action="store", \
#            type=str,  dest="subsampled_file",default=None, \
#            help="Tab-delimited text file containing processed, " + \
#                 "subsampled etco2 values.")
        optparser.add_option( "", "--resp-channel", action="store", \
            type=int, dest="resp_channel", default=0, \
            help="Biopac channel used for respiratory data.")
        optparser.add_option( "", "--etco2-channel", action="store", \
            type=int, dest="etco2_channel", default=2, \
            help="Biopac channel for etco2 data.")
        optparser.add_option( "", "--ttl-channel", action="store", \
            type=int, dest="ttl_channel", default=3, \
            help="Biopac channel used for ttl data.")
        optparser.add_option( "", "--TR", action="store", \
            type=float, dest="TR", default=None, \
            help="TR in ms.")
        optparser.add_option( "", "--nframes", action="store", \
            type=int, dest="nframes", default=None, \
            help="Number of frames in a run.")
        optparser.add_option( "", "--write-subsampled", action="store_true",  \
            dest="write_subsampled",default=False, \
            help="Write etco2 data at the reduced sampling rate given by " + \
                 "the --subsample-rate option.")
        optparser.add_option( "", "--subsample-rate", action="store", \
            type=float, dest="subsample_rate", default=DEFAULT_SUBSAMPLE_RATE, \
            help="Sampling rate of intermediate data written out when the " + \
                 "--write-subsampled option is present. " + \
                 "Default value is %1.3f seconds." % DEFAULT_SUBSAMPLE_RATE)
        opts, args = optparser.parse_args()

        if len(args) != 1:
            print usage
            sys.exit(1)

        self.biopac_file = args[0]
        if opts.prefix is None:
            self.prefix = '%s_etco2' % self.biopac_file.replace('.acq','')
        else:
            self.prefix = opts.prefix
        self.verbose = opts.verbose
        self.ttl_channel = opts.ttl_channel
        self.resp_channel = opts.resp_channel
        self.etco2_channel = opts.etco2_channel
        self.plot = opts.plot
        self.TR = opts.TR/1000.
        self.nframes = opts.nframes
        self.write_mat = opts.write_mat
        self.write_subsampled = opts.write_subsampled
        self.subsample_rate = opts.subsample_rate
        self.subsampled_file = opts.subsampled_file

    def ExtractData(self):
        corr_data = np.zeros(2000, dtype=float)

        logging.info("Reading %s" % self.biopac_file)
        if self.biopac_file.endswith('.gz'):
            import gzip
            f = gzip.GzipFile(self.biopac_file, 'r')
            tmp = GetTmpSpace(500)
            tmpfile = '%s/tmp_biopac' % tmp.tmpdir
            fout = open(tmpfile, 'w')
            fout.write(f.read())
            f.close()
            fout.close()
            data = bioread.read_file(tmpfile)
            tmp.Clean()
        else:
            data = bioread.read_file(self.biopac_file)
            f = open(self.biopac_file, 'r')
#        data = bioread.read_file(f)
        f.close()

        resp = data.channels[self.resp_channel].data
        etco2 = data.channels[self.etco2_channel].data_proportion*\
                                    data.channels[self.etco2_channel].data
        ttl_data = data.channels[self.ttl_channel].data
        self.sampling_rate = data.channels[self.etco2_channel].samples_per_second

        ttl_min = np.min(ttl_data)
        ttl_max = np.max(ttl_data)
        d_ttl_thresh = (ttl_max-ttl_min)/2.0

        d_ttl = np.diff(ttl_data)

        start_sample = np.flatnonzero(d_ttl >= d_ttl_thresh)[0]
        end_sample = np.flatnonzero(d_ttl <= -d_ttl_thresh)[-1]
        logging.debug("TTL start: %s end %s" % (start_sample, end_sample))

        logging.debug("\t".join(["i", "corr", "abs_corr", "max_corr", "max_corr_i"]))
        resp_start = start_pos
        resp_end = start_pos + window_len
        resp_window = resp[resp_start:resp_end]
        max_corr = 0.0
        max_corr_i = 0
        for i in range(6000,8000):
            co2_start = resp_start + i
            co2_end = resp_end + i
            co2_window = etco2[co2_start:co2_end]
            matrix = np.corrcoef(np.vstack([resp_window, co2_window]))
            corr = matrix[0,1]
            abs_corr = np.abs(corr)
            if abs_corr > max_corr:
                max_corr = max(max_corr, abs_corr)
                max_corr_i = i
            logging.debug("\t".join([str(e) for e in [i, corr, abs_corr, max_corr, max_corr_i]]))
            corr_data[i-6000] = corr

        best_start = start_sample + max_corr_i
        best_end = end_sample + max_corr_i
        logging.debug("Best data match from indexes %s to %s" % \
                                                    (best_start, best_end))
        return etco2[best_start:best_end] - etco2[best_start:best_end].mean()

    def Filter(self, data):
        N = data.shape[0]

#       Find leading and trailing edges of each positive epoch.
        lthresh = data.min() + (data.max() - data.min())/4.
        lthresh = 0
        msk1 = np.where(data[0:-1] > lthresh, 1., 0.)
        msk2 = np.where(data[1:] > lthresh, 1., 0.)
        leading_edges = np.nonzero(np.where(msk2 - msk1 == 1, 1., 0.))[0]
        trailing_edges = np.nonzero(np.where(msk1 - msk2 == 1, 1., 0.))[0]
        if trailing_edges[0] < leading_edges[0]:
            trailing_edges = trailing_edges[1:]
        if len(leading_edges) > len(trailing_edges):
            trailing_edges = trailing_edges + [N-1]
        leading_edges = np.array(leading_edges)
        trailing_edges = np.array(trailing_edges)
        Nexpire = len(trailing_edges)

#       Filter the data by a width of 1/8 an epoch to suppress short breaths.
        mean_epoch_lgth = (leading_edges[1:] - leading_edges[:-1]).mean()
        filter_width = int(round(mean_epoch_lgth/8.))
        data1 = uniform_filter1d(data, filter_width)

# Recalculate the epochs.
        N = data1.shape[0]
        lthresh = data1.min() + (data1.max() - data1.min())/4.
        msk1 = np.where(data1[0:-1] > lthresh, 1., 0.)
        msk2 = np.where(data1[1:] > lthresh, 1., 0.)
        leading_edges = np.nonzero(np.where(msk2 - msk1 == 1, 1., 0.))[0]
        trailing_edges = np.nonzero(np.where(msk1 - msk2 == 1, 1., 0.))[0]
        if trailing_edges[0] < leading_edges[0]:
            trailing_edges = trailing_edges[1:]
        if len(leading_edges) > len(trailing_edges):
            trailing_edges = trailing_edges.tolist() + [N-1]
        leading_edges = np.array(leading_edges)
        trailing_edges = np.array(trailing_edges)
        Nexpire = len(trailing_edges)

# Now replace value for each breath with its maximum.
        values = []
        for ibreath in xrange(Nexpire):
            le = leading_edges[ibreath]
            te = trailing_edges[ibreath]
            values.append(data[le:te].max())
        values = np.array(values)

        proc_etco2 = np.zeros(N, float)
        for ibreath in xrange(Nexpire):
            le = leading_edges[ibreath]
            if ibreath < Nexpire-1:
                le1 = leading_edges[ibreath+1]
            else:
                le1 = N
            proc_etco2[le:le1] = values[ibreath]

        if leading_edges[0] > 0:
#           Copy later value in initial range if sequence starts on exhale.
            proc_etco2[:leading_edges[0]] = values[0]

#       Smooth the piecewise constant result.
        fwhm = mean_epoch_lgth/2.
        sigma = .42466*fwhm
        proc_etco2 = gaussian_filter(proc_etco2, sigma)

        data = {'sampling_rate': self.sampling_rate, 'etco2': proc_etco2}
    
        return data

    def GetYcoord(self, data, npts):
        N = data.shape[0]
        idx = (N*np.arange(npts)/float(npts)).astype(int)
        return data.take(idx)

    def PlotEtco2(self, raw_etco2, etco2_data, regressor):
        proc_etco2 = etco2_data['etco2']
        sampling_rate =  etco2_data['sampling_rate']
        N = proc_etco2.shape[0]
        Nplot = 1000
        p = ScatterPlot(2, 1, height=4, width=10, suptitle=self.prefix, visible=self.plot)
        x_coord = np.arange(N)/sampling_rate
        p.AddPlot((float(N)/Nplot)*np.arange(Nplot)/sampling_rate, \
                 self.GetYcoord(proc_etco2, Nplot), \
                 lineonly=True, \
                 x_label='Time in Seconds', \
                 y_label='Processed End Tidal CO2')
        if raw_etco2 is not None:
            p.AddPlot((float(N)/Nplot)*np.arange(Nplot)/self.sampling_rate, \
                 self.GetYcoord(raw_etco2, Nplot), \
                 lineonly=True, \
                 overplot=True, \
                 x_label='Time in Seconds', \
                 y_label='Raw End Tidal CO2')
        p.AddPlot(self.TR*np.arange(self.nframes), \
                 regressor, \
                 lineonly=False, \
                 markerin='circle', \
                 overplot=False, \
                 x_label='Time in Seconds', \
                 y_label='Raw End Tidal CO2')
        p.WritePlot(self.prefix, filetype='png')
        if self.plot:
            p.Show()

    def WriteData(self, raw_etco2, proc_etco2, regressor):

        if self.write_mat:
#           Write data to a .mat file.
            data_out = {'sample_rate_Hz': self.sampling_rate, \
                        'raw_data': raw_etco2, \
                        'etco2': proc_etco2}
            fname = os.path.abspath(self.prefix) + '.mat'
            savemat(fname, data_out, oned_as='column', do_compression=True)

#       Write the regressor as an afni 1D file.
        fname = self.prefix + '.1D'
        f = open(fname, 'w')
        for i in xrange(regressor.shape[0]):
            f.write('%s\n' % regressor[i])
        f.close()

    def WriteSubsampled(self, etco2):
        sampling_rate = etco2['sampling_rate']
        etco2 = etco2['etco2']
        if self.subsample_rate > self.sampling_rate:
            raise RuntimeError( \
            'Subsample rate (%f) is larger than raw sampling rate (%f)' % \
                                (self.subsample_rate, self.sampling_rate))
        stride = self.sampling_rate/self.subsample_rate
        fname = '%s_subsamp.txt' % self.prefix
        f = open(fname, 'w')
        f.write('Time (sec)\tetCO2\n')
        it = 0.
        etco2_subsamp = []
        while it < etco2.shape[0]:
            delta = (it - float(int(it)))/self.subsample_rate
            t = it/self.sampling_rate
            etco2_sub = ((1. - delta)*etco2[int(it)] + delta*etco2[int(it)+1])
            f.write('%f\t%f\n' % (t, etco2_sub))
            it += stride
        f.close()

    def ReadSubsampled(self):
        f = open(self.subsampled_file, 'r')
        data = f.read()
        if '\r' in data:
#           Windows format
            lines = data.split('\r')
        else:
#           Unix format
            lines = data.split('\n')
        f.close()
        etco2 = []
        for line in lines[1:]:
            wds = line.split()
            etco2.append(float(wds[1]))
        sampling_rate = 1./(float(lines[2].split()[0]) - \
                                            float(lines[1].split()[0]))
        data = {'sampling_rate': sampling_rate, 'etco2': np.array(etco2)}
        return data

    def CreateRegressor(self, etco2):
        sampling_rate = etco2['sampling_rate']
        proc_etco2 = etco2['etco2']
        idx = (sampling_rate*self.TR*np.arange(self.nframes)).astype(int)

#       Make sure we don't read past the end of the data.
        max_idx = idx.shape[0]
        while idx[max_idx-1] > proc_etco2.shape[0] - 1:
#           etco2 data end early.
            max_idx -= 1
        idx = idx[:max_idx]
        nsamp = idx.shape[0] - 1
        N = proc_etco2.shape[0]
        stride = float(N)/float(nsamp)

        regressor = np.zeros(self.nframes, float)
        regressor[:max_idx] = proc_etco2.take(idx)

#       Extend regressor by copying last value.
        regressor[max_idx:] = regressor[max_idx-1]
        regressor -= regressor.mean()
        regressor *= 1./abs(regressor).max()
        return regressor

    def Process(self):
        if self.subsampled_file is not None:
#           Data have been filtered and subsampled for hand-editing. Read
#           the hand-edited data.
            raw_etco2 = None
            proc_etco2 = self.ReadSubsampled()
        else:
            raw_etco2 = self.ExtractData()
            proc_etco2 = self.Filter(raw_etco2)
        if self.write_subsampled:
            proc_etco2 = self.WriteSubsampled(proc_etco2)
        else:
            regressor = self.CreateRegressor(proc_etco2)
            self.WriteData(raw_etco2, proc_etco2, regressor)
            self.PlotEtco2(raw_etco2, proc_etco2, regressor)

def extract_etco2():
    try:
        ee = ExtractETC02()
        ee.Process()
    except (IOError, RuntimeError, OSError), errmsg:
        sys.stderr.write('\n%s\n%s\n' % (errmsg, except_msg()))
        sys.exit(1)

if __name__ == '__main__':
    extract_etco2()

