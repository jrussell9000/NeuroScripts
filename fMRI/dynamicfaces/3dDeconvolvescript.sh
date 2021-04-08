#!/bin/bash

subj=$1 # e.g., sub-011
ses=$2  # e.g., ses-01
subjses_root="${subj}_${ses}"
timing_dir='/fast_scratch/jdr/dynamicfaces/TimingFiles'
fmriprep_dir='/fast_scratch/jdr/dynamicfaces/BIDS_fmriprep/fmriprep'
subjses_dir="$fmriprep_dir/${subj}/${ses}/func"

echo $subjses_dir

input="${subjses_dir}/${subjses_root}_task-EPIDynamicFaces_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold_smooth6_scaled.nii.gz"
mask="/fast_scratch/jdr/dynamicfaces/BIDS_fmriprep/fmriprep/masks/longitudinal/full_mask.nii"

rm -f ${subjses_dir}/${subjses_root}_fitts_motionDerivs.nii.gz
rm -f ${subjses_dir}/${subjses_root}_Fim_motionDerivs.nii.gz
rm -f ${subjses_dir}/${subjses_root}_betas_motionDerivs.nii.gz
rm -f ${subjses_dir}/${subjses_root}_matrix_motionDerivs.xmat.1D

3dDeconvolve \
    -input ${input} \
    -polort A \
    -num_stimts 15 \
    -mask ${mask} \
    -censor ${subjses_dir}/${subjses_root}_motion_censor.1D \
    -stim_times 1 ${timing_dir}/angry.stimtime 'GAM(8.6,.547,1)' -stim_label 1 angry \
    -stim_times 2 ${timing_dir}/happy.stimtime 'GAM(8.6,.547,1)' -stim_label 2 happy \
    -stim_times 3 ${timing_dir}/shape.stimtime 'GAM(8.6,.547,1)' -stim_label 3 shape \
    -stim_base 4 -stim_file 4 ${subjses_dir}/${subjses_root}_motion_demean.1D'[0]' -stim_label 4 trans_x \
    -stim_base 5 -stim_file 5 ${subjses_dir}/${subjses_root}_motion_demean.1D'[1]' -stim_label 5 trans_y \
    -stim_base 6 -stim_file 6 ${subjses_dir}/${subjses_root}_motion_demean.1D'[2]' -stim_label 6 trans_z \
    -stim_base 7 -stim_file 7 ${subjses_dir}/${subjses_root}_motion_demean.1D'[3]' -stim_label 7 rot_x \
    -stim_base 8 -stim_file 8 ${subjses_dir}/${subjses_root}_motion_demean.1D'[4]' -stim_label 8 rot_y \
    -stim_base 9 -stim_file 9 ${subjses_dir}/${subjses_root}_motion_demean.1D'[5]' -stim_label 9 rot_z \
    -stim_base 10 -stim_file 10 ${subjses_dir}/${subjses_root}_motion_demean_deriv.1D'[0]' -stim_label 10 trans_x_deriv \
    -stim_base 11 -stim_file 11 ${subjses_dir}/${subjses_root}_motion_demean_deriv.1D'[1]' -stim_label 11 trans_y_deriv \
    -stim_base 12 -stim_file 12 ${subjses_dir}/${subjses_root}_motion_demean_deriv.1D'[2]' -stim_label 12 trans_z_deriv \
    -stim_base 13 -stim_file 13 ${subjses_dir}/${subjses_root}_motion_demean_deriv.1D'[3]' -stim_label 13 rot_x_deriv \
    -stim_base 14 -stim_file 14 ${subjses_dir}/${subjses_root}_motion_demean_deriv.1D'[4]' -stim_label 14 rot_y_deriv \
    -stim_base 15 -stim_file 15 ${subjses_dir}/${subjses_root}_motion_demean_deriv.1D'[5]' -stim_label 15 rot_z_deriv \
    -bout -rout -tout -fout \
    -fitts ${subjses_dir}/${subjses_root}_fitts_motionDerivs.nii.gz \
    -bucket ${subjses_dir}/${subjses_root}_Fim_motionDerivs.nii.gz \
    -cbucket ${subjses_dir}/${subjses_root}_betas_motionDerivs.nii.gz \
    -x1D ${subjses_dir}/${subjses_root}_matrix_motionDerivs.xmat.1D

motionFile=${subjses_dir}/${subjses_root}_motion_censor.1D
numTRs=$(wc -l < ${motionFile})
notCensored=$(1dsum ${motionFile})
totalCensored=$(ccalc -form int -expr "${numTRs}-${notCensored}")
percentCensored=$(ccalc -expr "${totalCensored}/(${numTRs})*100")

echo "${subjses_root} ${totalCensored} ${percentCensored}" >> '/fast_scratch/jdr/dynamicfaces/censorSummary_0.25mm.txt'
