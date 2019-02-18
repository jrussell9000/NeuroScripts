import bz2
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile

import pydicom

from lib.Converters import makefmaps
from lib.Utils import tools


class tgz2NIFTI():
    # Copy a TGZ dicom archive file ('input_tgz') to /tmp/tmpXXXX, unpack it, and copy the output to 'outputdir'
    # Assumes that the TGZ file is located within XXXX_Y1/dicoms where XXXX is the subject ID and Y is the wave number
    # def __init__(self, input_tgz_filepath, outputpath):
    #     self.input_tgz_filepath = input_tgz_filepath
    #     self.outputpath = outputpath
    #     self.unpack_tgz()
    #     self.getbidsparams()
    #     self.conv_dcms()
    #     self.cleanup()

    def __init__(self, studypath, outputpath, scanstoskip, inputidfile):
        self.studypath = pathlib.PosixPath(studypath)
        self.outputpath = pathlib.PosixPath(outputpath)
        if inputidfile == None:
            subjdirs = sorted(self.studypath.iterdir())
        else:
            with open(inputidfile, 'r') as idfile:
                sids = idfile.readlines()
                sids = [s.strip('\n') for s in sids]
                subjdirs = (subjdir for subjdir in sorted(self.studypath.iterdir()) if any(x in str(subjdir) for x in sids))
        for subjdir in subjdirs:
            print("\n" + "*"*35 + "\n" + "STARTING PARTICIPANT: " + subjdir.parts[-1] + "\n" + "*"*35)
            dcm_path = pathlib.PosixPath(subjdir, "dicoms")
            for fname in sorted(dcm_path.glob('*.tgz')):
                if not any(x in fname.name for x in scanstoskip):
                    self.unpack_tgz()
                    self.getbidsparams()
                    self.conv_dcms()
                    self.cleanup()

    def unpack_tgz(self):
        tgz_fpath = pathlib.PosixPath(self.input_tgz_filepath)
        tgz_fname = tgz_fpath.name
        fullid = str(tgz_fpath.parts[-3])
        if fullid[-2] == 'C':
            self.timept = fullid[-1]
            self.subjid = fullid.split('_')[0]
        elif fullid.__contains__('rescan'):
            self.timept = 2
            self.subjid = fullid[1:4]
        else:
            self.timept = 2
            self.subjid = fullid[1:4]
        self.tmpdir = pathlib.PosixPath(tempfile.mkdtemp(dir='/tmp'))
        shutil.copy(tgz_fpath, self.tmpdir)
        tgz_file_tmp = pathlib.PosixPath(self.tmpdir, tgz_fname)
        tgz_file_open = tarfile.open(tgz_file_tmp, 'r:gz')
        print("\n" + "STARTING SCAN: " + tgz_fname + "\n")
        print(tools.stru("Decompressing DICOM archive file") + "..." + "\n")
        tgz_file_open.extractall(path=self.tmpdir)
        tgz_dcm_dirname = os.path.commonprefix(tgz_file_open.getnames())
        self.tgz_dcm_dirpath = pathlib.PosixPath(self.tmpdir, tgz_dcm_dirname)

    def getbidsparams(self):
        raw_scandirname = str(self.tgz_dcm_dirpath.parts[-1])
        self.raw_scantype = raw_scandirname.split('.')[1]
        raw_seqno = int(raw_scandirname.split('.')[0][1:])
        raw_timept = int(self.timept)
        dcm = pydicom.dcmread(os.path.join(self.tgz_dcm_dirpath, 'i.000001.dcm'))
        self.dcmseriesdesc = str(dcm.SeriesDescription)
        bids_acqlabel = str(dcm.SeriesDescription)
        for c in ['(', ')', '-', '_', ' ', '/', 'FieldMap:', ':']:
            if c in bids_acqlabel:
                bids_acqlabel = bids_acqlabel.replace(c, '')
        bids_acqlabel = "acq-" + bids_acqlabel
        if self.raw_scantype.__contains__('EPI_'):
            bids_tasklabel = bids_acqlabel.replace("acq-", "task-")
            bids_acqlabel = ""
            # Count the number of similarly named scans in the dicom directory. If that count is greater than one,
            # start a counter variable that will increase by one for each scan we run through.
            raw_runcount = 0
            bids_runno = ''
            scandirs = (scandir for scandir in self.tmpdir.iterdir() if scandir.is_dir())
            for scandir in scandirs:
                if str(scandir).__contains__(self.raw_scantype):
                    raw_runcount = raw_runcount + 1
            if raw_runcount > 1:
                print("FOUND MULTIPLE RUNS!")
                try:
                    self.epi_runcount = self.epi_runcount + 1
                except AttributeError:
                    self.epi_runcount = 1
                bids_runno = "run-" + str(self.epi_runcount)
        else:
            bids_tasklabel = ''
            bids_runno = ''
        # if self.raw_scantype.__contains__('AxT2FLAIR'):
        #     bids_acqlabel = bids_acqlabel.replace('COPYDTI', '').replace('AxT2', '')
        if self.raw_scantype.__contains__('NODDI'):
            if self.raw_scantype.__contains__('pepolar0'):
                bids_pedir = "dir-PA"
            elif self.raw_scantype.__contains__('pepolar1'):
                bids_pedir = "dir-AP"
        else:
            bids_pedir = ""
        self.bids_participantID = "sub-" + self.subjid
        self.bids_scansession = "ses-" + str(self.timept).zfill(2)
        bids_scanmode = tools.scan2bidsmode(self.raw_scantype)
        print(tools.stru("Parsing BIDS parameters") + "...")
        print("Participant:", self.bids_participantID)
        print("Wave:", self.bids_scansession)
        if len(bids_acqlabel) > 0:
            print("ACQ Label:", bids_acqlabel.replace("acq-",""))
        print("Modality Label:", bids_scanmode)
        if len(bids_tasklabel) > 0:
            print("Task Label:", bids_tasklabel.replace("task-",""))
        if len(bids_runno) > 0:
            print("Run #:",bids_runno.replace("run-",""))
        if len(bids_pedir) > 0:
            print("Phase Encoding Label:", bids_pedir)
        dlist = [self.bids_participantID]
        dlist.append(self.bids_scansession)
        if len(bids_tasklabel) > 0:
            dlist.append(bids_tasklabel)
        if len(bids_acqlabel) > 0:
            dlist.append(bids_acqlabel)
        if len(bids_runno) > 0:
            dlist.append(bids_runno)
        if len(bids_pedir) > 0:
            dlist.append(bids_pedir)
        dlist.append(bids_scanmode)

        self.dcm2niix_label = "_".join(dlist)
        #self.dcm2niix_label = bids_participantID + bids_tasklabel + bids_acqlabel + \
           # bids_runno + bids_pedir + bids_scanmode
        self.bids_outdir = pathlib.Path(self.outputpath, self.bids_participantID, self.bids_scansession, tools.scan2bidsdir(raw_scandirname))

    def conv_dcms(self):
        os.makedirs(self.bids_outdir, exist_ok=True)
        print("\n" + tools.stru("Beginning scan conversion") + "...")
        subprocess.run(["dcm2niix", "-f", self.dcm2niix_label,
                        "-o", self.bids_outdir, self.tgz_dcm_dirpath])
        # If the scan is an fmri ('EPI'), append the taskname to the BIDS sidecar file
        if self.raw_scantype.__contains__('EPI_'):
            jsonfilepath = pathlib.PosixPath(self.bids_outdir, self.dcm2niix_label + '.json')
            with open(jsonfilepath) as jsonfile:
                sidecar = json.load(jsonfile)
            sidecar['TaskName'] = self.raw_scantype
            with open(jsonfilepath, 'w') as f:
                json.dump(sidecar, f)
        print("-"*35)
 
    def getfmapinfo(input_subjdir):
        subjdir = pathlib.PosixPath(input_subjdir)
        fullid = subjdir.parts[-1]
        if fullid[-2] == 'C':
            timept = fullid[-1]
            subjid = fullid.split('_')[0]
        elif fullid.__contains__('rescan'):
            timept = 2
            subjid = fullid[1:4]
        else:
            timept = 2
            subjid = fullid[1:4]
        bids_participantID = "sub-" + subjid
        bids_scansession = "ses-" + str(timept).zfill(2)
        return bids_participantID, bids_scansession

    def cleanup(self):
        shutil.rmtree(self.tmpdir)


class bz2NIFTI():

    def __init__(self, input_bz2_scandir, outputpath):
        self.input_bz2_scandir = input_bz2_scandir
        self.outputpath = outputpath
        self.unpack_bz2()

    def unpack_bz2(self):
        bz2_dpath = pathlib.PurePath(self.input_bz2_scandir)
        print(bz2_dpath)
        bz2_dname = bz2_dpath.parts[-1]
        print(bz2_dname)
        fullid = str(bz2_dpath.parts[-3]).replace('_','')
        print(fullid)
        tmpdir = tempfile.mkdtemp(dir='/tmp', suffix=fullid)
        if fullid.__contains__('rescan'):
            self.subjid = fullid.replace('rescan','')
            timept = 2
        else:
            timept = 1
            self.subjid = fullid
        shutil.copytree(bz2_dpath, tmpdir)
        bz2_dir_tmp = pathlib.PurePath(tmpdir, bz2_dname)
        for bz2_file in sorted(bz2_dir_tmp.glob('*.bz2')):
            bz2_fpath = pathlib.PurePath(bz2_dir_tmp, bz2_file)
            dcm_fpath = pathlib.PurePath(bz2_dir_tmp, bz2_file.replace('.bz2',''))
            with open(dcm_fpath, 'wb') as newfile, open(bz2_fpath, 'rb') as oldfile:
                decompressor = bz2.BZ2Decompressor()
                for data in iter(lambda: oldfile.read(100 * 1024), b''):
                    newfile.write(decompressor.decompress(data))
        self.raw_scanpath = bz2_dir_tmp
