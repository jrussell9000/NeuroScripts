#!/bin/bash
# Do Tromp 2013
# Convert DTI, FMAP, fMRI, T1, T2 from DICOM to NIfTI for multiple subjects

if [ $# -lt 3 ]
then
echo
echo ERROR, not enough input variables
echo
echo Convert DTI, FMAP, T1, T2 from DICOM to NIfTI for multiple subjects
echo Usage:
echo sh convert_script_all.sh raw_input_dir process_dir subjs_separate_by_space
echo eg:
echo
echo convert_script_all.sh /study/mri/raw-data /study5/aa-scratch/MRI 002 003 004
echo
echo

else

RAW_INPUT_DIR=$1
echo "Input directory "$RAW_INPUT_DIR
DATASET_DIR=$2
echo "Output directory "$DATASET_DIR

shift 2
subject=$*
cd ${RAW_INPUT_DIR} || exit

echo ~~~Convert File~~~;

for i in ${subject}; do

  #Making directories to hold per subject SCANS
  mkdir -p -v ${i}

done

for i in ${DATASET_DIR}/*/; do
  cd ${i} || return
  mkdir -p -v DTI_RAW
  mkdir -p -v T1
  mkdir -p -v T2
  mkdir -p -v 2DFAST
  mkdir -p -v MASK
  mkdir -p -v FMAP
  mkdir -p -v EDDY
  mkdir -p -v CORRECTED
  mkdir -p -v SCHEME
  mkdir -p -v CAMINO
  mkdir -p -v SNR
  mkdir -p -v TENSOR
  mkdir -p -v TEMPLATE
  mkdir -p -v SCALARS
  mkdir -p -v TRACKVIS
  mkdir -p -v INFO
  mkdir -p -v rs-fMRI

done

for i in ${RAW_INPUT_DIR}; do

  cd ${DATASET_DIR}/${i} || continue

  echo ~~~Subject in process: ${i}~~~

  SUBJ=`echo $i | tr "." "-"| awk -F"/" '{$1=$1}1' OFS=""`
  echo ~~~Prefix is ${SUBJ}~~~
  cp ${RAW_INPUT_DIR}/${i}/dicoms/info.txt INFO/${SUBJ}_info.txt;

done
fi

#echo CONVERT ANATOMICAL
#for j in `ls -d *_bravo *_3dir`;
#do
#prefix=`echo $j | awk 'BEGIN{FS="/"}{print $1}'`;
##subj=${i};
#echo Scan is ${j}
#echo convert_file ${j} T1/${subj}_${prefix} nii;
#convert_file ${j} T1/${subj}_${prefix} nii;
#done

#echo CONVERT T2
#for j in `ls -d *_cube`;
#do
#prefix=`echo $j | awk 'BEGIN{FS="/"}{print $1}'`;
##subj=${i};
#echo Scan is ${j}
#echo convert_file ${j} T2/${subj}_${prefix} nii;
#convert_file ${j} T2/${subj}_${prefix} nii;
#done
#
# echo CONVERT DTI SCANS
# for j in `ls -d *_dti *_hydie *_hydi`;
# do
#   prefix=`echo $j | awk 'BEGIN{FS="/"}{print $1}'`;
#   #subj=${i};
#   echo Scan is ${j}
#   echo convert_file ${j} DTI_RAW/${subj}_${prefix} nii;
#   convert_file ${j} DTI_RAW/${subj}_${prefix} nii;
# done
#
# #echo CONVERT rs-fMRI SCANS
# #for j in `ls -d *_epi`;
# #do
# #prefix=`echo $j | awk 'BEGIN{FS="/"}{print $1}'`;
# ##subj=${i};
# #echo Scan is ${j}
# #echo convert_file ${j} rs-fMRI/${subj}_${prefix} nii;
# #convert_file ${j} rs-fMRI/${subj}_${prefix} nii;
# #done
#
# echo CONVERT 2DFAST
# for k in `ls -d *_2dfast *_fmap *_FIELD_MAP`;
# do
# prefix=`echo $k | awk 'BEGIN{FS="/"}{print $1}'`;
# #subj=${i};
# echo Scan is ${prefix}
# echo convert_file ${k} 2DFAST/${subj}_${prefix} nii;
# convert_file ${k} 2DFAST/${subj}_${prefix} nii;
# done
#
# cd ${RAW_INPUT_DIR}
#
# done
#
# cd ${DATASET_DIR}
# echo "You are now in the output directory "
# pwd
# fi
