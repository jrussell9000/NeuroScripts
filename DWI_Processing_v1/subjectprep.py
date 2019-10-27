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
studypath = Path('/Volumes/Vol6/YouthPTSD/BIDS_master')
    # subjprocdir = Path(procpath, subjdir.parts[-1])
    # for sesdir in subjdir.iterdir():

sourcedir = Path('/Volumes/Vol6/YouthPTSD/BIDS_master/sub-001/ses-01')
procdir = Path('/Volumes/Vol6/YouthPTSD/dwiproc/sub-001/ses-01')

tmpdir = Path('/tmp')
def makesubjprocdirs(sourcedir, procdir):
    if procdir.exists():
        shutil.rmtree(procdir)
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
      
origdwi=Path('/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-AxDTIASSET_dwi.nii')
bvecfile=Path('/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-AxDTIASSET_dwi.bvec')
bvalfile=Path('/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-AxDTIASSET_dwi.bval')
jsonfile=Path('/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-AxDTIASSET_dwi.json')
fieldmap=Path('/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-FieldmapDTI_phasediff.nii')
fieldmapmag=Path('/Users/jdrussell3/youthptsd/dwiproc/sub-001/ses-01/sub-001_ses-01_acq-FieldmapDTI_magnitude1.nii')

origdwi_mif=origdwi.parent / Path(origdwi.parts[-1].replace('.nii','.mif'))
fmapcorr_nii_dwi=origdwi.parent / Path('fmapcorr.' + origdwi.parts[-1] + '.gz')
fmapcorr_mif_dwi=origdwi.parent / Path(origdwi.parts[-1].replace('.nii','.mif'))
denoise_dwi=origdwi.parent / Path('den.' + origdwi.parts[-1])
degibbs_dwi=origdwi.parent / Path('deg.' + origdwi.parts[-1])
preproc_dwi=origdwi.parent / Path('preproc.' + origdwi.parts[-1])
b0brain=origdwi.parent / Path('b0brain.nii.gz')
b0brain_mask=origdwi.parent / Path('b0brain_mask.nii.gz')
meanb0=origdwi.parent / Path('meanb0.nii.gz')
allb0s=origdwi.parent / Path('allb0s.nii.gz')
qa_dwi=origdwi.parent / Path('QA')
acqparams=origdwi.parent / Path('acqparams.txt')
index=origdwi.parent / Path('index.txt')
# qa_dwi.mkdir()

# Note! This is unnecessary - the PRELUDE created fieldmap (in HZ) is read into eddy
def fieldmapcorrection(inputdwi, fieldmap, fieldmapmag, fmapcorr_nii_dwi):
    inputdwi = Path(inputdwi)
    fieldmap = Path(fieldmap)
    fieldmapmag = Path(fieldmapmag)
    fmapcorr_nii_dwi = Path(fmapcorr_nii_dwi)
    masked_fmapmag = fieldmapmag.parent / Path('mask.' + fieldmapmag.parts[-1])
    masked2pi_fmap = fieldmap.parent / Path('masked2pi.' + fieldmap.parts[-1])
    tmpLPI_inputdwi = inputdwi.parent / Path('tmp.LPI.' + inputdwi.parts[-1])
    tmpLPImasked2pi_fmap = fieldmap.parent / Path('tmp.LPI.masked2pi.' + fieldmap.parts[-1])
    tmpLPI_fmapcorr_dwi = fmapcorr_nii_dwi.parent / ('tmp.LPI.' + fmapcorr_nii_dwi.parts[-1])
    subprocess.run(['3dAutomask','-prefix', masked_fmapmag, fieldmapmag])
    subprocess.run(['3dcalc', '-datum', 'float', '-a', fieldmap, '-b', masked_fmapmag, '-expr', 'a*b*2*PI',
    '-prefix', masked2pi_fmap])
    getorient = subprocess.Popen(['3dinfo', '-orient', inputdwi], stdout=subprocess.PIPE)
    orient = getorient.stdout.read()
    #Change the orientation of the fieldmap to LPI
    subprocess.run(['3dresample', '-orient', 'LPI', '-inset', inputdwi, '-prefix', tmpLPI_inputdwi])
    subprocess.run(['3dresample', '-master', tmpLPI_inputdwi, '-inset', masked2pi_fmap, '-prefix', tmpLPImasked2pi_fmap])
    #DWELL TIME = EffectiveEchoSpacing!!! per https://www.fmrib.ox.ac.uk/primers/intro_primer/ExBox19/IntroBox19.html
    subprocess.run(['fugue', '-v','-i', tmpLPI_inputdwi, '--loadfmap='+ str(tmpLPImasked2pi_fmap), '--dwell=.000568', '-u', tmpLPI_fmapcorr_dwi])
    subprocess.run(['3dresample', '-orient', orient, '-prefix', fmapcorr_nii_dwi, '-inset', tmpLPI_fmapcorr_dwi])
    #subprocess.run(['fugue', '-v','-i', inputdwi, '--loadfmap='+ str(masked2pi_fmap), '--dwell=.000568', '-u', fmapcorr_nii_dwi])
    #subprocess.run(['3dresample', '-orient', orient, '-prefix', fmapcorr_nii_dwi, '-inset', tmpLPI_fmapcorr_dwi])

def prepexternalfieldmap(inputdwi, fieldmap, t2anat, dwelltime):
    inputdwi = Path(inputdwi)
    fieldmap = Path(fieldmap)
    t2anat = Path(t2anat)

    t2anat_masked = str(t2anat).replace('.nii', '.masked.nii')
    subprocess.run(['bet', t2anat, t2anat_masked])

    fieldmap_rads = str(fieldmap).replace('.nii', '.rads.nii')
    subprocess.run(['fslmaths', fieldmap, '-mul', '6.28', '-mas', t2anat_masked ])

def mrconvert(inputdwi):
    inputdwi = Path(inputdwi)
    subprocess.run(['mrconvert', '-json_import', jsonfile, '-fslgrad', bvecfile, bvalfile, origdwi, origdwi_mif])

def denoise(inputdwi):
    inputdwi = Path(inputdwi)
    #outputdwi = origdwi.parent / Path('den.' + origdwi.parts[-1])
    subprocess.run(['dwidenoise', '-force', inputdwi, denoise_dwi])

def degibbs(inputdwi):
    inputdwi = Path(inputdwi)
    #outputdwi= origdwi.parent / Path('deg.' + origdwi.parts[-1])
    subprocess.run(['mrdegibbs', '-force', inputdwi, degibbs_dwi])

def dwipreproc(inputdwi):
    inputdwi = Path(inputdwi)
    eddyoptions="--slm=linear --residuals"
    subprocess.run(['dwipreproc', inputdwi, preproc_dwi, '-debug', '-tempdir', tmpdir, '-json', jsonfile, '-fslgrad', bvecfile, bvalfile, '-rpe_none', '-pe_dir', 'PA', '-eddyqc_all', qa_dwi, '-eddy_options', eddyoptions])
    # foreach * : dwipreproc IN/dwi_den_deg.mif IN/dwi_den_deg_pp.mif -rpe_none -pe_dir PA -eddy_options " --slm=linear"

def eddyprep(inputdwi):
    inputdwi = Path(inputdwi)
    subprocess.run(['fslroi', inputdwi, allb0s, '0', '7'])
    subprocess.run(['fslmaths', allb0s, '-Tmean', meanb0]) 
    subprocess.run(['bet', meanb0, 'b0brain', '-m'])
    #acqparams file is 0 1 0 0.14484 for youthptsd
    with open(acqparams, 'w') as acqfile:
        acqfile.write("0 1 0 0.14484")
    with open(index, 'w') as indexfile:
        getnvols = subprocess.Popen(['fslval', inputdwi, 'dim4'], stdout=subprocess.PIPE)
        nvols = getnvols.stdout.read()
        for i in range(int(nvols)):
            indexfile.write("1 ")

def eddy(inputdwi, inputfmap):
    inputdwi = Path(inputdwi)
    inputfmap = Path(inputfmap)
    proc = subprocess.run(['eddy_openmp', '--imain='+str(inputdwi), '--mask='+str(b0brain_mask), '--acqp='+str(acqparams), '--index='+str(index), '--bvecs='+str(bvecfile),
    '--bvals='+str(bvalfile), '--field='+str(inputfmap).replace('.nii',''), '--out='+str(preproc_dwi)])  
    print("{}".format(proc.args))

# makesubjprocdirs(sourcedir, procdir)
# # fieldmapcorrection(origdwi, fieldmap, fieldmapmag, fmapcorr_nii_dwi) 
# mrconvert(origdwi)
# denoise(origdwi_mif)
# degibbs(denoise_dwi)
# eddyprep(degibbs_dwi)
eddy(degibbs_dwi, fieldmap)

#dwipreproc(degibbs_dwi)



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
        # subprocess.run(['mrconvert', '-force', '-info', '-json_import', jsonfile, '-fslgrad', bvecfile, bvalfile, dwifile, miffile])

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