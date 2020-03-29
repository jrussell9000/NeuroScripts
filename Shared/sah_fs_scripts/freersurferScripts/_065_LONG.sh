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
echo "...........................................................Subject 065"
echo ".............................reconstruct tp1 and tp2 cross sectionally"
echo "**********************************************************************"
echo
recon-all -i _065_bravo.nii -subjid _065_PRE -all -parallel -openmp 12
recon-all -i _065rescan_bravo.nii -subjid _065_POST -all -parallel -openmp 12

echo "**********************************************************************"
echo "...........................................................Subject 065"
echo ".....................................Create a within-subject template "
echo "**********************************************************************"

recon-all -base _065_template -tp _065_PRE -tp _065_POST -all -parallel -openmp 12

echo "**********************************************************************"
echo "...........................................................Subject 065"
echo ".....register cross-sectional reconstructions to longitudinal template"
echo "**********************************************************************"


recon-all -long _065_PRE _065_template -all -parallel -openmp 12
recon-all -long _065_POST _065_template -all -parallel -openmp 12


echo "**********************************************************************"
echo "...........................................Subject 065 done. Allegedly"
echo "...............................I've done all I can do. Hope it worked."
echo "..................................If not, good luck with those errors."
echo "**********************************************************************"
echo

