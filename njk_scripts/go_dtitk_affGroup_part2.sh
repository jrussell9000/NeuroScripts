#!/usr/bin/env bash

export HOME=/home/`whoami`

chmod -R a=wrx .
export PATH=$PWD:$PATH

outputFile=$1


# ls toTemplate_*.nii.gz > myAffineImages.txt
ls *.nii.gz > myAffineImages.txt
TVMean -in myAffineImages.txt -out $outputFile

ls
# TVtool -in mean_affine${oldcount}.nii.gz -sm mean_affine${count}.nii.gz -SMOption $smoption | grep Similarity | tee -a ${log}
# TVtool -in templateDir/$template -sm $outputFile -SMOption EDS | grep Similarity 








