#!/usr/bin/env python3
import os, sys, tarfile, shutil, argparse, subprocess, tempfile, bz2
from pathlib import Path, PurePath
from distutils.dir_util import copy_tree

class BidsConv():

    scanstoskip = ('cardiac', 'ssfse', 'ADC', 'FA', 'CMB', 'assetcal', '3dir', 'epi')
    anatomicalscans = ('bravo', 'fse')
    functionalscans = ('epi')
    dwiscans = ('dwi')
    fieldmapscans = ('fmap')

    bids_taskrun = 0

    def __init__(self):
        self.verbose = False

    def initialize(self):
        ap = argparse.ArgumentParser()
        ap.add_argument("-s", "--studypath", required=True,
                        help="Directory containing subject folders downloaded \
                        from the scanner. Will look for subject folders \
                        each containing a 'dicoms' directory. Each scan is \
                        expected to be contained in a reflectively named \
                        directory (e.g., s04_bravo). Raw scan files are dcm \
                        series files compressed into a multiple file bz2 archive.")
        ap.add_argument("-o", "--outputpath", required=True)
        args = vars(ap.parse_args())

        self.studypath = args["studypath"]
        self.outputpath = args["outputpath"]

    def scan2bidsmode(self, modstring):
        scan2bidsmode_dict = {
            "bravo": "_T1w",
            "fse" : "_T2w",
            "epi" : "_bold",
            "dti": "_dwi",
            "fmap": "_fmap"
        }
        returnkey = "nomatch"
        for key in scan2bidsmode_dict.keys():
            if key in modstring:
                returnkey = scan2bidsmode_dict[key]
        return(returnkey)

    def scan2bidsdir(self, typestring):
        scan2bidsdir_dict = {
            "bravo": "anat",
            "fse" : "anat",
            "epi" : "func",
            "dti": "dwi",
            "fmap": "fmap"
        }
        returnkey = "nomatch"
        for key in scan2bidsdir_dict.keys():
            if key in typestring:
                returnkey = scan2bidsdir_dict[key]
        return(returnkey)

    def get_subj_dcms(self):
        self.subjID = self.subjID_dirname.replace("_", "")
        if not self.subjID.__contains__('rescan'):
            self.wave_no = 1         
        else:
            self.subjID = 2
            self.subjID = self.subjID.replace("rescan","")
        subjID_path = os.path.join(self.studypath, self.subjID_dirname)
        print("FOUND SUBJECT ID#:", self.subjID, "IN", self.studypath, "\n")
        self.dicomspath = Path(subjID_path, "dicoms")
        self.tmpdir = tempfile.mkdtemp(suffix=self.subjID)

    def unpack_dcms(self, fdir):
        self.rawscan_path = os.path.normpath(str(fdir))
        self.rawscan_dirname = os.path.basename(os.path.normpath(self.rawscan_path))
        os.mkdir(os.path.join(self.tmpdir, self.rawscan_dirname))
        self.tmpdest = os.path.join(self.tmpdir, self.rawscan_dirname)
        copy_tree(self.rawscan_path, self.tmpdest)
        bz2_list = (z for z in sorted(os.listdir(self.tmpdest)) if z.endswith('.bz2'))
        for filename in bz2_list:
            filepath = os.path.join(self.tmpdest, filename)
            newfilepath = os.path.join(self.tmpdest, filename.replace(".bz2",""))
            with open(newfilepath, 'wb') as new_file, open(filepath, 'rb') as file:
                decompressor = bz2.BZ2Decompressor()
                for data in iter(lambda : file.read(100 * 1024), b''):
                    new_file.write(decompressor.decompress(data))

    def organize_dcms(self):
        # --Full path to the directory containing the raw dcm files - PASS TO dcm_conv
        self.rawscan_path = self.tmpdest
        # --Getting the name of the directory holding the raw dcm files
        self.rawscan_dirname = os.path.basename(os.path.normpath(self.rawscan_path))
        # --Grabbing the sequence number from the name of the directory holding the raw dcms
        rawscan_seqno = int(self.rawscan_dirname.split('_')[0][1:])
        # --Grabbing the type of scan from the name of the directory holding the raw dcms
        self.rawscan_type = self.rawscan_dirname.split('_')[1]
        bids_acqlabel = ""
        bids_runno = ""
        yamlfile = os.path.join(self.rawscan_path, self.rawscan_dirname + '.yaml')
        with open(yamlfile, "r") as yfile:
            for line in yfile:
                if line.startswith("  SeriesDescription:"):
                    bids_acqlabel = line.split(': ')[1]
                    bids_acqlabel = bids_acqlabel.strip()
                    bids_acqlabel = bids_acqlabel.replace(" ","_")
                    bids_acqlabel = "_acq-" + bids_acqlabel
                    break
        with open(yamlfile, "r") as yfile2:
            for line in yfile2:
                if line.startswith("  SeriesNumber: "):
                    bids_runno = line.split(': ')[1]
                    bids_runno = "_run-" + bids_runno
                    break
                    
        # Need to add converted bids_session
        # bids_session = bc.scan2bidssession(rawscan.???)

        # --Creating common fields
        # ---bids_scansession: the wave of data collection formatted as a BIDS label string
        bids_scansession = "ses-" + str(self.wave_no)
        # ---bids_scanmode: the "modal" label for the scan per bids spec (e.g., anat, func, dwi)
        bids_scanmode = self.scan2bidsmode(self.rawscan_type)
        # ---bids_participantID: the subject ID formatted as a BIDS label string
        bids_participantID = "sub-" + self.subjID
        # ---bids_outdir: the path where the converted scan files will be written
        self.dcm2niix_outdir = os.path.join(
            self.outputpath, bids_participantID, bids_scansession, self.scan2bidsdir(self.rawscan_type))
        # ---bids_echo: if a multi-echo scan, the echo number in the volume formatted as a BIDS string and containing the dcm2niix echo flag
        #bids_echo = '_echo%e' if self.rawscan_type.__contains__(
            #'DUAL_ECHO') else ''

        #!!!!!!!!FIX FOR FIELDMAPS

        # --Creating scan-type-specific fields
        # ---Anatomical scans
        # - nothing to do here

        # ----bids_tasklabel: if a functional (EPI) scan, the BIDS formatted name of the task
        # if bids_scanmode == '_bold':
        #     rawscan_picklefname = str(self.rawscan_dirname) + '.pickle'
        #     rawscan_picklefpath = os.path.join(self.rawscan_path,rawscan_picklefname)
        #     rawscan_picklefile = open(rawscan_picklefpath, 'rb') 
        #     rawscan_dict = pickle.load(rawscan_picklefile)
        #     bids_epitasklabel = rawscan_dict(['native_header']['SeriesDescription'])
        #     bids_epirun_no = rawscan_dict(['native_header']['SeriesNumber'])
        # else:
        #     bids_epitasklabel = ''
        #     bids_epirun_no = ''

             
        # A better fix to the run # problem would involve reading and processing the entire dicom
        # directory BEFORE the loop starts - would extract the number of EPI scans, the tasks names, and run #s
        # For now, we'll just use a global counter
        # if self.rawscan_type.__contains__('Perspective'):
        #     bids_tasklabel = '_task-Perspective'
        #     bids_run_no = "_run-" + str(self.bids_taskrun)
        #     self.bids_taskrun = self.bids_taskrun + 1
        # elif self.rawscan_type.__contains__('n-Back'):
        #     bids_tasklabel = "_task-n-Back"
        # elif self.rawscan_type.__contains__('Resting'):
        #     bids_tasklabel = '_task-RestingState'
        # ---Diffusion-weighted scans
        # ----bids_dwi.pedir: if a diffusion-weighted scan, the (semi-)BIDS formattedphase encoding direction
        # bids_dwi_pedir = ""
        # if self.rawscan_type.__contains__('pepolar0'):
        #     bids_dwi_pedir = "_dir-PA"
        # elif self.rawscan_type.__contains__('pepolar1'):
        #     bids_dwi_pedir = "_dir-AP"
        # ---Field maps

        # bids_acqlabel = ""
        # # ---Anatomical: just replace the underscores
        # if any(x in self.rawscan_type for x in self.anatomicalscans):
        #     bids_acqlabel = "_acq-" + self.rawscan_type
        # # ---Functional: no acquisition label
        # elif self.rawscan_type.__contains__('epi'):
        #     bids_acqlabel = ""
        # # ---Diffusion Weighted: the acquisition type
        # elif self.rawscan_type.__contains__('dwi'):
        #     bids_acqlabel = "_acq-dwi-singleband"
        # # ---Fieldmaps: just replace the underscores
        # elif self.rawscan_type.__contains__('fmap'):
        #     bids_acqlabel = ""

        # --Setting the file label to be passed to dcm2niix (conv_dcms)
        self.dcm2niix_label = ''
        self.dcm2niix_label = bids_participantID + \
            bids_acqlabel + \
            bids_scanmode + \
            bids_runno
        print(self.dcm2niix_label + "\n")

    def conv_dcms(self):
        os.makedirs(self.dcm2niix_outdir, exist_ok=True)
        print(self.rawscan_type)
        print("dcm2niix" + " -f " + self.dcm2niix_label + " -o " +
              self.dcm2niix_outdir + " " + self.rawscan_path)
        subprocess.run(["dcm2niix", "-f", self.dcm2niix_label,
                        "-o", self.dcm2niix_outdir, self.rawscan_path])
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
            gen = (fdir for fdir in sorted(self.dicomspath.iterdir()) if fdir.is_dir())
            for fdir in gen:
                if not any(x in str(fdir) for x in self.scanstoskip):
                    self.unpack_dcms(fdir)
                    self.organize_dcms()
                    self.conv_dcms()

if __name__ == '__main__':

    bc = BidsConv()
    bc.main()
