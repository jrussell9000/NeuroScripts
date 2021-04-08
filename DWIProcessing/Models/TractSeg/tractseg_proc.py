#!/usr/bin/env python3
# coding: utf-8

import os
import subprocess
import shutil
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
tractsegproc_dir = Path('/fast_scratch/jdr/tractseg')


class tractseg():

    def __init__(self, ses_dir):
        self.ses_dir = Path(ses_dir)
        self.subj_dir = self.ses_dir.parent
        self.preproc_dir = self.ses_dir / 'dwi' / 'preprocessed'
        self.subjroot = "_".join([self.subj_dir.name, self.ses_dir.name])
        self.main()

    def cp_proc2scratch(self):
        self.tractsegproc_rawsubj_dir = tractsegproc_dir / self.subjroot
        if not tractsegproc_dir.exists():
            tractsegproc_dir.mkdir()
        if self.tractsegproc_rawsubj_dir.exists():
            shutil.rmtree(self.tractsegproc_rawsubj_dir)
        self.tractsegproc_rawsubj_dir.mkdir(parents=True)

        dwi_mif = self.preproc_dir / (self.subjroot + '_ppd.mif')
        dwimask_mif = self.preproc_dir / (self.subjroot + '_mask_ppd.mif')
        bvec = self.preproc_dir / (self.subjroot + '_ppd.bvec')
        bval = self.preproc_dir / (self.subjroot + '_ppd.bval')

        self.dwi_nii = self.tractsegproc_rawsubj_dir / (self.subjroot + '_ppd.nii')
        self.dwimask_nii = self.tractsegproc_rawsubj_dir / (self.subjroot + '_mask_ppd.nii')
        self.dwibvec = self.tractsegproc_rawsubj_dir / (self.subjroot + '_ppd.bvec')
        self.dwibval = self.tractsegproc_rawsubj_dir / (self.subjroot + '_ppd.bval')

        shutil.copy2(bvec, self.dwibvec)
        shutil.copy2(bval, self.dwibval)
        subprocess.run(['mrconvert', '-force', dwi_mif, self.dwi_nii])
        subprocess.run(['mrconvert', '-force', dwimask_mif, self.dwimask_nii])

    def tractseg_run(self):
        logdir = tractsegproc_dir / 'logs'
        if not logdir.exists():
            logdir.mkdir()
        logfile = logdir / (self.subjroot + "_ppd.txt")
        if os.path.exists(logfile):
            os.remove(logfile)
        os.chdir(self.tractsegproc_rawsubj_dir)
        with open(logfile, 'a') as log:

            subprocess.run(['calc_FA', '-i', self.dwi_nii, '--bvals', self.dwibval, '--bvecs', self.dwibvec,
                            '--brain_mask', self.dwimask_nii, '-o', 'FA.nii.gz'],
                           stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(['TractSeg', '-i', self.dwi_nii, '--bvals', self.dwibval, '--bvecs', self.dwibvec,
                            '--super_resolution', '--brain_mask', self.dwimask_nii,
                            '--raw_diffusion_input', '-o', 'tractseg_output'],
                           stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(['TractSeg', '-i', 'tractseg_output/peaks.nii.gz', '-o', 'tractseg_output',
                            '--super_resolution', '--output_type', 'endings_segmentation'],
                           stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(['TractSeg', '-i', 'tractseg_output/peaks.nii.gz', '-o', 'tractseg_output',
                            '--super_resolution', '--output_type', 'TOM'],
                           stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(['Tracking', '-i', 'tractseg_output/peaks.nii.gz', '-o', 'tractseg_output',
                            '--nr_cpus', '8', '--nr_fibers', '5000'],
                           stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(['Tractometry', '-i', 'tractseg_output/TOM_trackings/', '-o',
                            str('Tractometry_' + self.subjroot + '.csv'), '-e',
                            'tractseg_output/endings_segmentations/', '-s', 'FA.nii.gz'],
                           stdout=log, stderr=subprocess.STDOUT)

    def main(self):
        self.cp_proc2scratch()
        self.tractseg_run()


def tractseg_container(ses_dir):
    c = tractseg(ses_dir)  # noqa: F841


ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-01') if Path(ses_dir / 'dwi').exists())
with parallel_backend("loky", inner_max_num_threads=4):
    results = Parallel(n_jobs=8, verbose=1)(delayed(tractseg)(ses_dir) for ses_dir in sorted(ses_dirs))
