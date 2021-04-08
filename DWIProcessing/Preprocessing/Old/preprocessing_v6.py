#!/usr/bin/env python3
# coding: utf-8

import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel
from random import randint

# try:
#     mrtrixbinpath = str(Path(shutil.which("mrconvert")).parent)
#     mrtrixlibpath = str(Path(shutil.which("mrconvert")).parents[1] / 'lib')
#     if mrtrixbinpath not in sys.path:
#         sys.path.append(mrtrixbinpath)
#     if mrtrixlibpath not in sys.path:
#         sys.path.append(mrtrixlibpath)
#     from mrtrix3 import app, fsl, image, path, run
# except (TypeError, ImportError) as e:
#     print("\nERROR: Cannot find the MRtrix3/lib directory. Exiting...\n\n")
#     sys.exit(1)


#####################################
# ----PREPREOCESSING PARAMETERS---- #
#####################################

# --Change as needed - last set for BRC YouthPTSD
bidsmaster_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_master/')
bidspreproc_dir = Path('/scratch/jdrussell3/bidspreproc/')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
slspec = Path('/Users/jdrussell3/slspec.txt')
dwelltime = "0.000568"
totalreadouttime = "0.14484"
error_file = bidspreproc_dir / 'errors.txt'


def dwi_corr(subj_dir):

    with open(error_file) as errorfile:
        errorfile.write('SUBJECTS WITH ERRORS' + '\n' + '-'*75)

    # Initialize the GPU switch as zero
    gpu_switch = 0

    ses_dirs = (ses_dir for ses_dir in subj_dir.iterdir() if subj_dir.is_dir())

    for ses_dir in sorted(ses_dirs):
        ####################################################################################
        # ----Creating Directory Structures, Copying Files, and Initializing Variables---- #
        ####################################################################################

        # 1. Setting variables
        subjroot = "_".join([subj_dir.name, ses_dir.name])
        dwi_dir = ses_dir / 'dwi'
        fmap_dir = ses_dir / 'fmap'
        sourcedwi = dwi_dir/(subjroot + '_acq-AxDTIASSET_dwi.nii')
        sourcebvec = dwi_dir/(subjroot + '_acq-AxDTIASSET_dwi.bvec')
        sourcebval = dwi_dir/(subjroot + '_acq-AxDTIASSET_dwi.bval')
        sourcefmap_rads = fmap_dir / \
            (subjroot + '_acq-RealFieldmapDTIHz_fmap.nii')
        sourcefmap_mag = fmap_dir / \
            (subjroot + '_acq-FieldmapDTI_magnitude1.nii')

        if not sourcedwi.exists():
            next

        # 2. Create directory structure
        preprocdwi_dir = bidspreproc_dir / subj_dir.name / ses_dir.name / 'dwi'
        if preprocdwi_dir.exists():
            shutil.rmtree(preprocdwi_dir)

        # 3. Make directory to hold 'original' unprocessed files
        orig_dir = preprocdwi_dir / 'original'
        orig_dir.mkdir(parents=True, exist_ok=True)

        # 4. Make directory to hold preprocessing files
        preproc_dir = preprocdwi_dir / 'preprocessed'
        preproc_dir.mkdir(parents=True, exist_ok=True)

        # 5. Copy source files to 'original' directory
        inputdwi = orig_dir / (subjroot + '_dwi.nii')
        inputbvec = orig_dir / (subjroot + '_dwi.bvec')
        inputbval = orig_dir / (subjroot + '_dwi.bval')
        inputfmap_rads = orig_dir / (subjroot + '_fmap_hz.nii')
        inputfmap_mag = orig_dir / (subjroot + '_fmap_mag.nii')
        shutil.copyfile(sourcedwi, inputdwi)
        shutil.copyfile(sourcebvec, inputbvec)
        shutil.copyfile(sourcebval, inputbval)
        shutil.copyfile(sourcefmap_rads, inputfmap_rads)
        shutil.copyfile(sourcefmap_mag, inputfmap_mag)

        # 6. Create subject specific log file for preprocessing pipeline in 'preprocessed' directory
        logfile = preproc_dir / (subjroot + "_ppd.txt")

        with open(logfile, 'a') as log:

            ###########################################################
            # ----Preparing Log File and Creating Pre-Eddy Folder---- #
            ###########################################################

            # 1. Print the log file header
            startstr1 = "\n\t   BRAVE RESEARCH CENTER\n\t DTI PREPROCESSING PIPELINE\n"
            startstr2 = "\tSUBJECT: " + subj_dir.name[-3:] + "   " + \
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
            dwi_raw = orig_dir/(subjroot + '_dwi.mif')
            subprocess.run(['mrconvert', '-info', '-force', '-fslgrad', inputbvec,
                            inputbval, inputdwi, dwi_raw], stdout=log, stderr=subprocess.STDOUT)

            # 3. Within 'preprocessed', make directory to hold files created BEFORE eddy processing.
            pre_eddy_dir = preproc_dir / 'pre-eddy'
            pre_eddy_dir.mkdir()

            ############################################
            # ----Register fieldmap to DTI volumes---- #
            ############################################

            # 1. Copy the fieldmap (phase difference in Hz) and magnitude images to processing directory
            log.write(
                "\n#----Copying native fieldmap (in Hz) and magnitude scans to processing directory----#\n\n")
            log.flush()
            native_fmap_ph = pre_eddy_dir/(subjroot + '_native_fmap_ph.nii')
            native_fmap_mag = pre_eddy_dir/(subjroot + '_native_fmap_mag.nii')
            shutil.copy(inputfmap_rads, native_fmap_ph)
            shutil.copy(inputfmap_mag, native_fmap_mag)

            # 2. Create a mean b0 image, then skull strip it and save a binary mask file
            native_b0 = pre_eddy_dir/(subjroot + '_native_b0.nii')
            native_mnb0 = pre_eddy_dir/(subjroot + '_native_b0_brain.nii')
            native_mnb0_brain = pre_eddy_dir / \
                (subjroot + '_native_mnb0_brain.nii.gz')
            native_mnb0_brain_mask = pre_eddy_dir / \
                (subjroot + '_native_mnb0_brain_mask.nii.gz')
            log.write("\n#----Creating a mean b0 image----#\n\n")
            log.flush()
            subprocess.run(['fslroi', inputdwi, native_b0, '0',
                            '7'], stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(['fslmaths', native_b0, '-Tmean',
                            native_mnb0], stdout=log, stderr=subprocess.STDOUT)
            log.write("\n#----Skull-stripping the mean b0 (FSL bet2)----#\n\n")
            log.flush()
            subprocess.run(['bet2', native_mnb0, native_mnb0_brain,
                            '-m', '-v'], stdout=log, stderr=subprocess.STDOUT)

            # 3. Skull strip the magnitude image and save a binary mask file
            native_fmap_mag_brain = pre_eddy_dir / \
                (subjroot + '_native_fmap_mag_brain.nii.gz')
            native_fmap_mag_brain_mask = pre_eddy_dir / \
                (subjroot + '_native_fmap_mag_brain_mask.nii.gz')
            log.write(
                "\n#----Skull-striping the magnitude image and saving a mask (FSL bet2)----#\n\n")
            log.flush()
            subprocess.run(['bet2', native_fmap_mag, native_fmap_mag_brain,
                            '-m', '-v', '-f', '0.3'], stdout=log, stderr=subprocess.STDOUT)

            # 4. Mask the fieldmap using the binary mask of the magnitude image
            native_fmap_ph_brain = pre_eddy_dir / \
                (subjroot + '_native_fmap_ph_brain.nii.gz')
            log.write(
                "\n#----Masking the fieldmap using the binary mask of the magnitude image (FSL fslmaths -mas)----#\n\n")
            log.flush()
            subprocess.run(['fslmaths', native_fmap_ph, '-mas', native_fmap_mag_brain_mask, native_fmap_ph_brain],
                           stdout=log, stderr=subprocess.STDOUT)

            # 5. Smooth the fieldmap
            native_fmap_ph_brain_s4 = pre_eddy_dir / \
                (subjroot + '_native_fmap_ph_brain_s4.nii.gz')
            log.write("\n#----Smoothing the fieldmap (FSL FUGUE; -s 4)----#\n\n")
            log.flush()
            subprocess.run(['fugue', '-v', f'--loadfmap={native_fmap_ph_brain}', '-s', '4',
                            f'--savefmap={native_fmap_ph_brain_s4}'], stdout=log, stderr=subprocess.STDOUT)

            # 6. Warp the magnitude image
            native_fmap_mag_brain_warp = pre_eddy_dir / \
                (subjroot + '_native_fmap_mag_brain_warp.nii.gz')
            log.write(
                "\n#----Warping the magnitude image to the smoothed fieldmap (FSL FUGUE)----#\n\n")
            log.flush()
            subprocess.run(['fugue', '-v', '-i', native_fmap_mag_brain, '--unwarpdir=y', f'--dwell={dwelltime}',
                            f'--loadfmap={native_fmap_ph_brain_s4}', '-w', native_fmap_mag_brain_warp], stdout=log,
                           stderr=subprocess.STDOUT)

            # 7. Linearly register the warped magnitude image to the mean B0 image and save the affine matrix
            fmap_mag_brain_warp_reg_2_mnb0_brain = pre_eddy_dir / \
                (subjroot + '_fmap_mag_brain_warp_reg_2_mnb0_brain.nii.gz')
            fieldmap_2_mnb0_brain_mat = pre_eddy_dir / \
                (subjroot + '_fieldmap_2_mnb0_brain.mat')
            log.write(
                "\n#----Computing the transformation matrix to register the warped magnitude to the mean B0 (FSL FLIRT)----#\n\n")  # noqa: E501
            log.flush()
            subprocess.run(['flirt', '-v', '-in', native_fmap_mag_brain_warp, '-ref', native_mnb0_brain, '-out',
                            fmap_mag_brain_warp_reg_2_mnb0_brain, '-omat', fieldmap_2_mnb0_brain_mat], stdout=log,
                           stderr=subprocess.STDOUT)

            # 8. Linearly register the smoothed fieldmap to the full DTI set using the
            # warped_magnitude-2-meanB0 matrix as a starting point.
            fmap_ph_brain_s4_reg_2_mnb0_brain = pre_eddy_dir / \
                (subjroot + '_fmap_ph_brain_s4_reg_2_mnb0_brain.nii.gz')
            log.write(
                "\n#----Using the warped_mag2meanb0 matrix to register the smoothed fieldmap to the full DTI set (FSL FLIRT)----#\n\n")  # noqa: E501
            log.flush()
            subprocess.run(['flirt', '-v', '-in', native_fmap_ph_brain_s4, '-ref', native_mnb0_brain,
                            '-applyxfm', '-init', fieldmap_2_mnb0_brain_mat, '-out', fmap_ph_brain_s4_reg_2_mnb0_brain],
                           stdout=log, stderr=subprocess.STDOUT)

            ###################################
            # ----Eddy Current Correction---- #
            ###################################
            # https://www.sciencedirect.com/science/article/pii/S1053811915009209
            # dwifslpreproc: https://mrtrix.readthedocs.io/en/dev/dwi_preprocessing/dwifslpreproc.html

            eddy_starttime = datetime.now()

            # 1. Sleep for a random amount of time to avoid collisions when loading processes into GPU (???)
            time.sleep(randint(1, 90))

            # 2. Eddy Current Correction # - MRtrix automatically includes rotated bvecs in output file
            log.write("\n" + "#"*33 + "\n" +
                      "#----Eddy Current Correction----#\n" + "#"*33 + "\n\n")
            log.flush()

            eddyout_dir = preproc_dir/'eddy'
            eddyout_dir.mkdir(exist_ok=True)
            dwi_eddybasename = str(eddyout_dir / (subjroot + '_dwi_eddy'))
            bvec_eddy = eddyout_dir / (subjroot + '_bvec_eddy.bvec')
            # bval_eddy = eddyout_dir / (subjroot + '_bval_eddy.bval')
            eddy_acqp = eddyout_dir / 'eddy_acqp.txt'
            eddy_index = eddyout_dir / 'eddy_index.txt'
            # Need to organically create slspec based on slice ordering/interleaving (via AFNI?)
            slspec = Path('/Users/jdrussell3/slspec.txt')
            fieldmap2eddy = fmap_ph_brain_s4_reg_2_mnb0_brain.parent / \
                fmap_ph_brain_s4_reg_2_mnb0_brain.stem.split('.')[0]

            # eddy options to be passed to dwifslpreproc
            # eddy_options =   f" --very_verbose \
            #                     --slspec={slspec} \
            #                     --slm=linear \
            #                     --repol \
            #                     --cnr_maps \
            #                     --residuals \
            #                     --niter=8 \
            #                     --fwhm=10,6,4,2,0,0,0,0 \
            #                     --mporder=13 \
            #                     --s2v_niter=8 \
            #                     --estimate_move_by_susceptibility \
            #                     --field={fieldmap2eddy}"

            # Generating acquisition parameters file for eddy - Need to verify this
            # Also would be nice to not have to hard code these parameters
            with open(eddy_acqp, 'w') as acqfile:
                acqfile.write("0 1 0 0.14484")

            # Generating eddy index file
            with open(eddy_index, 'w') as indexfile:
                getnvols = subprocess.Popen(
                    ['fslval', inputdwi, 'dim4'], stdout=subprocess.PIPE)
                nvols = getnvols.stdout.read()
                for i in range(int(nvols)):
                    indexfile.write("1 ")

            mporder_val = int(nvols) / 4
            # Need to calc mporder value (N_slices / 4) instead of hardcoding
            # subprocess.run(['dwifslpreproc', '-info', '-force', dwi_raw, dwi_eddy, '-pe_dir',
            # 'AP', '-rpe_none', '-scratch', '/tmp', '-eddy_options', eddy_options, '-eddyqc_all',
            #  eddyout_dir, '-readout_time', totalreadouttime, '-export_grad_fsl',
            #  bvec_eddy, bval_eddy], stdout=log, stderr=subprocess.STDOUT)

            # Possible new, direct eddy call - doing this allows us to use all eddy options
            # (e.g., very_verbose), see real-time output, call eddy_quad independently,
            # and not depend on the MRTrix guys to keep pace with the FSL updates to eddy

            # Alternate between GPUs
            newenv = os.environ.copy()
            newenv['CUDA_VISIBLE_DEVICES'] = [str(gpu_switch)]
            try:
                subprocess.check_output(['eddy_cuda9.1',
                                         '--acqp='+str(eddy_acqp),
                                         '--bvals='+str(inputbval),
                                         '--bvecs='+str(inputbvec),
                                         '--cnr_maps',
                                         '--estimate_move_by_susceptibility',
                                         '--field='+str(fieldmap2eddy),
                                         '--fwhm=10,6,4,2,0,0,0,0',
                                         '--imain='+str(inputdwi),
                                         '--index='+str(eddy_index),
                                         '--mask='+str(native_mnb0_brain_mask),
                                         '--out='+str(dwi_eddybasename),
                                         '--mporder='+str(mporder_val),
                                         '--niter=8',
                                         '--residuals',
                                         '--repol',
                                         '--s2v_niter=8',
                                         '--slm=linear',
                                         '--slspec='+str(slspec),
                                         '--very_verbose'],
                                        env=newenv,
                                        stdout=log, stderr=subprocess.STDOUT)
                # Switch visible GPUs
                gpu_switch = 1 - gpu_switch
            except subprocess.CalledProcessError as e:
                with open(error_file, 'w+') as errorfile:
                    errorfile.write(subjroot + ' :FSL eddy correction FAILED with error' + e.output)
                next

            # Abbreviated eddy correction for testing-purposes
            # subprocess.run(['eddy_cuda9.1',
            #                 '--acqp='+str(eddy_acqp),
            #                 '--bvals='+str(inputbval),
            #                 '--bvecs='+str(inputbvec),
            #                 '--field='+str(fieldmap2eddy),
            #                 '--imain='+str(inputdwi),
            #                 '--index='+str(eddy_index),
            #                 '--mask='+str(native_mnb0_brain_mask),
            #                 '--out='+str(dwi_eddybasename),
            #                 '--very_verbose'],
            #                stdout=sys.stdout, stderr=sys.stderr)

            dwi_eddy_niigz = eddyout_dir / (dwi_eddybasename + '.nii.gz')
            bvec_eddy = eddyout_dir / (dwi_eddybasename + '.eddy_rotated_bvecs')

            eddy_stoptime = datetime.now()

            eddy_runtime = eddy_stoptime - eddy_starttime
            log.write("#"*50 + "\n" + f"FSL'S EDDY CORRECTION COMPLETED IN: {eddy_runtime}" + "\n" + "#"*50)
            log.flush()

            subprocess.run(['eddy_quad',
                            str(dwi_eddybasename),
                            '--eddyIdx='+str(eddy_index),
                            '--eddyParams='+str(eddy_acqp),
                            '--mask='+str(native_mnb0_brain_mask),
                            '--bvals='+str(inputbval),
                            '--bvecs='+str(bvec_eddy),
                            '--output-dir='+str(eddyout_dir / 'quad'),
                            '--field='+str(fieldmap2eddy),
                            '--slspec='+str(slspec),
                            '--verbose'],
                           stdout=log, stderr=subprocess.STDOUT)

            ##############################################
            # ----Removing Gibbs Rings and Denoising---- #
            ##############################################

            log.write("\n\n" + "#"*44 + "\n" + "#----Removing Gibbs Rings and Denoising----#\n" + "#"*44)
            log.flush()

            post_eddy_dir = preproc_dir / 'post-eddy'
            post_eddy_dir.mkdir()

            # 1. Converting eddy-corrected volumes to MRTrix3's .mif format

            dwi_eddy = post_eddy_dir / (subjroot + '_dwi_eddy.mif')

            subprocess.run(['mrconvert', '-info', '-force', '-fslgrad', bvec_eddy,
                            inputbval, dwi_eddy_niigz, dwi_eddy], stdout=log, stderr=subprocess.STDOUT)

            # 1. Denoise #https://www.ncbi.nlm.nih.gov/pubmed/27523449
            log.write("\n#----Denoising (MRtrix3 dwidenoise)----#\n\n")
            log.flush()
            dwi_eddy_den = post_eddy_dir/(subjroot + '_dwi_eddy_den.mif')
            subprocess.run(['dwidenoise', '-info', '-force', dwi_eddy,
                            dwi_eddy_den], stdout=log, stderr=subprocess.STDOUT)

            # 2. Remove Gibbs rings #https://onlinelibrary.wiley.com/doi/full/10.1002/mrm.26054
            log.write("\n#----Removing Gibbs Rings (MRtrix3 mrdegibbs)----#\n\n")
            log.flush()
            dwi_eddy_den_deg = post_eddy_dir / \
                (subjroot + '_dwi_eddy_den_deg.mif')
            subprocess.run(['mrdegibbs', '-info', '-force', dwi_eddy_den,
                            dwi_eddy_den_deg], stdout=log, stderr=subprocess.STDOUT)

            #################################################
            # ----Bias Field (B1) Distortion Correction---- #
            #################################################
            # https://www.ncbi.nlm.nih.gov/pubmed/20378467

            log.write("\n\n" + "#"*47 + "\n" +
                      "#----Bias Field (B1) Distortion Correction----#\n" + "#"*47 + "\n\n")
            log.flush()

            # -Within 'post-eddy', make directory to hold files for EPI distortion correction
            bias_corr_dir = post_eddy_dir / '2-Bias_Correction'
            bias_corr_dir.mkdir()

            # -Bias correction
            dwi_eddy_den_deg_unb = bias_corr_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb.mif')
            log.write(
                "\n#----Apply the ANTS N4 B1 Field bias correctoin (MRtrix3 dwibiasconnect ants)----#\n\n")
            log.flush()
            subprocess.run(['dwibiascorrect', '-info', '-force', 'ants', dwi_eddy_den_deg,
                            dwi_eddy_den_deg_unb, '-scratch', '/tmp'], stdout=log, stderr=subprocess.STDOUT)

            ########################################
            # ----Upsampling and Mask Creation---- #
            ########################################

            log.write("\n\n" + "#"*38 + "\n" +
                      "#----Upsampling and Mask Creation----#\n" + "#"*38 + "\n\n")
            log.flush()

            # -Within 'post-eddy', make directory to hold files for EPI distortion correction
            upsamp_dir = post_eddy_dir / '3-Upsampling_and_Masking'
            upsamp_dir.mkdir()

            # 1. Regridding to 1.5mm isomorphic voxels #Suggested on 3tissue.github.io/doc/single-subject.html
            dwi_eddy_den_deg_unb_ups = upsamp_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb_ups.mif')
            log.write(
                "#----Regrid the DWI volumes to 1.5mm isomorphic (MRtrix3 mrgrid)----#\n\n")
            log.flush()
            subprocess.run(['mrgrid', '-info', '-force', dwi_eddy_den_deg_unb, 'regrid', dwi_eddy_den_deg_unb_ups,
                            '-voxel', '1.5'], stdout=log, stderr=subprocess.STDOUT)

            # 2. Mask generation

            # a. Extract b0s
            dwi_eddy_den_deg_unb_b0s = upsamp_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb_b0s.mif')
            log.write(
                "\n#----Compute the mean b0 (MRtrix3 dwiextract, mrmath)----#\n\n")
            log.flush()
            subprocess.run(['dwiextract', '-info', '-force', '-bzero', dwi_eddy_den_deg_unb, dwi_eddy_den_deg_unb_b0s],
                           stdout=log, stderr=subprocess.STDOUT)

            # b. Compute mean b0
            dwi_eddy_den_deg_unb_meanb0 = upsamp_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb_meanb0.mif')
            subprocess.run(['mrmath', '-info', '-force', '-axis', '3', dwi_eddy_den_deg_unb_b0s, 'mean',
                            dwi_eddy_den_deg_unb_meanb0],
                           stdout=log, stderr=subprocess.STDOUT)

            # c. Convert mean b0 to NII.GZ
            dwi_eddy_den_deg_unb_meanb0_NIIGZ = upsamp_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb_meanb0.nii.gz')
            log.write(
                "\n#----Convert the mean b0 to .NII.GZ (MRtrix3 mrconvert)----#\n\n")
            log.flush()
            subprocess.run(['mrconvert', '-info', '-force', dwi_eddy_den_deg_unb_meanb0,
                            dwi_eddy_den_deg_unb_meanb0_NIIGZ],
                           stdout=log, stderr=subprocess.STDOUT)

            # d. Create mask
            dwi_eddy_den_deg_unb_meanb0maskroot = upsamp_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb_meanb0')
            log.write(
                "\n#----Skull-strip the mean b0 and create a binary mask (FSL bet2 -m)----#\n\n")
            log.flush()
            subprocess.run(['bet2', dwi_eddy_den_deg_unb_meanb0_NIIGZ, dwi_eddy_den_deg_unb_meanb0maskroot, '-m', '-v'],
                           stdout=log, stderr=subprocess.STDOUT)

            # e. Convert mask back to MIF
            dwi_eddy_den_deg_unb_meanb0mask_NIIGZ = upsamp_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb_meanb0_mask.nii.gz')
            dwi_eddy_den_deg_unb_meanb0mask = upsamp_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb_meanb0_mask.mif')
            log.write(
                "\n#----Convert the mean b0 binary mask to .MIF (MRtrix3 mrconvert)----#\n\n")
            log.flush()
            subprocess.run(['mrconvert', '-info', '-force', dwi_eddy_den_deg_unb_meanb0mask_NIIGZ,
                            dwi_eddy_den_deg_unb_meanb0mask],
                           stdout=log, stderr=subprocess.STDOUT)

            # f. Upsample mask
            dwi_eddy_den_deg_unb_meanb0mask_ups = upsamp_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb_meanb0_mask_ups.mif')
            log.write(
                "\n#----Upsample the binary mask to match the upsampled DTI volumes (MRTrx3 mrgrid)----#\n\n")
            log.flush()
            subprocess.run(['mrgrid', '-info', '-force', dwi_eddy_den_deg_unb_meanb0mask, 'regrid',
                            dwi_eddy_den_deg_unb_meanb0mask_ups, '-template', dwi_eddy_den_deg_unb_ups,
                            '-interp', 'linear', '-datatype', 'bit'], stdout=log, stderr=subprocess.STDOUT)

            # g. Filter mask
            dwi_eddy_den_deg_unb_meanb0mask_ups_filt = upsamp_dir / \
                (subjroot + '_dwi_eddy_den_deg_unb_meanb0_mask_ups_filt.mif')
            log.write(
                "\n#----Median filter the mask image (MRtrix3 maskfilter median----#\n\n")
            log.flush()
            subprocess.run(['maskfilter', '-info', '-force', dwi_eddy_den_deg_unb_meanb0mask_ups, 'median',
                            dwi_eddy_den_deg_unb_meanb0mask_ups_filt], stdout=log, stderr=subprocess.STDOUT)

            ##########################################
            # ----Copying Preprocessed DTI Files---- #
            ##########################################
            log.write("\n" + "#"*40 + "\n" +
                      "#----Copying Preprocessed DTI Files----#\n" + "#"*40 + "\n\n")
            log.flush()

            # 1. Define output paths and filenamesfor the final, preprocessed volumes and brain mask (in .MIF format)
            #    dti/preprocessing/sub-XXX_ses-YY_ppd.mif
            dwiproc_out = preproc_dir/(subjroot + '_ppd.mif')
            # dti/preprocessing/sub-XXX_ses-YY_mask_ppd.mif
            dwimaskproc_out = preproc_dir/(subjroot + '_mask_ppd.mif')
            dwibvalproc_out = preproc_dir/(subjroot + '_ppd.bval')
            dwibvecproc_out = preproc_dir/(subjroot + '_ppd.bvec')

            # 2. Copy preprocessed DTI volumes file to preprocessing directory and rename it sub-XXX_ses-YY_ppd.mif
            shutil.copy(dwi_eddy_den_deg_unb_ups, dwiproc_out)

            # 3. Copy preprocessed DTI mask file to preprocessing directory and rename it sub-XXX_ses-YY_mask_ppd.mif
            shutil.copy(dwi_eddy_den_deg_unb_meanb0mask_ups_filt,
                        dwimaskproc_out)

            # 4. Copy preprocessed bvecs and bvals to preprocessing directory and rename them
            #    sub-XXX_ses-YY_ppd.bvec/bval
            shutil.copy(bvec_eddy, dwibvecproc_out)
            shutil.copy(inputbval, dwibvalproc_out)

            # 4. Move preprocessing and original directories to long-term storage (e.g., Vol6)
            #    dwiout_dir = bidsproc_dir / subj_dir.name / ses_dir.name / 'dwi'
            dwiout_dir = Path('/scratch/jdrussell3/preproctest')
            if dwiout_dir.exists():
                shutil.rmtree(dwiout_dir)
            dwiout_dir.mkdir()

            shutil.move(str(preproc_dir), str(dwiout_dir))
            shutil.move(str(orig_dir), str(dwiout_dir))

            # Need to cleanup bidspreproc directories

            log.write("%"*40 + "\n" + "\t ----DONE---- \n" + "%"*40)

###########################################
# ----Starting Preprocessing Pipeline---- #
###########################################


# All subjects with DWI scans
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

# sub-104/ses-01 has bad fieldmap
subjspart = ['sub-093', 'sub-094', 'sub-097', 'sub-099', 'sub-100',
             'sub-101', 'sub-106', 'sub-107', 'sub-108', 'sub-111',
             'sub-112', 'sub-114', 'sub-117', 'sub-118', 'sub-122', 'sub-124',
             'sub-125', 'sub-127', 'sub-128', 'sub-129', 'sub-131', 'sub-132',
             'sub-133', 'sub-134', 'sub-135', 'sub-138', 'sub-139', 'sub-140',
             'sub-141', 'sub-142', 'sub-145', 'sub-146', 'sub-147', 'sub-148',
             'sub-149', 'sub-151', 'sub-153', 'sub-154', 'sub-155', 'sub-156',
             'sub-157']

subj_dirs = (subj_dir for subj_dir in bidsmaster_dir.iterdir()
             if subj_dir.is_dir() and subj_dir.name in subjlist1of3)


with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=2, verbose=1)(
        delayed(dwi_corr)(subj_dir) for subj_dir in sorted(subj_dirs))
