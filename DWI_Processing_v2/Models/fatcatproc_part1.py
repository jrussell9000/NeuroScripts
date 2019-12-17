#!/usr/bin/env python
# coding: utf-8

import os,sys,shutil,subprocess,time
from pathlib import Path
from joblib import Parallel, delayed, parallel_backend


def fatcatproc_part1(subjdir):
    for sesdir in subjdir.iterdir():
        #print("##########################################")
        #print("Starting subject: " + subjdir.name + ", session: ", sesdir.name + "....")
        #print("##########################################")
        sourcedir = Path(sesdir,'dti')
        if not sourcedir.exists():
            sourcedir.mkdir()
        subjroot = "_".join([subjdir.name, sesdir.name])

        #Creating processing directories
        afniprocdir = Path(sourcedir, 'afni')
        if afniprocdir.exists():
            shutil.rmtree(afniprocdir)
        afniprocdir.mkdir()
        fatcat_dir = Path(afniprocdir, 'fatcat')
        fatcat_dir.mkdir(exist_ok=True)
        fatcat_dwidir = fatcat_dir / 'dwi'
        fatcat_dwidir.mkdir(exist_ok=True)
        fatcat_t2wdir = fatcat_dir / 't2w'
        fatcat_t2wdir.mkdir(exist_ok=True)
        fatcat_t1wdir = fatcat_dir / 't1w'
        fatcat_t1wdir.mkdir(exist_ok=True)

        #Creating source file variable
        sourcedwi = sourcedir / (subjroot + "_ppd.mif")

        #Creating mrconvert output file variables
        fatcat_bvec = fatcat_dwidir / (subjroot + ".bvec")
        fatcat_bval = fatcat_dwidir / (subjroot + ".bval")
        fatcat_dwinii = fatcat_dwidir / (subjroot + ".nii")

        #Running mrconvert on sourcedwi and outputting to fatcat_dwidir
        subprocess.run(['mrconvert','-force', '-export_grad_fsl', fatcat_bvec, fatcat_bval, sourcedwi, fatcat_dwinii])

        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>#
        #-------fat_proc_convert_dcm_dwis--------#
        #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<#
        os.chdir(fatcat_dir) #Must change to fatcat_dir first
        fatcat_dwi00dir = fatcat_dir / 'dwi00'
        fatcat_dwi00dir.mkdir()
        fatcat_dwi00dir_dwiprefix = fatcat_dwi00dir / 'dwi'
        subprocess.run(['fat_proc_convert_dcm_dwis', '-innii', fatcat_dwinii, '-inbvec', fatcat_bvec, '-inbval', fatcat_bval, '-prefix', str(fatcat_dwi00dir_dwiprefix)])

        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>#
        #-------Copying original T1w and T2w volumes--------#
        #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<#

        #Creating variables as necessary to copy the T2w and T1w volumes from BIDS_master
        ##Source variables
        anat_sourcedir = Path(bidsmaster_dir, subjdir.name, sesdir.name, 'anat')
        orig_t1w = Path(anat_sourcedir, "_".join([subjdir.name, sesdir.name, 'acq-AXFSPGRBRAVONEW', 'T1w.nii']))
        orig_t2w = Path(anat_sourcedir, "_".join([subjdir.name, sesdir.name, 'acq-AxT2FLAIRCOPYDTI', 'T2w.nii']))

        ##Destination variables
        fatcat_t1w = fatcat_t1wdir / 't1w.nii'
        fatcat_t2w = fatcat_t2wdir / 't2w.nii'

        #Copying original T1w and T2w volumes to fatcat/t1w and fatcat/t2w
        if anat_sourcedir.exists():
            print("Copying T1w NiFTI...")  
            shutil.copy(orig_t1w, fatcat_t1w)

            print("Copying T2w NiFTI...")
            shutil.copy(orig_t2w, fatcat_t2w)

        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>#
        #-------fat_proc_convert_dcm_anat--------#
        #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<#

        #Making output directory
        fatcat_anat00dir = fatcat_dir / 'anat_00'

        #T1w - Outputting to fatcat_anat00dir/t1w.nii.gz
        fatcat_anat00dir_t1wprefix = fatcat_anat00dir / 't1w'
        subprocess.run(['fat_proc_convert_dcm_anat', '-innii', fatcat_t1w, '-prefix', str(fatcat_anat00dir_t1wprefix)])
        fatcat_anat00dir_t1w = fatcat_anat00dir / 't1w.nii.gz'

        #T2w - Outputting to fatcat_anat00dir/t2w.nii.gz
        fatcat_anat00dir_t2wprefix = fatcat_anat00dir / 't2w'
        subprocess.run(['fat_proc_convert_dcm_anat', '-innii', fatcat_t2w, '-prefix', str(fatcat_anat00dir_t2wprefix)])
        fatcat_anat00dir_t2w = fatcat_anat00dir / 't2w.nii.gz'

        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>#
        #-------fat_proc_axialize_anat--------#
        #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<#

        #Making output directory
        fatcat_anat01dir = fatcat_dir / 'anat_01'

        #Axializing the T2w volume - Outputting to fatcat_anat00dir/t2w.nii.gz
        fatcat_anat01dir_t2wprefix = fatcat_anat01dir / 't2w'
        subprocess.run(['fat_proc_axialize_anat', '-inset', fatcat_anat00dir_t2w, '-prefix', str(fatcat_anat01dir_t2wprefix) , '-mode_t2w', '-refset', axializeref_t2w, \
        '-extra_al_wtmask', axializeref_t2w_wt, '-out_match_ref', '-extra_al_opts', '-newgrid 1.0'])
        fatcat_anat01dir_t2w = fatcat_anat01dir / 't2w.nii.gz'
        time.sleep(20)

        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>#
        #-------fat_proc_axialize_anat--------#
        #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<#

        subprocess.run(['align_epi_anat.py', '-dset1', fatcat_anat01dir_t2w, '-dset2', fatcat_anat00dir_t1w, '-align_centers', 'yes', '-dset1_strip', 'None', '-dset2_strip', 'None', \
        '-big_move', '-rigid_body', '-dset2to1', '-dset2_base', '0', '-prep_off', '-suffix', 'align'])
        time.sleep(20)

bidsproc_dir = Path('/scratch/jdrussell3/bidsproc')
bidsmaster_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_master/')

axializeref_t2w = Path('/scratch/jdrussell3/mni2009/mni_icbm152_t2_relx_tal_nlin_sym_09a_ACPCE.nii.gz')
axializeref_t2w_wt = Path('/scratch/jdrussell3/mni2009/mni_icbm152_t1_tal_nlin_sym_09a_MSKD_ACPCE_wtell.nii.gz')

subjdirs = (subjdir for subjdir in bidsproc_dir.iterdir() if subjdir.is_dir())

os.chdir('/scratch/jdrussell3/')       

with parallel_backend("loky", inner_max_num_threads=4):
    results = Parallel(n_jobs=8, verbose = 1)(delayed(fatcatproc_part1)(subjdir) for subjdir in sorted(bidsproc_dir.iterdir()) if subjdir.is_dir())


