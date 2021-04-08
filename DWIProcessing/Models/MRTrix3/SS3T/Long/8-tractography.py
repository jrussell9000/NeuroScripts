#!/usr/bin/env python3
# coding: utf-8

import os
from pathlib import Path
import subprocess

nCores = 96

newenv = os.environ.copy()
newenv["MRTRIX_NTHREADS"] = nCores

ss3t_longproc_dir = Path('/fast_scratch/jdr/dti_longproc/')
intersubj_wmfod_templ = ss3t_longproc_dir / 'YouthPTSD_wmfodtempl_long.mif'
intersubj_mask_templ = ss3t_longproc_dir / 'YouthPTSD_masktempl_long.mif'
tracks_20mil = ss3t_longproc_dir / 'tracks_20_million.tck'
tracks_2mil = ss3t_longproc_dir / 'tracks_2_million.tck'
os.chdir(ss3t_longproc_dir)
subprocess.run(['tckgen', '-angle', '22.5', '-maxlen', '250', '-minlen', '10', '-power', '1.0', intersubj_wmfod_templ,
                '-seed_image', intersubj_mask_templ, '-mask', intersubj_mask_templ, '-select', '20000000', '-cutoff',
                '0.06', tracks_20mil])

subprocess.run(['tcksift', tracks_20mil, intersubj_wmfod_templ, tracks_2mil, '-term_number', '2000000'])
