#!/usr/bin/env python3
# coding: utf-8

import os
import shutil
import subprocess
import sys
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #


nCoresPerJob = "4"
nJobs = 8

anat_dir = Path('/scratch/jdrussell3/projects/iapsreg/long/anat')
MNI152_T1_2mm = str(os.getenv('FSLDIR') + '/data/standard/MNI152_T1_2mm.nii.gz')
T1_2_MNI152_CNF = str(os.getenv('FSLDIR') + '/etc/flirtsch/T1_2_MNI152_2mm.cnf')
subjs = []

for niifile in sorted(anat_dir.glob('sub-011*.nii')):
    niifn = niifile.name
    subjid = niifn.split('_')[0]
    subjs.append(subjid)

subjidlist = list(sorted(set(subjs)))


def templ2mni(subjid):
    subj_dir = Path(anat_dir / subjid)
    if not subj_dir.exists():
        subj_dir.mkdir()
    subjs = list(anat_dir.glob(str(subjid + '*.nii')))
    subjT1_orig = subjs[0]
    subjT2_orig = subjs[1]
    subjT1 = subj_dir / subjs[0].name
    subjT2 = subj_dir / subjs[1].name

    shutil.copy2(subjT1_orig, subjT1)
    shutil.copy2(subjT2_orig, subjT2)

    subjT1norm = subj_dir / (subjT1.stem + '_norm.nii')
    subjT2norm = subj_dir / (subjT2.stem + '_norm.nii')

    process = subprocess.Popen(['N4BiasFieldCorrection', '-v', '-d', '3', '-i', subjT1, '-o', subjT1norm],
                               stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    for c in iter(process.stdout.readline, b''):  # replace '' with b'' for Python 3
        sys.stdout.write(c.decode('utf-8'))

    process = subprocess.Popen(['N4BiasFieldCorrection', '-v', '-d', '3', '-i', subjT2, '-o', subjT2norm],
                               stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    for c in iter(process.stdout.readline, b''):  # replace '' with b'' for Python 3
        sys.stdout.write(c.decode('utf-8'))

    subjtempl = subj_dir / (subjid + '_acq-AXFSPGRBRAVONEW_T1w_norm.nii')
    process = subprocess.Popen(['mri_robust_template', '--mov', subjT1norm, subjT2norm, '--template', subjtempl,
                                '--satit'], stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    for c in iter(process.stdout.readline, b''):  # replace '' with b'' for Python 3
        sys.stdout.write(c.decode('utf-8'))

    subjtemplbrain = subj_dir / (subjid + '_acq-AXFSPGRBRAVONEW_T1w_norm_brain.nii')

    process = subprocess.Popen(['bet2', subjtempl, subjtemplbrain, '-v'],
                               stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    for c in iter(process.stdout.readline, b''):  # replace '' with b'' for Python 3
        sys.stdout.write(c.decode('utf-8'))

    struct2mni_mat = subj_dir / 'struct2mni.mat'
    struct2mni_warp = subj_dir / 'struct2mni_warp.nii'
    subjtempl_mni = subj_dir / (subjid + '_acq-AXFSPGRBRAVONEW_T1w_norm_mni152.nii')

    process = subprocess.Popen(['flirt', '-v', '-in', subjtemplbrain,
                                '-ref', MNI152_T1_2mm,
                                '-omat', struct2mni_mat],
                               stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    for c in iter(process.stdout.readline, b''):  # replace '' with b'' for Python 3
        sys.stdout.write(c.decode('utf-8'))

    process = subprocess.Popen(['fnirt', '-v', '--in='+MNI152_T1_2mm,
                                '--aff='+str(struct2mni_mat), '--cout='+str(struct2mni_warp),
                                '--config='+T1_2_MNI152_CNF],
                               stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    for c in iter(process.stdout.readline, b''):  # replace '' with b'' for Python 3
        sys.stdout.write(c.decode('utf-8'))

    process = subprocess.Popen(['applywarp', '-v', '--ref='+MNI152_T1_2mm, '--in='+str(subjtempl),
                                '--warp='+str(struct2mni_warp), '--out='+str(subjtempl_mni)],
                               stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    for c in iter(process.stdout.readline, b''):  # replace '' with b'' for Python 3
        sys.stdout.write(c.decode('utf-8'))


with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=4, verbose=1)(
        delayed(templ2mni)(subjid) for subjid in subjidlist)
