#!/usr/bin/env python3
# coding: utf-8

import shutil
import subprocess


from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

# Loops through the non-bedpostx directories in the autoptx preproc directory
# and applies the nat2std warp to each dti_FA file

preproc_dir = Path('/Volumes/Vol6/YouthPTSD/autoptx/preproc')
fslref = Path('/Volumes/apps/linux/fsl-current/data/standard/FMRIB58_FA_1mm')
comb_dir = Path('/fast_scratch/jdr/dti_wb')


def reg2std(subjses_dir):
    subjses_dir = Path(subjses_dir)
    dti_FA = subjses_dir / "dti_FA.nii.gz"
    dti_MD = subjses_dir / "dti_MD.nii.gz"
    dti_RD = subjses_dir / "dti_RD.nii.gz"
    dti_L1 = subjses_dir / "dti_L1.nii.gz"

    # Can't (?) include file extensions in calls to applywarp
    subprocess.run(['applywarp', '--ref='+str(fslref), '--in='+str(dti_FA), '--warp='+str(subjses_dir / 'nat2std_warp'),
                    '--out='+str(subjses_dir / 'dti_FA_std')])
    subprocess.run(['applywarp', '--ref='+str(fslref), '--in='+str(dti_MD), '--warp='+str(subjses_dir / 'nat2std_warp'),
                    '--out='+str(subjses_dir / 'dti_MD_std')])
    subprocess.run(['applywarp', '--ref='+str(fslref), '--in='+str(dti_RD), '--warp='+str(subjses_dir / 'nat2std_warp'),
                    '--out='+str(subjses_dir / 'dti_RD_std')])
    subprocess.run(['applywarp', '--ref='+str(fslref), '--in='+str(dti_L1), '--warp='+str(subjses_dir / 'nat2std_warp'),
                    '--out='+str(subjses_dir / 'dti_L1_std')])

    dti_FA_std = subjses_dir / 'dti_FA_std.nii.gz'
    dti_MD_std = subjses_dir / 'dti_MD_std.nii.gz'
    dti_RD_std = subjses_dir / 'dti_RD_std.nii.gz'
    dti_L1_std = subjses_dir / 'dti_L1_std.nii.gz'

    dti_FA_std_subj = comb_dir / str(subjses_dir.name + '_FA_std.nii.gz')
    dti_MD_std_subj = comb_dir / str(subjses_dir.name + '_MD_std.nii.gz')
    dti_RD_std_subj = comb_dir / str(subjses_dir.name + '_RD_std.nii.gz')
    dti_L1_std_subj = comb_dir / str(subjses_dir.name + '_L1_std.nii.gz')

    shutil.copy2(dti_FA_std, dti_FA_std_subj)
    shutil.copy2(dti_MD_std, dti_MD_std_subj)
    shutil.copy2(dti_RD_std, dti_RD_std_subj)
    shutil.copy2(dti_L1_std, dti_L1_std_subj)


subjses_dirs = (subjses_dir for subjses_dir in preproc_dir.glob('sub-???_ses-01'))
with parallel_backend("loky", inner_max_num_threads=4):
    results = Parallel(n_jobs=8, verbose=1)(delayed(reg2std)(subjses_dir) for subjses_dir in sorted(subjses_dirs))
