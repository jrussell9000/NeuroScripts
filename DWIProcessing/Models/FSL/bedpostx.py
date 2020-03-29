import os
import shutil
import subprocess
import time
from joblib import parallel_backend, delayed, Parallel
from pathlib import Path
from random import randint

xtractproc_dir = Path("/scratch/jdrussell3/fsl/cross_sec/xtract")
BIDSproc_dir = Path("/Volumes/Vol6/YouthPTSD/BIDS_Processed")

os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'


ses_dirs_str = (str(ses_dir) for ses_dir in sorted(BIDSproc_dir.glob('*/ses-01')) if Path(ses_dir / 'dwi').exists())
ses_list = list(ses_dirs_str)

def run_bedpostx(ses_dir):
    if not xtractproc_dir.exists():
        xtractproc_dir.mkdir()
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    xtractsubj_dir = xtractproc_dir / subjroot
    if xtractsubj_dir.exists():
        shutil.rmtree(xtractsubj_dir)
    xtractsubj_dir.mkdir()

    T1orig = ses_dir / 'anat' / (subjroot + "_acq-AXFSPGRBRAVONEW_T1w.nii")
    T1 = xtractsubj_dir / (subjroot + "_T1w.nii")
    T1brain = xtractsubj_dir / (subjroot + "_T1w_brain.nii")
    shutil.copy(T1orig, T1)
    subprocess.run(['bet2', T1, T1brain, '-f', '0.3', '-v'])

    orig_dwi_mif = preproc_dir / (subjroot + "_ppd.mif")
    orig_mask_mif = preproc_dir / (subjroot + "_mask_ppd.mif")
    orig_bvals = proc_dir / (subjroot + "_ppd.bval")
    orig_bvecs = proc_dir / (subjroot + "_ppd.bvec")

    input_dwi = xtractsubj_dir / ("data.nii")
    input_mask = xtractsubj_dir / "nodif_brain_mask.nii"
    input_bvals = xtractsubj_dir / 'bvals'
    input_bvecs = xtractsubj_dir / 'bvecs'

    # Copying files to run bedpostx
    subprocess.run(['mrconvert', '-force', orig_dwi_mif, input_dwi])
    subprocess.run(['mrconvert', '-force', orig_mask_mif, input_mask])
    shutil.copy2(orig_bvals, input_bvals)
    shutil.copy2(orig_bvecs, input_bvecs)

    newenv = os.environ.copy()

    for i in range(len(ses_list)):
        if subjpath in ses_list[i]:
            if i % 2 == 0:  # even
                newenv["CUDA_VISIBLE_DEVICES"] = "0"
                log.write("#----Now Starting Eddy Current Correction on GPU 0----#\n\n")
                log.flush()
                # For alternate even scans, wait two minutes before loading the scan into the GPU
                if i == 2 or i % 3 == 1:
                    time.sleep(120)
            elif i % 2 == 1:  # odd
                newenv["CUDA_VISIBLE_DEVICES"] = "1"
                log.write("#----Now Starting Eddy Current Correction on GPU 1----#\n\n")
                log.flush()
                # For alternate odd scans, wait two minutes before loading the scan into the GPU
                if i == 3 or i % 4 == 1:
                    time.sleep(120)

            # Running bedpostx_gpu with sticks model (for acquisions with a single non-zero shell)
            time.sleep(randint(1, 90))
            subprocess.run(['/Volumes/apps/linux/fsl-current/bin/bedpostx_gpu', xtractsubj_dir, '-model', '1'])
            bedpostxsubj_dir = xtractsubj_dir / (subjroot + ".bedpostX")

            # Creating files for registration
            b0 = xtractsubj_dir / ("b0.nii")
            subprocess.run(['fslroi', dwinii, b0, '0', '7'])
            mnb0 = xtractsubj_dir / ("meanb0.nii")
            subprocess.run(['fslmaths', b0, '-Tmean', mnb0])
            nodif_brain = xtractsubj_dir / ("nodif_brain.nii")
            subprocess.run(['bet2', mnb0, nodif_brain, '-f', '0.3', '-v'])

            # Creating transforms
            diff2struct = bedpostxsubj_dir / "xfms" / "diff2struct.mat"
            subprocess.run(['flirt', '-in', nodif_brain, '-ref', T1brain, '-omat', diff2struct, '-dof', '6', '-cost',
                            'mutualinfo'])
            struct2diff = bedpostxsubj_dir / "xfms" / "struct2diff.mat"
            subprocess.run(['convert_xfm', '–omat', struct2diff, '-inverse', diff2struct])
            struct2standard = bedpostxsubj_dir / "xfms" / "struct2standard.mat"
            subprocess.run(['flirt', '-in', T1brain, '-ref', '$FSLDIR/data/standard/avg152T1_brain.nii.gz', '-omat',
                            struct2standard, '-dof', '12', '-cost', 'corratio'])
            standard2struct = bedpostxsubj_dir / "xfms" / "standard2struct.mat"
            subprocess.run(['convert_xfm', '–omat', standard2struct, '-inverse', struct2standard])
            diff2standard = bedpostxsubj_dir / "xfms" / "diff2standard.mat"
            subprocess.run(['convert_xfm', '-omat', diff2standard, '-concat', struct2standard, diff2struct])
            standard2diff = bedpostxsubj_dir / "xfms" / "standard2diff.mat"
            subprocess.run(['convert_xfm', '–omat', standard2diff, '-inverse', diff2standard])

subj_dirs = (subj_dir for subj_dir in sorted(BIDSproc_dir.glob('sub*')))
with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=8, verbose=1)(delayed(run_bedpostx)(subj_dir) for subj_dir in sorted(subj_dirs))
