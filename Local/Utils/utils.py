import pathlib
import shutil
import tempfile
import tarfile
import os
import pydicom
# UTILITY FUNCTIONS #

# Underline strings
def stru(string):
    start = '\033[4m'
    end = '\033[0m'
    ustr = start + string + end
    return(ustr)


# Underline all strings in a print command
def printu(string):
    start = '\033[4m'
    end = '\033[0m'
    ustr = start + string + end
    print(ustr)

# Copy a TGZ dicom archive file ('input_tgz') to /tmp/tmpXXXX, unpack it, and copy the output to 'outputdir'
# Assumes that the TGZ file is located within XXXX_Y1/dicoms where XXXX is the subject ID and Y is the wave number
def unpack_tgz(input_tgz_filepath):
	tgz_fpath = pathlib.PurePath(input_tgz_filepath)
	tgz_fname = tgz_fpath.name
	fullid = tgz_fpath.parents[1]
	timept = fullid.split('_')[0].replace('C','')
	subjid = fullid.split('_')[1]
	tmpdir = tempfile.mkdtemp(dir='/tmp')
	shutil.copy(tgz_fpath, tmpdir)
	tgz_file_tmp = pathlib.PurePath(tmpdir,tgz_fname)
	tgz_file_open = tarfile.open(tgz_file_tmp, 'r:gz')
	print("Decompressing DICOM archive file", tgz_fname, "...")
	tgz_file_open.extractall(path=tmpdir)
	tgz_dcm_dirname = os.path.commonprefix(tgz_file_open.getnames())
	tgz_dcm_dirpath = pathlib.PurePath(tmpdir, tgz_dcm_dirname)
  	return(subjid, timept, tgz_dcm_dirpath)

def scan2bidsmode(modstring):
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

def scan2bidsdir(typestring):
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

def getbidsparams(inputdcmdir, subjid, timept):
	raw_scandirname = inputdcmdir.parents[0]
	raw_scantype = inputdcmdir.split('.')[1]
	raw_seqno = int(inputdcmdir.split('.')[0][1:])
	raw_timept = int(timept)

	dcm = pydicom.dcmread(pathlib.Path(inputdcmdir, 'i.000001.dcm'))
	bids_acqlabel = dcm.SeriesDescription
	for 
	bids_participantid = "sub-" + subjid
	bids_scansession = "ses-" + timept
	bids_scanmode = scan2bidsmode(raw_scantype)
	bids_scanecho
	



