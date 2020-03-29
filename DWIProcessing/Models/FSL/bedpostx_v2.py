import os
import shutil
import subprocess
import time
from joblib import parallel_backend, delayed, Parallel
from pathlib import Path
from random import randint

xtractproc_dir = Path("/scratch/jdrussell3/fsl/cross_sec/xtract")
BIDSproc_dir = Path("/Volumes/Vol6/YouthPTSD/BIDS_Processed")
BIDSmaster_dir = Path("/Volumes/Vol6/YouthPTSD/BIDS_Master")

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
    xtractlog_dir = xtractproc_dir / 'logs'
    if not xtractlog_dir.exists():
        xtractlog_dir.mkdir()

    logfile = xtractlog_dir / (subjroot + "_xtract.txt")
    if logfile.exists():
        os.remove(logfile)

    with open(logfile, 'a') as log:
        T1orig = BIDSmaster_dir / subj_dir.name / ses_dir.name / 'anat' / (subjroot + "_acq-AXFSPGRBRAVONEW_T1w.nii")
        T1 = xtractsubj_dir / (subjroot + "_T1w.nii")
        T1brain = xtractsubj_dir / (subjroot + "_T1w_brain.nii")
        shutil.copy(T1orig, T1)
        subprocess.run(['bet2', T1, T1brain, '-f', '0.3', '-v'], stdout=log, stderr=subprocess.STDOUT)

        orig_dwi_mif = preproc_dir / (subjroot + "_ppd.mif")
        orig_mask_mif = preproc_dir / (subjroot + "_mask_ppd.mif")
        orig_bvals = preproc_dir / (subjroot + "_ppd.bval")
        orig_bvecs = preproc_dir / (subjroot + "_ppd.bvec")

        input_dwi = xtractsubj_dir / "data.nii"
        input_mask = xtractsubj_dir / "nodif_brain_mask.nii"
        input_bvals = xtractsubj_dir / 'bvals'
        input_bvecs = xtractsubj_dir / 'bvecs'

        # Copying files to run bedpostx
        subprocess.run(['mrconvert', '-force', orig_dwi_mif, input_dwi], stdout=log, stderr=subprocess.STDOUT)
        subprocess.run(['mrconvert', '-force', orig_mask_mif, input_mask], stdout=log, stderr=subprocess.STDOUT)
        shutil.copy2(orig_bvals, input_bvals)
        shutil.copy2(orig_bvecs, input_bvecs)

        newenv = os.environ.copy()

        for i in range(len(ses_list)):
            if str(ses_dir) in ses_list[i]:
                if i % 2 == 0:  # even
                    newenv["CUDA_VISIBLE_DEVICES"] = "0"
                    log.write("#----Now Starting BEDPOSTX on GPU 0----#\n\n")
                    log.flush()
                    # For alternate even scans, wait two minutes before loading the scan into the GPU
                    if i == 2 or i % 3 == 1:
                        time.sleep(120)
                elif i % 2 == 1:  # odd
                    newenv["CUDA_VISIBLE_DEVICES"] = "1"
                    log.write("#----Now Starting BEDPOSTX on GPU 1----#\n\n")
                    log.flush()
                    # For alternate odd scans, wait two minutes before loading the scan into the GPU
                    if i == 3 or i % 4 == 1:
                        time.sleep(120)

                # Running bedpostx_gpu with sticks model (for acquisions with a single non-zero shell)
                time.sleep(randint(1, 90))
                subprocess.run(['/Volumes/apps/linux/fsl-current/bin/bedpostx_gpu', xtractsubj_dir, '-model', '1'],
                               stdout=log, stderr=subprocess.STDOUT, env=newenv)
                bedpostxsubj_dir = xtractproc_dir / (subjroot + ".bedpostX")

                # Creating files for registration
                b0 = xtractsubj_dir / ("b0.nii")
                subprocess.run(['fslroi', input_dwi, b0, '0', '7'], stdout=log, stderr=subprocess.STDOUT)
                mnb0 = xtractsubj_dir / ("meanb0.nii")
                subprocess.run(['fslmaths', b0, '-Tmean', mnb0], stdout=log, stderr=subprocess.STDOUT)
                nodif_brain = xtractsubj_dir / ("nodif_brain.nii")
                subprocess.run(['bet2', mnb0, nodif_brain, '-f', '0.3', '-v'], stdout=log, stderr=subprocess.STDOUT)

                # Creating transforms
                diff2struct = bedpostxsubj_dir / "xfms" / "diff2struct.mat"
                subprocess.run(['flirt', '-in', nodif_brain, '-ref', T1brain, '-omat', diff2struct, '-dof', '6',
                                '-cost', 'mutualinfo'], stdout=log, stderr=subprocess.STDOUT)

                struct2diff = bedpostxsubj_dir / "xfms" / "struct2diff.mat"
                os.system('convert_xfm -omat ' + str(struct2diff) + ' -inverse ' + str(diff2struct))

                struct2standard = bedpostxsubj_dir / "xfms" / "struct2standard.mat"
                subprocess.run(['flirt', '-in', T1brain, '-ref', os.path.expandvars('$FSLDIR/data/standard/avg152T1_brain.nii.gz'), '-omat',
                                struct2standard, '-dof', '12', '-cost', 'corratio'],
                               stdout=log, stderr=subprocess.STDOUT)

                standard2struct = bedpostxsubj_dir / "xfms" / "standard2struct.mat"
                os.system('convert_xfm -omat ' + str(standard2struct) + ' -inverse ' + str(struct2standard))
                # subprocess.run(['convert_xfm', '–omat', standard2struct, '-inverse', struct2standard],
                #                stdout=log, stderr=subprocess.STDOUT)

                diff2standard = bedpostxsubj_dir / "xfms" / "diff2standard.mat"
                os.system('convert_xfm -omat ' + str(diff2standard) + ' -concat ' + str(struct2standard) +
                          ' ' + str(diff2struct))
                # subprocess.run(['convert_xfm', '-omat', diff2standard, '-concat', struct2standard, diff2struct],
                #                stdout=log, stderr=subprocess.STDOUT)

                standard2diff = bedpostxsubj_dir / "xfms" / "standard2diff.mat"
                os.system('convert_xfm -omat ' + str(standard2diff) + ' -inverse ' + str(diff2standard))
                # subprocess.run(['convert_xfm', '–omat', standard2diff, '-inverse', diff2standard],
                #                stdout=log, stderr=subprocess.STDOUT)

                shutil.rmtree(xtractsubj_dir)

ses_dirs = (ses_dir for ses_dir in BIDSproc_dir.glob('*/ses-01')
            if Path(ses_dir / 'dwi').exists())

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(run_bedpostx)(ses_dir) for ses_dir in sorted(ses_dirs))
