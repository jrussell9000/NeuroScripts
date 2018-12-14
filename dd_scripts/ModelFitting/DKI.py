import string, os, sys, subprocess, shutil, time

#Neuroimaging Modules
import nibabel as nib
import numpy as np
from dipy.core.gradients import gradient_table
from dipy.io import read_bvals_bvecs
import dipy.reconst.dki as dki
import scipy.ndimage.filters as filters


def fit_dki_dipy(input_dwi, input_bval, input_bvec, output_dir, fit_method='', mask='', include_micro_fit='FALSE'):

    if fit_method == '':
        fit_method = 'OLS'

    img = nib.load(input_dwi)
    data = img.get_data()
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec,)
    gtab = gradient_table(bvals, bvecs)
    
    if mask != '':
        mask_data = nib.load(mask).get_data()

    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]
    b0_average = np.mean(data[:,:,:,ii], axis=3)

    #Recommended to smooth data prior to fitting:
    fwhm = 2.00
    gauss_std = fwhm / np.sqrt(8 * np.log(2))  # converting fwhm to Gaussian std
    data_smooth = np.zeros(data.shape)
    for v in range(data.shape[-1]):
        data_smooth[..., v] = filters.gaussian_filter(data[..., v], sigma=gauss_std)

    dkimodel = dki.DiffusionKurtosisModel(gtab, fit_method)

    if mask != '':
        dkifit = dkimodel.fit(data_smooth, mask_data)
    else:
        dkifit = dkimodel.fit(data_smooth)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    output_evecs = output_dir + '/dki_eigenvectors.nii.gz'
    output_evals = output_dir + '/dki_eigenvalues.nii.gz'

    output_fa = output_dir + '/dki_FA.nii.gz'
    output_md = output_dir + '/dki_MD.nii.gz'
    output_rd = output_dir + '/dki_RD.nii.gz'
    output_ad = output_dir + '/dki_AD.nii.gz'
    output_mk = output_dir + '/dki_MK.nii.gz'
    output_ak = output_dir + '/dki_AK.nii.gz'
    output_rk = output_dir + '/dki_RK.nii.gz'

    #Calculate Parameters for Kurtosis Model
    evals_img = nib.Nifti1Image(dkifit.evals.astype(np.float32), img.get_affine(),img.header)
    nib.save(evals_img, output_evals)
    os.system('fslreorient2std ' + output_evals+ ' ' + output_evals)

    evecs_img = nib.Nifti1Image(dkifit.evecs.astype(np.float32), img.get_affine(),img.header)
    nib.save(evecs_img, output_evecs)
    os.system('fslreorient2std ' + output_evecs+ ' ' + output_evecs)

    dki_fa = dkifit.fa
    dki_fa_img = nib.Nifti1Image(dki_fa.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_fa_img, output_fa)
    os.system('fslreorient2std ' + output_fa+ ' ' + output_fa)

    dki_md = dkifit.md
    dki_md_img = nib.Nifti1Image(dki_md.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_md_img, output_md)
    os.system('fslreorient2std ' + output_md+ ' ' + output_md)

    dki_ad = dkifit.ad
    dki_ad_img = nib.Nifti1Image(dki_ad.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_ad_img, output_ad)
    os.system('fslreorient2std ' + output_ad+ ' ' + output_ad)

    dki_rd = dkifit.rd
    dki_rd_img = nib.Nifti1Image(dki_rd.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_rd_img, output_rd)
    os.system('fslreorient2std ' + output_rd+ ' ' + output_rd)

    MK = dkifit.mk(0, 3)
    AK = dkifit.ak(0, 3)
    RK = dkifit.rk(0, 3)

    dki_mk_img = nib.Nifti1Image(MK.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_mk_img, output_mk)
    os.system('fslreorient2std ' + output_mk+ ' ' + output_mk)

    dki_ak_img = nib.Nifti1Image(AK.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_ak_img, output_ak)
    os.system('fslreorient2std ' + output_ak+ ' ' + output_ak)

    dki_rk_img = nib.Nifti1Image(RK.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_rk_img, output_rk)
    os.system('fslreorient2std ' + output_rk+ ' ' + output_rk)

    if include_micro_fit == 'TRUE':
        
        import dipy.reconst.dki_micro as dki_micro
        well_aligned_mask = np.ones(data.shape[:-1], dtype='bool')

        # Diffusion coefficient of linearity (cl) has to be larger than 0.4, thus
        # we exclude voxels with cl < 0.4.
        cl = dkifit.linearity.copy()
        well_aligned_mask[cl < 0.4] = False

        # Diffusion coefficient of planarity (cp) has to be lower than 0.2, thus
        # we exclude voxels with cp > 0.2.
        cp = dkifit.planarity.copy()
        well_aligned_mask[cp > 0.2] = False

        # Diffusion coefficient of sphericity (cs) has to be lower than 0.35, thus
        # we exclude voxels with cs > 0.35.
        cs = dkifit.sphericity.copy()
        well_aligned_mask[cs > 0.35] = False

        # Removing nan associated with background voxels
        well_aligned_mask[np.isnan(cl)] = False
        well_aligned_mask[np.isnan(cp)] = False
        well_aligned_mask[np.isnan(cs)] = False

        dki_micro_model = dki_micro.KurtosisMicrostructureModel(gtab, fit_method)
        dki_micro_fit = dki_micro_model.fit(data_smooth, mask=well_aligned_mask)

        output_awf = output_dir + '/dki_micro_AWF.nii.gz'
        output_tort = output_dir + '/dki_micro_TORT.nii.gz'
        dki_micro_awf = dki_micro_fit.awf
        dki_micro_tort = dki_micro_fit.tortuosity

        dki_micro_awf_img = nib.Nifti1Image(dki_micro_awf.astype(np.float32), img.get_affine(),img.header)
        nib.save(dki_micro_awf_img, output_awf)
        os.system('fslreorient2std ' + output_awf+ ' ' + output_awf)

        dki_micro_tort_img = nib.Nifti1Image(dki_micro_tort.astype(np.float32), img.get_affine(),img.header)
        nib.save(dki_micro_tort_img, output_tort)
        os.system('fslreorient2std ' + output_tort+ ' ' + output_awf)


