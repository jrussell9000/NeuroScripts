#!/usr/bin/env python3
# coding: utf-8

import subprocess
import pandas as pd
from pathlib import Path


# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

autoptxproc_dir = Path("/Volumes/Vol6/YouthPTSD/autoptx")
tractsall_dir = autoptxproc_dir / 'tracts'

df = pd.DataFrame(columns=['ID', 'Tract', 'FA', 'AD', 'RD', 'MD', 'nVox'])
for subjses_dir in sorted(tractsall_dir.glob('sub-*')):
    print("-------------------------\n" +
          "----    " + subjses_dir.name + "    ----\n" +
          "-------------------------")
    for struct_dir in sorted(subjses_dir.glob('*')):
        tractsNorm = struct_dir / 'tracts' / 'tractsNorm.nii.gz'
        print(struct_dir.name)
        if tractsNorm.exists():
            dti_FA = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_FA.nii.gz'
            dti_mask = autoptxproc_dir / 'preproc' / subjses_dir.name / str('dti_mask_' + struct_dir.name + '.nii.gz')
            subprocess.run(['3dresample', '-master', dti_FA, '-prefix', dti_mask, '-inset', tractsNorm, '-rmode', 'NN', '-overwrite'])
            nvox = subprocess.run(['3dBrickStat', '-count', '-non-zero', dti_mask], stdout=subprocess.PIPE).stdout.strip().decode()
            fa = subprocess.run(['3dmaskave', '-q', '-mask', dti_mask, dti_FA], stdout=subprocess.PIPE).stdout.strip().decode()

            dti_L1 = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_L1.nii.gz'
            ad = subprocess.run(['3dmaskave', '-q', '-mask', dti_mask, dti_L1], stdout=subprocess.PIPE).stdout.strip().decode()

            dti_L2 = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_L2.nii.gz'
            dti_L3 = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_L3.nii.gz'
            dti_RD = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_RD.nii.gz'
            subprocess.run(['3dcalc', '-a', dti_L2, '-b', dti_L3, '-expr', '(a + b) / 2', '-prefix', dti_RD, '-overwrite'])
            rd = subprocess.run(['3dmaskave', '-q', '-mask', dti_mask, dti_RD], stdout=subprocess.PIPE).stdout.strip().decode()

            dti_MD = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_MD.nii.gz'
            md = subprocess.run(['3dmaskave', '-q', '-mask', dti_mask, dti_MD], stdout=subprocess.PIPE).stdout.strip().decode()

            df = df.append({'ID': subjses_dir.name, 'Tract': struct_dir.name, 'FA': fa, 'AD': ad, 'RD': rd, 'MD': md, 'nVox': nvox}, ignore_index=True)

export_csv = df.to_csv(r'/Volumes/Vol6/YouthPTSD/autoptx/test.csv', header=True)
