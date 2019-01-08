#!/usr/bin/env python3
import os
import sys
import tarfile
import glob
import shutil
import argparse
from pathlib import Path
import subprocess
import tempfile
import json


class BidsConv():

    def __init__(self):
        self.verbose = False

    def initialize(self):
        ap = argparse.ArgumentParser()
        ap.add_argument("-s", "--studypath", required=False,
                        help="Directory containing subject folders downloaded \
                        from the scanner. Will look for subject folders \
                        containing one or more Gzip compressed (.TGZ) files \
                        holding the raw DICOM files output by the scanner.")
        ap.add_argument("-o", "--outputpath", required=True)
        ap.add_argument("-d", "--dicompath", required=False)
        args = vars(ap.parse_args())

        #global studypath
        self.studypath = args["studypath"]
        self.outputpath = args["outputpath"]

    def scan2bidsmode(self, modstring):
        scan2bidsmode_dict = {
            "MPRAGE": "_T1w",
            "BRAVO": "_T1w",
            "NODDI": "_dwi",
            "EPI": "_bold",
            "Fieldmap": "_fmap"
        }
        returnkey = "nomatch"
        for key in scan2bidsmode_dict.keys():
            if key in modstring:
                returnkey = scan2bidsmode_dict[key]
        return(returnkey)

    def scan2bidstype(self, string):
        scan2bidstype_dict = {
            "MPRAGE": 0,
            "BRAVO": 0,
            "EPI": 1,
            "NODDI": 2,
            "Fieldmap": 3
        }
        returnkey = "nomatch"
        for key in scan2bidstype_dict.keys():
            if key in string:
                returnkey = scan2bidstype_dict[key]
        return(returnkey)

    def scan2bidsdir(self, typestring):
        scan2bidsdir_dict = {
            "MPRAGE": "anat",
            "BRAVO": "anat",
            "NODDI": "dwi",
            "EPI": "func",
            "Fieldmap": "fmap"
        }
        returnkey = "nomatch"
        for key in scan2bidsdir_dict.keys():
            if key in typestring:
                returnkey = scan2bidsdir_dict[key]
        return(returnkey)

#Prepping the scan

#1 Get the path to the dicom directory for this subject
# bc = BidsConv()
# for subjID_dir in os.listdir(bc.studypath):
#     self.runcount = 1
    def get_subj_dcms(self, subjID_dir):
        self.rawscan.subjID = subjID_dir
        subjID_dir = os.path.join(bc.studypath, subjID_dir)
        print("FOUND SUBJECT ID#:", self.rawscan.subjID, "IN", bc.studypath, "\n")
        self.dicompath = os.path.join(subjID_dir, "dicoms")
        self.tmpdir = tempfile.mkdtemp(suffix=self.rawscan.subjID)
    
    def unpack_dcms(self, dicompath, tmpdir):
        for filename in sorted(os.listdir(dicompath)):
            if filename.endswith(".tgz") and not "Screen_Save" in filename and not "SSFSE" in filename:
                self.dcmpack.path = os.path.join(dicompath, filename)
                shutil.copy(self.dcmpack.path, tmpdir)
                self.dcmpack.path = os.path.join(tmpdir, filename)
                self.dcmpack = tarfile.open(self.dcmpack.path, 'r:gz')
                self.dcmpack.extractall(path=tmpdir)
    
    def organize_dcms(self, dcmpack, tmpdir):
        rawscan = []
        #--Full path to the directory containing the raw dcm files - PASS TO dcm_conv
        self.rawscan.path = os.path.join(tmpdir, os.path.commonprefix(dcmpack.getnames()))
        #--Getting the name of the directory holding the raw dcm files
        rawscan.dir_name = os.path.commonprefix(dcmpack.getnames())
        #--Grabbing the sequence number from the name of the directory holding the raw dcms
        rawscan.seqno = int(rawscan.dir_name.split('.')[0][1:])
        #--Grabbing the type of scan from the name of the directory holding the raw dcms
        rawscan.type = rawscan.dir_name.split('.')[1]
        #Need to add converted bidsscan.session
        #bidsscan.session = bc.scan2bidssession(rawscan.???)
        
        #--Creating common fields
        bidsscan = []
        #---bidsscan.session: the wave of data collection formatted as a BIDS label string
        bidsscan.session = "ses-1"
        #---bidsscan.mode: the "modal" label for the scan per bids spec (e.g., anat, func, dwi)
        bidsscan.mode = bc.scan2bidsmode(rawscan.type)
        #---bidsscan.type: a numeric value (from the dict above) reflecting the type of scan (so it will change each time the loop is run)
        bidsscan.type = bc.scan2bidstype(rawscan.type)
        #---bidsscan.partlabel: the subject ID formatted as a BIDS label string
        bidsscan.partlabel = "sub-" + rawscan.subjID + "_"
        #---bidsscan.outdir: the path where the converted scan files will be written 
        self.bidsscan.outdir = os.path.join(bc.outputpath, bidsscan.subjID, bidsscan.session, bc.scan2bidsdir(bidsscan.dir_name))
        #---bidsscan.echo: if a multi-echo scan, the echo number in the volume formatted as a BIDS string and containing the dcm2niix echo flag
        bidsscan.echo = '_echo%e' if rawscan.type.__contains__('DUAL_ECHO') else ''   
        #!!!!!!!!FIX FOR FIELDMAPS

        #--Creating scan-type-specific fields

        #---Anatomical scans - nothing to do here

        #---Functional scans
        #----bidsscan.func.run_no: if a functional (EPI) scan, the run number (i.e., block) in the sequence
        bidsscan.func.run_no = "_run-" + str(rawscan.seqno) if rawscan.type.__contains__('EPI') else ''
        #----bidsscan.func.tasklabel: if a functional (EPI) scan, the BIDS formatted name of the task
        #!!!!!!!!NEED TO ADD RESTING STATE
        bidsscan.func.tasklabel = ""
        if rawscan.type.__contains__('Perspective'):
            bidsscan.func.tasklabel = '_task-Perspective'
        elif rawscan.type.__contains__('n-Back'):
            bidsscan.func.tasklabel = "_task-n-Back"

        #---Diffusion-weighted scans
        #----bidsscan.dwi.pedir: if a diffusion-weighted scan, the (semi-)BIDS formattedphase encoding direction 
        bidsscan.dwi.pedir = ""
        if rawscan.type.__contains__('pepolar0'):
            bidsscan.dwi.pedir = "_dir-PA"
        elif rawscan.type.__contains__('pepolar1'):
            bidsscan.dwi.pedir = "_dir-AP"
        
        #---Field maps

        #--Setting the acquisition label based on the scan type
        bidsscan.acqlabel = ""
        #---Anatomical: just replace the underscores
        if bidsscan.type == 0:
            bidsscan.acqlabel = "_acq-" + rawscan.type.replace("_","-")
        #---Functional: no acquisition label
        elif bidsscan.type == 1:
            bidsscan.acqlabel = ""
        #---Diffusion Weighted: the acquisition type
        elif bidsscan.type == 2:
            if rawscan.type.__contains__('HB'):
                bidsscan.acqlabel = "_acq-NODDI-multiband"
            else:
                bidsscan.acqlabel = "_acq-NODDI-singleband"

        #--Setting the file label to be passed to dcm2niix (conv_dcms)
        self.dcm2niix_label = bidsscan.partlabel \
        #---Add a task label if it's a functional volume
        + bidsscan.tasklabel if bidsscan.type == 1 else '' \
        + bidsscan.acqlabel \
        + bidsscan.func.run_no if bidsscan.type == 1 else '' \
        + bidsscan.mode
        #---Add an echo label if its a multi-echo volume
        #-Add an echo label
        + bidsscan.echo if len(bidsscan.echo) > 0 else '' \
        #---Add a phase encoding direction label if its a diffusion weighted volume
        + bidsscan.dwi.phasedir if bidsscan.dwi == 1 else '' \
        + bidsscan.echo \
        + bidsscan.mode 

   
    def conv_dcms(self, dcm2niix_label, outsubjdir):
        os.makedirs(outsubjdir, exist_ok=True)
        subprocess.run(["dcm2niix", "-f", dcm2niix_label, "-o", outsubjdir, self.rawscan.path])
        #Fix json bids file for fieldmaps here.
    
    def cleanup(self, tmpdir):
        shutil.rmtree(tmpdir)

    def main(self, studypath):
        for self.subjID_dir in os.listdir(studypath):
            self.initialize()
            self.get_subj_dcms(self.subjID_dir)
            self.unpack_dcms(self.dicompath, self.tmpdir)
            self.organize_dcms(self.dcmpack, self.tmpdir)
            self.conv_dcms(self.dcm2niix_label, self.outsubjdir)
        self.cleanup()

if __name__ == '__main__':
    bc = BidsConv()
    bc.main()
