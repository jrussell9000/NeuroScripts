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


def init_single_subject_wf(subject_id):

    name = "single_subject_%s_wf" % subject_id
    subject_data = collect_data(
        bids_dir=bidsDir,
        participant_label='003',
        task='Resting',
        bids_validate=False)

    workflow = Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(
        fields=['subjects_dir']), name='inputnode')

    bidssrc = pe.Node(
        BIDSDataGrabber(
            subject_data=subject_data,
            subject_id=subject_id),
        name='bidssrc',
    )

    bids_info = pe.Node(
        BIDSInfo(bids_dir=bidsDir, bids_validate=False), name='bids_info'
    )

    summary = pe.Node(
        SubjectSummary(
            std_spaces=spaces.get_spaces(nonstandard=False),
            nstd_spaces=spaces.get_spaces(standard=False),
        ),
        name='summary',
        run_without_submitting=True,
    )

    about = pe.Node(
        AboutSummary(version=_nipype_ver, command=' '.join(sys.argv)),
        name='about',
        run_without_submitting=True,
    )

    ds_report_summary = pe.Node(
        DerivativesDataSink(
            base_directory=fmriprep_dir,
            desc='summary',
            datatype="figures",
            dismiss_entities=("echo",),
        ),
        name='ds_report_summary',
        run_without_submitting=True,
    )

    ds_report_about = pe.Node(
        DerivativesDataSink(
            base_directory=fmriprep_dir,
            desc='about',
            datatype="figures",
            dismiss_entities=("echo",),
        ),
        name='ds_report_about',
        run_without_submitting=True,
    )

    anat_preproc_wf = init_anat_preproc_wf(
        bids_root=bidsDir,
        existing_derivatives=None,
        freesurfer=True,
        hires=False,
        longitudinal=True,
        omp_nthreads=ompThreads,
        output_dir=bidsSrcDir,
        skull_strip_fixed_seed=False,
        skull_strip_mode="force",
        skull_strip_template=Reference('MNI152NLin2009cAsym'),
        spaces=spaces,
        t1w=subject_data['t1w'],
    )

    # workflow.connect([
    #     (inputnode, anat_preproc_wf, [
    #      ('subjects_dir', 'inputnode.subjects_dir')]),
    #     (inputnode, summary, [('subjects_dir', 'subjects_dir')]),
    #     (bidssrc, summary, [('bold', 'bold')]),
    #     (bids_info, summary, [('subject', 'subject_id')]),
    #     (bids_info, anat_preproc_wf, [
    #      (('subject', _prefix), 'inputnode.subject_id')]),
    #     (bidssrc, anat_preproc_wf, [('t1w', 'inputnode.t1w'),
    #                                 ('t2w', 'inputnode.t2w'),
    #                                 ('roi', 'inputnode.roi'),
    #                                 ('flair', 'inputnode.flair')]),
    #     (summary, ds_report_summary, [('out_report', 'in_file')]),
    #     (about, ds_report_about, [('out_report', 'in_file')]),
    # ])

    workflow.connect([
        (bidssrc, bids_info, [
            (('t1w', fix_multi_T1w_source_name), 'in_file')]),
        (bidssrc, summary, [('t1w', 't1w'),
                            ('t2w', 't2w')]),
        (bidssrc, ds_report_summary, [
            (('t1w', fix_multi_T1w_source_name), 'source_file')]),
        (bidssrc, ds_report_about, [
            (('t1w', fix_multi_T1w_source_name), 'source_file')]),
    ])

    for node in workflow.list_node_names():
        if node.split('.')[-1].startswith('ds_'):
            workflow.get_node(node).interface.out_path_base = ""

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

    fmap_estimators = [
        f for f in fmap_estimators if f.method == fm.EstimatorType.ANAT]

    workflow

    func_preproc_wfs = []
    has_fieldmap = bool(fmap_estimators)
    for bold_file in subject_data['bold']:
        func_preproc_wf = init_func_preproc_wf(
            bold_file, has_fieldmap=has_fieldmap)
        if func_preproc_wf is None:
            continue

    fmap_wf = init_fmap_preproc_wf(
        estimators=fmap_estimators,
        omp_nthreads=ompThreads,
        output_dir=fmriprep_dir,
        subject=subject_id,
    )

    func_
# inputnode = pe.Node(
#     interface=niu.IdentityInterface(field=['func', 'struct']),
#     name='inputspec')
