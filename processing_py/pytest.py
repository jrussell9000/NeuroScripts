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
with tempfile.TemporaryDirectory() as tempdir:
    for filename in os.listdir(dicompath):
        if filename.endswith(".tgz"):
            dicompack = os.path.join(args["dicompath"], filename)
            with tarfile.open(dicompack, 'r:gz') as f:
                f.extractall(path=tmpdir)  


# List all files in directory

for startdir, subdirs, files in os.walk(args["dicompath"], topdown=True):
    for file_name in files:
        if file_name.endswith(('.dcm')):
            dcmdir=startdir
            print(startdir)
            subprocess.Popen(["dcm2niix", dcmdir])
            break
                # pa = os.path.split(os.path.abspath(file_name))[0]
                # os.rmdir(pa)

#
# converter = Dcm2niix()
# converter.inputs.source_dir = 's0003.MPRAGE'
# converter.inputs.output_dir = '.'
# converter.cmdline
# converter.run()
