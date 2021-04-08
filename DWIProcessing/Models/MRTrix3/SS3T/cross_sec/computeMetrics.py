#!/usr/bin/env python3
# coding: utf-8

import os
from pathlib import Path
import shutil
import subprocess
from joblib import parallel_backend, delayed, Parallel

nCores = 8

template_dir = Path('/fast_scratch/jdr/mrtrix/cross_sec/')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
fixelmask_dir = template_dir / 'fixel_mask'
FD_dir = template_dir / 'FD'
FC_dir = template_dir / 'FC'
logFC_dir = template_dir / 'log_FC'
FDC_dir = template_dir / 'FDC'


def createCompDirs(FC_dir, FClog_dir, FDC_dir):

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


# Step 17. Compute the fibre cross-section (FC) metric
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html#compute-the-fibre-cross-section-fc-metric
def computeFC(subjroot, subj2templwarp_mif, fixelmask_dir, FC_dir):
    if not FC_dir.exists():
        FC_dir.mkdir()
    subjFC_mif2cmd = str(subjroot + '_fc.mif')
    subprocess.run(['warp2metric', '-force', subj2templwarp_mif, '-fc', fixelmask_dir, FC_dir,
                    subjFC_mif2cmd])
    subjFC_mif = FC_dir / (subjroot + '_fc.mif')
    return subjFC_mif


#  17a. Compute logFC to ensure data are centered around zero and normally distributed
def computeFClog(subjroot, subjFC_mif, logFC_dir):
    if not logFC_dir.exists():
        logFC_dir.mkdir()
        os.chdir(FC_dir)
        shutil.copy2('directions.mif', logFC_dir)
        shutil.copy2('index.mif', logFC_dir)
    subjlogFC_mif = logFC_dir / (subjroot + '_logfc.mif')
    subprocess.run(['mrcalc', subjFC_mif, '-log', subjlogFC_mif])


# Step 18. Compute a combined measure of fibre density and cross-section (FDC)
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html#compute-a-combined-measure-of-fibre-density-and-cross-section-fdc
# NOTE: FDC = FD x FC (NOT FD x log(FC)) per https://community.mrtrix.org/t/intersection-mask-using-mrmath-min/493/2
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
    createCompDirs(FC_dir, logFC_dir, FDC_dir)
    ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-01') if Path(ses_dir / 'dwi').exists())

    newenv = os.environ.copy()
    newenv["MRTRIX_NTHREADS"] = nCores

    with parallel_backend("loky", inner_max_num_threads=nCores):
        Parallel(n_jobs=1, verbose=1)(
            delayed(computeAll)(ses_dir) for ses_dir in sorted(ses_dirs))


main()
