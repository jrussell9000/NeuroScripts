#!/bin/tcsh

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

#Specified by text file referenced in submit file
set subjID=$1
set date1=$2
set date2=$3
set date3=$4
set wd = $PWD
set template = MNI152_2009_template.nii
set task=nback
set runs=( '01' '02' )
set baserun = '_run-01_bold'
#Align step and volume registration step expects run 1 to be called 
#${BidsPrefix}${task}${baserun}.trim.DSPK.tshft+orig
#See line 78 for details 
set BidsPrefix="sub-${subjID}_ses-baselineYear1Arm1"

#Move the files you need to process the images
tar -xzvf ${subjID}_baselineYear1Arm1_ABCD-MPROC-nBack-fMRI_${date1}.tgz
tar -xzvf ${subjID}_baselineYear1Arm1_ABCD-MPROC-nBack-fMRI_${date2}.tgz
mv sub-${subjID}/ses-baselineYear1Arm1/func/sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-01_bold.nii ${PWD}/
mv sub-${subjID}/ses-baselineYear1Arm1/func/sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-01_events.tsv ${PWD}/
mv sub-${subjID}/ses-baselineYear1Arm1/func/sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-01_motion.tsv ${PWD}/
mv sub-${subjID}/ses-baselineYear1Arm1/func/sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-02_bold.nii ${PWD}/
mv sub-${subjID}/ses-baselineYear1Arm1/func/sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-02_events.tsv ${PWD}/
mv sub-${subjID}/ses-baselineYear1Arm1/func/sub-${subjID}_ses-baselineYear1Arm1_task-nback_run-02_motion.tsv ${PWD}/
rm ${subjID}_baselineYear1Arm1_ABCD-MPROC-nBack-fMRI_${date1}.tgz
rm ${subjID}_baselineYear1Arm1_ABCD-MPROC-nBack-fMRI_${date2}.tgz

tar -xzvf ${subjID}_baselineYear1Arm1_ABCD-MPROC-T1_${date3}.tgz
mv sub-${subjID}/ses-baselineYear1Arm1/anat/sub-${subjID}_ses-baselineYear1Arm1_run-01_T1w.nii ${PWD}/

rm ${subjID}_baselineYear1Arm1_ABCD-MPROC-T1_${date3}.tgz
rm -r sub-${subjID}

set TR = `3dinfo -tr  ${BidsPrefix}_task-${task}${baserun}.nii`
set NT = `3dinfo -nt  ${BidsPrefix}_task-${task}${baserun}.nii`

python3 TimingFiles_ABCD.py ${subjID} ${TR} ${NT}
chmod +rwx ConditionCommands.${subjID}.csh


foreach run (${runs})

	set epiPrefix="${BidsPrefix}_task-${task}_run-${run}_bold"
	set anatPrefix="${BidsPrefix}_run-01_T1w"
		
	set TR = `3dinfo -tr ${epiPrefix}.nii`

	#Reorient functional and structual image to LPI space 
	
	3daxialize -orient 'LPI' -prefix ${epiPrefix}.LPI ${epiPrefix}.nii
	if (! -e ${anatPrefix}.LPI+orig.BRIK) then
		3daxialize -orient 'LPI' -prefix ${anatPrefix}.LPI ${anatPrefix}.nii
	endif				
	
	#Removing first 3 TRs

	3dTcat -prefix ${epiPrefix}.trim ${epiPrefix}.LPI+orig'[3..$]'
	
	#echo outlier detection
	
	3dToutcount -automask -fraction -polort 5 -legendre ${epiPrefix}.trim+orig > ${epiPrefix}.outcount.1D
		# Censor outlier TRs per run, ignoring the first 0 TRs
		# - censor when more than 0.1 of automask voxels are outliers
		# - step() defines which TRs to remove via censoring
	1deval -a ${epiPrefix}.outcount.1D -expr "1-step(a-0.1)" > ${epiPrefix}.rm.out.cen.1D
							
		# Catenate outlier counts into a single time series
	cat ${epiPrefix}.outcount.1D > ${epiPrefix}.outcount_rall.1D

		# Catenate outlier censor files into a single time series
	cat ${epiPrefix}.rm.out.cen.1D > ${epiPrefix}.outcount_censor.1D
	rm ${epiPrefix}.rm.out.cen.1D

	# despiking
	3dDespike -overwrite -prefix ${epiPrefix}.trim.DSPK ${epiPrefix}.trim+orig
	rm ${epiPrefix}.trim+orig*
	
	#slice timing correction
	3dTshift -ignore 1 -tzero 0 -quintic -TR ${TR} -prefix ${epiPrefix}.trim.DSPK.tshft ${epiPrefix}.trim.DSPK+orig
	rm ${epiPrefix}.trim.DSPK+orig*

	# align structural to EPI 
	
	if (! -e ${BidsPrefix}_task-${task}${baserun}.trim.DSPK.tshft_al_junk_mat.aff12.1D) then
		#Align only the first run to the structural, apply transformation to subsequent runs bellow
		align_epi_anat.py -epi2anat -anat ${anatPrefix}.LPI+orig \
			-save_skullstrip -suffix _al_junk -overwrite \
			-epi ${BidsPrefix}_task-${task}${baserun}.trim.DSPK.tshft+orig -epi_base 2 \
			-epi_strip 3dSkullStrip \
			-anat_has_skull yes \
			-cost lpc+ZZ -giant_move \
			-volreg off -tshift off -check_flip
		
	#06/17/19 changed anat2epi to epi2anat 
	#concatenate volreg and epi2anat transformations 
	#-I (was an inverse when align step was anta2epi, changed 6/26/19)
	endif 

	# motion correction and volReg
	#Align all other runs to run 1, vol2  
	3dvolreg -verbose -zpad 1 -base ${BidsPrefix}_task-${task}${baserun}.trim.DSPK.tshft+orig'[2]' \
		-1Dfile ${epiPrefix}.motion.1D -prefix ${epiPrefix}.trim.DSPK.tshft.motion \
		-cubic \
		-1Dmatrix_save ${epiPrefix}.mat.vr.aff12.1D \
		${epiPrefix}.trim.DSPK.tshft+orig

	cat_matvec -ONELINE \
		${BidsPrefix}_task-${task}${baserun}.trim.DSPK.tshft_al_junk_mat.aff12.1D \
		${epiPrefix}.mat.vr.aff12.1D > ${epiPrefix}.mat.warp.aff12.1D

	# apply catenated xform : volreg and epi2anat
	3dAllineate -base ${anatPrefix}.LPI_ns+orig \
		-input ${epiPrefix}.trim.DSPK.tshft+orig \
		-1Dmatrix_apply ${epiPrefix}.mat.warp.aff12.1D \
		-prefix ${epiPrefix}.volreg \
		-quiet -mast_dxyz 2  
	#2 is grid spacing, 2x2x2 grid and make sure it stays the same for later 
	# Previously created an all-1 dataset to mask the extents of the warp
	# Goal: have only voxels with data 

	rm ${epiPrefix}.trim.DSPK.tshft.motion+orig*
	
	# making motion regressors
	# Compute de-meaned motion parameters (for use in regression)
	1d_tool.py -infile ${epiPrefix}.motion.1D -set_nruns 1 -overwrite -demean -write ${epiPrefix}.motion_demean.1D

	# Compute motion parameter derivatives
	1d_tool.py -infile ${epiPrefix}.motion.1D -set_nruns 1 -overwrite -derivative \
		-write ${epiPrefix}.motion_deriv.1D
	
	# Demean motion parameter derivatives
	1d_tool.py -infile ${epiPrefix}.motion.1D -set_nruns 1 -overwrite -derivative -demean \
		-write ${epiPrefix}.motion_deriv_demean.1D

	#Concatonate motion files for 3dDeconvolve happens in step3.csh
	
	# Create censor file motion_${subj}_censor.1D, for censoring motion 
	1d_tool.py -infile ${epiPrefix}.motion.1D -set_nruns 1 -overwrite -show_censor_count -censor_prev_TR \
		-censor_motion 0.9 ${epiPrefix}.motion
	

	# Combine multiple censor files
	1deval -a ${epiPrefix}.motion_censor.1D -b ${epiPrefix}.outcount_censor.1D \
		-expr "a*b" > ${epiPrefix}.censor_combined_1.1D	
	#To concatenate all runs
	cat ${epiPrefix}.censor_combined_1.1D >> ${BidsPrefix}_task-${task}_bold.censor_all.1D 
	
	#echo masking and regression prep		
	# create 'full_mask' dataset (union mask)
	3dAutomask -dilate 1 -prefix ${epiPrefix}.rm.mask ${epiPrefix}.volreg+orig	
	
	# create union of inputs, output type is byte							
	3dmask_tool -inputs ${epiPrefix}.rm.mask+orig -union -prefix ${epiPrefix}.full_mask

	# ---- create subject anatomy mask, mask_anat.$subj+orig ----
	#      (resampled from aligned anat)
	if (! -e ${anatPrefix}.mask_anat+orig.BRIK) then        
		3dresample -master ${epiPrefix}.full_mask+orig -input ${anatPrefix}.LPI_ns+orig \
			-prefix ${anatPrefix}.rm.resam.anat

		# convert to binary anat mask; fill gaps and holes
		3dmask_tool -dilate_input 5 -5 -fill_holes -input ${anatPrefix}.rm.resam.anat+orig \
			-prefix ${anatPrefix}.mask_anat
	endif
	# compute overlaps between anat and EPI masks
	3dABoverlap -no_automask ${epiPrefix}.full_mask+orig ${anatPrefix}.mask_anat+orig \
		|& tee ${epiPrefix}.out.mask_ae_overlap.txt

	# note Dice coefficient of masks, as well
	3ddot -dodice ${epiPrefix}.full_mask+orig ${anatPrefix}.mask_anat+orig \
		|& tee ${epiPrefix}.out.mask_ae_dice.txt	


	# ---- segment anatomy into classes CSF/GM/WM ----
	if (! -e ${wd}/Segsy/Anat+orig.BRIK) then 
		3dSeg -anat ${anatPrefix}.LPI_ns+orig -mask AUTO -classes 'CSF ; GM ; WM'

		# copy resulting Classes dataset to current directory
		3dcopy ${wd}/Segsy/Classes ${wd}/Classes
	endif 
	# make individual ROI masks for regression (CSF GM WM and CSFe GMe WM)						
	foreach class ( CSF GM WM )
		if (! -e ${anatPrefix}.mask_GM+orig.BRIK) then 
				3dmask_tool -input ${wd}/Classes+orig"<$class>" \
					-prefix ${anatPrefix}.mask_${class}

		endif	
				# unitize and resample individual class mask from composite
				3dmask_tool -input ${wd}/Classes+orig"<$class>" \
					-prefix ${epiPrefix}.rm.mask_${class}

				3dresample -master ${epiPrefix}.volreg+orig -rmode NN \
					-input ${epiPrefix}.rm.mask_${class}+orig -prefix ${epiPrefix}.mask_${class}_resam
									
				# also, generate eroded masks
									
				3dmask_tool -input ${wd}/Classes+orig"<$class>" -dilate_input -1  \
					-prefix ${epiPrefix}.rm.mask_${class}e
									
				3dresample -master ${epiPrefix}.volreg+orig -rmode NN \
					-input ${epiPrefix}.rm.mask_${class}e+orig -prefix ${epiPrefix}.mask_${class}e_resam
		
	end

	rm *bold.rm.mask*
	rm *rm.resam*

	3dmaskave -quiet -mask ${epiPrefix}.mask_WMe_resam+orig \
		${epiPrefix}.volreg+orig \
		| 1d_tool.py -infile - -demean -write ${epiPrefix}.ROI.WMe.1D
	cat ${epiPrefix}.ROI.WMe.1D >> ${BidsPrefix}_task-${task}_bold.ROI.WMe.1D

	3dmaskave -quiet -mask ${epiPrefix}.mask_CSFe_resam+orig \
		${epiPrefix}.volreg+orig  \
		| 1d_tool.py -infile - -demean -write ${epiPrefix}.ROI.CSFe.1D
	cat ${epiPrefix}.ROI.CSFe.1D >> ${BidsPrefix}_task-${task}_bold.ROI.CSFe.1D
	
#End run loop
end	

				
	rm -f ${epiPrefix}.rm.mask*
	rm *LPI+orig*
	rm *bold.trim.DSPK.tshft+orig*
	rm *al_junk*
	rm -r Segsy
	rm Classes*
	rm *mask_CSF*HEAD
	rm *mask_CSF*BRIK
	rm *rm.resam*
	
	#Quality control motion check
	echo "Creating motion check"
	set motionFile = ${BidsPrefix}_task-${task}_bold.censor_all.1D 
	#Counts number of characters in file 
	set NT = `wc -l < ${motionFile}`
	set notCensored   = `1dsum ${motionFile}`
	set totalCensor   = `ccalc -form int -expr "${NT}-${notCensored}"` 
	set percentCensor = `ccalc -expr "${totalCensor}/(${NT})*100"`
	
	echo "Total Volumes Censored: ${totalCensor} Percent of Volumes Censored: ${percentCensor}" >> ${subjID}.QC.txt
	set diceepianatrun1 = `3ddot -dodice ${BidsPrefix}_task-${task}_run-01_bold.full_mask+orig ${anatPrefix}.mask_anat+orig`
	set diceepianatrun2 = `3ddot -dodice ${BidsPrefix}_task-${task}_run-01_bold.full_mask+orig ${anatPrefix}.mask_anat+orig`
	echo "Dice coef epi-anat run 1: ${diceepianatrun1} Dice coef epi-anat run 2: ${diceepianatrun2}" >> ${subjID}.QC.txt

echo --------------------------------

set epiPrefix=${BidsPrefix}_task-${task}_bold

#Model task activity
	echo --------------------------------
	echo 3dDeconvolve to model activity 
	echo --------------------------------

	#Create concatenated motion regressors 
	sed 's/$/ 0 0 0 0 0 0/g' ${BidsPrefix}_task-${task}_run-01_bold.motion_demean.1D > ${epiPrefix}.motion_demean_all.txt
	mv ${epiPrefix}.motion_demean_all.txt ${epiPrefix}.motion_demean_all.1D
	sed 's/^/ 0 0 0 0 0 0/g' ${BidsPrefix}_task-${task}_run-02_bold.motion_demean.1D >> ${epiPrefix}.motion_demean_all.1D

	sed 's/$/ 0 0 0 0 0 0/g' ${BidsPrefix}_task-${task}_run-01_bold.motion_deriv_demean.1D > ${epiPrefix}.motion_deriv_demean_all.txt
	mv ${epiPrefix}.motion_deriv_demean_all.txt ${epiPrefix}.motion_deriv_demean_all.1D
	sed 's/^/ 0 0 0 0 0 0/g' ${BidsPrefix}_task-${task}_run-02_bold.motion_deriv_demean.1D >> ${epiPrefix}.motion_deriv_demean_all.1D

	3dDeconvolve \
		-input ${BidsPrefix}_task-${task}_run-01_bold.volreg+orig \
			${BidsPrefix}_task-${task}_run-02_bold.volreg+orig \
		-censor ${epiPrefix}.censor_all.1D \
		-ortvec ${epiPrefix}.ROI.WMe.1D ROI.WMe \
		-ortvec ${epiPrefix}.ROI.CSFe.1D ROI.CSFe \
		-polort A \
		-num_stimts 33 \
			-stim_file 1 ${epiPrefix}.motion_demean_all.1D'[0]' -stim_base 1 -stim_label 1 roll1 \
			-stim_file 2 ${epiPrefix}.motion_demean_all.1D'[1]' -stim_base 2 -stim_label 2 pitch1 \
			-stim_file 3 ${epiPrefix}.motion_demean_all.1D'[2]' -stim_base 3 -stim_label 3 yaw1 \
			-stim_file 4 ${epiPrefix}.motion_demean_all.1D'[3]' -stim_base 4 -stim_label 4 dS1 \
			-stim_file 5 ${epiPrefix}.motion_demean_all.1D'[4]' -stim_base 5 -stim_label 5 dL1 \
			-stim_file 6 ${epiPrefix}.motion_demean_all.1D'[5]' -stim_base 6 -stim_label 6 dP1 \
			-stim_file 7 ${epiPrefix}.motion_deriv_demean_all.1D'[0]' -stim_base 7 -stim_label 7 roll_deriv1 \
			-stim_file 8 ${epiPrefix}.motion_deriv_demean_all.1D'[1]' -stim_base 8 -stim_label 8 pitch_deriv1 \
			-stim_file 9 ${epiPrefix}.motion_deriv_demean_all.1D'[2]' -stim_base 9 -stim_label 9 yaw_deriv1 \
			-stim_file 10 ${epiPrefix}.motion_deriv_demean_all.1D'[3]' -stim_base 10 -stim_label 10 dS_deriv1 \
			-stim_file 11 ${epiPrefix}.motion_deriv_demean_all.1D'[4]' -stim_base 11 -stim_label 11 dL_deriv1 \
			-stim_file 12 ${epiPrefix}.motion_deriv_demean_all.1D'[5]' -stim_base 12 -stim_label 12 dP_deriv1 \
			-stim_file 13 ${epiPrefix}.motion_demean_all.1D'[6]' -stim_base 13 -stim_label 13 roll2 \
			-stim_file 14 ${epiPrefix}.motion_demean_all.1D'[7]' -stim_base 14 -stim_label 14 pitch2 \
			-stim_file 15 ${epiPrefix}.motion_demean_all.1D'[8]' -stim_base 15 -stim_label 15 yaw2 \
			-stim_file 16 ${epiPrefix}.motion_demean_all.1D'[9]' -stim_base 16 -stim_label 16 dS2 \
			-stim_file 17 ${epiPrefix}.motion_demean_all.1D'[10]' -stim_base 17 -stim_label 17 dL2 \
			-stim_file 18 ${epiPrefix}.motion_demean_all.1D'[11]' -stim_base 18 -stim_label 18 dP2 \
			-stim_file 19 ${epiPrefix}.motion_deriv_demean_all.1D'[6]' -stim_base 19 -stim_label 19 roll_deriv2 \
			-stim_file 20 ${epiPrefix}.motion_deriv_demean_all.1D'[7]' -stim_base 20 -stim_label 20 pitch_deriv2 \
			-stim_file 21 ${epiPrefix}.motion_deriv_demean_all.1D'[8]' -stim_base 21 -stim_label 21 yaw_deriv2 \
			-stim_file 22 ${epiPrefix}.motion_deriv_demean_all.1D'[9]' -stim_base 22 -stim_label 22 dS_deriv2 \
			-stim_file 23 ${epiPrefix}.motion_deriv_demean_all.1D'[10]' -stim_base 23 -stim_label 23 dL_deriv2 \
			-stim_file 24 ${epiPrefix}.motion_deriv_demean_all.1D'[11]' -stim_base 24 -stim_label 24 dP_deriv2 \
			-stim_times 25 ${subjID}_nback_cue.stimtime 'GAM(8.6,.547,2.890)' -stim_label 25 CUE \
			-stim_times 26 ${subjID}_nback_0_back_negface.stimtime 'GAM(8.6,.547,1.900)' -stim_label 26 0_NEG \
			-stim_times 27 ${subjID}_nback_0_back_neutface.stimtime 'GAM(8.6,.547,1.900)' -stim_label 27 0_NEU \
			-stim_times 28 ${subjID}_nback_0_back_posface.stimtime 'GAM(8.6,.547,1.900)' -stim_label 28 0_POS \
			-stim_times 29 ${subjID}_nback_0_back_place.stimtime 'GAM(8.6,.547,1.900)' -stim_label 29 0_PLACE \
			-stim_times 30 ${subjID}_nback_2_back_negface.stimtime 'GAM(8.6,.547,1.900)' -stim_label 30 2_NEG \
			-stim_times 31 ${subjID}_nback_2_back_neutface.stimtime 'GAM(8.6,.547,1.900)' -stim_label 31 2_NEU \
			-stim_times 32 ${subjID}_nback_2_back_posface.stimtime 'GAM(8.6,.547,1.900)' -stim_label 32 2_POS \
			-stim_times 33 ${subjID}_nback_2_back_place.stimtime 'GAM(8.6,.547,1.900)' -stim_label 33 2_PLACE \
		-fout -tout \
		-mask ${anatPrefix}.mask_anat+orig \
		-cbucket ${epiPrefix}.act.betas \
		-errts ${epiPrefix}.act.errts \
		-x1D ${epiPrefix}.act.betas.xmat.1D

#Task specific connectivity 
	echo --------------------------------
	echo 3dDeconvolve to model task connectivity 
	echo --------------------------------				
		3dDeconvolve \
		-input ${BidsPrefix}_task-${task}_run-01_bold.volreg+orig ${BidsPrefix}_task-${task}_run-02_bold.volreg+orig \
			-censor ${epiPrefix}.censor_all.1D \
			-ortvec ${epiPrefix}.ROI.WMe.1D ROI.WMe \
			-ortvec ${epiPrefix}.ROI.CSFe.1D ROI.CSFe \
			-polort A \
			-num_stimts 25 \
				-stim_file 1 ${epiPrefix}.motion_demean_all.1D'[0]' -stim_base 1 -stim_label 1 roll1 \
				-stim_file 2 ${epiPrefix}.motion_demean_all.1D'[1]' -stim_base 2 -stim_label 2 pitch1 \
				-stim_file 3 ${epiPrefix}.motion_demean_all.1D'[2]' -stim_base 3 -stim_label 3 yaw1 \
				-stim_file 4 ${epiPrefix}.motion_demean_all.1D'[3]' -stim_base 4 -stim_label 4 dS1 \
				-stim_file 5 ${epiPrefix}.motion_demean_all.1D'[4]' -stim_base 5 -stim_label 5 dL1 \
				-stim_file 6 ${epiPrefix}.motion_demean_all.1D'[5]' -stim_base 6 -stim_label 6 dP1 \
				-stim_file 7 ${epiPrefix}.motion_deriv_demean_all.1D'[0]' -stim_base 7 -stim_label 7 roll_deriv1 \
				-stim_file 8 ${epiPrefix}.motion_deriv_demean_all.1D'[1]' -stim_base 8 -stim_label 8 pitch_deriv1 \
				-stim_file 9 ${epiPrefix}.motion_deriv_demean_all.1D'[2]' -stim_base 9 -stim_label 9 yaw_deriv1 \
				-stim_file 10 ${epiPrefix}.motion_deriv_demean_all.1D'[3]' -stim_base 10 -stim_label 10 dS_deriv1 \
				-stim_file 11 ${epiPrefix}.motion_deriv_demean_all.1D'[4]' -stim_base 11 -stim_label 11 dL_deriv1 \
				-stim_file 12 ${epiPrefix}.motion_deriv_demean_all.1D'[5]' -stim_base 12 -stim_label 12 dP_deriv1 \
				-stim_file 13 ${epiPrefix}.motion_demean_all.1D'[6]' -stim_base 13 -stim_label 13 roll2 \
				-stim_file 14 ${epiPrefix}.motion_demean_all.1D'[7]' -stim_base 14 -stim_label 14 pitch2 \
				-stim_file 15 ${epiPrefix}.motion_demean_all.1D'[8]' -stim_base 15 -stim_label 15 yaw2 \
				-stim_file 16 ${epiPrefix}.motion_demean_all.1D'[9]' -stim_base 16 -stim_label 16 dS2 \
				-stim_file 17 ${epiPrefix}.motion_demean_all.1D'[10]' -stim_base 17 -stim_label 17 dL2 \
				-stim_file 18 ${epiPrefix}.motion_demean_all.1D'[11]' -stim_base 18 -stim_label 18 dP2 \
				-stim_file 19 ${epiPrefix}.motion_deriv_demean_all.1D'[6]' -stim_base 19 -stim_label 19 roll_deriv2 \
				-stim_file 20 ${epiPrefix}.motion_deriv_demean_all.1D'[7]' -stim_base 20 -stim_label 20 pitch_deriv2 \
				-stim_file 21 ${epiPrefix}.motion_deriv_demean_all.1D'[8]' -stim_base 21 -stim_label 21 yaw_deriv2 \
				-stim_file 22 ${epiPrefix}.motion_deriv_demean_all.1D'[9]' -stim_base 22 -stim_label 22 dS_deriv2 \
				-stim_file 23 ${epiPrefix}.motion_deriv_demean_all.1D'[10]' -stim_base 23 -stim_label 23 dL_deriv2 \
				-stim_file 24 ${epiPrefix}.motion_deriv_demean_all.1D'[11]' -stim_base 24 -stim_label 24 dP_deriv2 \
				-stim_times 25 ${subjID}_nback_cue.stimtime 'GAM(8.6,.547,2.890)' -stim_label 25 CUE \
			-errts ${epiPrefix}.con.errts \
			-x1D ${epiPrefix}.con.errts.xmat.1D

		3dDeconvolve \
			-input ${epiPrefix}.con.errts+orig \
			-polort A \
			-num_stimts 1 \
				-stim_times_IM 1 ${subjID}_nback_all.stimtime 'GAM(8.6,.547,1.9)' -stim_label 1 ALL_STIM \
			-x1D_stop

		3dLSS \
			-matrix ${epiPrefix}.con.errts.IM.xmat.1D \
			-input ${epiPrefix}.con.errts+orig \
			-save1D ${epiPrefix}.LSS.xmat.1D \
			-mask ${anatPrefix}.mask_anat+orig \
			-prefix ${epiPrefix}.con.betas
	endif

rm *.stimtime
rm *Decon*
rm *Anat2MNI*
rm *xmat*
rm *volreg*
rm *ROI*
rm *outcount*

#Condition-Specific Beta Series Extraction (3dcalc) -> 
./ConditionCommands.${subjID}.csh
# #End task loop			
				
	echo ------------- "Affine Alignment of Anat to MNI" 
		3dAllineate -prefix ${anatPrefix}.LPI_ns.MNI -base ${template} \
			-source ${anatPrefix}.LPI_ns+orig -twopass -cost lpa \
			-1Dmatrix_save Anat2MNI.aff12.1D \
			-cmass
			# lpa = Local Pearson Correlation (absolute value)	
	echo ------------- "Applying nonlinear alignment of Anat to Template" 
		3dQwarp -prefix ${anatPrefix}.LPI_ns.MNI_NL -blur 0 0 \
			-base ${template} -source ${anatPrefix}.LPI_ns.MNI+tlrc
		
		set diceanattemplate = `3ddot -dodice ${anatPrefix}.LPI_ns.MNI+tlrc ${template}`


	echo -------------------------------------------------------------------------------
	echo Align EPI and ANAT to MNI space
	echo ------------------------------------------------------------------------------
		
	echo ------------- "Applying MNI-warped anat to activation and connectivity" 

	set bases = (act.betas 0_back_negface.betas 0_back_neutface.betas 0_back_posface.betas 0_back_place.betas \
	2_back_negface.betas 2_back_neutface.betas 2_back_posface.betas 2_back_place.betas)
	
	foreach base (${bases})				
		#Input must be EPI that has been aligned to origional anatomical (source in first 3dAllineate command)
		3dNwarpApply -nwarp "Anat2MNI.aff12.1D ${anatPrefix}.LPI_ns.MNI_NL_WARP+tlrc" \
				-source ${epiPrefix}.${base}+orig -master ${anatPrefix}.LPI_ns.MNI+tlrc \
				-prefix ${epiPrefix}.${base}_warped

	end 
		3dNwarpApply -nwarp "Anat2MNI.aff12.1D ${anatPrefix}.LPI_ns.MNI_NL_WARP+tlrc" \
                                -source ${anatPrefix}.mask_WM+orig -master ${anatPrefix}.LPI_ns.MNI+tlrc \
                                -prefix ${epiPrefix}.mask_WM_warped
               	3dNwarpApply -nwarp "Anat2MNI.aff12.1D ${anatPrefix}.LPI_ns.MNI_NL_WARP+tlrc" \
                                -source ${anatPrefix}.mask_GM+orig -master ${anatPrefix}.LPI_ns.MNI+tlrc \
                                -prefix ${epiPrefix}.mask_GM_warped


	set diceWMGMwarp=`3ddot -dodice ${epiPrefix}.mask_WM_warped+tlrc ${epiPrefix}.mask_GM_warped+tlrc`

	echo "Dice ant_template: ${diceanattemplate}" >> ${subjID}.QC.txt
	echo "Dice warped_GM/WM: ${diceWMGMwarp}" >> ${subjID}.QC.txt

# Adapted from @_ss_reciew_html in AFNI proc QC pipeline
# ================== Top level: file names and global vars ===================
set subj          = ${subjID}
set xmat_regress  = ${epiPrefix}.act.betas.xmat.1D
set stats_dset    = ${epiPrefix}act.betas_warped+tlrc
set final_anat    = ${anatPrefix}.LPI_ns.MNI+tlrc
set final_epi_dset = ${epiPrefix}.act.betas_warped+tlrc
set template_warp = nonlinear
set mask_dset     = ${anatPrefix}.mask_anat+orig
# ================ Top level: make output directory structure ================
set wd = ${PWD}
set odir_qc  = {wd}
set odir_img = ${wd}
set odir_info = ${wd}
# ======================== Top level: find a template ========================
set btemp = `basename ${template}`

# try to locate the template
set templ_path = `@FindAfniDsetPath ${template}`

if ( ${#templ_path} ) then
    set templ_vol = "${templ_path}/${btemp}"
    echo "*+ Found ${templ_vol}"
else
    echo "** ERROR: Cannot find template, even though one was specified."
    echo "   Please place the template in a findable spot, and try again."
    exit 1
endif
# ========================= title of html page: subj =========================
# subject ID for html page title
set opref = __page_title
set tjson  = _tmp.txt
set ojson  = ${odir_img}/${opref}.json

cat << EOF >! ${tjson}
itemtype    :: TITLE
itemid      :: pagetop
blockid     :: Top
blockid_hov :: Top of page for:&#10${subj}
title       :: afni_proc.py single subject report
subj        :: "${subj}"
EOF

abids_json_tool.py                                                           \
    -overwrite                                                               \
    -txt2json                                                                \
    -delimiter_major '::'                                                    \
    -delimiter_minor ',,'                                                    \
    -input  ${tjson}                                                         \
    -prefix ${ojson}                                                        
# ======================= EPI and anatomical alignment =======================
# Compare the quality of alignment between the anatomical (ulay) and
# edge-ified EPI (olay):
# look at gross alignment
# follow ventricles and gyral patterns

set opref    = qc_00_ve2a_epi2anat
set focus_box = ${templ_vol}
set ulay_name = `3dinfo -prefix ${final_anat}`
set olay_name = `3dinfo -prefix ${final_epi_dset}`
set tjson    = _tmp.txt
set ojson    = ${odir_img}/${opref}.axi.json
set tjson2   = _tmp2.txt
set ojson2   = ${odir_img}/${opref}.sag.json

@djunct_edgy_align_check                                                     \
    -ulay    ${final_anat}                                                   \
    -box_focus_slices ${focus_box}                                           \
    -olay    ${final_epi_dset}                                               \
    -prefix  ${odir_img}/${opref}                                           

cat << EOF >! ${tjson}
itemtype    :: VOL
itemid      :: epi2anat
blockid     :: ve2a
blockid_hov :: vol alignment (EPI-anat)
title       :: Check vol alignment (EPI to anat)
text        :: "ulay: ${ulay_name} (anat)" ,, "olay: ${olay_name} (EPI edges)"
EOF

abids_json_tool.py                                                           \
    -overwrite                                                               \
    -txt2json                                                                \
    -delimiter_major '::'                                                    \
    -delimiter_minor ',,'                                                    \
    -input  ${tjson}                                                         \
    -prefix ${ojson}                                                        

cat << EOF >! ${tjson2}
itemtype    :: VOL
itemid      :: epi2anat
blockid     :: ve2a
blockid_hov :: vol alignment (EPI-anat)
title       :: Check vol alignment (EPI to anat)
EOF

abids_json_tool.py                                                           \
    -overwrite                                                               \
    -txt2json                                                                \
    -delimiter_major '::'                                                    \
    -delimiter_minor ',,'                                                    \
    -input  ${tjson2}                                                        \
    -prefix ${ojson2}                                                       


# ==================== anatomical and template alignment =====================

# Compare the quality of alignment between the template (ulay) and
# edge-ified anatomical (olay):
# look at gross alignment
# follow ventricles and gyral patterns

set opref    = qc_01_va2t_anat2temp
set focus_box = ${templ_vol}
set ulay_name = `3dinfo -prefix ${templ_vol}`
set olay_name = `3dinfo -prefix ${final_anat}`
set tjson    = _tmp.txt
set ojson    = ${odir_img}/${opref}.axi.json
set tjson2   = _tmp2.txt
set ojson2   = ${odir_img}/${opref}.sag.json

@djunct_edgy_align_check                                                     \
    -ulay    ${templ_vol}                                                    \
    -box_focus_slices ${focus_box}                                           \
    -olay    ${final_anat}                                                   \
    -prefix  ${odir_img}/${opref}                                           

cat << EOF >! ${tjson}
itemtype    :: VOL
itemid      :: anat2temp
blockid     :: va2t
blockid_hov :: vol alignment (anat-template)
title       :: Check vol alignment (anat to template)
text        :: "ulay: ${ulay_name} (template)" ,, "olay: ${olay_name} (anat edges)"
EOF

abids_json_tool.py                                                           \
    -overwrite                                                               \
    -txt2json                                                                \
    -delimiter_major '::'                                                    \
    -delimiter_minor ',,'                                                    \
    -input  ${tjson}                                                         \
    -prefix ${ojson}                                                        



cat << EOF >! ${tjson2}
itemtype    :: VOL
itemid      :: anat2temp
blockid     :: va2t
blockid_hov :: vol alignment (anat-template)
title       :: Check vol alignment (anat to template)
EOF

abids_json_tool.py                                                           \
    -overwrite                                                               \
    -txt2json                                                                \
    -delimiter_major '::'                                                    \
    -delimiter_minor ',,'                                                    \
    -input  ${tjson2}                                                        \
    -prefix ${ojson2}                                                       
# ====================== Finish gracefully, if possible ======================

#exit 0                                                                      



rm *betas+orig*
rm *aff12*
rm *ConditionCommands*
rm ${anatPrefix}.LPI_ns.MNI_NL_WARP+tlrc*
rm ${anatPrefix}.LPI_ns.MNI+tlrc*
m ${anatPrefix}.LPI_ns+orig*


tar -cvf ABCD.NBACK.${subjID}_qc_anat.tar.gz ${subjID}.QC.txt ${anatPrefix}.LPI_ns.MNI_NL+tlrc.BRIK ${anatPrefix}.LPI_ns.MNI_NL+tlrc.HEAD *.jpg
tar -cvf ABCD.NBACK.${subjID}_activity.tar.gz ${epiPrefix}*act.betas*+tlrc* *errts*
tar -cvf ABCD.NBACK.${subjID}_connectivity.tar.gz *0_back_negface.betas*warp* *0_back_neutface.betas*warp* *0_back_posface.betas*warp* *0_back_place.betas*warp* *2_back_negface.betas*warp* *2_back_neutface.betas*warp *2_back_posface.betas*warp* *2_back_place.betas*warp*

#Report size for troubleshooting - Box takes 5 GB
wc -c "ABCD.NBACK.${subjID}_qc_anat.tar.gz" | awk '{print $1}'
wc -c "ABCD.NBACK.${subjID}_activity.tar.gz" | awk '{print $1}'
wc -c "ABCD.NBACK.${subjID}_connectivity.tar.gz" | awk '{print $1}'

rm *.tsv
rm *.1D
rm *.stimtime
rm *.BRIK
rm *.HEAD
rm *.nii
rm *.txt
rm *.1D
rm *.json