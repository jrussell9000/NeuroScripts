import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile

import pydicom

from lib.Utils import tools


class tgz2NIFTI():
    # Copy a TGZ dicom archive file ('input_tgz') to /tmp/tmpXXXX, unpack it, and copy the output to 'outputdir'
    # Assumes that the TGZ file is located within XXXX_Y1/dicoms where XXXX is the subject ID and Y is the wave number
    def __init__(self, input_tgz_filepath, outputpath):
        self.input_tgz_filepath = input_tgz_filepath
        self.outputpath = outputpath
        self.unpack_tgz()
        self.getbidsparams()
        self.conv_dcms()
        self.cleanup()

    def unpack_tgz(self):
        tgz_fpath = pathlib.PurePath(self.input_tgz_filepath)
        tgz_fname = tgz_fpath.name
        fullid = str(tgz_fpath.parts[-3])
        self.timept = fullid.split('_')[1].replace('C', '')
        self.subjid = fullid.split('_')[0]
        self.tmpdir = tempfile.mkdtemp(dir='/tmp')
        shutil.copy(tgz_fpath, self.tmpdir)
        tgz_file_tmp = pathlib.PurePath(self.tmpdir, tgz_fname)
        tgz_file_open = tarfile.open(tgz_file_tmp, 'r:gz')
        print("\n","Decompressing DICOM archive file", tgz_fname, "...")
        tgz_file_open.extractall(path=self.tmpdir)
        tgz_dcm_dirname = os.path.commonprefix(tgz_file_open.getnames())
        self.tgz_dcm_dirpath = pathlib.PurePath(self.tmpdir, tgz_dcm_dirname)

    def getbidsparams(self):
        raw_scandirname = str(self.tgz_dcm_dirpath.parts[-1])
        raw_scantype = raw_scandirname.split('.')[1]
        raw_seqno = int(raw_scandirname.split('.')[0][1:])
        raw_timept = int(self.timept)
        dcm = pydicom.dcmread(os.path.join(self.tgz_dcm_dirpath, 'i.000001.dcm'))
        bids_acqlabel = str(dcm.SeriesDescription)
        for c in ['(', ')', '-', '_', ' ', '/', 'EPI', 'FieldMap:', ':']:
            if c in bids_acqlabel:
                bids_acqlabel = bids_acqlabel.replace(c, '')
        bids_acqlabel = "acq-" + bids_acqlabel
        if raw_scantype.__contains__('EPI'):
            bids_tasklabel = bids_acqlabel.replace("acq-", "task-").replace("EPI", "")
            bids_acqlabel = ""
            # Count the number of similarly named scans in the dicom directory. If that count is greater than one,
            # start a counter variable that will increase by one for each scan we run through.
            raw_runcount = 0
            for scandir in os.listdir(self.tmpdir):
                if scandir.__contains__(raw_scantype):
                    raw_runcount = raw_runcount + 1
                    # try:
                    #     raw_runcount = raw_runcount + 1
                    # except NameError:
                    #     raw_runcount = 1
            if raw_runcount > 1:
                try:
                    self.epi_runcount = self.epi_runcount + 1
                except AttributeError:
                    self.epi_runcount = 1
            bids_runno = "run-" + str(self.epi_runcount)
        else:
            bids_tasklabel = ''
            bids_runno = ''
        if raw_scantype.__contains__('NODDI'):
            if raw_scantype.__contains__('pepolar0'):
                bids_pedir = "dir-PA"
            elif raw_scantype.__contains__('pepolar1'):
                bids_pedir = "dir-AP"
        else:
            bids_pedir = ""
        bids_participantID = "sub-" + self.subjid
        bids_scansession = "ses-" + self.timept
        bids_scanmode = tools.scan2bidsmode(raw_scantype)
        tools.printu("BIDS PARAMETERS")
        print("Participant:", bids_participantID)
        print("Wave:", bids_scansession)
        if len(bids_acqlabel) > 0:
            print("ACQ Label:", bids_acqlabel.replace("acq-",""))
        print("Modality Label:", bids_scanmode)
        if len(bids_tasklabel) > 0:
            print("Task Label:", bids_tasklabel.replace("task-",""))
        if len(bids_runno) > 0:
            print("Run #:",bids_runno.replace("run-",""))
        if len(bids_pedir) > 0:
            print("Phase Encoding Label:", bids_pedir)
        dlist = [bids_participantID]
        dlist.append(bids_scansession)
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
        self.bids_outdir = pathlib.Path(self.outputpath, bids_participantID, bids_scansession, tools.scan2bidsdir(raw_scandirname))

    def conv_dcms(self):
        os.makedirs(self.bids_outdir, exist_ok=True)
        subprocess.run(["dcm2niix", "-f", self.dcm2niix_label,
                        "-o", self.bids_outdir, self.tgz_dcm_dirpath])
        # Fix json bids file for fieldmaps here.

    def cleanup(self):
        shutil.rmtree(self.tmpdir)

class bz2NIFTI():

    def __init__(self, input_bz2_scandir, outputpath):
        self.input_bz2_scandir = input_bz2_scandir
        self.outputpath = outputpath
        self.unpack_bz2()

    def unpack_bz2(self):
        bz2_dpath = pathlib.PurePath(self.input_bz2_scandir)
        bz2_dname = bz2_dpath.parts[-1]
        fullid = str(bz2_dpath.parts[-2]).replace('_','')
        print(fullid)
