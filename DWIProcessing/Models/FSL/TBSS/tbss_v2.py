#!/usr/bin/env python3
# coding: utf-8

import subprocess
import shutil
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
tbssproc_dir = Path('/fast_scratchscratch/jdrussell3/fsl/cross_sec/tbss')


class tbss_run():

    def __init__(self, ses_dir):
        self.ses_dir = Path(ses_dir)
        self.subj_dir = self.ses_dir.parent
        self.preproc_dir = self.ses_dir / 'dwi' / 'preprocessed'
        self.subjroot = "_".join([self.subj_dir.name, self.ses_dir.name])
        self.main()

    def cp_proc2scratch(self):
        self.dtifitsubj_dir = tbssproc_dir / 'dtifit' / self.subjroot
        if self.dtifitsubj_dir.exists():
            shutil.rmtree(self.dtifitsubj_dir)
        self.dtifitsubj_dir.mkdir(parents=True)

        dwi_mif = self.preproc_dir / (self.subjroot + '_ppd.mif')
        dwimask_mif = self.preproc_dir / (self.subjroot + '_mask_ppd.mif')
        bvec = self.preproc_dir / (self.subjroot + '_ppd.bvec')
        bval = self.preproc_dir / (self.subjroot + '_ppd.bval')

        self.dwi_nii = self.dtifitsubj_dir / (self.subjroot + '_ppd.nii')
        self.dwimask_nii = self.dtifitsubj_dir / (self.subjroot + '_mask_ppd.nii')
        self.dwibvec = self.dtifitsubj_dir / (self.subjroot + '_ppd.bvec')
        self.dwibval = self.dtifitsubj_dir / (self.subjroot + '_ppd.bval')

        shutil.copy2(bvec, self.dwibvec)
        shutil.copy2(bval, self.dwibval)
        subprocess.run(['mrconvert', '-force', dwi_mif, self.dwi_nii])
        subprocess.run(['mrconvert', '-force', dwimask_mif, self.dwimask_nii])

    def dtifit(self):
        logfile = self.dtifitsubj_dir / (self.subjroot + "_ppd.txt")
        with open(logfile, 'a') as log:
            dtifitbasename = Path(self.dtifitsubj_dir, self.dtifitsubj_dir) / self.subjroot
            subprocess.run(['dtifit', '-V', '-k', self.dwi_nii, '-m', self.dwimask_nii, '-r', self.dwibvec, '-b',
                            self.dwibval, '-o', dtifitbasename], stdout=log, stderr=subprocess.STDOUT)

    def main(self):
        self.cp_proc2scratch()
        self.dtifit()
        # self.makeTBSSdir()


def tbss_run_container(ses_dir):
    c = tbss_run(ses_dir)  # noqa: F841


ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir / 'dwi').exists())
with parallel_backend("loky", inner_max_num_threads=1):
    results = Parallel(n_jobs=32, verbose=1)(delayed(tbss_run)(ses_dir) for ses_dir in sorted(ses_dirs))
