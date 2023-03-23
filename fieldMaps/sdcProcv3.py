#!/usr/bin/env python
import sys
from pathlib import Path
from sdcflows import fieldmaps as fm
from sdcflows.utils.wrangler import find_estimators
from sdcflows.workflows.base import init_fmap_preproc_wf
from sdcflows.workflows.fit.syn import init_syn_preprocessing_wf

from bids import BIDSLayout
from nipype import __version__ as _nipype_ver
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from niworkflows.utils.bids import collect_data
from niworkflows.utils.misc import fix_multi_T1w_source_name
from niworkflows.utils.spaces import Reference, SpatialReferences
from niworkflows.engine.workflows import LiterateWorkflow as Workflow
from niworkflows.interfaces.bids import BIDSDataGrabber, BIDSInfo, DerivativesDataSink
from smriprep.workflows.anatomical import init_anat_preproc_wf
from reports import SubjectSummary, AboutSummary


bidsDir = Path("/fast_scratch/jdr/resting/fmapTesting")
bidsDerivDir = bidsDir / 'derivatives'
bidsSrcDir = bidsDir / 'sourcedata'
subjectid = "003"
session = "01"
ompThreads = 16
outputDir = Path("/fast_scratch/jdr/resting/fmapTestProc")
fmriprep_dir = outputDir
restingLayout = BIDSLayout(bidsDir)

preproc_syn = pe.Workflow(name='preproc_syn')

spaces = SpatialReferences([
    ('MNI152Lin', {}),
    ('fsaverage', {'density': '10k'}),
    ('T1w', {}),
    ('fsnative', {})
])

# From github.com/nipreps/fmriprep/blob/master/fmriprep/workflows/base.py:113ish

fmap_estimators = None

# SDC Step 1: Run basic heuristics to identify available data for fieldmap estimation
# For now, no fmapless
fmap_estimators = find_estimators(
    layout=restingLayout,
    subject=subjectid,
    sessions=[session],
    fmapless=True,
    force_fmapless=True
)

fmap_wf = init_fmap_preproc_wf(
    estimators=fmap_estimators,
    omp_nthreads=ompThreads,
    output_dir=fmriprep_dir,
    subject=subjectid
)

print(fmap_estimators)