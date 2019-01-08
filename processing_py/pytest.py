#!/usr/bin/env python3
import os
import sys
import nibabel
import tarfile
import glob
import shutil
import argparse
from pathlib import Path
import pydicom
import subprocess
from nipype.interfaces.dcm2nii import Dcm2niix
import tempfile
import json


# Making an argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-s", "--studypath", required=False,
                help="Directory containing subject folders downloaded \
                from the scanner. Will look for subject folders \
                containing one or more Gzip compressed (.TGZ) files \
                holding the raw DICOM files output by the scanner.")
ap.add_argument("-o", "--outputpath", required=True)
ap.add_argument("-d", "--dicompath", required=False)
args = vars(ap.parse_args())

studypath = args["studypath"]
outputpath = args["outputpath"]

scan2bidsdir_dict = {
    "MPRAGE":"anat",
    "BRAVO":"anat",
    "NODDI":"dwi",
    "EPI":"func",
    "Fieldmap":"fmap"
}

scan2bidsmode_dict = {
    "MPRAGE":"_T1w",
    "BRAVO":"_T1w",
    "NODDI":"_dwi",
    "EPI":"_bold",
    "Fieldmap":"_fmap"
}

def scan2bidsmode(modstring):
    returnkey = "nomatch"
    for key in scan2bidsmode_dict.keys():
        if key in modstring:
            returnkey = scan2bidsmode_dict[key]
    return(returnkey)

def scan2bidsdir(typestring):
    returnkey = "nomatch"
    for key in scan2bidsdir_dict.keys():
        if key in typestring:
            returnkey = scan2bidsdir_dict[key]
    return(returnkey)

for subjID_dir in os.listdir(studypath):
    subjID = subjID_dir
    subjID_dir = os.path.join(studypath, subjID_dir)
    print("FOUND SUBJECT ID#:", subjID, "IN", studypath, "\n")
    dicompath = os.path.join(subjID_dir, "dicoms")
    tmpdir = tempfile.mkdtemp(suffix=subjID)
    i_1=1
    #For each file in the subject directory that's not a screenshot or localizer sequence...
    for filename in sorted(os.listdir(dicompath)):
        if filename.endswith(".tgz") and not "Screen_Save" in filename and not "SSFSE" in filename:
            #Get the name of the gzipped dicom archive, copy it to the tmpdir, and unpack it as 'scanfile'
            dicompack = os.path.join(dicompath, filename)
            shutil.copy(dicompack, tmpdir)
            dicompack = os.path.join(tmpdir, filename)
            scanfile = tarfile.open(dicompack, 'r:gz')
            scanfile.extractall(path=tmpdir)
            #Parse the name of the directory in the archive to get the sequence number and scan type
            scanpath = os.path.join(tmpdir, os.path.commonprefix(scanfile.getnames()))
            scandir = os.path.commonprefix(scanfile.getnames())
            scancnt = int(scandir.split('.')[0][1:])
            scansession = "ses-1"
            scantype = scandir.split('.')[1]
            bids_folder = scan2bidsdir(scantype)
            bids_mode = scan2bidsmode(scantype)
            bids_acqlabel = "_acq-" + scantype.replace("_","-")
            bids_subjID = "sub-" + subjID + "_"
            outsubjdir = os.path.join(outputpath, subjID, scansession, bids_folder)
            # print("Scan directory is " + scandir)
            # print("Sequence number is " + str(scancnt))
            # print("Scan type is " + scantype)      
            # print("BIDS folder is " + bids_folder)
            # print("BIDS modality is " + bids_mode)
            # print("BIDS ACQ label is " + bids_acqlabel)
            os.makedirs(outsubjdir, exist_ok=True)
            if any(x in scantype for x in ('MPRAGE','BRAVO')):
                #if scantype.__contains__('MPRAGE') or scantype.__contains__('BRAVO'): 
                if scantype.__contains__('DUAL_ECHO'):
                    dcm2niix_label = bids_subjID + scansession + bids_acqlabel + "_echo%e" + bids_mode
                    subprocess.run(["dcm2niix", "-f", dcm2niix_label, "-o", outsubjdir, scanpath])
                else:
                    dcm2niix_label = bids_subjID + scansession + bids_acqlabel + bids_mode
                    subprocess.run(["dcm2niix", "-f", dcm2niix_label, "-o", outsubjdir, scanpath])
            elif scantype.__contains__('EPI'):
                if scantype.__contains__('Perspective'):
                    run_no = "_run-" + str(i_1)
                    bids_tasklabel = "_task-Perspective"
                    dcm2niix_label = bids_subjID + scansession + bids_tasklabel + run_no + bids_mode
                    subprocess.run(["dcm2niix", "-f", dcm2niix_label, "-o", outsubjdir, scanpath])
                    i_1 = i_1 + 1
                elif scantype.__contains__('n-Back'):
                    bids_tasklabel = "_task-n-Back"
                    dcm2niix_label = bids_subjID + scansession + bids_tasklabel + bids_mode
                    subprocess.run(["dcm2niix", "-f", dcm2niix_label, "-o", outsubjdir, scanpath])
            elif scantype.__contains__('NODDI'):
                if scantype.__contains__('HB'):
                    bids_acqlabel = "_acq-NODDI-multiband"
                else:
                    bids_acqlabel = "_acq-NODDI-singleband"
                if scantype.__contains__('pepolar0'):
                    bids_dirlabel = "_dir-PA"
                elif scantype.__contains__('pepolar1'):
                    bids_dirlabel = "_dir-AP"
                else:
                    bids_dirlabel = ""
                dcm2niix_label = bids_subjID + scansession + bids_acqlabel + bids_dirlabel + bids_mode
                subprocess.run(["dcm2niix", "-f", dcm2niix_label, "-o", outsubjdir, scanpath])
            elif scantype.__contains__('Fieldmap'):
                dcm2niix_label = bids_subjID + scansession + bids_acqlabel + bids_mode
                subprocess.run(["dcm2niix", "-f", dcm2niix_label, "-o", outsubjdir, scanpath])
                jsonbidsfile = os.path.join(outsubjdir, dcm2niix_label + ".json")
                print(jsonbidsfile)
                #with open(jsonbidsfile)
    shutil.rmtree(tmpdir)

