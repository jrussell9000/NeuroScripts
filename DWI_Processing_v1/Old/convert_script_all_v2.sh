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
fmri_tools_local=$HOME/brave_scripts/fmri_tools-current/apps
#####FUNCTION CALLS#####
#convert() {
#
#  for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/*/; do
#      #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
#      if [ -d ${scanpath} ]; then
#	continue
#      fi
#
#      SEQ_GESCANTYPE=$(basename ${scanpath})
#
#      GE_SCANTYPE=`basename ${scanpath} | awk 'BEGIN {FS="_"} {print $NF}'`
#
#      IMAGE_DESC=$(grep -A 2 "_${i}/dicoms/${SEQ_SCANTYPE}" ${RAW_INPUT_DIR}/_${i}/dicoms/info.txt | tail -n 1 )
#
#      case "$IMAGE_DESC" in
#	*DTI*)
#	  MAPTYPE=DTI
#	;;
#	*EPI*)
#	  MAPTYPE=EPI
#	;;
#      esac
#
#      tmppath_check
#
#	cp -fr ${scanpath} /tmp
#
#	decompress
#	rm ${SUBJ_DIR}/ANAT/*T1*
#
#	dcm2niix -b y -f %i_${SCANTYPE}_T1 -o ${SUBJ_DIR}/ANAT/ /tmp/$(basename ${scanpath})
#
#    done
#}

#If $scanpath already exists in /tmp, delete it
tmppath_check() {
  if [ -d /tmp/"${scanpath##*/}" ]; then
    rm -rf /tmp/"${scanpath##*/}"
  fi
}

#Decompress bz2 DICOM files
decompress() {
  for z in /tmp/"${scanpath##*/}"/*.bz2; do
    bzip2 -d $z
  done
}

for i in ${SUBJECTS}; do

#Making directories to hold per subject SCANS
  SUBJ_PATH=${DATASET_DIR}/${i}
  rm -rf ${SUBJ_PATH}
  mkdir -p ${SUBJ_PATH}

  rm -rf ${SUBJ_PATH}/ANAT
  mkdir -p ${SUBJ_PATH}/ANAT

  rm -rf ${SUBJ_PATH}/DTI
  mkdir -p ${SUBJ_PATH}/DTI

  rm -rf ${SUBJ_PATH}/FMAP
  mkdir -p ${SUBJ_PATH}/FMAP

  rm -rf ${SUBJ_PATH}/INFO
  mkdir -p ${SUBJ_PATH}/INFO

done

cd ${RAW_INPUT_DIR} || exit

for i in ${SUBJECTS}; do

  cd ${RAW_INPUT_DIR}/_${i} || continue

  printf "\n%s\n" "/////////////////////////////////////////"
  printf "%s" "////////SUBJECT BEING PROCESSED: ${i}/////////"
  printf "\n%s\n" "/////////////////////////////////////////"

  SUBJ_DIR=${DATASET_DIR}/${i}

  cp ${RAW_INPUT_DIR}/_${i}/dicoms/info.txt ${SUBJ_DIR}/INFO/${i}_info.txt;

  printf "\n%s\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
  printf "%s" "~~~~~CONVERTING ANATOMICAL SCANS~~~~~~"
  printf "\n%s\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
    printf "\n%s\n" "-------Starting with T1 (BRAVO)-------"

    for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/*bravo; do
      #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
      if [ -d ${scanpath} ]; then

      	SCANTYPE=`basename ${scanpath} | awk 'BEGIN {FS="_"} {print $NF}'`

      	tmppath_check

      	cp -fr ${scanpath} /tmp

      	decompress

      	dcm2niix -b y -f ${i}_${SCANTYPE}_T1 -o ${SUBJ_DIR}/ANAT/ /tmp/"${scanpath##*/}"

      fi

    done

    printf "\n%s\n" "-------Starting with T2 (3DIR)-------"

    for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/*3dir; do
      #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
      if [ -d ${scanpath} ]; then

	      SCANTYPE=`basename ${scanpath} | awk 'BEGIN {FS="_"} {print $NF}'`

      	tmppath_check

      	cp -fr ${scanpath} /tmp

      	decompress

      	dcm2niix -b y -f ${i}_${SCANTYPE}_T2 -o ${SUBJ_DIR}/ANAT/ /tmp/"${scanpath##*/}"

      fi

    done

    printf "\n%s\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
    printf "%s" "~~~~~~~~~CONVERTING DTI SCANS~~~~~~~~~~"
    printf "\n%s\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

    for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/{*dti,*FA,*ADC,*CMB}; do
       #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
       if [ -d ${scanpath} ]; then
    
         SCANTYPE=`basename ${scanpath} | awk 'BEGIN {FS="_"} {print $NF}'`
   
         tmppath_check
    
         cp -fr ${scanpath} /tmp
    
         decompress
    
         dcm2niix -b y -v 2 -f ${i}_${SCANTYPE}_DTI -o ${SUBJ_DIR}/DTI/ /tmp/"${scanpath##*/}" > ~/dticonv_${SCANTYPE}.txt
    
       fi
    
     done

    printf "\n%s\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
    printf "%s" "~~~~~~~~~CONVERTING FIELDMAPS~~~~~~~~~~"
    printf "\n%s\n" "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

    for scanpath in ${RAW_INPUT_DIR}/_${i}/dicoms/*fmap; do
                #Verify that only directories are considered, per https://unix.stackexchange.com/questions/86722/how-do-i-loop-through-only-directories-in-bash
      if [ -d ${scanpath} ]; then

        echo ${scanpath}
        #Problem: Multiple fieldmap directories exist for each subject
        #Solution: Parse each subjects info.txt file to determine which is which

      	IMAGE_DESC=$(grep -A 2 "_${i}/dicoms/${scanpath##*/}" ${RAW_INPUT_DIR}/_${i}/dicoms/info.txt | tail -n 1 )

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

        make_fmap /tmp/"${scanpath##*/}" ${SUBJ_DIR}/FMAP/${i}_${MAPTYPE}_FMAP.nii -v
        # Option to register fieldmap to anatomical scan does NOT work (e.g., --anat ${SUBJ_DIR}/ANAT/${i}_bravo_T1.nii)
        # dcm2niix -b y -z y -m y -f ${i}_${SCANTYPE}_FMAP_${MAPTYPE} -o ${SUBJ_DIR}/FMAP/ /tmp/"${scanpath##*/}"

      fi

    done

done

fi

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
