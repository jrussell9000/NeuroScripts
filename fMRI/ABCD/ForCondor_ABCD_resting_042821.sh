#!/bin/bash

# ========================================================================================================
# INDIVIDUAL PREPROCESSING for ABCD NBACK TASK
# Adapted by Claire Laubacher for ABCD to run on UW CHTC Codor (Fall 2019)
# Adapted by Claire Laubacher for BIDS format with help from Grace George and Will Wooten (Summer 2019)
# Adapated from extensive work by Taylor Keding, Remi Patriat, Jullian Motzkin (Feb 2016), Rick Wolf (May 2015)
# Last Updated: 03.37.20


#Input files : Should be contained within a ABCD.NBACK.${subjID}_IN.tar.gz file specfied in condor submisison file
	#sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-01_bold.nii 
	#sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-01_events.tsv
	#sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-02_bold.nii 
	#sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-02_events.tsv
	#sub-${subjID}_ses-baselineYear1Arm1_run-01_T1w.nii
	#MNI template 
	#TimingFiles_ABCD.py 

# ./ForCondor_ABCD_resting_042821.sh NDARINV003RTV85 NDARINV003RTV85_baselineYear1Arm1_ABCD-MPROC-T1_20181001100823.tgz NDARINV003RTV85_baselineYear1Arm1_ABCD-MPROC-rsfMRI_20181001101042.tgz NDARINV003RTV85_baselineYear1Arm1_ABCD-MPROC-rsfMRI_20181001101637.tgz NDARINV003RTV85_baselineYear1Arm1_ABCD-MPROC-rsfMRI_20181001103936.tgz NDARINV003RTV85_baselineYear1Arm1_ABCD-MPROC-rsfMRI_20181001104531.tgz

cd /fast_scratch/jdr/ABCD/Testing/Scripting

#Specify incoming arguments
NDARID=$1
T1Scan_tgz="${2##*/}"
rsScan_1_tgz="${3##*/}"
rsScan_2_tgz="${4##*/}"
rsScan_3_tgz="${5##*/}"
rsScan_4_tgz="${6##*/}"

# sub-NDARINV003RTV85/ses-baselineYear1Arm1/func/sub-NDARINV003RTV85_ses-baselineYear1Arm1_task-rest_run-02_bold.nii

subNDARID="sub-${NDARID}"

# echo -e "Unpacking ${T1Scan_tgz}"
# tar -xzf ${T1Scan_tgz} --strip-components=3 --checkpoint=.500
# echo -e "\nUnpacking ${rsScan_1_tgz}"
# tar -xzf ${rsScan_1_tgz} --strip-components=3 --checkpoint=.500
# echo -e "\nUnpacking ${rsScan_2_tgz}"
# tar -xzf ${rsScan_2_tgz} --strip-components=3 --checkpoint=.500
# echo -e "\nUnpacking ${rsScan_3_tgz}"
# tar -xzf ${rsScan_3_tgz} --strip-components=3 --checkpoint=.500
# echo -e "\nUnpacking ${rsScan_4_tgz}"
# tar -xvzf ${rsScan_4_tgz} --strip-components=3 --checkpoint=.500

# rsScan_1="${subNDARID}_ses-baselineYear1Arm1_task-rest_run-01_bold.nii"
# rsScan_2="${subNDARID}_ses-baselineYear1Arm1_task-rest_run-02_bold.nii"
# rsScan_3="${subNDARID}_ses-baselineYear1Arm1_task-rest_run-03_bold.nii"
# rsScan_4="${subNDARID}_ses-baselineYear1Arm1_task-rest_run-04_bold.nii"

rsJSON_1="${subNDARID}_ses-baselineYear1Arm1_task-rest_run-01_bold.json"

rsScan="${subNDARID}_combined.nii"

# 3dTcat ${rsScan_1}[15..$] -prefix ${rsScan_1} -overwrite
# 3dTcat ${rsScan_2}[15..$] -prefix ${rsScan_2} -overwrite
# 3dTcat ${rsScan_3}[15..$] -prefix ${rsScan_3} -overwrite
# 3dTcat ${rsScan_4}[15..$] -prefix ${rsScan_4} -overwrite

# 3dTcat ${rsScan_1} ${rsScan_2} ${rsScan_3} ${rsScan_4} -prefix ${rsScan}

nTRs=$(3dinfo -nt ${rsScan})


regmat_file=${subNDARID}_EPI2T1_regmat.txt

# Pull the EPI-to-T1 registration matrix out of the JSON file and remove characters '[ ] ,'
regmat=$(cat ${rsJSON_1} | python3 -c "import sys, json; regmat = json.load(sys.stdin)['registration_matrix_T1']; print(regmat[0], regmat[1], regmat[2]);" | sed 's/[],[]//g')
# Repeat regmat once for each TR in the combined resting state scan and write to regmat_file
echo $regmat | awk -v nTRs="${nTRs}" '{for(i=1;i<=nTRs;i++){print}}' > ${regmat_file}

# Apply the affine transformation in regmat_file to the combined resting state scan
rsScan_reg2T1="${subNDARID}_combined_reg2T1.nii"
3dAllineate -1Dmatrix_apply ${regmat_file} -prefix ${rsScan_reg2T1} -input ${rsScan}