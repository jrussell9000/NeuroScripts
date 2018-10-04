#!/bin/bash
# Do Tromp 2013
# Convert DTI, FMAP, T1, T2 from DICOM to NIfTI for multiple subjects

if [ $# -lt 3 ]
then
echo
echo ERROR, not enough input variables
echo
echo Convert DTI, FMAP, T1, T2 from DICOM to NIfTI for multiple subjects
echo Usage:
echo sh convert_script.sh {raw_input_dir} {process_dir} {subjs_separate_by_space}
echo eg:
echo
echo convert_script.sh /study/mri/raw-data /study5/aa-scratch/MRI 002 003 004 
echo

else

raw=$1
echo "Input directory "$raw
PROCESS=$2
echo "Output directory "$PROCESS

shift 2
subject=$*
cd ${raw}

echo ~~~Convert File~~~;
for i in ${subject};
do

cd ${raw}/${i}/dicoms/;
mkdir -p -v ${PROCESS}/DTI_RAW
mkdir -p -v ${PROCESS}/T1
mkdir -p -v ${PROCESS}/T2
mkdir -p -v ${PROCESS}/2DFAST
mkdir -p -v ${PROCESS}/MASK
mkdir -p -v ${PROCESS}/FMAP
mkdir -p -v ${PROCESS}/EDDY
mkdir -p -v ${PROCESS}/CORRECTED
mkdir -p -v ${PROCESS}/SCHEME
mkdir -p -v ${PROCESS}/CAMINO
mkdir -p -v ${PROCESS}/SNR
mkdir -p -v ${PROCESS}/TENSOR
mkdir -p -v ${PROCESS}/TEMPLATE
mkdir -p -v ${PROCESS}/SCALARS
mkdir -p -v ${PROCESS}/TRACKVIS
mkdir -p -v ${PROCESS}/INFO

echo ~~~Subject in process: ${i}~~~
subj=`echo $i | tr "." "-"| awk -F"/" '{$1=$1}1' OFS=""`
echo ~~~Prefix is ${subj}~~~
cp ${raw}/${i}/dicoms/info.txt ${PROCESS}/INFO/${subj}_info.txt;

echo CONVERT ANATOMICAL
for j in `ls -d *_bravo *_3dir`;
do
prefix=`echo $j | awk 'BEGIN{FS="/"}{print $1}'`;
#subj=${i};
echo Scan is ${j}
convert_file ${j} ${PROCESS}/T1/${subj}_${prefix} nii;
done

echo CONVERT T2
for j in `ls -d *_cube`;
do
prefix=`echo $j | awk 'BEGIN{FS="/"}{print $1}'`;
#subj=${i};
echo Scan is ${j}
convert_file ${j} ${PROCESS}/T2/${subj}_${prefix} nii;
done

echo CONVERT DTI SCANS
for j in `ls -d *_dti *_hydie`;
do
prefix=`echo $j | awk 'BEGIN{FS="/"}{print $1}'`;
#subj=${i};
echo Scan is ${j}
convert_file ${j} ${PROCESS}/DTI_RAW/${subj}_${prefix} nii;
done

echo CONVERT 2DFAST
for k in `ls -d *_fmap *_2dfast`;
do
prefix=`echo $k | awk 'BEGIN{FS="/"}{print $1}'`;
#subj=${i};
echo Scan is ${prefix}
convert_file ${k} ${PROCESS}/2DFAST/${subj}_${prefix} nii;
done

cd ${raw}

done

cd ${PROCESS}
echo "You are now in the output directory "
pwd
fi
