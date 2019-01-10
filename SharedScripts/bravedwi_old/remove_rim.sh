#!/bin/bash
# Do Tromp 2013
# tromp@wisc.edu
# Remove rim around brain edge

if [ $# -lt 7 ]
then
echo
echo ~ERROR, not enough input variables~
echo
echo This will remove the rim around DTI brain data.
echo Usage:
echo sh remove_rim.sh {process_dir} {num} {b0} {bvalue} {grad_dir_txt} {corrected_prefix} {strip_prefix} {subject}
echo eg:
echo remove_rim.sh /study/scratch/MRI 57 8 1000 /study/etc/grad_dir_57.txt /study/etc/CORRECTED/001_dti_eddy_fmap /study/etc/CORRECTED/001_etc_strip 001
echo 
#echo Needs output of bval_bvec.sh

else

PROCESS=$1
num=$2
b0=$3
bvalue=$4
grad_dir_txt=$5
corrected_prefix=$6
strip_prefix=$7 

shift 7
subject=$*

echo ~~REMOVE RIM~~~
cd ${PROCESS}/CORRECTED
for j in ${subject};
do

mask=`ls ${corrected_prefix}.nii* | awk 'BEGIN{FS="CORRECTED/"}{print $2}'|awk 'BEGIN{FS=".nii"}{print $1}'`;
echo bet ${corrected_prefix}.nii* ${PROCESS}/MASK/${mask} -m -n;
bet ${corrected_prefix}.nii* ${PROCESS}/MASK/${mask} -m -n;

echo dti_recon ${corrected_prefix}.nii* ${corrected_prefix}_DTK -b0 $b0 -b $bvalue -gm ${grad_dir_txt} -no_tensor -no_eigen;
dti_recon ${corrected_prefix}.nii* ${corrected_prefix}_DTK -b0 $b0 -b $bvalue -gm ${grad_dir_txt} -no_tensor -no_eigen;
#dti_recon ${i} ${corrected_prefix}_DTK -gm ${PROCESS}/grad_dir_$num.txt -no_tensor -no_eigen;

fslmaths ${corrected_prefix}_DTK_dwi.nii -thrP 5 -bin ${corrected_prefix}_DTK_dwi_thrP;
fslmaths ${corrected_prefix}_DTK_adc.nii -uthrP 95 -bin ${corrected_prefix}_DTK_adc_uthrP
fslmaths ${corrected_prefix}_DTK_b0.nii -thrP 5 -bin ${corrected_prefix}_DTK_b0_thrP
#fslmaths ${corrected_prefix}_DTK_exp.nii -uthrP 95 -bin ${corrected_prefix}_DTK_exp_uthrP

fslmaths ${corrected_prefix}_DTK_dwi_thrP.nii.gz -mas ${corrected_prefix}_DTK_adc_uthrP.nii.gz ${corrected_prefix}_DTK_tmp1
fslmaths ${corrected_prefix}_DTK_tmp1.nii.gz -mas ${corrected_prefix}_DTK_b0_thrP.nii.gz ${corrected_prefix}_DTK_tmp2
#fslmaths ${corrected_prefix}_DTK_tmp2.nii.gz -mas ${corrected_prefix}_DTK_exp_uthrP ${corrected_prefix}_DTK_tmp3

#fslmaths ${i} -mas ${corrected_prefix}_DTK_tmp3.nii.gz ${corrected_prefix}_masked;
fslmaths ${corrected_prefix}.nii -mas ${corrected_prefix}_DTK_tmp2.nii.gz -mas ${PROCESS}/MASK/${mask}_mask.nii.gz ${strip_prefix};

rm -f ${corrected_prefix}_DTK*

echo Written:
ls -ltrh ${strip_prefix}* 
done
fi
