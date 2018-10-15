#!/bin/bash

# source dtitk_common.sh
. dtitk_common.sh
export PATH=$PATH:.
templatemean=$1
dftemplate=$2
template=$3
dftRoot=${dftemplate//\.nii.gz/};

echo "difGrpAfterMeans" 

dfToInverse -in ${dftemplate}
deformationSymTensor3DVolume -in ${templatemean} -out tmp.nii.gz -trans ${dftRoot}_inv.nii.gz

#TVResample -in tmp.nii.gz -align center -size 128 256 128 -vsize 0.625 0.625 0.625

cp tmp.nii.gz $template

ls -ltr



