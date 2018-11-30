#!/usr/bin/env bash

set -e 

usage() {
  cat << EOF

    Usage: fdt_proc.sh PARAMETER...

    PARAMETERS:

    Required:

    --studydir=<study-dir>    path to read/write location where raw scans exist 
                              and processed output will be placed
    --subject=<subject-id>    numeric subject ID. Should match the name of the 
                              directory containing the individual subject files
    --echospacing=<echo-spacing-in-ms>
                              echo spacing in milliseconds (e.g., .688)
    --hyperband=<Y/N>         are we processing hyperband scans?

    Optional:

    --gpuassist               use the GPU-enable functions in FSL and Freesurfer?

    --gradpack=<gradients-tar-file>      
                              path to the tar file containing original 
                              diffusion vector and diffusion weight 
                              (i.e., bvecs and bvals) from the scanner 
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

  while [ ${index} -lt "${numargs}" ] ; do
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
      --gpuassist)
        USEGPU="True"
        index=$(( index + 1 ))
        ;;
      --gradpack=*)
        GRADPACK=${argument#*=}
        index=$(( index + 1))
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
  GRADPACK=${GRADPACK/#\~/$HOME}
  FSL_DIR=$FSLDIR #Freesurfer sets this one way, FSL another....poTAYto poTAHto

  #Check for required variables, and echo an error message if they're missing
  local error_msgs=""

  if [ -z "${STUDY_DIR}" ] ; then
    error_msgs+="\\nERROR: <study-dir> not specified."
  fi

  if [ -z "${SUBJECT}" ] ; then
    error_msgs+="\\nERROR: <subject> not specified."
  fi

  if [ -z "${FSLDIR}" ] ; then
    error_msgs+="\\nERROR: FSLDIR environment variable not set.  Is FSL installed?"
  fi

  if [ -z "${HYPERBAND_OPT}" ] ; then
    error_msgs+="\\nERROR: Hyperband option not defined.  Please indictate Y or N as to whether the scans were obtained using hyperband."
  fi

  # if [ -z "${GRADPACK}" ] ; then
  #   error_msgs+="\\nERROR: Location of tar file containing original, unprocessed diffision gradient files not provided."
  # fi

  # if [ ! -f "${GRADPACK}" ] ; then
  #   error_msgs+="\\nERROR: Specified gradient file package is not a compressed file."
  # fi

  if [ -n "${error_msgs}" ] ; then
    usage
    echo -e "${error_msgs}"
    exit 1
  fi

  echo "Location of study files: $STUDY_DIR"
  echo "Performing operations for subject(s): ${SUBJECT}"
  echo "Gradients tar file path is: ${GRADPACK}"
}

# Make temporary directories for processing
tmp_dir() {
  unset rand
  unset TMP
  rand=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 8 | head -n 1)
  TMP=/tmp/proc_${rand}
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

  #PREPARATION

  #-Local variables
    DWIPROC="dwi_processing"
    INPUT_DIR="${STUDY_DIR}"/"${SUBJECT}"/dicoms
    OUTPUT_DIR=$STUDY_DIR/$SUBJECT/$DWIPROC

    if [[ "${HYPERBAND_OPT}" == "Y" || "${HYPERBAND_OPT}" == "y" ]]; then
      HYPERBAND=1
    elif [[ "${HYPERBAND_OPT}" == "N" || "${HYPERBAND_OPT}" == "n" ]]; then
      HYPERBAND=0
    else
      printf "\\nERROR: Hyperband flag value %s unrecognized.  Must be Y or N." "${HYPERBAND_OPT}" 
    fi

    #--GPU acceleration is disabled by
    if [ -z "${USEGPU}" ] ; then
      USEGPU="False"
    fi

  #-Making output directory and sub-directories.  If the specified output directory exists, remove it and make a new one.
    if [ -d "$OUTPUT_DIR" ] ; then
      rm -rf "$OUTPUT_DIR"
    fi

    mkdir -p "$OUTPUT_DIR"
    mkdir "${OUTPUT_DIR}"/anat
    mkdir "${OUTPUT_DIR}"/preproc
    mkdir "${OUTPUT_DIR}"/mrtrixproc

    if [ ! -d "$OUTPUT_DIR" ]; then
      printf "\\nERROR: Failed to create output directory. Do you have write permissions for the directory %s/%s" "${STUDY_DIR}" "${SUBJECT}"
      exit 1
    fi

  #-Making variables to hold output path directories
    anat_dir=$OUTPUT_DIR/anat
    preproc_dir=$OUTPUT_DIR/preproc
    mrtrixproc_dir=$OUTPUT_DIR/mrtrixproc

  #CONVERTING ANATOMICAL
  for file in "${INPUT_DIR}"/*MPRAGE*.tgz; do
    tmp_dir
    cp "$file" "$TMP"
    tar xf "$TMP"/"$(basename "${file}")" -C "$TMP" 
    dcm2niix -z y "$TMP"
    imcp "$TMP"/*.nii.gz "${anat_dir}"/T1.nii.gz
    #cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$pos_enc".bval - Must use the bval and bvec files from the scanner, values in dicoms are incorrect
    #cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$pos_enc".bvec
    cp "$TMP"/*.json "${anat_dir}"/T1.json
    rm -rf "${TMP}"
  done

  #-CONVERTING compressed raw DWI scan files in the input directory, and copying the conversion output to the 
  #-"raw" subdirectory of the output directory.  Rename the scans according to their phase encoding direction (pepolar0 or pepolar1).
  #-If the scans were created using hyperband, label the conversion files as such.
  #- pepolar0 is P>>A encoding (+1 in acqparams), pepolar1 is A>>P (-1)
  if [[ "${HYPERBAND}" = 1 ]]; then
    PostAnt="NODDI_HB2_pepolar0"
    AntPost="NODDI_HB2_pepolar1"
  elif [[ "${HYPERBAND}" = 0 ]]; then
    PostAnt="NODDI_pepolar0"
    AntPost="NODDI_pepolar1"
  fi
  
  printf "%s\\n\\n" "Beginning scan file conversion..."

  for file in "${INPUT_DIR}"/*"${PostAnt}"*.tgz; do
    tmp_dir
    cp "$file" "$TMP"
    tar xf "$TMP"/"$(basename "${file}")" -C "$TMP" 
    dcm2niix -z y "$TMP"
    imcp "$TMP"/*.nii.gz "${preproc_dir}"/"$PostAnt".nii.gz
    #cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$PostAnt".bval - Must use the bval and bvec files from the scanner, values in dicoms are incorrect
    #cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$PostAnt".bvec
    cp "$TMP"/*.json "${preproc_dir}"/"$PostAnt".json
    rm -rf "${TMP}"
  done

  for file in "${INPUT_DIR}"/*"${AntPost}"*.tgz; do
    tmp_dir
    cp "${file}" "${TMP}"
    tar xf "${TMP}"/"$(basename "${file}")" -C "${TMP}" 
    dcm2niix -z y "$TMP"
    imcp "$TMP"/*.nii.gz "${preproc_dir}"/"$AntPost".nii.gz
    #cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$AntPost".bval
    #cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$AntPost".bvec
    cp "$TMP"/*.json "${preproc_dir}"/"$AntPost".json
    rm -rf "${TMP}"
  done

  #-CONVERTING the crappy diffusion vector and diffusion weight files we get from the scanner
  if [ -n "${GRADPACK}" ]; then #----START raw gradient files conversion

    printf "\\nConverting raw gradient files..."

  #--UNPACKING the tar file to a temporary directory
    tmp_dir
    graddir_tmp="${TMP}"

    tar xf "${GRADPACK}" -C "${graddir_tmp}"
    if [[ $? != 0 ]]; then
      printf "\\nERROR: Could not unpack the gradient tar file - %s" "${GRADPACK}"
      exit 1
    fi
  
  #--TRIMMING the names of each file in the unpacked directory to "mmhhyy.{bval/bvec}""

  #---Locating the info file
      info_file=$(find "${INPUT_DIR}" -name "info*.txt" -printf '%P\n' | head -n 1)
      if [ -z "${info_file}" ]; then
        printf "\\nERROR: Scan info file (info.XXXXXX.txt) not found in gradient files path."
        exit 1
      else
        printf "\\nFound scan info file in gradient files path."
      fi

  #---Deleting unnecessary files, trimming the names of those we want to keep, and copying them to the raw_dir  
      printf "\\nRenaming and reformatting raw diffusion gradient files from the scanner..."
      for file in "${graddir_tmp}"/Research*.txt; do
        if [[ $file == *bvals2* || $file == *orientations2* || $file == *diff_amp* ]]; then
          rm "${file}"
        fi
        if [[ $file == *bvals_* ]]; then
          fname=$(basename "${file%.*}" | cut -c32- | sed -e 's/_m//' -e 's/_s//' -e 's/h//')
          mv "${file}" "${graddir_tmp}"/"${fname}".bval
        elif [[ $file == *orientations_* ]]; then
          fname=$(basename "${file%.*}" | cut -c39- | sed -e 's/_m//' -e 's/_s//' -e 's/h//')
          mv "${file}" "${graddir_tmp}"/"${fname}".bvec
        fi
      done

  #---Parsing the info file and getting any lines containing "NODDI" and the three below them 
  #---then echo each pair of SeriesDescription and AcquisitionTime values to a file, 'seq_times.txt'
      parse_list=$(grep -A3 "NODDI" "${INPUT_DIR}"/"${info_file}")
      echo "$parse_list" | awk 'BEGIN {RS="--"} {print ($2" "$8)}' > "${graddir_tmp}"/seq_times.txt

  #---For each line of 'seq_times.txt', save the first field as variable $seq, 
  #---and the second field as variable $time (without the seconds, which don't always match)
      while read -r line; do
        seq=$(echo "${line}" | cut -f1 -d" ")
        time=$(echo "${line}" | cut -f2 -d" " | cut -c-4)
        #----For each bval file, if the file name matches the $time variable, rename it as the $seq variable
        for bvalfile in "${graddir_tmp}"/*.bval; do
          if [[ "${bvalfile}" == *"${time}"* ]]; then
              mv "${bvalfile}" "${graddir_tmp}"/"${seq}".bval
          fi
        done
        #----For each bvec file, if the file name matches the $time variable, rename it as the $seq variable
        for bvecfile in "${graddir_tmp}"/*.bvec; do 
          if [[ "${bvecfile}" == *"${time}"* ]]; then
              mv "${bvecfile}" "${graddir_tmp}"/"${seq}".bvec
          fi
        done
      done < "${graddir_tmp}"/seq_times.txt

  #--REFORMATTING each file to the FSL scheme...

  #---For each .bvec file, get the number of columns in the file, then loop across them starting with the third (the first two are just labels)
  #---For each column in the loop, cut it, remove the last entry (extra line of zeros), echo it to transpose from a column to a row and append it to a temp file
  #---When the loop is over, replace the original .bvec file with the newly formatted temp file
      for bvecfile in "${graddir_tmp}"/*.bvec; do
        numc=$(($(head -n 1 "$bvecfile" | grep -o " " | wc -l) + 1))
        for ((i=3;i<="$numc";i++)); do 
          TEMP=$(cut -d" " -f"$i" "$bvecfile")
          TEMP=$(awk '{$NF=""}1' <(echo ${TEMP} )) #Do NOT double quote
          echo "${TEMP}" >> temp.txt
        done
        mv temp.txt "${bvecfile}"
        cp "${bvecfile}" "${preproc_dir}"
      done

  #---For each .bval file, grab the third column (first two are just labels), remove the last row (extra line of zeros)
  #---Echo it to tranpose from a column to a row, then export it to a temp file.  Rename the temp file with the original bval
      for bvalfile in "${graddir_tmp}"/*.bval; do
        TEMP=$(cut -d" " -f"3" "$bvalfile")
        TEMP=$(awk -F" " '{NF--; print}' <(echo ${TEMP} )) #Do NOT double quote
        echo "${TEMP}" > temp.txt
        mv temp.txt "${bvalfile}"
        cp "${bvalfile}" "${preproc_dir}"
      done
  else #If we don't need to convert the raw scan
    cp "${STUDY_DIR}"/diff_files/"${PostAnt}".b* "${STUDY_DIR}"/diff_files/"${AntPost}".b* "${preproc_dir}"
  fi #----END raw gradient files conversion

  #COMPUTING TOTAL READOUT TIME

  #-Computing the total readout time in seconds, and up to six decimal places. Grab any
  #-scan in the raw directory and get the second dimension (slice count if using PA/AP phase encoding)
  #-using fslval.  Compute total readout time as: echo spacing *(slice count - 1).  Divide by 1000
  #-to convert the value to seconds (from milliseconds )
    any_scan=$(find "${preproc_dir}"/*.nii.gz | head -n 1)
    dims=$("${FSL_DIR}"/bin/fslval "${any_scan}" dim2)
    dimsmin1=$(awk "BEGIN {print $dims - 1; exit}" )
    totalrotime=$(awk "BEGIN {print ${ECHOSPACING}*${dimsmin1}; exit}" )
    totalrotime=$(awk "BEGIN {print ${totalrotime} / 1000; exit}" )

  #DENOISE & DEGIBBS

  printf "\\nRemoving scan noise and Gibbs' rings using MRTrix3's dwidenoise and mrdegibbs tools..."
  for file in "${preproc_dir}"/*.nii.gz; do
    basename=$(imglob "${file}")
    dwidenoise "${basename}".nii.gz "${basename}"_den.nii.gz
    if [[ $! = 1 ]]; then
      echo "ERROR: Denoising of scan file ${basename}.nii.gz failed."
      exit 1
    fi
    mrdegibbs "${basename}"_den.nii.gz "${basename}"_den_deg.nii.gz
    if [[ $! = 1 ]]; then
      echo "ERROR: Gibbs ring removal on scan file ${basename}.nii.gz failed."
      exit 1
    else
      rm "${basename}".nii.gz
      rm "${basename}"_den.nii.gz
      mv "${basename}"_den_deg.nii.gz "${preproc_dir}"/"$(basename "$file")"
    fi
  done

  #TOPUP

  #-Extract b0's and make acqparms.txt for topup
    printf "\\nExtracting b0 scans from PA encoded volume and adding info to acqparams.txt for topup..."
    for file in "${preproc_dir}"/*"${PostAnt}".nii.gz; do
      fslroi "${file}" "${preproc_dir}"/PA_b0 0 1
      b0vols=$("${FSL_DIR}"/bin/fslval "${preproc_dir}"/PA_b0 dim4)
      for (( i=1; i<=b0vols; i++ )); do
        echo 0 1 0 "${totalrotime}" >> "${preproc_dir}"/acqparams.txt
      done
    done

    printf "\\nExtracting b0 scans from AP encoded volume and adding info to acqparams.txt for topup..."
    for file in "${preproc_dir}"/*"${AntPost}".nii.gz; do
      fslroi "${file}" "${preproc_dir}"/AP_b0 0 1
      b0vols=$("${FSL_DIR}"/bin/fslval "${preproc_dir}"/AP_b0 dim4)
      for (( i=1; i<=b0vols; i++ )); do
        echo 0 -1 0 "${totalrotime}" >> "${preproc_dir}"/acqparams.txt
      done
    done

    printf "\\nMerging b0 scans from PA and PA phase encoding volumes..."
  
  #-Merge separate b0 files 
    fslmerge -t "${preproc_dir}"/PA_AP_b0 "${preproc_dir}"/PA_b0 "${preproc_dir}"/AP_b0 

  #-Call TOPUP script
    scriptdir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
    sh "${scriptdir}"/runtopup.sh "${preproc_dir}"

  #EDDY

  #--Creating the index files for eddy
    PAvolcnt=$(fslval "${preproc_dir}"/"${PostAnt}" dim4)
    APvolcnt=$(fslval "${preproc_dir}"/"${AntPost}" dim4)

    for (( i=1; i<=PAvolcnt; i++ )); do
      indcnt=1
      echo $indcnt >> "${preproc_dir}"/index.txt
    done

    for (( i=1; i<=APvolcnt; i++ )); do
      indcnt=2
      echo $indcnt >> "${preproc_dir}"/index.txt
    done

  #--Merging the PA and AP phase encoded scan series into one file
    fslmerge -t "${preproc_dir}"/PA_AP "${preproc_dir}"/"${PostAnt}" "${preproc_dir}"/"${AntPost}"

  #--Merging the gradient files 
    paste "${preproc_dir}"/"${PostAnt}".bval "${preproc_dir}"/"${AntPost}".bval > "${preproc_dir}"/PA_AP.bval
    paste "${preproc_dir}"/"${PostAnt}".bvec "${preproc_dir}"/"${AntPost}".bvec > "${preproc_dir}"/PA_AP.bvec
  
  #-Calling EDDY script

    sh "${scriptdir}"/runeddy.sh ${preproc_dir} ${USEGPU}

  #BIAS CORRECTION
  mrconvert -fslgrad "${preproc_dir}"/PA_AP.bvec "${preproc_dir}"/PA_AP.bval "${preproc_dir}"/eddy_unwarped_images.nii.gz "${preproc_dir}"/eddy_unwarped_images.mif
  dwibiascorrect -ants "${preproc_dir}"/eddy_unwarped_images.mif "${mrtrixproc_dir}"/dwi.mif

  #GO TO MRTRIX3
  sh "${scriptdir}"/multifiber.sh ${mrtrixproc_dir} ${anat_dir}

}

main "$@"