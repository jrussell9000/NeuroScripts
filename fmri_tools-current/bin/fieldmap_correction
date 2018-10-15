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
import string
from os import R_OK, W_OK, F_OK
import numpy
from numpy import *
from numpy import fliplr,flipud,median, floor, median
from file_io import writefile, afni_to_rot44, rot44_to_afni, Wimage, \
                    append_history_note, extlist, WriteBrik
from math  import pi
import scipy
from math_bic import resample_phase_axis,dezoom_2n,reslice,invert_rot44, \
                     print_matrix,dilate,reslice_3d
from scipy.ndimage import gaussian_filter
from scipy.ndimage.interpolation import map_coordinates
from scipy.ndimage.morphology import binary_erosion,binary_dilation

from optparse import OptionParser
import constants as c
import traceback
from wbl_util import except_msg, GetTmpSpace
from subprocess import Popen, PIPE

ID = "$Id: fieldmap_correction.py 647 2012-05-17 21:35:26Z vack $"[1:-1]

FMAP_DIM = 128  # Final resolution of field map images.

"""
Program: field_map_correction

Purpose: Correct for image distortion due to variation in the magnetic field.

Inputs: Image(s) to be corrected.
        Field map compute by make_fmap

By: John Ollinger

Date: 3/27/05
"""

class FieldmapCorrection():

    def __init__(self):
        self.tmp = GetTmpSpace(500)
        self.tmpdir = self.tmp()
        self.verbose = False

    def Initialize(self):

        u1 = "Usage: fieldmap_correction field_map echo_spacing_time output_path  input_files\n"
        u2 = "    field_map: File containing field map computed by make_fmap\n"
        u3 = "    echo_spacing: The time between" +\
             "        lines in the acquisition. (.688 ms for epibold). \n" +\
             "            this argument will be overwritten if there is a valid value in the image header.\n"
        u4 = "    output_path: Directory where the corrected file(s) go.\n"
        u5 = "    input_files: One or more EPI image files.\n"
        usage = u1+u2+u3+u4+u5
        optparser = OptionParser(usage)
        optparser.add_option( "-s", "--tag", action="store",dest="tag", \
                    type='string', default="_fm", \
                    help='Tag to be appended to end of output_filename.') 
        optparser.add_option( "-p", "--pepolar", action="store_true", \
                    dest="pepolar", default=False, \
                    help='Flip phase-encode direction if present.') 
        optparser.add_option( "", "--dilate-mask", action="store", \
                    dest="dilate_mask", default=0, type=int, \
                    help='Number of pixels to dilate mask.') 
        optparser.add_option( "", "--beautify", action="store_true", \
                    dest="beautify", default=False, \
                    help='Process edges of fieldmap to remove incorrect values at the edge of the image.') 
        optparser.add_option( "-D", "--dti", action="store_true", \
                    dest="pepolar", default=False, \
                    help='Use phase encode direction used by dti sequence. ' +\
                    'Has the same effect as pepolar. This option will be ' + \
                    'overridden by the value in the image header (which is ' +\
                    'not present in GE dicom images.') 
        optparser.add_option( "-f", "--flip_lrtb", action="store_true", \
                    dest="flip_lrtb",default=False, \
                    help='Flips the fieldmap images top-to-bottom and ' + \
                           'left-to-right before using them.  This useful for ' + \
                           'converting "analyze format" images that have not ' + \
                           'been flipped before storage.')
        optparser.add_option( "-t", "--output_format", action="store",  \
                    dest="output_format",type="string",default=None, \
                    help="Format of output images.  Options are 'brik','nii'," + \
                         "'analyze',and 'tes'.")
        optparser.add_option( "", "--phase-axis", action="store",  \
                    dest="phase_axis",type="string",default=None, \
                    help='Direction of phase-encode axis. Must be either "row" or "col"')
        optparser.add_option( "-m", "--mask", action="store_true", \
                    dest="mask",default=False, \
                    help='Applys a loose mask derived from the fieldmap.  A ' + \
                         'mask is first defined as all nonzero values of the ' + \
                         'fieldmap. Then it is dilated by 2 pixels and smoothed ' +\
                         'with a 2-pixel FWHM Gaussian.')
        optparser.add_option( "-v", "--verbose", action="store_true",  \
                    dest="verbose",default=False, \
                    help="Verbose output to terminal.")
        optparser.add_option( "", "--allow-negative", action="store_true",  \
                    dest="allow_negative",default=False, \
                    help="Don't set negative values to zero. (Cubic spline " + \
                    "interpolation can yield negative values in the " + \
                    "resampled images.)'")
        optparser.add_option( "-d", "--debug", action="store_true",  \
                    dest="debug",default=False, \
                    help="Debug mode. Write diagnostic images to disk.")

        self.opts, args = optparser.parse_args()

        if len(args) < 4:
            sys.stderr.write(usage)
            raise \
            SyntaxError("*** Expecting at least 4 arguments, got %d ***\n" % \
                                                            (len(args)))
        self.fmap_file = args[0]
        if not os.path.exists(self.fmap_file) and \
                os.path.exists(self.fmap_file + '.gz'):
            self.fmap_file = self.fmap_file + '.gz'

        self.secho_spacing = args[1]
        self.output_path = args[2]
        self.input_files = args[3:]
        self.input_files = []
        for fname in args[3:]:
            if fname.endswith('.BRIK'):
                self.input_files.append(fname[:-5])
            else:
                self.input_files.append(fname)
        if self.opts.pepolar:
            self.pepolar = 1
        else:
            self.pepolar = 0
        self.beautify = self.opts.beautify
        self.verbose = self.opts.verbose
        if not self.verbose:
            numpy.seterr(divide='ignore')
        self.phase_axis = self.opts.phase_axis
        self.dilate_mask = self.opts.dilate_mask
        self.allow_negative = self.opts.allow_negative

#       First print out the path for bug reports.
#        print os.path.getcwd()

#       Set default permission to 0775
        os.umask(0113)

        fsldir = c.FSLDIR
        os.putenv('FSLDIR',fsldir)
        os.putenv('PATH',"%s/bin:%s" % (fsldir,os.environ['PATH']))

#       Check paths for access..
        if not os.access(self.output_path,W_OK):
            raise IOError("\nfieldmap_correction: Output path is not " + \
                    "writeable: %s\n\n"  % self.output_path)
        for file in [self.fmap_file] + self.input_files:
            if file.endswith("+orig"):
                file = file + ".BRIK"
            if not os.access(file, R_OK):
                raise IOError( \
                '\nfieldmap_correction: Could not open "%s" Aborting ...\n\n' \
                % file)

    def LoadData(self):
#       Get header but do not scan. This will be done later.
        self.Wimg = Wimage(self.input_files[0],scan=True)
        self.hdr_epi = self.Wimg.hdr
        self.whdr_epi = self.hdr_epi['native_header']
        
        if self.whdr_epi.has_key('EffEchoSpacing'):
#       Get value from header.
            self.echo_spacing = float(self.whdr_epi.get('EffEchoSpacing',-1))/1000.
        else:
            self.echo_spacing = -1
        if self.echo_spacing < 0 and self.secho_spacing.replace(".","0").isdigit():
#       Use argument if valid.
            self.echo_spacing = float(self.secho_spacing)
            print "Using value of echo_spacing time from command line: %6.3f ms" % self.echo_spacing
        elif self.echo_spacing > 0:
            print "Using value of echo_spacing time from header: %6.3f ms" % self.echo_spacing
        else:
            sys.stderr.write("\nDwell time not in header, please specify on " + \
                             "command line.\n\n")
        
        self.Wfmap = Wimage(self.fmap_file,scan=True)
        self.fmap_hdr = self.Wfmap.hdr
        if self.fmap_hdr is not None:
            self.fmap = self.Wfmap.readfile()
        else:
            raise IOError( \
            "fieldmap_correction: Could not read %s" % self.fmap_file)
        self.R_fmap = self.fmap_hdr['R']
#        print_matrix(R_fmap,"R_fmap")
        if self.beautify:
            print 'Beautifying fieldmap ...'
            self.BeautifyFieldmap()


    def BeautifyFieldmap(self):
        zdim, ydim, xdim = self.fmap.shape
        eroded_mask = zeros(self.fmap.shape, float)
        mask = where(self.fmap == 0., 0., 1.)
        bandmask = zeros(self.fmap.shape, float)
        xfmap_erode7 = zeros(self.fmap.shape, float)
        for z in xrange(zdim):
            slcmsk = mask[z,...]
            bandmask[z,...] = slcmsk - binary_erosion(slcmsk, ones([15,15],float)).astype(float)
        self.WriteDebug('bandmask', self.fmap_hdr, bandmask)
        for z in xrange(zdim):
            fmap_slc = self.fmap[z,...].ravel()
            sbandmsk = bandmask[z,...].ravel()
            if sbandmsk.max() == 0:
                print 'Skipping slice ', z
                continue
            else:
                sys.stdout.write('.')
                sys.stdout.flush()
            fixed = zeros(ydim*xdim, float)
            slcmsk = mask[z,...]
            eroded_mask7 = binary_erosion(slcmsk, ones([15,15],float)).astype(float)
            eroded_mask3 = binary_erosion(slcmsk, ones([7,7],float)).astype(float)
            bandmsk3 = (slcmsk - eroded_mask3).ravel()
            fmap_erode7 = (self.fmap[z,...]*eroded_mask7)
            msk = where(fmap_erode7 != 0., 1., 0.)
            if msk.sum() == 0:
                continue
            xcg = int((arange(xdim)*msk.sum(1)).sum()/msk.sum())
            ycg = int((arange(ydim)*msk.sum(0)).sum()/msk.sum())
            fmap_erode7 = fmap_erode7.ravel()
            if fmap_erode7.min() == fmap_erode7.max() or bandmsk3.max == 0:
                continue
            voxels = nonzero(bandmsk3)[0]
            for vox in voxels.tolist():
                if bandmsk3[vox] == 0:
#                    sys.stdout.write('@')
#                    sys.stdout.flush()
                    continue
                yvox = int(vox/xdim)
                xvox = vox - yvox*xdim
                dx = xcg - xvox
                dy = ycg - yvox
                if dx > dy:
                    xvals = sign(dx)*arange(32)
                    yvals = (dy*xvals/dx + .5).astype(integer)
                    xvals += xvox
                    yvals += yvox
                else:
                    yvals = sign(dy)*arange(32)
                    xvals = (dx*yvals/dy + .5).astype(integer)
                    xvals += xvox
                    yvals += yvox
                msk = where(xvals > xdim-1, 0, 1)*where(xvals < 0, 0, 1)* \
                      where(yvals > ydim-1, 0, 1)*where(yvals < 0, 0, 1)
                xvals = xvals.take(nonzero(msk)[0])
                yvals = yvals.take(nonzero(msk)[0])
                coords = xdim*yvals + xvals
                msk = where(coords > xdim*ydim-1, 0, 1)*where(coords < 0, 0, 1)
                coords = coords.take(nonzero(msk)[0])
                if coords.size == 0:
                    continue
                values = fmap_erode7.take(coords)
                ivox = nonzero(values)[0]
                values = values.take(ivox)
                if values.size == 0:
                    continue
                idx = coords.take(ivox)
                yvals = (idx/xdim).astype(integer)
                xvals = idx - yvals*xdim
                dsq = (xvals - xvox)**2 + (yvals - yvox)**2
                nearest_vox = coords[dsq.argmin()]
                if fmap_slc[vox] > values.max() or fmap_slc[vox] < values.min():
#                    fixed[vox] = median(values)
                    fixed[vox] = values[0]
#                    fixed[vox] = fmap_erode7[nearest_vox]
                else:
                    fixed[vox] = fmap_slc[vox]
                bandmsk3[vox] = 0
            bandmsk3 = (slcmsk - eroded_mask3).ravel()
            self.fmap[z,...] = eroded_mask3*self.fmap[z,...] + (fixed*bandmsk3).reshape([ydim, xdim])
        self.WriteDebug('fmap_beautified', self.fmap_hdr, self.fmap)
        

    def PrepareFieldmap(self):

#       Reduce resolution to FMAP_DIM
        dezoom = self.fmap_hdr['xdim']/FMAP_DIM
        if dezoom > 1 and self.fmap_hdr['xdim'] == self.fmap_hdr['ydim'] and FMAP_DIM > self.hdr_epi['xdim']:
            self.fmap = dezoom_2n(self.fmap,dezoom)
            self.fmap_hdr['xdim'] =  self.fmap_hdr['xdim']/dezoom
            self.fmap_hdr['ydim'] =  self.fmap_hdr['ydim']/dezoom
            self.fmap_hdr['xsize'] = self.fmap_hdr['xsize']*dezoom
            self.fmap_hdr['ysize'] = self.fmap_hdr['ysize']*dezoom
            self.fmap_hdr['dims'][:2] =  self.fmap_hdr['dims'][:2]/dezoom
            self.fmap_hdr['sizes'][:2] = self.fmap_hdr['sizes'][:2]*dezoom

#       Reslice fmap.
        self.fmap1 = reslice_3d(self.fmap, self.fmap_hdr, self.hdr_epi)
        self.WriteDebug('fmap_reslice', self.fmap_hdr, self.fmap1)
        self.tightmask = where(self.fmap1 != 0., 1., 0.)

        dims = self.hdr_epi['dims']
        if self.opts.flip_lrtb:
#           Images stored in nonstandard orientation.  
#           Flip left to right and top to bottom.
            tmp = zeros([dims[1],dims[0]],float)
            for z in range(dims[2]):
                tmp[:,:] = flipud(self.fmap1[z,:,:])
                self.self.fmap1[z,:,:] = fliplr(tmp[:,:])

#       Create mask with smooth transition outside of valid fieldmap data.
        if self.opts.mask:
            self.mask = where(equal(self.fmap1, 0.), 0., 1.)
            N = self.dilate_mask + 5
            self.mask = dilate(self.mask,N, N, N)
            self.mask = gaussian_filter(self.mask, 2*c.fwhm2sg)
        else:
            self.mask = ones([dims[2],dims[1],dims[0]],float)

#       Convert field map to pixel positions by scaling
#       fmap in radians/sec to pixel offset in pixels.

#       Retrieve phase encode direction.
        if self.whdr_epi.has_key('PhaseEncDir'):
            PhaseEncDir =  self.whdr_epi.get('PhaseEncDir',None).lower()
        elif self.phase_axis is not None:
            PhaseEncDir =  self.phase_axis
        else:
            PhaseEncDir = None
        if PhaseEncDir is None:
            if 'axial' in self.hdr_epi['plane'] or \
               'coronal' in self.hdr_epi['plane']:
                PhaseEncDir = "col"
            else:
                PhaseEncDir = "row"

        if PhaseEncDir.strip() == "col":
            self.phase_axis = 1 # Along vertical (y) axis in image coordinates.
            base_pos = reshape(repeat(arange(dims[1]),dims[0]), \
                                    [dims[1],dims[0]]).astype(float)
            direction = -1
        elif PhaseEncDir.strip() == "row":
            self.phase_axis = 0 # Along horizontal (x) axis in image coordinates.
            base_pos = transpose(reshape(repeat(arange(dims[0]),dims[1]), \
                                           [dims[0],dims[1]]).astype(float))
            direction = 1
        else:
            raise ValueError( \
            "fieldmap_correction: Could not determine phase axis. (%s)\n" % \
                                                                PhaseEncDir)
        if self.hdr_epi['plane'] == 'coronal':
            direction = -direction


        if int(self.whdr_epi.get('PEPolar',self.pepolar)) > 0:
#           Phase encode direction reversed.
            direction = -direction

        if self.phase_axis:
            axis = "vertical (y)"
        else:
            axis = "horizontal (x)"
        print "Correcting the %s axis in raw image coordinates." % axis

        scl = direction*dims[1]*self.echo_spacing/(2*pi)/1000. 
        for z in range(dims[2]):
            self.fmap1[z,:,:] = scl*self.fmap1[z,:,:] + base_pos
        self.valid_mask = self.CreateValidVoxelMask(self.fmap1, self.phase_axis)

    def CorrectEPIs(self):
        "Correct each run specified on the command line."""
        for fname in self.input_files:
            print 'Processing %s' % fname
            if fname != self.input_files[0]:
                self.Wimg = Wimage(fname)
                hdr = self.Wimg.hdr
            else:
                hdr = self.hdr_epi
            if hdr is None:
                sys.stderr.write("fieldmap_correction: " + \
                "Could not read header from %s\n"%fname)
                continue

#           Get history note for use on output.
            if hdr['filetype'] == 'brik':
                old_history_note = hdr['native_header']['history_note']
            else:
                old_history_note = ''

            if self.opts.output_format is not None:
                self.output_format = self.opts.output_format
            else:
#               Default to input file type.
                self.output_format = hdr['filetype']
#                self.output_format = extlist.get(hdr['filetype'],'nii')[1:]
            hdrout = hdr.copy()
            xdim, ydim, zdim, tdim = hdr['dims'][:4]
            if hdr['filetype'] == 'tes':
                epiall = self.Wimg.readfile()
                if epiall is None:
                    raise IOError( \
                    "fieldmap_correction: Could not read %s" % self.fmap_file)
                s = shape(epiall)
                if (len(s) == 3):
                    tdim = s[0]/zdim
                elif (len(s) == 4 and s[0] == 1):
                    tdim = s[1]/zdim
                else:
                    tdim = s[0]
                epiall = reshape(epiall,[tdim,zdim,ydim,xdim]).astype(float)
            else:
                tdim = hdr['tdim']
            datatype = hdrout['datatype']
            if datatype == 'short':
                datatype = short
            elif datatype == 'byte':
                datatype = ubyte
            else:
                datatype = float
                
            output = zeros((zdim,ydim,xdim), datatype)
            for t in range(tdim):
                sys.stdout.write(".")
                sys.stdout.flush()
                if hdr['filetype'] == 'tes':
                    epi = epiall[t,:,:,:]
                else:
                    # print("Reading frame %s" % t)
                    epi = self.Wimg.readfile(frame=t, dtype=float)
                    if epi is None:
                        raise IOError( \
                              "fieldmap_correction: Could not read %s" % fname)
                for z in range(zdim):
                    output[z,:,:] = self.mask[z,:,:]* \
                      self.ResamplePhaseAxisCubic(epi[z,:,:], self.fmap1[z,:,:])
                output *= self.valid_mask.astype(int, casting='unsafe')
                if not self.allow_negative:
                    output = where(output < 0., 0, output).astype(datatype)
                self.WriteOutput(fname, hdrout, output, tdim, frame=t, \
                                 history_note=old_history_note)
            sys.stdout.write('\n')
            del output
            del epi

    def ResamplePhaseAxisCubic(self, image, pixpos):
        imgout = zeros(image.shape, float)
        ydim, xdim = image.shape

        if self.phase_axis == 0:
            ypos = arange(ydim).repeat(xdim)
            coords = [ypos.tolist(), pixpos.ravel().tolist()]
            imgout = map_coordinates(image, coords, order=3).reshape([ydim, xdim])
        elif self.phase_axis == 1:
            xpos = arange(ydim).repeat(xdim).reshape([ydim, xdim]).transpose().ravel()
            coords = [pixpos.ravel().tolist(), xpos.tolist()]
            imgout = map_coordinates(image, coords, order=3).reshape([ydim, xdim])
        return imgout

    def CreateValidVoxelMask(self, pixpos, axis):
        """
        Create mask by setting pixels outside the brain that were resampled inside
        the brain to zero.
        """
        zdim, ydim, xdim = pixpos.shape
        mask = zeros(pixpos.shape, float)
#        used_voxels_mask = zeros(pixpos.shape[2-axis], float)
        vals = ones(pixpos.shape[2-axis], float)
        for z in xrange(zdim):
            slcmask = zeros(pixpos.shape[1:], float)
#            pixmsk = where(self.tightmask[z,:,:] != 0., 1., 0.)
            pixmsk = self.tightmask[z,:,:]
            if axis == 1:
                for x in xrange(xdim):
                    ypixpos = pixmsk[:,x]*pixpos[z,:,x]
                    iposn = clip(floor(ypixpos).astype(int),0,ydim-2)
                    used_voxels = nonzero(iposn)[0]
                    used_voxels = unique(used_voxels.tolist() + (used_voxels+1).tolist())
                    mask[z,:,x] = self.CreateValidMask(used_voxels, pixmsk[:,x])
            elif axis == 0:
                for y in xrange(ydim):
                    ypixpos = pixmsk[y,:]*pixpos[z,y,:]
                    iposn = clip(floor(ypixpos).astype(int),0,xdim-2)
                    used_voxels = nonzero(iposn)[0]
                    used_voxels = unique(used_voxels.tolist() + (used_voxels+1).tolist())
                    mask[z,y,:] = self.CreateValidMask(used_voxels, pixmsk[y,:])
            else:
                raise RuntimeError(  \
                            'Argument "axis" can only take on values of 1 or 2')
#        self.WriteDebug('validmask', self.fmap_hdr, mask)
#        self.WriteDebug('tightmask', self.fmap_hdr, self.tightmask)
        return mask

    def CreateValidMask(self, used_voxels, pixmask):
        """
        Find voxels further from brain than the voxel that has been resampled 
        inside the brain that is nearest to the brain.
        """
        dim = pixmask.shape[0]
        if len(used_voxels) == 0:
            return zeros(dim, float)
        else:
            mask = ones(dim, float)
        brainvox = nonzero(pixmask)[0]
        if len(brainvox) == 0:
            return zeros(dim, float)

#       Create mask for voxels outside brain.
        used_voxels_array = array(used_voxels)
        firstmask = where(used_voxels_array < brainvox.min(), 1., 0.)
#       Find which of these voxels were used.
        valid = firstmask*used_voxels_array
        resamp_low = valid.take(nonzero(valid)[0])
#       Any voxel index less than this maximum is outside the resampled region.
        if resamp_low.size == 0:
            low_boundary = brainvox.min()
        else:
            low_boundary = resamp_low.max()

#       Now do the same for the other side.
        endmask = where(used_voxels_array > brainvox.max(), 1., 0.)
        valid = endmask*used_voxels_array
        resamp_high = valid.take(nonzero(valid)[0])
        if resamp_high.size == 0:
            high_boundary = brainvox.max()
        else:
            high_boundary = resamp_high.min()

        mask[high_boundary:] = 0.
        mask[:low_boundary+1] = 0.
        return mask


    def WriteOutput(self, fname, hdr, output, tdim, frame=None, \
                                                history_note=None):
        """ Write EPI run to disk."""
        if output.max() == 0.:
            raise RuntimeError('Output image sums to zero.')
#        basename = os.path.basename(fname)
#        name = os.path.splitext(basename)[0]
        name = (os.path.basename(fname)).replace(".nii",'')
        name = name.replace('+orig','')
        name = name.replace('+orig.HEAD','')
        name = name.replace('+orig.BRIK','')
        filename = "%s/%s%s" % (self.output_path,name,self.opts.tag)
        hdr['filetype'] = self.output_format
        hdr['dims'][3] = tdim
        hdr['dims'][4] = 1
        hdr['swap'] = 0
        if frame is None:
            writefile(filename, output, hdr)
        else:
            if self.output_format == 'brik':
                if frame == 0:
                    self.briks = WriteBrik(filename, hdr, output, frame)
                else:
                    self.briks.AddImage(output, frame, last=(frame==tdim-1), \
                                                    history_note=history_note)
            else:
                tmpname = filename
                writefile(tmpname, output, hdr,frame=frame,last=(frame==tdim-1))

    def ExecCmd(self, cmd, ignore_errors=False):
        if self.verbose:
            print cmd
        f = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        output, errs = f.communicate()
        if errs:
            print output
            if not ignore_errors:
                raise RuntimeError(\
                'Error executing commands:\n\t%s\n\tError: %s' % (cmd, errs))
            else:
                sys.stderr.write('%s\n' % errs)
        return output

    def WriteDebug(self, fname, hdr_template, image):
        if self.opts.debug:
            hdr = hdr_template.copy()
            keys = ('xdim', 'ydim', 'zdim', 'tdim', 'mdim')
            hdr['dims'] = []
            for i in xrange(image.ndim):
                hdr[keys[i]] = image.shape[-i-1]
                hdr['dims'].append(image.shape[-i-1])
            for i in xrange(image.ndim, 5, 1):
                hdr[keys[i]] = 1
                hdr['dims'].append(1)
            hdr['swap'] = 0
            if hdr['tdim'] > 1:
                for t in xrange(hdr['tdim']):
                    writefile(fname, image, hdr, frame=t, last=(t==hdr['tdim']-1))
            else:
                writefile(fname, image, hdr)
            print 'File written to %s' % fname

    def Cleanup(self):
#        print 'Not Cleaning up %s' % self.tmpdir
        self.tmp.Clean()


if __name__ == '__main__':
#   Set the process name.

    fmap = FieldmapCorrection()

    try:
        fmap.Initialize()
        fmap.LoadData()
        fmap.PrepareFieldmap()
        fmap.CorrectEPIs()
        sys.exit(0)
    except SystemExit:
        fmap.Cleanup()
    except:
        errstr = except_msg('fieldmap_correction')
        sys.stderr.write(errstr)
        sys.exit(1)
