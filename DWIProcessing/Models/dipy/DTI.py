import os
# import shutil
# import string
# import subprocess
# import sys
# import time
import dipy.reconst.dti as dti
import numpy as np
import nibabel as nib
import shutil
import subprocess

from dipy.denoise.noise_estimate import estimate_sigma
from dipy.core.gradients import gradient_table
from dipy.io import read_bvals_bvecs
from joblib import parallel_backend, delayed, Parallel
from pathlib import Path
# from dipy.reconst.dti import fractional_anisotropy

out_dir = Path('/Users/jdrussell3/scratch/fsl/dtifit')


def loadsubj(ses_dir, out_dir):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    input_mif = preproc_dir / (subjroot + '_ppd.mif')
    mask_mif = preproc_dir / (subjroot + '_mask_ppd.mif')
    output_dir = out_dir / subjroot
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    return input_mif, mask_mif, output_dir, subjroot


def mif2nii(input_mif, mask_mif, output_dir, subjroot):
    input_bvec = input_mif.parent / (subjroot + '_ppd.bvec')
    input_bval = input_mif.parent / (subjroot + '_ppd.bval')
    input_dwi = output_dir / (subjroot + '_ppd.nii')
    input_mask = output_dir / (subjroot + '_mask_ppd.nii')
    subprocess.run(['mrconvert', input_mif, input_dwi])
    subprocess.run(['mrconvert', mask_mif, input_mask])
    print(input_bval)
    return input_bval, input_bvec, input_dwi, input_mask


def fit_dti_dipy(input_dwi, input_bval, input_bvec, output_dir, fit_type='', mask='', bmax='', mask_tensor='T'):

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    img = nib.load(input_dwi)
    data = img.get_fdata()
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)

    if mask != '':
        mask_data = nib.load(mask).get_fdata()

    aff = img.affine
    sform = img.get_sform()
    qform = img.get_qform()

    if bmax != "":
        jj = np.where(bvals >= bmax)
        bvals = np.delete(bvals, jj)
        bvecs = np.delete(bvecs, jj, 0)
        data = np.delete(data, jj, axis=3)

    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]
    b0_average = np.mean(data[:, :, :, ii], axis=3)

    gtab = gradient_table(bvals, bvecs)

    if fit_type == 'RESTORE':
        sigma = estimate_sigma(data)
        # calculate the average sigma from the b0's
        sigma = np.mean(sigma[ii])

        dti_model = dti.TensorModel(gtab, fit_method='RESTORE', sigma=sigma)

        if mask != '':
            dti_fit = dti_model.fit(data, mask_data)
        else:
            dti_fit = dti_model.fit(data)

    elif fit_type != 'RESTORE' and fit_type != '':
        dti_model = dti.TensorModel(gtab, fit_method=fit_type)

        if mask != '':
            dti_fit = dti_model.fit(data, mask_data)
        else:
            dti_fit = dti_model.fit(data)

    else:
        dti_model = dti.TensorModel(gtab)

        if mask != '':
            dti_fit = dti_model.fit(data, mask_data)
        else:
            dti_fit = dti_model.fit(data)

    estimate_data = dti_fit.predict(gtab, S0=b0_average)
    residuals = np.absolute(data - estimate_data)

    evecs = dti_fit.evecs.astype(np.float32)
    evals = dti_fit.evals.astype(np.float32)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    # Define output imgs
    output_evecs = output_dir + '/dti_eigenvectors.nii.gz'
    output_tensor = output_dir + '/dti_tensor.nii.gz'
    dti_tensor_spd = output_dir + '/dti_tensor_spd.nii.gz'
    output_tensor_norm = output_dir + '/dti_tensor_norm.nii.gz'
    dti_tensor_spd_masked = output_dir + '/dti_tensor_spd_masked.nii.gz'
    norm_mask = output_dir + '/norm_mask.nii.gz'
    output_V1 = output_dir + '/dti_V1.nii.gz'
    output_V2 = output_dir + '/dti_V2.nii.gz'
    output_V3 = output_dir + '/dti_V3.nii.gz'
    output_L1 = output_dir + '/dti_L1.nii.gz'
    output_L2 = output_dir + '/dti_L2.nii.gz'
    output_L3 = output_dir + '/dti_L3.nii.gz'

    output_fa = output_dir + '/dti_FA.nii.gz'
    output_md = output_dir + '/dti_MD.nii.gz'
    output_rd = output_dir + '/dti_RD.nii.gz'
    output_ad = output_dir + '/dti_AD.nii.gz'

    output_res = output_dir + '/dti_residuals.nii.gz'

    evecs_img = nib.Nifti1Image(evecs, img.get_affine(), img.header)
    nib.save(evecs_img, output_evecs)

    dti_V1 = evecs[:, :, :, :, 0]
    V1_img = nib.Nifti1Image(dti_V1, aff, img.header)
    V1_img.set_sform(sform)
    V1_img.set_qform(qform)
    nib.save(V1_img, output_V1)

    dti_V2 = evecs[:, :, :, :, 1]
    V2_img = nib.Nifti1Image(dti_V2, aff, img.header)
    V2_img.set_sform(sform)
    V2_img.set_qform(qform)
    nib.save(V2_img, output_V2)

    dti_V3 = evecs[:, :, :, :, 2]
    V3_img = nib.Nifti1Image(dti_V3, aff, img.header)
    V3_img.set_sform(sform)
    V3_img.set_qform(qform)
    nib.save(V3_img, output_V3)

    dti_L1 = evals[:, :, :, 0]
    L1_img = nib.Nifti1Image(dti_L1, aff, img.header)
    L1_img.set_sform(sform)
    L1_img.set_qform(qform)
    nib.save(L1_img, output_L1)

    dti_L2 = evals[:, :, :, 1]
    L2_img = nib.Nifti1Image(dti_L2, aff, img.header)
    L2_img.set_sform(sform)
    L2_img.set_qform(qform)
    nib.save(L2_img, output_L2)

    dti_L3 = evals[:, :, :, 2]
    L3_img = nib.Nifti1Image(dti_L3, aff, img.header)
    L3_img.set_sform(sform)
    L3_img.set_qform(qform)
    nib.save(L3_img, output_L3)

    res_img = nib.Nifti1Image(residuals.astype(np.float32), aff, img.header)
    res_img.set_sform(sform)
    res_img.set_qform(qform)
    nib.save(res_img, output_res)

    os.chdir(output_dir)
    os.system('TVFromEigenSystem -basename dti -type FSL -out ' + output_tensor)
    os.system('TVtool -in ' + output_tensor + ' -scale 1000.00 -out ' + output_tensor)
    os.system('rm -rf dti_V* dti_L*')

    # Create the SPD
    os.system('TVtool -in ' + output_tensor + ' -spd -out ' + dti_tensor_spd)

    if mask_tensor == 'T':
        os.system('TVtool -in ' + dti_tensor_spd + ' -norm -out ' + output_tensor_norm)
        os.system('BinaryThresholdImageFilter ' + output_tensor_norm + ' ' + norm_mask + ' 0.01 3.0 1 0')
        os.system('TVtool -in ' + dti_tensor_spd + ' -mask ' + norm_mask + ' -out ' + dti_tensor_spd_masked)
        os.system('TVEigenSystem -in ' + dti_tensor_spd_masked + ' -type FSL')

        # Calculate Eigenvectors and Eigenvalues, FA, MD, RD, AD
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -fa -out ' + output_fa)
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -rd -out ' + output_rd)
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -ad -out ' + output_ad)
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -tr -out ' + output_md)
        os.system('fslmaths ' + output_md + ' -div 3.0 ' + output_md)

    else:
        # Calculate FA, MD, RD, AD
        os.system('TVEigenSystem -in ' + dti_tensor_spd + ' -type FSL')
        os.system('TVtool -in ' + dti_tensor_spd + ' -fa -out ' + output_fa)
        os.system('TVtool -in ' + dti_tensor_spd + ' -rd -out ' + output_rd)
        os.system('TVtool -in ' + dti_tensor_spd + ' -ad -out ' + output_ad)
        os.system('TVtool -in ' + dti_tensor_spd + ' -tr -out ' + output_md)
        os.system('fslmaths ' + output_md + ' -div 3.0 ' + output_md)


def main(ses_dir):
    input_mif, mask_mif, output_dir, subjroot = loadsubj(ses_dir, out_dir)
    input_bval, input_bvec, input_dwi, input_mask = mif2nii(input_mif, mask_mif, output_dir, subjroot)
    fit_dti_dipy(input_dwi, str(input_bval), str(input_bvec), str(output_dir), fit_type='RESTORE', mask=str(input_mask), bmax='', mask_tensor='T')


bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed')
# ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-01') if Path(ses_dir / 'dwi').exists() if ses_dir.parents[0].name == 'sub-001')

ses_dir = bidsproc_dir / 'sub-001' / 'ses-01'

main(ses_dir)