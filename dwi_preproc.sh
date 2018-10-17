#!/usr/bin/env bash
# JD Russell 2018
# Perform MRtrix3 preprocessing steps for DWI sequences in subject folders

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

INCOMING_DIR=$1
echo "Input directory "$RAW_INPUT_DIR

PREPROC_DIR=$2
echo "Output directory "$DATASET_DIR

shift 2
SUBJECTS=$*

#####PREPROCESSING FUNCTIONS#####

skullstrip
