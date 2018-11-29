#!/usr/bin/env bash

# Need to get:
# -PREPROC_DIR

# Need to do:
# -Check for cuda support

PREPROC_DIR=$1

main() {
	FSL_DIR=$FSLDIR
	verbose="--verbose"
	ReplOutliers="--repol"
	eddyExec="${FSL_DIR}/bin/eddy_cuda"
	eddy_command="${eddyExec}"
	eddy_command="${eddy_command} ${verbose}"
	eddy_command="${eddy_command} ${ReplOutliers}"
	eddy_command="${eddy_command} --imain=${PREPROC_DIR}/PA_AP"
	eddy_command="${eddy_command} --mask=${PREPROC_DIR}/nodif_brain_mask"
	eddy_command="${eddy_command} --index=${PREPROC_DIR}/index.txt"
	eddy_command="${eddy_command} --acqp=${PREPROC_DIR}/acqparams.txt"
	eddy_command="${eddy_command} --bvecs=${PREPROC_DIR}/PA_AP.bvec"
	eddy_command="${eddy_command} --bvals=${PREPROC_DIR}/PA_AP.bval"
	eddy_command="${eddy_command} --topup=${PREPROC_DIR}/topup_PA_AP_b0"
	eddy_command="${eddy_command} --out=${PREPROC_DIR}/eddy_unwarped_images"
	${eddy_command}
}

main $@
 
  # eddy_command="${eddy_exec} "
  # eddy_command+="${outlierStatsOption} "
	# eddy_command+="${replaceOutliersOption} "
	# eddy_command+="${nvoxhpOption} "
	# eddy_command+="${sep_offs_moveOption} "
	# eddy_command+="${rmsOption} "
	# eddy_command+="${ff_valOption} "
  # eddy_command+="--imain=${PREPROC_DIR}/PA_AP "
	# eddy_command+="--mask=${PREPROC_DIR}/nodif_brain_mask "
	# eddy_command+="--index=${PREPROC_DIR}/index.txt "
	# eddy_command+="--acqp=${PREPROC_DIR}/acqparams.txt "
	# eddy_command+="--bvecs=${PREPROC_DIR}/PA_AP.bvecs "
	# eddy_command+="--bvals=${PREPROC_DIR}/PA_AP.bvals "
	# eddy_command+="--fwhm=${fwhm_value} "
	# eddy_command+="--topup=${topupdir}/topup_Pos_Neg_b0 "
	# eddy_command+="--out=${PREPROC_DIR}/eddy_unwarped_images "
	# eddy_command+="--flm=quadratic "

