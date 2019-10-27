#!/usr/bin/env bash


set -e 

usage() {
  cat << EOF
    Usage: fdt_proc.sh PARAMETER

    PARAMETERS:

    --studydir=<study-dir>   path to read/write location where raw scans exist and processed output will be placed
    --subject=<subject-id>  numeric subject ID. Should match the name of the directory containing the individual subject files
  
EOF
}

get_options() {
  unset INPUT_DIR
  unset OUTPUT_DIR

  local index=0
  local numargs=${#arguments[@]}
  local argument

  while [ ${index} -lt ${numargs} ] ; do
    argument=${arguments[index]}

    case ${argument} in
      --help)
        usage
        exit 1
        ;;
      --studydir=*)
        STUDY_DIR=${argument#*=}
        index=$(( index + 1 ))
        ;;
      --subject=*)
        SUBJECT=${argument#*=}
        index=$(( index + 1 ))
        ;;
      *)
        usage
        echo "ERROR: Option ${argument} not recognized."
        exit 1
        ;;
    esac
  done

  #Check for required variables, and echo an error message if they're missing
  local error_msgs=""

  if [ -z "${STUDY_DIR}" ] ; then
    error_msgs+="\nERROR: <study-dir> not specified."
  fi

  if [ -z "${SUBJECT}" ] ; then
    error_msgs+="\nERROR: <subject> not specified."
  fi

  if [ -z "${FSL_DIR}" ] ; then
    error_msgs+="ERROR: FSLDIR environment variable not set.  Is FSL installed?"
  fi

  if [ -z "${error_msgs}" ] ; then
    usage
    echo -e "${error_msgs}"
    exit 1
  fi

  echo "Location of study files: ${INPUT_DIR}"
  echo "Performing operations for subjects: ${OUTPUT_DIR}"

}
tmp_dir() {
  if [ -d "${TMP}" ]; then
    rm -rf "${TMP}"
  fi
  unset "${rand}"
  unset "${TMP}"
  rand=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 8 | head -n 1)
  TMP=/tmp/fdt_proc-${rand}
  mkdir "${TMP}"
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

main() {

  get_options $@
  DWIPROC="DWI_processing"
  INPUT_DIR="${STUDY_DIR}"/"${SUBJECT}"
  OUTPUT_DIR=${STUDY_DIR}/${SUBJECT}/${DWIPROC}

  if [ -d $OUTPUT_DIR ] ; then
    rm -rf ${OUTPUT_DIR}
  fi

  mkdir -p ${OUTPUT_DIR}
  mkdir -p ${OUTPUT_DIR}/original
  mkdir -p ${OUTPUT_DIR}/raw

  pepositive="pepolar0"
  penegative="pepolar1"

  for file in "$INPUT_DIR"/*.NODDI*.tgz; do
    if [[ "$file" == *"$pepositive"* ]]; then
      tmp_dir
      cp "$file" "$TMP"
      tar xvf "$TMP"/*.tgz
      "${FSL_DIR}"/bin/imcp "$TMP"/*.nii "$OUTPUT_DIR"/raw/"$pepositive".nii
      cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$pepositive".bval
      cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$pepositive".bvec
    fi
    if [[ "$file" == *"$penegative"* ]]; then
      tmp_dir
      cp "$file" "$TMP"
      tar xvf "$TMP"/*.tgz
      "${FSL_DIR}"/bin/imcp "$TMP"/*.nii "$OUTPUT_DIR"/raw/"$penegative".nii
      cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$penegative".bval
      cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$penegative".bvec
    fi
  done
}







}
while getopts 'p:' args; do
	case "${args}" in
  i)
    INPUT_DIR=${OPTARG}
    ;;
	o)
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

copy_scanfiles() {
  cp "${SUBJ_PATH}"/DTI/* "${FSL_PROC}"
  cp "${SUBJ_PATH}"/FMAP/* "${FSL_PROC}"
}

# brain_extract() {
#   bet "${SUBJ}"_DTI_fm "${SUBJ}"_DTI_fm_bet_temp -v
#   fslmaths "${SUBJ}"_DTI_fm -mas "${SUBJ}"_DTI_fm_bet_temp "${SUBJ}"_DTI_fm_bet
# }

denoise() {
  mrconvert -quiet -json_import "${SUBJ}"_DTI.json -fslgrad "${SUBJ}"_DTI.bvec "${SUBJ}"_DTI.bval "${SUBJ}"_DTI_fm.nii "${SUBJ}"_DTI_fm.mif
  dwidenoise "${SUBJ}"_DTI_fm.mif "${SUBJ}"_DTI_fm_den.mif -noise "${SUBJ}"_DTI_noise.mif
  mrcalc "${SUBJ}"_DTI_fm.mif "${SUBJ}"_DTI_fm_den.mif -subtract "${SUBJ}"_DTI_residual.mif
  mrdegibbs "${SUBJ}"_DTI_fm_den.mif "${SUBJ}"_DTI_fm_den_deg.mif
  mrconvert -quiet "${SUBJ}"_DTI_fm_den_deg.mif "${SUBJ}"_DTI_fm_den_deg.nii.gz
}

# 0 1 for A>>P phase encoding
create_acqp_index() {
  printf "0 0 0 0.05" >> "${FSL_PROC}"/acqparams.txt
  indx=""
  for ((i=1; i<=56; i+=1)); do indx="$indx 1"; done
  echo "$indx" > index.txt
}

make_mask() {
  fslroi "${SUBJ}"_DTI_fm.nii.gz "${SUBJ}"_DTI_fm_1b0.nii.gz 0 1
  fslmaths "${SUBJ}"_DTI_fm_1b0.nii.gz -bin "${SUBJ}"_DTI_fm_mask.nii.gz
}

eddy() {
  if [[ $(command -v nvcc) ]]; then
    printf "\\033[1;33m%s\\033[m\\n" "I'm David Pumpkins!  And I found your CUDA installation!  be bop boo boo bop be be bo bop... Any questions???"
    printf "\\nRunning eddy_cuda...\\n\\n"
    eddy_cuda --imain="${SUBJ}"_DTI_fm_den_deg --mask="${SUBJ}"_DTI_fm_mask --acqp=acqparams.txt --index=index.txt \
    --bvecs="${SUBJ}"_DTI.bvec --bvals="${SUBJ}"_DTI.bval --repol --out="${SUBJ}"_DTI_fm_den_deg_eddy
  else
    printf "\\033[1;33m%s\\033[m\\n" "I'm Kevin Roberts! And I got a very important question!  Can a bitch get a graphics card???"
    printf "\\nRunning eddy_openmp...\\n\\n"
    eddy_openmp --imain="${SUBJ}"_DTI_fm_den_deg --mask="${SUBJ}"_DTI_fm_mask --acqp=acqparams.txt --index=index.txt \
    --bvecs="${SUBJ}"_DTI.bvec --bvals="${SUBJ}"_DTI.bval --repol --out="${SUBJ}"_DTI_fm_den_deg_eddy
  fi
}

dti_fit() {
  # dtifit -k "${SUBJ}"_DTI_fm_den_deg_eddy -o "${SUBJ}"_dti_fit -m "${SUBJ}"_DTI_fm_mask.nii.gz -r "${SUBJ}"_DTI.bvec -b "${SUBJ}"_DTI.bval
  dtifit -k "${SUBJ}"_DTI_fm_den_deg -o "${SUBJ}"_dti_fit -m "${SUBJ}"_DTI_fm_mask.nii.gz -r "${SUBJ}"_DTI.bvec -b "${SUBJ}"_DTI.bval
}

######MAIN######

main() {
  parse_subjs

  for SUBJ in "${subj_array[@]}"; do
    subj_start
    make_proc_dir
    proc_prep
    pushd "${FSL_PROC}" || continue
    denoise
    create_acqp_index
    make_mask
    eddy
    dti_fit
  done
}

main