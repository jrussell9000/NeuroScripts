#!/usr/bin/env bash

# Need to get:
# -working_dir

# Need to do:
# -Check for cuda support

working_dir=$1
USEGPUopt=$2
PostAnt=$3
AntPost=$4

main() {

	#--Creating the index files for eddy
    PAvolcnt=$(fslval "${working_dir}"/"${PostAnt}" dim4)
    APvolcnt=$(fslval "${working_dir}"/"${AntPost}" dim4)

    for (( i=1; i<=PAvolcnt; i++ )); do
      indcnt=1
      echo $indcnt >> "${working_dir}"/index.txt
    done

    for (( i=1; i<=APvolcnt; i++ )); do
      indcnt=2
      echo $indcnt >> "${working_dir}"/index.txt
    done

  #--Merging the PA and AP phase encoded scan series into one file
    fslmerge -t "${working_dir}"/PA_AP "${working_dir}"/"${PostAnt}" "${working_dir}"/"${AntPost}"

  #--Merging the gradient files 
    paste "${working_dir}"/"${PostAnt}".bval "${working_dir}"/"${AntPost}".bval > "${working_dir}"/PA_AP.bval
    paste "${working_dir}"/"${PostAnt}".bvec "${working_dir}"/"${AntPost}".bvec > "${working_dir}"/PA_AP.bvec
  
	FSL_DIR="$FSLDIR"
	verbose="--verbose"
	ReplOutliers="--repol"
	Residuals="--residuals"
	CNRMaps="--cnr_maps"
	if [[ "${USEGPUopt}" == "True" ]] ; then
		eddyExec="${FSL_DIR}/bin/eddy_cuda"
		printf "\\nGPU acceleration enabled.  Using eddy_cuda for eddy correction..."
	else
		eddyExec="${FSL_DIR}/bin/eddy_openmp"
		printf "\\nGPU acceleration not enabled.  Using eddy_openmp for eddy correction..."
	fi
	eddy_command="${eddyExec}"
	eddy_command="${eddy_command} ${verbose}"
	eddy_command="${eddy_command} ${ReplOutliers}"
	eddy_command="${eddy_command} ${Residuals}"
	eddy_command="${eddy_command} ${CNRMaps}"
	eddy_command="${eddy_command} --imain=${working_dir}/PA_AP"
	eddy_command="${eddy_command} --mask=${working_dir}/nodif_brain_mask"
	eddy_command="${eddy_command} --index=${working_dir}/index.txt"
	eddy_command="${eddy_command} --acqp=${working_dir}/acqparams.txt"
	eddy_command="${eddy_command} --bvecs=${working_dir}/PA_AP.bvec"
	eddy_command="${eddy_command} --bvals=${working_dir}/PA_AP.bval"
	eddy_command="${eddy_command} --topup=${working_dir}/topup_PA_AP_b0"
	eddy_command="${eddy_command} --out=${working_dir}/eddy_unwarped_images"
	${eddy_command}
}

main $@