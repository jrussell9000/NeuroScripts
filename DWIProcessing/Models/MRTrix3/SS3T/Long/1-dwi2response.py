#!/usr/bin/env python3
# coding: utf-8

import subprocess
import os
import shutil
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel


def dwi2response(ses_dir):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    proc_dir = ses_dir / 'dwi' / 'processed'
    if not proc_dir.exists():
        proc_dir.mkdir()
    mrtrix_dir = proc_dir / 'mrtrix'
    if not mrtrix_dir.exists():
        mrtrix_dir.mkdir()
    ss3t_dir = mrtrix_dir / 'ss3t'
    if ss3t_dir.exists():
        shutil.rmtree(ss3t_dir)
    ss3t_dir.mkdir()

    dwi_ppd = preproc_dir / (subjroot + '_ppd.mif')
    dwi_mask_ppd = preproc_dir / (subjroot + '_mask_ppd.mif')
    response_wm = ss3t_dir / (subjroot + '_response_wm.txt')
    response_gm = ss3t_dir / (subjroot + '_response_gm.txt')
    response_csf = ss3t_dir / (subjroot + '_response_csf.txt')
    os.chdir('/tmp')
    # dwi2response included with MRTrix3Tissue has issues: see https://github.com/3Tissue/MRtrix3Tissue/issues/12
    subprocess.run(['/Volumes/apps/linux/mrtrix-current/bin/dwi2response', '-force', '-mask', dwi_mask_ppd,
                    'dhollander', dwi_ppd, response_wm, response_gm, response_csf])


bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')

ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir / 'dwi').exists() and
            not Path(ses_dir / 'dwi' / 'processed' / 'mrtrix' / 'ss3t').exists())

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(dwi2response)(ses_dir) for ses_dir in sorted(ses_dirs))
