#!/usr/bin/env python3
# coding: utf-8

import os
import shutil
import subprocess
from joblib import parallel_backend, delayed, Parallel
from pathlib import Path

#####################################
# ----PREPREOCESSING PARAMETERS---- #
#####################################

# --Change as needed - last set for BRC YouthPTSD
bidsmaster_dir = Path('/fast_scratch/jdr/PNC/BIDS_Master/')
bidspreproc_dir = Path('/fast_scratch/jdr/BIDS_Preprocessing/')
bidsproc_dir = Path('/fast_scratch/jdr/BIDS_Processed')
# slspec = Path('/Users/jdrussell3/slspec.txt')
# dwelltime = "0.000568"
# totalreadouttime = "0.14484"
error_file = bidspreproc_dir / 'errors.txt'
os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'


class dwipreproc():

    def __init__(self, ses_dir):
        self.ses_dir = ses_dir
        self.subj_dir = ses_dir.parent
        self.subjroot = "_".join([self.subj_dir.name, self.ses_dir.name])
        self.main(self.ses_dir)

    def preproc_prep(self, ses_dir):

        ####################################################################################
        # ----Creating Directory Structures, Copying Files, and Initializing Variables---- #
        ####################################################################################

        # 1. Setting variables
        dwi_dir = ses_dir / 'dwi'
        anat_dir = ses_dir / 'anat'
        sourcedwi = dwi_dir/(self.subjroot + '_acq-AxDTIASSET_dwi.nii')
        sourcebvec = dwi_dir/(self.subjroot + '_acq-AxDTIASSET_dwi.bvec')
        sourcebval = dwi_dir/(self.subjroot + '_acq-AxDTIASSET_dwi.bval')
        sourceanat = anat_dir/(self.subjroot + '_acq-AXFSPGRBRAVONEW_T1w.nii')

        if not sourcedwi.exists():
            next

        # 2. Create directory structure
        preproc_dir = bidspreproc_dir / self.subj_dir.name / ses_dir.name

        self.preprocdwi_dir = preproc_dir / 'dwi'
        # if self.preprocdwi_dir.exists():
        #     shutil.rmtree(self.preprocdwi_dir)
        self.preprocdwi_dir.mkdir(parents=True, exist_ok=True)

        self.preprocanat_dir = preproc_dir / 'anat'
        # if self.preprocanat_dir.exists():
        #     shutil.rmtree(self.preprocanat_dir)
        self.preprocanat_dir.mkdir(parents=True, exist_ok=True)

        # 3. Make directories to hold 'original' unprocessed files

        origdwi_dir = self.preprocdwi_dir / 'original'
        origdwi_dir.mkdir(parents=True, exist_ok=True)

        origanat_dir = self.preprocanat_dir / 'original'
        origanat_dir.mkdir(parents=True, exist_ok=True)

        # 4. Copy source files to 'original' directory
        self.inputdwi = origdwi_dir / (self.subjroot + '_dwi.nii')
        self.inputbvec = origdwi_dir / (self.subjroot + '_dwi.bvec')
        self.inputbval = origdwi_dir / (self.subjroot + '_dwi.bval')
        self.inputanat = origanat_dir / (self.subjroot + '_T1w.nii')
        try:
            shutil.copyfile(sourcedwi, self.inputdwi)
            shutil.copyfile(sourcebvec, self.inputbvec)
            shutil.copyfile(sourcebval, self.inputbval)
            shutil.copyfile(sourceanat, self.inputanat)
        except FileNotFoundError as e:
            with open(error_file, 'w+') as errorfile:
                errorfile.write(self.subjroot + ': Preprocessing failed due to missing file - ' + str(e))
            next

        # 6. Create subject specific log file for preprocessing pipeline in 'preprocessed' directory
        logfile = preproc_dir / (self.subjroot + "_ppd.txt")

        with open(logfile, 'a') as log:

            ###########################################################
            # ----Preparing Log File and Creating Pre-Eddy Folder---- #
            ###########################################################

            # 1. Print the log file header
            startstr1 = "\n\t   BRAVE RESEARCH CENTER\n\t DTI PREPROCESSING PIPELINE\n"
            startstr2 = "\tSUBJECT: " + self.subj_dir.name[-3:] + "   " + \
                "SESSION: " + ses_dir.name[-2:] + "\n"
            log.write(44*"%")
            log.write(startstr1)
            log.write(" " + "_"*43 + " \n\n")
            log.write(startstr2)
            log.write(44*"%" + "\n\n")

            # 2. Convert to MIF format
            log.write("#----Converting to .MIF format----#\n\n")
            log.flush()
            log.flush()

    def denoise(self):
        self.dwi_denoised = self.preprocdwi_dir / (self.subjroot + '_denoised.nii')
        subprocess.run(['dwidenoise', '-force', self.inputdwi, self.dwi_denoised])

    def degibbs(self):
        self.dwi_degibbs = self.preprocdwi_dir / (self.subjroot + '_degibbs.nii')
        subprocess.run(['mrdegibbs', '-force', self.dwi_denoised, self.dwi_degibbs])

    def regrid(self):
        self.dwi_regrid = self.preprocdwi_dir / (self.subjroot + '_regrid.nii')
        subprocess.run(['mrgrid', '-info', '-force', self.dwi_degibbs, 'regrid', self.dwi_regrid,
                        '-voxel', '1'])

    def synb0(self):
        synb0_dir = self.preprocdwi_dir / 'synb0'
        if synb0_dir.exists():
            shutil.rmtree(synb0_dir)
        synb0_dir.mkdir(exist_ok=True)

        self.synb0_INPUT_dir = synb0_dir / 'INPUTS'
        if self.synb0_INPUT_dir.exists():
            shutil.rmtree(self.synb0_INPUT_dir)
        self.synb0_INPUT_dir.mkdir(exist_ok=True)

        self.synb0_OUTPUT_dir = synb0_dir / 'OUTPUTS'
        if self.synb0_OUTPUT_dir.exists():
            shutil.rmtree(self.synb0_OUTPUT_dir)
        self.synb0_OUTPUT_dir.mkdir(exist_ok=True)

        all_b0 = self.synb0_INPUT_dir / 'all_b0.nii'
        subprocess.run(['dwiextract', '-force', '-fslgrad', self.inputbvec, self.inputbval, self.dwi_regrid, all_b0])

        syn_b0 = self.synb0_INPUT_dir / 'b0.nii.gz'
        subprocess.run(['mrmath', '-force', all_b0, 'mean', syn_b0, '-axis', '3'])

        synb0_T1 = self.synb0_INPUT_dir / 'T1.nii.gz'
        shutil.copy(self.inputanat, synb0_T1)

        self.synb0_topup_acqc = self.synb0_INPUT_dir / 'acqparams.txt'
        with open(self.synb0_topup_acqc, 'w') as acqfile:
            acqfile.write("0 1 0 0.14484" + '\n' + "0 1 0 0")

        subprocess.run(['docker', 'run', '--rm', '-v', str(self.synb0_INPUT_dir)+str(':/INPUTS/'), '-v',
                        str(self.synb0_OUTPUT_dir)+str(':/OUTPUTS/'),
                        '-v', '/fast_scratch/jdr/dwiproc_test/ses-01/license.txt:/extra/freesurfer/license.txt',
                        '--user', '57059:20', 'hansencb/synb0'])

    def eddy(self):

        # REMOVE AFTER TESTING #
        synb0_dir = self.preprocdwi_dir / 'synb0'
        self.synb0_INPUT_dir = synb0_dir / 'INPUTS'
        self.synb0_OUTPUT_dir = synb0_dir / 'OUTPUTS'
        self.synb0_topup_acqc = self.synb0_INPUT_dir / 'acqparams.txt'
        ###########################

        eddy_dir = self.preprocdwi_dir / 'eddy'
        eddy_dir.mkdir(exist_ok=True)

        # Create dwi mask
        dwi_mask = eddy_dir / (self.subjroot + '_mask.nii')
        subprocess.run(['dwi2mask', '-force', '-fslgrad', self.inputbvec, self.inputbval, self.inputdwi, dwi_mask])

        # Generating volume index file
        eddy_index = eddy_dir / 'eddy_index.txt'
        with open(eddy_index, 'w') as indexfile:
            getnvols = subprocess.Popen(
                ['fslval', self.inputdwi, 'dim4'], stdout=subprocess.PIPE)
            nvols = getnvols.stdout.read()
            for i in range(int(nvols)):
                indexfile.write("1 ")

        # Run eddy
        eddy_basename = str(eddy_dir / (self.subjroot + '_dwi_eddy'))
        subprocess.run(['eddy_cuda9.1', '--imain='+str(self.inputdwi), '--mask='+str(dwi_mask),
                        '--acqp='+str(self.synb0_topup_acqc), '--index='+str(eddy_index),
                        '--bvecs='+str(self.inputbvec), '--bvals='+str(self.inputbval),
                        '--topup='+str(self.synb0_OUTPUT_dir)+('/topup'),
                        '--out='+eddy_basename, '--repol', '--residuals', '--slm=linear', '--very_verbose'])
        self.dwi_eddycorr = eddy_dir / (self.subjroot + '_dwi_eddy.nii.gz')

    def biascorrection(self):
        self.biascorr = self.preprocdwi_dir / (self.subjroot + '_biascorr.nii')
        subprocess.run(['dwibiascorrect', '-info', '-force', 'ants', self.dwi_eddycorr,
                        self.biascorr, '-scratch', '/tmp'])

    def main(self, ses_dir):
        self.preproc_prep(ses_dir)
        self.denoise()
        self.degibbs()
        self.regrid()
        self.synb0()
        self.eddy()


ses_dirs = lambda: (ses_dir for ses_dir in bidsmaster_dir.glob('*/ses-01')  # noqa: E731
                    if ses_dir.parent.name == 'sub-001')


def container(ses_dir):
    c = dwipreproc(ses_dir)  # noqa: F841


with parallel_backend("loky", inner_max_num_threads=1):
    results = Parallel(n_jobs=1, verbose=1)(
        delayed(container)(ses_dir) for ses_dir in sorted(ses_dirs()))
