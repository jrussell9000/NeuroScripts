#!/usr/bin/env python3
# coding: utf-8

import os
import shutil
import subprocess
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')

subjs = ['sub-001']

ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir / 'dwi').exists() and ses_dir.parents[0].name in subjs)

for ses_dir in ses_dirs:

    # 1. Setting variables
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    orig_dir = ses_dir / 'dwi' / 'original'
    eddy_dir = preproc_dir / 'eddy'
    preeddy_dir = preproc_dir / 'pre-eddy'
    eddy_dir = ses_dir / 'dwi' / 'preprocessed' / 'eddy'
    eddy_basename = str(eddy_dir / (subjroot + '_dwi_eddy'))
    eddy_index = eddy_dir / 'eddy_index.txt'
    eddy_acqp = eddy_dir / 'eddy_acqp.txt'
    eddy_mask = preeddy_dir / (subjroot + '_native_mnb0_brain_mask.nii.gz')
    eddy_bvec = eddy_dir / (subjroot + '_dwi_eddy.eddy_rotated_bvecs')
    inputbval = orig_dir / (subjroot + '_dwi.bval')
    fmap_ph_brain_s4_reg_2_mnb0_brain = preeddy_dir / (subjroot + '_fmap_ph_brain_s4_reg_2_mnb0_brain.nii.gz')
    fieldmap2eddy = fmap_ph_brain_s4_reg_2_mnb0_brain.parent / fmap_ph_brain_s4_reg_2_mnb0_brain.stem.split('.')[0]

    quad_out = eddy_dir / (subjroot + '_dwi_eddy.qc')
    if quad_out.exists():
        shutil.rmtree(quad_out)
    subprocess.run(['eddy_quad', eddy_basename,
                    '-idx='+str(eddy_index),
                    '-par='+str(eddy_acqp),
                    '-m='+str(eddy_mask),
                    '-b='+str(inputbval),
                    '-g='+str(eddy_bvec),
                    '-f='+str(fieldmap2eddy),
                    '-s=/Users/jdrussell3/slspec.txt',
                    '-v'])
