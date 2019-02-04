import sys
import os
import subprocess
import pathlib
import shutil
import glob
import fnmatch
from distutils.dir_util import copy_tree
from lib.Correction import dwicorrection


# Copy necessary subject files\folders to a processing directory

procpath = pathlib.Path('/Volumes/Vol6/YouthPTSD/dwiproc')
studypath = pathlib.Path('/Volumes/Vol6/YouthPTSD/bids_master')
subjdirs = (subjdir for subjdir in sorted(studypath.glob('*/')) if subjdir.is_dir())

subjdir = pathlib.PosixPath(studypath, 'sub-001')
for sesdir in subjdir.iterdir():
	orig_dwidir = pathlib.PosixPath(sesdir, 'dwi')
	orig_anatdir = pathlib.PosixPath(sesdir, 'anat')
	orig_fmapdir = pathlib.PosixPath(sesdir, 'fmap')
	proc_dir = pathlib.PosixPath(procpath, subjdir.parts[-1], sesdir.parts[-1], 'dwiproc')
	for file in orig_dwidir.glob('*'):
		if file.suffix == ('.nii'):
			dwifile = file
			print(dwifile)
		elif file.suffix == ('.bval'):
			bvalfile = file
			print(bvalfile)
		elif file.suffix == ('.bvec'):
			bvecfile = file
			print(bvecfile)
		elif file.suffix == ('.json'):
			jsonfile = file
			print(jsonfile)
		else:
			next
	miffile = str(dwifile.stem) + '.mif'
	miffile = os.path.join(proc_dir, miffile)
	os.makedirs(proc_dir, exist_ok=True)
	subprocess.call(['mrconvert', '-force', '-json_import', jsonfile, '-fslgrad', bvecfile, bvalfile, dwifile, str(miffile)])
	for file in orig_anatdir.glob('*.nii'):
		print(file)
		shutil.copy(file, proc_dir)
	
	for file in orig_fmapdir.glob('*FieldmapDTI_phasediff.nii'):
		print(file)
		shutil.copy(file, proc_dir)
	
