#!/usr/bin/env bash
# JD Russell 2018

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
	printf "\\n%s" "//-----------NOW PRE-PROCESSING----------//"
  printf "\\n%s" "//----------------SUBJECT #--------------//"
	printf "\\n%s" "//------------------$SUBJ_F------------------//"
	printf "\\n%s\\n" "///////////////////////////////////////////"
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

dwi2res() {
  dwi2response dhollander "${SUBJ}"_DTI_den_deg_preproc_unbiased_4.mif "${SUBJ}"_wm.txt "${SUBJ}"_gm.txt "${SUBJ}"_csf.txt -voxels "${SUBJ}"_voxels.mig
}

dwi2fd () {
  dwi2fod msmt_csd "${SUBJ}"_DTI_den_deg_preproc_unbiased_4.mif -mask "${SUBJ}"_DTI_den_deg_preproc_unbiased_mask.mif "${SUBJ}"_wm.txt "${SUBJ}"_wmfod.mif  "${SUBJ}"_csf.txt "${SUBJ}"_csffod.mif
  mrconvert -coord 3 0 "${SUBJ}"_wmfod.mif "${SUBJ}"_wmfod_1st.mif
  mrcat "${SUBJ}"_csffod.mif "${SUBJ}"_wmfod_1st.mif "${SUBJ}"_volfract.mif
}

2tnormalize() {
  mtnormalise "${SUBJ}"_wmfod.mif "${SUBJ}"_wmfod_norm.mif "${SUBJ}"_csffod.mif "${SUBJ}"_csffod_norm.mif -mask "${SUBJ}"_DTI_den_deg_preproc_unbiased_mask.mif
  mrconvert -coord 3 0 "${SUBJ}"_wmfod_norm.mif "${SUBJ}"_wmfod_norm_1st.mif
  mrcat "${SUBJ}"_csffod_norm.mif "${SUBJ}"_wmfod_norm_1st.mif "${SUBJ}"_volfract_norm.mif
}

make_5tt_mask() {
  mrconvert ../ANAT/"${SUBJ}"_T1.nii "${SUBJ}"_T1_raw.mif
  5ttgen fsl "${SUBJ}"_T1_raw.mif "${SUBJ}"_5tt_nocoreg.mif
}

reg_5tt_mask() {
  dwiextract "${SUBJ}"_DTI_den_deg_preproc_unbiased_4.mif "${SUBJ}"_DTI_den_deg_preproc_unbiased_4_b0s.mif -bzero
  mrmath "${SUBJ}"_DTI_den_deg_preproc_unbiased_4_b0s.mif mean "${SUBJ}"_DTI_den_deg_preproc_unbiased_4_meanofb0s.mif -axis 3
  mrconvert "${SUBJ}"_DTI_den_deg_preproc_unbiased_4_meanofb0s.mif "${SUBJ}"_DTI_den_deg_preproc_unbiased_4_meanofb0s.nii.gz
  mrconvert "${SUBJ}"_5tt_nocoreg.mif "${SUBJ}"_5tt_nocoreg.nii.gz
  flirt -v -in "${SUBJ}"_DTI_den_deg_preproc_unbiased_4_meanofb0s.nii.gz -ref "${SUBJ}"_5tt_nocoreg.nii.gz -interp nearestneighbour -dof 6 -omat 001_diff2struct_fsl.mat
  transformconvert 001_diff2struct_fsl.mat "${SUBJ}"_DTI_den_deg_preproc_unbiased_4_meanofb0s.nii.gz "${SUBJ}"_5tt_nocoreg.nii.gz flirt_import 001_diff2struct_mrtrix.txt
  mrtransform "${SUBJ}"_5tt_nocoreg.mif -linear 001_diff2struct_mrtrix.txt -inverse "${SUBJ}"_5TT_coreg.mif
}
####




mif_conv() {
  mrconvert -json_import "${SUBJ}"_DTI.json -fslgrad "${SUBJ}"_DTI.bvec "${SUBJ}"_DTI.bval "${SUBJ}"_DTI.nii "${SUBJ}"_DTI_raw_0.mif
}

denoise() {
  dwidenoise "${SUBJ}"_DTI_raw_0.mif "${SUBJ}"_DTI_den_1.mif -noise "${SUBJ}"_DTI_noise.mif
  mrcalc "${SUBJ}"_DTI_raw_0.mif "${SUBJ}"_DTI_den_1.mif -subtract "${SUBJ}"_DTI_residual.mif
}

degibbs() {
  mrdegibbs "${SUBJ}"_DTI_den_1.mif "${SUBJ}"_DTI_den_deg_2.mif -axes 0,1
  mrcalc "${SUBJ}"_DTI_den_1.mif "${SUBJ}"_DTI_den_deg_2.mif -subtract "${SUBJ}"_DTI_den_resid_undeg.mif 
}

extract_b0() {
  dwiextract -bzero "${SUBJ}"_DTI_den_deg_2.mif "${SUBJ}"_b0.mif
  mrmath "${SUBJ}"_b0.mif mean "${SUBJ}"_b0_mean.mif -axis 3
}

motioncorrect() {
  dwipreproc "${SUBJ}"_DTI_den_deg_2.mif "${SUBJ}"_DTI_den_deg_preproc_3.mif -rpe_none -pe_dir PA -eddy_options " --slm=linear"
}

biascorrect() {
  dwibiascorrect -ants "${SUBJ}"_DTI_den_deg_preproc_3.mif "${SUBJ}"_DTI_den_deg_preproc_unbiased_4.mif -bias "${SUBJ}"_bias.mif
}

create_mask() {
  dwi2mask "${SUBJ}"_DTI_den_deg_preproc_unbiased_4.mif "${SUBJ}"_DTI_den_deg_preproc_unbiased_mask.mif
}

######MAIN######
parse_subjs

for SUBJ in "${subj_array[@]}"; do
	set +f
  subj_start
  make_proc_dir
  proc_prep
  pushd "${MRTRIX_PROC}" || continue
  mif_conv
  denoise
  degibbs
  extract_b0
  motioncorrect
  biascorrect
  create_mask
done
