#!/usr/bin/env python3
# coding: utf-8

import subprocess

from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

# Loops through the non-bedpostx directories in the autoptx preproc directory
# and applies the nat2std warp to each dti_FA file

preproc_dir = Path('/fast_scratch/jdr/PNC/BIDS_Preproc/')


def rundtifit(subjdir):
    subjdir = Path(subjdir)
    dti = Path(subjdir, 'ses-01', 'dwi', str(subjdir.name + '_ses-01_run-01_space-T1w_desc-preproc_dwi.nii.gz'))
    bvals = Path(subjdir, 'ses-01', 'dwi', str(subjdir.name + '_ses-01_run-01_space-T1w_desc-preproc_dwi.bval'))
    bvecs = Path(subjdir, 'ses-01', 'dwi', str(subjdir.name + '_ses-01_run-01_space-T1w_desc-preproc_dwi.bvec'))
    mask = Path(subjdir, 'ses-01', 'dwi', str(subjdir.name + '_ses-01_run-01_space-T1w_desc-brain_mask.nii.gz'))
    dtifit_out = Path(subjdir, 'ses-01', 'dwi', str(subjdir.name + '_ses-01_run-01_space-T1w_dtifit'))
    subprocess.run(['dtifit', '-k', dti, '-m', mask, '-r', bvecs, '-b', bvals, '-o', dtifit_out])


subjdirs = (subjdir for subjdir in preproc_dir.glob('sub-*'))
with parallel_backend("loky", inner_max_num_threads=4):
    results = Parallel(n_jobs=8, verbose=1)(delayed(rundtifit)(subjdir) for subjdir in sorted(subjdirs))
