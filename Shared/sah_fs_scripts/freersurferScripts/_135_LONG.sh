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
echo "...........................................................Subject 135"
echo ".............................reconstruct tp1 and tp2 cross sectionally"
echo "**********************************************************************"
echo
recon-all -i _135_bravo.nii -subjid _135_PRE -all
recon-all -i _135rescan_bravo.nii -subjid _135_POST -all

echo "**********************************************************************"
echo "...........................................................Subject 036"
echo ".....................................Create a within-subject template "
echo "**********************************************************************"

recon-all -base _135_template -tp _135_PRE -tp _135_POST -all

echo "**********************************************************************"
echo "...........................................................Subject 036"
echo ".....register cross-sectional reconstructions to longitudinal template"
echo "**********************************************************************"


recon-all -long _135_PRE _135_template -all
recon-all -long _135_POST _135_template -all


echo "**********************************************************************"
echo "...........................................Subject 036 done. Allegedly"
echo "...............................I've done all I can do. Hope it worked."
echo "..................................If not, good luck with those errors."
echo "**********************************************************************"
echo

