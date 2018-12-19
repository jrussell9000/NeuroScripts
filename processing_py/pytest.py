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


# Making an argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-s", "--studypath", required=False,
                help="Directory containing subject folders downloaded \
                from the scanner. Will look for subject folders \
                containing one or more Gzip compressed (.TGZ) files \
                holding the raw DICOM files output by the scanner.")
ap.add_argument("-o", "--outputpath", required=True)
ap.add_argument("-d", "--dicompath", required=False)
#ap.add_argument("-s", "--subjectdir", required=True, help="Where should the BIDS directory be created?")
args = vars(ap.parse_args())

#
# Opening the file argument and labeling it 'gzipfile'
# ftar = tarfile.open(args["dicomdir"], mode='w:gz')
# for member in ftar.getmembers():
#   if "dcm" in member.name:
#     ftar.extractall(path=".", members=member)

dicompath = args["dicompath"]
outputpath = args["outputpath"]

for subjID_dir in os.listdir(dicompath):
    subjID = subjID_dir
    subjID_dir = os.path.join(dicompath, subjID_dir)
    print("FOUND SUBJECT ID#:", subjID, "IN", dicompath, "\n")
    tmpdir = tempfile.mkdtemp(suffix=subjID)
    for filename in os.listdir(subjID_dir):
        if filename.endswith(".tgz"):
            dicompack = os.path.join(subjID_dir, filename)
            shutil.copy(dicompack, tmpdir)
            dicompack = os.path.join(tmpdir, filename)
            scanfile = tarfile.open(dicompack, 'r:gz')
            scanfile.extractall(path=tmpdir)
            
            tmpsubjdir = os.path.join(tmpdir, os.path.commonprefix(scanfile.getnames()))
            print(tmpsubjdir)
            outsubjdir = os.path.join(outputpath, tmpsubjdir)
            #Scan String
            
            subprocess.Popen(["dcm2niix", "-f", "sub-" + subjID, "-o", outputpath, outsubjdir])


# # List all files in directory

# for startdir, subdirs, files in os.walk(args["dicompath"], topdown=True):
#     for file_name in files:
#         if file_name.endswith(('.dcm')):
#             dcmdir=startdir
#             print(startdir)
#             subprocess.Popen(["dcm2niix", dcmdir])
#             break
#
# converter = Dcm2niix()
# converter.inputs.source_dir = 's0003.MPRAGE'
# converter.inputs.output_dir = '.'
# converter.cmdline
# converter.run()
