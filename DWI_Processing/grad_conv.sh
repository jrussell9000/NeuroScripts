#!/usr/bin/env bash

usage() {
  cat << EOF
    Usage: fdt_proc.sh PARAMETER...

    PARAMETERS:

    --i=<gradinfo-path> 

EOF
}

get_options() {

  local arguments=("$@")
  unset INPUT
  unset OUTPUT

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
      --i=*)
        GRADINFO_PATH=${argument#*=}
        index=$(( index + 1 ))
        ;;
      *)
        usage
        echo "ERROR: Option ${argument} not recognized."
        exit 1
        ;;
    esac
  done
}

main() {
  get_options "$@"

  for file in "${GRADINFO_PATH}"/*.txt; do
    if [[ $file == *bvals2* || $file == *orientations2* || $file == *diff_amp* ]]; then
      #echo "Removing $file"
      rm "${file}"
    fi
    if [[ $file == *bvals_* ]]; then
      fname=$(basename "${file%.*}" | cut -c32- | sed -e 's/_m//' -e 's/_s//' -e 's/h//')
      mv "${file}" "${GRADINFO_PATH}"/"${fname}".bval
    elif [[ $file == *orientations_* ]]; then
      fname=$(basename "${file%.*}" | cut -c39- | sed -e 's/_m//' -e 's/_s//' -e 's/h//')
      mv "${file}" "${GRADINFO_PATH}"/"${fname}".bvec
    fi
  done

  INPUT_DIR="/home/justin/ceda_scans/_9997/dicoms"
  info_file=$(find ${INPUT_DIR} -maxdepth 1 -name "*.txt" -printf '%P\n')
  echo $INPUT_DIR
  echo $info_file
  parse_list=$(cat ${INPUT_DIR}/${info_file} | grep -A3 "NODDI")
  echo "$parse_list" | awk 'BEGIN {RS="--"} {print ($2" "$8)}' > seq_times.txt

  while read -r line; do
    seq=$(echo "${line}" | cut -f1 -d" ")
    time=$(echo "${line}" | cut -f2 -d" " | cut -c-4)
    echo "$seq"
    echo "$time"
    for bvalfile in $(find "$GRADINFO_PATH" -name "*.bval" -printf '%P\n'); do
      if [[ "${bvalfile}" == *"${time}"* ]]; then
          mv "${bvalfile}" "${seq}".bval
      fi
    done
    for bvecfile in $(find "$GRADINFO_PATH" -name "*.bvec" -printf '%P\n'); do
      if [[ "${bvecfile}" == *"${time}"* ]]; then
          mv "${bvecfile}" "${seq}".bvec
      fi
    done
  done < seq_times.txt

  #rm seq_times.txt
    
  #Now we need to reformt each vector and weight file...

  # #---Starting with the third column (the first containing coordinates), loop over the remaining columns, and for each one cut it, remove the last entry
  # #---(which is a volume that doesn't exist), then echo it into a new text file.  The last step will transpose it from a column to a space-delimited row) 
  for bvecfile in $(find $GRADINFO_PATH -name "*.bvec" -printf '%P\n'); do
    numc=$(($(head -n 1 "$bvecfile" | grep -o " " | wc -l) + 1))
    for ((i=3;i<="$numc";i++)); do 
      TEMP=$(cut -d" " -f"$i" "$bvecfile")
      TEMP=$(awk '{$NF=""}1' <(echo $TEMP))
      echo $TEMP >> temp.txt
    done
    mv temp.txt $bvecfile
  done

  for bvalfile in $(find "${GRADINFO_PATH}" -name "*.bval" -printf '%P\n'); do
    TEMP=$(cut -d" " -f"3" "$bvalfile")
    TEMP=$(awk -F" " '{NF--; print}' <(echo $TEMP))
    echo $TEMP > temp.txt
    mv temp.txt $bvalfile
  done

}

main "$@"