import sys
import os
import subprocess
from pathlib import Path, PosixPath
import shutil
import glob
import fnmatch
from distutils.dir_util import copy_tree
from lib.Correction import dwicorrection as corr

# Copy necessary subject files\folders to a processing directory

procpath = Path('/Volumes/Vol6/YouthPTSD/dwiproc')
studypath = Path('/Volumes/Vol6/YouthPTSD/bids_master')
    # subjprocdir = Path(procpath, subjdir.parts[-1])
    # for sesdir in subjdir.iterdir():

sourcedir = Path('/Volumes/Vol6/YouthPTSD/bids_master/sub-001/ses-01')
procdir = Path('/Volumes/Vol6/YouthPTSD/dwiproc/sub-001/ses-01')
def makesubjprocdirs(sourcedir, procdir):
    procdir.mkdir(exist_ok=True, parents=True)
    # subjdirs = (subjdir for subjdir in sorted(studypath.glob('*/')) if subjdir.is_dir())
    # for subjdir in subjdirs:
    sourcedir = Path(sourcedir)
    procdir = Path(procdir)
    for file in Path(sourcedir, 'dwi').glob('*'):
        shutil.copy(file, procdir)
    for file in Path(sourcedir, 'fmap').glob('*FieldmapDTI_phasediff.nii'):
        shutil.copy(file, procdir)
    for file in Path(sourcedir, 'fmap').glob('*FieldmapDTI_magnitude1.nii'):
        shutil.copy(file, procdir)
    for file in Path(sourcedir, 'anat').glob('*.nii'):
        shutil.copy(file, procdir)
    
#makesubjprocdirs(sourcedir, procdir)  
inputdwi='/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-AxDTIASSET_dwi.nii'
fieldmap='/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-FieldmapDTI_phasediff.nii'
fieldmapmag='/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-FieldmapDTI_magnitude1.nii'
outputdwi='/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-FieldmapDTI_dwi_fmapcorr.nii'

def fieldmapcorrection(inputdwi, fieldmap, fieldmapmag, outputdwi):
    inputdwi = Path(inputdwi)
    fieldmap = Path(fieldmap)
    fieldmapmag = Path(fieldmapmag)
    outputdwi = Path(outputdwi)
    masked_fmapmag = fieldmapmag.parent / Path('mask.' + fieldmapmag.parts[-1])
    masked2pi_fmap = fieldmap.parent / Path('masked2pi' + fieldmap.parts[-1])
    tmpLPI_inputdwi = inputdwi.parent / Path('tmp.LPI.' + inputdwi.parts[-1])
    tmpLPImasked2pi_fmap = fieldmap.parent / Path('tmp.LPI.masked2pi.' + fieldmap.parts[-1])
    tmpLPI_outputdwi = outputdwi.parent / ('tmp.LPI.' + outputdwi.parts[-1])
    subprocess.run(['3dAutomask','-prefix', masked_fmapmag, fieldmapmag])
    subprocess.run(['3dcalc', '-datum', 'float', '-a', fieldmap, '-b', masked_fmapmag, '-expr', 'a*b*2*PI',
    '-prefix', masked2pi_fmap])
    getorient = subprocess.Popen(['3dinfo', '-orient', inputdwi], stdout=subprocess.PIPE)
    orient = getorient.stdout.read()
    subprocess.run(['3dresample', '-orient', 'LPI', '-inset', inputdwi, '-prefix', tmpLPI_inputdwi])
    subprocess.run(['3dresample', '-master', tmpLPI_inputdwi, '-inset', masked2pi_fmap, '-prefix', tmpLPImasked2pi_fmap])
    subprocess.run(['fugue', '-v','-i', tmpLPI_inputdwi, '--loadfmap='+ str(tmpLPImasked2pi_fmap), '--dwell=.000568', '-u', tmpLPI_outputdwi])
    subprocess.run(['3dresample', '-orient', orient, '-prefix', outputdwi, '-inset', tmpLPI_outputdwi])
    
fieldmapcorrection(inputdwi, fieldmap, fieldmapmag, outputdwi) 
        # orig_dwidir = pathlib.PosixPath(sesdir, 'dwi')
        # orig_anatdir = pathlib.PosixPath(sesdir, 'anat')
        # orig_fmapdir = pathlib.PosixPath(sesdir, 'fmap')
        # dwiproc_dir = pathlib.Path(procpath, subjdir.parts[-1], sesdir.parts[-1], 'dwiproc')
        # dwiproc_dir.mkdir(exist_ok=True, parents=True)
        # fmapproc_dir.mkdir(exist_ok=True)
        # for file in orig_dwidir.glob('*'):
        #     if file.suffix == ('.nii'):
        #         shutil.copy(file, fmapproc_dir)
        #         fname = pathlib.PurePath(file).name
        #         dwifile = pathlib.Path(fmapproc_dir, fname)
        #         print(dwifile)
            # elif file.suffix == ('.bval'):
            #     shutil.copy(file, dwiproc_dir)
            #     bvalfile = file
            # elif file.suffix == ('.bvec'):
            #     bvecfile = file
            # elif file.suffix == ('.json'):
            #     jsonfile = file
            # else:
            #     next
        # miffile = dwifile.stem + '.mif'
        # miffile = pathlib.PosixPath(proc_dir, miffile)
        # proc_dir.mkdir(exist_ok=True)
        # os.makedirs(proc_dir, exist_ok=True)
        # print("Creating MRTRIX .MIF file from volume, gradient, and JSON files...")
        # subprocess.call(['mrconvert', '-force', '-info', '-json_import', jsonfile, '-fslgrad', bvecfile, bvalfile, dwifile, miffile])

#         for file in orig_anatdir.glob('*.nii'):
#             anatfile = file
#             print("Copying anatomical volume:",anatfile,">>>>",proc_dir)
#             shutil.copy(anatfile, proc_dir)
        
#         for file in orig_fmapdir.glob('*FieldmapDTI_phasediff.nii'):
#             fmapfile = file
#             print("Copying fieldmap volume:",fmapfile,">>>>",proc_dir)
#             shutil.copy(fmapfile, proc_dir)
        
#         return(dwifile, anatfile, fmapfile)

# subjdir = pathlib.PosixPath(studypath, 'sub-001')
# # sesdir = pathlib.PosixPath(subjdir, 'ses-01')
# # # subjdirs = (subjdir for subjdir in sorted(studypath.glob('*/')) if subjdir.is_dir())
# # # for subjdir in subjdirs:
# # #     for sesdir in subjdir.iterdir():

# # miffile, anatfile, fmapfile = makesubjprocdirs(subjdir, procpath)
# # # miffile_den = str(miffile).replace("_dwi","_dwi_den")
# # corr.denoise(miffile, miffile_den )
# # miffile_den_deg = str(miffile_den).replace("_den", "_den_deg")
# # corr.degibbs(miffile_den, miffile_den_deg)
# makesubjprocdirs(subjdir, procpath)