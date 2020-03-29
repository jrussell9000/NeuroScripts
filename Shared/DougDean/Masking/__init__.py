import string, os, sys, subprocess, shutil, time

#Neuroimaging Modules
import numpy as np
import nibabel as nib
from dipy.segment.mask import median_otsu

def mask_dipy(input_dwi, output_mask, output_dwi=''):

    img = nib.load(input_dwi)
    data = img.get_data()
    masked_data, mask = median_otsu(data, 2,2)

    aff = img.get_affine()
    sform = img.get_sform()
    qform = img.get_qform()

    #Save these files
    masked_img = nib.Nifti1Image(masked_data.astype(np.float32), aff, img.header)
    mask_img = nib.Nifti1Image(mask.astype(np.float32), aff,  img.header)

    masked_img.set_sform(sform)
    masked_img.set_qform(qform)
    mask_img.set_sform(sform)
    mask_img.set_qform(qform)

    nib.save(mask_img, output_mask)

    if output_dwi != '':
        nib.save(masked_img, output_dwi)

def mask_skull_strip(input_dwi, output_mask, output_dwi=''):

    output_root, img = os.path.split(output_mask)

    tmpImg = output_root + '/tmp.nii.gz'
    tmpMask = output_root + '/tmp_mask.nii.gz'

    os.system('fslroi ' + input_dwi + ' ' + tmpImg + ' 0 1')
    os.system('3dSkullStrip -input ' + tmpImg + ' -prefix ' + tmpMask)

    os.system('fslmaths ' + tmpMask + ' -bin ' + output_mask)
    
    if output_dwi != '':
        os.system('fslmaths ' + input_dwi + ' -mas ' + output_mask + ' ' + output_dwi)

    os.system('rm -rf ' + tmpImg)
    os.system('rm -rf ' + tmpMask)

def mask_bet(input_dwi, output_mask, output_dwi='', f_threshold=''):
    
    output_root, img = os.path.split(output_mask)
    tmpImg = output_root + '/tmp.nii.gz'
    tmpMask = output_root + '/tmp_mask.nii.gz'
    
    os.system('fslroi ' + input_dwi + ' ' + tmpImg + ' 0 1')
    
    if f_threshold != '':
        os.system('bet ' + tmpImg + ' ' + tmpMask + ' -f ' + f_threshold)
    else:
        os.system('bet ' + tmpImg + ' ' + tmpMask)
    
    os.system('fslmaths ' + tmpMask + ' -bin ' + output_mask)
    
    if output_dwi != '':
        os.system('fslmaths ' + input_dwi + ' -mas ' + output_mask + ' ' + output_dwi)

    os.system('rm -rf ' + tmpImg)
    os.system('rm -rf ' + tmpMask)

def mask_mrtrix(input_dwi, input_bval, input_bvec, output_mask, output_dwi=''):

    output_dir = os.path.dirname(output_dwi)
    tmp_dwi = output_dir + '/tmp.dwi.mif'
    os.system('mrconvert -fslgrad '+ input_bvec + ' ' + input_bval + ' ' + input_dwi + ' ' + tmp_dwi)
    os.system('dwi2mask ' +  tmp_dwi + ' ' + output_mask + ' -quiet')
    
    if output_dwi != '':
        os.system('fslmaths ' + input_dwi + ' -mas ' + output_mask + ' ' + output_dwi)

    os.system('rm -rf ' + output_dir + '/tmp*')

