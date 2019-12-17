from pathlib import Path
import shutil, os, subprocess, time
from joblib import parallel_backend, delayed, Parallel
from random import randint

xtractproc_dir = Path("/Volumes/Vol6/YouthPTSD/xtract")
BIDSproc_dir = Path("/Volumes/Vol6/YouthPTSD/BIDS_Processed")


def run_bedpostx(subjdir):
    for ses_dir in sorted(subjdir.glob('ses*')):
        subjroot = "_".join([subjdir.name, ses_dir.name])
        xtractsubj_dir = xtractproc_dir / subjroot
        xtractsubj_dir.mkdir(exist_ok=True)

        for anat_dir in ses_dir.glob('anat'):
            T1orig = anat_dir / (subjroot + "_acq-AXFSPGRBRAVONEW_T1w.nii")
            T1 = xtractsubj_dir / (subjroot + "_T1w.nii")
            T1brain = xtractsubj_dir / (subjroot + "_T1w_brain.nii")
            shutil.copy(T1orig, T1)
            subprocess.run(['bet2', T1, T1brain, '-f', '0.3', '-v'])
        
        for dwi_dir in ses_dir.glob('dwi'):
            proc_dir = dwi_dir / 'preprocessed'
            procdwi = proc_dir / (subjroot + "_ppd.mif")
            procdwimask = proc_dir / (subjroot + "_mask_ppd.mif")
            procbval = proc_dir / (subjroot + "_ppd.bval")
            procbvec = proc_dir / (subjroot + "_ppd.bvec")
            dwinii = xtractsubj_dir / ("data.nii")
            dwimasknii = xtractsubj_dir / "nodif_brain_mask.nii"
            bvals = xtractsubj_dir / 'bvals'
            bvecs = xtractsubj_dir / 'bvecs'
 
            #Copying files to run bedpostx
            subprocess.run(['mrconvert', '-force', procdwi, dwinii])
            subprocess.run(['mrconvert', '-force', procdwimask, dwimasknii])
            shutil.copy(procbval, bvals)
            shutil.copy(procbvec, bvecs)

            #Running bedpostx_gpu with sticks model (for acquisionts with a single non-zero shell)
            time.sleep(randint(1,90))
            subprocess.run(['/Volumes/apps/linux/fsl-current/bin/bedpostx_gpu', xtractsubj_dir, '-model', '1'])
            bedpostxsubj_dir = xtractsubj_dir / (subjroot + ".bedpostX")

            #Creating files for registration
            b0 = xtractsubj_dir / ("b0.nii")
            subprocess.run(['fslroi', dwinii, b0, '0', '7'])
            mnb0 = xtractsubj_dir / ("meanb0.nii")
            subprocess.run(['fslmaths', b0, '-Tmean', mnb0])
            nodif_brain = xtractsubj_dir / ("nodif_brain.nii")
            subprocess.run(['bet2', mnb0, nodif_brain, '-f', '0.3', '-v'])

            #Creating transforms
            diff2struct = bedpostxsubj_dir / "xfms" / "diff2struct.mat"
            subprocess.run(['flirt', '-in', nodif_brain, '-ref', T1brain, '-omat', diff2struct, '-dof', '6', '-cost', 'mutualinfo'])
            struct2diff = bedpostxsubj_dir / "xfms" / "struct2diff.mat"
            subprocess.run(['convert_xfm', '–omat', struct2diff, '-inverse', diff2struct])
            struct2standard = bedpostxsubj_dir / "xfms" / "struct2standard.mat"
            subprocess.run(['flirt', '-in', T1brain, '-ref', '$FSLDIR/data/standard/avg152T1_brain.nii.gz', '-omat' , struct2standard, '-dof', '12', '-cost', 'corratio'])
            standard2struct = bedpostxsubj_dir / "xfms" / "standard2struct.mat"
            subprocess.run(['convert_xfm', '–omat', standard2struct, '-inverse', struct2standard])
            diff2standard = bedpostxsubj_dir / "xfms" / "diff2standard.mat"
            subprocess.run(['convert_xfm', '-omat', diff2standard, '-concat', struct2standard, diff2struct])
            standard2diff = bedpostxsubj_dir / "xfms" / "standard2diff.mat"
            subprocess.run(['convert_xfm', '–omat', standard2diff, '-inverse', diff2standard])



subj_dirs = (subj_dir for subj_dir in sorted(BIDSproc_dir.glob('sub*')))
with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=8, verbose = 1)(delayed(run_bedpostx)(subj_dir) for subj_dir in sorted(subj_dirs))

            