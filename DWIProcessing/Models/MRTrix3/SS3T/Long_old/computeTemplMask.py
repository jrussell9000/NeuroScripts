#!/usr/bin/env python3
# coding: utf-8

import os
import subprocess
from pathlib import Path

# NOTE: Needs to be run manually from the command-line, subprocess/mrmaths have difficulty
# dealing with multiple paths (i.e., MIF files) in one argument


ss3t_longproc_dir = Path('/scratch/jdrussell3/dti_longproc/')
intersubj_mask_templ = ss3t_longproc_dir / 'YouthPTSD_masktempl_long.mif'
common_mask_dir = ss3t_longproc_dir / 'common_mask_creation'


mifstrs = []
for mif in list(common_mask_dir.glob('*.mif')):
    mifstrs.append(str(mif))
common_mask_paths = ' '.join(mifstrs)
print(common_mask_paths)


def computeTemplMask(common_mask_dir, common_mask_paths, intersubj_mask_templ):
    os.chdir(common_mask_dir)
    subprocess.run(['mrmath', common_mask_paths, 'min', intersubj_mask_templ, '-datatype', 'bit'])


computeTemplMask(common_mask_dir, common_mask_paths, intersubj_mask_templ)
