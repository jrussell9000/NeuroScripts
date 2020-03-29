#!/usr/bin/env python3
# coding: utf-8

import os
import subprocess
from pathlib import Path

# NOTE: This step does NOT need to be run if population_template was run with the -template_mask flag

# NOTE: Needs to be run manually from the command-line, subprocess/mrmaths have difficulty
# dealing with multiple paths (i.e., MIF files) in one argument

wmfod_template = Path('/Users/jdrussell3/scratch/mrtrix/fba/cross_sec/wmfod_template.mif')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
template_dir = Path('/scratch/jdrussell3/mrtrix/fba/cross_sec')
fod_input_dir = '/scratch/jdrussell3/mrtrix/fba/cross_sec/fod_input2'
mask_input_dir = '/scratch/jdrussell3/mrtrix/fba/cross_sec/mask_input2'

# Step 11. Compute the template mask (intersection of all subject masks in template space)
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html#compute-the-template-mask-intersection-of-all-subject-masks-in-template-space


def loadsubj(ses_dir):
    subj_dir = ses_dir.parent
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'
    subjroot = "_".join([subj_dir.name, ses_dir.name])

    dwiMaskUps = preproc_dir / (subjroot + '_mask_ppd.mif')
    subj2templwarp_mif = ss3t_dir / (subjroot + '_subj2templwarp.mif')
    return dwiMaskUps, ss3t_dir, subj2templwarp_mif, subjroot


def transformMask(dwiMaskUps, ss3t_dir, subj2templwarp_mif, subjroot):
    dwiMaskInTemplSpace = ss3t_dir / (subjroot + '_mask_ppd_reg2CrossSectempl.mif')
    subprocess.run(['mrtransform', dwiMaskUps, '-warp', subj2templwarp_mif, '-interp', 'nearest',
                    '-datatype', 'bit', dwiMaskInTemplSpace])
 

def computeTemplMask():
    mifstrs = []
    for mif in bidsproc_dir.glob('**/ses-01/dwi/preprocessed/sub*ses-01_mask_ppd_reg2CrossSectempl.mif'):
        mifstrs.append(str(mif))
    common_mask_paths = ' '.join(mifstrs)
    mask_template = str(template_dir / 'template_mask.mif')
    # cannot use subprocess with line below - doesn't accept common_mask_paths as multiple files
    os.system('mrmath ' + common_mask_paths + ' min ' + mask_template + ' -datatype' + ' bit')
    return mask_template


computeTemplMask(common_mask_dir, common_mask_paths, intersubj_mask_templ)
