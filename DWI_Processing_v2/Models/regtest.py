from pathlib import Path
import shutil, os, subprocess, time
from subprocess import run, Popen
from joblib import parallel_backend, delayed, Parallel
from random import randint

xtractproc_dir = Path('/Volumes/Vol6/YouthPTSD/xtract')
BIDSproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed')

xtractsubj_dir = xtractproc_dir / 'sub-084_ses-01'
bedpostxsubj_dir = xtractproc_dir / 'sub-084_ses-01.bedpostX'
dwinii = xtractsubj_dir / 'data.nii'

# #Creating files for registration
# b0 = xtractsubj_dir / ("b0.nii")
# subprocess.run(['fslroi', dwinii, b0, '0', '7'])
# mnb0 = xtractsubj_dir / ("meanb0.nii")
# subprocess.run(['fslmaths', b0, '-Tmean', mnb0])
nodif_brain = xtractsubj_dir / ("nodif_brain.nii")
# subprocess.run(['bet2', mnb0, nodif_brain, '-f', '0.3', '-v'])
T1 = xtractsubj_dir / "sub-084_ses-01_acq-AXFSPGRBRAVONEW_T1w.nii"
T1brain = xtractsubj_dir / "sub-084_ses-01_acq-AXFSPGRBRAVONEW_T1w_brain.nii"
# subprocess.run(['bet2', T1, T1brain, '-f', '0.3', '-v'])

#Creating transforms
os.chdir(bedpostxsubj_dir / "xfms")
diff2struct = bedpostxsubj_dir / 'xfms' / 'diff2struct.mat'
subprocess.run(['flirt', '-v', '-in', nodif_brain, '-ref', T1brain, '-omat', diff2struct, '-dof', '6', '-cost', 'mutualinfo'])
struct2diff = bedpostxsubj_dir / 'xfms' / 'struct2diff.mat'
print("Struct2diff path is: " + str(struct2diff))
subprocess.run(['convert_xfm', '-omat', struct2diff, '-inverse', diff2struct])
struct2standard = bedpostxsubj_dir / "xfms" / "struct2standard.mat"
print("\nStarting struct2standard...\n")
subprocess.run(['flirt', '-v', '-in', T1brain, '-ref', '/Volumes/apps/linux/fsl-current/data/standard/avg152T1_brain.nii.gz', '-omat', struct2standard, '-dof', '12', '-cost', 'corratio'])
standard2struct = bedpostxsubj_dir / 'xfms' / 'standard2struct.mat'
print("\nStarting standard2struct...\n")
subprocess.run(['convert_xfm', '-omat', standard2struct, '-inverse', struct2standard])
diff2standard = bedpostxsubj_dir / 'xfms' / 'diff2standard.mat'
print("\nStarting diff2standard...\n")
subprocess.run(['convert_xfm', '-omat', diff2standard, '-concat', struct2standard, diff2struct])
standard2diff = bedpostxsubj_dir / 'xfms' / 'standard2diff.mat'
subprocess.run(['convert_xfm', '-omat', standard2diff, '-inverse', diff2standard])

def execute(cmd, verbose=True, skipif=False):
    if skipif:
        return "Skipping..."
    try:
        print(cmd, flush=True)
        p = Popen(cmd, shell=True, stderr=PIPE, stdout=PIPE)
        log = []
        while True:
            line = p.stdout.readline().decode('utf-8').strip('\n')
            if not line:
                break
            log += [line]
            if verbose:
                print(line, flush=True)
        sout, serr = [tmp.decode('utf-8') for tmp in p.communicate()]
        if serr is not '':
            raise Exception(serr)
    except Exception as e:
        raise(e)
        # Leaving as a blanket raise for now so I can add specific
        # exceptions as they pop up...
    else:
        return log

def convert_xfm(inp=None, omat=None, inverse=None, concat=None):
    # convert_xfm(concat=t12mnixfm, inp=dwi2t1xfm, omat=totalxfm)
    # convert_xfm(inverse=totalxfm, inverse=reversexfm)
    if inverse:
        return ("convert_xfm "
                "-inverse {0} "
                "-omat {1}"
                "".format(inverse, omat))
    elif concat:
        return ("convert_xfm "
                "-concat {0} "
                "-omat {1} "
                "{2}"
                "".format(concat, omat, inp))