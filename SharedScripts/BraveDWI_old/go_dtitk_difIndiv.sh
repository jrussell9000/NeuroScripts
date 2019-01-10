#!/bin/bash

echo "-> $1 $2 $3 $4 $5 "

template=$1
subj=$2
iter=$3
ftol=$4

# source dtitk_common.sh
./dtitk_common.sh
export PATH=$PATH:.

TVtool -in $template -tr -out tr.nii.gz
BinaryThresholdImageFilter tr.nii.gz mask.nii.gz 1.0 100 1 0

# echo "--> dti_diffeomorphic_reg $template $subj mask.nii.gz 1 $iter $ftol "
# echo "-----> $lengthscale"
# dti_diffeomorphic_reg $template $subj mask.nii.gz 1 $iter $ftol 

echo "--> dti_diffeomorphic_reg $template $subj mask.nii.gz 1 $iter .001 "
dti_diffeomorphic_reg $template $subj mask.nii.gz 1 $iter .001 

# ls *diffeo.*gz | awk '{print "mv "$0" toTemplate_"$0 }' | bash 
echo finished!
ls

