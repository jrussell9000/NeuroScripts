#!/usr/bin/env python3
# coding: utf-8

from pathlib import Path
import os
import subprocess
from joblib import parallel_backend, Parallel, delayed


# https://github.com/andrewjahn/OpenScience_Scripts/blob/master/script_fMRIPrep_Analysis.sh

BIDS_fmriprep = Path('/fast_scratch/jdr/resting/BIDS_fmriprep/fmriprep')
nTRs2Remove = 2


def removeTRs(ses_dir):
    subjses_root = str(ses_dir.parent.name + "_" + ses_dir.name)
    func_dir = ses_dir / 'func'
    func_input = func_dir / str(subjses_root +
                                "_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold.nii.gz")
    if func_input.exists():
        func_SS = func_dir / str(subjses_root +
                                 "_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold_SS.nii.gz")
        if func_SS.exists():
            os.remove(func_SS)
        # Drop the first 2 TRs from the scan !!! SPECIFIC TO YOUTH PTSD !!!
        nTRs = subprocess.run(['3dinfo', '-nt', func_input], stdout=subprocess.PIPE, text=True).stdout
        nTRsmin1 = str(int(nTRs) - 1)
        func_inputDropTRs = func_dir / str(subjses_root +
                                           "_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold" +
                                           ".nii.gz[" + str(nTRs2Remove) + '..' +
                                           nTRsmin1 + ']')
        subprocess.run(['3dTcat', '-prefix', func_SS, func_inputDropTRs])


def normalize(ses_dir):
    subjses_root = str(ses_dir.parent.name + "_" + ses_dir.name)
    func_dir = ses_dir / 'func'
    func_SS = func_dir / str(subjses_root +
                             "_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold_SS.nii.gz")
    if func_SS.exists():
        # Compute the mean scan across TRs
        func_mean = func_dir / str(subjses_root +
                                   "_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold_SS_mean.nii.gz")
        if func_mean.exists():
            os.remove(func_mean)
        subprocess.run(['3dTstat', '-prefix', func_mean, func_SS])

        # Standardize the scan as percent signal change (PSC)
        func_PSC = func_dir / str(subjses_root +
                                  "_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold_SS_PSC.nii.gz")
        if func_PSC.exists():
            os.remove(func_PSC)
        clip = subprocess.run(['3dClipLevel', func_SS], stdout=subprocess.PIPE, text=True).stdout
        calcstring = '(a/b * 100) * step(b - ' + clip.replace('\n', '') + ')'
        subprocess.run(['3dcalc', '-a', func_SS, '-b', func_mean, '-expr', calcstring, '-prefix', func_PSC])


def detrending(ses_dir):
    subjses_root = str(ses_dir.parent.name + "_" + ses_dir.name)
    func_dir = ses_dir / 'func'
    func_PSC = func_dir / str(subjses_root +
                              "_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold_SS_PSC.nii.gz")
    func_errts = func_dir / str(subjses_root +
                                "_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold_SS_PSC_errts.nii.gz")

    censor = func_dir / str(subjses_root + '_motion_censor.1D')
    CSF_demean = func_dir / str(subjses_root + '_CSF_demean.1D')
    WM_demean = func_dir / str(subjses_root + '_WM_demean.1D')

    # Now we need to drop the first N lines from each ort file, with N = to the number of TRs we removed.
    censor_SS = func_dir / str(subjses_root + '_motion_censor_SS.1D')
    CSF_demean_SS = func_dir / str(subjses_root + '_CSF_demean_SS.1D')
    WM_demean_SS = func_dir / str(subjses_root + '_WM_demean_SS.1D')

    if censor.exists():
        with open(censor) as censorfile:
            censorlines = censorfile.readlines()
        with open(censor_SS, 'w') as censorSSfile:
            censorSSfile.writelines(censorlines[nTRs2Remove:])

    if CSF_demean.exists():
        with open(CSF_demean) as csffile:
            csflines = csffile.readlines()
        with open(CSF_demean_SS, 'w') as csfSSfile:
            csfSSfile.writelines(csflines[nTRs2Remove:])

    if WM_demean.exists():
        with open(WM_demean) as wmfile:
            wmlines = wmfile.readlines()
        with open(WM_demean_SS, 'w') as wmSSfile:
            wmSSfile.writelines(wmlines[nTRs2Remove:])

    if func_errts.exists():
        os.remove(func_errts)

    if func_PSC.exists() and censor_SS.exists() and CSF_demean_SS.exists() and WM_demean_SS.exists():
        subprocess.run(['3dTproject', '-input', func_PSC, '-prefix', func_errts, '-censor', censor_SS, '-cenmode',
                        'NTRP', '-polort', '1', '-bandpass', '.01', '.1', '-ort', CSF_demean_SS, '-ort', WM_demean_SS])


# def smoothing(ses_dir):
#     subjses_root = str(ses_dir.parent.name + "_" + ses_dir.name)
#     func_dir = ses_dir / 'func'
#     func_errts = func_dir / str(subjses_root +
#                                 "_task-EPIresting_space-MNI152NLin2009cAsym_desc-preproc_bold_PSC_errts.nii.gz")
#     func_smooth = func_dir / str(subjses_root +
#                                  "_task-EPIresting_space-MNI152NLin2009cAsym_desc-preproc_bold_PSC_errts_smooth.nii.gz")
#     if func_smooth.exists():
#         os.remove(func_smooth)

#     if func_errts.exists():
#         subprocess.run(['3dBlurToFWHM', '-FWHM', '6', '-automask', '-prefix', func_smooth, '-input', func_errts])


def main(ses_dir):
    removeTRs(ses_dir)
    normalize(ses_dir)
    detrending(ses_dir)
    # smoothing(ses_dir)


ses_dirs = (ses_dir for ses_dir in BIDS_fmriprep.glob('*/ses-*'))

with parallel_backend("loky", inner_max_num_threads=1):
    results = Parallel(n_jobs=16, verbose=1)(
        delayed(main)(ses_dir) for ses_dir in sorted(ses_dirs))
