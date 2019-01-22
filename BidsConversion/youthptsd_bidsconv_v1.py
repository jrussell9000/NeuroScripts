#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
import subprocess
import tempfile
import bz2
import json
from pathlib import Path
from distutils.dir_util import copy_tree



# - Utility function to underline strings
def stru(string):
    start = '\033[4m'
    end = '\033[0m'
    ustr = start + string + end
    return(ustr)


def printu(self, string):
    start = '\033[4m'
    end = '\033[0m'
    ustr = start + string + end
    print(ustr)


class BidsConv():

    scanstoskip = ('cardiac', 'ssfse', 'ADC', 'FA', 'CMB',
                   'assetcal', '3dir')

    subjectstoskip = ('EyeTrackTest', '_Rachael')

    data_description = {
        "Name": "Youth PTSD",
        "BIDSVersion": "1.1.1",
        "License": "None",
    }  

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
            "fse": "_T2w",
            "epi": "_bold",
            "dti": "_dwi",
        }
        returnkey = "nomatch"
        for key in scan2bidsmode_dict.keys():
            if key in modstring:
                returnkey = scan2bidsmode_dict[key]
        return(returnkey)

    def scan2bidsdir(self, typestring):
        scan2bidsdir_dict = {
            "bravo": "anat",
            "fse": "anat",
            "epi": "func",
            "dti": "dwi",
            "fmap": "fmap"
        }
        returnkey = "nomatch"
        for key in scan2bidsdir_dict.keys():
            if key in typestring:
                returnkey = scan2bidsdir_dict[key]
        return(returnkey)

    def scan2helpful(self, typestring):
        scan2helpful_dict = {
            "bravo": "AN ANATOMICAL - T1w",
            "fse": "AN ANATOMICAL - T2w",
            "epi": "A FUNCTIONAL",
            "dti": "A DIFFUSION WEIGHTED",
            "fmap": "A FIELD MAP"
        }
        returnkey = "UNKNOWN"
        for key in scan2helpful_dict.keys():
            if key in typestring:
                returnkey = scan2helpful_dict[key]
        return(returnkey)

    def get_subj_dcms(self):
        self.subjID = str(self.subjID_dirname).replace("_", "")
        if self.subjID.__contains__('rescan'):
            self.wave_no = 2
            self.subjID = self.subjID.replace("rescan", "")
        else:
            self.wave_no = 1
        subjID_path = Path(self.studypath, self.subjID_dirname)
        self.dicomspath = Path(subjID_path, "dicoms")
        self.subjID_tmpdir = tempfile.mkdtemp(suffix=self.subjID)

    # Copying the bzip files to /tmp/<scan_type> and decompressing there (faster)
    def unpack_dcms(self, fdir):
        
        # Getting info about the scan we're working with...
        self.rawscan_path = os.path.normpath(fdir)
        self.rawscan_dirname = os.path.basename(
            os.path.normpath(self.rawscan_path))
        self.rawscan_type = self.rawscan_dirname.split('_')[1]
        self.helpful_type = self.scan2helpful(self.rawscan_type)
        print("\n" + stru(str("FOUND " + self.helpful_type + " SCAN")) + ": " + self.rawscan_path + "\n")

        # Copying the scan's bzip files to /tmp/<scan_type> and decompressing there (time saver)
        os.mkdir(os.path.join(self.subjID_tmpdir, self.rawscan_dirname))
        self.tmpdest = os.path.join(self.subjID_tmpdir, self.rawscan_dirname)
        copy_tree(self.rawscan_path, self.tmpdest)

        # Decompressing scan files
        print(stru("Step 1") + ": Decompressing the raw DICOM archive files...\n")
        bz2_list = (z for z in sorted(os.listdir(
            self.tmpdest)) if z.endswith('.bz2'))
        for filename in bz2_list:
            filepath = os.path.join(self.tmpdest, filename)
            newfilepath = Path(
                self.tmpdest, filename.replace(".bz2", ""))
            with open(newfilepath, 'wb') as new_file, open(filepath, 'rb') as file:
                decompressor = bz2.BZ2Decompressor()
                for data in iter(lambda: file.read(100 * 1024), b''):
                    new_file.write(decompressor.decompress(data))

        self.rawscan_path = self.tmpdest
        self.rawscan_dirname = os.path.basename(
            os.path.normpath(self.rawscan_path))

    # Extracting all the info we'll need to name the file accordings to BIDS and create the JSON sidecar
    def organize_dcms(self):
        print(stru("Step 2") + ": Extracting the relevant BIDS parameters...\n")

        # Each scan folder should contain a YAML file with the scan info
        yaml_filepath = Path(self.rawscan_path, self.rawscan_dirname + '.yaml')

        if not yaml_filepath.exists():
            print("ERROR: A YAML file was not found in this scan's directory: " + self.rawscan_path)
            sys.exit(1)

        with open(yaml_filepath, "r") as yfile:
            for line in yfile:
                if line.startswith("  SeriesDescription:"):
                    bids_acqlabel = line.split(': ')[1]
                    self.bids_sidecar_taskname = bids_acqlabel.replace("\n", "")
                    bids_acqlabel = bids_acqlabel.strip()
                    for c in ['(', ')', '-', ' ']:
                        if c in bids_acqlabel:
                            bids_acqlabel = bids_acqlabel.replace(c, '')
                    bids_acqlabel = bids_acqlabel.replace(" ", "")
                    bids_acqlabel = "_acq-" + bids_acqlabel
                    break

        if self.rawscan_type.__contains__('epi'):
            bids_tasklabel = bids_acqlabel.replace("_acq-", "")
            bids_tasklabel = "_task-" + bids_tasklabel
            bids_acqlabel = ''
            with open(yaml_filepath, "r") as yfile2:
                for line in yfile2:
                    if line.startswith("  SeriesNumber: "):
                        bids_runno = line.split(': ')[1]
                        bids_runno = "_run-" + bids_runno
                        break
        else:
            bids_tasklabel = ''

        # --Creating common fields

        # ---bids_scansession: the wave of data collection formatted as a BIDS label string
        self.bids_scansession = "_ses-" + str(self.wave_no).zfill(2)
        self.bids_scansessiondir = "ses-" + str(self.wave_no).zfill(2)
        # ---bids_scanmode: the "modal" label for the scan per bids spec (e.g., anat, func, dwi)
        if self.rawscan_type.__contains__('fmap'):
            if bids_acqlabel.__contains__('EPI'):
                self.bids_scanmode = '_epirawfmap'
            elif bids_acqlabel.__contains__('DTI'):
                self.bids_scanmode = '_dwirawfmap'
        else:
            self.bids_scanmode = self.scan2bidsmode(self.rawscan_type)
        # ---bids_participantID: the subject ID formatted as a BIDS label string
        self.bids_participantID = "sub-" + self.subjID
        # ---bids_outdir: the path where the converted scan files will be written
        self.dcm2niix_outdir = os.path.join(
            self.outputpath, self.bids_participantID, self.bids_scansessiondir, self.scan2bidsdir(self.rawscan_type))

        # --Setting the file label to be passed to dcm2niix (conv_dcms)
        self.dcm2niix_label = ''
        self.dcm2niix_label = self.bids_participantID + \
            self.bids_scansession + \
            bids_tasklabel + \
            bids_acqlabel + \
            self.bids_scanmode

    def conv_dcms(self):
        print(stru("Step 3") + ": Converting to NIFTI using dcm2niix and sorting into appropriate BIDS folder...\n")
        os.makedirs(self.dcm2niix_outdir, exist_ok=True)
        # print("Running command: dcm2niix" + " -f " + self.dcm2niix_label + " -o " + self.dcm2niix_outdir + " " + self.rawscan_path)
        subprocess.run(["dcm2niix", "-f", self.dcm2niix_label,
                        "-o", self.dcm2niix_outdir, self.rawscan_path])
        if self.rawscan_type.__contains__('epi'):
            jsonfilepath = os.path.join(self.dcm2niix_outdir, self.dcm2niix_label + '.json')
            with open(jsonfilepath) as jsonfile:
                sidecar = json.load(jsonfile)
            sidecar['TaskName'] = self.bids_sidecar_taskname
            with open(jsonfilepath, 'w') as f:
                json.dump(sidecar, f)

    def make_fmap(self, scan_type):
        self.fmap_dir = os.path.join(
            self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'fmap')
        gen = (rawfmapfile for rawfmapfile in os.listdir(self.fmap_dir)
               if rawfmapfile.endswith('.nii') if rawfmapfile.__contains__(scan_type))

        if len(gen) > 0:
            for rawfmapfile in gen:
                if rawfmapfile.__contains__('_e1a.'):
                    rawfmapfile_2 = rawfmapfile

                elif rawfmapfile.__contains__('_e1.'):
                    rawfmapfile_1 = rawfmapfile

        os.chdir(self.fmap_dir)
        rawfmapfile_1v0 = str(rawfmapfile_1 + '[0]')
        rawfmapfile_1v2 = str(rawfmapfile_1 + '[2]')
        rawfmapfile_1v3 = str(rawfmapfile_1 + '[3]')
        rawfmapfile_2v0 = str(rawfmapfile_2 + '[0]')
        rawfmapfile_2v2 = str(rawfmapfile_2 + '[2]')
        rawfmapfile_2v3 = str(rawfmapfile_2 + '[3]')

        scan_type = str(scan_type)

        if scan_type.__contains__('epi'):
            wrappedphasefile = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_wrapped_phasediff')
            magoutfile1 = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_magnitude1')
            magoutfile2 = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_magnitude2')
            phasediffileRads = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_phasediff_rads')
            phasediffileHz = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_phasediff')
            # What scans does the field map go with?
            fmap_intendedfor_path = os.path.join(
                self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'func')
            fmap_intendedfor_dict = {}
            for scan in os.listdir(fmap_intendedfor_path):
                if scan.endswith('.nii'):
                    fmap_intendedfor_dict.setdefault("IntendedFor", []).append(
                        self.bids_scansessiondir + '/func/' + scan)
            print("\n" + stru("CREATING FIELD MAP FOR EPI SCANS:"))
        elif scan_type.__contains__('dwi'):
            wrappedphasefile = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_wrapped_phasediff')
            magoutfile1 = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_magnitude1')
            magoutfile2 = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_magnitude2')
            phasediffileRads = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_phasediff_rads')
            phasediffileHz = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_phasediff')
            # What scans does the field map go with?
            fmap_intendedfor_path = os.path.join(
                self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'dwi')
            fmap_intendedfor_dict = {}
            for scan in os.listdir(fmap_intendedfor_path):
                if scan.endswith('.nii'):
                    fmap_intendedfor_dict.setdefault("IntendedFor", []).append(
                        self.bids_scansessiondir + '/dwi/' + scan)
            print("\n" + stru("CREATING FIELD MAP FOR DTI SCANS:"))

        calc_computephase = "atan2((b*c-d*a),(a*c+b*d))"
        calc_extractmag = "a"
        te_diff = 3
        calc_rads2hz = "a*1000/" + str(te_diff)

        fmap_description = {
            "EchoTime1": ".007",
            "EchoTime2": ".010"
        }

        fmap_description.update(fmap_intendedfor_dict)

        # -Output the BIDS sidecar file describing this field map
        json_phasediffile = phasediffileHz.replace(".nii", ".json")
        with open(json_phasediffile, 'w') as outfile:
            json.dump(fmap_description, outfile)

        print("\n" + stru("Step 1") + ": Computing phase difference from raw fieldmap volume")
        # -Computing the phase difference from the raw fieldmap volume
        subprocess.call(["3dcalc", "-float", "-a", rawfmapfile_1v2, "-b", rawfmapfile_1v3, "-c", rawfmapfile_2v2, "-d", rawfmapfile_2v3,
                         "-expr", calc_computephase, "-prefix", wrappedphasefile])

        print("\n" + stru("Step 2") + ": Computing magnitude image #1")
        # -Extract magnitude image from first raw fieldmap volume
        subprocess.call(["3dcalc", "-a", rawfmapfile_1v0,
                         "-expr", calc_extractmag, "-prefix", magoutfile1])

        print("\n" + stru("Step 3") + ": Computing magnitude image #2")
        # -Extract magnitude image from second raw fieldmap volume
        subprocess.call(["3dcalc", "-a", rawfmapfile_2v0,
                         "-expr", calc_extractmag, "-prefix", magoutfile2])

        print("\n" + stru("Step 4") + ": Unwrapping the phase difference using FSL's 'prelude'")
        # -Unwrap the phase difference file
        subprocess.call(["prelude", "-v", "-p", wrappedphasefile,
                         "-a", magoutfile1, "-o", phasediffileRads])
        phasediffileRads = phasediffileRads + '.gz'

        print("\n" + stru("Step 5") + ": Converting the phase difference from radians to Hz")
        # -Convert the phase difference file from rads to Hz
        # -Formula for conversion: "a" x 1000 / x ; where x is the abs. value of the difference in TE between the two volumes
        subprocess.call(["3dcalc", "-a", phasediffileRads,
                         "-expr", calc_rads2hz, "-prefix", phasediffileHz])

        # Cleanup unnecessary fieldmap files and old sidecar files
        os.remove(wrappedphasefile)
        os.remove(phasediffileRads)
        os.remove(rawfmapfile_1)
        os.remove(rawfmapfile_1.replace('.nii', '.json'))
        os.remove(rawfmapfile_2)
        os.remove(rawfmapfile_2.replace('.nii', '.json'))

    def cleanup(self):
        shutil.rmtree(self.outputpath)

    def main(self):
        try:
            self.initialize()
        except:
            sys.exit(1)
        subjs = (sid_dir for sid_dir in sorted(os.listdir(self.studypath)) if not any(x in str(sid_dir) for x in self.subjectstoskip))
        for sid_dir in subjs:
            self.subjID_dirname = sid_dir
            self.get_subj_dcms()
            print(
                "\n".join(['#'*23, "FOUND SUBJECT ID#: " + self.subjID, '#'*23]))
            scandirs = (fdir for fdir in sorted(
                self.dicomspath.iterdir()) if fdir.is_dir() if not any (x in str(fdir) for x in self.scanstoskip))
            for fdir in scandirs:
                #if not any(x in str(fdir) for x in self.scanstoskip):
                    self.unpack_dcms(fdir)
                    self.organize_dcms()
                    self.conv_dcms()
            #self.addtasknames
            self.make_fmap('epi')
            self.make_fmap('dwi')
            self.cleanup()
            print("\n" + "#"*40 + "\n" + "CONVERSION AND PROCESSING FOR " +
                  self.subjID + " DONE!" + "\n" + "#"*40 + "\n")
        with open(os.path.join(self.outputpath, 'dataset_description.json'), 'w') as outfile:
            json.dump(self.data_description, outfile)


if __name__ == '__main__':

    bc = BidsConv()
    bc.main()
