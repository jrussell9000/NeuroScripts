#!/bin/bash
# Do Tromp 2013
# tromp@wisc.edu
# Mask human data 

if [ $# -lt 2 ]
then
echo
echo ~ERROR, not enough input variables~
echo
echo This will remove the rim around DTI brain data.
echo Usage:
echo sh mask_human.sh {process_dir} {subjects}
echo eg:
echo mask_human.sh /study/scratch/MRI 001 002
echo 
echo Needs output of bval_bvec.sh
echo

else

echo "Process directory: "$1
PROCESS=$1

shift 1
subject=$*

echo ~~MASK~~~
cd ${PROCESS}/EDDY
for j in ${subject};
do
subj=`echo $j | tr "." "-"| awk -F"/" '{$1=$1}1' OFS=""`

for i in `ls ${subj}*_eddy.nii*`;
do
prefix=`echo ${i} | awk 'BEGIN{FS=".nii"}{print $1}'`;
num=`fslinfo ${i}|grep ^dim4|awk 'BEGIN{FS="4"}{print $2}'| sed 's/ //g'`

bet ${i} ${PROCESS}/MASK/${prefix} -m -n;
fslmaths ${i} -mas ${PROCESS}/MASK/${prefix}_mask.nii.gz ${PROCESS}/CORRECTED/${prefix};
done
done
fi
