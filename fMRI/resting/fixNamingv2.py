#!/usr/bin/env python3
# coding: utf-8

# This script fixes the file naming of the YouthPTSD Resting State scans,
# fieldmaps, and their accompanying JSONS to match BIDS specification.
# It assumes we've already renamed the resting state scans (and their JSONS)
# to sub-XXX_ses-YY_task-Resting_bold.nii using the bash command:
# find -name test-this\*.ext | sed 'p;s/test-this/replace-that/' | xargs -d '\n' -n 2 mv
# see: https://stackoverflow.com/questions/20657432/rename-multiple-files-but-only-rename-part-of-the-filename-in-bash
# Should code in this process later....


from pathlib import Path
import os
import json
import re

BIDS_Master = Path('/fast_scratch/jdr/resting/fmapTesting')


def fixRSjsons(ses_dir):
    subjroot = str(ses_dir.parent.name + '_' + ses_dir.name)
    ses_dir = Path(ses_dir)
    func_dir = ses_dir / 'func'
    rsJSON = func_dir / str(subjroot + '_task-Resting_bold.json')
    if rsJSON.exists():
        # Open the json file for the fieldmap, and edit the IntendedFor key to match the magnitude file name
        with open(rsJSON, 'r') as f:
            rsJSONdata = json.load(f)
            rsJSONdata['TaskName'] = "Resting"
        with open(rsJSON, 'w') as f:
            json.dump(rsJSONdata, f, indent=4)


def fixFieldmapFilenames(ses_dir):
    subjroot = str(ses_dir.parent.name + '_' + ses_dir.name)
    ses_dir = Path(ses_dir)
    fmap_dir = ses_dir / 'fmap'

    epiMag_orig = fmap_dir / str(subjroot + '_acq-FieldmapEPI_magnitude1.nii')
    if epiMag_orig.exists():
        epiMag = fmap_dir / str(subjroot + '_acq-EPIHz_magnitude.nii')
        os.rename(epiMag_orig, epiMag)

    dtiMag_orig = fmap_dir / str(subjroot + '_acq-FieldmapDTI_magnitude1.nii')
    if dtiMag_orig.exists():
        dtiMag = fmap_dir / str(subjroot + '_acq-DTIHz_magnitude.nii')
        os.rename(dtiMag_orig, dtiMag)

    epiPhasediff = fmap_dir / str(subjroot + '_acq-EPIHz_phasediff.nii')
    if epiPhasediff.exists():
        epiFieldmap = fmap_dir / str(subjroot + '_acq-EPIHz_fieldmap.nii')
        os.rename(epiPhasediff, epiFieldmap)

    dtiPhasediff = fmap_dir / str(subjroot + '_acq-DTIHz_phasediff.nii')
    if dtiPhasediff.exists():
        dtiFieldmap = fmap_dir / str(subjroot + '_acq-DTIHz_fieldmap.nii')
        os.rename(dtiPhasediff, dtiFieldmap)

    epiJson_orig = fmap_dir / str(subjroot + '_acq-EPIHz_phasediff.json')
    if epiJson_orig.exists():
        epiJson = fmap_dir / str(subjroot + '_acq-EPIHz_fieldmap.json')
        os.rename(epiJson_orig, epiJson)

    dtiJson_orig = fmap_dir / str(subjroot + '_acq-DTIHz_phasediff.json')
    if dtiJson_orig.exists():
        dtiJson = fmap_dir / str(subjroot + '_acq-DTIHz_fieldmap.json')
        os.rename(dtiJson_orig, dtiJson)


def fixFieldmapJSONS(ses_dir):
    subjroot = str(ses_dir.parent.name + '_' + ses_dir.name)
    ses_dir = Path(ses_dir)
    fmap_dir = ses_dir / 'fmap'
    epiJson = fmap_dir / str(subjroot + '_acq-EPIHz_fieldmap.json')
    if epiJson.exists():
        # Open the json file for the fieldmap, and edit the IntendedFor key to match the magnitude file name
        with open(epiJson, 'r') as f:
            epijsondata = json.load(f)
            bidspath = str("bids::" + "/".join([ses_dir.parent.name, ses_dir.name, 'func/']))
            epijsondata['IntendedFor'] = [bidspath + str(subjroot + '_task-Resting_bold.nii'),
                                          bidspath + str(subjroot + '_acq-EPIHz_magnitude.nii')]
        with open(epiJson, 'w') as f:
            json.dump(epijsondata, f, indent=4)

    dtiJson = fmap_dir / str(subjroot + '_acq-DTIHz_fieldmap.json')
    if dtiJson.exists():
        with open(dtiJson, 'r') as f:
            dtijsondata = json.load(f)
            for k in range(len(dtijsondata['IntendedFor'])):
                dtijsondata['IntendedFor'][k] = dtijsondata['IntendedFor'][k].replace('FieldmapDTI_magnitude1', 'DTIHz_magnitude')
        with open(dtiJson, 'w') as f:
            json.dump(dtijsondata, f, indent=4)


def runall(ses_dir):
    fixRSjsons(ses_dir)
    fixFieldmapFilenames(ses_dir)
    fixFieldmapJSONS(ses_dir)

ses_dirs = (ses_dir for ses_dir in BIDS_Master.glob('*/ses-*'))

for ses_dir in ses_dirs:
    runall(ses_dir)
