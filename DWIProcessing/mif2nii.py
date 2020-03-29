#!/usr/bin/env python3
# coding: utf-8

import subprocess
import os
import shutil
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
template_dir = Path('/scratch/jdrussell3/mrtrix/cross_sec2')
out_dir = Path('/Volumes/Vol6/YouthPTSD/dtiproc/ses-01')

nCoresPerJob = "4"
nJobs = 8

mrtrix_env = os.environ.copy()
mrtrix_env["MRTRIX_NTHREADS"] = nCoresPerJob


def mif2nii(ses_dir):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    orig_dwi_mif = preproc_dir / (subjroot + "_ppd.mif")
    orig_mask_mif = preproc_dir / (subjroot + "_mask_ppd.mif")
    orig_bvals = preproc_dir / (subjroot + "_ppd.bval")
    orig_bvecs = preproc_dir / (subjroot + "_ppd.bvec")

    dwi_niigz = out_dir / (subjroot + "_ppd.nii.gz")
    dwi_mask_niigz = out_dir / 'masks' / (subjroot + "_mask_ppd.nii.gz")
    dwi_bvals = out_dir / 'bvals' / (subjroot + "_ppd.bval")
    dwi_bvecs = out_dir / 'bvecs' / (subjroot + "_ppd.bvec")

    subprocess.run(['mrconvert', orig_dwi_mif, dwi_niigz])
    subprocess.run(['mrconvert', orig_mask_mif, dwi_mask_niigz])
    shutil.copy2(orig_bvals, dwi_bvals)
    shutil.copy2(orig_bvecs, dwi_bvecs)


ses_dirs = lambda: (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-01')  # noqa: E731
                    if Path(ses_dir / 'dwi').exists())


with parallel_backend("loky", inner_max_num_threads=nCoresPerJob):
    results = Parallel(n_jobs=nJobs, verbose=1)(
        delayed(mif2nii)(ses_dir) for ses_dir in sorted(ses_dirs()))
