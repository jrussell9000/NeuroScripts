import string, os, sys, subprocess, shutil, time
from glob import glob

import numpy as np
import nibabel as nib

def topup_fsl(input_dwi, input_bvals, input_index, input_acqparams, output_topup_base, config_file='', field_output=''):

    #First, find the indices of the B0 images
    dwi_img = nib.load(input_dwi)
    aff = dwi_img.get_affine()
    sform = dwi_img.get_sform()
    qform = dwi_img.get_qform()
    dwi_data = dwi_img.get_data()
    
    bvals = np.loadtxt(input_bvals)
    index = np.loadtxt(input_index)
    acqparams = np.loadtxt(input_acqparams)
    ii = np.where(bvals == 0)

    b0_data = dwi_data[:,:,:,np.asarray(ii).flatten()]
    b0_indices = index[ii].astype(int)
    b0_acqparams=acqparams[b0_indices-1]
    
    output_dir = os.path.dirname(output_topup_base)
    tmp_acqparams = output_dir + '/tmp.acqparams.txt'
    tmp_b0 = output_dir + '/tmp.B0.nii.gz'
    
    b0_imgs = nib.Nifti1Image(b0_data, aff, dwi_img.header)
    nib.save(b0_imgs, tmp_b0)
    np.savetxt(tmp_acqparams, b0_acqparams, fmt='%.8f')
    
    topup_command='topup --imain='+tmp_b0+' --datain='+tmp_acqparams+' --out='+output_topup_base
    
    if config_file != '':
        topup_command += ' --config='+config_file
    if field_output != '':
        topup_command += ' --fout='+field_output

    os.system(topup_command)
    os.system('rm -rf ' + output_dir + '/tmp*')



def fugue_fsl(input_dwi, input_bvals, input_fm, input_fm_ref, output_dwi, field_map_dir, unwarpdir, dwellTime, fm_ref_mask_img=''):

    if not os.path.exists(field_map_dir):
        os.mkdir(field_map_dir)
    
    #Skull-strip the reference
    if input_fm_ref.endswith('.nii'):
        input_fm_ref_base = input_fm_ref[0:len(input_fm_ref)-4]
    else:
        input_fm_ref_base = input_fm_ref[0:len(input_fm_ref)-7]

    fm_ref_mask = input_fm_ref_base + '.mask.nii.gz'
    if fm_ref_mask_img == '':
        os.system('bet ' + input_fm_ref + ' ' + fm_ref_mask)
    else:
        os.system('fslmaths ' + input_fm_ref + ' -mas ' + fm_ref_mask_img + ' ' + fm_ref_mask)

    if input_fm.endswith('.nii'):
        input_fm_base = input_fm[0:len(input_fm)-4]
    else:
        input_fm_base = input_fm[0:len(input_fm)-7]

    fm_rads = input_fm_base + '.rads.nii.gz'

    #Now scale the field map and mask
    os.system('fslmaths ' + input_fm + ' -mul 6.28 -mas ' + fm_ref_mask + ' ' + fm_rads)
    os.system('fugue --loadfmap='+fm_rads+' --smooth3=1.0 --despike --savefmap='+fm_rads)

    input_fm_ref_warp = input_fm_ref_base + '.warp.nii.gz'
    #Warp the reference image
    os.system('fugue -i ' + fm_ref_mask + ' --unwarpdir='+unwarpdir + ' --dwell='+dwellTime + ' --loadfmap='+fm_rads + ' -s 0.5 -w ' + input_fm_ref_warp)

    dwi_ref = field_map_dir + '/dwi_ref.nii.gz'
    bvals = np.loadtxt(input_bvals)
    ii = np.where(bvals != 0)

    dwi_img = nib.load(input_dwi)
    aff = dwi_img.get_affine()
    sform = dwi_img.get_sform()
    qform = dwi_img.get_qform()
    dwi_data = dwi_img.get_data()

    dwi = dwi_data[:,:,:,np.asarray(ii).flatten()]
    dwi_mean = np.mean(dwi_data, axis=3)
    dwi_mean_img = nib.Nifti1Image(dwi_mean, aff, dwi_img.header)
    nib.save(dwi_mean_img, dwi_ref)

    #Align warped reference to the dwi data
    fm_ref_warp_align = input_fm_ref_base + '.warp.aligned.nii.gz'
    fm_ref_mat = input_fm_ref_base + '_2_dwi.mat'
    os.system('flirt -in ' + input_fm_ref_warp + ' -ref ' + dwi_ref + ' -out ' + fm_ref_warp_align + ' -omat ' + fm_ref_mat + ' -dof 6')

    #Apply this to the field map
    fm_rads_warp = input_fm_base + '.rads.warp.nii.gz'
    os.system('flirt -in ' + fm_rads + ' -ref ' + dwi_ref + ' -applyxfm -init ' + fm_ref_mat + ' -out ' + fm_rads_warp)

    #Now, undistort the image
    os.system('fugue -i ' + input_dwi + ' --icorr --unwarpdir='+unwarpdir + ' --dwell='+dwellTime + ' --loadfmap='+fm_rads_warp+' -u ' + output_dwi)


def prep_external_fieldmap(input_dwi, input_fm, input_fm_ref, dwellTime, unwarpdir, field_map_dir):
    
    if not os.path.exists(field_map_dir):
        os.mkdir(field_map_dir)
    
    #Skull-strip the reference
    if input_fm_ref.endswith('.nii'):
        input_fm_ref_base = input_fm_ref[0:len(input_fm_ref)-4]
    else:
        input_fm_ref_base = input_fm_ref[0:len(input_fm_ref)-7]
    
    fm_ref_mask = input_fm_ref_base + '.mask.nii.gz'

    os.system('bet ' + input_fm_ref + ' ' + fm_ref_mask)

    if input_fm.endswith('.nii'):
        input_fm_base = input_fm[0:len(input_fm)-4]
    else:
        input_fm_base = input_fm[0:len(input_fm)-7]

    fm_rads = input_fm_base + '.rads.nii.gz'
    
    #Now scale the field map and mask
    os.system('fslmaths ' + input_fm + ' -mul 6.28 -mas ' + fm_ref_mask + ' ' + fm_rads)
    
    input_fm_ref_warp = input_fm_ref_base + '.warp.nii.gz'
    #Warp the reference image
    os.system('fugue -i ' + fm_ref_mask + ' --unwarpdir='+unwarpdir + ' --dwell='+dwellTime + ' --loadfmap='+fm_rads + ' -w ' + input_fm_ref_warp)
    
    dwi_ref = field_map_dir + '/dwi_ref.nii.gz'
    os.system('fslroi ' + input_dwi + ' ' + dwi_ref + ' 0 1' )
    
    #Align warped reference to the dwi data
    fm_ref_warp_align = input_fm_ref_base + '.warp.aligned.nii.gz'
    fm_ref_mat = input_fm_ref_base + '_2_dwi.mat'
    os.system('flirt -in ' + input_fm_ref_warp + ' -ref ' + dwi_ref + ' -out ' + fm_ref_warp_align + ' -omat ' + fm_ref_mat)
    
    #Apply this to the field map
    fm_rads_warp = input_fm_base + '.rads.warp.nii.gz'
    os.system('flirt -in ' + fm_rads + ' -ref ' + dwi_ref + ' -applyxfm -init ' + fm_ref_mat + ' -out ' + fm_rads_warp)

    fm_hz_warp = input_fm_base + '.hz.warp.nii.gz'
    os.system('fslmaths ' + fm_rads_warp + ' -mul 0.1592 ' + fm_hz_warp)


