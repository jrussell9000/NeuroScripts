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



import sys
import os
from os import R_OK
from optparse import OptionParser
from subprocess import PIPE, Popen
from numpy import ones, zeros, nonzero, where, array
from file_io import Wimage, isdicom, writefile
from scipy.ndimage.morphology import binary_erosion,binary_dilation 
from scipy.ndimage.measurements import center_of_mass
from wbl_util import except_msg

ID = "$Id: make_siemens_fmap.py 25 2008-03-16 16:59:21Z jjo $"[1:-1]

DILATE_WIDTH = 5

def exec_cmd(cmd, verbose=False):
    if verbose:
        print cmd
    f = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, errs = f.communicate()
    if errs:
        raise RuntimeError('Error executing commands:\n\t%s\n\tError: %s'%\
                                                        (cmd, errs))
    return output

def make_fmap():
    usage = 'Usage: make_siemens_fmap input_dir output_file\n\tinput_dir is the directory above the directory containing the dicom files.\n\tdelta_te is the difference in echo times, (2.46 for the asthma \n\tstudy). input_dir is directory above the directories containing the \n\tfieldmap data, e.g. "anatomicals"'
    optparser = OptionParser(usage)
    optparser.add_option( "-t", "--tediff", action="store", dest="tediff",\
                    type="float",default=-1.,help="Delay between echos in ms." )
    optparser.add_option( "-v", "--verbose", action="store_true",  \
            dest="verbose",default=False,help="Verbose.")
    opts, args = optparser.parse_args()

    if len(args) != 2: # or opts.tediff < 1.:
        optparser.error( "Expecting at least 2 arguments and -t option:\n" + \
                         "Enter 'make_siemens_fmap --help' for more." )

    topdir = args[0]
    outfile = args[1]

    mag_dir_file = None
    phs_dir_file = None
    if not os.path.exists(topdir):
        raise RuntimeError( \
        'Top directory specified on command line does not exist.')
    for root,dirs,files in os.walk(topdir): #, followlinks=True):
        for fname in files:
            filename = '%s/%s' % (root, fname)
            if isdicom(filename):
                w = Wimage(filename)
                image_format =  w.hdr['native_header'].get('ImageFormat','')
                image_type =  w.hdr['native_header'].get('ImageType','Unknown')
                psd_name = w.hdr['native_header']. \
                                        get('InternalPulseSequenceName','')
                if 'fm2d2' in psd_name:
#                   This looks like valid fieldmap data - psd name matches.
                    if image_type == 'Phase':
                        print 'Found phase data: %s' % root
                        phs_dir_file = root
                    elif image_type == 'Magnitude':
                        print 'Found magnitude data: %s' % root
                        mag_dir_file = root
                    else:
                        raise RuntimeError( \
                        'make_siemens_fmap: Unrecognizable ImageType value ' + \
                        'for fieldmap data in %s'% filename)
                break

#   Read data from disk.
    if mag_dir_file is None:
        raise RuntimeError('Incomplete data. Could not find magnitude images.')
    if phs_dir_file is None:
        raise RuntimeError('Incomplete data. Could not find phase images')
    wm = Wimage(mag_dir_file,scan=True)
    wp = Wimage(phs_dir_file, scan=True)
    mhdr = wm.hdr.copy()
    mhdr['dims'][4] = 1
    mhdr['mdim'] = 1
    mhdr['dims'][3] = 1
    mhdr['tdim'] = 1
    mhdr['filetype'] = 'n+1'
    mhdr['datatype'] = 'float'
    mag = wm.readfile()
    if opts.tediff < 0:
        if mhdr['native_header'].has_key('EchoTimes'):
            echo_times = mhdr['native_header']['EchoTimes']
            tediff = abs(echo_times[1] - echo_times[0])
        else:
            raise RuntimeError('Could not find echo times in header.')
    else:
        tediff = opts.tediff
    print 'Echo time difference:%5.2fms' % tediff

#   Use bet the strip brain.
    fname = 'mag_tmp.nii'
    fname_strip = '%s_strip.nii' % os.path.splitext(fname)[0]
    mag = mag.squeeze().mean(0)
    writefile(fname, mag, mhdr)
    garbage = [os.path.abspath(fname)]
    
    bcmd = 'bet %s %s' % (fname, fname_strip)
#    print bcmd
    exec_cmd(bcmd, opts.verbose)
    if os.access(fname_strip + '.gz', R_OK):
        cmd = 'gunzip -f %s.gz' % fname_strip
#        print cmd
#        os.system(cmd)
        exec_cmd(cmd, opts.verbose)
    garbage.append(os.path.abspath(fname_strip))

#   Read stripped brain from disk
    ws = Wimage(fname_strip, scan=True)
    mag_strip = ws.readfile()
    if mag_strip is None:
        sys.stderr.write('\nmake_siemens_fmap: bet command failed:\n\t%s\n\n'%bcmd)
        sys.exit(-1)

#   Threshold and dilate.
    idx_nz = nonzero(mag_strip.ravel())
    avg = mag_strip.sum()/idx_nz[0].size
    mag_mask = where(mag_strip < .25*avg, 0., 1.)
    structure = ones([DILATE_WIDTH, DILATE_WIDTH, DILATE_WIDTH],float)
    mask = binary_dilation(mag_mask, structure,1).astype(float)
    mask_file = 'mask.nii'
    writefile(mask_file, mask, mhdr)
    garbage.append(os.path.abspath(mask_file))

#   Write masked magnitude to disk.
    mag_file = 'mag_masked.nii'
    mag_strip = mask*mag_strip
    writefile(mag_file, mag_strip, mhdr)
    garbage.append(os.path.abspath(mag_file))

#   Read the phase data from disk.
    phdr = wp.hdr.copy()
    phdr['filetype'] = 'n+1'
    phdr['datatype'] = 'float'
    phs = wp.readfile(dtype=float)

#   Rescale and mask phase as is done in Iowa script.
    phs = .00153436*mask*(phs - 2047.5)
    wphs_file = 'phs_masked.nii'
    writefile(wphs_file, phs, phdr)
    garbage.append(os.path.abspath(wphs_file))

#   Unwrap phases with prelude.
    uphs_file = 'phs_unwrapped.nii'
    cmd = 'prelude -p %s -a %s -o %s -f  -m %s' % \
                        (wphs_file, mag_file, uphs_file, mask_file)
#    print cmd
#    os.system(cmd)
    exec_cmd(cmd, opts.verbose)
    garbage.append(os.path.abspath(uphs_file))

#   Read unwrapped phase difference from disk.
    if os.access(uphs_file + '.gz', R_OK):
        cmd = 'gunzip -f %s.gz' % uphs_file
#        print cmd
#        os.system(cmd)
        exec_cmd(cmd, opts.verbose)
    wu = Wimage(uphs_file)
    uphs = wu.readfile()

#   Scale to radians/second. Add minus sign to account for opposite direction
#   of phase encode traversal.
    fmap = -1000.*uphs/opts.tediff

#   Compute centroid over the posterior 1/2 of the image.
    ydim = mhdr['ydim']
    skip = ydim/2
    centroid = center_of_mass(mag_strip[:,skip:,:]) + array([0., skip, 0.])
#    centroid = center_of_mass(mag)
    print 'Center of mass of posterior half of image at ',centroid
    zcom, ycom, xcom  = (centroid.round().astype(int)).tolist()
    com_value = fmap[zcom-1:zcom+2,ycom-1:ycom+2,xcom-1:xcom+2].mean()

    writefile(outfile, mask*(fmap - com_value), phdr)

    for fname in garbage:
        exec_cmd('/bin/rm %s' % fname)


if __name__ == '__main__':
    try:
        make_fmap()
    except:
        sys.stderr.write('%s\n' % except_msg())
        sys.exit(1)

