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

  echo $GRADINFO_PATH

  for file in "${GRADINFO_PATH}"/*.txt; do
    echo $file
    if [[ $file == *bvals2* || $file == *orientations2* || $file == *diff_amp* ]]; then
      echo "Removing $file"
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


  # NUMC=$(($(head -n 1 "$INPUT" | grep -o " " | wc -l) + 1))

  # for ((i=3;i<="$NUMC";i++)); do 
  #   TEMP=$(cut -d" " -f"$i" "$INPUT")
  #   TEMP=$(awk '{$NF=""}1' <(echo $TEMP))
  #   echo $TEMP >> "$OUTPUT"
  #   #TEMP=$(paste -s -d" " <(echo "$TEMP"))
  #   #TEMP=$(awk '{$NF=""}1'); 
  #   #echo "$TEMP" >> "$OUTPUT"."$TYPE"
  # done
    
}

main "$@"