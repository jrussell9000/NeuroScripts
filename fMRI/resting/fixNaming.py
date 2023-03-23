#!/usr/bin/env python3
# coding: utf-8

from pathlib import Path
import os
import json

BIDS_Master = Path('/fast_scratch/jdr/resting/extrafmriprep_in')


def fixRestingFilename(ses_dir):
    subjroot = str(ses_dir.parent.name + '_' + ses_dir.name)
    ses_dir = Path(ses_dir)
    func_dir = ses_dir / 'func'
    restingnii = func_dir / str(subjroot + '_task-EPIDynamicFaces_bold.nii')
    if not dynamicfacesnii.exists():
        dynamicfacesnii_alt = func_dir / str(subjroot + '_task-DynamicFaces_bold.nii')
        dynamicfacesnii_rename = func_dir / str(subjroot + '_task-EPIDynamicFaces_bold.nii')
        os.rename(dynamicfacesnii_alt, dynamicfacesnii_rename)


def fixDynamicFacesJSON(ses_dir):
    subjroot = str(ses_dir.parent.name + '_' + ses_dir.name)
    ses_dir = Path(ses_dir)
    func_dir = ses_dir / 'func'
    dynamicfaces_json = func_dir / str(subjroot + '_task-EPIDynamicFaces_bold.json')
    if not dynamicfaces_json.exists():
        dynamicfacesjson_alt = func_dir / str(subjroot + '_task-DynamicFaces_bold.json')
        dynamicfacesjson_rename = func_dir / str(subjroot + '_task-EPIDynamicFaces_bold.json')
        os.rename(dynamicfacesjson_alt, dynamicfacesjson_rename)
        dynamicfaces_json = dynamicfacesjson_rename

    intendedForDynamicFaces = str(ses_dir.name + '/func/' + subjroot + '_task-EPIDynamicFaces_bold.nii')
    fieldmapjson = ses_dir / 'fmap' / str(subjroot + '_acq-EPIHz_phasediff.json')
    if fieldmapjson.exists():
        with open(fieldmapjson, 'r', encoding="ISO-8859-1") as f:
            data = json.load(f)
            data['IntendedFor'] = [intendedForDynamicFaces]
        os.remove(fieldmapjson)
        with open(fieldmapjson, 'w') as f:
            json.dump(data, f, indent=4)


def fixFieldmapFilenames(ses_dir):
    subjroot = str(ses_dir.parent.name + '_' + ses_dir.name)
    ses_dir = Path(ses_dir)
    fmap_dir = ses_dir / 'fmap'
    magnitude_orig = fmap_dir / str(subjroot + '_acq-FieldmapEPI_magnitude1.nii')
    if magnitude_orig.exists():
        magnitude_renamed = fmap_dir / str(subjroot + '_magnitude.nii')
        os.rename(magnitude_orig, magnitude_renamed)
    phasediffnii_orig = fmap_dir / str(subjroot + '_acq-EPIHz_phasediff.nii')
    if phasediffnii_orig.exists():
        phasediffnii_renamed = fmap_dir / str(subjroot + '_phasediff.nii')
        os.rename(phasediffnii_orig, phasediffnii_renamed)
    phasediffjson_orig = fmap_dir / str(subjroot + '_acq-EPIHz_phasediff.json')
    if phasediffjson_orig.exists():
        phasediffjson_renamed = fmap_dir / str(subjroot + '_phasediff.json')
        os.rename(phasediffjson_orig, phasediffjson_renamed)


def fixFieldmapJson(ses_dir):
    subjroot = str(ses_dir.parent.name + '_' + ses_dir.name)
    ses_dir = Path(ses_dir)
    fmap_dir = ses_dir / 'fmap'
    epiFieldmapjson = fmap_dir / str(subjroot + '_acq-EPIHz_phasediff.json')
    if epiFieldmapjson.exists():
        # Open the json file for the fieldmap, and edit the IntendedFor key to match the magnitude file name
        with open(epiFieldmapjson, 'r') as f:
            epijsondata = json.load(f)
            for k in range(len(epijsondata['IntendedFor'])):
                epijsondata['IntendedFor'][k] = epijsondata['IntendedFor'][k].replace('FieldmapEPI', 'EPIHz')
                epijsondata['IntendedFor'][k] = epijsondata['IntendedFor'][k].replace('magnitude1', 'magnitude')
        with open(epiFieldmapjson, 'w') as f:
            json.dump(epijsondata, f, indent=4)
        epiMagnii = fmap_dir / str(subjroot + '_acq-FieldmapEPI_magnitude1.nii')
        if epiMagnii.exists():
            epiMagnii.rename(fmap_dir / str(subjroot + '_acq-EPIHz_magnitude.nii'))

    dtiFieldmapjson = fmap_dir / str(subjroot + '_acq-DTIHz_phasediff.json')
    if dtiFieldmapjson.exists():
        with open(dtiFieldmapjson, 'r') as f:
            dtijsondata = json.load(f)
            for k in range(len(dtijsondata['IntendedFor'])):
                dtijsondata['IntendedFor'][k] = dtijsondata['IntendedFor'][k].replace('FieldmapDTI', 'DTIHz')
                dtijsondata['IntendedFor'][k] = dtijsondata['IntendedFor'][k].replace('magnitude1', 'magnitude')
        with open(dtiFieldmapjson, 'w') as f:
            json.dump(dtijsondata, f, indent=4)
        dtiMagnii = fmap_dir / str(subjroot + '_acq-FieldmapDTI_magnitude1.nii')
        if dtiMagnii.exists():
            dtiMagnii.rename(fmap_dir / str(subjroot + '_acq-DTIHz_magnitude.nii'))





ses_dirs = (ses_dir for ses_dir in BIDS_Master.glob('*/ses-*'))

for ses_dir in ses_dirs:
    fixFieldmapJson(ses_dir)
