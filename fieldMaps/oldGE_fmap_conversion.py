#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 30 14:36:03 2020
Translation of Chris Rorden's nii_complex2magPhase.m code,
     https://github.com/rordenlab/spmScripts/blob/master/nii_complex2magPhase.m
Prior to executing this code, the following dcm2niix command was performed:
        dcm2niix -o $PWD $PWD
@author: dlevitas
https://github.com/dlevitas/miscellaneous/blob/main/Phillips_fmap_conversion.py
"""


import os
import nibabel as nib
import numpy as np

directory = '/fast_scratch/jdr/resting/fmapRaw/s14_fmap'
nifti_files = [x for x in os.listdir(directory) if '.nii' in x and 'test' not in x]
nifti_files.sort()

print(nifti_files)
quit()
imaginary1 = nifti_files[0]
real1 = nifti_files[1]
imaginary2 = nifti_files[2]
real2 = nifti_files[3]

real_img = nib.load('{}/{}'.format(directory, real1))
imaginary_img = nib.load('{}/{}'.format(directory, imaginary1))

real_data = nib.load('{}/{}'.format(directory, real1)).get_fdata()
imaginary_data = nib.load('{}/{}'.format(directory, imaginary1)).get_fdata()

mag_data = np.sqrt(real_data**2 + imaginary_data**2)
mag_hdr_pinfo = [1,0,0]

mag_data = mag_data - min(mag_data.flatten('F'))

scalef = 65535/max(mag_data.flatten('F'))

mag_data = mag_data * scalef
print('Magnitude image saved as UINT16, range {}..{}'.format(min(mag_data.flatten('F')), max(mag_data.flatten('F'))))


if not os.path.isfile('{}/e1_mag_test.nii.gz'.format(directory)):
    empty_mag_header = nib.Nifti2Header()
    final_mag_img = nib.Nifti2Image(mag_data, real_img.affine, empty_mag_header)
    nib.save(final_mag_img, '{}/e1_mag_test.nii.gz'.format(directory))
    
    
#create phase image
phase_data = np.arctan2(imaginary_data, real_data)  


if not os.path.isfile('{}/e1_phase_test.nii.gz'.format(directory)):
    empty_phase_header = nib.Nifti2Header()
    final_phase_img = nib.Nifti2Image(phase_data, imaginary_img.affine, empty_phase_header)
    nib.save(final_phase_img, '{}/e1_phase_test.nii.gz'.format(directory))
    
print('Phase image range (-pi..pi) {}..{}'.format(min(phase_data.flatten('F')), max(phase_data.flatten('F'))))

#
#
#











#phdr = rhdr;
#phdr.dt(1) = 16; %32-bit float
#phdr.pinfo = [1;0;0]; %slope=1, intercept=0 
#phdr.fname = fullfile(pth, [nm '_ph' ext]);  
#spm_write_vol(phdr,pimg);
#fprintf('Phase image range (-pi..pi) %g..%g\n', min(pimg(:)), max(pimg(:)) );



# #Make complex volumes
# os.system('fslcomplex -complex {} {} complex_e1'.format(real1, imaginary1))
# os.system('fslcomplex -complex {} {} complex_e2'.format(real2, imaginary2))

# #Get magnitude images
# os.system('fslcomplex -realabs complex_e1.nii.gz fieldmap_mag_e1')
# os.system('fslcomplex -realabs complex_e2.nii.gz fieldmap_mag_e2')

# #Get wrapped phase image(s) in radians
# os.system('fslcomplex -realphase complex_e1.nii.gz phase_e1_rad')
# os.system('fslcomplex -realphase complex_e2.nii.gz phase_e2_rad')

# #Unwrapping phases image(s)
# os.system('prelude -a fieldmap_mag_e1 -p phase_e1_rad -o phase_e1_unwrapped_rad')
# os.system('prelude -a fieldmap_mag_e2 -p phase_e2_rad -o phase_e2_unwrapped_rad')