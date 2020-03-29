#!/usr/bin/env python3
# coding: utf-8

import subprocess
import os
import shutil
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


class reg2dwi():

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

    def copyfiles(self):
        dwi_ppd_orig = self.dwi_preproc_dir / (self.subjroot + '_ppd.mif')
        self.dwi_ppd = self.anat_reg_dir / (self.subjroot + '_ppd.mif')
        # subprocess.run(['mrconvert', '-force', dwi_ppd_orig, dwi_ppd])
        shutil.copy2(dwi_ppd_orig, self.dwi_ppd)
        dwi_ppd_mask_orig = self.dwi_preproc_dir / (self.subjroot + '_mask_ppd.mif')
        self.dwi_mask_ppd = self.anat_reg_dir / (self.subjroot + '_mask_ppd.mif')
        shutil.copy2(dwi_ppd_mask_orig, self.dwi_mask_ppd)
        anat_orig = self.ses_dir / 'anat' / (self.subjroot + '_acq-AXFSPGRBRAVONEW_T1w.nii')
        self.anat_nii = self.anat_reg_dir / (self.subjroot + '_T1.nii')
        shutil.copy2(anat_orig, self.anat_nii)

    def skullstrip(self):
        self.anat_initmask_nii = self.anat_reg_dir / (self.subjroot + '_T1_initial_mask.nii')
        subprocess.run(['runROBEX.sh', self.anat_nii, 'T1_initial_brain.nii', self.anat_initmask_nii])
        os.remove('T1_initial_brain.nii')
        self.anat_biascorr_nii = self.anat_reg_dir / (self.subjroot + '_T1_biascorr.nii')
        subprocess.run(['N4BiasFieldCorrection', '-i', self.anat_nii, '-w', self.anat_initmask, '-o',
                        self.anat_biascorr])
        self.anat_biascorr_brain_nii = self.anat_reg_dir / (self.subjroot + '_T1_biascorr_brain.nii')
        self.anat_biascorr_mask_nii = self.anat_reg_dir / (self.subjroot + '_T1_biascorr_mask.nii')
        subprocess.run(['runROBEX.sh', self.anat_biascorr_nii, self.anat_biascorr_brain_nii,
                        self.anat_biascorr_mask_nii])
        self.anat_biascorr_brain = self.anat_reg_dir / (self.subjroot + '_T1_biascorr_brain.mif')
        self.anat_mask = self.anat_reg_dir / (self.subjroot + '_T1_mask.mif')
        subprocess.run(['mrconvert', self.anat_biascorr_brain_nii, self.anat_biascorr_brain])
        subprocess.run(['mrconvert', self.anat_biascorr_mask_niim, self.anat_mask])

    def gentargetregimgs(self):
        dwi_bzeros = self.anat_reg_dir / (self.subjroot + '_bzeros.mif')
        subprocess.run(['dwiextract', self.dwi_ppd, dwi_bzeros, '-bzero'])
        dwi_bzeros_min0 = self.anat_reg_dir / (self.subjroot + '_bzeros_min0.mif')
        subprocess.run(['mrcalc', dwi_bzeros, '0.0', '-max', dwi_bzeros_min0])
        dwi_meanbzero = self.anat_reg_dir / (self.subjroot + '_meanbzero.mif')
        subprocess.run(['mrmath', dwi_bzeros_min0, 'mean', dwi_meanbzero, '-axis', '3'])
        self.dwi_meanbzero_reg_masked = self.anat_reg_dir / (self.subjroot + '_meanbzero_reg_masked.mif')
        subprocess.run(['mrcalc', '1', dwi_meanbzero, '-div', self.dwi_mask_ppd, '-mult',
                        self.dwi_meanbzero_reg_masked])
        self.dwi_pseudoT1 = self.anat_reg_dir / (self.subjroot + '_dwipseudoT1.mif')
        subprocess.run(['mrhistmatch', 'nonlinear', self.dwi_meanbzero_reg_masked, self.anat_biascorr_brain,
                        self.dwi_pseudoT1, '-mask_input', self.dwi_mask_ppd, '-mask_target', self.anat_mask])
        T1_norm_masked = self.anat_reg_dir / (self.subjroot + '_T1w_reg_masked.mif')
        subprocess.run(['mrcalc', '1', self.anat_biascorr_brain, '-div', self.anat_mask, '-mult', T1_norm_masked])
        self.T1_pseudobzero = self.anat_reg_dir / (self.subjroot + '_T1pseudobzero.mif')
        subprocess.run(['mrhistmatch', 'nonlinear', T1_norm_masked, self.dwi_meanbzero_reg_masked, self.T1_pseudobzero,
                        '-mask_input', self.anat_mask, '-mask_target', self.dwi_mask_ppd])

    def regT1_2_dwi(self):
        rigid_T1_to_pseudoT1 = self.anat_reg_dir / (self.subjroot + '_rigid_T1_to_pseudoT1.txt')
        subprocess.run(['mrregister', self.anat_biascorr_brain, self.dwi_pseudoT1, '-type', 'rigid', '-mask1',
                        self.anat_mask, '-mask2', self.dwi_mask_ppd, '-rigid', rigid_T1_to_pseudoT1])
        rigid_pseudobzero_to_bzero = self.anat_reg_dir / (self.subjroot + '_rigid_pseudobzero_to_bzero.txt')
        subprocess.run(['mrregister', self.T1_pseudobzero, self.dwi_meanbzero_reg_masked, '-type', 'rigid',
                        '-mask1', self.anat_mask, '-mask2', self.dwi_mask_ppd, '-rigid', rigid_pseudobzero_to_bzero])
        rigid_T1_to_dwi = self.anat_reg_dir / (self.subjroot + '_rigid_T1_to_dwi.txt')
        subprocess.run(['transformcalc', rigid_T1_to_pseudoT1, rigid_pseudobzero_to_bzero, 'average', rigid_T1_to_dwi])
        self.anat = self.anat_reg_dir / (self.subjroot + '_T1.mif')
        subprocess.run(['mrconvert', self.anat_nii, self.anat])
        self.anat_registered = self.anat_reg_dir / (self.subjroot + '_T1_reg2dwi.mif')
        subprocess.run(['mrtransform', self.anat, self.anat_registered, '-linear', rigid_T1_to_dwi])
        self.anat_mask_registered = self.anat_reg_dir / (self.subjroot + '_T1_mask_reg2dwi.mif')
        subprocess.run(['mrtransform', self.anat_mask, self.anat_mask_registered, '-linear', rigid_T1_to_dwi,
                        '-template', self.anat_registered, '-interp', 'nearest', '-datatype', 'bit'])

    def main(self, ses_dir):
        self.makedirs()
        self.copyfiles()
        self.skullstrip()
        self.gentargetregimgs()
        self.regT1_2_dwi()


ses_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/sub-011/ses-01')

r = reg2dwi(ses_dir)
r()
