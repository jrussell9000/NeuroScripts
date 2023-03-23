#!/usr/bin/env python3
# coding: utf-8

import sys
from pathlib import Path
import subprocess
from joblib import parallel_backend, delayed, Parallel

BIDS_Master = Path('/fast_scratch/sah/BIDS_Master_test/')
fastSurfer_script = Path('/Users/jdrussell3/NeuroScripts/Structural/fastsurfer_gpudocker.sh')

# Function for running fmriprep script, passing the subject directory name as input
def runFastSurfer(subj_dir):
    try:
        subj_dirname = subj_dir.name
        subprocess.run(['bash', fastSurfer_script, subj_dirname])
    except:
        print("Subject: " + str(subj_dirname) + " didn't complete preprocessing.")

# Generator creating an iteratable list of subject directories in the specified BIDS_Master directory
subj_dirs = (subj_dir for subj_dir in sorted(BIDS_Master.glob('*/sub-*')))

# Run up to 16 instances of the runfMRIPrep script above, looping over subj_dirs, and allotting 8 cores to each
with parallel_backend("loky", inner_max_num_threads=4):
    results = Parallel(n_jobs=33, verbose=1)(
        delayed(runFastSurfer)(subj_dir) for subj_dir in sorted(subj_dirs))
