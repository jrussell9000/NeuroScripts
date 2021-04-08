#!/bin/bash

docker run --rm -i -u 57059 \
-v /Volumes/apps/linux/FreeSurfer-7.1.0/license.txt:/opt/freesurfer/license.txt:ro \
-v /fast_scratch/jdr/dynamicfaces/BIDS_Master:/data:ro \
-v /fast_scratch/jdr/dynamicfaces/BIDS_fmriprep:/out nipreps/fmriprep:20.2.1 /data /out participant -w /tmp \
--longitudinal \
--nprocs 16 \
--error-on-aroma-warnings \
--use-aroma \
--fd-spike-threshold 0.25 \
--skull-strip-t1w force \
--resource-monitor \
--output-spaces MNI152NLin2009cAsym:res-2
