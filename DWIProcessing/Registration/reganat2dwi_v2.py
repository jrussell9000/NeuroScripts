#!/usr/bin/env python3
# coding: utf-8

import subprocess
import os
import shutil
import tempfile
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')

nCoresPerJob = "12"
nJobs = 8

mrtrix_env = os.environ.copy()
mrtrix_env["MRTRIX_NTHREADS"] = nCoresPerJob


class crosssec_anat2dtireg():

    def __init__(self, ses_dir):
        self.ses_dir = ses_dir
        self.subj_dir = ses_dir.parent
        self.dwi_preproc_dir = ses_dir / 'dwi' / 'preprocessed'
        self.subjroot = "_".join([self.subj_dir.name, self.ses_dir.name])
        self.main(ses_dir)

    def makedirs(self):
        self.anat_reg_dir = self.ses_dir / 'anat' / 'reg2dwippd'
        if not self.anat_reg_dir.exists():
            self.anat_reg_dir.mkdir()

    # Copy all the necessary files into the reg2dwippd subdirectory and give simpler names
    def copyfiles(self):
        dwi_ppd_orig = self.dwi_preproc_dir / (self.subjroot + '_ppd.mif')
        self.dwi_ppd = self.anat_reg_dir / (self.subjroot + '_ppd.mif')
        dwi_ppd_mask_orig = self.dwi_preproc_dir / (self.subjroot + '_mask_ppd.mif')
        self.dwi_mask_ppd = self.anat_reg_dir / (self.subjroot + '_mask_ppd.mif')
        anat_orig = self.ses_dir / 'anat' / (self.subjroot + '_acq-AXFSPGRBRAVONEW_T1w.nii')
        self.anat_nii = self.anat_reg_dir / (self.subjroot + '_T1.nii')
        # subprocess.run(['mrconvert', '-force', dwi_ppd_orig, dwi_ppd])
        shutil.copy2(dwi_ppd_orig, self.dwi_ppd)
        shutil.copy2(dwi_ppd_mask_orig, self.dwi_mask_ppd)
        shutil.copy2(anat_orig, self.anat_nii)

    # Skullstrip the anatomical scan using Robex - skullstripped anatomicals work better for flirt
    def skullstrip(self):
        self.anat_initmask_nii = self.anat_reg_dir / (self.subjroot + '_T1_initial_mask.nii')
        self.tmpdir = tempfile.mkdtemp(suffix=self.subjroot)
        # Run Robex to create a brain mask to feed into N4BiasCorrect (don't care about the skull stripped output yet)
        subprocess.run(['runROBEX.sh', self.anat_nii, str(self.tmpdir + 'T1_initial_brain.nii'), self.anat_initmask_nii])
        shutil.rmtree(self.tmpdir)

        # Using the just created brain mask, bias correct the anatomical (w/ skull)
        self.anat_biascorr_nii = self.anat_reg_dir / (self.subjroot + '_T1_biascorr.nii')
        subprocess.run(['N4BiasFieldCorrection', '-i', self.anat_nii, '-w', self.anat_initmask_nii, '-o',
                        self.anat_biascorr_nii])
        os.remove(self.anat_initmask_nii)

        # Skull strip the bias-corrected anatomical and save a mask
        self.anat_biascorr_brain_nii = self.anat_reg_dir / (self.subjroot + '_T1_biascorr_brain.nii')
        self.anat_biascorr_mask_nii = self.anat_reg_dir / (self.subjroot + '_T1_biascorr_mask.nii')
        subprocess.run(['runROBEX.sh', self.anat_biascorr_nii, self.anat_biascorr_brain_nii,
                        self.anat_biascorr_mask_nii])

        # Convert the bias-corrected anatomical (brain) and mask files to MIF
        self.anat_biascorr_brain = self.anat_reg_dir / (self.subjroot + '_T1_biascorr_brain.mif')
        self.anat_mask = self.anat_biascorr_mask_nii
        subprocess.run(['mrconvert', '-force', self.anat_biascorr_brain_nii, self.anat_biascorr_brain])
        subprocess.run(['mrconvert', '-force', self.anat_biascorr_mask_nii, self.anat_mask])

    # Extracting the mean b0 image we'll register/warp the anatomical to fit
    def genmeanbzero(self):

        # Extract the b0 volumes, create an average, and mask it using the pre-existing brain mask
        # we created during preprocessing
        dwi_bzeros = self.anat_reg_dir / (self.subjroot + '_bzeros.mif')
        subprocess.run(['dwiextract',  '-force', self.dwi_ppd, dwi_bzeros, '-bzero'])
        self.dwi_meanbzero = self.anat_reg_dir / (self.subjroot + '_meanbzero.mif')
        subprocess.run(['mrmath',  '-force', dwi_bzeros, 'mean', self.dwi_meanbzero, '-axis', '3'])

    def regT1_2_dwi(self):

        # Convert mean bzero to NII
        self.dwi_meanbzero_nii = self.anat_reg_dir / (self.subjroot + '_meanbzero.nii')
        subprocess.run(['mrconvert', '-force', self.dwi_meanbzero, self.dwi_meanbzero_nii])

        # Run epi_reg
        self.diff2struct = self.anat_reg_dir / (self.subjroot + '_diff2struct')
        subprocess.run(['epi_reg', '--epi='+str(self.dwi_meanbzero_nii), '--t1='+str(self.anat_biascorr_nii),
                        '--t1brain='+str(self.anat_biascorr_brain_nii), '--out='+str(self.diff2struct)])

        # Invert the affine matrix
        self.struct2diff = self.anat_reg_dir / (self.subjroot + '_struct2diff.mat')
        subprocess.run(['convert_xfm', '-omat', self.struct2diff, '-inverse', str(str(self.diff2struct) + '.mat')])

        # Convert dwi ppd to NII
        self.dwi_ppd_nii = self.anat_reg_dir / (self.subjroot + '_ppd.nii')
        subprocess.run(['mrconvert', '-force', self.dwi_ppd, self.dwi_ppd_nii])
        self.T1_biascorr_reg = self.anat_reg_dir / (self.subjroot + '_T1_reg.nii')
        subprocess.run(['applywarp', '--ref='+str(self.dwi_ppd_nii), '--in='+str(self.anat_biascorr_nii),
                        '--postmat='+str(self.struct2diff), '--out='+str(self.T1_biascorr_reg)])

    def main(self, ses_dir):
        self.makedirs()
        self.copyfiles()
        self.skullstrip()
        self.genmeanbzero()
        self.regT1_2_dwi()


ses_dirs = lambda: (ses_dir for ses_dir in sorted(bidsproc_dir.glob('*/ses-*'))  # noqa: E731
                    if Path(ses_dir / 'dwi').exists() and Path(ses_dir / 'anat').exists())


def anat2dtireg_container(ses_dir):
    c = crosssec_anat2dtireg(ses_dir)


with parallel_backend("loky", inner_max_num_threads=nCoresPerJob):
    results = Parallel(n_jobs=nJobs, verbose=1)(
        delayed(anat2dtireg_container)(ses_dir) for ses_dir in sorted(ses_dirs()))
