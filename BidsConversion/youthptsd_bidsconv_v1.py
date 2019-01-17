#!/usr/bin/env python3
import os
import sys
import tarfile
import shutil
import argparse
import subprocess
import tempfile
import bz2
import json
from pathlib import Path, PurePath
from distutils.dir_util import copy_tree
import nipype
from nipype.interfaces import afni


class BidsConv():

    def printu(self, string):
        start = '\033[4m'
        end = '\033[0m'
        ustr = start + string + end
        print(ustr)

    scanstoskip = ('cardiac', 'ssfse', 'ADC', 'FA', 'CMB',
                   'assetcal', '3dir', 'dti', 'fse', 'bravo')
    anatomicalscans = ('bravo', 'fse')
    functionalscans = ('epi')
    dwiscans = ('dwi')
    fieldmapscans = ('fmap')

    data_description = {
        "Name": "Youth PTSD",
        "BIDSVersion": "1.1.1",
        "License": "None",
    }

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
            "bravo": "ANATOMICAL - T1w",
            "fse": "ANATOMICAL - T2w",
            "epi": "FUNCTIONAL",
            "dti": "DIFFUSION WEIGHTED",
            "fmap": "FIELD MAP"
        }
        returnkey = "UNKNOWN"
        for key in scan2helpful_dict.keys():
            if key in typestring:
                returnkey = scan2helpful_dict[key]
        return(returnkey)

    def get_subj_dcms(self):
        self.subjID = self.subjID_dirname.replace("_", "")
        if not self.subjID.__contains__('rescan'):
            self.wave_no = 1
        else:
            self.wave_no = 2
            self.subjID = self.subjID.replace("rescan", "")
        subjID_path = os.path.join(self.studypath, self.subjID_dirname)
        self.dicomspath = Path(subjID_path, "dicoms")
        self.tmpdir = tempfile.mkdtemp(suffix=self.subjID)

    def unpack_dcms(self, fdir):
        self.rawscan_path = os.path.normpath(str(fdir))
        self.rawscan_dirname = os.path.basename(
            os.path.normpath(self.rawscan_path))
        os.mkdir(os.path.join(self.tmpdir, self.rawscan_dirname))
        self.tmpdest = os.path.join(self.tmpdir, self.rawscan_dirname)
        copy_tree(self.rawscan_path, self.tmpdest)
        bz2_list = (z for z in sorted(os.listdir(
            self.tmpdest)) if z.endswith('.bz2'))
        for filename in bz2_list:
            filepath = os.path.join(self.tmpdest, filename)
            newfilepath = os.path.join(
                self.tmpdest, filename.replace(".bz2", ""))
            with open(newfilepath, 'wb') as new_file, open(filepath, 'rb') as file:
                decompressor = bz2.BZ2Decompressor()
                for data in iter(lambda: file.read(100 * 1024), b''):
                    new_file.write(decompressor.decompress(data))
        self.orig_path = self.rawscan_path
        self.rawscan_path = self.tmpdest
        self.rawscan_dirname = os.path.basename(
            os.path.normpath(self.rawscan_path))

    def organize_dcms(self):
        # --Full path to the directory containing the raw dcm files - PASS TO dcm_conv
        self.rawscan_path = ''

        self.rawscan_path = self.tmpdest
        # --Grabbing the sequence number from the name of the directory holding the raw dcms
        rawscan_seqno = int(self.rawscan_dirname.split('_')[0][1:])
        # --Grabbing the type of scan from the name of the directory holding the raw dcms
        self.rawscan_type = self.rawscan_dirname.split('_')[1]

        self.helpful_type = ''
        self.helpful_type = self.scan2helpful(self.rawscan_type)
        yamlfile = os.path.join(
            self.rawscan_path, self.rawscan_dirname + '.yaml')

        bids_runno = ''
        bids_tasklabel = ''

        with open(yamlfile, "r") as yfile:
            for line in yfile:
                if line.startswith("  SeriesDescription:"):
                    bids_acqlabel = line.split(': ')[1]
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
            with open(yamlfile, "r") as yfile2:
                for line in yfile2:
                    if line.startswith("  SeriesNumber: "):
                        bids_runno = line.split(': ')[1]
                        bids_runno = "_run-" + bids_runno
                        break

        # --Creating common fields
        # ----bids_scanecho
        bids_scanecho = '_echo-%e' if self.rawscan_type.__contains__(
            'fmap') else ''
        # ---bids_scansession: the wave of data collection formatted as a BIDS label string
        self.bids_scansession = "_ses-" + str(self.wave_no).zfill(2)
        self.bids_scansessiondir = "ses-" + str(self.wave_no).zfill(2)
        # ---bids_scanmode: the "modal" label for the scan per bids spec (e.g., anat, func, dwi)
        if self.rawscan_type.__contains__('fmap'):
            if bids_acqlabel.__contains__('EPI'):
                self.bids_scanmode = '_epirawfmap'
            elif bids_acqlabel.__contains__('DTI'):
                self.bids_scanmode = '_dtirawfmap'
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
        os.makedirs(self.dcm2niix_outdir, exist_ok=True)
        # print("Running command: dcm2niix" + " -f " + self.dcm2niix_label + " -o " + self.dcm2niix_outdir + " " + self.rawscan_path)
        subprocess.run(["dcm2niix", "-f", self.dcm2niix_label,
                        "-o", self.dcm2niix_outdir, self.rawscan_path])

    def make_fmap(self, scan_type):
        self.fmap_dir = os.path.join(
            self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'fmap')
        gen = (rawfmapfile for rawfmapfile in os.listdir(self.fmap_dir)
               if rawfmapfile.endswith('.nii') if rawfmapfile.__contains__(scan_type))

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
            print(fmap_intendedfor_path)
            fmap_intendedfor = ''
            for scan in os.listdir(fmap_intendedfor_path):
                if scan.endswith('.nii'):
                    print(scan)
                    fmap_intendedfor += '"' + self.bids_scansessiondir + '/func/' + scan + '",' + '\n'
            fmap_intendedfor = "[" + fmap_intendedfor[:-2] + "]"
            print(fmap_intendedfor)
            self.printu("\n" + "CREATING FIELD MAP FOR EPI SCANS:")
        elif scan_type.__contains__('dti'):
            wrappedphasefile = rawfmapfile_1.replace(
                '_dtirawfmap_e1', '_wrapped_phasediff')
            magoutfile1 = rawfmapfile_1.replace(
                '_dtirawfmap_e1', '_magnitude1')
            magoutfile2 = rawfmapfile_1.replace(
                '_dtirawfmap_e1', '_magnitude2')
            phasediffileRads = rawfmapfile_1.replace(
                '_dtirawfmap_e1', '_phasediff_rads')
            phasediffileHz = rawfmapfile_1.replace(
                '_dtirawfmap_e1', '_phasediff')
            # What scans does the field map go with?
            fmap_intendedfor_path = os.path.join(
                self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'func')
            print(fmap_intendedfor_path)
            fmap_intendedfor = ''
            for scan in os.listdir(fmap_intendedfor_path):
                if scan.endswith('.nii'):
                    fmap_intendedfor += '"' + self.bids_scansessiondir + '/func/' + scan + '",'
            fmap_intendedfor = "[" + fmap_intendedfor[:-2] + "]"
            self.printu("\n" + "CREATING FIELD MAP FOR DTI SCANS:")

        calc_computephase = "atan2((b*c-d*a),(a*c+b*d))"
        calc_extractmag = "a"
        te_diff = 3
        calc_rads2hz = "a*1000/" + str(te_diff)

        fmap_description = {
            "EchoTime1": 7,
            "EchoTime2": 10,
            "IntendedFor": fmap_intendedfor
        }

        # -Output the BIDS sidecar file describing this field map
        json_phasediffile = phasediffileHz.replace(".nii",".json")
        with open(json_phasediffile, 'w') as outfile:
            json.dump(str(fmap_description), outfile)

        self.printu(
            "\n" + "  Computing phase difference from raw fieldmap volume:")
        # -Computing the phase difference from the raw fieldmap volume
        subprocess.call(["3dcalc", "-a", rawfmapfile_1v2, "-b", rawfmapfile_1v3, "-c", rawfmapfile_2v2, "-d", rawfmapfile_2v3,
                         "-expr", calc_computephase, "-prefix", wrappedphasefile])

        self.printu("\n" + "  Computing magnitude image #1:")
        # -Extract magnitude image from first raw fieldmap volume
        subprocess.call(["3dcalc", "-a", rawfmapfile_1v0,
                         "-expr", calc_extractmag, "-prefix", magoutfile1])

        self.printu("\n" + "  Computing magnitude image #2:")
        # -Extract magnitude image from second raw fieldmap volume
        subprocess.call(["3dcalc", "-a", rawfmapfile_2v0,
                         "-expr", calc_extractmag, "-prefix", magoutfile2])

        self.printu("\n" + "  Unwrapping the phase difference using FSL's 'prelude':")
        # -Unwrap the phase difference file
        subprocess.call(["prelude", "-v", "-p", wrappedphasefile,
                         "-a", magoutfile1, "-o", phasediffileRads])
        phasediffileRads = phasediffileRads + '.gz'

        self.printu(
            "\n" + "  Converting the phase difference from radians to Hz:")
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

        for self.subjID_dirname in os.listdir(self.studypath):

            self.get_subj_dcms()
            print(
                "\n".join(['#'*23, "FOUND SUBJECT ID#: " + self.subjID, '#'*23]))
            gen = (fdir for fdir in sorted(
                self.dicomspath.iterdir()) if fdir.is_dir())
            for fdir in gen:
                if not any(x in str(fdir) for x in self.scanstoskip):
                    self.unpack_dcms(fdir)
                    self.organize_dcms()
                    self.printu("\n" + "FOUND A " + self.helpful_type +
                                " SCAN: " + self.orig_path + "\n")
                    self.printu(
                        "  Step 1: Decompressing the raw DICOM archive file..." + "\n")
                    self.printu(
                        "  Step 2: Extracting the relevant BIDS parameters..." + "\n")
                    self.printu(
                        "  Step 3: Converting to NIFTI using dcm2niix and sorting into appropriate BIDS folder..." + "\n")
                    self.conv_dcms()
            self.make_fmap('epi')
            self.make_fmap('dti')
            print("\n" + "#"*40 + "\n" + "CONVERSION AND PROCESSING FOR " +
                  self.subjID + " DONE!" + "\n" + "#"*40 + "\n")
        with open(os.path.join(self.outputpath, 'dataset_description.json'), 'w') as outfile:
            json.dump(self.data_description, outfile)


if __name__ == '__main__':

    bc = BidsConv()
    bc.main()
