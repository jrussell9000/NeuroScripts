#!/usr/bin/env python3
# coding: utf-8

import os
from pathlib import Path
import shutil
import subprocess
from joblib import parallel_backend, delayed, Parallel

nCores = 8

ss3t_longproc_dir = Path('/fast_scratch/jdr/dti_longproc/')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
fixelmask_dir = Path('/fast_scratch/jdr/dti_longproc/fixel_mask')
FD_dir = Path('/fast_scratch/jdr/dti_longproc/FD')
FC_dir = Path('/fast_scratch/jdr/dti_longproc/FC')
logFC_dir = Path('/fast_scratch/jdr/dti_longproc/logFC')
FDC_dir = Path('/fast_scratch/jdr/dti_longproc/FDC')


def clearOldCompDirs(FC_dir, FClog_dir, FDC_dir):

    if FC_dir.exists():
        shutil.rmtree(FC_dir)
    if FClog_dir.exists():
        shutil.rmtree(FClog_dir)
    if FDC_dir.exists():
        shutil.rmtree(FDC_dir)


def loadsubj(ses_dir):
    subj_dir = ses_dir.parent
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    subj2templwarp_mif = ss3t_dir / (subjroot + '_subj2templwarp.mif')
    return subjroot, subj2templwarp_mif


def computeFC(subjroot, subj2templwarp_mif, fixelmask_dir, FC_dir):
    if not FC_dir.exists():
        FC_dir.mkdir()
    subjFC_mif2cmd = str(subjroot + '_fc.mif')
    subprocess.run(['warp2metric', '-force', subj2templwarp_mif, '-fc', fixelmask_dir, FC_dir,
                    subjFC_mif2cmd])
    subjFC_mif = FC_dir / (subjroot + '_fc.mif')
    return subjFC_mif


def computeFClog(subjroot, subjFC_mif, logFC_dir):
    if not logFC_dir.exists():
        logFC_dir.mkdir()
        os.chdir(FC_dir)
        shutil.copy2('directions.mif', logFC_dir)
        shutil.copy2('index.mif', logFC_dir)
    subjlogFC_mif = logFC_dir / (subjroot + '_logfc.mif')
    subprocess.run(['mrcalc', subjFC_mif, '-log', subjlogFC_mif])


# FDC = FD x FC (NOT FD x log(FC)) per https://community.mrtrix.org/t/intersection-mask-using-mrmath-min/493/2
def computeFDC(subjroot, FD_dir, FC_dir, FDC_dir):
    if not FDC_dir.exists():
        FDC_dir.mkdir()
        os.chdir(FC_dir)
        shutil.copy2('directions.mif', FDC_dir)
        shutil.copy2('index.mif', FDC_dir)
    subjFD_mif = FD_dir / (subjroot + '_fd.mif')
    subjFC_mif = FC_dir / (subjroot + '_fc.mif')
    subjFDC_mif = FDC_dir / (subjroot + '_fdc.mif')
    subprocess.run(['mrcalc', subjFD_mif, subjFC_mif, '-mult', subjFDC_mif])


def computeAll(ses_dir):
    subjroot, subj2templwarp_mif = loadsubj(ses_dir)
    subjFC_mif = computeFC(subjroot, subj2templwarp_mif, fixelmask_dir, FC_dir)
    computeFClog(subjroot, subjFC_mif, logFC_dir)
    computeFDC(subjroot, FD_dir, FC_dir, FDC_dir)


def main():
    clearOldCompDirs(FC_dir, logFC_dir, FDC_dir)
    ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir.parent / 'ses-01' / 'dwi').exists() and
                Path(ses_dir.parent / 'ses-02' / 'dwi').exists())

    newenv = os.environ.copy()
    newenv["MRTRIX_NTHREADS"] = nCores

    with parallel_backend("loky", inner_max_num_threads=nCores):
        Parallel(n_jobs=8, verbose=1)(
            delayed(computeAll)(ses_dir) for ses_dir in sorted(ses_dirs))


main()
