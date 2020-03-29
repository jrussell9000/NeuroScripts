#!/usr/bin/env python3
# coding: utf-8

import shutil
from bids_validator import BIDSValidator
from pathlib import Path

validator = BIDSValidator()


def fmap_rename(ses_dir):

    ses_dir = Path(ses_dir)
    subj_dir = ses_dir.parent
    fmap_dir = ses_dir / 'fmap'
    print(fmap_dir)
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    print(subjroot)
    for niifile in fmap_dir.glob('*.nii'):
        print(niifile)
        acq = niifile.name.split("_")[2]
        if "RealFieldmap" in acq:
            new_acq = acq.replace('RealFieldmap', '')
        elif "Fieldmap" in acq:
            new_acq = acq.replace('Fieldmap', '')
        else:
            new_acq = acq

        modality_label = niifile.name.split("_")[3]
        if modality_label == "fmap.nii":
            new_modality_label = "phasediff.nii"
        elif modality_label == "magnitude1.nii":
            new_modality_label = modality_label

        if subjroot is not None and new_acq is not None and new_modality_label is not None:
            ren_niifile = Path(fmap_dir / "_".join([subjroot, new_acq, new_modality_label]))
            shutil.move(niifile, ren_niifile)
        else:
            next

    for jsonfile in fmap_dir.glob('*.json'):
        acq = jsonfile.name.split("_")[2]
        if "RealFieldmap" in acq:
            new_acq = acq.replace('RealFieldmap', '')
        elif "Fieldmap" in acq:
            new_acq = acq.replace('Fieldmap', '')
        else:
            new_acq = acq

        modality_label = niifile.name.split("_")[3]
        if modality_label == "fmap.nii":
            new_modality_label = "phasediff.nii"
        elif modality_label == "magnitude1.nii":
            new_modality_label = modality_label

        if subjroot is not None and new_acq is not None and new_modality_label is not None:
            ren_jsonfile = Path(fmap_dir / "_".join([subjroot, new_acq, new_modality_label]))
            shutil.move(jsonfile, ren_jsonfile)
        else:
            next


fmap_rename('/Volumes/Users/jdrussell3/sub-001/ses-01/')
