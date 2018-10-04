#!/bin/bash
# Do Tromp 2013
# Register manual T1 mask to magnitude map

if [ $# -lt 5 ]
then
echo
echo "ERROR, not enough input variables"
echo
echo "Register manual T1 mask to magnitude map"
echo "Usage:"
echo "reg_mask.sh {process_dir} {inputpath_of_T1_files} {twodfast} {t1_prefix} {mask_prefix} {subj}"
echo "eg:"
echo "reg_mask.sh /study/process /study/process/T1 /study/etc/001_s04_2dfast.nii.gz 001_s03_T1high /study/etc/MASK/001_mask 001"
echo
echo "Before running this script run make_mask.sh" 
#echo "Before you run this script first run dti_2dfast.sh and get text file with 2dfast names"
echo

else
PROCESS=$1
t1_dir=$2
twodfast=$3
t1_prefix=$4
mask_prefix=$5

shift 5
subject=$*

for j in ${subject};
do
#subj=`echo $j | tr "." "-"| awk -F"/" '{$1=$1}1' OFS=""`
subj=$j
cd ${t1_dir}
#fast=`cat ${PROCESS}/dti_2dfast*.txt|grep ${subj}|awk 'BEGIN{FS=", "}{print $2}'|awk 'BEGIN{FS=" "}{print $1}'`;
#scan=`ls ${PROCESS}/DTI_RAW/${subj}*dti.nii* | awk 'BEGIN{FS="_"}{print $2}' | awk 'BEGIN{FS="_"}{print $1}' | cut -c2- | sed -e 's:^0*::'`;
#num=$(( $scan + 1 ))
#fast=`ls ${PROCESS}/2DFAST/${subj}_[sS]*${num}_2dfast.nii*`;
#echo 2dfast file used: ${fast};

echo ~~~Register manual T1 mask to magnitude map~~~
#echo SVtool -in ${t1_prefix}.nii.gz -out ${subj}_LSP.nii.gz -orientation LPI LSP
SVtool -in ${t1_prefix}.nii.gz -out ${subj}_LSP.nii.gz -orientation LPI LSP
#echo flirt -in ${subj}_LSP.nii.gz -ref ${twodfast} -omat ${subj}_omat
flirt -in ${subj}_LSP.nii.gz -ref ${twodfast} -omat ${subj}_omat

#echo SVtool -in ${t1_prefix}_M.nii.gz -out ${subj}_LSP_M.nii.gz -orientation LPI LSP
SVtool -in ${t1_prefix}_M.nii.gz -out ${subj}_LSP_M.nii.gz -orientation LPI LSP
#echo flirt -in ${subj}_LSP_M.nii.gz -ref ${twodfast} -applyxfm -init ${subj}_omat -out ${mask_prefix}
flirt -in ${subj}_LSP_M.nii.gz -ref ${twodfast} -applyxfm -init ${subj}_omat -out ${mask_prefix}

#echo fslmaths ${mask_prefix}.nii.gz -bin -dilM ${mask_prefix}
fslmaths ${mask_prefix}.nii.gz -bin -dilM ${mask_prefix}
echo Written: 
ls -lthr ${mask_prefix}* 

#rm -f ${subj}_LSP.nii.gz
#rm -f ${subj}_LSP_M.nii.gz
done
fi
