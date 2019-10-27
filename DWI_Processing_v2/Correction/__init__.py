import string, os, sys, subprocess, shutil, time
import nibabel as nib
import numpy as np

from dipy.segment.mask import median_otsu
from dipy.denoise.nlmeans import nlmeans
from dipy.denoise.noise_estimate import estimate_sigma
from dipy.io import read_bvals_bvecs
from dipy.io.bvectxt import reorient_vectors

def denoise(input_dwi, output_dwi, output_noise):
    subprocess.call(['dwidenoise', '-force', '-quiet', input_dwi, output_dwi])

def degibbs(input_dwi, output_dwi):
    subprocess.call(['mrdegibbs', '-force', '-quiet', input_dwi, output_dwi])

def denoise_dipy(input_dwi, input_bval, input_bvec, mask_image, output_dwi):
    #This function uses nlmeans as part of dipy to remove noise from images
    img = nib.load(input_dwi)
    data = img.get_data()
    mask = nib.load(mask_image).get_data()
    affine = img.get_affine()
    sform = img.get_sform()
    qform = img.get_qform()
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
    values = np.array(bvals)
    
    #Get the standard deviation of the noise in each volume as an array
    sigma = estimate_sigma(data)

    #Get the mean standard deviation of the noise in B0 volumes
    sigma = np.mean(sigma[[ii]])

    den = nlmeans(data, sigma=sigma, mask=mask)

    den_img = nib.Nifti1Image(den.astype(np.float32), aff, img.header)
    den_img.set_sform(sform)
    den_img.set_qform(qform)
    nib.save(den_img, output_dwi)

def runTopUp(input_dwi, input_bvals, input_index, input_acqparams, output_topup_base, config_file='', field_output=''):
    
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

def runEddy(input_dwi, input_bval, input_bvec, input_index, input_acqparam, output_dwi, output_bvec, topup_base='', external_b0='', repol=0, data_shelled=0, mb='', cuda='', mporder=0, slice_order='', mask_img=''):
    
    output_dir = os.path.dirname(output_dwi)
    tmp_mask = output_dir + '/tmp_mask.nii.gz'
    
    if mask_img == '':
        tmp_dwi = output_dir + '/tmp_img.nii.gz'
        os.system('fslroi ' + input_dwi + ' ' + tmp_dwi + ' 0 1')
        os.system('bet ' + tmp_dwi + ' ' + output_dir + '/tmp -m')
    else:
        os.system('cp ' + mask_img + ' ' + tmp_mask)

    eddy_output_basename = output_dwi[0:len(output_dwi)-7]
    if cuda != '':
        command = eddy_cuda + ' --imain=' + input_dwi + ' --mask=' + tmp_mask + ' --index=' + input_index + ' --acqp=' + input_acqparam + ' --bvecs=' + input_bvec + ' --bvals=' + input_bval + ' --out='  + eddy_output_basename
    else:
        command = eddy + ' --imain=' + input_dwi + ' --mask=' + tmp_mask + ' --index=' + input_index + ' --acqp=' + input_acqparam + ' --bvecs=' + input_bvec + ' --bvals=' + input_bval + ' --out='  + eddy_output_basename

    if topup_base != '':
        command += ' --topup='+topup_base
    if external_b0 != '':
        command += ' --field='+external_b0
    if repol != 0:
        command += ' --repol '
    if data_shelled != 0:
        command += ' --data_is_shelled '
    if mb != '':
        command += ' --mb ' + mb
    if mporder != 0 and slice_order != '':
        command += ' --niter=8 --fwhm=10,8,4,2,0,0,0,0 --ol_type=both --mporder='+str(mporder)+' --s2v_niter=5 --slspec='+slice_order + ' --s2v_lambda=1 --s2v_interp=trilinear'
  
    print command
    os.system(command)
    #Rotate b-vecs after doing the eddy correction
    os.system('mv ' + eddy_output_basename+'.eddy_rotated_bvecs ' + output_bvec)

    #Remove temporary mask
    os.system('rm -rf ' + tmp_mask)
    if mask_img == '':
        os.system('rm -rf ' + tmp_dwi)



