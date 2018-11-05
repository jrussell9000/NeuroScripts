#!/usr/bin/env bash
# JD Russell 2018
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
}

make_proc_dir() {
  if [ -d "${SUBJ_PATH}"/mrtrix3_proc ]; then
    rm -rf "${SUBJ_PATH}"/mrtrix3_proc
	  mkdir -p "${SUBJ_PATH}"/mrtrix3_proc
  else
    mkdir -p "${SUBJ_PATH}"/mrtrix3_proc
  fi
  MRTRIX_PROC="${SUBJ_PATH}"/mrtrix3_proc
}

proc_prep() {
  cp "${SUBJ_PATH}"/DTI/* "${MRTRIX_PROC}"
  cp "${SUBJ_PATH}"/ANAT/* "${MRTRIX_PROC}"
}

mif_conv() {
  mrconvert -json_import DTI.json -fslgrad DTI.bvec DTI.bval DTI.nii DTI.mif
  mrconvert T1.nii T1.mif
  dwidenoise_input=DTI.nii
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
}

temp_mask() {
  dwi2mask "$biascorr_input" DTI_temp_mask.mif
}

intnorm_prep() {
  intnorm_dir="${PROC_DIR}"/dwiintensitynorm
  if [ ! -d ${intnorm_dir} ]; then
    mkdir -p "${intnorm_dir}"/dwi_input
    mkdir "${intnorm_dir}"/mask_input
  fi
  ln -sr "${SUBJ_PATH}"/mrtrix3_proc/"${biascorr_input}" "${intnorm_dir}"/dwi_input/"${SUBJ}"_biascorr.mif
  ln -sr "${SUBJ_PATH}"/mrtrix3_proc/DTI_temp_mask.mif "${intnorm_dir}"/mask/"${SUBJ}"_mask.mif
}

normalize() {
  dwiintensitynorm "${intnorm_dir}"/dwi_input/ "${intnorm_dir}"/mask_input "${intnorm_dir}"/dwi_output/ "${intnorm_dir}"/fa_template.mif "${intnorm_dir}"/fa_template_wm_mask.mif
!!!!!!!!!!!!!!!!!!!!!!!!!!!!
}

biascorrect() {
  printf "\\n%s\\n" "Performing bias correction of DWI data..."
  dwibiascorrect -ants "$biascorr_input" DTI_preproc.mif
}

dwi2res() {
  dwi2response dhollander DTI_preproc.mif wm_response.txt gm_response.txt csf_response.txt -mask DTI_preproc_mask.mif
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

for SUBJ in "${subj_array[@]}"; do
	set +f
  subj_start
  pushd "${MRTRIX_PROC}" || continue
  make_proc_dir
  proc_prep
  mif_conv
  denoise
  degibbs
  geomcorrect
  temp_mask
done

for SUBJ in "${subj_array[@]}"; do
  intnorm_prep
  normalize
done
