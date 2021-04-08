#!/usr/bin/env python3
# coding: utf-8

import string
import os
import shutil
import subprocess
import sys
import time
import argparse
from pathlib import Path
from multiprocessing import Pool
from joblib import parallel_backend, delayed, Parallel
from random import randint

# Ollinger convention:
# Only pass arguments to subfunctions reused throughout the code (never to main functions, e.g. get_raw_scans)


class dwipreproc:

    def __init__(self):
        if __name__ == '__main__':
            self.parse_args()

    def processCommandLine(self):

        # Check if BIDS Output Path
        self.BIDSinput_dir = Path(self.args.BIDSinput_dir)
        self.scratch_dir = Path(self.args.scratch_dir)
        self.BIDSoutput_dir = Path(self.args.BIDSoutput_dir)
        self.dwelltime = self.args.dwelltime
        self.trt = self.args.totalreadouttime

        if not self.BIDSinput_dir.exists():
            sys.stderr.write("ERROR: BIDS formatted directory does not exist at path: %s\n" % self.BIDSinput_dir)
            sys.exit(1)

        self.scratch_dir.mkdir(exist_ok=True)

        if not self.BIDSoutput_dir.exists():
            self.BIDSoutput_dir.mkdir()

    def parse_args(self):

        parser = argparse.ArgumentParser(prog="preprocessing_v7",
                                         usage="preprocessing_v7 [options] <BIDS Input Path> <Scratch Path> <BIDS Output Path> \
                                         <DwellTime (sec)> <TotalReadoutTime (sec)>",
                                         description="")
        parser.add_argument("BIDS-Input-Path", metavar="BIDS-Input-Path", help="Root of the BIDS formatted \
            directory containing DTI scans to be pre-processed.")
        parser.add_argument("Scratch-Path", metavar="Scratch-Path", help="Path of a scratch directory \
            where preprocessing operations will occur.")
        parser.add_argument("BIDS-Output-Path", metavar="BIDS-Output-Path", help="Path where the BIDS \
            formatted output directories will be stored. If the BIDS directory structure does not exist, it will be \
            created here.")
        parser.add_argument("DwellTime", help="Dwell time for scans to be preprocessed (in seconds; e.g. 0.000568")
        parser.add_argument("TotalReadoutTime", help="Total readout time for scans to be preprocessed\
            (in seconds; e.g., 0.14484")
        self.args = parser.parse_args()

    def get_raw_scans(self):

        sourcedwi = ses_dir / 'dwi' / (subjroot + '_acq-*_dwi.nii')
        sourcebvec = ses_dir / 'dwi' / (subjroot + '_acq-*_dwi.bvec')
        sourcebval = ses_dir / 'dwi' / (subjroot + '_acq-*_dwi.bval')

        sourcefmap_ph = ses_dir / 'fmap' / (subjroot + '_acq-RealFieldmapDTIHz_fmap.nii')
        sourcefmap_mag = ses_dir / 'fmap' / (subjroot + '_acq-FieldmapDTI_magnitude1.nii')

        scratch_dir = ARGS.scratch
        if not scratch_dir.exists():
            scratch_dir.mkdir()

        self.scratchdwi_dir = self.scratch_dir / subj_dir.name / ses_dir.name / 'dwi'
        if scratchdwi_dir.exists():
            shutil.rmtree(scratchdwi_dir)
        scratchdwi_dir.mkdir(parents=True)

        orig_dir = scratchdwi_dir / 'original'
        orig_dir.mkdir()

        self.rawdwi = orig_dir / (subjroot + '_dwi.nii')
        self.rawbvec = orig_dir / (subjroot + '_dwi.bvec')
        self.rawbval = orig_dir / (subjroot + '_dwi.bval')
        self.rawfmap_hz = orig_dir / (subjroot + '_fmap_hz.nii')
        self.rawfmap_mag = orig_dir / (subjroot + '_fmap_mag.nii')
        shutil.copyfile(sourcedwi, self.rawdwi)
        shutil.copyfile(sourcebvec, self.rawbvec)
        shutil.copyfile(sourcebval, self.rawbval)
        shutil.copyfile(sourcefmap_ph, self.rawfmap_hz)
        shutil.copyfile(sourcefmap_mag, self.rawfmap_mag)

    def regfmap2dti(self):
        pre_eddy_dir = self.scratchdwi_dir / 'pre-eddy'
        pre_eddy_dir.mkdir()

        # 1. Copy the fieldmap (phase difference in Hz) and magnitude images to processing directory
        native_fmap_hz = pre_eddy_dir / (self.subjroot + '_native_fmap_hz.nii')
        native_fmap_mag = pre_eddy_dir / (self.subjroot + '_native_fmap_mag.nii')
        shutil.copy(self.rawfmap_hz, native_fmap_hz)
        shutil.copy(self.rawfmap_mag, native_fmap_mag)

        # 2. Create a mean b0 image, then skull strip it and save a binary mask file
        native_b0 = pre_eddy_dir / (self.subjroot + '_native_b0.nii')
        native_mnb0 = pre_eddy_dir / (self.subjroot + '_native_b0_brain.nii')
        native_mnb0_brain = pre_eddy_dir / (self.subjroot + '_native_mnb0_brain.nii.gz')
        self.native_mnb0_brain_mask = pre_eddy_dir / (self.subjroot + '_native_mnb0_brain_mask.nii.gz')
        #Need to change line below to actually read the number of b0 volumes
        subprocess.run(['fslroi', self.rawdwi, native_b0, '0', '7'])
        subprocess.run(['fslmaths', native_b0, '-Tmean', native_mnb0])
        subprocess.run(['bet2', native_mnb0, native_mnb0_brain, '-m', '-v'])

        # 3. Skull strip the magnitude image and save a binary mask file
        native_fmap_mag_brain = pre_eddy_dir / (self.subjroot + '_native_fmap_mag_brain.nii.gz')
        native_fmap_mag_brain_mask = pre_eddy_dir / (self.subjroot + '_native_fmap_mag_brain_mask.nii.gz')
        subprocess.run(['bet2', native_fmap_mag, native_fmap_mag_brain, '-m', '-v', '-f', '0.3'])

        # 4. Mask the fieldmap using the binary mask of the magnitude image
        native_fmap_ph_brain = pre_eddy_dir / (self.subjroot + '_native_fmap_ph_brain.nii.gz')
        subprocess.run(['fslmaths', native_fmap_ph, '-mas',
                        native_fmap_mag_brain_mask, native_fmap_ph_brain])

        # 5. Smooth the fieldmap
        native_fmap_ph_brain_s4 = pre_eddy_dir / (self.subjroot + '_native_fmap_ph_brain_s4.nii.gz')
        subprocess.run(['fugue', '-v', f'--loadfmap={native_fmap_ph_brain}', '-s', '4',
                        f'--savefmap={native_fmap_ph_brain_s4}'], stdout=log, stderr=subprocess.STDOUT)

        # 6. Warp the magnitude image
        native_fmap_mag_brain_warp = pre_eddy_dir / (self.subjroot + '_native_fmap_mag_brain_warp.nii.gz')
        subprocess.run(['fugue', '-v', '-i', native_fmap_mag_brain, '--unwarpdir=y', f'--dwell={self.dwelltime}',
                        f'--loadfmap={native_fmap_ph_brain_s4}', '-w', native_fmap_mag_brain_warp])

        # 7. Linearly register the warped magnitude image to the mean B0 image and save the affine matrix
        fmap_mag_brain_warp_reg_2_mnb0_brain = pre_eddy_dir / (self.subjroot + '_fmap_mag_brain_warp_reg_2_mnb0_brain.nii.gz')
        fieldmap_2_mnb0_brain_mat = pre_eddy_dir / (self.subjroot + '_fieldmap_2_mnb0_brain.mat')
        subprocess.run(['flirt', '-v', '-in', native_fmap_mag_brain_warp, '-ref', native_mnb0_brain, '-out',
                        fmap_mag_brain_warp_reg_2_mnb0_brain, '-omat', fieldmap_2_mnb0_brain_mat], stdout=log, stderr=subprocess.STDOUT)

        # 8. Linearly register the smoothed fieldmap to the full DTI set using the warped_magnitude-2-meanB0 matrix as a starting point.
        self.fmap_ph_brain_s4_reg_2_mnb0_brain = pre_eddy_dir / \
            (self.subjroot + '_fmap_ph_brain_s4_reg_2_mnb0_brain.nii.gz')
        subprocess.run(['flirt', '-v', '-in', native_fmap_ph_brain_s4, '-ref', native_mnb0_brain, '-applyxfm', '-init',
                        fieldmap_2_mnb0_brain_mat, '-out', self.fmap_ph_brain_s4_reg_2_mnb0_brain], stdout=log, stderr=subprocess.STDOUT)

    def run_eddy(self):

        eddyout_dir = scratchdwi_dir / 'eddy'
        eddyout_dir.mkdir()

        slspec = Path('/Users/jdrussell3/slspec.txt')

        # Generating acquisition parameters file for eddy - Need to verify this
        # Also would be nice to not have to hard code these parameters
        eddy_acqp = eddyout_dir / 'eddy_acqp.txt' 
        with open(eddy_acqp, 'w') as acqfile:
            acqfile.write("0 1 0 0.14484")

        # Generating eddy index file
        eddy_index = eddyout_dir / 'eddy_index.txt'
        with open(eddy_index, 'w') as indexfile:
            getnvols = subprocess.Popen(
                ['fslval', self.rawdwi, 'dim4'], stdout=subprocess.PIPE)
            nvols = getnvols.stdout.read()
            for i in range(int(nvols)):
                indexfile.write("1 ")
        
        # Copying the registered fieldmap to the eddy folder, then
        # creating a variable to hold the full path, without the suffix (eddy doesn't like it)
        fieldmap2eddy = self.inputfmap_hz.parent / self.inputfmap_hz.split('.')[0]

        # Calling eddy
        subprocess.run(['time', 'eddy_cuda9.1', 
                                '--acqp='+str(eddy_acqp), 
                                '--bvecs='+str(self.inputbvec), 
                                '--bvals='+str(self.inputbval), 
                                '--cnr_maps',
                                '--estimate_move_by_susceptibility', 
                                '--field='+str(fieldmap2eddy), 
                                '--fwhm=10,6,4,2,0,0,0,0', 
                                '--imain='+str(self.inputdwi), 
                                '--index='+str(eddy_index),
                                '--mask='+str(self.native_mnb0_brain_mask), 
                                '--mporder=13', 
                                '--niter=8', 
                                '--out='+str(eddyout_dir / self.subjroot),
                                '--repol', 
                                '--residuals', 
                                '--s2v_niter=8', 
                                '--slm=linear', 
                                '--slspec='+str(slspec), 
                                '--very_verbose'], 
                        stdout=sys.stdout, stderr=sys.stderr)
        
        #Add eddy quad 

    def denoise(self, inputdwi):
        # Denoise
        outputdwi = self.inputdwi.parent / (self.inputdwi.name.split('.')[0] + '_den.mif')
        subprocess.run(['dwidenoise', '-info', '-force', self.inputdwi, outputdwi])
        return outputdwi

    def degibbs(self, inputdwi):
        # Degibbs
        outputdwi = inputdwi.parent / (inputdwi.name.split('.')[0] + '_deg.mif')
        subprocess.run(['mrdegibbs', '-info', '-force', inputdwi, outputdwi])
        return outputdwi

    def preproc_scans():
        
        for subj_dir in bidsmaster_dir.iterdir() if subj_dir.is_dir():
            self.get_raw_scans
            
            #Add commands here
            #Add possible exceptions here

if __name__ == '__main__':
    preproc_scans()
