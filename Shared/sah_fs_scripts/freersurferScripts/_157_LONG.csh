#!/bin/bash

##############################################################################################################################################
# Extract longitudinal cortical volume and surface estimates from Freesurfer recon-all
# Running on new THOR server
# Data from PTO study - Josh Cisler
# Created by Sara Heyn (sheyn@wisc.edu)
# Last Updated 01.16.19
##############################################################################################################################################

echo "**********************************************************************"
echo "............Welcome to the hell that is Freesurfer. Good luck, friend."
echo "**********************************************************************"

echo "**********************************************************************"
echo "..................................................Set Freesurfer Paths"
echo "**********************************************************************"

export FREESURFER_HOME=/Volumes/apps/linux/freesurfer-current
export FSFAST_HOME=/Volumes/apps/linux/freesurfer-current/fsfast
export MNI_DIR=/Volumes/apps/linux/freesurfer-current/mni
source $FREESURFER_HOME/SetUpFreeSurfer.sh
export PATH=$PATH:/Volumes/apps/linux/freesurfer-current
export PATH=$PATH:/Volumes/apps/linux/freesurfer-current/bin
export PATH=$PATH:/Volumes/apps/linux/freesurfer-current/lib

SUBJECTS_DIR=/Volumes/Vol6/YouthPTSD/data/freesurferFullSample/rawT1s
cd $SUBJECTS_DIR

echo "**********************************************************************"
echo "...........................................................Subject 157"
echo ".............................reconstruct tp1 and tp2 cross sectionally"
echo "**********************************************************************"
echo
recon-all -i _157_bravo.nii -subjid _157_PRE -all -parallel -openmp 12
#recon-all -i _157rescan_bravo.nii -subjid _157_POST -all -parallel -openmp 12

echo "**********************************************************************"
echo "...........................................................Subject 157"
echo ".....................................Create a within-subject template "
echo "**********************************************************************"

#recon-all -base _154_template -tp _154_PRE -tp _154_POST -all -parallel -openmp 12

echo "**********************************************************************"
echo "...........................................................Subject 154"
echo ".....register cross-sectional reconstructions to longitudinal template"
echo "**********************************************************************"


#recon-all -long _154_PRE _154_template -all -parallel -openmp 12
#recon-all -long _154_POST _154_template -all -parallel -openmp 12


echo "**********************************************************************"
echo "...........................................Subject 154s done. Allegedly"
echo "...............................I've done all I can do. Hope it worked."
echo "..................................If not, good luck with those errors."
echo "**********************************************************************"
echo

