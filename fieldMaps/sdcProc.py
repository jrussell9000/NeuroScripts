#!/usr/bin/env python

from pathlib import Path
from sdcflows import fieldmaps as fm
from sdcflows.utils.wrangler import find_estimators
from sdcflows.workflows.base import init_fmap_preproc_wf
from sdcflows.workflows.fit.syn import init_syn_preprocessing_wf
from bids import BIDSLayout

import nipype.interfaces.io as nio  # Data i/o
import nipype.interfaces.fsl as fsl  # fsl
import nipype.interfaces.utility as util  # utility
import nipype.pipeline.engine as pe  # pypeline engine
import nipype.algorithms.modelgen as model  # model generation
import nipype.algorithms.rapidart as ra  # artifact detection


restingPath = Path("/fast_scratch/jdr/resting/fmapTesting")
subjectid = "003"
session = "01"
restingLayout = BIDSLayout(restingPath)

preproc_syn = pe.Workflow(name='preproc_syn')

inputnode = pe.Node(
    interface=util.IdentityInterface(field=['func', 'struct']),
    name='inputspec')

fmap_estimators = find_estimators(
    layout=restingLayout,
    subject=subjectid,
    sessions=[session],
    fmapless=True,
    force_fmapless=True
)


# Need to add intendedfor field to fieldmap/mag jsons
fmap_syn_wf = init_syn_preprocessing_wf(
    debug=True,
    name="Test",
    omp_nthreads=6,
    auto_bold_nss=True,
    in_epis=["/fast_scratch/jdr/resting/fmapTesting/sub-003/ses-01/func/sub-003_ses-01_task-Resting_bold.nii"],
    in_meta=["/fast_scratch/jdr/resting/fmapTesting/sub-003/ses-01/func/sub-003_ses-01_task-Resting_bold.json"],
    in_anat="/fast_scratch/jdr/resting/fmapTesting/sub-003/ses-01/anat/sub-003_ses-01_acq-AXFSPGRBRAVONEW_T1w.nii",
    mask_anat="/fast_scratch/jdr/resting/fmapTesting/sub-003/ses-01/anat/sub-003_ses-01_brainmask.nii",
    std2anat_xfm = "/fast_scratch/jdr/resting/fmapTesting/sub-003/ses-01/anat/sub-003_ses-01_acq-AXFSPGRBRAVONEWwarp2mni_T1w_WARPINV.nii"
)



fmap_wf = init_fmap_preproc_wf(
    debug=True,
    estimators=fmap_estimators,
    omp_nthreads=6,
    output_dir="/fast_scratch/jdr/resting/fmapTesting",
    subject=subjectid,
    )

fmap_syn_wf.run()
#fmap_dir = Path("/fast_scratch/jdr/LOKI/1170_L_Day1/dicoms/s1001.FieldMap_Fieldmap_3D")
#fmap = fmap_dir / "sub-1170_ses-01_run-1_fieldmap.nii"


#fmap_estimators = find_estimators


