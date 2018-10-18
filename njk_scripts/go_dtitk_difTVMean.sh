#!/bin/bash

# source dtitk_common.sh
#. dtitk_common.sh
export PATH=$PATH:.
template=$1

for subj_dif in *diffeo*.nii.gz
do
	echo ${subj_dif} >> subjects_diffeo.txt
done

echo "difTVMean" 

TVMean -in subjects_diffeo.txt -out ${template}

ls -al


