#!/usr/bin/env python3
# coding: utf-8

import shutil
import subprocess
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

ss3t_longproc_dir = Path('/fast_scratch/jdr/dti_longproc')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
intrasubjreg_dir = ss3t_longproc_dir / 'intrasubjreg'
intersubjreg_dir = ss3t_longproc_dir / 'intersubjreg'
intersubjreg_fods_dir = ss3t_longproc_dir / 'intersubjreg' / 'fods'
intersubjreg_masks_dir = ss3t_longproc_dir / 'intersubjreg' / 'masks'
if not intrasubjreg_dir.exists():
    intrasubjreg_dir.mkdir()
if not intersubjreg_dir.exists():
    intersubjreg_dir.mkdir()
if not intersubjreg_fods_dir.exists():
    intersubjreg_fods_dir.mkdir()
if not intersubjreg_masks_dir.exists():
    intersubjreg_masks_dir.mkdir()


def copy2intrasubtempl_dir(subj_dir):

    ses01wmfod_orig = subj_dir / 'ses-01' / 'dwi' / 'processed' / 'mrtrix' / 'ss3t'/ (subj_dir.name + '_ses-01_wmfod_norm.mif')
    ses02wmfod_orig = subj_dir / 'ses-02' / 'dwi' / 'processed' / 'mrtrix' / 'ss3t'/ (subj_dir.name + '_ses-02_wmfod_norm.mif')

    ses01mask_orig = subj_dir / 'ses-01' / 'dwi' / 'preprocessed' / (subj_dir.name + '_ses-01_mask_ppd.mif')
    ses02mask_orig = subj_dir / 'ses-02' / 'dwi' / 'preprocessed' / (subj_dir.name + '_ses-02_mask_ppd.mif')

    subj_intrasubjreg_dir = intrasubjreg_dir / subj_dir.name
    subj_intrasubjreg_fods_dir = subj_intrasubjreg_dir / 'fods'
    subj_intrasubjreg_masks_dir = subj_intrasubjreg_dir / 'masks'
    if subj_intrasubjreg_dir.exists():
        shutil.rmtree(subj_intrasubjreg_dir)
    if subj_intrasubjreg_fods_dir.exists():
        shutil.rmtree(subj_intrasubjreg_fods_dir)
    if subj_intrasubjreg_masks_dir.exists():
        shutil.rmtree(subj_intrasubjreg_masks_dir)
    subj_intrasubjreg_dir.mkdir()
    subj_intrasubjreg_fods_dir.mkdir()
    subj_intrasubjreg_masks_dir.mkdir()

    ses01wmfod = subj_intrasubjreg_fods_dir / 'ses-01_wmfod_norm.mif'
    ses02wmfod = subj_intrasubjreg_fods_dir / 'ses-02_wmfod_norm.mif'

    ses01mask = subj_intrasubjreg_masks_dir / 'ses-01_dwi_mask_ppd.mif'
    ses02mask = subj_intrasubjreg_masks_dir / 'ses-02_dwi_mask_ppd.mif'

    shutil.copy(ses01wmfod_orig, ses01wmfod)
    shutil.copy(ses02wmfod_orig, ses02wmfod)
    shutil.copy(ses01mask_orig, ses01mask)
    shutil.copy(ses02mask_orig, ses02mask)

    return subj_intrasubjreg_dir, subj_intrasubjreg_fods_dir, subj_intrasubjreg_masks_dir, ses01wmfod, ses02wmfod, \
        ses01mask, ses02mask


def makeintrasubjtempl(subj_dir, subj_intrasubjreg_dir, subj_intrasubjreg_fods_dir, subj_intrasubjreg_masks_dir):
    # Output the intrasubject templates to the intersubject directory for processing
    subj_intrasubjreg_wmfodtempl = intersubjreg_fods_dir / (subj_dir.name + '_wmfod_intrasubjtempl.mif')
    subj_intrasubjreg_masktempl = intersubjreg_masks_dir / (subj_dir.name + '_mask_intrasubjtempl.mif')
    # Create an intra-subject template from the time 1 and time 2 FODs and masks, then output the template
    # to a inter-subjects directory for more processing
    subprocess.run(['population_template', subj_intrasubjreg_fods_dir, subj_intrasubjreg_wmfodtempl, '-force', '-type',
                    'rigid_affine', '-voxel_size', '1.5', '-mask_dir', subj_intrasubjreg_masks_dir, '-template_mask',
                    subj_intrasubjreg_masktempl, '-scratch', '/tmp/'])


# Not appropriate to register the fod to the intrasubject template, then re-register them to the population template
# per https://community.mrtrix.org/t/replicating-longitudinal-fixel-based-analysis-approach/2071/16
# def makeintrasubjwarps(subj_dir, subj_intrasubjreg_dir, subj_intrasubjreg_wmfodtempl, ses01wmfod, ses02wmfod,
#                        ses01mask, ses02mask):
#     subj_intrasubjreg_warps_dir = subj_intrasubjreg_dir / 'warps'
#     subj_intrasubjreg_warps_dir.mkdir()
#     ses01wmfod_subj2templ_warp = subj_intrasubjreg_warps_dir / (subj_dir.name + '_ses-01_wmfod_subj2templ.mif')
#     ses01wmfod_templ2subj_warp = subj_intrasubjreg_warps_dir / (subj_dir.name + '_ses-01_wmfod_templ2subj.mif')
#     ses02wmfod_subj2templ_warp = subj_intrasubjreg_warps_dir / (subj_dir.name + '_ses-02_wmfod_subj2templ.mif')
#     ses02wmfod_templ2subj_warp = subj_intrasubjreg_warps_dir / (subj_dir.name + '_ses-02_wmfod_templ2subj.mif')

#     subprocess.run(['mrregister', ses01wmfod, '-mask1', ses01mask, subj_intrasubjreg_wmfodtempl, '-nlwarp',
#                     ses01wmfod_subj2templ_warp, ses01wmfod_templ2subj_warp])

#     subprocess.run(['mrregister', ses02wmfod, '-mask1', ses02mask, subj_intrasubjreg_wmfodtempl, '-nlwarp',
#                     ses02wmfod_subj2templ_warp, ses02wmfod_templ2subj_warp])

def create_intrasubj_template(subj_dir):
    subj_intrasubjreg_dir, subj_intrasubjreg_fods_dir, subj_intrasubjreg_masks_dir, ses01wmfod, ses02wmfod, ses01mask, \
        ses02mask = copy2intrasubtempl_dir(subj_dir)
    makeintrasubjtempl(subj_dir, subj_intrasubjreg_dir, subj_intrasubjreg_fods_dir, subj_intrasubjreg_masks_dir)


def create_intersubj_template(ss3t_longproc_dir, intersubjreg_fods_dir, intersubjreg_masks_dir):
    intersubj_fod_templ = ss3t_longproc_dir / 'YouthPTSD_wmfodtempl_long.mif'
    intersubj_mask_templ = ss3t_longproc_dir / 'YouthPTSD_masktempl_long.mif'
    subprocess.run(['population_template', intersubjreg_fods_dir, intersubj_fod_templ, '-voxel_size', '1.5',
                    '-mask_dir', intersubjreg_masks_dir, '-template_mask', intersubj_mask_templ, '-scratch',
                    '/tmp/'])


def main():
    subj_dirs = (subj_dir for subj_dir in bidsproc_dir.glob('sub-*') if Path(subj_dir / 'ses-01' / 'dwi').exists() and
                 Path(subj_dir / 'ses-02' / 'dwi').exists())
    with parallel_backend("loky", inner_max_num_threads=8):
        Parallel(n_jobs=8, verbose=1)(
            delayed(create_intrasubj_template)(subj_dir) for subj_dir in sorted(subj_dirs))


main()
create_intersubj_template(ss3t_longproc_dir, intersubjreg_fods_dir, intersubjreg_masks_dir)
