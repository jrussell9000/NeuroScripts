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
    --hyperband=<Y/N>         are we processing hyperband scans?

    --bvecs=<bvecs-path>      location of original bvecs file from the scanner
                              to be converted to FSL format
    --bvals=<bvals-path>      location of original bvals file from the scanner
                              to be converted to FSL format
  
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
      --hyperband=*)
        HYPERBAND_OPT=${argument#*=}
        index=$(( index + 1 ))
        ;;
      --bvecs=*)
        BVEC_PATH=${argument#*=}
        index=$(( index + 1))
        ;;
      --bvals=*)
        BVAL_PATH=${argument#*=}
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

  if [ -z "${HYPERBAND_OPT}" ] ; then
    error_msgs+="ERROR: Hyperband option not defined.  Please indictate Y or N as to whether the scans were obtained using hyperband."
  fi

  if [ -z "${BVEC_PATH}" ] ; then
    error_msgs+="ERROR: Location of original, unprocessed bvecs file (diffusion gradient vectors) not provided."
  fi

  if [ -z "${BVAL_PATH}" ] ; then
    error_msgs+="ERROR: Location of original, unprocessed bvals file (diffusion gradient weights) not provided."
  fi
  
  if [ -n "${error_msgs}" ] ; then
    usage
    echo -e "${error_msgs}"
    exit 1
  fi

  echo "Location of study files: $STUDY_DIR"
  echo "Performing operations for subjects: ${SUBJECT}"
}

# Make temporary directories for processing
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

# Parse provided subject lists
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
  pepositive="pepolar0"
  penegative="pepolar1"
  hyperband="HB2"

  # Making output directory and sub-directories.  If the specified output directory exists, remove it and make a new one.
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

  # Finding compressed raw DWI scan files in the input directory, converting them, and copying the conversion output to the 
  # "raw" subdirectory of the output directory.  Rename the scans according to their phase encoding direction (pepolar0 or pepolar1).
  # If the scans were created using hyperband, label the conversion files as such.

  for file in "$INPUT_DIR"/*.NODDI*.tgz; do
    if [[ "$HYPERBAND_OPT" == "Y" ]]; then
      if [[ "$file" == *"$pepositive"* && "$file" == *"$hyperband"* ]]; then
        tmp_dir
        cp "$file" "$TMP"
        tar xf "$TMP"/"$file" -C "$TMP"
        dcm2niix "$TMP"
        "${FSL_DIR}"/bin/imcp "$TMP"/*.nii "$OUTPUT_DIR"/raw/"$hyperband"_"$pepositive".nii
        cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$hyperband"_"$pepositive".bval
        cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$hyperband"_"$pepositive".bvec
        cp "$TMP"/*.json "$OUTPUT_DIR"/raw/"$hyperband"_"$pepositive".json
        rm -rf "$TMP"
      fi

      if [[ "$file" == *"$penegative"* && "$file" == *"$hyperband"* ]]; then
        tmp_dir
        cp "$file" "$TMP"
        tar xf "$TMP"/"$file" -C "$TMP"
        dcm2niix "$TMP"
        "${FSL_DIR}"/bin/imcp "$TMP"/*.nii "$OUTPUT_DIR"/raw/"$hyperband"_"$penegative".nii
        cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$hyperband"_"$penegative".bval
        cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$hyperband"_"$penegative".bvec
        cp "$TMP"/*.json "$OUTPUT_DIR"/raw/"$hyperband"_"$penegative".json
        rm -rf "$TMP"
      fi
    fi
    
    if [[ "$HYPERBAND_OPT" == "N" ]]; then
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
    fi
  done

  # Computing the total readout time in seconds, and up to six decimal places. Grab any
  # scan in the raw directory and get the second dimension (slice count if using PA/AP phase encoding)
  # using fslval.  Compute total readout time as: echo spacing *(slice count - 1).  Divide by 1000
  # to convert the value to seconds (from milliseconds )
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

  # Merge files
  fslmerge -t "${OUTPUT_DIR}"/raw/Pos_Neg_b0 "${OUTPUT_DIR}"/raw/Pos_b0 "${OUTPUT_DIR}"/raw/Neg_b0
  fslmerge -t "${OUTPUT_DIR}"/raw/Pos_Neg "${OUTPUT_DIR}"/raw/pepolar0 "${OUTPUT_DIR}"/raw/pepolar1

  ###!!!!!!!!!!DELETE DCM2NIIX CREATED BVAL AND BVEC FILES - REMOVE THIS SECTION ONCE STEVE PUTS CORRECT VALUES IN THE DICOM!!!!###
  rm "${OUTPUT_DIR}"/raw/*.bvec
  rm "${OUTPUT_DIR}"/raw/*.bval
  cp "${STUDY_DIR}"/"${SUBJECT}"/NODDI_pepolar0.bval "${OUTPUT_DIR}"/raw/"$pepositive".bval
  cp "${STUDY_DIR}"/"${SUBJECT}"/NODDI_pepolar0.bvec "${OUTPUT_DIR}"/raw/"$pepositive".bvec
  cp "${STUDY_DIR}"/"${SUBJECT}"/NODDI_pepolar1.bval "${OUTPUT_DIR}"/raw/"$penegative".bval
  cp "${STUDY_DIR}"/"${SUBJECT}"/NODDI_pepolar1.bvec "${OUTPUT_DIR}"/raw/"$penegative".bvec

}

main "$@"