#!/bin/bash
# Do Tromp 2015
# tromp@wisc.edu
# Run DTI youthptsd processing pipeline

if [ $# -lt 5 ]
then
echo
echo ERROR, not enough input variables
echo
echo Run DTI youthptsd processing pipeline
echo Usage:
echo sh youthptsd_dti_processing.sh {raw_input_dir} {nifti_output_dir} {pre-existing_mask} {pepolar} {species} {subjs_separate_by_space}
echo eg:
echo sh youthptsd_dti_processing.sh /Volumes/Studies/Herringa/YouthPTSD /Volumes/Vol6/YouthPTSD/data/DTI nomask 0 hp _125/
echo
echo pr-existing_mask = mask or nomask, if pre-existing mask is available location in output_dir/MASK or not respectively
echo
echo pepolar = 0 or 1 flip phase encoding direction, 0 is used for squished, 1 is used for stretched raw DWI
echo


else
echo
echo
raw=$1
echo "Input directory: "$raw
PROCESS=$2
echo "Output directory: "$PROCESS
manual_mask=$3
echo "Pre-existing mask: "$manual_mask
pepolar=$4
echo "Pe-polar direction: "$pepolar
species=$5
echo "Species: "$species

shift 5
subject=$*

##echo ~~~Make bvec and bval files~~~
##echo bvec_bval.sh ${PROCESS} 1000 /Volumes/Processing/Oler/Shelton/NOMOM2/r10046.524/dicoms/s04_dti/ dicom
#bvec_bval.sh ${PROCESS} 1000 /Volumes/Vol5/processed_DTI/multisite/UW/P001/dicoms/s12_dti/ dicom

for i in $subject;
do
echo Subject in process: ${i};
subj=`echo $i | tr "." "-"| awk -F"/" '{$1=$1}1' OFS=""`
echo Subject prefix is: ${subj};

#echo ~~~Convert File~~~;
#my_script=/Volumes/Vol6/YouthPTSD/scripts/njk_scripts
#sh $my_script/convert_script_all.sh $raw $PROCESS $i;

cd ${PROCESS}/DTI_RAW
for dti_scan in `ls ${subj}*dti.nii*`;
do
scan=`echo ${dti_scan} | awk 'BEGIN{FS="_"}{print $2}' | awk 'BEGIN{FS="_"}{print $1}' | cut -c2- | sed -e 's:^0*::'`;
number=$(( $scan + 1 ))
prefix=`ls ${dti_scan} | awk 'BEGIN{FS=".nii"}{print $1}'`;
dti_prefix=`ls ${PROCESS}/DTI_RAW/${dti_scan} | awk 'BEGIN{FS=".nii"}{print $1}'`;
echo DTI scan: ${dti_prefix}
#twodfast=`ls ${PROCESS}/2DFAST/${subj}_[sS]*${number}_fmap.nii*`;
#echo 2dfast file: ${twodfast};
#twodfast_raw=`echo ${twodfast}|awk 'BEGIN{FS="2DFAST/"}{print $2}'|awk 'BEGIN{FS="_fmap"}{print $1}'|awk 'BEGIN{FS="_"}{print $2}'`_fmap
#echo 2dfast raw file: ${twodfast_raw};
#fmap_prefix=${PROCESS}/FMAP/`echo ${twodfast}|awk 'BEGIN{FS="2DFAST/"}{print $2}'|awk 'BEGIN{FS="_fmap"}{print $1}'`_fmap;
#echo Fmap file: ${fmap_prefix};
eddy_prefix=${PROCESS}/EDDY/${prefix}_eddy;
echo Eddy file: ${eddy_prefix}
t1_prefix=${PROCESS}/T1/${subj}_T1High;
echo T1 file: ${t1_prefix};
mask_prefix=${PROCESS}/MASK/${subj}_mask
echo Mask file: ${mask_prefix};
corrected_prefix=${PROCESS}/CORRECTED/${prefix}_eddy
echo Corrected file: ${corrected_prefix};
strip_prefix=${corrected_prefix}_strip;
echo Stripped file: ${strip_prefix};
camino_dwi=${PROCESS}/CAMINO/${prefix}_eddy_strip_DWI;
echo Camino DWI file: ${camino_dwi};
camino_dti=${PROCESS}/CAMINO/${prefix}_eddy_strip_rest_DTI;
echo Camino RESTORE DTI file: ${camino_dti};
dt_prefix=${PROCESS}/TENSOR/${prefix}_eddy_strip_rest_;
echo DT output prefix file: ${dt_prefix};

num=`fslinfo ${dti_prefix}.nii.gz |grep ^dim4|awk 'BEGIN{FS="4"}{print $2}'| sed 's/ //g'`
echo Number of dirs: ${num}
b0=`cat ${PROCESS}/info_bvals_${num}.txt|grep b0:|awk 'BEGIN{FS=" "}{print $2}'| sed 's/ //g'`
echo B0: ${b0};
bvalue=`tail -n 1 ${PROCESS}/bvals_${num}.txt| sed 's/ //g'`
echo B-value: ${bvalue};
grad_dir_txt=${PROCESS}/grad_dir_${num}.txt;
echo Grad dir file: ${grad_dir_txt};
snr_txt=${PROCESS}/snr_all.txt;
echo SNR text out: ${snr_txt};
bvec_txt=${PROCESS}/bvecs_${num}.txt;
echo Bvecs text file: ${bvec_txt};
bval_txt=${PROCESS}/bvals_${num}.txt;
echo Bval text file: ${bval_txt};
scheme_txt=${PROCESS}/SCHEME/${prefix}.scheme
echo Scheme text out: ${scheme_txt};
cd ${PROCESS};
echo



#echo ~~~Standardize~~~;
my_script=/Volumes/Vol6/YouthPTSD/scripts/njk_scripts
echo sh $my_script/standardize.sh $PROCESS $species $subj;
sh $my_script/standardize.sh $PROCESS $species $subj;
echo

#echo ~~~Make Scalars~~~;
my_script=/Volumes/Vol6/YouthPTSD/scripts/njk_scripts
echo sh $my_script/make_scalars.sh $PROCESS/TEMPLATE $PROCESS/SCALARS all $subj;
sh $my_script/make_scalars.sh $PROCESS/TEMPLATE $PROCESS/SCALARS all $subj;
echo
echo FINISHED RUNNING THIS SUBJECT - ONWARDS!
echo

done
done
fi
