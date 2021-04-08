#!/usr/bin/env python3
# coding: utf-8

import os
import subprocess
import shutil
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

rs_dir = Path('/fast_scratch/jdr/resting/NetCorrROIs')
roimasks_dir = Path('/fast_scratch/tjk/PNC/seeds/')
BIDS_fmriprep = Path('/fast_scratch/jdr/resting/BIDS_fmriprep/fmriprep')


def netproc(ses_dir):
    subjses_root = str(ses_dir.parent.name + "_" + ses_dir.name)
    func_dir = ses_dir / 'func'
    errts = func_dir / str(subjses_root + '_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold_SS_PSC_errts.nii.gz')
    fconn_dir = func_dir / 'fconn'
    if fconn_dir.exists():
        shutil.rmtree(fconn_dir)
        os.mkdir(fconn_dir)
    if errts.exists():
        for roimask in roimasks_dir.glob('*HBA*.nii.gz'):
            print(roimask.name.split('_HBA')[0])
            # The ROIs in the roimasks_dir specified above are of the format region_HBA_blah.nii.gz, 
            # so we split at the '_HBA' part to just get the region
            seedconn = fconn_dir / str(subjses_root + '_task-rest_conn_fishZ_' + roimask.name.split('_HBA')[0])
            # Using the inset (errts), calculate the correlation between the ROI (roimask) and the rest of the brain
            # then convert the correlations to Z-scores, and output it as a NIFTI
            subprocess.run(['3dNetCorr', '-inset', errts, '-in_rois', roimask,
                            '-fish_z', '-ts_wb_Z', '-prefix', seedconn, '-nifti'])
            # AFNI puts the ROI to whole brain map in a weird subdirectory with an uninformative name
            # Copy it to the fconn directory and rename it
            wbzroi_dir = fconn_dir / str(subjses_root + '_task-rest_conn_fishZ_' + roimask.name.split('_HBA')[0] + '_000_INDIV')
            wbzroi_orig = wbzroi_dir / str('WB_Z_ROI_001.nii.gz')
            wbzroi = fconn_dir / str('WB_Z_' + roimask.name.split('_HBA')[0] + '.nii.gz')
            shutil.copy(wbzroi_orig, wbzroi)
            # Create a map of connectivity between the ROI and just the PFC (or any other ROI) by multiplying the
            # whole brain to ROI map (wbzroi) by the PFC 
            pfczroi = fconn_dir / str('PFC_Z_' + roimask.name.split('_HBA')[0] + '.nii.gz')
            subprocess.run(['3dcalc', '-a', wbzroi, '-b', '/fast_scratch/tjk/PNC/seeds/PFC_AFNI_final.nii.gz',
                            '-expr', 'a*b', '-prefix', pfczroi])


def main(ses_dir):
    netproc(ses_dir)


ses_dirs = (ses_dir for ses_dir in BIDS_fmriprep.glob('*/ses-01'))


with parallel_backend("loky", inner_max_num_threads=1):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(netproc)(ses_dir) for ses_dir in ses_dirs)
