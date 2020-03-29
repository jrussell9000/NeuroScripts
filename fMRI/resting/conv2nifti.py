#!/usr/bin/env python3
# coding: utf-8

import gzip
import os
import shutil
import subprocess
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
appendage = '_task-EPIEMOReg1_bold.IAPSnegTS_updated_warped_cross+tlrc.HEAD'
nCoresPerJob = "4"
nJobs = 8

###PROBLEM - ses-01 and ses-02 files are in the same directory: ses-02/align_MNI_long


class afni_conv():

    def __init__(self, ses_dir):
        self.ses_dir = ses_dir
        self.subj_dir = ses_dir.parent
        self.alignmni_dir = ses_dir / 'align_MNI'
        self.subjroot = "_".join([self.subj_dir.name, self.ses_dir.name])
        afni_headfile_orig = self.alignmni_dir / str(self.subjroot + appendage)
        if afni_headfile_orig.exists():
            self.main(afni_headfile_orig)
        else:
            next

    def copy2scratch(self, afni_headfile_orig):
        afniconv_dir = Path('/scratch/jdrussell3/afniconv')
        afni_headfile_orig = Path(afni_headfile_orig)
        if not afniconv_dir.exists():
            afniconv_dir.mkdir()
        afni_headfile = afniconv_dir / afni_headfile_orig.name
        shutil.copy2(afni_headfile_orig, afni_headfile)
        afni_brikfile_orig = afni_headfile_orig.with_suffix('.BRIK')
        afni_brikfile = afniconv_dir / afni_brikfile_orig.name
        shutil.copy2(afni_brikfile_orig, afni_brikfile)
        afni_root = afni_headfile.parent / afni_headfile.stem
        return afni_root

    def afni2nifti(self, afni_root):
        afni_froot = afni_root.name.split('+')[0]
        NII_file = str(afni_froot + '.nii')

        os.chdir(afni_root.parent)
        subprocess.run(['3dAFNItoNIFTI', afni_root, '-prefix', NII_file])

        NIIGZ_file = str(afni_froot + '.nii.gz')
        with open(NII_file, 'rb') as f_in:
            with gzip.open(NIIGZ_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        os.remove(NII_file)
        os.remove(afni_root.parent / (afni_root.name + '.HEAD'))
        os.remove(afni_root.parent / (afni_root.name + '.BRIK'))

        NIIGZ_file_bidsproc = self.alignmni_dir / NIIGZ_file
        shutil.copy2(NIIGZ_file, NIIGZ_file_bidsproc)
        os.remove(NIIGZ_file)

    def main(self, afni_file_orig):
        afni_root = self.copy2scratch(afni_file_orig)
        self.afni2nifti(afni_root)


ses_dirs = lambda: (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-02')  # noqa: E731
                    if Path(ses_dir / 'align_MNI').exists())


def container(ses_dir):
    c = afni_conv(ses_dir)  # noqa: F841


with parallel_backend("loky", inner_max_num_threads=nCoresPerJob):
    results = Parallel(n_jobs=nJobs, verbose=1)(
        delayed(container)(ses_dir) for ses_dir in sorted(ses_dirs()))
