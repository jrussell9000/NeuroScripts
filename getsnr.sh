#!/usr/bin/env bash
set -e 

usage() {
  cat << EOF

    Usage: getsnr.sh PARAMETER...

    PARAMETERS:

    Required:

    --eddyoutput=<eddyoutput.nii.gz>   

    --anatomical=<T1.nii.gz>
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
      --eddyoutput=*)
        EDDYOUTPUT=${argument#*=}
        index=$(( index + 1 ))
        ;;      
      --anatomical=*)
        ANAT=${argument#*=}
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
  FSL_DIR="$FSLDIR" #Freesurfer sets this one way, FSL another....poTAYto poTAHto

  #Check for required variables, and echo an error message if they're missing
  local error_msgs=""

  if [ -z "${EDDYOUTPUT}" ] ; then
    error_msgs+="\\nERROR: Eddy output file not provided."
  fi

  if [ -z "${ANAT}" ] ; then
    error_msgs+="\\nERROR: Anatomical scan file not provided."
  fi

  if [ -n "${error_msgs}" ] ; then
    usage
    echo -e "${error_msgs}"
    exit 1
  fi
}

main() {
  get_options "$@"
  CWD=$(dirname "$EDDYOUTPUT")
  SNRDIR="$CWD"/snrcalc
  if [ -d "$SNRDIR" ] ; then
    rm -rf "$SNRDIR"
  fi
  mkdir "$CWD"/snrcalc


  cp "$EDDYOUTPUT" "${SNRDIR}"/eddy_output.nii.gz
  cp "${ANAT}" "${SNRDIR}"/T1.nii.gz

  cd "$SNRDIR" || exit 1

  fslroi eddy_output.nii.gz b0s.nii.gz 0 4
  bet2 b0s.nii.gz b0s_brain.nii.gz -v
  fslmaths b0s_brain.nii.gz -Tmean meanb0.nii.gz
  fslmaths b0s_brain.nii.gz -Tstd stdb0.nii.gz
  fslmaths meanb0.nii.gz -div stdb0.nii.gz snrb0.nii.gz

  bet2 T1.nii.gz T1_brain.nii.gz -v
  flirt -v -in T1_brain.nii.gz -ref meanb0.nii.gz -omat T1brain_to_meanb0.mat -out T1_brain_reg.nii.gz -dof 6 -v
  fast -v -g --nopve T1_brain_reg.nii.gz 

  fslmaths snrb0.nii.gz -mas T1_brain_reg_seg_2.nii.gz wm_snrb0.nii.gz

  SNRVAL=$(fslstats wm_snrb0.nii.gz -M)

  printf "############################\\n"
  printf "SNR Value is: %s\\n" "$SNRVAL"
  printf "############################\\n"

}

main $@