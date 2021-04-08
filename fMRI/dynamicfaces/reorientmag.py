#!/usr/bin/env python3
# coding: utf-8

from pathlib import Path
import os
import subprocess

BIDS_Master = Path('/fast_scratch/jdr/dynamicfaces/BIDS_Master/')


def reorientmag(ses_dir):
    subjroot = str(ses_dir.parent.name + '_' + ses_dir.name)
    fmap_dir = ses_dir / 'fmap'
    magnitude = fmap_dir / str(subjroot + '_acq-FieldmapEPI_magnitude1.nii')
    magnitude_temp = fmap_dir / str(subjroot + '_tempmag.nii')
    subprocess.run(['3dresample', '-orient', 'LPI', '-input', magnitude, '-prefix', magnitude_temp])
    os.rename(magnitude_temp, magnitude)


ses_dirs = (ses_dir for ses_dir in BIDS_Master.glob('*/ses-*'))

for ses_dir in ses_dirs:
    reorientmag(ses_dir)
