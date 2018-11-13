#!/usr/bin/env bash

usage() {
  cat << EOF
    Usage: fdt_proc.sh PARAMETER...

    PARAMETERS:

    --i=<input-file> 
    --o=<output-file>
  
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
        INPUT=${argument#*=}
        index=$(( index + 1 ))
        ;;
      --o=*)
        OUTPUT=${argument#*=}
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
    NUMC=$(($(head -n 1 "$INPUT" | grep -o " " | wc -l) + 1))
    for ((i=3;i<="$NUMC";i++)); do 
        TEMP=$(cut -d" " -f"$i" "$INPUT")
        TEMP=$(awk '{$NF=""}1' <(echo $TEMP))
        echo $TEMP >> "$OUTPUT"
        #TEMP=$(paste -s -d" " <(echo "$TEMP"))
        #TEMP=$(awk '{$NF=""}1'); 
        #echo "$TEMP" >> "$OUTPUT"."$TYPE"
    done
    
}

main "$@"