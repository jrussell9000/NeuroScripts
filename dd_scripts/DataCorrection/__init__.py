import string, os, sys, subprocess, shutil, time
import nibabel as nib
import numpy as np

from dipy.segment.mask import median_otsu
from dipy.denoise.nlmeans import nlmeans
from dipy.denoise.noise_estimate import estimate_sigma
from dipy.io import read_bvals_bvecs
from dipy.io.bvectxt import reorient_vectors

def denoise_mrtrix(input_dwi, output_dwi, output_noise=''):
    #This function uses MRTRix function dwidenoise to remove noise from images
    if(output_noise != ''):
        os.system('dwidenoise ' + input_dwi + ' ' + output_dwi + ' -noise ' + output_noise + ' -quiet -force')
    else:
        os.system('dwidenoise ' + input_dwi + ' ' + output_dwi + ' -quiet -force')

def mrdegibbs_mrtrix(input_dwi, output_dwi):
    #This function uses MRTRix to perform Gibbs ringing correction
    os.system('mrdegibbs ' + input_dwi + ' ' + output_dwi  + ' -quiet -force')

def denoise_dipy(input_dwi, input_bval, input_bvec, mask_image, output_dwi):
    #This function uses nlmeans as part of dipy to remove noise from images
    img = nib.load(input_dwi)
    data = img.get_data()
    mask = nib.load(mask_image).get_data()
    aff = img.get_affine()
    sform = img.get_sform()
    qform = img.get_qform()
    
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]
    
    sigma = estimate_sigma(data)
    sigma = np.mean(sigma[ii])
    
    den = nlmeans(data,sigma=sigma, mask=mask)
    
    den_img = nib.Nifti1Image(den.astype(np.float32), aff, img.header)
    den_img.set_sform(sform)
    den_img.set_qform(qform)
    nib.save(den_img, output_dwi)
