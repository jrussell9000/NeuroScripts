#!/usr/bin/env python3
# coding: utf-8

import nibabel as nib
import numpy as np
import os
import shutil
import subprocess
import time
from datetime import datetime
from joblib import parallel_backend, delayed, Parallel
from pathlib import Path

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
os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'

subjsrescan = ['sub-154']
ses_dirs_str = (str(ses_dir) for ses_dir in sorted(bidsmaster_dir.glob('*/ses-*')) if Path(ses_dir / 'dwi').exists() and
                ses_dir.parents[0].name in subjsrescan and ses_dir.name == 'ses-02')
ses_list = list(ses_dirs_str)

with open(error_file, "w") as errorfile:
    errorfile.write('SUBJECTS WITH ERRORS' + '\n' + '-'*75 + '\n\n')


def dwi_corr(ses_dir):

    ####################################################################################
    # ----Creating Directory Structures, Copying Files, and Initializing Variables---- #
    ####################################################################################

    # 1. Setting variables
    subj_dir = ses_dir.parent
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
    try:
        shutil.copyfile(sourcedwi, inputdwi)
        shutil.copyfile(sourcebvec, inputbvec)
        shutil.copyfile(sourcebval, inputbval)
        shutil.copyfile(sourcefmap_rads, inputfmap_rads)
        shutil.copyfile(sourcefmap_mag, inputfmap_mag)
    except FileNotFoundError as e:
        with open(error_file, 'w+') as errorfile:
            errorfile.write(subjroot + ': Preprocessing failed due to missing file - ' + e.output)
        next

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
        # native_mnb0_brain_mask = pre_eddy_dir / \
        #    (subjroot + '_native_mnb0_brain_mask.nii.gz')
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

        log.write("\n" + "#"*33 + "\n" +
                  "#----Eddy Current Correction----#\n" + "#"*33 + "\n\n")
        log.flush()

        eddy_dir = preproc_dir / 'eddy'
        if eddy_dir.exists():
            shutil.rmtree(eddy_dir)
        eddy_dir.mkdir(exist_ok=True)
        preeddy_dir = preproc_dir / 'pre-eddy'
        eddy_basename = str(eddy_dir / (subjroot + '_dwi_eddy'))
        eddy_index = eddy_dir / 'eddy_index.txt'
        eddy_acqp = eddy_dir / 'eddy_acqp.txt'
        eddy_mask = preeddy_dir / (subjroot + '_native_mnb0_brain_mask.nii.gz')
        bvec_eddy_woutliers = eddy_dir / (subjroot + '_dwi_eddy.eddy_rotated_bvecs')
        inputbval = orig_dir / (subjroot + '_dwi.bval')

        # Need to organically create slspec based on slice ordering/interleaving (via AFNI?)
        slspec = Path('/Users/jdrussell3/slspec.txt')
        fieldmap2eddy = preeddy_dir / \
            fmap_ph_brain_s4_reg_2_mnb0_brain.stem.split('.')[0]

        # Generating acquistion parameters file - should be created organically
        with open(eddy_acqp, 'w') as acqfile:
            acqfile.write("0 1 0 0.14484")

        # Generating volume index file
        with open(eddy_index, 'w') as indexfile:
            getnvols = subprocess.Popen(
                ['fslval', inputdwi, 'dim4'], stdout=subprocess.PIPE)
            nvols = getnvols.stdout.read()
            for i in range(int(nvols)):
                indexfile.write("1 ")

        # Setting the allowable degrees of freedom for modeling movement
        # Should be N/4, where N is number of excitations (slices) per volume
        # see: https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/eddy/UsersGuide#A--mporder
        mporder_val = int(nvols) / 4

        # Alternate between GPUs
        # Get the numerical index of the subj_dir/ses_dir combination
        # If the index value is even, use GPU 0, if odd use GPU 1
        subjpath = subj_dir.name + '/' + ses_dir.name
        newenv = os.environ.copy()

        for i in range(len(ses_list)):
            if subjpath in ses_list[i]:
                if i % 2 == 0:  # even
                    newenv["CUDA_VISIBLE_DEVICES"] = "0"
                    log.write("#----Now Starting Eddy Current Correction on GPU 0----#\n\n")
                    log.flush()
                    # For alternate even scans, wait two minutes before loading the scan into the GPU
                    if i == 2 or i % 3 == 1:
                        time.sleep(120)
                elif i % 2 == 1:  # odd
                    newenv["CUDA_VISIBLE_DEVICES"] = "1"
                    log.write("#----Now Starting Eddy Current Correction on GPU 1----#\n\n")
                    log.flush()
                    # For alternate odd scans, wait two minutes before loading the scan into the GPU
                    if i == 3 or i % 4 == 1:
                        time.sleep(120)

        try:
            output = subprocess.run(['eddy_cuda9.1',
                                     '--acqp='+str(eddy_acqp),
                                     '--bvals='+str(inputbval),
                                     '--bvecs='+str(inputbvec),
                                     '--cnr_maps',
                                     '--estimate_move_by_susceptibility',
                                     '--field='+str(fieldmap2eddy),
                                     '--fwhm=10,6,4,2,0,0,0,0',
                                     '--imain='+str(inputdwi),
                                     '--index='+str(eddy_index),
                                     '--mask='+str(eddy_mask),
                                     '--out='+str(eddy_basename),
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
            output.check_returncode()

        except subprocess.CalledProcessError as e:
            with open(error_file, 'w+') as errorfile:
                errorfile.write(subjroot + ': FSL eddy correction FAILED with error' + e.output)
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

        # Get the time eddy ended, and compute then report the total eddy run time
        eddy_stoptime = datetime.now()
        eddy_runtime = eddy_stoptime - eddy_starttime
        log.write("#"*50 + "\n" + f"FSL'S EDDY CORRECTION COMPLETED IN: {eddy_runtime}" + "\n" + "#"*50)
        log.flush()

        # Run eddy quality control (eddy_quad) and output to eddy\quad
        subprocess.run(['eddy_quad',
                        str(eddy_basename),
                        '--eddyIdx='+str(eddy_index),
                        '--eddyParams='+str(eddy_acqp),
                        '--mask='+str(eddy_mask),
                        '--bvals='+str(inputbval),
                        '--bvecs='+str(bvec_eddy_woutliers),
                        '--field='+str(fieldmap2eddy),
                        '--slspec='+str(slspec),
                        '--verbose'],
                       stdout=log, stderr=subprocess.STDOUT)

        # --Removing outlier volumes
        dwi_eddy_niigz_woutliers = eddy_dir / (eddy_basename + '.nii.gz')
        dwi_eddy_niigz = eddy_dir / (subjroot + '_dwi_eddy_no_outliers.nii.gz')
        vols_no_outliers = eddy_dir / (subjroot + '_dwi_eddy.qc') / 'vols_no_outliers.txt'

        img = nib.load(dwi_eddy_niigz_woutliers)
        data = img.get_fdata()
        aff = img.affine
        sform = img.get_sform()
        qform = img.get_qform()
        nvols = np.size(data, 3)

        allvols = np.arange(0, nvols)
        goodvols = np.loadtxt(vols_no_outliers)
        vols_to_remove = np.setdiff1d(allvols, goodvols)

        data_to_keep = np.delete(data, vols_to_remove, 3)
        corr_img = nib.Nifti1Image(data_to_keep.astype(np.float32), aff, img.header)
        corr_img.set_sform(sform)
        corr_img.set_qform(qform)
        nib.save(corr_img, dwi_eddy_niigz)
        # --eddy quad creates no outlier bvecs and bvals files, so no need to correct those

        quadout_dir = eddy_dir / (subjroot + '_dwi_eddy.qc')
        bvec_eddy = quadout_dir / 'bvecs_no_outliers.txt'
        bval_eddy = quadout_dir / 'bvals_no_outliers.txt'

        ##############################################
        # ----Removing Gibbs Rings and Denoising---- #
        ##############################################

        log.write("\n\n" + "#"*44 + "\n" + "#----Removing Gibbs Rings and Denoising----#\n" + "#"*44)
        log.flush()

        post_eddy_dir = preproc_dir / 'post-eddy'
        if post_eddy_dir.exists():
            shutil.rmtree(post_eddy_dir)
        post_eddy_dir.mkdir()

        # 1. Converting eddy-corrected volumes to MRTrix3's .mif format

        dwi_eddy = post_eddy_dir / (subjroot + '_dwi_eddy.mif')

        subprocess.run(['mrconvert', '-info', '-force', '-fslgrad', bvec_eddy,
                        bval_eddy, dwi_eddy_niigz, dwi_eddy], stdout=log, stderr=subprocess.STDOUT)

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
        if bias_corr_dir.exists():
            shutil.rmtree(bias_corr_dir)
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
        shutil.copy(bval_eddy, dwibvalproc_out)

        # 4. Move preprocessing and original directories to long-term storage (e.g., Vol6)
        dwiout_dir = bidsproc_dir / subj_dir.name / ses_dir.name / 'dwi'
        # dwiout_dir = Path('/scratch/jdrussell3/preproctest')
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


ses_dirs = (ses_dir for ses_dir in bidsmaster_dir.glob('*/ses-*') if Path(ses_dir / 'dwi').exists() and
            ses_dir.parents[0].name in subjsrescan and ses_dir.name == 'ses-02')

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=4, verbose=1)(
        delayed(dwi_corr)(ses_dir) for ses_dir in sorted(ses_dirs))
