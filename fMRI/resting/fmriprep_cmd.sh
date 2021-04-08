#!/bin/bash

docker run --rm -i -u 57059 \
-v /fast_scratch/jdr/license.txt:/opt/freesurfer/license.txt:ro \
-v /fast_scratch/jdr/resting/BIDS_Master:/data:ro \
-v /fast_scratch/jdr/resting/BIDS_fmriprep:/out nipreps/fmriprep:20.2.1 /data /out participant -w /tmp \
--skip_bids_validation \
--participant-label ${1} \
--nprocs 8 \
--fd-spike-threshold 0.25 \
--skull-strip-t1w force \
--error-on-aroma-warnings \
--use-aroma