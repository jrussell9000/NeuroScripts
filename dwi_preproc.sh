#!/usr/bin/env bash
# JD Russell 2018
# MRTrix3 preprocessing steps

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

make_proc_dir() {
	SUBJ_PATH="${PROC_DIR}"/"${SUBJ}"
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
}

mif_conv() {
  mrconvert -json_import "${SUBJ}"_DTI.json -fslgrad "${SUBJ}"_DTI.bvec "${SUBJ}"_DTI.bval "${SUBJ}"_DTI.nii "${SUBJ}"_DTI_raw.mif
}

denoise() {
  dwidenoise "${SUBJ}"_DTI_raw.mif "${SUBJ}"_DTI_den.mif -noise "${SUBJ}"_DTI_noise.mif
  mrcalc "${SUBJ}"_DTI_raw.mif "${SUBJ}"_DTI_den.mif -subtract "${SUBJ}"_DTI_residual.mif
}

degibbs() {
  mrdegibbs "${SUBJ}"_DTI_den.mif "${SUBJ}"_DTI_den_deg.mif -axes 0,1
  mrcalc "${SUBJ}"_DTI_den.mif "${SUBJ}"_DTI_den_deg.mif -subtract "${SUBJ}"_DTI_den_resid_undeg.mif 
}

extract_b0() {
  dwiextract -bzero "${SUBJ}"_DTI_den_deg.mif "${SUBJ}"_b0.mif
  mrmath "${SUBJ}"_b0.mif mean "${SUBJ}"_b0_mean.mif -axis 3
}

motioncorrect() {
  dwipreproc "${SUBJ}"_DTI_den_deg.mif "${SUBJ}"_DTI_den_deg_preproc.mif -rpe_none -pe_dir PA -eddy_options " --slm=linear"
}

biascorrect() {
  dwibiascorrect -ants "${SUBJ}"_DTI_den_deg_preproc.mif "${SUBJ}"_DTI_den_deg_preproc_unbiased.mif -bias "${SUBJ}"_bias.mif
}

create_mask() {
  dwi2mask "${SUBJ}"_DTI_den_deg_preproc_unbiased.mif "${SUBJ}"_DTI_den_deg_preproc_unbiased_mask.mif
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
  time motioncorrect
  biascorrect
  create_mask
done