#!/bin/bash


#  ./createDtitkDag.sh MNI152_T1_1mm_brain.nii.gz mean_initial_affine5_resize.nii.gz 4 9 *dti_eddy_masked_rest_sdt.nii.gz
#  ./createDtitkDag.sh t1.nii.gz mean_dti_T1Space.nii.gz 16 37 rawData/[hw]*[0123456789][0123456789][0123456789].nii.gz
#  ./createDtitkDag.sh t1.nii.gz mean_dti_T1Space_diffeo6.nii.gz 11 49 [hw]*[0123456789][0123456789][0123456789].nii.gz
#  ./createDtitkDag.sh t1.nii.gz mean_dti_T1Space_diffeo6.nii.gz 11 23 hhigh[0123456789][0123456789][0123456789].nii.gz


T1=$1
TemplateFile=$2
subGroupSize=$3
subGroups=$4

shift 4
MyImages=`ls $*`

TemplateImage=$TemplateFile
TemplateRoot=${TemplateFile//\.nii.gz/};

ftol=.001
affineIter=5;
diffeoIter=6;

echo "#"

# RIGID LOOP!
#for Image in $MyImages
#do
#    ImageRoot=${Image//\.nii.gz/};
#    ImageFile=$ImageRoot.nii.gz
#    
#    # JobName="toTemplate_"$TemplateRoot"_affine"$iterationCount"Pass_"$ImageRoot
#    JobName="toTemplate_"$TemplateRoot"_rigid_"$ImageRoot
#
#    outputFile=toTemplate_rigid_$ImageRoot.nii.gz
#    affineFile=$ImageRoot"Rigid.txt"
#    
#    echo "Job $JobName go_dtitk_rigidIndiv.submit"
#    echo "VARS $JobName templateFile=\"$TemplateImage\" inputFile=\"$ImageFile\" outputFile=\"$outputFile\" outputAffine=\"$affineFile\" "
#
#done


# AFFINE LOOP!
iterationCount=0;
while [ $iterationCount -le $affineIter ]
do
    ouputFileList=""
    
    imageCount=0;
    for Image in $MyImages
    do
        ImageRoot=${Image//\.nii.gz/};
        ImageFile=$ImageRoot.nii.gz
    
        JobName="toTemplate_"$TemplateRoot"_affine"$iterationCount"Pass_"$ImageRoot

        outputFile=toTemplate_$ImageRoot.nii.gz
        affineFile=toTemplate_$ImageRoot"Affine.txt"
    
    	if [ $iterationCount -eq 0 ]
    	then
       	    echo "Job $JobName go_dtitk_rigidIndiv.submit"
	else
       	    echo "Job $JobName go_dtitk_affIndiv.submit"
	fi

        #echo "Job $JobName go_dtitk_affIndiv.submit"
	echo "RETRY $JobName 5"
        echo "VARS $JobName templateFile=\"$TemplateImage\" inputFile=\"$ImageFile\" outputFile=\"$outputFile\" outputAffine=\"$affineFile\" "

        inputFileList[$imageCount]=$ImageFile
        outputFileList[$imageCount]=$outputFile
        outputAffineList[$imageCount]=$affineFile
        JobList[$imageCount]=$JobName
        
        imageCount=$(( $imageCount + 1 ))

    	#if [ $iterationCount -eq 1 ]
    	#then
        #    ParentJobName="toTemplate_"$TemplateRoot"_rigid_"$ImageRoot
        #    echo "PARENT $ParentJobName CHILD $JobName"
        #fi
    done

    previousTemplate=$TemplateImage
    TemplateImage=""$TemplateRoot"_affine"$iterationCount".nii.gz";


    if [ $iterationCount -ne 0 ]
    then
        parentIteration=$(( $iterationCount - 1 ))
        ParentJobName="createTemplate_"$TemplateRoot"_affine"$parentIteration
        echo "PARENT $ParentJobName CHILD ${JobList[@]}"
    fi


echo "# starting affGroupMean***************************************************"$iterationCount
    JobName="groupTemplate_"$TemplateRoot"_affine"$iterationCount"_part0"
    echo "Job $JobName go_dtitk_affGroup_part0.submit"
    echo "RETRY $JobName 5"
    echo "PARENT ${JobList[@]} CHILD $JobName"
    AvgAffineInv=$TemplateRoot"_affine"$iterationCount"_InvAffine.txt"

    inputFileListText=$(printf "%s," "${inputFileList[@]}")
    outputFileListText=$(printf "%s," "${outputFileList[@]}")
    outputAffineListText=$(printf "%s," "${outputAffineList[@]}")
    echo VARS $JobName templateFile=\"$previousTemplate\" AffineFiles=\"${outputAffineListText%?}\" AvgAffineInv=\"$AvgAffineInv\"
#"

    ParentJobName=$JobName
    JobList=''
    ApplyAffineJobList=''
    imageCount=0;
    for Image in $MyImages
    do
        ImageRoot=${Image//\.nii.gz/};
        ImageFile=$ImageRoot.nii.gz

        outputFile=toTemplate_$ImageRoot.nii.gz
        InputAffineFile=toTemplate_$ImageRoot"Affine.txt"
        OutputAffineFile=toTemplate_$ImageRoot"Affine_concat.txt"

        JobName="groupTemplate_"$TemplateRoot"_affine"$iterationCount"_part1_"$ImageRoot
        echo "Job $JobName go_dtitk_affGroup_part1.submit"
	echo "RETRY $JobName 5"
	echo "PARENT $ParentJobName CHILD $JobName"
	echo "VARS $JobName templateFile=\"$previousTemplate\" InputFile=\"$ImageFile\" InputAffineFile=\"$InputAffineFile\" AvgAffineInv=\"$AvgAffineInv\" OutputFile=\"$outputFile\" OutputAffineFile=\"$OutputAffineFile\" "
        ApplyAffineJobList[$imageCount]=$JobName

	imageCount=$(( $imageCount + 1 ))
    done

echo "# starting affGroupMeanPart2***************************************************"$iterationCount


	grpsCount=0;
	parentJobName=$JobName
	AffineJobList=''
	AffineInputFileList=''
	#inputFileListText=''
	while [ $grpsCount -lt $subGroups ]
	do		
		AffineInputFileListText=''

		TemplateImage=""$TemplateRoot"_affine"$iterationCount"_"$grpsCount".nii.gz";
		JobName="create1Template_"$TemplateRoot"_affine"$iterationCount"_"$grpsCount
		echo "Job $JobName go_dtitk_affGroup_part2.submit"
		echo "RETRY $JobName 5"
		echo "PARENT ${ApplyAffineJobList[@]} CHILD $JobName"
		AffineJobList[$grpsCount]=$JobName
		AffineInputFileList[$grpsCount]=$TemplateImage	
		grpCount=0;
		while [ $grpCount -lt $subGroupSize ]
		do
			spot=$(( ( $grpsCount * $subGroupSize ) + $grpCount ))
			AffineInputFileListText=$AffineInputFileListText$(printf "%s," "${outputFileList[${spot}]}")
			grpCount=$(( $grpCount + 1 ))
		done
		echo VARS $JobName InputFiles=\"${AffineInputFileListText%?}\" OutputTemplate=\"$TemplateImage\"
		#"
		grpsCount=$(( $grpsCount + 1 ))
	done
	
	
	#inputFileList=$outputFileList
	TemplateImage=""$TemplateRoot"_affine"$iterationCount".nii.gz";
	# JobName="create2Template_"$TemplateRoot"_affine"$iterationCount
	JobName="createTemplate_"$TemplateRoot"_affine"$iterationCount
	echo "Job $JobName go_dtitk_affGroup_part2.submit"
	echo "RETRY $JobName 5"
	echo "PARENT ${AffineJobList[@]} CHILD $JobName"
	AffineInputFileListText=$(printf "%s," "${AffineInputFileList[@]}")
	echo VARS $JobName InputFiles=\"${AffineInputFileListText%?}\" OutputTemplate=\"$TemplateImage\"
#"
	parentJobName=$JobName
	#JobName="testTemplate_"$TemplateRoot"_affine"$iterationCount
	#echo "Job $JobName go_dtitk_affGroup_part3.submit"
	#echo "PARENT $parentJobName CHILD $JobName"
	#echo VARS $JobName templateFile=\"$previousTemplate\" OutputTemplate=\"$TemplateImage\" 
#"
	
    iterationCount=$(( $iterationCount + 1 ))

done

echo "# starting difeoGroup***************************************************"
parentJobName="createTemplate_"$TemplateRoot"_affine"$affineIter

iterationCount=1;
while [ $iterationCount -le $diffeoIter ]
do
    ouputFileList=""
    
    imageCount=0;
    for Image in $MyImages
    do

        ImageRoot=${Image//\.nii.gz/};
        ImageFile=$ImageRoot.nii.gz

        JobName="toTemplate_"$TemplateRoot"_diffeo"$iterationCount"Pass_"$ImageRoot


        MaskFile="mask.nii.gz"
        affineFile="toTemplate_"$ImageRoot".nii.gz"
        diffeoFile="toTemplate_"$ImageRoot"_diffeo.nii.gz"
        diffeoDfFile="toTemplate_"$ImageRoot"_diffeo.df.nii.gz"
    
        echo "Job $JobName go_dtitk_difIndiv.submit"
        echo "VARS $JobName template=\"$TemplateImage\" subj=\"$affineFile\" outputDiffeo=\"$diffeoFile\" outputDiffeoDF=\"$diffeoDfFile\" no_of_iter=\"$iterationCount\" ftol=\"$ftol\" "

        diffeoFileList[$imageCount]=$diffeoFile
        diffeoDfFileList[$imageCount]=$diffeoDfFile

        JobList[$imageCount]=$JobName
        
        imageCount=$(( $imageCount + 1 ))

    done

    if [ $iterationCount -ne 1 ]
    then
        parentIteration=$(( $iterationCount - 1 ))
        #ParentJobName="createTemplate_"$TemplateRoot"_diffeo"$parentIteration
	ParentJobName="createTemplate_"$TemplateRoot"_difGrpAfterMean"$parentIteration
        echo "PARENT $ParentJobName CHILD ${JobList[@]}"
    fi
    if [ $iterationCount -eq 1 ]
    then
        echo PARENT $parentJobName CHILD ${JobList[@]}
    fi
echo "# starting difeoGroupMean***************************************************"$iterationCount
	grpsCount=0;
	while [ $grpsCount -lt $subGroups ]
	do
		
		MeanImage=""$TemplateRoot"_diffeo"$iterationCount"_"$grpsCount"_mean.nii.gz";
		TemplateImage=""$TemplateRoot"_diffeo"$iterationCount"_"$grpsCount".nii.gz";
		dfTemplateImage="mean_df"$iterationCount"_"$grpsCount".nii.gz"; #needs root added???????*************************************************************************

		JobName="createTemplate_"$TemplateRoot"_diffeoTVMean"$iterationCount"_"$grpsCount
			echo "Job $JobName go_dtitk_difTVMean.submit"
			echo "RETRY $JobName 5"
			echo "PARENT ${JobList[@]} CHILD $JobName"
		JobName2="createTemplate_"$TemplateRoot"_diffeoVVMean"$iterationCount"_"$grpsCount
			echo "Job $JobName2 go_dtitk_difVVMean.submit"
			echo "RETRY $JobName2 5"
			echo "PARENT ${JobList[@]} CHILD $JobName2"
		JobName3="createTemplate_"$TemplateRoot"_difGrpAfterMean"$iterationCount"_"$grpsCount
			echo "Job $JobName3 go_dtitk_difGrpAfterMeans.submit"
			echo "RETRY $JobName3 5"
			echo "PARENT $JobName $JobName2 CHILD $JobName3"
		diffeoFileListText=''
		diffeoDfFileListText=''
		grpCount=0;
		while [ $grpCount -lt $subGroupSize ]
		do
			spot=$(( ( $grpsCount * $subGroupSize ) + $grpCount ))
			diffeoFileListText=$diffeoFileListText$(printf "%s," "${diffeoFileList[${spot}]}")
			diffeoDfFileListText=$diffeoDfFileListText$(printf "%s," "${diffeoDfFileList[${spot}]}")
			# unused ? #  outputWarpListText=$(printf "%s," "${outputWarpList[@]}")
			grpCount=$(( $grpCount + 1 ))
		done
		echo VARS $JobName template=\"$MeanImage\" outputDiffeo=\"${diffeoFileListText%?}\"
		#"
		echo VARS $JobName2 dftemplate=\"$dfTemplateImage\" outputDiffeoDF=\"${diffeoDfFileListText%?}\"
		#"
		echo VARS $JobName3 template=\"$TemplateImage\" templatemean=\"$MeanImage\" dftemplate=\"$dfTemplateImage\"
		#"
		
		grpsCount=$(( $grpsCount + 1 ))
	done
	
	grpsCount=0;
	JobList=''
	SubGrpsList=''
	dfSubGrpsList=''
	while [ $grpsCount -lt $subGroups ]
	do
		JobList[$grpsCount]="createTemplate_"$TemplateRoot"_difGrpAfterMean"$iterationCount"_"$grpsCount
		SubGrpsList[$grpsCount]=""$TemplateRoot"_diffeo"$iterationCount"_"$grpsCount".nii.gz"
		dfSubGrpsList[$grpsCount]="mean_df"$iterationCount"_"$grpsCount".nii.gz"
		grpsCount=$(( $grpsCount + 1 ))		
	done
	
    	MeanImage=""$TemplateRoot"_diffeo"$iterationCount"_mean.nii.gz";
    	TemplateImage=""$TemplateRoot"_diffeo"$iterationCount".nii.gz";
	
	dfTemplateImage="mean_df"$iterationCount".nii.gz"; #needs root added???????*************************************************************************
	SubGrpsListText=$(printf "%s," "${SubGrpsList[@]}")
	dfSubGrpsListText=$(printf "%s," "${dfSubGrpsList[@]}")
	
	JobName="createTemplate_"$TemplateRoot"_diffeoTVMean"$iterationCount
		echo "Job $JobName go_dtitk_difTVMean.submit"
		echo "RETRY $JobName 5"
		echo "PARENT ${JobList[@]} CHILD $JobName"
	JobName2="createTemplate_"$TemplateRoot"_diffeoVVMean"$iterationCount
		echo "Job $JobName2 go_dtitk_difVVMean.submit"
		echo "RETRY $JobName2 5"
		echo "PARENT ${JobList[@]} CHILD $JobName2"
	JobName3="createTemplate_"$TemplateRoot"_difGrpAfterMean"$iterationCount
		echo "Job $JobName3 go_dtitk_difGrpAfterMeans.submit"
		echo "RETRY $JobName3 5"
		echo "PARENT $JobName $JobName2 CHILD $JobName3"
	
	echo VARS $JobName template=\"$MeanImage\" outputDiffeo=\"${SubGrpsListText%?}\"
	#"
	echo VARS $JobName2 dftemplate=\"$dfTemplateImage\" outputDiffeoDF=\"${dfSubGrpsListText%?}\"
	#"
	echo VARS $JobName3 template=\"$TemplateImage\" templatemean=\"$MeanImage\" dftemplate=\"$dfTemplateImage\"
	#"

    iterationCount=$(( $iterationCount + 1 ))

done
echo "# end of difeoGroupMean***************************************************"

finalDTIMean=$TemplateRoot"_diffeo"$diffeoIter"_mean.nii.gz"
dtiToT1Trans=$TemplateRoot"_diffeo"$diffeoIter"_toT1.aff"

parentJobName=$JobName3
JobName="alignToT1"
echo "Job $JobName go_dtitk_alignToT1.submit"
echo "RETRY $JobName 5"
echo "PARENT $parentJobName CHILD $JobName"
echo "VARS $JobName dti=\"$finalDTIMean\" t1=\"$T1\" dtiToT1Trans=\"$dtiToT1Trans\" "

echo "# end of Align to T1 ***************************************************"


parentJobName=$JobName
for Image in $MyImages
do

    ImageRoot=${Image//\.nii.gz/};
    ImageFile=$ImageRoot.nii.gz

    JobName="scalar_"$ImageRoot

    diffeoFile="toTemplate_"$ImageRoot"_diffeo.nii.gz"
    diffeoDfFile="toTemplate_"$ImageRoot"_diffeo.df.nii.gz"

    fa="toT1_"$ImageRoot"_diffeo_fa.nii.gz"
    tr="toT1_"$ImageRoot"_diffeo_tr.nii.gz"
    ad="toT1_"$ImageRoot"_diffeo_ad.nii.gz"
    rd="toT1_"$ImageRoot"_diffeo_rd.nii.gz"

    tensorFile="toT1_"$ImageRoot"_diffeo.nii.gz"
    orig=$ImageRoot".nii.gz"
#   affineTrans="toTemplate_"$ImageRoot"Affine.txt"
    affineTrans="toTemplate_"$ImageRoot"Affine_concat.txt" 
    diffeoTrans="toTemplate_"$ImageRoot"_diffeo.df.nii.gz"
    

    echo "Job $JobName go_dtitk_createScalars_inT1Space.submit"
    echo "RETRY $JobName 5"
    echo "PARENT $parentJobName CHILD $JobName"
    echo "VARS $JobName fa=\"$fa\" tr=\"$tr\" ad=\"$ad\" rd=\"$rd\" tensorFile=\"$tensorFile\" orig=\"$orig\" affineTrans=\"$affineTrans\" diffeoTrans=\"$diffeoTrans\" dtiToT1Trans=\"$dtiToT1Trans\" T1=\"$T1\" "






done



