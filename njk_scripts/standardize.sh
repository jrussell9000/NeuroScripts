#!/bin/bash
# Do Tromp 2013
# Standardize images for nomalization step

if [ $# -lt 3 ]
then
echo
echo "ERROR, not enough input variables"
echo
echo "This script standardizes images before nomalization"
echo "Usage:"
echo "standardize.sh {process_dir} {species} {subj}"
echo "eg:"
echo "standardize.sh /study/mri nhp 001 002"
echo

else
PROCESS=$1
species=$2

shift 2
subject=$*

dir=${PROCESS}/TENSOR
outdir=${PROCESS}/TEMPLATE
#rm -f ${outdir}/number_of_spds.txt
cd ${dir}

echo ~~~Run Standardization~~~
for j in ${subject};
do
subj=`echo $j | tr "." "-"| awk -F"/" '{$1=$1}1' OFS=""`

for i in `ls ${subj}*_dt.nii*`;
do
prefix=`echo $i | awk 'BEGIN{FS="_dt.nii"}{print $1}'`
echo Prefix is $prefix
echo

echo ~~Adjusting Diffusivity Units~~
TVtool -in $i -scale 1000000000 -out $prefix"_sdt".nii.gz
echo

echo ~~Making and applying Mask~~
TVtool -in $prefix"_sdt".nii.gz -tr
BinaryThresholdImageFilter $prefix"_sdt_tr".nii.gz ${prefix}_mask.nii.gz 0.5 100 1 0
TVtool -in $prefix"_sdt".nii.gz -out ${prefix}_tmp.nii.gz -mask ${prefix}_mask.nii.gz
mv -f ${prefix}_tmp.nii.gz $prefix"_sdt".nii.gz
echo

echo ~~Checking for and removing Outliers~~
TVtool -in $prefix"_sdt".nii.gz -norm
SVtool -in $prefix"_sdt_norm".nii.gz -stats
BinaryThresholdImageFilter $prefix"_sdt_norm".nii.gz ${prefix}_non_outliers.nii.gz 0 100 1 0
TVtool -in $prefix"_sdt".nii.gz -mask ${prefix}_non_outliers.nii.gz -out $prefix"_tmp".nii.gz
mv -f ${prefix}_tmp.nii.gz $prefix"_sdt".nii.gz
TVtool -in $prefix"_sdt".nii.gz -norm
echo

echo ~~~Stats for${prefix} - max should be below 100~~~
SVtool -in $prefix"_sdt_norm".nii.gz -stats
echo

echo ~~Enforcing positive semi-definiteness~~
TVtool -in $prefix"_sdt".nii.gz -spd -out $prefix"_tmp".nii.gz
mv -f ${prefix}_tmp.nii.gz $prefix"_sdt".nii.gz
spds=`fslstats ${prefix}_sdt_nonSPD.nii.gz -V | awk 'BEGIN{FS=" "}{print $1}'`;
echo ${prefix} ${spds} >> ${outdir}/number_of_spds.txt
echo

if [ $species == "nhp" ]
then

echo ~~Standardizing Voxel Space for non-human primates~~
TVAdjustVoxelspace -in $prefix"_sdt".nii.gz -origin 0 0 0 -out ${outdir}/$prefix"_sdt".nii.gz
echo
echo ~~~Reorient Image to LPI~~~
TVtool -in ${outdir}/$prefix"_sdt".nii.gz -out ${outdir}/$prefix"_sdt_LPI".nii.gz -orientation LIP LPI
rm -f ${outdir}/$prefix"_sdt".nii.gz
echo ~~~Output file:~~~
echo ${outdir}/$prefix"_sdt_LPI".nii.gz

else
echo ~~Standardizing Voxel Space for human primates~~
TVAdjustVoxelspace -in $prefix"_sdt".nii.gz -origin 0 0 0 -out ${outdir}/$prefix"_sdt".nii.gz
echo ~~~Output file:~~~
echo ${outdir}/${prefix}_sdt.nii.gz
fi

echo ~~~Cleaning up~~~
rm -f ${prefix}_mask.nii.gz
rm -f ${prefix}_sdt_tr.nii.gz
rm -f ${prefix}_tmp.nii.gz
rm -f ${prefix}_non_outliers.nii.gz
rm -f ${prefix}_sdt_nonSPD.nii.gz
rm -f ${prefix}_sdt_norm.nii.gz
rm -f $prefix"_sdt".nii.gz
echo
done
done
echo Written:
ls -ltrh ${outdir}/${prefix}*.nii.gz
#echo ~~Optional: Resample images with different Voxel sizes (Insert in Above Script)~~
#TVResample -in $prefix"_sdt".nii.gz -align center -size 128 128 64 -vsize 1.5 1.75 2.25 #human
#TVResample -in mean_initial.nii.gz -align center -size 128 128 64 -vsize 0.6 0.675 0.9 #monkey

fi