#!/usr/bin/env python3
# coding: utf-8

import shutil
import subprocess
import pandas as pd
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

xtract_dir = Path('/fast_scratch/jdr/fsl/xtract')
df = pd.DataFrame(columns=['ID', 'Tract', 'FA', 'AD', 'RD', 'MD', 'nVox'])


def xtract_extract(xtractsubj_dir):
    subjroot = xtractsubj_dir.name.split('.')[0]
    bpxsubj_dir = xtract_dir / (subjroot + '.bedpostX')
    dtifitsubj_dir = xtract_dir / (subjroot)

    if bpxsubj_dir.exists():
        std2diff = bpxsubj_dir / 'xfms' / 'standard2diff.mat'
        shutil.copy(std2diff, xtractsubj_dir)

    if dtifitsubj_dir.exists():
        dti_FA = dtifitsubj_dir / (subjroot + '_FA.nii.gz')
        dti_L1 = dtifitsubj_dir / (subjroot + '_L1.nii.gz')
        dti_L2 = dtifitsubj_dir / (subjroot + '_L2.nii.gz')
        dti_L3 = dtifitsubj_dir / (subjroot + '_L3.nii.gz')
        dti_MD = dtifitsubj_dir / (subjroot + '_MD.nii.gz')
        dti_RD = dtifitsubj_dir / (subjroot + '_RD.nii.gz')

    logfile = xtractsubj_dir / (subjroot + "_reg2fa.txt")
    with open(logfile, 'a') as log:
        tractssubj_dir = xtractsubj_dir / 'tracts'
        for tract_dir in sorted(tractssubj_dir.glob('*')):
            print(tract_dir)
            densityNorm = tract_dir / 'densityNorm.nii.gz'
            densityNorm_warped = tract_dir / 'densityNorm_warped.nii.gz'
            warp2diff = tract_dir / 'warp2diff.nii.gz'
            subprocess.run(['fnirt', '--verbose', '--ref='+str(dti_FA), '--in='+str(densityNorm),
                            '--aff='+str(std2diff), '--cout='+str(warp2diff)],
                           stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(['applywarp', '--verbose', '--ref='+str(dti_FA), '--in='+str(densityNorm),
                            '--warp='+str(warp2diff), '--out='+str(densityNorm_warped)], stdout=log,
                           stderr=subprocess.STDOUT)

            fa = subprocess.run(['3dmaskave', '-q', '-mask', densityNorm_warped, dti_FA],
                                stdout=subprocess.PIPE).stdout.strip().decode()
            ad = subprocess.run(['3dmaskave', '-q', '-mask', densityNorm_warped, dti_L1],
                                stdout=subprocess.PIPE).stdout.strip().decode()
            md = subprocess.run(['3dmaskave', '-q', '-mask', densityNorm_warped, dti_MD],
                                stdout=subprocess.PIPE).stdout.strip().decode()
            subprocess.run(['3dcalc', '-a', dti_L2, '-b', dti_L3, '-expr', '(a + b) / 2', '-prefix', dti_RD,
                            '-overwrite'], stdout=log, stderr=subprocess.STDOUT)
            rd = subprocess.run(['3dmaskave', '-q', '-mask', densityNorm_warped, dti_RD],
                                stdout=subprocess.PIPE).stdout.strip().decode()
            nvox = subprocess.run(['3dBrickStat', '-count', '-non-zero', densityNorm_warped],
                                  stdout=subprocess.PIPE).stdout.strip().decode()

            global df
            df = df.append({'ID': subjroot, 'Tract': tract_dir.name, 'FA': fa, 'AD': ad, 'RD': rd, 'MD': md,
                            'nVox': nvox}, ignore_index=True)
            print(df)


xtractsubj_dirs = (xtractsubj_dir for xtractsubj_dir in sorted(xtract_dir.glob('sub-*xtract')))

with parallel_backend("loky", inner_max_num_threads=1):
    results = Parallel(n_jobs=51, verbose=1, require='sharedmem')(
        delayed(xtract_extract)(xtractsubj_dir) for xtractsubj_dir in sorted(xtractsubj_dirs))

export_csv = df.to_csv(r'/Volumes/Vol6/YouthPTSD/xtract.csv', header=True)

# 1. For each subject, for each tract directory
# 2. Copy the necessary files to it (FA, xfms)
# 3. Warp the densityNorm image to native space. e.g.,....
#   a. fnirt --ref=sub-001_ses-01_FA.nii.gz --in=densityNorm.nii.gz --aff=standard2diff.mat --cout=warp2diff
#   b. applywarp --ref=sub-001_ses-01_FA.nii.gz --in=densityNorm.nii.gz --warp=warp2diff.nii.gz --out=densityNorm_warped
# 4. Create a binary mask of the (warped) tract.
#   a. fslmaths densityNorm_warped -thr 0.001 -bin densityNorm_warped_bin
# 5. Multiply the mask and the FA image to get the FA for the tract
#   b. fslmaths densityNorm_warped -mul densityNorm_warped_bin densityNorm_FA
