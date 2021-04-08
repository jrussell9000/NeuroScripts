#!/usr/bin/env python3
# coding: utf-8

from pathlib import Path
import os
import subprocess
from joblib import parallel_backend, Parallel, delayed


# https://github.com/andrewjahn/OpenScience_Scripts/blob/master/script_fMRIPrep_Analysis.sh

BIDS_fmriprep = Path('/fast_scratch/jdr/dynamicfaces/BIDS_fmriprep/fmriprep')


def smoothing(ses_dir):
    subjses_root = str(ses_dir.parent.name + "_" + ses_dir.name)
    func_dir = ses_dir / 'func'
    func_input = func_dir / str(subjses_root +
                                "_task-EPIDynamicFaces_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz")
    func_output = func_dir / str(subjses_root +
                                 "_task-EPIDynamicFaces_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold_smooth6.nii.gz")
    subprocess.run(['3dBlurToFWHM', '-input', func_input, '-prefix', func_output, '-FHWM', '4'])


def scaling(ses_dir):
    subjses_root = str(ses_dir.parent.name + "_" + ses_dir.name)
    func_dir = ses_dir / 'func'
    func_blur = func_dir / str(subjses_root + 
                               "_task-EPIDynamicFaces_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold_smooth6.nii.gz")

    func_blur_mean = func_dir / str(subjses_root +
                                    "_task-EPIDynamicFaces_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold_smooth6_mean.nii.gz")

    subprocess.run(['3dTstat', '-prefix', func_blur_mean, func_blur])

    func_mask = func_dir / str(subjses_root +
                               "_task-EPIDynamicFaces_space-MNI152NLin2009cAsym_res-2_desc-brain_mask.nii.gz")

    func_blur_scaled = func_dir / str(subjses_root +
                                      "_task-EPIDynamicFaces_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold_smooth6_scaled.nii.gz")

    subprocess.run(['3dcalc', '-a', func_blur, '-b', func_blur_mean, '-c', func_mask,
                    '-expr', "c * min(200, a/b*100)*step(a)*step(b)", '-prefix', func_blur_scaled])


def main(ses_dir):
    smoothing(ses_dir)
    scaling(ses_dir)


ses_dirs = (ses_dir for ses_dir in BIDS_fmriprep.glob('*/ses-*'))

with parallel_backend("loky", inner_max_num_threads=1):
    results = Parallel(n_jobs=16, verbose=1)(
        delayed(main)(ses_dir) for ses_dir in sorted(ses_dirs))
