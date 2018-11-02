#!/usr/bin/env bash
# JD Russell 2018
# Processing DWI to connectomes using MRTrix3

while getopts 'p:' args; do
	case "${args}" in
	p)
		PROC_DIR=${OPTARG}
		;;
	esac
done

######GLOBALS######

######FUNCTIONS#####

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

make_dwi_mask() {
  "${SUBJ}"_
}

dwi2res() {
  dwi2response dhollander "${SUBJ}"_preproc.mif "${SUBJ}"_wm.txt "${SUBJ}"_gm.txt "${SUBJ}"_csf.txt -mask "${SUBJ}"_preproc_mask.mif
}

dwi2fd () {
  dwi2fod msmt_csd "${SUBJ}"_preproc.mif -mask "${SUBJ}"_preproc_mask_dilated.mif "${SUBJ}"_wm.txt "${SUBJ}"_wmfod.mif  "${SUBJ}"_csf.txt "${SUBJ}"_csffod.mif \
  -lmax 10,0,0
  mrconvert -coord 3 0 "${SUBJ}"_wmfod.mif "${SUBJ}"_wmfod_1st.mif
  mrcat "${SUBJ}"_csffod.mif "${SUBJ}"_wmfod_1st.mif "${SUBJ}"_volfract.mif
}

2tnormalize() {
  mtnormalise "${SUBJ}"_wmfod.mif "${SUBJ}"_wmfod_norm.mif "${SUBJ}"_csffod.mif "${SUBJ}"_csffod_norm.mif -mask "${SUBJ}"_preproc_mask_dilated.mif
  mrconvert -coord 3 0 "${SUBJ}"_wmfod_norm.mif "${SUBJ}"_wmfod_norm_1st.mif
  mrcat "${SUBJ}"_csffod_norm.mif "${SUBJ}"_wmfod_norm_1st.mif "${SUBJ}"_volfract_norm.mif
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
  dwi2res
  dwi2fd
  2tnormalize
  make_5tt_mask
  reg_5tt_mask
done
