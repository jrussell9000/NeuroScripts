#!/bin/bash

# This script requires the GPU FastSurfer docker image.
# https://github.com/Deep-MI/FastSurfer/tree/stable/Docker
subjdir_name=${1}

docker run --gpus all -v /fast_scratch/sah/BIDS_Master_test:/data \
		      -v /fast_scratch/jdr/LOKI:/output \
		      -v /fast_scratch/jdr:/fs_license \
		      --rm --user 57059:1044 fastsurfer:gpu \
		      --fs_license /fs_license/license.txt \
		      --t1 /data/${subjdir_name}/ses-02/anat/${subjdir_name}_ses-02_acq-MPRAGE_T1w.nii.gz \
		      --sid ${subjdir_name} --sd /output \
		      --parallel --threads 4
