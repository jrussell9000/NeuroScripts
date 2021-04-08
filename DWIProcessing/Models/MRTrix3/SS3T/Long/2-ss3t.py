#!/usr/bin/env python3
# coding: utf-8

import subprocess
import os
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
grpavgresp_wm = bidsproc_dir / 'dwi_resp' / 'group_average_response_wm.txt'
grpavgresp_gm = bidsproc_dir / 'dwi_resp' / 'group_average_response_gm.txt'
grpavgresp_csf = bidsproc_dir / 'dwi_resp' / 'group_average_response_csf.txt'


def ss3t(ses_dir):

    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'
    dwi_ppd = preproc_dir / (subjroot + '_ppd.mif')
    dwi_mask_ppd = preproc_dir / (subjroot + '_mask_ppd.mif')

    wmfod = ss3t_dir / (subjroot + '_wmfod.mif')
    gm = ss3t_dir / (subjroot + '_gm.mif')
    csf = ss3t_dir / (subjroot + '_csf.mif')

    os.chdir('/tmp')
    subprocess.run(['ss3t_csd_beta1', '-force', dwi_ppd, grpavgresp_wm, wmfod, grpavgresp_gm, gm, grpavgresp_csf, csf,
                    '-mask', dwi_mask_ppd])


ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir / 'dwi').exists())

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=16, verbose=1)(
        delayed(ss3t)(ses_dir) for ses_dir in sorted(ses_dirs))
