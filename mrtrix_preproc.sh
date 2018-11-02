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
  cp "${SUBJ_PATH}"/ANAT/* "${MRTRIX_PROC}"
}

mif_conv() {
  mrconvert -json_import "${SUBJ}"_DTI.json -fslgrad "${SUBJ}"_DTI.bvec "${SUBJ}"_DTI.bval "${SUBJ}"_DTI.nii "${SUBJ}"_DTI.mif
  mrconvert "${SUBJ}"_T1.nii "${SUBJ}"_T1.mif
  dwidenoise_input="${SUBJ}"_DTI.mif
}

denoise() {
  printf "\\n%s\\n" "Performing MP-PCA denoising of DWI data..."
  mrgibbs_input="${dwidenoise_input}_denoise.mif"
  dwidenoise "$dwidenoise_input" "$mrgibbs_input"
  rm "$dwidenoise_input"
  # mrcalc "${SUBJ}"_DTI_raw.mif "${SUBJ}"_DTI_den.mif -subtract "${SUBJ}"_DTI_residual.mif
}

degibbs() {
  printf "\\n%s\\n" "Removing Gibbs rings from DWI data..."
  geomcorr_input="${mrgibbs_input}_degibbs.mif"
  mrdegibbs "$mrgibbs_input" "$preproc_input" -axes 0,1
  rm "$dwidenoise_input"
  # mrcalc "${SUBJ}"_DTI_den.mif "${SUBJ}"_DTI_den_deg.mif -subtract "${SUBJ}"_DTI_den_resid_undeg.mif 
}

extract_b0() {
  dwiextract -bzero "${SUBJ}"_DTI_den_deg.mif "${SUBJ}"_b0.mif
  mrmath "${SUBJ}"_b0.mif mean "${SUBJ}"_b0_mean.mif -axis 3
}

geomcorrect() {
  printf "\\n%s\\n" "Performing geometric correction of DWI data... Go see a movie."
  biascorr_input="${geomcorr_input}_geomcorr.mif"
  dwipreproc "$geomcorr_input" "$biascorr_input" -rpe_none -pe_dir PA -eddy_options " --slm=linear"
}

biascorrect() {
  printf "\\n%s\\n" "Performing bias correction of DWI data..."
  preproc_output="${SUBJ}_preproc.mif"
  dwibiascorrect -ants "$biascorr_input" "$preproc_output"
}

create_mask() {
  printf "\\n%s\\n" "Creating brain mask for spherical deconvolution..."
  dwi2mask "${SUBJ}"_preproc.mif "${SUBJ}"_preproc_mask.mif
  maskfilter "${SUBJ}"_preproc_mask.mif -dilate "${SUBJ}"_preproc_mask_dilated.mif -npass 3
}

######MAIN######
main() {
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
    # extract_b0
    time geomcorrect
    biascorrect
    create_mask
  done
}