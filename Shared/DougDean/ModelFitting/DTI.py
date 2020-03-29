import string, os, sys, subprocess, shutil, time

import numpy as np
import nibabel as nib
import dipy.reconst.dti as dti

from dipy.denoise.noise_estimate import estimate_sigma
from dipy.core.gradients import gradient_table
from dipy.io import read_bvals_bvecs
from dipy.reconst.dti import fractional_anisotropy

def fit_dti_dipy(input_dwi, input_bval, input_bvec, output_dir, fit_type='', mask='', bmax='', mask_tensor='T'):

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    img = nib.load(input_dwi)
    data = img.get_data()
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)

    if mask != '':
        mask_data = nib.load(mask).get_data()

    aff = img.get_affine()
    sform = img.get_sform()
    qform = img.get_qform()

    if bmax != "":
        jj = np.where(bvals >= bmax)
        bvals = np.delete(bvals, jj)
        bvecs = np.delete(bvecs, jj, 0)
        data = np.delete(data, jj , axis=3)

    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]
    b0_average = np.mean(data[:,:,:,ii], axis=3)

    gtab = gradient_table(bvals, bvecs)

    if fit_type == 'RESTORE':
        sigma = estimate_sigma(data)
        #calculate the average sigma from the b0's
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

    #Define output imgs
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

    dti_V1 = evecs[:,:,:,:,0]
    V1_img = nib.Nifti1Image(dti_V1,aff,img.header)
    V1_img.set_sform(sform)
    V1_img.set_qform(qform)
    nib.save(V1_img, output_V1)

    dti_V2 = evecs[:,:,:,:,1]
    V2_img = nib.Nifti1Image(dti_V2,aff,img.header)
    V2_img.set_sform(sform)
    V2_img.set_qform(qform)
    nib.save(V2_img, output_V2)

    dti_V3 = evecs[:,:,:,:,2]
    V3_img = nib.Nifti1Image(dti_V3,aff,img.header)
    V3_img.set_sform(sform)
    V3_img.set_qform(qform)
    nib.save(V3_img, output_V3)

    dti_L1 = evals[:,:,:,0]
    L1_img = nib.Nifti1Image(dti_L1,aff,img.header)
    L1_img.set_sform(sform)
    L1_img.set_qform(qform)
    nib.save(L1_img, output_L1)

    dti_L2 = evals[:,:,:,1]
    L2_img = nib.Nifti1Image(dti_L2,aff,img.header)
    L2_img.set_sform(sform)
    L2_img.set_qform(qform)
    nib.save(L2_img, output_L2)

    dti_L3 = evals[:,:,:,2]
    L3_img = nib.Nifti1Image(dti_L3,aff,img.header)
    L3_img.set_sform(sform)
    L3_img.set_qform(qform)
    nib.save(L3_img, output_L3)

    res_img = nib.Nifti1Image(residuals.astype(np.float32), aff,img.header)
    res_img.set_sform(sform)
    res_img.set_qform(qform)
    nib.save(res_img, output_res)

    os.chdir(output_dir)
    os.system('TVFromEigenSystem -basename dti -type FSL -out ' + output_tensor)
    os.system('TVtool -in ' + output_tensor + ' -scale 1000.00 -out ' + output_tensor)
    os.system('rm -rf dti_V* dti_L*')

    #Create the SPD
    os.system('TVtool -in ' + output_tensor + ' -spd -out ' + dti_tensor_spd)

    if mask_tensor == 'T':
        os.system('TVtool -in ' + dti_tensor_spd + ' -norm -out ' + output_tensor_norm)
        os.system('BinaryThresholdImageFilter ' +  output_tensor_norm + ' ' + norm_mask + ' 0.01 3.0 1 0')
        os.system('TVtool -in ' + dti_tensor_spd + ' -mask ' + norm_mask + ' -out ' + dti_tensor_spd_masked)
        os.system('TVEigenSystem -in ' + dti_tensor_spd_masked + ' -type FSL')

        #Calculate Eigenvectors and Eigenvalues, FA, MD, RD, AD
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -fa -out ' + output_fa)
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -rd -out ' + output_rd)
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -ad -out ' + output_ad)
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -tr -out ' + output_md)
        os.system('fslmaths ' + output_md + ' -div 3.0 ' + output_md)

    else:
        #Calculate FA, MD, RD, AD
        os.system('TVEigenSystem -in ' + dti_tensor_spd + ' -type FSL')
        os.system('TVtool -in ' + dti_tensor_spd + ' -fa -out ' + output_fa)
        os.system('TVtool -in ' + dti_tensor_spd + ' -rd -out ' + output_rd)
        os.system('TVtool -in ' + dti_tensor_spd + ' -ad -out ' + output_ad)
        os.system('TVtool -in ' + dti_tensor_spd + ' -tr -out ' + output_md)
        os.system('fslmaths ' + output_md + ' -div 3.0 ' + output_md)

def fit_dti_mrtrix(input_dwi, input_bval, input_bvec, output_dir, mask='', bmax=''):
    
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    output_tensor = output_dir + '/dti_tensor.nii.gz'
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
    
    if bmax!='':
        img = nib.load(input_dwi)
        data = img.get_data()
        bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)

        aff = img.get_affine()
        sform = img.get_sform()
        qform = img.get_qform()
    
        jj = np.where(bvals >= bmax)
        bvals = np.delete(bvals, jj)
        bvecs = np.delete(bvecs, jj, 0)
        data = np.delete(data, jj , axis=3)

        #Save the dwi data
        tmp_dwi_img = nib.Nifti1Image(data,aff,img.header)
        tmp_dwi_img.set_sform(sform)
        tmp_dwi_img.set_qform(qform)
        nib.save(tmp_dwi_img, output_dir+'/tmp_dwi.nii.gz')
        np.savetxt(output_dir+'/tmp_bvals.bval', bvals, fmt='%i')
        np.savetxt(output_dir+'/tmp_bvecs.bvec', np.transpose(bvecs), fmt='%.5f')

        #Run the tensor fitting using MRTRIX:
        command = 'dwi2tensor -fslgrad ' + output_dir+'/tmp_bvecs.bvec ' + output_dir+'/tmp_bvals.bval ' + output_dir+'/tmp_dwi.nii.gz ' + output_tensor

    else:
        command = 'dwi2tensor -fslgrad ' + input_bvec + ' ' +  input_bval + ' ' + input_dwi + ' ' + output_tensor

    if mask!='':
        os.system(command+' -mask ' + mask)
    else:
        os.system(command)

    #Write out the parameters
    os.system('tensor2metric -adc ' + output_md + ' ' + output_tensor)
    os.system('tensor2metric -fa ' + output_fa + ' ' + output_tensor)
    os.system('tensor2metric -ad ' + output_ad + ' ' + output_tensor)
    os.system('tensor2metric -rd ' + output_rd + ' ' + output_tensor)


    os.system('tensor2metric -value ' + output_L1 + ' -num 1 ' + output_tensor)
    os.system('tensor2metric -value ' + output_L2 + ' -num 2 ' + output_tensor)
    os.system('tensor2metric -value ' + output_L3 + ' -num 3 ' + output_tensor)

    os.system('tensor2metric -vector ' + output_V1 + ' -num 1 ' + output_tensor)
    os.system('tensor2metric -vector ' + output_V2 + ' -num 2 ' + output_tensor)
    os.system('tensor2metric -vector ' + output_V3 + ' -num 3 ' + output_tensor)

    os.system('rm -rf ' + output_dir + '/tmp*')

def fit_dti_camino(input_dwi, input_bval, input_bvec, output_dir, fit_type='', mask='', bmax=''):
    
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    #First create temporary camino style data
    camino_dwi = output_dir + '/tmp_dwi.Bfloat'
    camino_scheme = output_dir + '/tmp_dwi.scheme'
    camino_tensor = output_dir + '/tmp_dti.Bfloat'
    os.system('image2voxel -4dimage ' + input_dwi + ' -outputfile ' + camino_dwi)
    os.system('fsl2scheme -bvecfile ' + input_bvec + ' -bvalfile ' + input_bval + ' > ' + camino_scheme)

    if fit_type == 'RESTORE':
        data = nib.load(input_dwi).get_data()
        bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
        values = np.array(bvals)
        ii = np.where(values == bvals.min())[0]
        sigma = estimate_sigma(data)
        sigma = np.mean(sigma[ii])

        #FIT TENSOR
        os.system('modelfit -inputfile ' + camino_dwi + ' -schemefile ' + camino_scheme + ' -model restore -sigma ' + str(sigma) + ' -bgmask ' + mask + ' -outputfile ' + camino_tensor)

    elif fit_type == 'WLLS':
        os.system('modelfit -inputfile ' + camino_dwi + ' -schemefile ' + camino_scheme + ' -model ldt_wtd -bgmask ' + mask + ' -outputfile ' + camino_tensor)
                  
    elif fit_type == 'NLLS':
        os.system('modelfit -inputfile ' + camino_dwi + ' -schemefile ' + camino_scheme + ' -model nldt_pos -bgmask ' + mask + ' -outputfile ' + camino_tensor)
                  
    else:
        os.system('modelfit -inputfile ' + camino_dwi + ' -schemefile ' + camino_scheme + ' -model ldt -bgmask ' + mask + ' -outputfile ' + camino_tensor)
                
    #Convert the data back to NIFTI
    output_root = output_dir + 'dti_'
    os.system('dt2nii -inputfile ' + camino_tensor + ' -gzip -inputdatatype double -header ' + input_dwi + ' -outputroot ' + output_root)

    #Define the output file paths
    output_tensor = output_dir + '/dti_tensor.nii.gz'
    output_tensor_spd = output_dir + '/dti_tensor_spd.nii.gz'
    output_tensor_norm = output_dir + '/dti_tensor_norm.nii.gz'
    norm_mask = output_dir + '/norm_mask.nii.gz'
    output_tensor_spd_masked = output_dir + '/dti_tensor_spd_masked.nii.gz'

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

    os.system('TVtool -in ' + output_root + 'dt.nii.gz -scale 1e9 -out ' + output_tensor)
    os.system('TVtool -in ' + output_tensor + ' -spd -out ' + output_tensor_spd)
    os.system('TVtool -in ' + output_tensor_spd + ' -norm -out ' + output_tensor_norm)
    os.system('BinaryThresholdImageFilter ' +  output_tensor_norm + ' ' + norm_mask + ' 0.01 3.0 1 0')
    os.system('TVtool -in ' + output_tensor_spd + ' -mask ' + norm_mask + ' -out ' + output_tensor_spd_masked)
    os.system('TVFromEigenSystem -basename dti -type FSL -out ' + output_tensor_spd_masked)

    #Calculate FA, MD, RD, AD
    os.system('TVtool -in ' + output_tensor_spd_masked + ' -fa -out ' + output_fa)
    os.system('TVtool -in ' + output_tensor_spd_masked + ' -rd -out ' + output_rd)
    os.system('TVtool -in ' + output_tensor_spd_masked + ' -ad -out ' + output_ad)
    os.system('TVtool -in ' + output_tensor_spd_masked + ' -tr -out ' + output_md)
    os.system('fslmaths ' + output_md + ' -div 3.00 ' + output_md)

    #Output the eigenvectors and eigenvalues
    os.system('TVEigenSystem -in ' + output_tensor_spd_masked + ' -type FSL')
    dti_basename=nib.filename_parser.splitext_addext(output_tensor_spd_masked)[0]
    os.system('mv ' + dti_basename + '_V1.nii.gz ' + output_V1)
    os.system('mv ' + dti_basename + '_V2.nii.gz ' + output_V2)
    os.system('mv ' + dti_basename + '_V3.nii.gz ' + output_V3)
    os.system('mv ' + dti_basename + '_L1.nii.gz ' + output_L1)
    os.system('mv ' + dti_basename + '_L2.nii.gz ' + output_L2)
    os.system('mv ' + dti_basename + '_L3.nii.gz ' + output_L3)

    #Clean up files
    os.system('rm -rf ' + dti_basename +'_[V,L]* ' + output_dir + '/tmp*')


def fit_fwdti_dipy(input_dwi, input_bval, input_bvec, output_dir, fit_method='', mask=''):

    import dipy.reconst.fwdti as fwdti
    
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    if fit_method=='':
        fit_method = 'WLS'

    img = nib.load(input_dwi)
    data = img.get_data()
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec,)
    gtab = gradient_table(bvals, bvecs)

    if mask != '':
        mask_data = nib.load(mask).get_data()

    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]
    b0_average = np.mean(data[:,:,:,ii], axis=3)
    
    fwidtimodel = fwdti.FreeWaterTensorModel(gtab, fit_method)

    if mask!='':
        fwidti_fit = fwidtimodel.fit(data, mask_data)
    else:
        fwidti_fit = fwidtimodel.fit(data)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    output_evecs = output_dir + '/fwe_dti_eigenvectors.nii.gz'
    output_evals = output_dir + '/fwe_dti_eigenvalues.nii.gz'

    output_fa = output_dir + '/fwe_dti_FA.nii.gz'
    output_md = output_dir + '/fwe_dti_MD.nii.gz'
    output_rd = output_dir + '/fwe_dti_RD.nii.gz'
    output_ad = output_dir + '/fwe_dti_AD.nii.gz'
    output_f = output_dir + '/fwe_dti_F.nii.gz'

    #Calculate Parameters for FWDTI Model
    evals_img = nib.Nifti1Image(fwidti_fit.evals.astype(np.float32), img.get_affine(),img.header)
    nib.save(evals_img, output_evals)
    os.system('fslreorient2std ' + output_evals + ' ' + output_evals)
    
    evecs_img = nib.Nifti1Image(fwidti_fit.evecs.astype(np.float32), img.get_affine(),img.header)
    nib.save(evecs_img, output_evecs)
    os.system('fslreorient2std ' + output_evecs+ ' ' + output_evecs)
    
    fwidti_fa = fwidti_fit.fa
    fwidti_fa_img = nib.Nifti1Image(fwidti_fa.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_fa_img, output_fa)
    os.system('fslreorient2std ' + output_fa + ' ' + output_fa)
    
    fwidti_md = fwidti_fit.md
    fwidti_md_img = nib.Nifti1Image(fwidti_md.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_md_img, output_md)
    os.system('fslreorient2std ' + output_md+ ' ' + output_md)

    fwidti_ad = fwidti_fit.ad
    fwidti_ad_img = nib.Nifti1Image(fwidti_ad.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_ad_img, output_ad)
    os.system('fslreorient2std ' + output_ad+ ' ' + output_ad)
    
    fwidti_rd = fwidti_fit.rd
    fwidti_rd_img = nib.Nifti1Image(fwidti_rd.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_rd_img, output_rd)
    os.system('fslreorient2std ' + output_rd+ ' ' + output_rd)

    fwidti_f = fwidti_fit.f
    fwidti_f_img = nib.Nifti1Image(fwidti_f.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_f_img, output_f)
    os.system('fslreorient2std ' + output_f+ ' ' + output_f)

