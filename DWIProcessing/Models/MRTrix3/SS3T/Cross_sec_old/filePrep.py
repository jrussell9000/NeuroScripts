#!/usr/bin/env python3
# coding: utf-8

import os
import shutil
import subprocess
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

wmfod_templ = Path('/Users/jdrussell3/scratch/mrtrix/fba/cross_sec/wmfod_template.mif')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')

template_dir = Path('/scratch/jdrussell3/mrtrix/fba/cross_sec')
fod_input_dir = template_dir / 'fod_input'
mask_input_dir = template_dir / 'mask_input'
mask_template = template_dir / 'template_mask.mif'


# Continuing steps from : https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html
# Step 9. Generate a study-specific unbiased FOD template
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html#generate-a-study-specific-unbiased-fod-template

#  9a. Create fod_input and mask_input directories (overwrite if they exist)
if fod_input_dir.exists():
    shutil.rmtree(fod_input_dir)
if mask_input_dir.exists():
    shutil.rmtree(mask_input_dir)
fod_input_dir.mkdir()
mask_input_dir.mkdir()


#  9b. Create relative soft links to each wmfod_norm and mask in the fod_input and mask_input directories
def createFODlinks():
    for wmfod in bidsproc_dir.glob('**/sub*_ses-01_wmfod_norm.mif'):
        os.chdir(fod_input_dir)
        os.symlink(os.path.relpath(wmfod, fod_input_dir), os.path.join(fod_input_dir, os.path.basename(wmfod)))
    for mask in bidsproc_dir.glob('**/sub-*_ses-01_mask_ppd.mif'):
        os.chdir(mask_input_dir)
        os.symlink(os.path.relpath(mask, mask_input_dir), os.path.join(mask_input_dir, os.path.basename(mask)))


#  9c. Create the population template
def createPoplTempl(template_dir, fod_input_dir, mask_input_dir):
    wmfod_template = template_dir / 'wmfod_template.mif'
    subprocess.run(['population_template', fod_input_dir, '-mask_dir', mask_input_dir, wmfod_template,
                    '-voxel_size', '1.5'])
    return wmfod_template


# Step 10. Register all subject FOD images to the FOD template
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html#register-all-subject-fod-images-to-the-fod-template
def regfod2Popltempl(ses_dir, wmfod_template):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'

    dwi_mask_ppd = preproc_dir / (subjroot + '_mask_ppd.mif')
    wmfod_norm = ss3t_dir / (subjroot + '_wmfod_norm.mif')

    subj2templwarp = ss3t_dir / (subjroot + '_subj2templwarp.mif')
    templ2subjwarp = ss3t_dir / (subjroot + '_templ2subjwarp.mif')

    subprocess.run(['mrregister', '-force', wmfod_norm, '-mask1', dwi_mask_ppd, wmfod_template, '-nl_warp',
                    subj2templwarp, templ2subjwarp])


# Step 11. Compute the template mask (intersection of all subject masks in template space)
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html#compute-the-template-mask-intersection-of-all-subject-masks-in-template-space

#  11a. Warp all subject masks into template space
def transformMask(ses_dir):
    subj_dir = ses_dir.parent
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'
    subjroot = "_".join([subj_dir.name, ses_dir.name])

    dwiMaskUps = preproc_dir / (subjroot + '_mask_ppd.mif')
    subj2templwarp_mif = ss3t_dir / (subjroot + '_subj2templwarp.mif')
    dwiMaskInTemplSpace = ss3t_dir / (subjroot + '_mask_ppd_reg2CrossSectempl.mif')
    subprocess.run(['mrtransform', dwiMaskUps, '-warp', subj2templwarp_mif, '-interp', 'nearest',
                    '-datatype', 'bit', dwiMaskInTemplSpace])
    return subj2templwarp_mif


#  11b. Compute the template mask as the intersection of all warped masks
def computeTemplMask():
    mifstrs = []
    for mif in bidsproc_dir.glob('**/ses-01/dwi/preprocessed/sub*ses-01_mask_ppd_reg2CrossSectempl.mif'):
        mifstrs.append(str(mif))
    common_mask_paths = ' '.join(mifstrs)
    # cannot use subprocess with line below - doesn't accept common_mask_paths as multiple files
    os.system('mrmath ' + common_mask_paths + ' min ' + str(mask_template) + ' -datatype' + ' bit')
    return mask_template


# Step 12. Compute a white matter template analysis fixel mask
def segmentFODTempl(wmfod_template, mask_template):
    fixel_mask = template_dir / 'fixel_mask'
    if fixel_mask.exists():
        shutil.rmtree(fixel_mask)
    subprocess.run(['fod2fixel', '-mask', mask_template, '-fmls_peak_value', '0.06',
                    wmfod_template, fixel_mask])
    return fixel_mask


# Step 13. Warp FOD images to template space
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html#warp-fod-images-to-template-space
def warpFODs2Templ(ses_dir):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'

    wmfod_norm = ss3t_dir / (subjroot + '_wmfod_norm.mif')
    subj2templwarp = ss3t_dir / (subjroot + '_subj2templwarp.mif')
    wmfod_norm_reg2templ_notreoriented = ss3t_dir / (subjroot + '_wmfod_norm_reg2templ_notreoriented.mif')

    subprocess.run(['mrtransform', '-force', '-warp', subj2templwarp, '-reorient_fod', 'no', wmfod_norm,
                    wmfod_norm_reg2templ_notreoriented])
    return wmfod_norm_reg2templ_notreoriented


def segmentSubjFODs(ses_dir):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    proc_dir = ses_dir / 'dwi' / 'processed'
    ss3t_dir = proc_dir / 'mrtrix' / 'ss3t'

    wmfod_norm_reg2templ_notreoriented = ss3t_dir / (subjroot + '_wmfod_norm_reg2templ_notreoriented.mif')
    fixel_reg2templ_notreoriented = ss3t_dir / 'fixel_reg2templ_notreoriented'

    if fixel_reg2templ_notreoriented.exists():
        shutil.rmtree(fixel_reg2templ_notreoriented)
    fiber_density_notreoriented = str(subjroot + '_fd.mif')
    subprocess.run(['fod2fixel', '-mask', mask_template, wmfod_norm_reg2templ_notreoriented,
                    fixel_reg2templ_notreoriented, '-afd', fiber_density_notreoriented])
    return fixel_reg2templ_notreoriented





ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-*') if Path(ses_dir / 'dwi').exists())

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(regfod2templ)(ses_dir) for ses_dir in sorted(ses_dirs))
 