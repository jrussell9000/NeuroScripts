#!/bin/bash
# Do Tromp 2013
# Convert DTI, FMAP, fMRI, T1, T2 from DICOM to NIfTI for multiple subjects

if [ $# -lt 3 ]; then

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

#####VARIABLES PASSED FROM COMMAND#####

RAW_INPUT_DIR=$1 
echo "Input directory "$RAW_INPUT_DIR

DATASET_DIR=$2
echo "Output directory "$DATASET_DIR

shift 2
SUBJECTS_RAW=$* 

#####GLOBALS#####

SUBJECTS=$(echo $SUBJECTS_RAW | tr -d "_")

#####FUNCTION CALLS#####
convert() {
  
  for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/*/; do
      #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
      if [ -d ${scanpath} ]; then
	continue
      fi
		  
      SEQ_GESCANTYPE=$(basename ${scanpath}) 
      
      GE_SCANTYPE=`basename ${scanpath} | awk 'BEGIN {FS="_"} {print $NF}'`		
	
      IMAGE_DESC=$(grep -A 2 "_${i}/dicoms/${SEQ_SCANTYPE}" ${RAW_INPUT_DIR}/_${i}/dicoms/info.txt | tail -n 1 )

      case "$IMAGE_DESC" in
	*DTI*)
	  MAPTYPE=DTI
	;;
	*EPI*)
	  MAPTYPE=EPI
	;;
      esac
      
      tmppath_check

	cp -fr ${scanpath} /tmp	
		  
	decompress 
	rm ${SUBJ_DIR}/ANAT/*T1*

	dcm2niix -b y -f %i_${SCANTYPE}_T1 -o ${SUBJ_DIR}/ANAT/ /tmp/$(basename ${scanpath})	

    done
}

#If $scanpath already exists in /tmp, delete it
tmppath_check() {
  if [ -d /tmp/$(basename ${scanpath}) ]; then
    rm -rf /tmp/$(basename ${scanpath})
  fi
}

#Decompress bz2 DICOM files
decompress() {
  for z in /tmp/$(basename ${scanpath})/*.bz2; do
    bzip2 -d $z
  done
}

echo ~~~Convert File~~~;

for i in ${SUBJECTS}; do

#Making directories to hold per subject SCANS
  SUBJ_PATH=${DATASET_DIR}/${i}
  mkdir -p -v ${SUBJ_PATH}
  mkdir -p -v ${SUBJ_PATH}/ANAT 
  mkdir -p -v ${SUBJ_PATH}/DTI 
  mkdir -p -v ${SUBJ_PATH}/FMAP  
  mkdir -p -v ${SUBJ_PATH}/INFO 

done

cd ${RAW_INPUT_DIR} || exit

for i in ${SUBJECTS}; do

  cd ${RAW_INPUT_DIR}/_${i} || continue 
  
  echo ~~~Subject in process: ${i}~~~

  SUBJ_DIR=${DATASET_DIR}/${i}

  cp ${RAW_INPUT_DIR}/_${i}/dicoms/info.txt ${SUBJ_DIR}/INFO/${i}_info.txt;

  echo "~~~~~Converting anatomical scans~~~~~~"

    echo "-------Starting T1-------"

    for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/*bravo/; do
      #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
      if [ -d ${scanpath} ]; then
		  
	SCANTYPE=`basename ${scanpath} | awk 'BEGIN {FS="_"} {print $NF}'`	
		  
	tmppath_check

	cp -fr ${scanpath} /tmp	
		  
	decompress 
	rm ${SUBJ_DIR}/ANAT/*T1*

	dcm2niix -b y -f %i_${SCANTYPE}_T1 -o ${SUBJ_DIR}/ANAT/ /tmp/$(basename ${scanpath})	
      
      fi

    done

    echo "-------Starting T2-------"

    for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/*3dir/; do
      #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
      if [ -d ${scanpath} ]; then
	      
	SCANTYPE=`basename ${scanpath} | awk 'BEGIN {FS="_"} {print $NF}'`	
      
	tmppath_check

	cp -fr ${scanpath} /tmp	
      
	decompress 
		       
	dcm2niix -b y -f %i_${SCANTYPE}_T2 -o ${SUBJ_DIR}/ANAT/ /tmp/$(basename ${scanpath})	
      
      fi
    
    done
    
    echo "~~~~~Converting DTI scans~~~~~" 
    
    for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/{*dti,*FA,*ADC,*CMB}/; do
      #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
      if [ -d ${scanpath} ]; then
	      
	SCANTYPE=`basename ${scanpath} | awk 'BEGIN {FS="_"} {print $NF}'`	
      
	tmppath_check

	cp -fr ${scanpath} /tmp	
      
	decompress 
		       
	dcm2niix -b y -f %i_${SCANTYPE}_DTI -o ${SUBJ_DIR}/DTI/ /tmp/$(basename ${scanpath})

      fi
    
    done

    echo "~~~~~Converting Field Maps~~~~~"

    for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/*fmap/; do
                #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
      if [ -d ${scanpath} ]; then
	      
	echo ${scanpath}
	#Problem: Multiple fieldmap directories exist for each subject
	#Solution: Parse each subjects info.txt file to determine which is which
	
	#SEQ_SCANTYPE is the full directory name of the scan sequence (e.g., s01_epi)
	SEQ_SCANTYPE=$(basename ${scanpath})
		
	IMAGE_DESC=$(grep -A 2 "_${i}/dicoms/${SEQ_SCANTYPE}" ${RAW_INPUT_DIR}/_${i}/dicoms/info.txt | tail -n 1 )

	case "$IMAGE_DESC" in
		*DTI*)
			MAPTYPE=DTI
			;;
		*EPI*)
			MAPTYPE=EPI
			;;
	esac
	
	tmppath_check

	cp -fr ${scanpath} /tmp	
      
	decompress 
		       
	dcm2niix -b y -f %i_${SCANTYPE}_${MAPTYPE}_DTI -o ${SUBJ_DIR}/FMAP/ /tmp/$(basename ${scanpath}) 
	
      fi
        done

      done

# for j in `ls -d *_dti *_hydie *_hydi`;
# do
#   prefix=`echo $j | awk 'BEGIN{FS="/"}{print $1}'`;
#   #subj=${i};
#   echo Scan is ${j}
#   echo convert_file ${j} DTI_RAW/${subj}_${prefix} nii;
#   convert_file ${j} DTI_RAW/${subj}_${prefix} nii; # done
#
# #echo CONVERT rs-fMRI SCANS
# #for j in `ls -d *_epi`;
# #do
# #prefix=`echo $j | awk 'BEGIN{FS="/"}{print $1}'`;
# ##subj=${i};
# #echo Scan is ${j}
# #echo convert_file ${j} rs-fMRI/${subj}_${prefix} nii; #convert_file ${j} rs-fMRI/${subj}_${prefix} nii;
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
 fi
