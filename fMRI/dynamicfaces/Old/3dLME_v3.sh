#!/bin/bash

datadir='/fast_scratch/jdr/dynamicfaces/GroupAnalysis'

3dLME -prefix /fast_scratch/jdr/dynamicfaces/GroupAnalysis_v3 \
-jobs 48 \
-model "GroupT1*Condition+Age_T1+Sex" \
-qVars "Age_T1" \
-mask /fast_scratch/jdr/dynamicfaces/BIDS_fmriprep/fmriprep/masks/longitudinal/full_mask.nii \
-ranEff '~1+Condition' \
-SS_type 3 \
-dataTable \
Subj	Age_T1	Sex	GroupT2	GroupT1	Time	Condition	InputFile	\
sub-011	14.31	M	Control	Control	1	angry	${datadir}/sub-011_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-011	14.31	M	Control	Control	1	happy	${datadir}/sub-011_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-011	14.31	M	Control	Control	1	shape	${datadir}/sub-011_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-019	12.66	F	PTSD	PTSD	1	angry	${datadir}/sub-019_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-019	12.66	F	PTSD	PTSD	1	happy	${datadir}/sub-019_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-019	12.66	F	PTSD	PTSD	1	shape	${datadir}/sub-019_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-020	14.63	M	Remit	PTSD	1	angry	${datadir}/sub-020_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-020	14.63	M	Remit	PTSD	1	happy	${datadir}/sub-020_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-020	14.63	M	Remit	PTSD	1	shape	${datadir}/sub-020_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-021	11.04	F	Remit	PTSD	1	angry	${datadir}/sub-021_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-021	11.04	F	Remit	PTSD	1	happy	${datadir}/sub-021_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-021	11.04	F	Remit	PTSD	1	shape	${datadir}/sub-021_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-024	14.58	M	PTSD	PTSD	1	angry	${datadir}/sub-024_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-024	14.58	M	PTSD	PTSD	1	happy	${datadir}/sub-024_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-024	14.58	M	PTSD	PTSD	1	shape	${datadir}/sub-024_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-026	16.68	F	Remit	PTSD	1	angry	${datadir}/sub-026_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-026	16.68	F	Remit	PTSD	1	happy	${datadir}/sub-026_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-026	16.68	F	Remit	PTSD	1	shape	${datadir}/sub-026_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-029	18.8	F	PTSD	PTSD	1	angry	${datadir}/sub-029_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-029	18.8	F	PTSD	PTSD	1	happy	${datadir}/sub-029_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-029	18.8	F	PTSD	PTSD	1	shape	${datadir}/sub-029_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-036	14.85	M	Remit	PTSD	1	angry	${datadir}/sub-036_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-036	14.85	M	Remit	PTSD	1	happy	${datadir}/sub-036_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-036	14.85	M	Remit	PTSD	1	shape	${datadir}/sub-036_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-041	12.74	F	PTSD	PTSD	1	angry	${datadir}/sub-041_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-041	12.74	F	PTSD	PTSD	1	happy	${datadir}/sub-041_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-041	12.74	F	PTSD	PTSD	1	shape	${datadir}/sub-041_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-042	14.13	M	Control	Control	1	angry	${datadir}/sub-042_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-042	14.13	M	Control	Control	1	happy	${datadir}/sub-042_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-042	14.13	M	Control	Control	1	shape	${datadir}/sub-042_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-043	17.15	F	Control	Control	1	angry	${datadir}/sub-043_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-043	17.15	F	Control	Control	1	happy	${datadir}/sub-043_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-043	17.15	F	Control	Control	1	shape	${datadir}/sub-043_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-045	16.07	F	PTSD	PTSD	1	angry	${datadir}/sub-045_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-045	16.07	F	PTSD	PTSD	1	happy	${datadir}/sub-045_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-045	16.07	F	PTSD	PTSD	1	shape	${datadir}/sub-045_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-058	11.28	F	Control	Control	1	angry	${datadir}/sub-058_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-058	11.28	F	Control	Control	1	happy	${datadir}/sub-058_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-058	11.28	F	Control	Control	1	shape	${datadir}/sub-058_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-060	16.62	F	Control	Control	1	angry	${datadir}/sub-060_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-060	16.62	F	Control	Control	1	happy	${datadir}/sub-060_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-060	16.62	F	Control	Control	1	shape	${datadir}/sub-060_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-061	15.44	F	Control	Control	1	angry	${datadir}/sub-061_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-061	15.44	F	Control	Control	1	happy	${datadir}/sub-061_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-061	15.44	F	Control	Control	1	shape	${datadir}/sub-061_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-068	14.28	M	PTSD	PTSD	1	angry	${datadir}/sub-068_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-068	14.28	M	PTSD	PTSD	1	happy	${datadir}/sub-068_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-068	14.28	M	PTSD	PTSD	1	shape	${datadir}/sub-068_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-071	10.8	F	Control	Control	1	angry	${datadir}/sub-071_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-071	10.8	F	Control	Control	1	happy	${datadir}/sub-071_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-071	10.8	F	Control	Control	1	shape	${datadir}/sub-071_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-075	8.07	F	Remit	PTSD	1	angry	${datadir}/sub-075_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-075	8.07	F	Remit	PTSD	1	happy	${datadir}/sub-075_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-075	8.07	F	Remit	PTSD	1	shape	${datadir}/sub-075_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-076	11.58	M	Control	Control	1	angry	${datadir}/sub-076_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-076	11.58	M	Control	Control	1	happy	${datadir}/sub-076_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-076	11.58	M	Control	Control	1	shape	${datadir}/sub-076_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-078	17.85	F	PTSD	PTSD	1	angry	${datadir}/sub-078_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-078	17.85	F	PTSD	PTSD	1	happy	${datadir}/sub-078_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-078	17.85	F	PTSD	PTSD	1	shape	${datadir}/sub-078_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-079	14.82	F	PTSD	PTSD	1	angry	${datadir}/sub-079_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-079	14.82	F	PTSD	PTSD	1	happy	${datadir}/sub-079_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-079	14.82	F	PTSD	PTSD	1	shape	${datadir}/sub-079_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-081	14.67	M	Control	Control	1	angry	${datadir}/sub-081_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-081	14.67	M	Control	Control	1	happy	${datadir}/sub-081_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-081	14.67	M	Control	Control	1	shape	${datadir}/sub-081_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-082	15.93	F	PTSD	PTSD	1	angry	${datadir}/sub-082_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-082	15.93	F	PTSD	PTSD	1	happy	${datadir}/sub-082_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-082	15.93	F	PTSD	PTSD	1	shape	${datadir}/sub-082_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-084	17.99	F	Remit	PTSD	1	angry	${datadir}/sub-084_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-084	17.99	F	Remit	PTSD	1	happy	${datadir}/sub-084_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-084	17.99	F	Remit	PTSD	1	shape	${datadir}/sub-084_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-085	11.39	F	Control	Control	1	angry	${datadir}/sub-085_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-085	11.39	F	Control	Control	1	happy	${datadir}/sub-085_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-085	11.39	F	Control	Control	1	shape	${datadir}/sub-085_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-087	15.31	F	Control	Control	1	angry	${datadir}/sub-087_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-087	15.31	F	Control	Control	1	happy	${datadir}/sub-087_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-087	15.31	F	Control	Control	1	shape	${datadir}/sub-087_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-090	14.58	M	Control	Control	1	angry	${datadir}/sub-090_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-090	14.58	M	Control	Control	1	happy	${datadir}/sub-090_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-090	14.58	M	Control	Control	1	shape	${datadir}/sub-090_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-091	11.63	M	Remit	PTSD	1	angry	${datadir}/sub-091_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-091	11.63	M	Remit	PTSD	1	happy	${datadir}/sub-091_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-091	11.63	M	Remit	PTSD	1	shape	${datadir}/sub-091_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-093	13.07	F	Control	Control	1	angry	${datadir}/sub-093_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-093	13.07	F	Control	Control	1	happy	${datadir}/sub-093_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-093	13.07	F	Control	Control	1	shape	${datadir}/sub-093_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-094	17.51	F	Control	Control	1	angry	${datadir}/sub-094_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-094	17.51	F	Control	Control	1	happy	${datadir}/sub-094_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-094	17.51	F	Control	Control	1	shape	${datadir}/sub-094_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-097	17.99	F	Control	Control	1	angry	${datadir}/sub-097_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-097	17.99	F	Control	Control	1	happy	${datadir}/sub-097_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-097	17.99	F	Control	Control	1	shape	${datadir}/sub-097_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-099	16.23	F	Control	Control	1	angry	${datadir}/sub-099_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-099	16.23	F	Control	Control	1	happy	${datadir}/sub-099_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-099	16.23	F	Control	Control	1	shape	${datadir}/sub-099_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-100	12.04	F	Control	Control	1	angry	${datadir}/sub-100_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-100	12.04	F	Control	Control	1	happy	${datadir}/sub-100_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-100	12.04	F	Control	Control	1	shape	${datadir}/sub-100_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-106	10.48	M	Control	Control	1	angry	${datadir}/sub-106_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-106	10.48	M	Control	Control	1	happy	${datadir}/sub-106_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-106	10.48	M	Control	Control	1	shape	${datadir}/sub-106_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-112	12.48	F	Control	Control	1	angry	${datadir}/sub-112_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-112	12.48	F	Control	Control	1	happy	${datadir}/sub-112_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-112	12.48	F	Control	Control	1	shape	${datadir}/sub-112_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-117	12.36	F	Control	Control	1	angry	${datadir}/sub-117_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-117	12.36	F	Control	Control	1	happy	${datadir}/sub-117_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-117	12.36	F	Control	Control	1	shape	${datadir}/sub-117_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-118	17.68	M	Remit	PTSD	1	angry	${datadir}/sub-118_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-118	17.68	M	Remit	PTSD	1	happy	${datadir}/sub-118_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-118	17.68	M	Remit	PTSD	1	shape	${datadir}/sub-118_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-122	14.24	F	Remit	PTSD	1	angry	${datadir}/sub-122_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-122	14.24	F	Remit	PTSD	1	happy	${datadir}/sub-122_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-122	14.24	F	Remit	PTSD	1	shape	${datadir}/sub-122_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-124	16.39	F	PTSD	PTSD	1	angry	${datadir}/sub-124_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-124	16.39	F	PTSD	PTSD	1	happy	${datadir}/sub-124_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-124	16.39	F	PTSD	PTSD	1	shape	${datadir}/sub-124_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-125	15.61	F	Control	Control	1	angry	${datadir}/sub-125_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-125	15.61	F	Control	Control	1	happy	${datadir}/sub-125_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-125	15.61	F	Control	Control	1	shape	${datadir}/sub-125_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-134	15.75	F	Control	Control	1	angry	${datadir}/sub-134_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-134	15.75	F	Control	Control	1	happy	${datadir}/sub-134_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-134	15.75	F	Control	Control	1	shape	${datadir}/sub-134_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-135	14.84	M	Control	Control	1	angry	${datadir}/sub-135_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-135	14.84	M	Control	Control	1	happy	${datadir}/sub-135_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-135	14.84	M	Control	Control	1	shape	${datadir}/sub-135_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-139	17.17	F	PTSD	PTSD	1	angry	${datadir}/sub-139_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-139	17.17	F	PTSD	PTSD	1	happy	${datadir}/sub-139_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-139	17.17	F	PTSD	PTSD	1	shape	${datadir}/sub-139_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-140	12.5	M	Control	Control	1	angry	${datadir}/sub-140_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-140	12.5	M	Control	Control	1	happy	${datadir}/sub-140_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-140	12.5	M	Control	Control	1	shape	${datadir}/sub-140_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-142	9.63	F	Control	Control	1	angry	${datadir}/sub-142_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-142	9.63	F	Control	Control	1	happy	${datadir}/sub-142_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-142	9.63	F	Control	Control	1	shape	${datadir}/sub-142_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-148	17.84	F	Control	Control	1	angry	${datadir}/sub-148_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-148	17.84	F	Control	Control	1	happy	${datadir}/sub-148_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-148	17.84	F	Control	Control	1	shape	${datadir}/sub-148_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-153	16.85	F	PTSD	PTSD	1	angry	${datadir}/sub-153_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-153	16.85	F	PTSD	PTSD	1	happy	${datadir}/sub-153_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-153	16.85	F	PTSD	PTSD	1	shape	${datadir}/sub-153_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-154	17.09	F	PTSD	PTSD	1	angry	${datadir}/sub-154_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-154	17.09	F	PTSD	PTSD	1	happy	${datadir}/sub-154_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-154	17.09	F	PTSD	PTSD	1	shape	${datadir}/sub-154_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-155	10.06	M	Remit	PTSD	1	angry	${datadir}/sub-155_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-155	10.06	M	Remit	PTSD	1	happy	${datadir}/sub-155_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-155	10.06	M	Remit	PTSD	1	shape	${datadir}/sub-155_ses-01_betas_motionDerivs.nii.gz'[shape#0]'	\
sub-156	17.97	F	Control	Control	1	angry	${datadir}/sub-156_ses-01_betas_motionDerivs.nii.gz'[angry#0]'	\
sub-156	17.97	F	Control	Control	1	happy	${datadir}/sub-156_ses-01_betas_motionDerivs.nii.gz'[happy#0]'	\
sub-156	17.97	F	Control	Control	1	shape	${datadir}/sub-156_ses-01_betas_motionDerivs.nii.gz'[shape#0]'