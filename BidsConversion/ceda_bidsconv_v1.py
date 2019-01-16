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

    scanstoskip = ('Screen_Save', 'SSFSE')
    anatomicalscans = ('MPRAGE', 'BRAVO')
    functionalscans = ('EPI')
    dwiscans = ('NODDI')
    fieldmapscans = ('Fieldmap')

    bids_taskrun = 0

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

    def get_subj_dcms(self):
        self.subjID = self.subjID_dirname
        subjID_path = os.path.join(bc.studypath, self.subjID_dirname)
        print("FOUND SUBJECT ID#:", self.subjID, "IN", bc.studypath, "\n")
        self.dicomspath = os.path.join(subjID_path, "dicoms")
        self.tmpdir = tempfile.mkdtemp(suffix=self.subjID)

    def unpack_dcms(self, filename):
        # for filename in sorted(os.listdir(self.dicomspath)):
        self.dicomtgz_path = os.path.join(self.dicomspath, filename)
        shutil.copy(self.dicomtgz_path, self.tmpdir)
        self.dicomtgz_path = os.path.join(self.tmpdir, filename)
        self.dicomtgz_file = tarfile.open(self.dicomtgz_path, 'r:gz')
        print("Decompressing DICOM archive file " + filename + "...")
        self.dicomtgz_file.extractall(path=self.tmpdir)

    def organize_dcms(self):
        # --Full path to the directory containing the raw dcm files - PASS TO dcm_conv
        self.rawscan_path = os.path.join(
            self.tmpdir, os.path.commonprefix(self.dicomtgz_file.getnames()))
        # --Getting the name of the directory holding the raw dcm files
        rawscan_dirname = os.path.commonprefix(self.dicomtgz_file.getnames())
        # --Grabbing the sequence number from the name of the directory holding the raw dcms
        rawscan_seqno = int(rawscan_dirname.split('.')[0][1:])
        # --Grabbing the type of scan from the name of the directory holding the raw dcms
        self.rawscan_type = rawscan_dirname.split('.')[1]

        # Need to add converted bidsscan.session
        # bidsscan.session = bc.scan2bidssession(rawscan.???)

        # --Creating common fields
        # ---bidsscan.session: the wave of data collection formatted as a BIDS label string
        bidsscan_session = "ses-1"
        # ---bidsscan.mode: the "modal" label for the scan per bids spec (e.g., anat, func, dwi)
        bidsscan_mode = self.scan2bidsmode(self.rawscan_type)
        # # ---bidsscan.type: a numeric value (from the dict above) reflecting the type of scan (so it will change each time the loop is run)
        # bidsscan_type = self.scan2bidstype(rawscan_type)
        # ---bidsscan.partlabel: the subject ID formatted as a BIDS label string
        bidsscan_participantID = "sub-" + self.subjID
        # ---bidsscan.outdir: the path where the converted scan files will be written
        self.bidsscan_outdir = os.path.join(
            self.outputpath, bidsscan_participantID, bidsscan_session, self.scan2bidsdir(rawscan_dirname))
        # ---bidsscan.echo: if a multi-echo scan, the echo number in the volume formatted as a BIDS string and containing the dcm2niix echo flag
        bidsscan_echo = '_echo%e' if self.rawscan_type.__contains__(
            'DUAL_ECHO') else ''

        #!!!!!!!!FIX FOR FIELDMAPS

        # --Creating scan-type-specific fields
        # ---Anatomical scans 
            # - nothing to do here
        # ---Functional scans
        # ----bidsscan_run_no: if a functional (EPI) scan, the run number (i.e., block) in the sequence
        bidsscan_run_no = ""
        # ----bidsscan_tasklabel: if a functional (EPI) scan, the BIDS formatted name of the task
        bidsscan_tasklabel = ""
        #A better fix to the run # problem would involve reading and processing the entire dicom
        #directory BEFORE the loop starts - would extract the number of EPI scans, the tasks names, and run #s
        #For now, we'll just use a global counter 
        if self.rawscan_type.__contains__('Perspective'):
            bidsscan_tasklabel = '_task-Perspective'
            bidsscan_run_no = "_run-" + str(self.bids_taskrun)
            self.bids_taskrun = self.bids_taskrun + 1
        elif self.rawscan_type.__contains__('n-Back'):
            bidsscan_tasklabel = "_task-n-Back"
        elif self.rawscan_type.__contains__('Resting'):
            bidsscan_tasklabel = '_task-RestingState'
        # ---Diffusion-weighted scans
        # ----bidsscan.dwi.pedir: if a diffusion-weighted scan, the (semi-)BIDS formattedphase encoding direction
        bidsscan_dwi_pedir = ""
        if self.rawscan_type.__contains__('pepolar0'):
            bidsscan_dwi_pedir = "_dir-PA"
        elif self.rawscan_type.__contains__('pepolar1'):
            bidsscan_dwi_pedir = "_dir-AP"
        # ---Field maps

        # --Setting the acquisition label based on the scan type

        bidsscan_acqlabel = ""
        # ---Anatomical: just replace the underscores
        if any(x in self.rawscan_type for x in self.anatomicalscans):
            bidsscan_acqlabel = "_acq-" + self.rawscan_type.replace("_", "-")
        # ---Functional: no acquisition label
        elif self.rawscan_type.__contains__('EPI'):
            bidsscan_acqlabel = ""
        # ---Diffusion Weighted: the acquisition type
        elif self.rawscan_type.__contains__('NODDI'):
            if self.rawscan_type.__contains__('HB'):
                bidsscan_acqlabel = "_acq-NODDI-multiband"
            else:
                bidsscan_acqlabel = "_acq-NODDI-singleband"
        # ---Fieldmaps: just replace the underscores
        elif self.rawscan_type.__contains__('Fieldmap'):
            bidsscan_acqlabel = "_acq-" + self.rawscan_type.replace("_", "-")

        # --Setting the file label to be passed to dcm2niix (conv_dcms)
        self.dcm2niix_label = ''
        self.dcm2niix_label = bidsscan_participantID + \
        bidsscan_tasklabel + bidsscan_acqlabel + \
        bidsscan_run_no + \
        bidsscan_echo + \
        bidsscan_dwi_pedir + bidsscan_mode

    def conv_dcms(self):
        os.makedirs(self.bidsscan_outdir, exist_ok=True)
        print(self.rawscan_type)
        print("dcm2niix" + " -f " + self.dcm2niix_label + " -o " +
              self.bidsscan_outdir + " " + self.rawscan_path)
        subprocess.run(["dcm2niix", "-f", self.dcm2niix_label,
                        "-o", self.bidsscan_outdir, self.rawscan_path])
        print("\n")
        # Fix json bids file for fieldmaps here.

    def cleanup(self):
        shutil.rmtree(self.tmpdir)

    def main(self):
        try:
            self.initialize()
        except:
            sys.exit(1)
        for self.subjID_dirname in os.listdir(self.studypath):
            self.get_subj_dcms()
            for filename in sorted(os.listdir(self.dicomspath)): 
                if filename.endswith('.tgz') and not any(x in filename for x in self.scanstoskip):
                    self.unpack_dcms(filename)
                    self.organize_dcms()
                    self.conv_dcms()
        self.cleanup()

if __name__ == '__main__':

    bc = BidsConv()
    bc.main()
