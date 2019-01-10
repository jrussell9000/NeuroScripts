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

ID = "$Id: math_bic.py 583 2011-07-08 18:47:42Z jmo $"[1:-1]

import sys
import string
import os
import struct
from numpy import *
from numpy.linalg import det,inv

from scipy.special.basic import erfcinv, erfinv
from scipy.special import stdtr, fdtr, fdtri, stdtrit, ndtr
#from levmar import levmar_der

try:
#    import geio
    from geio import pyreslice_3d, pyextent_threshold
except ImportError:
    def pyreslice_3d(data_type,  Rtot, dims_out):
#        sys.stderr.write("_reslice_3d is not available on this system.\n")
        raise OSError("_reslice_3d is not available on this system.\n")
    def pyextent_threshold(dumm1, dummy2, dummy3, dummy4):
        raise OSError("_extent_threshold is not available on this system.\n")
#        sys.stderr.write("_extent_threshold is not available on this system\n")
#        return None

import file_io
import constants as c

import scipy
import scipy.signal
from scipy.stats.stats import histogram2
from scipy import ndimage
from scipy.ndimage import gaussian_filter, uniform_filter
from scipy.ndimage.morphology import binary_erosion,binary_dilation

from scipy.special.basic import erfcinv, erfinv
from scipy.special import stdtr, fdtrc,ndtr

ID = "$Id: math_bic.py 583 2011-07-08 18:47:42Z jmo $"[1:-1]


#*********************
def invert_xform(xfm):
#*********************

# Invert affine 4x4 transformation matrix.

    r = xfm[0:3,0:3]
    rm1 = inv(r)
    dx = xfm[:3,3]
    dxm1 = -dot(rm1,dx)
    inv = zeros((4,4)).astype(float)
    inv[:3,:3] = rm1
    inv[:3,3] = dxm1
    inv[3,3] = 1.

    return inv


#*************************************************
def clip_sinuses(input_file,output_file,skip,lcv):
#*************************************************

# Usage: clip_sinuses input_image output_image
# Extract brain and then sets image to zero for inferior non-brain regions.

    dot = string.find(input_file,".img")
    if(dot < 0):
        dot = string.find(input_file,".hdr")
    if dot < 0:
        stem = input_file
    else:
        stem = input_file[0:dot]
    
#     Extract brains.
    brain_file = stem + "_brain.img"
    cmd = "bet %s %s" % (input_file,brain_file)
    file_io.exec_cmd(cmd)
    
    brain_data = file_io.read_file(brain_file)
    brain_hdr = brain_data['header']
    brain_image = brain_data['image']

    data = file_io.read_file(input_file)
    hdr = data['header']
    image = data['image']

    brain_data = file_io.read_file(brain_file)
    brain_hdr = brain_data['header']
    brain_image = brain_data['image']

    xdim = brain_hdr['xdim']
    ydim = brain_hdr['ydim']
    zdim = brain_hdr['zdim']

    brain_image = reshape(brain_image,(zdim,ydim,xdim))
    image = reshape(image,(zdim,ydim,xdim))

    profile = sum(brain_image,2)
    profile_mask = where(greater(profile,0.),1.,0.)

    ramp = ydim -1 - arange(ydim)
    mn = zeros(zdim)
    for slc in range(zdim):
        mn[slc] = argmax(ramp*profile_mask[slc,:])
    minmin = mn[argmin(mn)]

    ydim = ydim - minmin
    img = zeros((zdim,ydim,xdim)).astype(float32)
    img[:,:,:] = brain_image[:,minmin:,:]

    hdr['ydim'] = ydim
    file_io.write_analyze(output_file,hdr,img)

    return ydim



#************************************************************
def create_transform(dx,dy,dz,roll,pitch,yaw,xscl,yscl,zscl):
#************************************************************

# Create transformation matrix.

    D2R = math.pi/180.
    A = identity(3).astype(float)
    B = identity(3).astype(float)

    B[1,1] =  cos(pitch*D2R)
    B[1,2] =  sin(pitch*D2R)
    B[2,1] = -sin(pitch*D2R)
    B[2,2] =  cos(pitch*D2R)
    AX = dot(A,B)
    
    B = identity(3).astype(float)
    B[0,0] =  cos(roll*D2R)
    B[0,2] =  sin(roll*D2R)
    B[2,0] = -sin(roll*D2R)
    B[2,2] =  cos(roll*D2R)
    A = dot(AX,B)

    B = identity(3).astype(float)
    B[0,0] =  cos(yaw*D2R)
    B[0,1] =  sin(yaw*D2R)
    B[1,0] = -sin(yaw*D2R)
    B[1,1] =  cos(yaw*D2R)
    AX = dot(A,B)

    B = identity(3).astype(float)
    B[0,0] = xscl
    B[1,1] = yscl
    B[2,2] = zscl
    A = transpose(dot(AX,B))

    offset = zeros(3).astype(float)
    offset[0] = dx
    offset[1] = dy
    offset[2] = dz
    off1 = dot(A,offset)

    xfm = identity(4).astype(float)
    xfm[:3,:3] = A
    xfm[:3,3] = off1[:]

    return xfm
    
#**************************************************
def resample_phase_axis(input_image,pixel_pos,axis):
#**************************************************

# Purpose: Resample along phase encode axis of epi images. It is assumed that the phase encode axis is the last (fastest varying) axis in the input image.

# Inputs: input_image: Epi image to be resampled.
#         pixel_pos: Image of resampled pixel positions.
#         axis: 0=x-axis, 1=y-axis
#         direction: 1 if pe_polar=0; -1 if pe_polar=1

    shp = input_image.shape
    ndim = len(shp)
    xdim = shp[1]
    if ndim == 2:
        ydim = shp[0]
        output_image = zeros((ydim,xdim)).astype(input_image.dtype.char)
    elif ndim == 1:
        ydim = 1
        output_image = zeros((xdim)).astype(input_image.dtype.char)
    else:
        print 'math_bic: Resample phase axis can only handle 1D or 2D input arrays.'
        sys.exit(1)

    if (axis):
        delta = zeros((ydim)).astype(float)
        dim = ydim
    else:
        delta = zeros((xdim)).astype(float)
        dim = xdim
    for x in range(dim):
        if ndim == 1:
            vals = input_image[:]
            y = pixel_pos[:]
        elif ndim == 2:
            if (axis):
                vals = input_image[:,x]
                y = pixel_pos[:,x]
            else:
                vals = input_image[x,:]
                y = pixel_pos[x,:]
        iy = clip(floor(y).astype(int),0,dim-2)
        delta = y - iy
        if ndim == 1:
            output_image[:] = (1.-delta)*take(vals,iy) + delta*take(vals,iy+1)
        elif ndim == 2:
            if (axis):
                output_image[:,x] = (1.-delta)*take(vals,iy) + delta*take(vals,iy+1)
            else:
                output_image[x,:] = (1.-delta)*take(vals,iy) + delta*take(vals,iy+1)

    return output_image

#*******************************************
def inverse_fft3d(image,verbose,save_kspace):
#*******************************************

# Invert affine 4x4 transformation matrix.

    shp = shape(image)
    xdim = shp[2]
    ydim = shp[1]
    zdim = shp[0]

    kimg = zeros((zdim,ydim,xdim)).astype(Complex)

#   First transform along the axial dimension.
    tmp = zeros((zdim)).astype(Complex)
    for y in range(ydim):
        if verbose:
            sys.stdout.write(".")
            sys.stdout.flush()
        for x in range(xdim):
            tmp[:] = image[:,y,x]
            ktmp = FFT.inverse_fft(tmp)
            kimg[:,y,x] = ktmp[:]

    if save_kspace:
###        file_io.dump_image("kspace_mag.4dfp.img",abs(kimg),xdim,ydim,zdim,1,1,1,1,0,0)
        img_file = "kspace_mag.img"
        hdr = file_io.create_hdr(xdim,ydim,zdim,1,1.,1.,1.,1.,0,0,0,'Short',16,1.,'analyze',img_file,0)
        file_io.write_analyze(img_file,hdr,abs(kimg))

#   Now do an in-plane 2D fft.
    tmp = zeros((ydim,xdim)).astype(Complex)
    for z in range(zdim):
        if verbose:
            sys.stdout.write(".")
            sys.stdout.flush()
        tmp[:,:] = kimg[z,:,:]
        image = FFT.inverse_fft2d(tmp)
        kimg[z,:,:] = image
    sys.stdout.write("\n")


    return kimg


#***************************
def shift(matrix,axis,shft):
#***************************

# axis: Axis of shift: 0=x (rows), 1=y (columns),2=z
# shft: Number of pixels to shift.

    dims = matrix.shape
    ndim = len(dims)
    if globals().has_key('numpy'):
        tcode = matrix.dtype.char
    else:
        tcode = matrix.dtype.char
    if ndim == 1:
        tmp = zeros((shft),tcode)
        tmp[:] = matrix[-shft:]
        matrix[-shft:] = matrix[-2*shft:-shft]
        matrix[:shft] = tmp
    elif ndim == 2:
        ydim = dims[0]
        xdim = dims[1]
        tmp = zeros((shft),tcode)
        new = zeros((ydim,xdim),matrix.dtype.char)
        if(axis == 0):
            for y in range(ydim):
                tmp[:] = matrix[y,-shft:]
                new[y,shft:] =  matrix[y,:-shft]
                new[y,:shft] = matrix[y,-shft:]
            matrix[:,:] = new[:,:]
        elif(axis == 1):
            for x in range(xdim):
                new[shft:,x] =  matrix[:-shft,x]
                new[:shft,x] = matrix[-shft:,x]
            matrix[:,:] = new[:,:]
    elif ndim == 3:
        zdim = dims[0]
        ydim = dims[1]
        xdim = dims[2]
        new = zeros((zdim,ydim,xdim),tcode)
        if(axis == 0):
            tmp = zeros((zdim,ydim,shft),tcode)
            tmp[:,:,:] = matrix[:,:,-shft:]
            new[:,:,shft:] =  matrix[:,:,:-shft]
            new[:,:,:shft] = matrix[:,:,-shft:]
        elif(axis == 1):
            tmp = zeros((zdim,shft,xdim),tcode)
            tmp[:,:,:] = matrix[:,-shft:,:]
            new[:,shft:,:] =  matrix[:,:-shft,:]
            new[:,:shft,:] = matrix[:,-shft:,:]
        elif(axis == 2):
            tmp = zeros((shft,ydim,xdim),tcode)
            tmp[:,:,:] = matrix[-shft:,:,:]
            new[shft:,:,:] =  matrix[:-shft,:,:]
            new[:shft,:,:] = matrix[-shft:,:,:]
        matrix[:,:,:] = new[:,:,:]
    else:
        print "math_bic: shift() only support 1D, 2D, and 3D arrays."
        sys.exit(1)
    return new

#*************
def factor(N):
#*************

# Compute factors of N.

#    sys.stdout.write("%d: e % N)
    if N > 0:
        f = [1]
    elif N == 0:
        return([0])
    else:
        f = [-1]

    fp = 2
    Np = N
    while Np != 1:
#       Loop until all factors are found
#        print "Np: ",Np#,f
        while (Np % fp != 0) and (fp < N):
#           Loop until fp is a factor.
            fp = fp + 1
#            print "Np%fp: ",fp%Np
        f = f + [fp]  # Add this factor to the list.
        Np = Np/fp
#        print "Np: ",N,Np,fp
#        print "Np%fp: ",fp%N#,f
#        return(f)

    return(f)

#***************************
def polar(image,four_quad=1):
#***************************

# Compute phase from a complex number.
# four_quad = 1: Compute 4-quadrant arctan, otherwise phs is in [-pi/2,pi/2)

    if four_quad:
        phs = scipy.arctan2(image.imag,image.real)
    else:
        msk = where(equal(image.real,0.),1.,0.)
        phs = ((1.-msk)*arctan(image.imag/(image.real+msk))).astype(float)

    return(phs,abs(image))

#****************************
def phase(image,four_quad=1):
#****************************

# Compute phase from a complex number.
    if four_quad:
        phs = scipy.arctan2(image.imag,image.real)
    else:
        msk = where(equal(abs(image),0.),1.,0.)
        phs = ((1.-msk)*arctan(image.imag/(image.real+msk))).astype(float)

    return(phs)

#***************************************************
def smooth_gauss_2d(image,fwhm,xsize,ysize,frame=1):
#***************************************************


    sigma = c.fwhm2sg*fwhm
    s = shape(image)
    if len(s) == 4:
        tdim = s[0]
        zdim = s[1]
        ydim = s[2]
        xdim = s[3]
    elif len(s) == 3:
        tdim = 1
        zdim = s[0]
        ydim = s[1]
        xdim = s[2]
    elif len(s) == 2:
        tdim = 1
        zdim = 1
        ydim = s[0]
        xdim = s[1]
    else:
        print "math_bic: Image must have at least two dimensions."
        return(-1)
    if fwhm==0.:
        return(image)
    if tdim > 1:
        img = image[frame,:,:,:]
    else:
        img = image
    for t in range(tdim):
         jmg[t,:,:,:] = gaussian_filter(img[t,:,:,:],[1., sigma, sigma])
    if tdim == 1:
        jmg = reshape(jmg,(zdim,ydim,xdim))
    if zdim == 1:
        jmg = reshape(jmg,(ydim,xdim))
    return(jmg)

#*********************************************
def smooth_box(image,x_width,y_width,z_width):
#*********************************************

#   Smooth  2D or 3D image with a box filter of width x_width by y_width by z_width

    return uniform_filter(image,[x_width, y_width, z_width])


#************************************************************
def smooth_gauss_3d(image,fwhm,xsize,ysize,zsize,frame=None):
#************************************************************

#   Filter image with an isotropic 3D Gaussian kernel.


    sigma = c.fwhm2sg*fwhm
    return gaussian_filter(image, sigma)



#****************
def ltqnorm( p ):
#****************
    """
    Modified from the author's original perl code (original comments follow below)
    by dfield@yahoo-inc.com.  May 3, 2004.

    Lower tail quantile for standard normal distribution function.

    This function returns an approximation of the inverse cumulative
    standard normal distribution function.  I.e., given P, it returns
    an approximation to the X satisfying P = Pr{Z <= X} where Z is a
    random variable from the standard normal distribution.

    The algorithm uses a minimax approximation by rational functions
    and the result has a relative error whose absolute value is less
    than 1.15e-9.

    Author:      Peter J. Acklam
    Time-stamp:  2000-07-19 18:26:14
    E-mail:      pjacklam@online.no
    WWW URL:     http://home.online.no/~pjacklam
    """

    mask = where(p > 0.,.5,0.)
    p = p + (.5-mask)
    mask = where(p == 1.,1.e-15,0.)
    p = p - mask
    pmin = p[argmin(p)]
    pmax = p[argmax(p)]
#   Replace zeros with valid numbers then zero them out at the end.
    if pmin < 0 or pmax > 1:
        # The original perl code exits here, we'll throw an exception instead
        raise ValueError( "Argument to ltqnorm with min %f and max %f must be in open interval (0,1)" % (pmin,pmax) )

    # Coefficients in rational approximations.
    a = (-3.969683028665376e+01,  2.209460984245205e+02, \
         -2.759285104469687e+02,  1.383577518672690e+02, \
         -3.066479806614716e+01,  2.506628277459239e+00)
    b = (-5.447609879822406e+01,  1.615858368580409e+02, \
         -1.556989798598866e+02,  6.680131188771972e+01, \
         -1.328068155288572e+01 )
    c = (-7.784894002430293e-03, -3.223964580411365e-01, \
         -2.400758277161838e+00, -2.549732539343734e+00, \
          4.374664141464968e+00,  2.938163982698783e+00)
    d = ( 7.784695709041462e-03,  3.224671290700398e-01, \
          2.445134137142996e+00,  3.754408661907416e+00)

    # Define break-points.
    plow  = 0.02425
    phigh = 1 - plow

    # Rational approximation for lower region:
    if p < plow:
       q  = sqrt(-2*log(p))
       return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)

    # Rational approximation for upper region:
    if phigh < p:
       q  = sqrt(-2*log(1-p))
       return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)

    # Rational approximation for central region:
    q = p - 0.5
    r = q*q
    z =  (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    return(z*mask)

#----------------------
def find_center(image):
#----------------------

#   Image is a 2D image.

#   Define center of phantom as its center of mass.
    sumimg = sum(image.flat)
    s = shape(image)
    ydim = s[0]
    xdim = s[1]
    sumx = 0
    for x in range(xdim):
        sumx = sumx + x*sum(image[:,x])
    y0 = int(round(sumx/sumimg))
    sumy = 0
    for y in range(ydim):
        sumy = sumy + y*sum(image[y,:])
    x0 = int(round(sumy/sumimg))

    return((x0,y0))

#--------------------------------------
def make_circle(D,N,x_ctr,y_ctr):
#--------------------------------------

# D: Diameter of circle inserted in image in pixels.
# N: Dimension of image in pixels.
# (x_ctr,y_ctr): Center of circle with (0,0) being at pixels ((N-1)/2.,(N-1)/2.)
# Value: Value pixels inside circles are to be set to.

    a = 10  # Factor to subsample circle by.
    NN = a*N
    DD = a*D
    radius = DD/2.
    x0 = int(a*(N - 1.)/2. - a*x_ctr)
    y0 = int(a*(N - 1.)/2. - a*y_ctr)

#   Compute chord at each subsampled point x
    x = arange(NN).astype(float) - x0
    ysq = radius**2 - x**2
    y = sqrt(ysq * where(ysq > 0.,1.,0.))

#   Convert to true sampling.
    M = zeros((N,NN),float)
    for i in range(N):
        M[i,i*a:(i+1)*a] = 1./float(a)

#   Create output image.
    img = zeros((NN,N),float)
    image = zeros((N,N),float)
    row = zeros(NN,float)
    for i in range(NN):
        if y[i] > 0.:
            row[:] = 0.
            yy = int(y[i])
            frac = y[i] - float(yy)
            ymin = y0 - yy
            if ymin < 0:
                ymin = 0
            ymax = y0 + yy
            if ymax > NN-1:
                ymax = NN-1
            row[ymin:ymax] = 1.
            row[ymin-1] = frac/2.
            row[ymax] = frac/2.
            img[i,:] = dot(M,row)
    for i in range(N):
         image[:,i] = dot(M,img[:,i])
#    print "Dimension: %d, Diameter: %f, Sum: %f" % (N,D,sum(image.flat))

    return(image)

#************************
def dezoom_2n(image,zoom):
#************************

    """ Zooms out by a factor that must be equal to 2^-n where n is a positive
        integer.  
        image: A square input image with dimension 2^m
        zoom_factor: The dezoom factor. Allowable values: 2,4,8,... """

    shp = shape(image)
    zdim = 1
    tdim = 1
    if len(shp) == 2:
        ydim,xdim = shp
    elif len(shp) == 3:
        zdim,ydim,xdim = shp
    elif len(shp) == 4:
        tdim,zdim,ydim,xdim = shp
    tzdim = tdim*zdim
    
    if xdim != ydim:
        print "math_bic: Error in dezoom_2n.  Image must be square."
        return(-1)

    image = reshape(image,(tdim*zdim,ydim,xdim))
    idxs = zeros([zoom,xdim/zoom],int)
    for i in range(zoom):
        idxs[i,:] = zoom*arange(xdim/zoom) + i

    tcode = image.dtype.char
    img_out = zeros([tzdim,ydim/zoom,xdim/zoom],tcode)
    for tz in range(tzdim):
#       Sum over rows.
        tmp = zeros([ydim,xdim/zoom],tcode)
        for y in range(ydim):
            for i in range(zoom):
                tmp[y,:] = tmp[y,:] + take(image[tz,y,:],idxs[i,:])
#       Sum over columns.
        for x in range(xdim/zoom):
            for i in range(zoom):
                img_out[tz,:,x] = img_out[tz,:,x] + take(tmp[:,x],idxs[i,:])


    if len(shp) == 4:
        shp = [tdim,zdim,ydim/zoom,xdim/zoom]
    elif len(shp) == 3:
        shp = [zdim,ydim/zoom,xdim/zoom]
    else:
        shp = [ydim/zoom,xdim/zoom]
    img_out = reshape(img_out,shp)
    return(img_out/zoom**2)

#*******************************************
def dilate(image,dx=1,dy=1,dz=1):
#*******************************************

#   dx,dy, and dz define the major axis of the ellipsoid used in the dilation.
#   These values should be set to 2*n+1 where n is the size of the dilation 
#   in pixels, i.e.,
#   if you want to dilate an image by 1 pixel in x,y and z, set dx=dy=dz=3.
#   The mask image must have been computed.
#   vox_size: A tuple containing the voxel dimensions, e.g., (xsize,ysize,zsize)


    structure = ones([dz,dx,dy],float)
    return binary_dilation(image,structure,1).astype(float)
#        from vtk import vtkImageContinuousDilate3D,vtkImageContinuousErode3D
#        from vtk.util.vtkImageExportToArray import vtkImageExportToArray
#        from vtk.util.vtkImageImportFromArray import vtkImageImportFromArray
#
#        vox_size = [1.,1.,1.]
#        mx = image.flat[argmax(image.flat)]
#        mn = image.flat[argmin(image.flat)]
#        if mn < 0. or mx > 1.:
#            print "math_bic: Image must be a mask with values of 0 or 1."
#            return(-1)
#        vimg = vtkImageImportFromArray()
#        vimg.SetDataOrigin((0.,0.,0.))
#        vimg.SetDataSpacing(vox_size)
#        vimg.SetArray(image)
#
##       Add the dilation operator to the pipeline.
#        dilation = vtkImageContinuousDilate3D()
#        dilation.SetKernelSize(dx,dy,dz)
#        dilation.SetInput(vimg.GetOutput())
#
##       Cap the pipeline with a conversion back to Numarray format.
#        vout = vtkImageExportToArray()
#        vout.SetInput(dilation.GetOutput())
#
##       Execute the pipeline and return.
#        return vout.GetArray()


#*************************
def erode(image,ex,ey,ez):
#*************************
#   dx,dy, and dz define the major axis of the ellipsoid used in the erosion.  These
#   values should be set to 2*n+1 where n is the size of the erosion in pixels, i.e.,
    structure = ones([ez,ex,ey],float)
    return binary_erosion(image,structure,1).astype(float)

#********************
def hex_to_int(word):
#********************

# Convert strings of the form 0x1234 or 0x12345678 to integer.

    value = 0
    test = '0123456789abcdef'
    x = 1
    for i in range(len(word)):
        value = value + x*test.find(word[-i-1])
        x = 16*x
    return(value)


def print_matrix(A,title="",write=True, fmt='%7.4f', f=sys.stdout, tab_del=False):
    """
    Print matrix A with a pretty format.
    """

    if len(title) > 0:
        first_str = "%s |" % title
        bar = "|"
    else:
        first_str = " |"
        bar = "|"
    pad = (len(first_str) - len(bar)-1)*" "
    if A.shape == (4,4) or A.shape == (3,3): # Might be a rotation matrix. Set output format.
        if allclose(abs(sum(A[:3,:3],0)),1.):
#           Looks like a rotation matrix with cardinal angles., 
            low_precision = True
            fmt_str = '%3.0f'
        else:
            low_precision = False
            fmt_str = fmt
    else:
        low_precision = False
        fmt_str = fmt
    if fmt_str.endswith('d'):
        amax = A.max()
        amin = A.min()
        if amax > 0:
            lmax = log10(amax)
        elif amax < 0. and amin < amax:
            lmax = log10(-amin)
        else:
            lmax = 1.
        fmtlen = int(lmax) + 1
    else:
        sfmt = fmt_str.split('.')
        fmtlen = int(sfmt[0][1:]) + int(sfmt[1][:-1])  + 5
    outstr = ""
    if A.ndim == 2:
        ydim, xdim = A.shape
        for y in range(ydim):
            if y > 0:
                outstr = "%s%s %s" % (outstr,pad,bar)
            else:
                outstr = first_str
            if low_precision:
                str = fmt_str % A[y,0]
                str = (fmtlen - len(str))*" " + str
            else:
                str = fmt_str % A[y,0]
                str = (fmtlen-len(str))*" " + str
            outstr += str
            for x in range(xdim-2):
                if low_precision:
                    str = fmt_str % A[y,x+1]
                    str = (fmtlen -len(str))*" " + str
                else:
                    str = fmt_str % A[y,x+1]
                    str = (fmtlen -len(str))*" " + str
                outstr += str
            else:
                str = ""
            str = fmt_str % A[y,xdim-1]
            str = (fmtlen-len(str))*" " + str
            outstr += "%s %s" % (str,bar)
            outstr = outstr + "\n"
    elif A.ndim == 1:
        xdim = A.shape[0]
        outstr = '%s: ' % title
        for x in range(xdim):
            outstr = outstr + "  " + fmt_str % A[x]
        if write:
            outstr = outstr + "\n"
    else:
        outstr = array2string(A)

    if tab_del:
        for i in xrange(10):
            tgt = (10-i)*' '
            outstr = outstr.replace(tgt, '\t')
    if write:
        f.write(outstr)
    return outstr

#************************************
def reslice(imgin,hdr_in,hdr_parent):
#************************************
    """
    
    position.

    Purpose: Reslice the image given by image and hdr_in to the coordinate 
             system defined in hdr_parent.
    hdr_in is the header for image.
    hdr_parent is the header of an image in the desired orientation and 

    Assumptions: Rotation matrices define rotations to and from cardinal axes.
    """

# Compute transformation of fieldmap coordinates to image coordinates.
    R_pnt = hdr_parent['R']
    R_in = hdr_in['R']
    R_tot = dot(invert_rot44(R_pnt),R_in)

# Compute new image dimensions.
    xd = zeros(3,float)
    xdim_in = hdr_in['xdim']
    ydim_in = hdr_in['ydim']
    zdim_in = hdr_in['zdim']
    xdout = dot(abs(R_tot[:3,:3]),array([xdim_in,ydim_in,zdim_in])).astype(int)
    xdim_out = xdout[0]
    ydim_out = xdout[1]
    zdim_out = xdout[2]

    # Compute offsets
    dxyz = dot(R_tot[:3,:3],array([1,xdim_in,xdim_in*ydim_in])).astype(int)

    # Compute offsets for transformation.
    cvt = array([(xdim_in-1)/2.,(xdim_in*(ydim_in-1))/2.,(xdim_in*ydim_in*(zdim_in-1))/2.])
    xyzoff = (dot(abs(R_tot[:3,:3]),cvt) -  dot(R_tot[:3,:3],cvt)).astype(int)
    dtype = imgin.dtype
    imgin = imgin.flat
    imgout = zeros([zdim_out,ydim_out,xdim_out],dtype)
    zoff = xyzoff[2]
    # Transform fieldmap to image coordinates.
    for z in range(zdim_out):
        yoff = xyzoff[1]
        for y in range(ydim_out):
            idc = zoff + yoff + dxyz[0]*arange(xdim_out)
            x = take(imgin,idc)
            imgout[z,y,:] = take(imgin,idc)
            yoff = yoff + dxyz[1] 
        zoff = zoff + dxyz[2]

    # Create output header.
    hdr_out = hdr_in.copy()
    hdr_out['xdim'] = xdim_out
    hdr_out['ydim'] = ydim_out
    hdr_out['zdim'] = zdim_out

#   Compute new voxel sizes.
    tmp = dot(abs(R_tot[:3,:3]),array([hdr_in['xsize'],hdr_in['ysize'],hdr_in['zsize']]))
    hdr_out['xsize'] = tmp[0]
    hdr_out['ysize'] = tmp[1]
    hdr_out['zsize'] = tmp[2]

#   Compute new transformation matrix.
    Rout = zeros([4,4],float)
    Rout[:3,:3] = R_pnt[:3,:3]
    sign_change = .5*(identity(3) - dot(transpose(R_tot[:3,:3]),abs(R_tot[:3,:3])))   
    sign_dir =    dot(transpose(R_in[:3,:3]),abs(R_in[:3,:3]))
    x = dot(dot(sign_dir,sign_change),array([hdr_in['xsize']*(xdim_in-1.),hdr_in['ysize']*(ydim_in-1.),hdr_in['zsize']*(zdim_in-1.)]).astype(float))
    offset = dot(abs(R_in[:3,:3]),x)
    Rout[:3,3] = R_in[:3,3] + offset
    hdr_out['R'] = Rout
    hdr_out['x0'] = Rout[0,3]
    hdr_out['y0'] = Rout[1,3]
    hdr_out['z0'] = Rout[2,3]
###    print_matrix(Rout,"Rout")

    return(imgout,hdr_out)

#*******************************
def resample(image,hdr,hdr_out):
#*******************************

    """
    Function: resample_rot44

    Purpose: Resample image to a different orientation and/or grid size.

    Usage: resample_rot44(image,hdr_in,hdr_out)

    where


    describe the dimensions and pixel sizes of the input and output images.

    """

    R_in = hdr['R']
    R_out = hdr_out['R']
###    print_matrix(R_in,"resample:: R_in: ")
###    print_matrix(R_out,"resample:: R_out: ")
    if not allclose(R_in[:3,:3],R_out[:3,:3]):
#       Rotation matrices are different. Reslice the input image.
        image_in,hdr_in = reslice(image,hdr,hdr_out)
        R_in = hdr_in['R']
    else:
        image_in = image
        hdr_in = hdr

#   First retrieve parameters that describe the images.
    xdim_in = hdr_in['xdim']
    ydim_in = hdr_in['ydim']
    zdim_in = hdr_in['zdim']
    xsize_in = hdr_in['xsize']
    ysize_in = hdr_in['ysize']
    zsize_in = hdr_in['zsize']

    xdim_out = hdr_out['xdim']
    ydim_out = hdr_out['ydim']
    zdim_out = hdr_out['zdim']
    xsize_out = hdr_out['xsize']
    ysize_out = hdr_out['ysize']
    zsize_out = hdr_out['zsize']

# Field map has been resliced. Interpolate it. 
#    print_matrix(R_in,"R_in (after reslice): ")
#    print_matrix(R_out,"R_out: ")
#    print_matrix(invert_rot44(R_in),"R_in_inv: ")
    R_tot = dot(invert_rot44(R_in),R_out)
    xyzoff = R_tot[:3,3]
###    print_matrix(R_tot,"resample:: R_tot: ")
    
# Setup column interpolation.
    cols = (xyzoff[0] + arange(xdim_out)*xsize_out)/xsize_in
    mask1 = where(greater(cols,xdim_in-1),0.,1.)
    mask1 = mask1*where(less(cols,0),0.,1.)
    cols = cols*mask1
    icols = cols.astype(int)
    icols[-1] = icols[-2]
    dx = cols - icols.astype(float)
    
# Setup row interpolation.
    jrows = arange(ydim_in)
    rows = (xyzoff[1]  + arange(ydim_out)*ysize_out)/ysize_in
# Mask out illegal values
    mask1 = where(greater(rows,ydim_in-2),0.,1.)*where(less(rows,0),0.,1.)
    rows = rows*mask1
    irows = rows.astype(int)
    irows[-1] = irows[-2]
    dy = rows - irows.astype(float)
    
#Setup slice interpolation.
    slices = (xyzoff[2] + arange(zdim_out)*zsize_out)/zsize_in
    mask1 = where(greater(slices,zdim_in-1),0.,1.)*where(less(slices,0),0.,1.)
    slices = slices*mask1
    islcs = slices.astype(int)
    dz = slices - islcs.astype(float)
#    print 443,irows
#    print 444,jrows
#    print 445,icols
    
# Resample the input image to the output coordinates.
    image_out = zeros([zdim_out,ydim_out,xdim_out],image_in.dtype)
    for z in range(zdim_out):
        zp = islcs[z]
        if z < zdim_out-1:
            s1 = image_in[zp,:,:]
            s2 = image_in[zp+1,:,:]
            slc = (1. - dz[z])*s1 + dz[z]*s2
        else:
            slc = image_in[zp,:,:]
#       Usually zero. Ensures unsampled pixels are zero in new image.
        slc[0,:] = 0. 
        for x in range(xdim_out-1):
            c1 = take(slc[:,icols[x]],jrows)
            c2 = take(slc[:,icols[x+1]],jrows)
            column = (1. - dx[x])*c1 + dx[x]*c2
            r1 = take(column,irows)
            r2 = take(column,irows+1)
            image_out[z,:,x] = (1. - dy)*r1 + dy*r2
    return(image_out)


#*******************
def invert_rot44(R):
#*******************

    """
    Function: invert_rot44(R)

    Purpose: Invert a 4x4 transformation matrix.

    Usage: R_inverse = invert_rot44(R)

    where R is a 4x4 transformation matrix.

    Details: The rotation matrix is defined as follows:
        - The upper left 3x3 submatrix is an orthonormal rotation matrix.
        - The upper right 3x1 vector is a displacement in the target space.
        - Element 3x3 is equal to 1.
        - All other elements are equal to zero.

    Standard coordinate system used througout math_bic and file_io:
        - The rotation matrix defines a rotation into an RAI coordinate system, i.e.
          the voxel at x[0,0,0] where x is an image is the right, anterior, inferior
          edge of the image.  
        - Each value in the array represents the value at the center of a voxel.
        - The center is defined to be between the two central array elements. (If
          pixels are thought of as rectangular areas of the image, the voxel values sample          centers of these areas and the center of the image lies on the boundary between
          two pixels.
    """

    Rinv = zeros([4,4],float)
    Rinv[:3,:3] = R[:3,:3].transpose()
    Rinv[:3,3] = -dot(R[:3,:3].transpose(),R[:3,3])
    Rinv[3,3] = 1.
    return(Rinv)

#*************************************************************
def fit_legendre(image,axis,order,skip,setup_data=(None,None)):
#*************************************************************

    """
    Function: fit_legendre(image,order,setup_data=None)

    Purpose: Use ordinary least squares to fit the first 'order' members of
             a series of Legendre polynomials to the second dimension of the
             input image.

    Usage: fit_legendre data,5,(ATAinv,A) where
        data is an Nxdim array. Fit is made over dim points.
        5 is the number of Legendre polynomials to fit.
        (ATAinv,A) is a tuple containing matrices that define the inversion.
        If the third argument is set to "None", these matrices will be computed.

    By: John Ollinger, 2/21/07

    """

    MINDIM = 10 # Minimum number of points to fit
    MEDIAN_WDW = 5

    image.shape
    tdim = shp[axis]
    ndim = len(shp)
    nfit = 1
    dims = []
    dim_axis = shp[axis]
    for ax in range(len(shp)):
        nfit = nfit*shp[ax]
        if ax != axis:
            dims.append(shp[ax])
    if setup_data[0] == None:
#       Compute design matrix.
        A = zeros([tdim+1,order],float)
        Aestimators = []
        As = []
        for dim1 in range(MINDIM,tdim+1,1):
            A = zeros([dim1,order],float)
            for y in range(dim1):
                x = float(y)/float(tdim-1) - .5;
                A[y,0] = 1.
                if order > 1:
                    A[y,1] = x
                if order > 2:
                    A[y,2] = (3.*x**2 - 1.)/2.
                if order > 3:
                    A[y,3] = (5.*x**3 - 3.*x)/2.
                if order > 4:
                    A[y,4] = (35*x**4 - 30*x**2 + 3.)/8.
            AT = transpose(A[:,:])
            ATA = dot(AT,A[:dim1,:])
            ATAinv = inv(ATA)
            ATAinvAT = dot(ATAinv,AT)
            Aestimators.append(ATAinvAT)
            As.append(A)
    else:
        Aestimators,As = setup_data # Get previously computed matrices

#   Compute estimates.
    beta_out = zeros([dims[0],dims[1],order],float)
    fit_out = zeros([shp[0],shp[1],shp[2]],float)
    skip = 0
    for d1 in range(dims[0]):
        for d2 in range(dims[1]):
            if axis == 0:
                data = image[:,d1,d2]
            elif axis == 1:
                data = image[d1,:,d2]
            else:
                data = image[d1,d2,:]
            nz = nonzero(data)
            if nz < 5:
                continue
            idx = sort(nz) # Only fit to nonzero data.
            if len(idx) < 5: # Skip lines that are almost all zeros.
                continue
            ibeg = idx[0] + skip # Skip points on either end to avoid noisy edges.
            iend = idx[-1] - skip
#           Strip of isolated zeros at beginning and end.
            for i in range(ibeg,iend-1):
                if abs(data[i]*data[i+1]*data[i+2]) > 0.:
                    ibeg = i
                    break
            for i in range(iend,ibeg+2,-1):
                if abs(data[i]*data[i-1]*data[i-2]) > 0.:
                    iend = i
                    break
            if iend - ibeg >= MINDIM:
                N = iend - ibeg + 1
                y = data[ibeg:iend+1] # Get the nonzero data.
#               Use a median filter to get rid of interior zero voxels.
                idc_tmp = nonzero(where(abs(y[MEDIAN_WDW/2:-MEDIAN_WDW/2]) > 0.,0.,1.)) + MEDIAN_WDW/2
                for i in idc_tmp: # Replace zeros with the average of neighbors.
                    nbrhood = argsort(y[i-MEDIAN_WDW/2:i+MEDIAN_WDW/2+1])
                    y[i] = y[i+nbrhood[MEDIAN_WDW/2]-MEDIAN_WDW/2]
#               First fit "order" Legendre polynomials.
                ATAinvAT = Aestimators[N-MINDIM]
                beta = dot(ATAinvAT,y)
                fit = dot(As[N-MINDIM],beta)
                beta_out[d1,d2,:] = beta
                if axis == 0:
                    fit_out[ibeg:ibeg+N,d1,d2] = fit
                elif axis == 1:
                    fit_out[d1,ibeg:ibeg+N,d2] = fit
                else:
                    fit_out[d1,d2,ibeg:ibeg+N] = fit

    return(beta_out,fit_out,(Aestimators,As))

#**********************************
def whisto(data,number_bins,lg=0):
#**********************************

    """
    Function: whisto

    Wrap scipy's histo2 function.  Compute log or linear bin widths.

    Usage: whisto(data,number_bins,log=0)

    """

    if len(data) < 5:
        return -1 
    mx = max(data)
    mn = min(data)
    if mx-mn <= 0:
        return(None,None)
    if lg:
        a = log(mx-mn)/float(number_bins-1)
        bins = mn + exp(a*arange(number_bins)) # Logarithmic scale for histogram.
    else:
        bins = mn + (mx - mn)*arange(number_bins)/float(number_bins-1)
    histo = (histogram2(data.flat,bins)).astype(float)
    histo = histo/sum(histo)

    return(histo,bins)

#*******************************************
def reslice_3d(src_image, src_hdr, tgt_hdr):
#*******************************************


    """
    Function: reslice_3d
    Purpose: Call C program to reslice to an arbitrary plane.  
    Usage: reslice_3d(image, hdr, target, target_hdr)
        src_image: input image as a 3D ndarray.
        src_hdr: hdr attribute from Wimage instance
        tgt_hdr: hdr attribute from Wimage instance in desired coordinates.
    """

    Rtmp = diag(src_hdr['sizes'][:3])
    Rsrc = dot(src_hdr['R'][:3,:3],Rtmp)
    
    Rtmp = diag(tgt_hdr['sizes'][:3])
    Rtgt = dot(tgt_hdr['R'][:3,:3],Rtmp)

#   Compute source to taarget xform.
    Rtot = zeros([4,4],float)
    Rtot[:3,:3] = dot(linalg.inv(Rsrc),Rtgt)
    Rtot[:3, 3] = dot(linalg.inv(Rsrc),(-src_hdr['R'][:3,3] + \
                                                    tgt_hdr['R'][:3,3]))
    Rtot[3,3] = 1. 


#   Reslice source to target coordinates.
    dims_out = (tgt_hdr['zdim'],tgt_hdr['ydim'],tgt_hdr['xdim'])
    imgout = pyreslice_3d(src_image.astype(float), Rtot, dims_out)

    return imgout

def extent_threshold(image, hght_thresh, extent_lower_thresh, \
                                                extent_upper_thresh=None):
    """
    Purpose: Apply hght_thresh to an image to isolate above-threshold 
             regions, and then apply a spatial extent threshold to those
             regions.

    Usage: 
        mask = extent_thresh(image, hght_thresh, extent_lower_thresh, extent_upper_thresh=None)
    where
        image: image to be thresholded.
        hgth_thresh: Height threshold.
        extent_lower_thresh: Minimum region size.
        extent_upper_thresh: Maximum region size (Not used if set to None)
        mask: Integer array of same size as image.  Each region is assigned an
              integer value starting at 1, i.e., voxels in the first region 
              found will have a value of one, voxels in the second will 
              have the value two and so forth.

    Method: After the height threshold is applied, voxels above threshold are
            used as seeds to find neighbors with face-connectivity.

    """
    if extent_upper_thresh:
        upper_thresh = extent_upper_thresh
    else:
        upper_thresh = int(image.size)
    image =  pyextent_threshold(image, hght_thresh, \
                            int(extent_lower_thresh), int(upper_thresh))

    n_reg = int(image[0,0,0])
    size_reg = []
    for i in xrange(n_reg):
        size_reg.append(int(image.ravel()[i+1]))
    return (n_reg, size_reg, image)

class ThreshConvert():
    """
    Convert between p, z, t, and f values.  Assumes that z and t values
    are two sided, so p<.001 is interpreted as z < -3.29 and z > 3.29
    """
    def __init__(self, stat, stat_type, df1=None, df2=None, one_sided=False):

        self.input_type = stat_type.lower()
        self.df1 = double(df1)
        self.df2 = double(df2)
        if not isinstance(stat, ndarray):
            stat = array(stat)
        if one_sided:
            self.one_sided = 2.
        else:
            self.one_sided = 1.
        if self.input_type == 'f':
            self.f = stat
            self.t = None
            self.z = None
            self.p = self.FtoP()
        elif self.input_type == 't':
            self.f = None
            self.z = None
            self.t = stat
            self.p = self.TtoP()
        elif self.input_type == 'z':
            self.f = None
            self.t = None
            self.z = stat
            self.p = self.ZtoP()
        elif self.input_type == 'p':
            self.p = stat
            self.f = None
            self.t = None
            self.z = None
        else:
            raise OSError('ThreshConvert: Unrecognized type. Must be t, f or z\n')

    def PtoStat(self, stype, df1=None, df2=None):
        ltype = stype.lower()
        if ltype == 'z':
            return self.Z()
        elif ltype == 't':
            return self.T(df1)
        elif ltype == 'f':
            return self.F(df1, df2)
        else:
            return None

    def ZtoP(self):
        if self.z is not None:
            self.p = self.one_sided*(1. - ndtr(self.z))
        else:
            self.p = None
        return self.p

    def Z(self):
        if self.p is not None:
            if isinstance(self.p, ndarray):
                x = 1. - self.p.astype(double)
            else:
                x = array(1.-double(self.p))
            self.z = 1.41421356237*erfinv(x)
        else:
            self.z = None
        return self.z

    def TtoP(self):
        if self.t is not None:
            self.p = self.one_sided*(1. - stdtr(self.df1, self.t))
        else:
            self.p = None
        return self.p

    def T(self, df1):
        if self.p is not None:
            self.t = abs(stdtrit(df1, self.p/self.one_sided))
        else:
            self.t =  None
        return self.t

    def FtoP(self):
        if self.f is not None:
            self.p = 1. - fdtr(self.df1, self.df2, self.f.astype(double))
        else:
            self.p = None
        return self.p

    def F(self, df1, df2):
        if self.p is not None:
            self.f = fdtri(df1, df2, 1.-self.p)
        else:
            self.f = None
        return self.f

#def lm_der(func, jacf, p0, extra, data, max_iter, delta0=1.e-3, \
#                        eps_jac=1.e-17, eps_cauchy=1.e-17, eps_rsse=1.e-17):
#    """
#    func: func(p, data, extra_data),  returns residuals evaluated at p
#    jacf jacfc(p, data, extra_data),  returns Jacobian evaluated at p
#    p0: Initial estimate.
#    extra: Values for independent variable.
#    data: Input data.
#    max_iter: Stop if number of iterations exceeds this.
#    delta0: Scale factor for initial step-size.
#    eps_jac: Stopping threshold for ||J^T e||_inf, 
#    eps_cauchy: Stopping threshold for||Dp||_2 
#    eps_rsse: Stopping threshold for||e||_2. 
#    info:
#      rsse0: ||e||_2 at initial p.
#      rsse: [ ||e||_2
#      eps_jac: ||J^T e||_inf
#      eps_cauchy: ||Dp||_2, 
#      eps_2: \mu/max[J^T J]_ii
#      niter:  # iterations,
#      term_code: 1 - stopped by small gradient J^T e
#                 2 - stopped by small Dp
#                 3 - stopped by itmax
#                 4 - singular matrix. Restart from current p with increased \mu
#                 5 - no further error reduction is possible. Restart with increased mu
#      *          6 - stopped by small ||e||_2
#      *          7 - stopped by invalid (i.e. NaN or Inf) "func" values; a user error
#      * nfunc_evals: Number of function evaluations
#      * njacf_evals: Number of Jacobian evaluations
#      * nsys_solveld: linear systems solved, i.e. # attempts for reducing error
#    """
#    term_codes =  { \
#      1:'Stopped by small gradient J^T e', \
#      2:'Stopped by small Dp', \
#      3:'Stopped by itmax', \
#      4:'Singular matrix. Restart from current p with increased \mu', \
#      5:'No further error reduction is possible. Restart with increased mu', \
#      6:'Stopped by small ||e||_2', \
#      7:'Stopped by invalid (i.e. NaN or Inf) "func" values; a user error'}
#
#    opts = empty(4, float)
#    if delta0 is not None:
#        opts[0] = delta0
#    if eps_jac is not None:
#        opts[1] = eps_jac
#    if eps_cauchy is not None:
#        opts[2] = eps_cauchy
#    if eps_rsse is not None:
#        opts[3] = eps_rsse
#    niter, phat, info = levmar_der(func, jacf, p0, extra, data, max_iter, opts)
#
#    return niter, phat, info, term_codes[info['term_code']]

if __name__ == '__main__':
    sys.stdout.write('%s\n' % ID)
