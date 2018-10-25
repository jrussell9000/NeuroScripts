#!/bin/bash
# JD Russell 2018
# Convert anatomical, DWI, and field maps from multiple subjects using Rorden's dcm2niix (mostly)

while getopts 'i:o:' args; do
  case "${args}" in
    i)
      RAW_INPUT_DIR=${OPTARG}
      ;;
    o)
      DATASET_DIR=${OPTARG}
      ;;
    *)
      ;;
  esac
done

######GLOBALS######
FMRITOOLS_PATH="/Users/jdrussell3/brave_scripts/fmri_tools-current/apps"

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

tmp_dir() {
  rand=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 8 | head -n 1)
  TMP=/tmp/proc_conv-${rand}
  mkdir "${TMP}"
}

decompress() {
  for z in "${TMP_PATH}"/"$1"/*.bz2; do
    bzip2 -d "$z"
  done
}

make_proc_dirs() {
  SUBJ_PATH="${DATASET_DIR}"/"${SUBJ}"
  rm -rf "${SUBJ_PATH}"
  mkdir -p "${SUBJ_PATH}"
  mkdir -p "${SUBJ_PATH}"/ANAT
  mkdir -p "${SUBJ_PATH}"/DTI
  mkdir -p "${SUBJ_PATH}"/FMAP
  mkdir -p "${SUBJ_PATH}"/INFO
  TMP_PATH="${TMP}"/"${SUBJ}"
  mkdir -p "${TMP_PATH}"
  mkdir -p "${TMP_PATH}"/ANAT
  mkdir -p "${TMP_PATH}"/DTI
  mkdir -p "${TMP_PATH}"/FMAP
  mkdir -p "${TMP_PATH}"/INFO
}

start_subj() {
  blink=$(tput blink)$(tput setaf 1)
  normal=$(tput sgr0)
  SUBJ_F=${blink}${SUBJ}${normal}
  printf "\\n%s" "//////////////////////////////////////////"
  printf "\\n%s" "//-------NOW CONVERTING SUBJECT #-------//"
  printf "\\n%s" "//------------------$SUBJ_F-----------------//"  
  printf "\\n%s\\n" "//////////////////////////////////////////"
}

cp_info() {
  cp "${RAW_INPUT_DIR}"/*"${SUBJ}"/dicoms/info.txt "${SUBJ_PATH}"/INFO/"${SUBJ}"_info.txt;
}

convert_t1() {
  printf "\\n%s\\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
  printf "%s" "~~~~~CONVERTING ANATOMICAL SCANS~~~~~~"
  printf "\\n%s\\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
  printf "\\n%s\\n\\n" "--------------T1 (BRAVO)--------------"
  for SCAN in "${RAW_INPUT_DIR}"/*"${SUBJ}"/dicoms/*bravo; do
    #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
    if [ -d "${SCAN}" ]; then
      rsync -rq "${SCAN}"/*.bz2 "${TMP_PATH}"/T1
      decompress T1
      dcm2niix -b y -f "${SUBJ}"_T1 -o "${SUBJ_PATH}"/ANAT/ "${TMP_PATH}"/T1
    fi
  done
}

convert_t2() {
  printf "\\n%s\\n\\n" "--------------T2 (3DIR)--------------"
  for SCAN in "${RAW_INPUT_DIR}"/*"${SUBJ}"/dicoms/*3dir; do
    #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
    if [ -d "${SCAN}" ]; then
      rsync -rq "${SCAN}"/*.bz2 "${TMP_PATH}"/T2
      decompress T2
      dcm2niix -b y -f "${SUBJ}"_T2 -o "${SUBJ_PATH}"/ANAT/ "${TMP_PATH}"/T2/
    fi
  done
}

convert_fmap() {
  printf "\\n%s\\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
  printf "%s" "~~~~~~~~~~MAKING FIELDMAPS~~~~~~~~~"
  printf "\\n%s\\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

  for SCAN in "${RAW_INPUT_DIR}"/*"${SUBJ}"/dicoms/*fmap; do
    if [ -d "${SCAN}" ]; then
      #Problem: Multiple fieldmap directories exist for each subject
      #Solution: Parse each subjects info.txt file to determine which is which
      IMAGE_DESC=$(grep -A 2 "$(basename "$SCAN")" "${RAW_INPUT_DIR}"/*"${SUBJ}"/dicoms/info.txt | tail -n 1 )
      
      case "$IMAGE_DESC" in
        *DTI*)
          MAPTYPE=DTI
          #mkdir -p "${TMP_PATH}"/FMAP/"${MAPTYPE}"
          ;;
        *EPI*)
          continue
          ;;
      #  *EPI*)
      #    MAPTYPE=EPI
      #    mkdir -p "${TMP_PATH}"/FMAP/"${MAPTYPE}"
      #    ;;
      esac
      ###! MUST COPY .YAML AND PICKLE FILES (i.e., entire scan directory)!
      ###! If yaml and pickle files aren't there, make_fmap will try to read scan info from dicom headers, 
      ###! but this function doesn't work properly, and the script will fail (took 2 days to figure this out)
      cp -fr "${SCAN}" "${TMP_PATH}"/FMAP/
      # cp -fr "${SCAN}" "${TMP_PATH}"/FMAP/"${MAPTYPE}"
      decompress FMAP/"$(basename "${SCAN}")"
      # Using local, corrected version of make_fmap.py (original is very buggy)
      "${FMRITOOLS_PATH}"/make_fmap.py "${TMP_PATH}"/FMAP/"$(basename "$SCAN")" "${SUBJ_PATH}"/FMAP/"${SUBJ}"_"${MAPTYPE}"_FMAP.nii 
      # Option to register fieldmap to T1: --anat "${SUBJ_PATH}"/ANAT/"${SUBJ}"_T1.nii
      # Don't use dcm2niix to convert field maps (doesn't work well)
      # dcm2niix -b y -z y -m y -f ${i}_${SCANTYPE}_FMAP_${MAPTYPE} -o ${SUBJ_DIR}/FMAP/ /tmp/"${scanpath##*/}"
    fi
  done
}

convert_dti() {
  printf "\\n%s\\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
  printf "%s" "~~~~~~~~CONVERTING DTI SCANS~~~~~~~~~~"
  printf "\\n%s\\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

  for SCAN in "${RAW_INPUT_DIR}"/*"${SUBJ}"/dicoms/*dti; do
    if [ -d "${SCAN}" ]; then
      cp -fr "${SCAN}"/*.bz2 "${TMP_PATH}"/DTI
      decompress DTI
      dcm2niix -b y -f "${SUBJ}"_DTI -o "${SUBJ_PATH}"/DTI/ "${TMP_PATH}"/DTI/
    fi
  done
}

correct_dti() {
  #Using local version of fieldmap_correction.py - the version in Vol\apps has a bug
  #Echo spacing time of .568ms taken from dcm2niix JSON file, which specifies it as 0.000568s
  "${FMRITOOLS_PATH}"/fieldmap_correction.py --beautify --dti "${SUBJ_PATH}"/FMAP/"${SUBJ}"_DTI_FMAP.nii .568 "${SUBJ_PATH}"/DTI "${SUBJ_PATH}"/DTI/001_DTI.nii
}

mv_to_local() {
  if ! rsync -r --progress "${SUBJ_PATH}" jdrussell3@braveyouthlab1329.psychiatry.local:/home/jdrussell3/proc; then
    echo "Subject transfer failed."
  else
    echo "Subject ${SUBJ} transfered successfully"
    rm -rf "${SUBJ_PATH}"
  fi
}

######MAIN######
parse_subjs
tmp_dir
for SUBJ in "${subj_array[@]}"; do
  set +f
  start_subj
  make_proc_dirs "${SUBJ}"
  cp_info
  convert_t1
  convert_t2
  convert_fmap
  convert_dti
  correct_dti
  rm -rf "${TMP_PATH}"
  mv_to_local
done
rm -rf "${TMP}"
