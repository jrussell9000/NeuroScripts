#!/usr/bin/env python3
import sys, nibabel, tarfile
import shutil, argparse
from nipype.interfaces.dcm2nii import Dcm2niix


# Making an argument parser

ap = argparse.ArgumentParser()
ap.add_argument("-f", "--file", required=True, help="Compressed scan file")
args = vars(ap.parse_args())

gzipfile = tarfile.open(args["file"])

gzipfile.extractall(path=".")
gzipfile.close()

converter = Dcm2niix()
converter.inputs.source_dir = 's0003.MPRAGE'
converter.inputs.output_dir = '.'
converter.cmdline
converter.run()