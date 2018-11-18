#!/usr/bin/env bash

# Need to get:
# -eddy_dir
# -topup_dir

# Need to do:
# -Check for cuda support
get_options()
{

	local arguments=("$@")
	

	# parse arguments
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
			--eddy_dir=*)
				EDDY_DIR=${argument#*=}
				index=$(( index + 1 ))
				;;
      --topup_dir=*)
				TOPUP_DIR=${argument#*=}
				index=$(( index + 1 ))
				;;
      *)
        echo "Unrecognized option: ${argument}"
        exit 1
        ;;
		esac
	done
	
  if [[ -z ${EDDY_DIR} ]]; then
    echo "ERROR: Eddy files directory not specified."
    exit 1
  fi

  if [[ -z ${TOPUP_DIR} ]]; then
    echo "ERROR: Topup files directory not specified."
    exit 1
  fi

}

main() {

  get_options "$@"

  echo "eddy directory is: $EDDY_DIR"
  eddy_command="eddy_cuda --repol "
  eddy_command+="--imain=${EDDY_DIR}/pos_neg "
  eddy_command+="--mask=${EDDY_DIR}/nodif_brain_mask "
  eddy_command+="--index=${EDDY_DIR}/index.txt "
  eddy_command+="--acqp=${EDDY_DIR}/acqparams.txt "
  eddy_command+="--bvecs=${EDDY_DIR}/pos_neg.bvec "
  eddy_command+="--bvals=${EDDY_DIR}/pos_neg.bval "
  eddy_command+="--topup=${TOPUP_DIR}/topup_pos_neg_b0 "
  eddy_command+="--out=${EDDY_DIR}/eddy_unwarped_images "
  ${eddy_command}
}

main "$@"
 
  # eddy_command="${eddy_exec} "
  # eddy_command+="${outlierStatsOption} "
	# eddy_command+="${replaceOutliersOption} "
	# eddy_command+="${nvoxhpOption} "
	# eddy_command+="${sep_offs_moveOption} "
	# eddy_command+="${rmsOption} "
	# eddy_command+="${ff_valOption} "
  # eddy_command+="--imain=${eddy_dir}/pos_neg "
	# eddy_command+="--mask=${eddy_dir}/nodif_brain_mask "
	# eddy_command+="--index=${eddy_dir}/index.txt "
	# eddy_command+="--acqp=${eddy_dir}/acqparams.txt "
	# eddy_command+="--bvecs=${eddy_dir}/pos_neg.bvecs "
	# eddy_command+="--bvals=${eddy_dir}/pos_neg.bvals "
	# eddy_command+="--fwhm=${fwhm_value} "
	# eddy_command+="--topup=${topupdir}/topup_Pos_Neg_b0 "
	# eddy_command+="--out=${eddy_dir}/eddy_unwarped_images "
	# eddy_command+="--flm=quadratic "