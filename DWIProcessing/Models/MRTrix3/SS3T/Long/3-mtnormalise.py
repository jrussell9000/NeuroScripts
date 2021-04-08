#!/usr/bin/env python3
# coding: utf-8

import subprocess
import os
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')


def mtnormalise(ses_dir):

    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'

    dwi_mask_ppd = preproc_dir / (subjroot + '_mask_ppd.mif')
    wmfod = ss3t_dir / (subjroot + '_wmfod.mif')
    gm = ss3t_dir / (subjroot + '_gm.mif')
    csf = ss3t_dir / (subjroot + '_csf.mif')

    wmfod_norm = ss3t_dir / (subjroot + '_wmfod_norm.mif')
    gm_norm = ss3t_dir / (subjroot + '_gm_norm.mif')
    csf_norm = ss3t_dir / (subjroot + '_csf_norm.mif')

    os.chdir('/tmp')
    subprocess.run(['mtnormalise', '-force', wmfod, wmfod_norm, gm, gm_norm, csf, csf_norm, '-mask', dwi_mask_ppd])


#subjs = ['sub-142', 'sub-148', 'sub-149', 'sub-153', 'sub-154', 'sub-155', 'sub-156', 'sub-157']
ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir / 'dwi').exists())
            #and ses_dir.parents[0].name in subjs)

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(mtnormalise)(ses_dir) for ses_dir in sorted(ses_dirs))
