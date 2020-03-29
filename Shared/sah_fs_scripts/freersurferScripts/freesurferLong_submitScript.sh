#!/bin/bash

##############################################################################################################################################
# Run Freesurfer recon-all longitudinal
# Calls other script - (1) *SUBID*_LONG.sh
# Data from Youth PTSD
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
SCRIPTS=/Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts
cd $SUBJECTS_DIR

echo "**********************************************************************"
echo "......Running all the individual scripts for longitudinal registration"
echo "............................Each runs in an individual screen detached"
echo "**********************************************************************"
echo

screen -dm -S "_036_LONG" $SCRIPTS/_036_LONG
echo "..................._036_LONG"

screen -dm -S "_065_LONG" $SCRIPTS/_065_LONG
echo "..................._065_LONG"

screen -dm -S "_081_LONG" $SCRIPTS/_081_LONG
echo "..................._081_LONG"


echo "**********************************************************************"
echo "............I've done all I can do. All the scripts should be running."
echo "..................................If not, good luck with those errors."
echo "**********************************************************************"
echo

