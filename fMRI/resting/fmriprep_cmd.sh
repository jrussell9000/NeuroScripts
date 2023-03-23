#!/bin/bash

docker run --rm -i -u 57059 \
-v /fast_scratch/jdr/license.txt:/opt/freesurfer/license.txt \
-v /fast_scratch/jdr/resting/extrafmriprep_in:/data:ro \
-v /fast_scratch/jdr/resting/extrafmriprep_out:/out nipreps/fmriprep:bleeding121222 /data /out participant \
--skip_bids_validation \
--work-dir /tmp \
--participant-label ${1} \
--nprocs 8 \
--fd-spike-threshold 0.25 \
--skull-strip-t1w force \
--error-on-aroma-warnings \
--use-aroma \
--cifti-output \
--stop-on-first-crash