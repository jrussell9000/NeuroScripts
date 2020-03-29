#!/usr/bin/env python3
# coding: utf-8

import subprocess
from pathlib import Path
import shutil
from joblib import parallel_backend, delayed, Parallel

# NOTE: This script may not be necessary if the inter-subject population_template
# command was run with the '-template_mask' flag on....need to verify this.

ss3t_longproc_dir = Path('/scratch/jdrussell3/dti_longproc/')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
intersubj_mask_templ = ss3t_longproc_dir / 'YouthPTSD_masktempl_long.mif'
common_mask_dir = ss3t_longproc_dir / 'common_mask_creation'
if common_mask_dir.exists():
    shutil.rmtree(common_mask_dir)
common_mask_dir.mkdir()


def warpMasks2Templ(ses_dir):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'

    dwi_mask_ppd = preproc_dir / (subjroot + '_mask_ppd.mif')

    subj2templwarp = ss3t_dir / (subjroot + '_subj2templwarp.mif')
    dwi_mask_ppd_reg2templ = common_mask_dir / (subjroot + '_mask_ppd_reg2templ.mif')
    subprocess.run(['mrtransform', dwi_mask_ppd, '-warp', subj2templwarp, '-interp', 'nearest',
                    '-datatype', 'bit', dwi_mask_ppd_reg2templ])


def computeTemplMask(common_mask_dir, intersubj_mask_templ):
    mifstrs = []
    for mif in list(common_mask_dir.glob('*.mif')):
        mifstrs.append(str(mif))
    common_mask_paths = ' '.join(mifstrs)
    subprocess.run(['mrmath', common_mask_paths, 'min', intersubj_mask_templ, '-datatype', 'bit'])


ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir / 'dwi').exists())

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(warpMasks2Templ)(ses_dir) for ses_dir in sorted(ses_dirs))

computeTemplMask(common_mask_dir, intersubj_mask_templ)
