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
  SUBJ_PATH="${PROC_DIR}"/"${SUBJ}"
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

makeprocdir () {
mkdir "${SUBJ}"/fslproc
FSL_PROC="${SUBJ_PATH}"/fslproc
cp "${SUBJ}"/ANAT/* "${SUBJ}"/fslproc
cp "${SUBJ}"/FMAP/* "${SUBJ}"/fslproc
}


bet() {
  bet "${SUBJ}"_DTI.nii "${SUBJ}"_DTI_bet.nii -m
}

denoise() {
  mrconvert -json_import "${SUBJ}"_DTI.json -fslgrad "${SUBJ}"_DTI.bvec "${SUBJ}"_DTI.bval "${SUBJ}"_DTI_bet.nii "${SUBJ}"_DTI_bet.mif
  dwidenoise "${SUBJ}"_DTI_bet.mif "${SUBJ}"_DTI_bet_den.mif -noise "${SUBJ}"_DTI_noise.mif
  mrcalc "${SUBJ}"_DTI_bet.mif "${SUBJ}"_DTI_bet_den.mif -subtract "${SUBJ}"_DTI_residual.mif
  mrdegibbs "${SUBJ}"_DTI_bet_den.mif "${SUBJ}"_DTI_bet_den_deg.mif
  mrconvert "${SUBJ}"_DTI_bet_den_deg.mif "${SUBJ}"_DTI_bet_den_deg.nii
}

# 0 1 for A>>P phase encoding
create_acqp_index() {
printf "0 1 0 0.05" >> acqparams.txt
indx=""
for ((i=1; i<=56; i+=1)); do indx="$indx 1"; done
echo "$indx" > index.txt
}

eddy() {
  eddy_openmp --imain="${SUBJ}"_DTI_bet_den_deg.nii --mask="${SUBJ}"_DTI_bet_mask.nii.gz --acqp=acqparams.txt --field="${SUBJ}"_DTI_FMAP.nii \
  --index=index.txt --bvecs="${SUBJ}"_DTI.bvec --bval="${SUBJ}"_DTI.bval --repol --out="${SUBJ}"_DTI_bet_den_deg_eddy
}

######MAIN######
parse_subjs

for SUBJ in "${subj_array[@]}"; do
	subj_start
  pushd "${FSL_PROC}" || continue
  bet
  denoise
  create_acqp_index
  eddy
done
