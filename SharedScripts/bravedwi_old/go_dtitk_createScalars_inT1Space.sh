#!/usr/bin/env bash

export HOME=/home/`whoami`

chmod -R a=wrx ./
export PATH=$PWD:$PATH

smoption=EDS
#lengthscale=0.5
lengthscale=1

fa=$1
tr=$2
ad=$3
rd=$4

tensorFile=$5
orig=$6
affineTrans=$7
diffeoTrans=$8
dtiToT1Trans=$9
T1=${10}



##compose full warp and apply
dfRightComposeAffine -aff $affineTrans -df $diffeoTrans -out combined.df.nii.gz

##combine full warp with affine to T1 and apply
dfLeftComposeAffine -df combined.df.nii.gz -aff $dtiToT1Trans -out toT1_combined.df.nii.gz
deformationSymTensor3DVolume -in $orig -trans toT1_combined.df.nii.gz -target $T1 -out $tensorFile


TVtool -in $tensorFile -fa -out $fa
TVtool -in $tensorFile -tr -out $tr
TVtool -in $tensorFile -ad -out $ad 
TVtool -in $tensorFile -rd -out $rd

touch test.txt

SVGaussianSmoothing -in $fa -fwhm  4 4 4
SVGaussianSmoothing -in $tr -fwhm  4 4 4
SVGaussianSmoothing -in $ad -fwhm  4 4 4
SVGaussianSmoothing -in $rd -fwhm  4 4 4

fslchfiletype NIFTI_GZ $fa 
fslchfiletype NIFTI_GZ $tr 
fslchfiletype NIFTI_GZ $ad 
fslchfiletype NIFTI_GZ $rd 

ls -ltr


