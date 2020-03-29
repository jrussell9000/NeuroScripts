#!/usr/bin/env python3
# coding: utf-8

import subprocess
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

wmfod_long_templ = Path('/Users/jdrussell3/scratch/mrtrix/fba/cross_sec/wmfod_template.mif')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')

# Continuing steps from : https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html
# Step 10 - Register all subject FOD images to the FOD template


def regfod2templ(ses_dir):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'

    dwi_mask_ppd = preproc_dir / (subjroot + '_mask_ppd.mif')
    wmfod_norm = ss3t_dir / (subjroot + '_wmfod_norm.mif')

    subj2templwarp = ss3t_dir / (subjroot + '_subj2templwarp.mif')
    templ2subjwarp = ss3t_dir / (subjroot + '_templ2subjwarp.mif')

    subprocess.run(['mrregister', '-force', wmfod_norm, '-mask1', dwi_mask_ppd, wmfod_long_templ, '-nl_warp',
                    subj2templwarp, templ2subjwarp])


ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-01') if Path(ses_dir / 'dwi').exists())

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(regfod2templ)(ses_dir) for ses_dir in sorted(ses_dirs))
