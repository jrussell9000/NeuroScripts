from pathlib import Path
import shutil, os, subprocess

#1.  Each subject in a separate directory containing the data, bvecs, bvals, nodif_brain_mask

xtractproc_dir = Path("/Volumes/Vol6/YouthPTSD/xtract")
BIDSproc_dir = Path("/Volumes/Vol6/YouthPTSD/BIDS_Processed")
for subjdir in sorted(BIDSproc_dir.glob('sub-009')):
    for sesdir in sorted(subjdir.glob('ses*')):
        for dwidir in sesdir.glob('dwi'):
            subjroot = "_".join([subjdir.name, sesdir.name])
            proc_dir = dwidir / 'preprocessed'
            procdwi = proc_dir / (subjroot + "_ppd.mif")
            procdwimask = proc_dir / (subjroot + "_mask_ppd.mif")
            procbval = proc_dir / (subjroot + "_ppd.bval")
            procbvec = proc_dir / (subjroot + "_ppd.bvec")
            xtractsubj_dir = xtractproc_dir / subjroot
            xtractsubj_dir.mkdir(exist_ok=True)
            dwinii = xtractsubj_dir / ("data.nii")
            dwimasknii = xtractsubj_dir / "nodif_brain_mask.nii"
            bvals = xtractsubj_dir / 'bvals'
            bvecs = xtractsubj_dir / 'bvecs'
            subprocess.run(['mrconvert', '-force', procdwi, dwinii])
            subprocess.run(['mrconvert', '-force', procdwimask, dwimasknii])
            shutil.copy(procbval, bvals)
            shutil.copy(procbvec, bvecs)
            # subprocess.run(['/Users/jdrussell3/apps/autoptx/autoPtx_1_preproc', dwinii])
            # os.chdir(autoptxproc_dir)
            # subprocess.run(['/Users/jdrussell3/apps/autoptx/autoPtx_2_preproc'])
            