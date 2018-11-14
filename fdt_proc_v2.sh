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

  DWIPROC="dwi_processing"
  INPUT_DIR=$STUDY_DIR/$SUBJECT/dicoms
  OUTPUT_DIR=$STUDY_DIR/$SUBJECT/$DWIPROC
  raw_dir=$OUTPUT_DIR/raw
  topup_dir=$OUTPUT_DIR/topup
  pepositive="pepolar0"
  penegative="pepolar1"
  hyperband="HB2"

  # Making output directory and sub-directories.  If the specified output directory exists, remove it and make a new one.
  if [ -d "$OUTPUT_DIR" ] ; then
     rm -rf "$OUTPUT_DIR"
  fi

  mkdir -p "$OUTPUT_DIR"
  mkdir "${OUTPUT_DIR}"/raw
  mkdir "${OUTPUT_DIR}"/topup

  if [ ! -d "$OUTPUT_DIR" ]; then
    echo "ERROR: Failed to create output directory.  Do you have write permissions for the directory ${STUDY_DIR}/${SUBJECT}?"
    exit 1
  fi

  # Finding compressed raw DWI scan files in the input directory, converting them, and copying the conversion output to the 
  # "raw" subdirectory of the output directory.  Rename the scans according to their phase encoding direction (pepolar0 or pepolar1).
  # If the scans were created using hyperband, label the conversion files as such.

  if [[ "$HYPERBAND_OPT" == "Y" ]]; then
    pos_enc="NODDI_HB2_pepolar0"
    neg_enc="NODDI_HB2_pepolar1"
  else
    pos_enc="NODDI_pepolar0"
    neg_enc="NODDI_pepolar1"
  fi
  
  for file in "$INPUT_DIR"/*"${pos_enc}"*.tgz; do
    tmp_dir
    cp "$file" "$TMP"
    tar xf "$TMP"/"$(basename $file)" -C "$TMP" 
    dcm2niix -z y "$TMP"
    imcp "$TMP"/*.nii.gz "$OUTPUT_DIR"/raw/"$pos_enc".nii.gz
    #cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$pos_enc".bval - Must use the bval and bvec files from the scanner, values in dicoms are incorrect
    #cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$pos_enc".bvec
    cp "$TMP"/*.json "$OUTPUT_DIR"/raw/"$pos_enc".json
  done

  for file in "$INPUT_DIR"/*"${neg_enc}"*.tgz; do
    tmp_dir
    cp "$file" "$TMP"
    tar xf "$TMP"/"$(basename $file)" -C "$TMP" 
    dcm2niix -z y "$TMP"
    imcp "$TMP"/*.nii.gz "$OUTPUT_DIR"/raw/"$neg_enc".nii.gz
    #cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$neg_enc".bval
    #cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$neg_enc".bvec
    cp "$TMP"/*.json "$OUTPUT_DIR"/raw/"$neg_enc".json
  done

  #COMPUTE TOTAL READOUT TIME

  # Computing the total readout time in seconds, and up to six decimal places. Grab any
  # scan in the raw directory and get the second dimension (slice count if using PA/AP phase encoding)
  # using fslval.  Compute total readout time as: echo spacing *(slice count - 1).  Divide by 1000
  # to convert the value to seconds (from milliseconds )
  any_scan=$(find "${OUTPUT_DIR}"/raw/*.nii.gz | head -n 1)
  dims=$("${FSL_DIR}"/bin/fslval "${any_scan}" dim2)
  dimsmin1=$(awk "BEGIN {print $dims - 1; exit}" )
  totalrotime=$(awk "BEGIN {print ${ECHOSPACING}*${dimsmin1}; exit}" )
  totalrotime=$(awk "BEGIN {print ${totalrotime} / 1000; exit}" )


  #TOPUP

  #-Extract b0's and make acqparms.txt for topup
  for file in "${OUTPUT_DIR}"/raw/"${pos_enc}".nii.gz; do
    fslroi "${file}" "${OUTPUT_DIR}"/raw/pos_b0 0 4
    b0vols=$(${FSL_DIR}/bin/fslval "${OUTPUT_DIR}"/raw/pos_b0 dim4)
    for (( i=1; i<=b0vols; i++ )); do
      echo 0 1 0 "$totalrotime" >> "${OUTPUT_DIR}"/raw/acqparams.txt
    done
  done

  for file in "${OUTPUT_DIR}"/raw/"${neg_enc}".nii.gz; do
    fslroi "${file}" "${OUTPUT_DIR}"/raw/neg_b0 0 4
    b0vols=$(${FSL_DIR}/bin/fslval "${OUTPUT_DIR}"/raw/neg_b0 dim4)
    for (( i=1; i<=b0vols; i++ )); do
      echo 0 -1 0 "$totalrotime" >> "${OUTPUT_DIR}"/raw/acqparams.txt
    done
  done

  #-Merge separate b0 files 
  fslmerge -t "${OUTPUT_DIR}"/raw/pos_neg_b0 "${OUTPUT_DIR}"/raw/pos_b0 "${OUTPUT_DIR}"/raw/neg_b0


  #-copying necessary files to topup directory for further processing
  imcp "${raw_dir}"/pos_b0 "${topup_dir}"
  imcp "${raw_dir}"/neg_b0 "${topup_dir}"
  imcp "${raw_dir}"/pos_neg_b0 "${topup_dir}"
  cp "${raw_dir}"/acqparams.txt "${topup_dir}"

  #-Run topup using the combined b0 file
  topup -v --imain="${topup_dir}"/pos_neg_b0 --datain="${topup_dir}"/acqparams.txt --config=b02b0.cnf --out="${topup_dir}"/topup_pos_neg_b0

  #-Per HCP script (run_topup.sh), run applytopup to first b0 from positive and negative phase encodings to generate a hifib0 which will
  #-be used to create the brain mask.  
  fslroi "${topup_dir}"/pos_b0 "${topup_dir}"/pos_b0_1st 0 1
  fslroi "${topup_dir}"/neg_b0 "${topup_dir}"/neg_b0_1st 0 1

  dimt=$(fslval "${topup_dir}"/Pos_b0 dim4)
  dimt=$(("${dimt}" + 1))

  #-applytopup must use the jacobian modulation method (--method=jac) since the diffusion gradients do not match one-to-one across the phase encodings
  applytopup --imain="${topup_dir}"/pos_b0_1st,"${topup_dir}"/neg_b0_1st --method=jac --topup="${topup_dir}"/topup_pos_neg_b0 --datain="${topup_dir}"/acqparams.txt --inindex=1,"${dimt}" --out="${topup_dir}"/hifib0
 
  bet "${topup_dir}"/hifib0 "${topup_dir}"/nodif_brain -m -f 0.2

  #EDDY

  #-Converting the crappy diffusion vector and diffusion weight files we get from the scanner
  
  #--Starting with the vectors first....
  #---Getting the number of columns in the vector file as "numcols"
  numcols=$(($(head -n 1 "$BVEC_PATH" | grep -o " " | wc -l) + 1))

  #---Starting with the third column (the first containing coordinates), loop over the remaining columns, and for each one cut it, remove the last entry
  #---(which is a volume that doesn't exist), then echo it into a new text file.  The last step will transpose it from a column to a space-delimited row) 
  
  for file in "${BVEC_PATH}"

  #???? How the fuck do I properly rename the files ????  Need to parse the info file for the scan, get the time value for each scan, reformat them,
  #and then match them to each file.  FML.

  for ((i=3;i<="$NUMC";i++)); do 
      TEMP=$(cut -d" " -f"$i" "$BVEC_PATH")
      TEMP=$(awk '{$NF=""}1' <(echo $TEMP))
      echo $TEMP >> "$OUTPUT"
      #TEMP=$(paste -s -d" " <(echo "$TEMP"))
      #TEMP=$(awk '{$NF=""}1'); 
      #echo "$TEMP" >> "$OUTPUT"."$TYPE"
  done
}

main "$@"