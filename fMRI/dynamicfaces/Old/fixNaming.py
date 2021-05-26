#!/usr/bin/env python3
# coding: utf-8

from pathlib import Path
import os
import json

BIDS_Master = Path('/fast_scratch/jdr/dynamicfaces/BIDS_Master/')


def fixDynamicFacesFilename(ses_dir):
    subjroot = str(ses_dir.parent.name + '_' + ses_dir.name)
    ses_dir = Path(ses_dir)
    func_dir = ses_dir / 'func'
    dynamicfacesnii = func_dir / str(subjroot + '_task-EPIDynamicFaces_bold.nii')
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
        magnitude_renamed = fmap_dir / str(subjroot + '_magnitude1.nii')
        os.rename(magnitude_orig, magnitude_renamed)
    phasediffnii_orig = fmap_dir / str(subjroot + '_acq-EPIHz_phasediff.nii')
    if phasediffnii_orig.exists():
        phasediffnii_renamed = fmap_dir / str(subjroot + '_phasediff.nii')
        os.rename(phasediffnii_orig, phasediffnii_renamed)
    phasediffjson_orig = fmap_dir / str(subjroot + '_acq-EPIHz_phasediff.json')
    if phasediffjson_orig.exists():
        phasediffjson_renamed = fmap_dir / str(subjroot + '_phasediff.json')
        os.rename(phasediffjson_orig, phasediffjson_renamed)


ses_dirs = (ses_dir for ses_dir in BIDS_Master.glob('*/ses-*'))

for ses_dir in ses_dirs:
    fixDynamicFacesFilename(ses_dir)
    fixDynamicFacesJSON(ses_dir)
    fixFieldmapFilenames(ses_dir)
