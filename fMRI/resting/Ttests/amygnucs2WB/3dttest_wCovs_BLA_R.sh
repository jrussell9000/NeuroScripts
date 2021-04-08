#!/bin/bash

data=/fast_scratch/jdr/resting/BIDS_fmriprep/fmriprep 

3dttest++ -setA noPTSD sub-003	${data}/sub-003/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-004	${data}/sub-004/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-006	${data}/sub-006/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-009	${data}/sub-009/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-011	${data}/sub-011/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-014	${data}/sub-014/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-042	${data}/sub-042/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-043	${data}/sub-043/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-044	${data}/sub-044/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-057	${data}/sub-057/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-058	${data}/sub-058/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-059	${data}/sub-059/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-060	${data}/sub-060/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-061	${data}/sub-061/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-062	${data}/sub-062/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-064	${data}/sub-064/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-071	${data}/sub-071/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-076	${data}/sub-076/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-085	${data}/sub-085/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-087	${data}/sub-087/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-090	${data}/sub-090/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-092	${data}/sub-092/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-093	${data}/sub-093/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-094	${data}/sub-094/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-097	${data}/sub-097/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-099	${data}/sub-099/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-100	${data}/sub-100/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-106	${data}/sub-106/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-117	${data}/sub-117/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-125	${data}/sub-125/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-128	${data}/sub-128/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-134	${data}/sub-134/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-135	${data}/sub-135/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-142	${data}/sub-142/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-148	${data}/sub-148/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-156	${data}/sub-156/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-157	${data}/sub-157/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
-setB yesPTSD	sub-012	${data}/sub-012/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-019	${data}/sub-019/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-021	${data}/sub-021/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-024	${data}/sub-024/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-026	${data}/sub-026/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-028	${data}/sub-028/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-031	${data}/sub-031/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-036	${data}/sub-036/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-041	${data}/sub-041/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-045	${data}/sub-045/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-050	${data}/sub-050/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-065	${data}/sub-065/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-068	${data}/sub-068/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-070	${data}/sub-070/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-073	${data}/sub-073/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-075	${data}/sub-075/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-078	${data}/sub-078/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-079	${data}/sub-079/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-082	${data}/sub-082/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-084	${data}/sub-084/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-086	${data}/sub-086/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-091	${data}/sub-091/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-104	${data}/sub-104/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-108	${data}/sub-108/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-118	${data}/sub-118/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-122	${data}/sub-122/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-124	${data}/sub-124/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-127	${data}/sub-127/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-129	${data}/sub-129/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-132	${data}/sub-132/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-133	${data}/sub-133/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-138	${data}/sub-138/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-139	${data}/sub-139/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-146	${data}/sub-146/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-147	${data}/sub-147/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-151	${data}/sub-151/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-153	${data}/sub-153/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-154	${data}/sub-154/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
			sub-155	${data}/sub-155/ses-01/func/fconn/WB_Z_BLA_R.nii.gz \
-mask '/fast_scratch/tjk/PNC/seeds/MNI152_T1_2mm_brain.nii.gz' \
-covariates covariates.txt \
-BminusA \
-prefix 3dttest_wCovs_BLA_R
