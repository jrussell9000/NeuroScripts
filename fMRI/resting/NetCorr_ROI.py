#!/usr/bin/env python3
# coding: utf-8

import subprocess
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

rs_dir = Path('/fast_scratch/jdr/resting/workingAFNI/resting/amygnucs2PFC')
mni_mask_2mm = Path('/fast_scratch/jdr/resting/wb_masks/MNI_mask_2mm+tlrc.')
amygmasks_dir = Path('/fast_scratch/jdr/resting/masks/amygdala_subnuclei')


def netproc(nii):
    subjroot = str(nii.name)[0:14]
    masked_out = nii.parent / str(nii.stem + '_masked.nii')
    subprocess.run(['3dcalc', '-a', nii, '-b', mni_mask_2mm, '-exp', 'a*bool(b)', '-prefix', masked_out])
    for amygmask in amygmasks_dir.glob('*.nii.gz'):
        print(str(masked_out.name)[0:14] + "_" + str(amygmask.name)[0:3])
        wbcorr_root = masked_out.parent / (subjroot + "_" + str(amygmask.name)[0:5])
        subprocess.run(['3dNetCorr', '-inset', masked_out, '-mask',
                        '/Volumes/Vol6/YouthPTSD/ROIs/AFNI_Anat_Masks/PFC_AFNI_final+tlrc.', '-in_rois', amygmask,
                        '-fish_z', '-ts_wb_corr', '-prefix', wbcorr_root, '-nifti'])
        wbcorr_dir = wbcorr_root.parent / str(wbcorr_root.name + '_000_INDIV')
        wbcorr_out = wbcorr_dir / 'WB_CORR_ROI_001.nii.gz'
        wbcorr_out_smooth = wbcorr_dir / (subjroot + "_" + str(wbcorr_out.name).split('.')[0] + str('_smooth.nii.gz'))
        subprocess.run(['3dBlurToFWHM', '-input', wbcorr_out, '-FHWM', '6', '-prefix', wbcorr_out_smooth])


with parallel_backend("loky", inner_max_num_threads=1):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(netproc)(nii) for nii in sorted(rs_dir.glob('*.nii')))
