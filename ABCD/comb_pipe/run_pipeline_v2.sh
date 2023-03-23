#!/usr/bin/env bash

subjid=$1
tr=0.8
fd_thresh=0.2
minutes=8

datamanifest="datastructure_manifest.txt"
schaeferTian_label="/fast_scratch/jdr/atlases/Schaefer300Tian4/Schaefer2018_300Parcels_7Networks_order_Tian_Subcortex_S4.dlabel.nii"
pconnout_dir="/fast_scratch/jdr/ABCD/ABCD_3165_Pipe/Schaefer2018300p_TianS4/pconns_raw"
cifticonn="/fast_scratch/jdr/ABCD/ABCD_3165_Pipe/comb_pipe/cifti_conn_wrapper.py"
mre_dir="/fast_scratch/jdr/apps/MCR2016b/v91"

starttime='date +%s.$N'

tempdir="/tmp/${subjid}.tmp"
if [ -d "${tempdir}" ]; then
  rm -rf ${tempdir}
fi
  mkdir ${tempdir}

python3 download.py -i $datamanifest -o ${tempdir} -x ${subjid} -l . -d data_subsets.txt

tempdir_unpkd="${tempdir}/derivatives/abcd-hcp-pipeline/${subjid}/ses-baselineYear1Arm1/func"
tempdir_dtseries="${tempdir_unpkd}/${subjid}_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.dtseries.nii"
tempdir_ptseries="${tempdir_unpkd}/${subjid}_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.ptseries.nii"
tempdir_motionmat="${tempdir_unpkd}/${subjid}_ses-baselineYear1Arm1_task-rest_desc-filtered_motion_mask.mat"
tempdir_pconn="${tempdir_unpkd}/${subjid}_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.pconn.nii"
faildl_file="${pconnout_dir}/${subjid}_ses-baselineYearArm1_task-rest_bold_ERROR.txt"

# echo 33 spaces and replace them with 33 @s (best mem usage)
printf '%*.0s\n' 33 "" | tr " " "@"
printf 'Starting parcellation of dense time series...\n'
printf '%*.0s\n' 33 "" | tr " " "@"

if [ ! -f ${tempdir_dtseries} ]; then
  rm -rf ${tempdir}
  echo "Dense time series file could not be downloaded." > ${faildl_file}
  exit 1
fi

wb_command -cifti-parcellate ${tempdir_dtseries} ${schaeferTian_label} COLUMN ${tempdir_ptseries}

printf '%*.0s\n' 33 "" | tr " " "@"
printf 'Now creating correlation matrix (with motion thresholding and outlier removal)...\n'
printf '%*.0s\n' 33 "" | tr " " "@"

if [ ! -f ${tempdir_motionmat} ]; then
  rm -rf ${tempdir}
  echo "Motion file could not be downloaded." >>${faildl_file}
  exit 1
fi

${cifticonn} -min ${minutes} -m ${tempdir_motionmat} -mre ${mre_dir} -outliers ${tempdir_ptseries} --fd-threshold ${fd_thresh} ${tr} ${tempdir_pconn} matrix 

cp -r ${tempdir_pconn} ${pconnout_dir}
if [ $? -eq 0 ]; then
  echo "Successfully copied pconn series to permanent storage....now deleting temporary files."
  rm -rf ${tempdir}
else
  echo "WARNING: PCONN series not found. Maybe subject didn't have enough data?" >> ${faildl_file}
  rm -rf ${tempdir}
fi
endtime='date +%s.%N'

