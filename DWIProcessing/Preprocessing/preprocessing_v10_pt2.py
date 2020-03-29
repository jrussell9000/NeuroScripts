#!/usr/bin/env python3
# coding: utf-8

import shutil
import subprocess
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel
import nibabel as nib
import numpy as np

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')


def dwicorr_2(ses_dir):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    orig_dir = ses_dir / 'dwi' / 'original'

    # Running eddy_quad and removing outlier volumes

    # --Defining quad input parameters
    eddy_dir = preproc_dir / 'eddy'
    preeddy_dir = preproc_dir / 'pre-eddy'
    eddy_dir = ses_dir / 'dwi' / 'preprocessed' / 'eddy'
    eddy_basename = str(eddy_dir / (subjroot + '_dwi_eddy'))
    eddy_index = eddy_dir / 'eddy_index.txt'
    eddy_acqp = eddy_dir / 'eddy_acqp.txt'
    eddy_mask = preeddy_dir / (subjroot + '_native_mnb0_brain_mask.nii.gz')
    bvec_eddy_woutliers = eddy_dir / (subjroot + '_dwi_eddy.eddy_rotated_bvecs')
    inputbval = orig_dir / (subjroot + '_dwi.bval')
    fmap_ph_brain_s4_reg_2_mnb0_brain = preeddy_dir / (subjroot + '_fmap_ph_brain_s4_reg_2_mnb0_brain.nii.gz')
    fieldmap2eddy = fmap_ph_brain_s4_reg_2_mnb0_brain.parent / fmap_ph_brain_s4_reg_2_mnb0_brain.stem.split('.')[0]
    slspec = '/Users/jdrussell3/slspec.txt'

    # --Removing the old quad directory if it exists
    quad_old = eddy_dir / 'quad'
    if quad_old.exists():
        shutil.rmtree(quad_old)

    # --Removing any pre-existing quad directories (FSL will kick back an error if the quad output directory already
    # exists
    quad_out = eddy_dir / (subjroot + '_dwi_eddy.qc')
    if quad_out.exists():
        shutil.rmtree(quad_out)

    # --Running eddy_quad and outputing to subjroot_dwi_eddy.qc
    subprocess.run(['eddy_quad',
                    str(eddy_basename),
                    '--eddyIdx='+str(eddy_index),
                    '--eddyParams='+str(eddy_acqp),
                    '--mask='+str(eddy_mask),
                    '--bvals='+str(inputbval),
                    '--bvecs='+str(bvec_eddy_woutliers),
                    '--field='+str(fieldmap2eddy),
                    '--slspec='+str(slspec),
                    '--verbose'])

    # --Removing outlier volumes
    dwi_eddy_niigz_woutliers = eddy_dir / (eddy_basename + '.nii.gz')
    dwi_eddy_niigz = eddy_dir / (subjroot + '_dwi_eddy_no_outliers.nii.gz')
    vols_no_outliers = eddy_dir / (subjroot + '_dwi_eddy.qc') / 'vols_no_outliers.txt'

    img = nib.load(dwi_eddy_niigz_woutliers)
    data = img.get_fdata()
    aff = img.affine
    sform = img.get_sform()
    qform = img.get_qform()
    nvols = np.size(data, 3)

    allvols = np.arange(0, nvols)
    goodvols = np.loadtxt(vols_no_outliers)
    vols_to_remove = np.setdiff1d(allvols, goodvols)

    data_to_keep = np.delete(data, vols_to_remove, 3)
    corr_img = nib.Nifti1Image(data_to_keep.astype(np.float32), aff, img.header)
    corr_img.set_sform(sform)
    corr_img.set_qform(qform)
    nib.save(corr_img, dwi_eddy_niigz)
    # --eddy quad creates no outlier bvecs and bvals files, so no need to correct those

    quadout_dir = eddy_dir / (subjroot + '_dwi_eddy.qc')
    bvec_eddy = quadout_dir / 'bvecs_no_outliers.txt'
    bval_eddy = quadout_dir / 'bvals_no_outliers.txt'

    ##############################################
    # ----Removing Gibbs Rings and Denoising---- #
    ##############################################

    post_eddy_dir = preproc_dir / 'post-eddy'
    if post_eddy_dir.exists():
        shutil.rmtree(post_eddy_dir)
    post_eddy_dir.mkdir(exist_ok=True)

    # 1. Converting eddy-corrected volumes to MRTrix3's .mif format

    dwi_eddy = post_eddy_dir / (subjroot + '_dwi_eddy.mif')

    subprocess.run(['mrconvert', '-info', '-force', '-fslgrad', bvec_eddy,
                    bval_eddy, dwi_eddy_niigz, dwi_eddy])

    # 1. Denoise #https://www.ncbi.nlm.nih.gov/pubmed/27523449
    dwi_eddy_den = post_eddy_dir / (subjroot + '_dwi_eddy_den.mif')
    subprocess.run(['dwidenoise', '-info', '-force', dwi_eddy,
                    dwi_eddy_den])

    # 2. Remove Gibbs rings #https://onlinelibrary.wiley.com/doi/full/10.1002/mrm.26054
    dwi_eddy_den_deg = post_eddy_dir / (subjroot + '_dwi_eddy_den_deg.mif')
    subprocess.run(['mrdegibbs', '-info', '-force', dwi_eddy_den,
                    dwi_eddy_den_deg])

    #################################################
    # ----Bias Field (B1) Distortion Correction---- #
    #################################################
    # https://www.ncbi.nlm.nih.gov/pubmed/20378467

    # -Within 'post-eddy', make directory to hold files for EPI distortion correction
    bias_corr_dir = post_eddy_dir / '2-Bias_Correction'
    bias_corr_dir.mkdir()

    # -Bias correction
    dwi_eddy_den_deg_unb = bias_corr_dir / (subjroot + '_dwi_eddy_den_deg_unb.mif')
    subprocess.run(['dwibiascorrect', '-info', '-force', 'ants', dwi_eddy_den_deg,
                    dwi_eddy_den_deg_unb, '-scratch', '/tmp'])

    ########################################
    # ----Upsampling and Mask Creation---- #
    ########################################

    # -Within 'post-eddy', make directory to hold files for EPI distortion correction
    upsamp_dir = post_eddy_dir / '3-Upsampling_and_Masking'
    upsamp_dir.mkdir()

    # 1. Regridding to 1.5mm isomorphic voxels #Suggested on 3tissue.github.io/doc/single-subject.html
    dwi_eddy_den_deg_unb_ups = upsamp_dir / (subjroot + '_dwi_eddy_den_deg_unb_ups.mif')
    subprocess.run(['mrgrid', '-info', '-force', dwi_eddy_den_deg_unb, 'regrid', dwi_eddy_den_deg_unb_ups,
                    '-voxel', '1.5'])

    # 2. Mask generation

    # a. Extract b0s
    dwi_eddy_den_deg_unb_b0s = upsamp_dir / (subjroot + '_dwi_eddy_den_deg_unb_b0s.mif')
    subprocess.run(['dwiextract', '-info', '-force', '-bzero', dwi_eddy_den_deg_unb, dwi_eddy_den_deg_unb_b0s])

    # b. Compute mean b0
    dwi_eddy_den_deg_unb_meanb0 = upsamp_dir / (subjroot + '_dwi_eddy_den_deg_unb_meanb0.mif')
    subprocess.run(['mrmath', '-info', '-force', '-axis', '3', dwi_eddy_den_deg_unb_b0s, 'mean',
                    dwi_eddy_den_deg_unb_meanb0])

    # c. Convert mean b0 to NII.GZ
    dwi_eddy_den_deg_unb_meanb0_NIIGZ = upsamp_dir / (subjroot + '_dwi_eddy_den_deg_unb_meanb0.nii.gz')
    subprocess.run(['mrconvert', '-info', '-force', dwi_eddy_den_deg_unb_meanb0,
                    dwi_eddy_den_deg_unb_meanb0_NIIGZ])

    # d. Create mask
    dwi_eddy_den_deg_unb_meanb0maskroot = upsamp_dir / (subjroot + '_dwi_eddy_den_deg_unb_meanb0')
    subprocess.run(['bet2', dwi_eddy_den_deg_unb_meanb0_NIIGZ, dwi_eddy_den_deg_unb_meanb0maskroot, '-m', '-v'])

    # e. Convert mask back to MIF
    dwi_eddy_den_deg_unb_meanb0mask_NIIGZ = upsamp_dir / (subjroot + '_dwi_eddy_den_deg_unb_meanb0_mask.nii.gz')
    dwi_eddy_den_deg_unb_meanb0mask = upsamp_dir / (subjroot + '_dwi_eddy_den_deg_unb_meanb0_mask.mif')
    subprocess.run(['mrconvert', '-info', '-force', dwi_eddy_den_deg_unb_meanb0mask_NIIGZ,
                    dwi_eddy_den_deg_unb_meanb0mask])

    # f. Upsample mask
    dwi_eddy_den_deg_unb_meanb0mask_ups = upsamp_dir / (subjroot + '_dwi_eddy_den_deg_unb_meanb0_mask_ups.mif')
    subprocess.run(['mrgrid', '-info', '-force', dwi_eddy_den_deg_unb_meanb0mask, 'regrid',
                    dwi_eddy_den_deg_unb_meanb0mask_ups, '-template', dwi_eddy_den_deg_unb_ups,
                    '-interp', 'linear', '-datatype', 'bit'])

    # g. Filter mask
    dwi_eddy_den_deg_unb_meanb0mask_ups_filt = upsamp_dir / (subjroot +
                                                             '_dwi_eddy_den_deg_unb_meanb0_mask_ups_filt.mif')
    subprocess.run(['maskfilter', '-info', '-force', dwi_eddy_den_deg_unb_meanb0mask_ups, 'median',
                    dwi_eddy_den_deg_unb_meanb0mask_ups_filt])

    ##########################################
    # ----Copying Preprocessed DTI Files---- #
    ##########################################

    # 1. Define output paths and filenamesfor the final, preprocessed volumes and brain mask (in .MIF format)
    #    dti/preprocessing/sub-XXX_ses-YY_ppd.mif
    dwiproc_out = preproc_dir/(subjroot + '_ppd.mif')
    # dti/preprocessing/sub-XXX_ses-YY_mask_ppd.mif
    dwimaskproc_out = preproc_dir/(subjroot + '_mask_ppd.mif')
    dwibvalproc_out = preproc_dir/(subjroot + '_ppd.bval')
    dwibvecproc_out = preproc_dir/(subjroot + '_ppd.bvec')

    # 2. Copy preprocessed DTI volumes file to preprocessing directory and rename it sub-XXX_ses-YY_ppd.mif
    shutil.copy(dwi_eddy_den_deg_unb_ups, dwiproc_out)

    # 3. Copy preprocessed DTI mask file to preprocessing directory and rename it sub-XXX_ses-YY_mask_ppd.mif
    shutil.copy(dwi_eddy_den_deg_unb_meanb0mask_ups_filt,
                dwimaskproc_out)

    # 4. Copy preprocessed bvecs and bvals to preprocessing directory and rename them
    #    sub-XXX_ses-YY_ppd.bvec/bval
    shutil.copy(bvec_eddy, dwibvecproc_out)
    shutil.copy(bval_eddy, dwibvalproc_out)


###########################################
# ----Starting Preprocessing Pipeline---- #
###########################################

subjs = ['sub-001']

# ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir / 'dwi').exists() and
#             ses_dir.parents[0].name in subjs)
ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir / 'dwi' / 'preprocessed').exists())

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=4, verbose=1)(
        delayed(dwicorr_2)(ses_dir) for ses_dir in sorted(ses_dirs))
