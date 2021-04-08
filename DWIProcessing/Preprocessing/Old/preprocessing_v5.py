#!/usr/bin/env python3
# coding: utf-8

import string
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from multiprocessing import Pool
from joblib import parallel_backend, delayed, Parallel
from random import randint

try:
    mrtrixbinpath = str(Path(shutil.which("mrconvert")).parent)
    mrtrixlibpath = str(Path(shutil.which("mrconvert")).parents[1] / 'lib')
    if mrtrixbinpath not in sys.path:
        sys.path.append(mrtrixbinpath)
    if mrtrixlibpath not in sys.path:
        sys.path.append(mrtrixlibpath)
    from mrtrix3 import app, fsl, image, path, run 
except (TypeError, ImportError) as e:
    print("\nERROR: Cannot find the MRtrix3/lib directory. Exiting...\n\n")
    sys.exit(1)


###################################
#----PREPREOCESSING PARAMETERS----#
###################################

#--Change as needed - last set for BRC YouthPTSD
bidsmaster_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_master/')
bidspreproc_dir = Path('/scratch/jdrussell3/bidspreproc/')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
eddy_options = "--verbose --slm=linear --repol --cnr_maps --residuals"
dwelltime = "0.000568"
totalreadouttime = "0.14484"

def dwi_corr(subj_dir):
    
    ses_dirs = (ses_dir for ses_dir in subj_dir.iterdir() if subj_dir.is_dir())

    for ses_dir in sorted(ses_dirs):
        ##################################################################################
        #----Creating Directory Structures, Copying Files, and Initializing Variables----#
        ##################################################################################
        
        #1. Setting variables
        subjroot = "_".join([subj_dir.name, ses_dir.name])
        dwi_dir = ses_dir / 'dwi'
        fmap_dir = ses_dir / 'fmap'
        sourcedwi = dwi_dir/(subjroot + '_acq-AxDTIASSET_dwi.nii')
        sourcebvec = dwi_dir/(subjroot + '_acq-AxDTIASSET_dwi.bvec')
        sourcebval = dwi_dir/(subjroot + '_acq-AxDTIASSET_dwi.bval')
        sourcefmap_rads = fmap_dir/(subjroot + '_acq-RealFieldmapDTIrads_fmap.nii')
        sourcefmap_mag = fmap_dir/(subjroot + '_acq-FieldmapDTI_magnitude1.nii')

        if not sourcedwi.exists():
            next

        #2. Create directory structure
        preprocdwi_dir = bidspreproc_dir / subj_dir.name / ses_dir.name / 'dwi' 
        if preprocdwi_dir.exists():
            try:
                shutil.rmtree(preprocdwi_dir)
            except:
                print('Could not delete old preprocessed directory.')
                sys.exit(1)
        
        #3. Make directory to hold 'original' unprocessed files
        orig_dir = preprocdwi_dir / 'original'
        orig_dir.mkdir(parents=True, exist_ok=True)

        #4. Make directory to hold preprocessing files
        preproc_dir = preprocdwi_dir / 'preprocessed'
        preproc_dir.mkdir(parents=True, exist_ok=True)
       
        #5. Copy source files to 'original' directory
        inputdwi = orig_dir / (subjroot + '_dwi.nii')
        inputbvec = orig_dir / (subjroot + '_dwi.bvec')
        inputbval = orig_dir / (subjroot + '_dwi.bval')
        inputfmap_rads = orig_dir / (subjroot + '_fmap_rads.nii')
        inputfmap_mag = orig_dir / (subjroot + '_fmap_mag.nii')
        shutil.copyfile(sourcedwi, inputdwi)
        shutil.copyfile(sourcebvec, inputbvec)
        shutil.copyfile(sourcebval, inputbval)
        shutil.copyfile(sourcefmap_rads, inputfmap_rads)
        shutil.copyfile(sourcefmap_mag, inputfmap_mag)

        #6. Create subject specific log file for preprocessing pipeline in 'preprocessed' directory
        logfile = preproc_dir / (subjroot + "_ppd.txt")
            
        with open (logfile, 'a') as log:

            #########################################################
            #----Preparing Log File and Creating Pre-Eddy Folder----#
            #########################################################

            #1. Print the log file header
            startstr1 = "\n\t   BRAVE RESEARCH CENTER\n\t DTI PREPROCESSING PIPELINE\n"
            startstr2 = "\tSUBJECT: " + subj_dir.name[-3:] + "   " + "SESSION: " + ses_dir.name[-2:] + "\n\n"        
            log.write(44*"%")
            log.write(startstr1)
            log.write(" " + "_"*43 + " \n\n")
            log.write(startstr2)
            log.write(44*"%" + "\n\n")

            #2. Within 'preprocessed', make directory to hold files created BEFORE eddy correction is performed.
            pre_eddy_dir = preproc_dir / 'pre-eddy'
            pre_eddy_dir.mkdir()

            ############################################
            #----Removing Gibbs Rings and Denoising----#
            ############################################

            log.write("#"*44 + "\n" + "#----Removing Gibbs Rings and Denoising----#\n" + "#"*44)
            log.flush()

            #1. Convert to MIF format
            log.write("\n\n#----Converting to .MIF format----#\n\n"); log.flush()
            log.flush()
            dwi_raw = pre_eddy_dir/(subjroot + '_dwi.mif')
            subprocess.run(['mrconvert', '-info', '-force', '-fslgrad', inputbvec, inputbval, inputdwi, dwi_raw], stdout=log, stderr=subprocess.STDOUT)

            #2. Denoise #https://www.ncbi.nlm.nih.gov/pubmed/27523449
            #!! Should change...denoising should be run AFTER eddy per: https://www.jiscmail.ac.uk/cgi-bin/webadmin?A2=ind1901&L=FSL&O=D&P=169883 
            log.write("\n#----Denoising (MRtrix3 dwidenoise)----#\n\n"); log.flush()
            dwi_den = pre_eddy_dir/(subjroot + '_dwi_den.mif')
            subprocess.run(['dwidenoise', '-info', '-force', dwi_raw, dwi_den], stdout=log, stderr=subprocess.STDOUT)

            #3. Remove Gibbs rings #https://onlinelibrary.wiley.com/doi/full/10.1002/mrm.26054
            log.write("\n#----Removing Gibbs Rings (MRtrix3 mrdegibbs)----#\n\n"); log.flush()
            dwi_den_deg = pre_eddy_dir/(subjroot + '_dwi_den_deg.mif')
            subprocess.run(['mrdegibbs', '-info', '-force', dwi_den, dwi_den_deg], stdout=log, stderr=subprocess.STDOUT)

            #4. Within 'preprocessed', make directory to hold files created AFTER eddy correction is performed.
            post_eddy_dir = preproc_dir / 'post-eddy'
            post_eddy_dir.mkdir()

            #################################
            #----Eddy Current Correction----#
            #################################
            #https://www.sciencedirect.com/science/article/pii/S1053811915009209
            #dwifslpreproc: https://mrtrix.readthedocs.io/en/dev/dwi_preprocessing/dwifslpreproc.html

            #1. Sleep for a random amount of time to avoid collisions when loading processes into GPU (???)
            time.sleep(randint(1, 90))

            #2. Eddy Current Correction # - MRtrix automatically includes rotated bvecs in output file
            log.write("\n" + "#"*57 + "\n" + "#----Eddy Current Correction (MRtrix3 dwifslpreproc)----#\n" + "#"*57 + "\n\n"); log.flush()
            eddyout_dir = preproc_dir/'eddy' #dwifslpreproc kicks back an error if this isn't a string (e.g., PosixPath)
            dwi_den_deg_preproc = eddyout_dir/(subjroot + '_dwi_den_deg_preproc.nii.gz')
            bvec_posteddy = eddyout_dir/(subjroot + '_bvec_preproc.bvec')
            bval_posteddy = eddyout_dir/(subjroot + '_bval_preproc.bval')

            subprocess.run(['dwifslpreproc', '-info', '-force', dwi_den_deg, dwi_den_deg_preproc, '-pe_dir', 'AP', '-rpe_none', '-scratch', '/tmp', \
                 '-eddy_options', eddy_options, '-eddyqc_all', eddyout_dir, '-readout_time', totalreadouttime, '-export_grad_fsl', \
                 bvec_posteddy, bval_posteddy])
            # eddyout, eddyerr = run.command(['dwifslpreproc', '-info', '-force', str(dwi_den_deg), str(dwi_den_deg_preproc), '-pe_dir', 'AP', '-rpe_none', '-scratch', '/tmp', # pylint: disable=unused-variable
            #     '-eddy_options', eddy_options, '-eddyqc_all', str(eddyout_dir), '-readout_time', totalreadouttime, '-export_grad_fsl', \
            #     str(bvec_posteddy), str(bval_posteddy)], show=True) 
            #log.write(eddyout); log.flush()

            ###################################
            #----EPI Distortion Correction----#
            ###################################
            #https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4819327/pdf/nihms767022.pdf

            log.write("#"*35 + "\n" + "#----EPI Distortion Correction----#\n" + "#"*35 + "\n\n"); log.flush()

            #-Within 'post-eddy', make directory to hold files for EPI distortion correction
            epi_corr_dir = post_eddy_dir / '1-EPI_Correction'
            epi_corr_dir.mkdir()

            #----Prepare Fieldmap and Magnitude Images----#
            
            #1. Copy the fieldmap (phase difference in radians) and magnitude images to processing directory
            log.write("#----Renaming input fieldmap (rads) and magnitude scans as 'native' space----#\n\n"); log.flush()
            native_fmap_ph = epi_corr_dir/(subjroot + '_native_fmap_ph.nii')
            native_fmap_mag = epi_corr_dir/(subjroot + '_native_fmap_mag.nii')
            shutil.copy(inputfmap_rads, native_fmap_ph)
            shutil.copy(inputfmap_mag, native_fmap_mag)
            
            #2. Create a mean b0 image, then skull strip it and save a binary mask file
            native_b0 = epi_corr_dir/(subjroot + '_native_b0.nii')
            native_mnb0 = epi_corr_dir/(subjroot + '_native_b0_brain.nii')
            native_mnb0_brain = epi_corr_dir/(subjroot + '_native_mnb0_brain.nii.gz')
            #native_mnb0_brain_mask = post_eddy_dir/(subjroot + '_native_mnb0_brain_mask.nii.gz') 
            log.write("\n#----Creating a mean b0 image----#\n\n"); log.flush()
            subprocess.run(['fslroi', inputdwi, native_b0, '0', '7'], stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(['fslmaths', native_b0, '-Tmean', native_mnb0], stdout=log, stderr=subprocess.STDOUT)
            log.write("\n#----Skull-stripping the mean b0 (FSL bet2)----#\n\n"); log.flush()
            subprocess.run(['bet2', native_mnb0, native_mnb0_brain, '-m', '-v'], stdout=log, stderr=subprocess.STDOUT)
            
            #3. Skull strip the magnitude image and save a binary mask file
            native_fmap_mag_brain = epi_corr_dir/(subjroot + '_native_fmap_mag_brain.nii.gz')
            native_fmap_mag_brain_mask = epi_corr_dir/(subjroot + '_native_fmap_mag_brain_mask.nii.gz')
            log.write("\n#----Skull-striping the magnitude image and saving a mask (FSL bet2)----#\n\n"); log.flush()
            subprocess.run(['bet2', native_fmap_mag, native_fmap_mag_brain, '-m', '-v', '-f', '0.3'], stdout=log, stderr=subprocess.STDOUT)

            #4. Mask the fieldmap using the binary mask of the magnitude image
            native_fmap_ph_brain = epi_corr_dir/(subjroot + '_native_fmap_ph_brain.nii.gz')
            log.write("\n#----Masking the fieldmap using the binary mask of the magnitude image----#\n\n"); log.flush()
            subprocess.run(['fslmaths', native_fmap_ph, '-mas', native_fmap_mag_brain_mask, native_fmap_ph_brain], \
                stdout=log, stderr=subprocess.STDOUT)

            #5. Smooth the fieldmap
            native_fmap_ph_brain_s4 = epi_corr_dir/(subjroot + '_native_fmap_ph_brain_s4.nii.gz')
            log.write("\n#----Smoothing the fieldmap (FSL FUGUE; -s 4)----#\n\n"); log.flush()
            subprocess.run(['fugue', '-v', f'--loadfmap={native_fmap_ph_brain}', '-s', '4', f'--savefmap={native_fmap_ph_brain_s4}'], stdout=log, stderr=subprocess.STDOUT)
            
            #6. Warp the magnitude image
            native_fmap_mag_brain_warp = epi_corr_dir/(subjroot + '_native_fmap_mag_brain_warp.nii.gz')
            log.write("\n#----Warping the magnitude image to the smoothed fieldmap (FSL FUGUE)----#\n\n"); log.flush()
            subprocess.run(['fugue', '-v', '-i', native_fmap_mag_brain, '--unwarpdir=y', f'--dwell={dwelltime}', \
                f'--loadfmap={native_fmap_ph_brain_s4}', '-w', native_fmap_mag_brain_warp], stdout=log, stderr=subprocess.STDOUT)
            
            #7. Register the warped magnitude image to the mean B0 image and save the affine matrix
            fmap_mag_brain_warp_reg_2_mnb0_brain = epi_corr_dir/(subjroot + '_fmap_mag_brain_warp_reg_2_mnb0_brain.nii.gz')
            fieldmap_2_mnb0_brain_mat = epi_corr_dir/(subjroot + '_fieldmap_2_mnb0_brain.mat')
            log.write("\n#----Computing the transformation matrix to register the warped magnitude to the mean B0 (FSL FLIRT)----#\n\n"); log.flush()
            subprocess.run(['flirt', '-v', '-in', native_fmap_mag_brain_warp, '-ref', native_mnb0_brain, '-out', \
                fmap_mag_brain_warp_reg_2_mnb0_brain, '-omat', fieldmap_2_mnb0_brain_mat], stdout=log, stderr=subprocess.STDOUT)

            #8. Use the warped_magnitude-2-meanB0 matrix to register the smoothed fieldmap to the full DTI set.
            fmap_ph_brain_s4_reg_2_mnb0_brain = epi_corr_dir/(subjroot + '_fmap_ph_brain_s4_reg_2_mnb0_brain.nii.gz')
            log.write("\n#----Using the warped_mag2meanb0 matrix to register the smoothed fieldmap to the full DTI set (FSL FLIRT)----#\n\n"); log.flush()
            subprocess.run(['flirt', '-v', '-in', native_fmap_ph_brain_s4, '-ref', native_mnb0_brain, '-applyxfm', '-init', \
                fieldmap_2_mnb0_brain_mat, '-out', fmap_ph_brain_s4_reg_2_mnb0_brain], stdout=log, stderr=subprocess.STDOUT)
            
            #9. Warp the DTI volumes using the newly registered fieldmap.
            dwi_den_deg_preproc_warp_niigz = epi_corr_dir/(subjroot + '_dwi_den_deg_preproc_warp.nii.gz')
            log.write("#----Warping the DTI volumes using the newly registered fieldmap (FSL FUGUE)----#\n\n"); log.flush()
            subprocess.run(['fugue', '-v', '-i', dwi_den_deg_preproc, '--icorr', '--unwarpdir=y', f'--dwell={dwelltime}', 
                f'--loadfmap={fmap_ph_brain_s4_reg_2_mnb0_brain}', '-u', dwi_den_deg_preproc_warp_niigz], stdout=log, stderr=subprocess.STDOUT)
            
            ###############################################
            #----Bias Field (B1) Distortion Correction----#
            ###############################################
            #https://www.ncbi.nlm.nih.gov/pubmed/20378467

            log.write("\n\n" + "#"*47 + "\n" + "#----Bias Field (B1) Distortion Correction----#\n" + "#"*47 + "\n\n"); log.flush()
            
            #-Within 'post-eddy', make directory to hold files for EPI distortion correction          
            bias_corr_dir = post_eddy_dir / '2-Bias_Correction'
            bias_corr_dir.mkdir()

            #1. Convert back to .MIF
            dwi_den_deg_preproc_warp_mif = bias_corr_dir/(subjroot + '_dwi_den_deg_preproc_warp.mif')
            log.write("#----Convert the EPI Distortion corrected DWI volumes back to .MIF----#\n\n"); log.flush()
            subprocess.run(['mrconvert', '-info', '-force', '-fslgrad', bvec_posteddy, bval_posteddy, dwi_den_deg_preproc_warp_niigz, \
                dwi_den_deg_preproc_warp_mif], stdout=log, stderr=subprocess.STDOUT)

            #2. Bias correction
            dwi_den_deg_preproc_warp_unb = bias_corr_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb.mif')
            log.write("\n#----Apply the ANTS N4 B1 Field bias correctoin (MRtrix3 dwibiasconnect ants)----#\n\n"); log.flush()
            subprocess.run(['dwibiascorrect', '-info', '-force', 'ants', dwi_den_deg_preproc_warp_mif, dwi_den_deg_preproc_warp_unb, '-scratch', '/tmp'], \
                stdout=log, stderr=subprocess.STDOUT)

            ######################################
            #----Upsampling and Mask Creation----#
            ######################################

            log.write("\n\n" + "#"*38 + "\n" + "#----Upsampling and Mask Creation----#\n" + "#"*38 + "\n\n"); log.flush()

            #-Within 'post-eddy', make directory to hold files for EPI distortion correction
            upsamp_dir = post_eddy_dir / '3-Upsampling_and_Masking'
            upsamp_dir.mkdir()
            
            #1. Regridding to 1.5mm isomorphic voxels #Suggested on 3tissue.github.io/doc/single-subject.html
            dwi_den_deg_preproc_warp_unb_ups = upsamp_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb_ups.mif')
            log.write("#----Regrid the DWI volumes to 1.5mm isomorphic (MRtrix3 mrgrid)----#\n\n"); log.flush()
            subprocess.run(['mrgrid', '-info', '-force', dwi_den_deg_preproc_warp_unb, 'regrid', dwi_den_deg_preproc_warp_unb_ups, '-voxel', '1.5'], \
                stdout=log, stderr=subprocess.STDOUT)
            
            #2. Mask generation
            
            ##a. Extract b0s
            dwi_den_deg_preproc_warp_unb_b0s = upsamp_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb_b0s.mif')
            log.write("\n#----Compute the mean b0 (MRtrix3 dwiextract, mrmath)----#\n\n"); log.flush()
            subprocess.run(['dwiextract', '-info', '-force', '-bzero', dwi_den_deg_preproc_warp_unb, dwi_den_deg_preproc_warp_unb_b0s], stdout=log, \
                stderr=subprocess.STDOUT)
            
            ##b. Compute mean b0
            dwi_den_deg_preproc_warp_unb_meanb0 = upsamp_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb_meanb0.mif')
            subprocess.run(['mrmath', '-info', '-force', '-axis', '3', dwi_den_deg_preproc_warp_unb_b0s, 'mean', dwi_den_deg_preproc_warp_unb_meanb0], \
                stdout=log, stderr=subprocess.STDOUT)
            
            ##c. Convert mean b0 to NII.GZ
            dwi_den_deg_preproc_warp_unb_meanb0_NIIGZ = upsamp_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb_meanb0.nii.gz')
            log.write("\n#----Convert the mean b0 to .NII.GZ (MRtrix3 mrconvert)----#\n\n"); log.flush()
            subprocess.run(['mrconvert', '-info', '-force', dwi_den_deg_preproc_warp_unb_meanb0, dwi_den_deg_preproc_warp_unb_meanb0_NIIGZ], \
                stdout=log, stderr=subprocess.STDOUT)
            
            ##d. Create mask
            dwi_den_deg_preproc_warp_unb_meanb0maskroot = upsamp_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb_meanb0')
            log.write("\n#----Skull-strip the mean b0 and create a binary mask (FSL bet2 -m)----#\n\n"); log.flush()
            subprocess.run(['bet2', dwi_den_deg_preproc_warp_unb_meanb0_NIIGZ, dwi_den_deg_preproc_warp_unb_meanb0maskroot, '-m', '-v'], \
                stdout=log, stderr=subprocess.STDOUT)
            
            ##e. Convert mask back to MIF
            dwi_den_deg_preproc_warp_unb_meanb0mask_NIIGZ = upsamp_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb_meanb0_mask.nii.gz')
            dwi_den_deg_preproc_warp_unb_meanb0mask = upsamp_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb_meanb0_mask.mif')
            log.write("\n#----Convert the mean b0 binary mask to .MIF (MRtrix3 mrconvert)----#\n\n"); log.flush()
            subprocess.run(['mrconvert', '-info', '-force', dwi_den_deg_preproc_warp_unb_meanb0mask_NIIGZ, dwi_den_deg_preproc_warp_unb_meanb0mask], \
                stdout=log, stderr=subprocess.STDOUT)
            
            ##f. Upsample mask
            dwi_den_deg_preproc_warp_unb_meanb0mask_ups = upsamp_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb_meanb0_mask_ups.mif')
            log.write("\n#----Upsample the binary mask to match the upsampled DTI volumes (MRTrx3 mrgrid)----#\n\n"); log.flush()
            subprocess.run(['mrgrid', '-info', '-force', dwi_den_deg_preproc_warp_unb_meanb0mask, 'regrid', \
                dwi_den_deg_preproc_warp_unb_meanb0mask_ups, '-template', dwi_den_deg_preproc_warp_unb_ups, \
                '-interp', 'linear', '-datatype', 'bit'], stdout=log, stderr=subprocess.STDOUT)
            
            ##g. Filter mask
            dwi_den_deg_preproc_warp_unb_meanb0mask_ups_filt = upsamp_dir/(subjroot + '_dwi_den_deg_preproc_warp_unb_meanb0_mask_ups_filt.mif')
            log.write("\n#----Median filter the mask image (MRtrix3 maskfilter median----#\n\n"); log.flush()
            subprocess.run(['maskfilter', '-info', '-force', dwi_den_deg_preproc_warp_unb_meanb0mask_ups, 'median', \
                dwi_den_deg_preproc_warp_unb_meanb0mask_ups_filt], stdout=log, stderr=subprocess.STDOUT)
            
            ########################################
            #----Copying Preprocessed DTI Files----#
            ########################################
            log.write("\n" + "#"*40 + "\n" + "#----Copying Preprocessed DTI Files----#\n" + "#"*40 + "\n\n"); log.flush()
            
            #1. Define output paths and filenamesfor the final, preprocessed volumes and brain mask (in .MIF format)
            dwiproc_out = preproc_dir/(subjroot + '_ppd.mif') #dti/preprocessing/sub-XXX_ses-YY_ppd.mif
            dwimaskproc_out = preproc_dir/(subjroot + '_mask_ppd.mif') #dti/preprocessing/sub-XXX_ses-YY_mask_ppd.mif
            dwibvalproc_out = preproc_dir/(subjroot + '_ppd.bval')
            dwibvecproc_out = preproc_dir/(subjroot + '_ppd.bvec')
            
            #2. Copy preprocessed DTI volumes file to preprocessing directory and rename it sub-XXX_ses-YY_ppd.mif
            shutil.copy(dwi_den_deg_preproc_warp_unb_ups, dwiproc_out)
                
            #3. Copy preprocessed DTI mask file to preprocessing directory and rename it sub-XXX_ses-YY_mask_ppd.mif
            shutil.copy(dwi_den_deg_preproc_warp_unb_meanb0mask_ups_filt, dwimaskproc_out)

            #4. Copy preprocessed bvecs and bvals to preprocessing directory and rename them sub-XXX_ses-YY_ppd.bvec/bval
            shutil.copy(bvec_posteddy, dwibvecproc_out)
            shutil.copy(bval_posteddy, dwibvalproc_out)

            #4. Move preprocessing and original directories to long-term storage (e.g., Vol6)
            dwiout_dir = bidsproc_dir / subj_dir.name / ses_dir.name / 'dwi'
            if dwiout_dir.exists():
                shutil.rmtree(dwiout_dir)
            dwiout_dir.mkdir()

            # preprocout_dir = dwiout_dir / 'preprocessed'
            # preprocout_dir.mkdir(exist_ok=True)

            # origout_dir = dwiout_dir / 'original'
            # origout_dir.mkdir(exist_ok=True)

            shutil.move(str(preproc_dir), str(dwiout_dir))
            shutil.move(str(orig_dir), str(dwiout_dir)) 

            #Need to cleanup bidspreproc directories

            log.write("%"*40 + "\n" + "\t ----DONE---- \n" + "%"*40)

#########################################
#----Starting Preprocessing Pipeline----#
#########################################

#All subjects with DWI scans
subjlist1of3 = ['sub-001', 'sub-003', 'sub-004', 'sub-005', 'sub-006', 'sub-009', 
                'sub-011', 'sub-012', 'sub-013', 'sub-014', 'sub-019', 'sub-020', 
                'sub-021', 'sub-023', 'sub-024', 'sub-025', 'sub-026', 'sub-028', 
                'sub-029', 'sub-031', 'sub-035', 'sub-036', 'sub-041', 'sub-042', 
                'sub-043', 'sub-044', 'sub-045', 'sub-050', 'sub-056', 'sub-057',
                'sub-058', 'sub-059', 'sub-060', 'sub-061', 'sub-062', 'sub-064']
subjlist2of3 = ['sub-065', 'sub-068', 'sub-070', 'sub-071', 'sub-073', 'sub-075', 
                'sub-076', 'sub-078', 'sub-079', 'sub-081', 'sub-082', 'sub-084', 
                'sub-085', 'sub-086', 'sub-087', 'sub-089', 'sub-090', 'sub-091', 
                'sub-092', 'sub-093', 'sub-094', 'sub-097', 'sub-099', 'sub-100', 
                'sub-101', 'sub-104', 'sub-106', 'sub-107', 'sub-108', 'sub-111', 
                'sub-112', 'sub-114', 'sub-117', 'sub-118', 'sub-122', 'sub-124']
subjlist3of3 = ['sub-125', 'sub-127', 'sub-128', 'sub-129', 'sub-131', 'sub-132', 
                'sub-133', 'sub-134', 'sub-135', 'sub-138', 'sub-139', 'sub-140', 
                'sub-141', 'sub-142', 'sub-145', 'sub-146', 'sub-147', 'sub-148', 
                'sub-149', 'sub-151', 'sub-153', 'sub-154', 'sub-155', 'sub-156', 
                'sub-157']

subjs = ['sub-001', 'sub-003', 'sub-004', 'sub-005', 'sub-006', 'sub-009', 
         'sub-011', 'sub-012', 'sub-013', 'sub-014', 'sub-019', 'sub-020', 
         'sub-021', 'sub-023', 'sub-024', 'sub-025', 'sub-026', 'sub-028', 
         'sub-029', 'sub-031', 'sub-035', 'sub-036', 'sub-041', 'sub-042', 
         'sub-043', 'sub-044', 'sub-045', 'sub-050', 'sub-056', 'sub-057',
         'sub-058', 'sub-059', 'sub-060', 'sub-061', 'sub-062', 'sub-064',
         'sub-065', 'sub-068', 'sub-070', 'sub-071', 'sub-073', 'sub-075', 
         'sub-076', 'sub-078', 'sub-079', 'sub-081', 'sub-082', 'sub-084', 
         'sub-085', 'sub-086', 'sub-087', 'sub-089', 'sub-090', 'sub-091', 
         'sub-092', 'sub-093', 'sub-094', 'sub-097', 'sub-099', 'sub-100', 
         'sub-101', 'sub-104', 'sub-106', 'sub-107', 'sub-108', 'sub-111', 
         'sub-112', 'sub-114', 'sub-117', 'sub-118', 'sub-122', 'sub-124',
         'sub-125', 'sub-127', 'sub-128', 'sub-129', 'sub-131', 'sub-132',
         'sub-133', 'sub-134', 'sub-135', 'sub-138', 'sub-139', 'sub-140', 
         'sub-141', 'sub-142', 'sub-145', 'sub-146', 'sub-147', 'sub-148', 
         'sub-149', 'sub-151', 'sub-153', 'sub-154', 'sub-155', 'sub-156', 
         'sub-157']

#sub-104/ses-01 has bad fieldmap
subjspart = ['sub-093', 'sub-094', 'sub-097', 'sub-099', 'sub-100',
             'sub-101', 'sub-106', 'sub-107', 'sub-108', 'sub-111',
             'sub-112', 'sub-114', 'sub-117', 'sub-118', 'sub-122', 'sub-124',
             'sub-125', 'sub-127', 'sub-128', 'sub-129', 'sub-131', 'sub-132',
             'sub-133', 'sub-134', 'sub-135', 'sub-138', 'sub-139', 'sub-140',
             'sub-141', 'sub-142', 'sub-145', 'sub-146', 'sub-147', 'sub-148',
             'sub-149', 'sub-151', 'sub-153', 'sub-154', 'sub-155', 'sub-156',
             'sub-157']

subj_dirs = (subj_dir for subj_dir in bidsmaster_dir.iterdir() if subj_dir.is_dir() and subj_dir.name == "sub-001")


with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=1, verbose = 1)(delayed(dwi_corr)(subj_dir) for subj_dir in sorted(subj_dirs))
