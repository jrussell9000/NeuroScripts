#!/usr/bin/env bash

export HOME=/home/`whoami`

chmod -R a=wrx ./
export PATH=$PWD:$PATH


dti=$1
t1=$2
dtiToT1Trans=$3

#TVtool -in $1 -fa -out myFA.nii.gz 
#asvDSM -template $t1 -subject myFA.nii.gz -outTrans $dtiToT1Trans -sep 0.5 0.5 0.5 -ftol 0.0001
TVtool -in $dti -tr -out my_tr.nii.gz 
BinaryThresholdImageFilter my_tr.nii.gz my_mask.nii.gz 0.7 100 1 0
TVtool -in $dti -mask my_mask.nii.gz -out my_strip.nii.gz
TVtool -in my_strip.nii.gz -fa -out my_strip_fa.nii.gz 
asvDSM -template $t1 -subject my_strip_fa.nii.gz -outTrans $dtiToT1Trans -sep 0.5 0.5 0.5 -ftol 0.0001
#affineSymTensor3DVolume -in ${dti} -trans $dtiToT1Trans -target $t1 -out my_toT1.nii.gz

