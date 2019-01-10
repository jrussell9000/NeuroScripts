#!/bin/bash
# Do Tromp 2013
# tromp@wisc.edu
# Run Sanity Control

if [ $# -lt 2 ]
then
echo
echo ~ERROR, not enough input variables~
echo
echo Run Sanity Control
echo Usage:
echo sh sanity_control.sh {process_dir} {example_subject}
echo eg:
echo sanity_control.sh /study/scratch/MRI 001
echo 

else

echo "Process directory: "$1
PROCESS=$1

shift 1
subject=$*

cd ${PROCESS}/CAMINO
for j in ${subject};
do
subj=`echo $j | tr "." "-"| awk -F"/" '{$1=$1}1' OFS=""`

for i in `ls ${subj}*DTI.Bfloat`;
do 
prefix=`echo $i | awk 'BEGIN{FS="_rest_DTI"}{print $1}'`
echo subject: ${subj}
echo prefix: ${prefix}

echo Extracting Voxel and Pixel dimensions
xdim=`fslinfo ${PROCESS}/CORRECTED/$prefix.nii.gz |grep 'dim1'| sed -n '1p' | awk 'BEGIN{FS=" "}{print $2}'`
ydim=`fslinfo ${PROCESS}/CORRECTED/$prefix.nii.gz |grep 'dim2'| sed -n '1p' | awk 'BEGIN{FS=" "}{print $2}'`
zdim=`fslinfo ${PROCESS}/CORRECTED/$prefix.nii.gz |grep 'dim3'| sed -n '1p' | awk 'BEGIN{FS=" "}{print $2}'`
xpix=`fslinfo ${PROCESS}/CORRECTED/$prefix.nii.gz |grep 'pixdim1'| sed -n '1p' | awk 'BEGIN{FS=" "}{print $2}'`
ypix=`fslinfo ${PROCESS}/CORRECTED/$prefix.nii.gz |grep 'pixdim2'| sed -n '1p' | awk 'BEGIN{FS=" "}{print $2}'`
zpix=`fslinfo ${PROCESS}/CORRECTED/$prefix.nii.gz |grep 'pixdim3'| sed -n '1p' | awk 'BEGIN{FS=" "}{print $2}'`
echo "xdim: "$xdim" ydim: "$ydim" zdim: "$zdim" xpix: "$xpix" ypix: "$ypix" zpix: "$zpix

echo ~~~SANITY CHECK~~~
dteig -inputmodel dt -inputdatatype float -outputdatatype float < ${PROCESS}/CAMINO/$prefix"_rest_DTI".Bfloat > ${PROCESS}/TENSOR/$prefix"_rest_DTI_EIG".Bfloat
pdview -inputdatatype float -inputmodel dteig -inputfile ${PROCESS}/TENSOR/$prefix"_rest_DTI_EIG".Bfloat -datadims $xdim $ydim $zdim &

done
done
fi
