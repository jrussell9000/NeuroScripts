#!/usr/bin/env python3
# coding: utf-8

import os
from pathlib import Path
import shutil
import subprocess
from joblib import parallel_backend, delayed, Parallel

nCores = 8


smoothFD_dir = Path('/fast_scratch/jdr/dti_longproc/FD_smooth')
smoothFDC_dir = Path('/fast_scratch/jdr/dti_longproc/FDC_smooth')
smoothlogFC_dir = Path('/fast_scratch/jdr/dti_longproc/logFC_smooth')

for smoothFD in smoothFD_dir.glob('sub-*_ses*'):
    subj = str(smoothFD.name)[0:7]
    subj_diff = smoothFD_dir / (subj + '_diff_fd.mif')
    if subj_diff.exists():
        next
    else:
        subj_FD1 = smoothFD_dir / (subj + '_ses-01_fd.mif')
        subj_FD2 = smoothFD_dir / (subj + '_ses-02_fd.mif')
        subprocess.run(['mrcalc', '-force', subj_FD1, subj_FD2, '-subtract', subj_diff])

for smoothFDC in smoothFDC_dir.glob('sub-*_ses*'):
    subj = str(smoothFDC.name)[0:7]
    subj_diff = smoothFDC_dir / (subj + '_diff_fdc.mif')
    if subj_diff.exists():
        next
    else:
        subj_FDC1 = smoothFDC_dir / (subj + '_ses-01_fdc.mif')
        subj_FDC2 = smoothFDC_dir / (subj + '_ses-02_fdc.mif')
        subprocess.run(['mrcalc', '-force', subj_FDC1, subj_FDC2, '-subtract', subj_diff])

for smoothlogFC in smoothlogFC_dir.glob('sub-*_ses*'):
    subj = str(smoothlogFC.name)[0:7]
    subj_diff = smoothlogFC_dir / (subj + '_diff_logfc.mif')
    if subj_diff.exists():
        next
    else:
        subj_logFC1 = smoothlogFC_dir / (subj + '_ses-01_logfc.mif')
        subj_logFC2 = smoothlogFC_dir / (subj + '_ses-02_logfc.mif')
        subprocess.run(['mrcalc', '-force', subj_logFC1, subj_logFC2, '-subtract', subj_diff])
