#!/usr/bin/env python3
# coding: utf-8

from pathlib import Path
import subprocess
from joblib import parallel_backend, delayed, Parallel

BIDS_Master = Path('/fast_scratch/jdr/resting/extrafmriprep_in')
BIDS_fmriprep = Path('/fast_scratch/jdr/resting/extrafmriprep_out')
fmriprep_script = Path('/Users/jdrussell3/NeuroScripts/fMRI/resting/fmriprep_cmd.sh')


def runfMRIPrep(subj_dir):
    try:
        subj_dirname = subj_dir.name
        subprocess.run(['bash', fmriprep_script, subj_dirname])
    except:
        print("Subject: " + str(subj_dirname) + " didn't complete preprocessing.")


subj_dirs = (subj_dir for subj_dir in BIDS_Master.glob('*sub*'))

# for subj_dir in subj_dirs:
#     runfMRIPrep(subj_dir.name)

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=16, verbose=1)(
        delayed(runfMRIPrep)(subj_dir) for subj_dir in sorted(subj_dirs))
