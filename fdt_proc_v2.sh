#!/usr/bin/env bash


set -e 

usage() {
  cat << EOF
    Usage: fdt_proc.sh PARAMETER...

    PARAMETERS:

    --studydir=<study-dir>    path to read/write location where raw scans exist 
                              and processed output will be placed
    --subject=<subject-id>    numeric subject ID. Should match the name of the 
                              directory containing the individual subject files
    --echospacing=<echo-spacing-in-ms>
                              echo spacing in milliseconds (e.g., .688)
  
EOF
}

get_options() {

  local arguments=($@)
  unset STUDY_DIR
  unset SUBJECT

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
      --echospacing=*)
        ECHOSPACING=${argument#*=}
        index=$(( index + 1 ))
        ;;
      *)
        usage
        echo "ERROR: Option ${argument} not recognized."
        exit 1
        ;;
    esac
  done

  # Replace '~' with $HOME
  STUDY_DIR=${STUDY_DIR/#\~/$HOME}
  
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

  if [ -n "${error_msgs}" ] ; then
    usage
    echo -e "${error_msgs}"
    exit 1
  fi

  echo "Location of study files: $STUDY_DIR"
  echo "Performing operations for subjects: ${SUBJECT}"
}

tmp_dir() {
  if [ -d "${TMP}" ]; then
    rm -rf "${TMP}"
  fi
  unset rand
  unset TMP
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

  get_options "$@"

  DWIPROC="DWI_processing"
  INPUT_DIR=$STUDY_DIR/$SUBJECT/dicoms
  OUTPUT_DIR=$STUDY_DIR/$SUBJECT/$DWIPROC

  if [ -d "$OUTPUT_DIR" ] ; then
     rm -rf "$OUTPUT_DIR"
  fi

  mkdir -p "$OUTPUT_DIR"
  mkdir "${OUTPUT_DIR}"/original
  mkdir "${OUTPUT_DIR}"/raw

  if [ ! -d "$OUTPUT_DIR" ]; then
    echo "ERROR: Failed to create output directory.  Do you have write permissions for the directory ${STUDY_DIR}/${SUBJECT}?"
    exit 1
  fi

  pepositive="pepolar0"
  penegative="pepolar1"

  for file in "$INPUT_DIR"/*.NODDI_pepolar*.tgz; do
    if [[ "$file" == *"$pepositive"* ]]; then
      tmp_dir
      cp "$file" "$TMP"
      tar xf "$TMP"/*.tgz -C "$TMP"
      dcm2niix "$TMP"
      "${FSL_DIR}"/bin/imcp "$TMP"/*.nii "$OUTPUT_DIR"/raw/"$pepositive".nii
      cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$pepositive".bval
      cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$pepositive".bvec
      cp "$TMP"/*.json "$OUTPUT_DIR"/raw/"$pepositive".json
      rm -rf "$TMP"
    fi

    if [[ "$file" == *"$penegative"* ]]; then
      tmp_dir
      cp "$file" "$TMP"
      tar xf "$TMP"/*.tgz -C "$TMP"
      dcm2niix "$TMP"
      "${FSL_DIR}"/bin/imcp "$TMP"/*.nii "$OUTPUT_DIR"/raw/"$penegative".nii
      cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$penegative".bval
      cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$penegative".bvec
      cp "$TMP"/*.json "$OUTPUT_DIR"/raw/"$penegative".json
      rm -rf "$TMP"
    fi
  done

  # Computing total readout time in seconds, and up to six decimal places

  # Grab a scan in the raw directory and get the second dimension using fslval (if PA/AP)
  any_scan=$(find "${OUTPUT_DIR}"/raw/*.nii.gz | head -n 1)
  dims=$("${FSL_DIR}"/bin/fslval "${any_scan}" dim2)
  dimsmin1=$(awk "BEGIN {print $dims - 1; exit}" )
  totalrotime=$(awk "BEGIN {print ${ECHOSPACING}*${dimsmin1}; exit}" )
  totalrotime=$(awk "BEGIN {print ${totalrotime} / 1000; exit}" )

  # Extract b0's and make acqparms.txt for topup
  for file in "${OUTPUT_DIR}"/raw/"${pepositive}".nii.gz; do
    fslroi "${file}" "${OUTPUT_DIR}"/raw/Pos_b0 0 4
    b0vols=$(${FSL_DIR}/bin/fslval "${OUTPUT_DIR}"/raw/Pos_b0 dim4)
    for (( i=1; i<=b0vols; i++ )); do
      echo 0 1 0 "$totalrotime" >> "${OUTPUT_DIR}"/raw/acqparms.txt
    done
  done

  for file in "${OUTPUT_DIR}"/raw/"${penegative}".nii.gz; do
    fslroi "${file}" "${OUTPUT_DIR}"/raw/Neg_b0 0 4
    b0vols=$(${FSL_DIR}/bin/fslval "${OUTPUT_DIR}"/raw/Neg_b0 dim4)
    for (( i=1; i<=b0vols; i++ )); do
      echo 0 -1 0 "$totalrotime" >> "${OUTPUT_DIR}"/raw/acqparms.txt
    done
  done

  #
}

main "$@"