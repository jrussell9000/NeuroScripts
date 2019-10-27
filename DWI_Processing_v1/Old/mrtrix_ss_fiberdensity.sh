#!/usr/bin/env bash
# JD Russell 2018
# Single tissue fixel-based fibre density and cross section processing and analyses
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/st_fibre_density_cross-section.html

while getopts 'p:' args; do
	case "${args}" in
	p)
		PROC_DIR=${OPTARG}
		;;
	esac
done

######GLOBALS######

######FUNCTIONS#####
parse_subjs() {
	if [ -f subj_list.txt ]; then
		while read -r subjects; do
		  subj_array+=("$subjects")
	  done <subj_list.txt
  else
    find /Volumes/Studies/Herringa/YouthPTSD -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort -u | tr -d "_" >>subj_list.txt
    while read -r subjects; do
      subj_array+=("$subjects")
	  done <subj_list.txt
  fi
}

cleanup_old() {
  if [ -d "${PROC_DIR}/dwiintensitynorm" ]; then
    rm -rf "${PROC_DIR}/dwiintensitynorm"
  fi
}

groupwise_dirs() {
  # Making directory for global intensity normalization
  intnorm_dir="${PROC_DIR}"/dwiintensitynorm
  if [ -d "${intnorm_dir}" ]; then
    rm -rf "${intnorm_dir}"
  fi
  mkdir -p "${intnorm_dir}"/dwi_input
  mkdir "${intnorm_dir}"/mask_input

  # Making directory to contain inputs needed to make FOD template
  template_dir="${PROC_DIR}"/template
  if [ -d "${template_dir}" ]; then
    rm -rf "${template_dir}"
  fi
  mkdir -p "${template_dir}"/fod_input
  mkdir "${template_dir}"/mask_input
}

subj_start() {
  blink=$(tput blink)$(tput setaf 1)
  normal=$(tput sgr0)
  SUBJ_F=${blink}${SUBJ}${normal}
	printf "\\n%s" "///////////////////////////////////////////"
	printf "\\n%s" "//-------------NOW PROCESSING------------//"
  printf "\\n%s" "//----------------SUBJECT #--------------//"
	printf "\\n%s" "//------------------$SUBJ_F------------------//"
	printf "\\n%s\\n" "///////////////////////////////////////////"
  SUBJ_PATH="${PROC_DIR}"/"${SUBJ}"
  MRTRIX_PROC="${SUBJ_PATH}"/mrtrix3_proc
  if [ -d "${MRTRIX_PROC}" ]; then
    rm -rf "${MRTRIX_PROC}"
    mkdir "${MRTRIX_PROC}"
  else
    mkdir "${MRTRIX_PROC}"
  fi
}

make_proc_dir() {
  if [ -d "${SUBJ_PATH}"/mrtrix3_proc ]; then
    rm -rfv "${SUBJ_PATH}"/mrtrix3_proc
	  mkdir -p "${SUBJ_PATH}"/mrtrix3_proc
  else
    mkdir -p "${SUBJ_PATH}"/mrtrix3_proc
  fi
  MRTRIX_PROC="${SUBJ_PATH}"/mrtrix3_proc
}

copy_scanfiles() {
  cp "${SUBJ_PATH}"/DTI/* "${MRTRIX_PROC}"
  cp "${SUBJ_PATH}"/ANAT/* "${MRTRIX_PROC}"
}

conv_nii2mif() {
  cd "${MRTRIX_PROC}" || return
  mrconvert -json_import "${SUBJ}"_DTI.json -fslgrad "${SUBJ}"_DTI.bvec "${SUBJ}"_DTI.bval "${SUBJ}"_DTI.nii DTI.mif
  mrconvert "${SUBJ}"_T1.nii T1.mif
  dwidenoise_input=DTI.mif
}

denoise() {
  printf "\\n%s\\n" "Performing MP-PCA denoising of DWI data..."
  mrgibbs_input="${dwidenoise_input%.*}_den.mif"
  dwidenoise "$dwidenoise_input" "$mrgibbs_input"
  rm "$dwidenoise_input"
}

degibbs() {
  printf "\\n%s\\n" "Removing Gibbs rings from DWI data..."
  geomcorr_input="${mrgibbs_input%.*}_deg.mif"
  mrdegibbs "$mrgibbs_input" "$geomcorr_input" -axes 0,1
  rm "$mrgibbs_input"
}

geomcorrect() {
  printf "\\n%s\\n" "Performing geometric correction of DWI data... Go see a movie."
  biascorr_input="${geomcorr_input%.*}_geomcorr.mif"
  dwipreproc "$geomcorr_input" "$biascorr_input" -rpe_none -pe_dir PA -eddy_options " --slm=linear"
  rm "$geomcorr_input"
}

temp_mask() {
  # SKIPPING GEOMCORRECT FOR TESTING...dwi2mask "$biascorr_input" DTI_temp_mask.mif
  dwi2mask "$geomcorr_input" DTI_temp_mask.mif
}

biascorrect() {
  printf "\\n%s\\n" "Performing bias correction of DWI data..."
  dwibiascorrect -ants "$geomcorr_input" DTI_preproc.mif
  # SKIPPING GEOMCORRECT FOR TESTING...dwibiascorrect -ants "$biascorr_input" DTI_preproc.mif
}

linkout() {
  ln -s "${MRTRIX_PROC}"/DTI_preproc.mif "${intnorm_dir}"/dwi_input/"${SUBJ}"_DTI.mif
  ln -s "${MRTRIX_PROC}"/DTI_temp_mask.mif "${intnorm_dir}"/mask_input/"${SUBJ}"_mask.mif
}

##################################
# Global Intensity Normalization #
##################################

normalize() {
  dwiintensitynorm "${intnorm_dir}"/dwi_input/ "${intnorm_dir}"/mask_input/ "${intnorm_dir}"/dwi_output/ "${intnorm_dir}"/fa_template.mif "${intnorm_dir}"/fa_template_wm_mask.mif
}

#####################################
# Fixed-based Analysis Steps Part I #
#####################################

linkback() {
  ln -s "${intnorm_dir}"/dwi_output/"${SUBJ}"_DTI.mif "${MRTRIX_PROC}"/DTI_norm.mif
}

dwi2res() {
  dwi2response tournier DTI_norm.mif response.txt
}

average_res() {
  cd "${MRTRIX_PROC}" || return
  average_response response.txt "${PROC_DIR}"/group_average_response.txt
}

upsample() {
  mrresize DTI_norm.mif -vox 1.3 DTI_upsamp.mif
  dwi2mask DTI_upsamp.mif DTI_mask.mif
}

make_fod() {
  # Removing unweighted volumes (b0s)
  cd "${MRTRIX_PROC}" || return
  dwiextract DTI_upsamp.mif DTI_noB0s.mif
  dwi2fod msmt_csd DTI_noB0s.mif "${PROC_DIR}"/group_average_response.txt wmfod.mif -mask DTI_mask.mif
}

fod_template_links() {
  ln -s "${MRTRIX_PROC}"/wmfod.mif "${template_dir}"/fod_input/"${SUBJ}"_wmfod.mif
  ln -s "${MRTRIX_PROC}"/DTI_mask.mif "${template_dir}"/mask_input/"${SUBJ}"_mask.mif
}

#############################
# Creating the FOD Template #
#############################

make_fod_template() {
  population_template "${template_dir}"/fod_input -mask_dir "${template_dir}"/mask_input "${template_dir}"/wmfod_template.mif -voxel_size 1.3
}

######################################
# Fixed-based Analysis Steps Part II #
######################################

reg_fod2template() {
  cd "${MRTRIX_PROC}" || return
  mrregister wmfod.mif -mask1 DTI_mask.mif "${template_dir}"/wmfod_template.mif -nl_warp subject2template_warp.mif template2subject_warp.mif
}

warp_mask2template() {
  mrtransform DTI_mask.mif -warp subject2template_warp.mif -interp nearest -datatype bit DTI_mask_in_templ_space.mif
}

############################
# Making FOD Template Mask #
############################

maketemplatemask() {
  mrmath "${PROC_DIR}"/*/DTI_mask_in_templ_space.mif min "${template_dir}"/template_mask.mif -datatype bit
}

makewmfixelmask() {
  cd "${template_dir}" || return
  fod2fixel -mask template_mask.mif -fmls_peak_value 0.10 wmfod_template.mif fixel_mask
}

#######################################
# Fixed-based Analysis Steps Part III #
#######################################

warp_fod2template() {
  cd "${MRTRIX_PROC}" || return
  mrtransform wmfod.mif -warp subject2template_warp.mif -noreorientation FOD_in_template_space_NOT_REORIENTED.mif
}

segment_fod() {
  fod2fixel -mask "${template_dir}"/template_mask.mif "${MRTRIX_PROC}"/FOD_in_template_space_NOT_REORIENTED.mif "${MRTRIX_PROC}"/fixels_in_template_space_NOT_REORIENTED -afd fd.mif
}

reorienting() {
  cd "${MRTRIX_PROC}" || return
  fixelreorient fixels_in_template_space_NOT_REORIENTED subject2template_warp.mif fixel_in_template_space
  rm -rf fixels_in_template_space_NOT_REORIENTED
}

subjfixel2templfixel() {
  cd "${MRTRIX_PROC}" || return
  fixelcorrespondence fixel_in_template_space/fd.mif "${template_dir}"/fixel_mask "${template_dir}"/fd "${SUBJ}"_DTI_corresp_fixels.mif
}

compute_fc() {
  cd "${MRTRIX_PROC}" || return
  warp2metric subject2template_warp.mif -fc "${template_dir}"/fixel_mask "${template_dir}"/fc "${SUBJ}"_FC.mif
}

group_fc() {
  cd "${template_dir}" || return
  mkdir fdc
  cp fc/index.mif fdc
  cp fc/directions.mif fdc
}

dwi2fd () {
  dwi2fod msmt_csd DTI_preproc.mif -mask DTI_preproc_mask_dilated.mif wm_response.txt wmfod.mif csf_response.txt csffod.mif -lmax 10,0,0
  mrconvert -coord 3 0 wmfod.mif wmfod_1st.mif
  mrcat csffod.mif wmfod_1st.mif volfract.mif
}

2tnormalize() {
  mtnormalise wmfod.mif wmfod_norm.mif csffod.mif csffod_norm.mif -mask DTI_preproc_mask_dilated.mif
  mrconvert -coord 3 0 wmfod_norm.mif wmfod_norm_1st.mif
  mrcat csffod_norm.mif wmfod_norm_1st.mif volfract_norm.mif
}

anat() {
  runROBEX.sh T1.nii T1_initial.nii T1_initial_mask.nii
  N4BiasFieldCorrection -i T1.nii -w T1_initial_mask.nii -o T1_biascorr.nii
  runROBEX.sh T1_biascorr.nii T1_biascorr_brain.nii T1_biascorr_brain_mask.nii
  mrconvert T1_biascorr_brain.nii T1_biascorr_brain.mif
  mrconvert T1_biascorr_brain_mask.nii T1_mask.mif -datatype bit

}
make_5tt_mask() {
  mrconvert "${SUBJ}"_T1.nii "${SUBJ}"_T1.mif
  5ttgen fsl "${SUBJ}"_T1_raw.mif "${SUBJ}"_5tt_nocoreg.mif
}

reg_5tt_mask() {
  dwiextract "${SUBJ}"_DTI_den_deg_preproc_unbiased.mif "${SUBJ}"_DTI_den_deg_preproc_unbiased_b0s.mif -bzero
  mrmath "${SUBJ}"_DTI_den_deg_preproc_unbiased_b0s.mif mean "${SUBJ}"_DTI_den_deg_preproc_unbiased_meanofb0s.mif -axis 3
  mrconvert "${SUBJ}"_DTI_den_deg_preproc_unbiased_meanofb0s.mif "${SUBJ}"_DTI_den_deg_preproc_unbiased_meanofb0s.nii.gz
  mrconvert "${SUBJ}"_5tt_nocoreg.mif "${SUBJ}"_5tt_nocoreg.nii.gz
  flirt -v -in "${SUBJ}"_DTI_den_deg_preproc_unbiased_meanofb0s.nii.gz -ref "${SUBJ}"_5tt_nocoreg.nii.gz -interp nearestneighbour -dof 6 -omat "${SUBJ}"_diff2struct_fsl.mat
  transformconvert "${SUBJ}"_diff2struct_fsl.mat "${SUBJ}"_DTI_den_deg_preproc_unbiased_meanofb0s.nii.gz "${SUBJ}"_5tt_nocoreg.nii.gz flirt_import "${SUBJ}"_diff2struct_mrtrix.txt
  mrtransform "${SUBJ}"_5tt_nocoreg.mif -linear "${SUBJ}"_diff2struct_mrtrix.txt -inverse "${SUBJ}"_5TT_coreg.mif
}

######MAIN######
parse_subjs
groupwise_dirs

for SUBJ in "${subj_array[@]}"; do
	set +f
  subj_start
  make_proc_dir
  copy_scanfiles
  conv_nii2mif
  denoise
  degibbs
  #geomcorrect
  temp_mask
  biascorrect
done

normalize
wait $!

for SUBJ in "${subj_array[@]}"; do
  linkback
done 