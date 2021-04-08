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

        # Apply the anatomical mask to the bias corrected anatomical to remove all non-brain data
        subprocess.run(['mrcalc',  '-force', '1', self.anat_biascorr_brain, '-div', self.anat_mask, '-mult',
                        self.anat_biascorr_mask_nii])

    # Extracting the mean b0 image we'll register/warp the anatomical to fit
    def gentargetregimgs(self):

        # Extract the b0 volumes, create an average, and mask it using the pre-existing brain mask
        # we created during preprocessing
        dwi_bzeros = self.anat_reg_dir / (self.subjroot + '_bzeros.mif')
        subprocess.run(['dwiextract',  '-force', self.dwi_ppd, dwi_bzeros, '-bzero'])
        dwi_bzeros_min0 = self.anat_reg_dir / (self.subjroot + '_bzeros_min0.mif')
        subprocess.run(['mrcalc',  '-force', dwi_bzeros, '0.0', '-max', dwi_bzeros_min0])
        dwi_meanbzero = self.anat_reg_dir / (self.subjroot + '_meanbzero.mif')
        subprocess.run(['mrmath',  '-force', dwi_bzeros_min0, 'mean', dwi_meanbzero, '-axis', '3'])
        self.dwi_meanbzero_masked = self.anat_reg_dir / (self.subjroot + '_meanbzero_masked.mif')
        subprocess.run(['mrcalc', '-force', dwi_meanbzero, self.dwi_mask_ppd, '-mult',
                        self.dwi_meanbzero_masked])

        # Create 'pseudo' versions of each image to be aligned, wherein 'pseudo' means that the contrast
        # distribution matches the other image

        # Create a 'pseudo' T1 - the masked DWI image with its contrast matched to the T1
        self.dwi_pseudoT1 = self.anat_reg_dir / (self.subjroot + '_dwipseudoT1.mif')
        subprocess.run(['mrhistmatch', '-force', 'nonlinear', self.dwi_meanbzero_masked, self.anat_biascorr_brain,
                        self.dwi_pseudoT1, '-mask_input', self.dwi_mask_ppd, '-mask_target', self.anat_mask])

        # Create a 'pseudo' DWI - the T1 image with its contrast matched to the T1
        self.T1_pseudobzero = self.anat_reg_dir / (self.subjroot + '_T1pseudobzero.mif')
        subprocess.run(['mrhistmatch', '-force', 'nonlinear', self.anat_mask, self.dwi_meanbzero_masked,
                        self.T1_pseudobzero, '-mask_input', self.anat_mask, '-mask_target', self.dwi_mask_ppd])

    def regT1_2_dwi(self):

        # Register T1 to pseudoT1 and output linear matrix
        rigid_T1_to_pseudoT1 = self.anat_reg_dir / (self.subjroot + '_rigid_T1_to_pseudoT1.txt')
        subprocess.run(['mrregister', '-force', self.anat_biascorr_brain, self.dwi_pseudoT1, '-type', 'rigid', '-mask1',
                        self.anat_mask, '-mask2', self.dwi_mask_ppd, '-rigid', rigid_T1_to_pseudoT1])

        # Register pseudoDWIb0 to DWIb0 and output linear matrix
        rigid_pseudobzero_to_bzero = self.anat_reg_dir / (self.subjroot + '_rigid_pseudobzero_to_bzero.txt')
        subprocess.run(['mrregister', '-force', self.T1_pseudobzero, self.dwi_meanbzero_masked, '-type', 'rigid',
                        '-mask1', self.anat_mask, '-mask2', self.dwi_mask_ppd, '-rigid', rigid_pseudobzero_to_bzero])

        # Average the two linear matrices using transformcalc to create a T1 to DWI transform matrix
        rigid_T1_to_dwi = self.anat_reg_dir / (self.subjroot + '_rigid_T1_to_dwi.txt')
        subprocess.run(['transformcalc', '-force', rigid_T1_to_pseudoT1, rigid_pseudobzero_to_bzero, 'average',
                        rigid_T1_to_dwi])
        self.anat = self.anat_reg_dir / (self.subjroot + '_T1.mif')

        # Convert the original anat file back to .MIF
        subprocess.run(['mrconvert', '-force', self.anat_nii, self.anat])

        # Transform the anatomical to the DTI using the combined matrix
        self.anat_registered = self.anat_reg_dir / (self.subjroot + '_T1_reg2dwi.mif')
        subprocess.run(['mrtransform', '-force', self.anat, self.anat_registered, '-linear', rigid_T1_to_dwi])

        # Transform the anatomical mask to the DTI using the combined matrix
        self.anat_mask_registered = self.anat_reg_dir / (self.subjroot + '_T1_mask_reg2dwi.mif')
        subprocess.run(['mrtransform', '-force', self.anat_mask, self.anat_mask_registered, '-linear', rigid_T1_to_dwi,
                        '-template', self.anat_registered, '-interp', 'nearest', '-datatype', 'bit'])

    def main(self, ses_dir):
        self.makedirs()
        self.copyfiles()
        self.skullstrip()
        self.gentargetregimgs()
        self.regT1_2_dwi()


ses_dirs = lambda: (ses_dir for ses_dir in sorted(bidsproc_dir.glob('*/ses-0*'))  # noqa: E731
                    if Path(ses_dir / 'dwi').exists() and Path(ses_dir / 'anat').exists() and ses_dir.parent.name == 'sub-003')


def anat2dtireg_container(ses_dir):
    c = crosssec_anat2dtireg(ses_dir)


with parallel_backend("loky", inner_max_num_threads=nCoresPerJob):
    results = Parallel(n_jobs=nJobs, verbose=1)(
        delayed(anat2dtireg_container)(ses_dir) for ses_dir in sorted(ses_dirs()))
