#!/usr/bin/env bash
cat datastructure_manifest.txt | awk 'NR>2{gsub(/\"|\;/,"",$4); print substr($4,0,19)}' | awk '!x[$0]++' > subj_list.txt

inputsubjlist="subj_list_one.txt"
datamanifest="datastructure_manifest.txt"
schaefer_label="/fast_scratch/jdr/ABCD/Schaefer/fsLR/Schaefer400_7net.32k_fs_LR.dlabel.nii"
pconnout_dir="/fast_scratch/jdr/ABCD/ABCD_3165_Pipe/pconns"
cifticonn="/fast_scratch/jdr/ABCD/ABCD_3165_Pipe/comb_pipe/cifti_conn_wrapper.py"
mre_dir="/fast_scratch/jdr/apps/MCR2016b/v91"

while IFS= read -r line; do
  
  starttime='date +%s.$N'
  echo "$line"
  tempdir="/tmp/${line}.tmp"
  if [ -d "${tempdir}" ]; then
    rm -rf ${tempdir}
  fi
    mkdir ${tempdir}
  
  python3 download.py -i $datamanifest -o ${tempdir} -x $line -l . -d data_subsets.txt

  tempdir_unpkd="${tempdir}/derivatives/abcd-hcp-pipeline/${line}/ses-baselineYear1Arm1/func"
  tempdir_dtseries="${tempdir_unpkd}/${line}_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.dtseries.nii"
  tempdir_ptseries="${tempdir_unpkd}/${line}_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.ptseries.nii"
  tempdir_motionmat="${tempdir_unpkd}/${line}_ses-baselineYear1Arm1_task-rest_desc-filtered_motion_mask.mat"
  tempdir_pconn="${tempdir_unpkd}/${line}_ses-baselineYear1Arm1_task-rest_bold_desc-filtered_timeseries.pconn.nii"
  
  # echo 33 spaces and replace them with 33 @s (best mem usage)
  printf '%*.0s\n' 33 "" | tr " " "@"
  printf 'Starting parcellation of dense time series...\n'
  printf '%*.0s\n' 33 "" | tr " " "@"
  
  wb_command -cifti-parcellate ${tempdir_dtseries} ${schaefer_label} COLUMN ${tempdir_ptseries}
  
  printf '%*.0s\n' 33 "" | tr " " "@"
  printf 'Now creating correlation matrix (with motion thresholding and outlier removal)...\n'
  printf '%*.0s\n' 33 "" | tr " " "@"

  ${cifticonn} -min 5 -m ${tempdir_motionmat} -mre ${mre_dir} -outliers ${tempdir_ptseries} 0.8 ${tempdir_pconn} matrix 

  cp -r ${tempdir_pconn} ${pconnout_dir}
  if [ $? -eq 0 ]; then
    echo "Successfully copied pconn series to permanent storage....now deleting temporary files."
    rm -rf ${tempdir}
  else
    echo "WARNING: COULD NOT COPY PCONN SERIES. TEMPORARY FILES WILL REMAIN (CHECK /TMP)"
  fi
  endtime='date +%s.%N'
  #echo "Finished parcellation and correlation matrix creation in $( echo "($endtime-$starttime)" | bc -l )."

done < "$inputsubjlist"
