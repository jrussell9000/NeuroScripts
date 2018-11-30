#!/usr/bin/env bash

preproc_dir=$1
PostAnt=$2
AntPost=$3 
echospacing=$4

#COMPUTING TOTAL READOUT TIME

#-Computing the total readout time in seconds, and up to six decimal places. Grab any
#-scan in the raw directory and get the second dimension (slice count if using PA/AP phase encoding)
#-using fslval.  Compute total readout time as: echo spacing *(slice count - 1).  Divide by 1000
#-to convert the value to seconds (from milliseconds )
any_scan=$(find "${preproc_dir}"/*.nii.gz | head -n 1)
dims=$("${FSL_DIR}"/bin/fslval "${any_scan}" dim2)
dimsmin1=$(awk "BEGIN {print $dims - 1; exit}" )
totalrotime=$(awk "BEGIN {print ${echospacing}*${dimsmin1}; exit}" )
totalrotime=$(awk "BEGIN {print ${totalrotime} / 1000; exit}" )

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

#-Run topup using the combined b0 file
printf "\\n%s\\n\\n" "Decompressing the combined b0 scans and running topup..."
gzip -d "${preproc_dir}"/PA_AP_b0.nii.gz

topup -v --imain="${preproc_dir}"/PA_AP_b0 --datain="${preproc_dir}"/acqparams.txt --config=b02b0.cnf --out="${preproc_dir}"/topup_PA_AP_b0

fslmaths "${preproc_dir}"/topup_PA_AP_b0 -Tmean "${preproc_dir}"/avg_topup_PA_AP_b0
bet "${preproc_dir}"/avg_topup_PA_AP_b0 "${preproc_dir}"/nodif_brain -m -f 0.2

#-Per HCP script (run_topup.sh), run applytopup to first b0 from positive and negative phase encodings to generate a hifib0 which will
#-be used to create the brain mask.  

# fslroi "${preproc_dir}"/PA_b0 "${preproc_dir}"/PA_b0_1st 0 1
# fslroi "${preproc_dir}"/AP_b0 "${preproc_dir}"/AP_b0_1st 0 1

# dimt=$(fslval "${preproc_dir}"/PA_b0 dim4)
# dimt=$(( dimt + 1 ))

# # #-Running applytopup to create a hifi b0 image, then using that image to create a brain mask.
# # #-For applytopup, must use the jacobian modulation method (--method=jac) since the diffusion gradients do not match one-to-one across the phase encodings
# applytopup --imain="${preproc_dir}"/PA_b0_1st,"${preproc_dir}"/AP_b0_1st --method=jac --topup="${preproc_dir}"/topup_PA_AP_b0 --datain="${preproc_dir}"/acqparams.txt --inindex=1,"${dimt}" --out="${preproc_dir}"/hifib0

# bet "${preproc_dir}"/hifib0 "${preproc_dir}"/nodif_brain -m -f 0.2

printf "\\n%s\\n\\n" "TOPUP processing finished successfully."

exit 0