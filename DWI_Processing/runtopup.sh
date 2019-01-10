#!/usr/bin/env bash

set -e 

working_dir=$1
PostAnt=$2
AntPost=$3 
echospacing=$4

#COMPUTING TOTAL READOUT TIME

#-Computing the total readout time in seconds, and up to six decimal places. Grab any
#-scan in the raw directory and get the second dimension (slice count if using PA/AP phase encoding)
#-using fslval.  Compute total readout time as: echo spacing *(slice count - 1).  Divide by 1000
#-to convert the value to seconds (from milliseconds )
any_scan=$(find "${working_dir}"/*.nii.gz | head -n 1)
dims=$("${FSL_DIR}"/bin/fslval "${any_scan}" dim2)
dimsmin1=$(awk "BEGIN {print $dims - 1; exit}" )
totalrotime=$(awk "BEGIN {print ${echospacing}*${dimsmin1}; exit}" )
totalrotime=$(awk "BEGIN {print ${totalrotime} / 1000; exit}" )

#-Extract b0's and make acqparms.txt for topup
printf "\\nExtracting b0 scans from PA encoded volume and adding info to acqparams.txt for topup..."
for file in "${working_dir}"/*"${PostAnt}".nii.gz; do
    fslroi "${file}" "${working_dir}"/PA_b0 0 1
    b0vols=$("${FSL_DIR}"/bin/fslval "${working_dir}"/PA_b0 dim4)
    for (( i=1; i<=b0vols; i++ )); do
    echo 0 1 0 "${totalrotime}" >> "${working_dir}"/acqparams.txt
    done
done

printf "\\nExtracting b0 scans from AP encoded volume and adding info to acqparams.txt for topup..."
for file in "${working_dir}"/*"${AntPost}".nii.gz; do
    fslroi "${file}" "${working_dir}"/AP_b0 0 1
    b0vols=$("${FSL_DIR}"/bin/fslval "${working_dir}"/AP_b0 dim4)
    for (( i=1; i<=b0vols; i++ )); do
    echo 0 -1 0 "${totalrotime}" >> "${working_dir}"/acqparams.txt
    done
done

printf "\\nMerging b0 scans from PA and PA phase encoding volumes..."

#-Merge separate b0 files 
fslmerge -t "${working_dir}"/PA_AP_b0 "${working_dir}"/PA_b0 "${working_dir}"/AP_b0 

#-Run topup using the combined b0 file
printf "\\n%s\\n\\n" "Decompressing the combined b0 scans and running topup..."
gzip -d "${working_dir}"/PA_AP_b0.nii.gz

cd "${working_dir}" || exit 1
topup -v --imain="${working_dir}"/PA_AP_b0 --datain="${working_dir}"/acqparams.txt --config=b02b0.cnf --out=topup_PA_AP_b0 --iout=topup_PA_AP_b0 \
--fout=topup_PA_AP_b0_fieldHz --logout=topup_log.txt

fslmaths "${working_dir}"/topup_PA_AP_b0 -Tmean "${working_dir}"/avg_topup_PA_AP_b0
bet "${working_dir}"/avg_topup_PA_AP_b0 "${working_dir}"/nodif_brain -m -f 0.2

#-Per HCP script (run_topup.sh), run applytopup to first b0 from positive and negative phase encodings to generate a hifib0 which will
#-be used to create the brain mask.  

# fslroi "${working_dir}"/PA_b0 "${working_dir}"/PA_b0_1st 0 1
# fslroi "${working_dir}"/AP_b0 "${working_dir}"/AP_b0_1st 0 1

# dimt=$(fslval "${working_dir}"/PA_b0 dim4)
# dimt=$(( dimt + 1 ))

# # #-Running applytopup to create a hifi b0 image, then using that image to create a brain mask.
# # #-For applytopup, must use the jacobian modulation method (--method=jac) since the diffusion gradients do not match one-to-one across the phase encodings
# applytopup --imain="${working_dir}"/PA_b0_1st,"${working_dir}"/AP_b0_1st --method=jac --topup="${working_dir}"/topup_PA_AP_b0 --datain="${working_dir}"/acqparams.txt --inindex=1,"${dimt}" --out="${working_dir}"/hifib0

# bet "${working_dir}"/hifib0 "${working_dir}"/nodif_brain -m -f 0.2

printf "\\n%s\\n\\n" "TOPUP processing finished successfully."

exit 0