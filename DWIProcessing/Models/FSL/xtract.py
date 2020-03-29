#!/usr/bin/env python3
# coding: utf-8

import os
import subprocess
import shutil
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

xtract_dir = Path('/scratch/jdrussell3/fsl/cross_sec/xtract/')
xtractlogs_dir = Path('/scratch/jdrussell3/fsl/cross_sec/xtract/logs')
if xtractlogs_dir.exists():
    shutil.rmtree(xtractlogs_dir)
xtractlogs_dir.mkdir()

bedpostx_dirs_str = (str(bedpostx_dir) for bedpostx_dir in sorted(Path(xtract_dir / 'bedpostx').glob('sub-*')))
bedpostxdirs_list = list(bedpostx_dirs_str)


def run_xtract(bedpostxsubj_dir):

    subjroot = bedpostxsubj_dir.name.split('.')[0]
    logfile = xtractlogs_dir / (subjroot + "_ppd.txt")

    with open(logfile, 'a') as log:
        newenv = os.environ.copy()
        bedpostxsubjdir_str = str(bedpostxsubj_dir)
        for i in range(len(bedpostxdirs_list)):
            if bedpostxsubjdir_str in bedpostxdirs_list[i]:
                if i % 2 == 0:  # even
                    newenv["CUDA_VISIBLE_DEVICES"] = "0"
                    log.write("#----Now Starting FSL's XTRACT on GPU 0----#\n\n")
                    log.flush()

                elif i % 2 == 1:  # odd
                    newenv["CUDA_VISIBLE_DEVICES"] = "1"
                    log.write("#----Now Starting FSL's XTRACT on GPU 1----#\n\n")
                    log.flush()

        xtractout_dir = xtract_dir / (subjroot + '.xtract')
        std2diff = bedpostxsubj_dir / 'xfms' / 'standard2diff.mat'
        diff2std = bedpostxsubj_dir / 'xfms' / 'diff2standard.mat'
        subprocess.run(['xtract', '-bpx', str(bedpostxsubj_dir), '-out', str(xtractout_dir),
                        '-species', 'HUMAN', '-stdwarp', std2diff, diff2std, '-gpu'],
                       env=newenv, stdout=log, stderr=subprocess.STDOUT)


bedpostxsubj_dirs = (bedpostxsubj_dir for bedpostxsubj_dir in sorted(Path(xtract_dir / 'bedpostx').glob('sub-*')))

with parallel_backend("loky", inner_max_num_threads=32):
    results = Parallel(n_jobs=2, verbose=1)(
        delayed(run_xtract)(bedpostxsubj_dir) for bedpostxsubj_dir in sorted(bedpostxsubj_dirs))
