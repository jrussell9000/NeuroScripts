#!/bin/bash

# source dtitk_common.sh
. dtitk_common.sh
export PATH=$PATH:.
dftemplate=$1

for subj_dif in *df*nii.gz
do
	echo ${subj_dif} >> diffeo.txt
done

echo "difVVmean" 

VVMean -in diffeo.txt -out ${dftemplate}
