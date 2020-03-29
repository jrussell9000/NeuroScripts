#!/usr/bin/env python3
# coding: utf-8

import subprocess
import os

from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

autoptx_dir = Path('/Volumes/Vol6/YouthPTSD/autoptx')

structList = [
              ["ar_l", "ar_r", "atr_l", "atr_r", "cgc_l", "cgc_r",
               "cgh_l", "cgh_r", "cst_l", "cst_r", "fma", "fmi",
               "ifo_l", "ifo_r", "ilf_l", "ilf_r", "mcp", "ml_l",
               "ml_r", "ptr_l", "ptr_r", "slf_l", "slf_r", "str_l",
               "str_r", "unc_l", "unc_r"],
              [10, 10, 1, 1, 20, 20, 3, 3, 4, 4, 0.6, 0.6, 4.4, 4.4,
               1.2, 1.2, 4.4, 1.2, 1.2, 20, 20, 0.4, 0.4, 0.8, 0.8, 1.2, 1.2]
             ]


def autoptx_2(subject_dir):
    newenv = os.environ.copy()
    os.chdir(autoptx_dir)
    autoptx_subj_logfile = subject_dir / str(subject_dir.name + '_log.txt')
    with open(autoptx_subj_logfile, 'a') as log:
        for i in range(len(structList[0])):
            if i % 2 == 0:  # even
                newenv["CUDA_VISIBLE_DEVICES"] = "0"
                log.write("#----Now Starting FSL's AutoPTX on GPU 0----#\n\n")
                log.flush()
                structure = structList[0][i]
                seed = str(structList[1][i])
                subprocess.run(['/Volumes/Users/jdrussell3/apps/fsl/autoptx/trackSubjectStruct', subject_dir.name,
                                structure, seed], env=newenv)
            if i % 2 == 1:  # odd
                newenv["CUDA_VISIBLE_DEVICES"] = "1"
                log.write("#----Now Starting FSL's AutoPTX on GPU 1----#\n\n")
                log.flush()
                structure = structList[0][i]
                seed = str(structList[1][i])
                subprocess.run(['/Volumes/Users/jdrussell3/apps/fsl/autoptx/trackSubjectStruct', subject_dir.name,
                                structure, seed], env=newenv)


subject_dirs = (subject_dir for subject_dir in autoptx_dir.glob('sub-*'))

with parallel_backend("loky", inner_max_num_threads=32):
    results = Parallel(n_jobs=2, verbose=1)(
        delayed(autoptx_2)(subject_dir) for subject_dir in sorted(subject_dirs))
