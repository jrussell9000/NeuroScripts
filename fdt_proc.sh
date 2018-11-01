#!/usr/bin/env bash

while getopts 'p:' args; do
	case "${args}" in
	p)
		PROC_DIR=${OPTARG}
		;;
	esac
done

subj_start() {
  blink=$(tput blink)$(tput setaf 1)
  normal=$(tput sgr0)
  SUBJ_F=${blink}${SUBJ}${normal}
	printf "\\n%s" "///////////////////////////////////////////"
	printf "\\n%s" "//-------------NOW PROCESSING------------//"
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
  if [ -d "${SUBJ_PATH}"/fsl_proc ]; then
    rm -rf "${SUBJ_PATH}"/fsl_proc
	  mkdir -p "${SUBJ_PATH}"/fsl_proc
  else
    mkdir -p "${SUBJ_PATH}"/fsl_proc
  fi
  FSL_PROC="${SUBJ_PATH}"/fsl_proc
}

proc_prep() {
  cp "${SUBJ_PATH}"/DTI/* "${FSL_PROC}"
  cp "${SUBJ_PATH}"/FMAP/* "${FSL_PROC}"
}

brain_extract() {
  bet "${SUBJ}"_DTI_fm "${SUBJ}"_DTI_fm_bet_temp
  fslmaths "${SUBJ}"_DTI_fm -mas "${SUBJ}"_DTI_fm_bet_temp "${SUBJ}"_DTI_fm_bet
}

denoise() {
  mrconvert -json_import "${SUBJ}"_DTI.json -fslgrad "${SUBJ}"_DTI.bvec "${SUBJ}"_DTI.bval "${SUBJ}"_DTI_fm_bet.nii.gz "${SUBJ}"_DTI_fm_bet.mif
  dwidenoise "${SUBJ}"_DTI_fm_bet.mif "${SUBJ}"_DTI_fm_bet_den.mif -noise "${SUBJ}"_DTI_noise.mif
  mrcalc "${SUBJ}"_DTI_fm_bet.mif "${SUBJ}"_DTI_fm_bet_den.mif -subtract "${SUBJ}"_DTI_residual.mif
  mrdegibbs "${SUBJ}"_DTI_fm_bet_den.mif "${SUBJ}"_DTI_fm_bet_den_deg.mif
  mrconvert "${SUBJ}"_DTI_fm_bet_den_deg.mif "${SUBJ}"_DTI_fm_bet_den_deg.nii.gz
}

# 0 1 for A>>P phase encoding
create_acqp_index() {
  printf "0 1 0 0.05" >> "${FSL_PROC}"/acqparams.txt
  indx=""
  for ((i=1; i<=56; i+=1)); do indx="$indx 1"; done
  echo "$indx" > index.txt
}

make_mask() {
  fslmaths "${SUBJ}"_DTI_fm_bet -bin "${SUBJ}"_DTI_mask
}

eddy() {
  eddy_cuda --imain="${SUBJ}"_DTI_fm_bet_den_deg --mask="${SUBJ}"_DTI_bet_mask --acqp=acqparams.txt --field="${SUBJ}"_DTI_FMAP \
  --index=index.txt --bvecs="${SUBJ}"_DTI.bvec --bvals="${SUBJ}"_DTI.bval --repol --out="${SUBJ}"_DTI_bet_den_deg_eddy
}

######MAIN######
parse_subjs

for SUBJ in "${subj_array[@]}"; do
	subj_start
  make_proc_dir
  proc_prep
  pushd "${FSL_PROC}" || continue
  brain_extract
  denoise
  create_acqp_index
  eddy
done
