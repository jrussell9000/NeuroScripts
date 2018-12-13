#!/usr/bin/env python3
import os, sys, nibabel, tarfile, glob
import shutil, argparse
from pathlib import Path
from nipype.interfaces.dcm2nii import Dcm2niix


# Making an argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-d", "--dicomdir", required=True, help="Directory containing compressed dicoms from the scanner.")
#ap.add_argument("-s", "--subjectdir", required=True, help="Where should the BIDS directory be created?")
args = vars(ap.parse_args())

#Opening the file argument and labeling it 'gzipfile'
# ftar = tarfile.open(args["dicomdir"], mode='w:gz')
# for member in ftar.getmembers():
#   if "dcm" in member.name:
#     ftar.extractall(path=".", members=member)



for filename in os.listdir(args["dicomdir"]):
  if filename.endswith(".tgz"):
    f = tarfile.open(filename)
    f.extractall(path=".")

#List all files in directory

for root,dirs,files in os.walk(args["dicomdir"], topdown=True):
  for file_name in files:
    if file_name.endswith(('.dcm')):
      pa = os.path.split(os.path.abspath(file_name))[0]
      os.rmdir(pa)

#
# converter = Dcm2niix()
# converter.inputs.source_dir = 's0003.MPRAGE'
# converter.inputs.output_dir = '.'
# converter.cmdline
# converter.run()
