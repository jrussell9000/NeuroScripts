#!/bin/bash

##############################################################################################################################################
# Longitudinal Freesurfer recon-all
# Running on THOR server
# Called by other script - freesurferLong_submitScript.sh
# Created by Sara Heyn (sheyn@wisc.edu)
# Last Updated 07.10.19
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

echo
echo
echo "**********************************************************************"
echo "...........................................................Subject 081"
echo ".............................reconstruct tp1 and tp2 cross sectionally"
echo "**********************************************************************"
echo
echo

recon-all -i _081_bravo.nii -subjid _081_PRE -all -parallel -openmp 12
recon-all -i _081rescan_bravo.nii -subjid _081_POST -all -parallel -openmp 12

echo
echo
echo "**********************************************************************"
echo "...........................................................Subject 081"
echo ".....................................Create a within-subject template "
echo "**********************************************************************"
echo
echo

recon-all -base _081_template -tp _081_PRE -tp _081_POST -all -parallel -openmp 12

echo
echo
echo "**********************************************************************"
echo "...........................................................Subject 081"
echo ".....register cross-sectional reconstructions to longitudinal template"
echo "**********************************************************************"
echo
echo

recon-all -long _081_PRE _081_template -all -parallel -openmp 12
recon-all -long _081_POST _081_template -all -parallel -openmp 12

echo
echo
echo "**********************************************************************"
echo "...........................................Subject 081 done. Allegedly"
echo "...............................I've done all I can do. Hope it worked."
echo "..................................If not, good luck with those errors."
echo "**********************************************************************"
echo
echo

