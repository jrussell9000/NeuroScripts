#!/usr/bin/env bash

topup_dir=$1

#-Run topup using the combined b0 file
printf "\\n%s\\n\\n" "Decompressing the combined b0 scans and running topup..."
gzip -d "${topup_dir}"/pos_neg_b0.nii.gz

topup -v --imain="${topup_dir}"/pos_neg_b0 --datain="${topup_dir}"/acqparams.txt --config=b02b0.cnf --out="${topup_dir}"/topup_pos_neg_b0

#-Per HCP script (run_topup.sh), run applytopup to first b0 from positive and negative phase encodings to generate a hifib0 which will
#-be used to create the brain mask.  

fslroi "${topup_dir}"/pos_b0 "${topup_dir}"/pos_b0_1st 0 1
fslroi "${topup_dir}"/neg_b0 "${topup_dir}"/neg_b0_1st 0 1

dimt=$(fslval "${topup_dir}"/pos_b0 dim4)
dimt=$(( dimt + 1 ))

#-Running applytopup to create a hifi b0 image, then using that image to create a brain mask.
#-For applytopup, must use the jacobian modulation method (--method=jac) since the diffusion gradients do not match one-to-one across the phase encodings
applytopup --imain="${topup_dir}"/pos_b0_1st,"${topup_dir}"/neg_b0_1st --method=jac --topup="${topup_dir}"/topup_pos_neg_b0 --datain="${topup_dir}"/acqparams.txt --inindex=1,"${dimt}" --out="${topup_dir}"/hifib0

bet "${topup_dir}"/hifib0 "${topup_dir}"/nodif_brain -m -f 0.2

printf "\\n%s\\n\\n" "TOPUP processing finished successfully."

exit 0