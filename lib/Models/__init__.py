
#%% Setup
import string, os, sys, subprocess, shutil, time, webbrowser
from glob import glob

import numpy as np
#import matplotlib.pyplot as plt

#Neuroimaging Modules
import pathlib
import pydicom
import nibabel as nib
import dipy.reconst.dti as dti

from pathlib import Path, PosixPath
from dipy.segment.mask import median_otsu
from dipy.denoise.nlmeans import nlmeans
from dipy.denoise.noise_estimate import estimate_sigma
from dipy.core.gradients import gradient_table
from dipy.io import read_bvals_bvecs
from dipy.reconst.dti import fractional_anisotropy
#from dipy.external.fsl import write_bvals_bvecs
from dipy.io.bvectxt import reorient_vectors

from lib.Utils.PNGViewer.PNGViewer import PNGViewer

#%%
input_dwi = "/scratch/jdrussell3/dipytest/sub-023_ses-01_eddycorr.nii.gz"
input_bval = "/scratch/jdrussell3/dipytest/sub-023_ses-01_dwi.bval"
input_bvec = "/scratch/jdrussell3/dipytest/sub-023_ses-01_eddycorr.bvec"
output_dir = "/scratch/jdrussell3/dipytest/dti_model"
mask = "/scratch/jdrussell3/dipytest/meanb0_brain_mask.nii.gz"

#%%
def fit_dti_model(input_dwi, input_bval, input_bvec, output_dir, fit_type='', mask='', bmax='', mask_tensor='T'):
    
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

    #Remove volumes with b > bmax
    if bmax != "":
        jj = np.where(bvals >= bmax)
        bvals = np.delete(bvals, jj)
        bvecs = np.delete(bvecs, jj, 0)
        data = np.delete(data, jj , axis=3)

    #Get a mean b0 volume
    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]
    b0_average = np.mean(data[:,:,:,ii], axis=3)

    #Convert bvals and bvecs to a dipy gradient table
    gtab = gradient_table(bvals, bvecs)

    #Lots of different options for tensor fitting algorithms ('fit_type')
    #See: https://dipy.org/documentation/1.0.0./reference/dipy.reconst/#dipy.reconst.dti.TensorModel
    if fit_type == 'RESTORE':
        #Get the standard deviation of the noise in each volume
        sigma = estimate_sigma(data)

        #Calculate the average sigma from the b0's (???)
        sigma = 2.00*np.mean(sigma[ii])

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

    evecs_img = nib.Nifti1Image(evecs, img.affine, img.header)
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



#See: https://www.sciencedirect.com/science/article/pii/S1053811918307419

#%%
mrtrix3tissue = Path("/Volumes/Users/jdrussell3/apps/MRtrix3Tissue/bin")

dwi_pre = "sub-023_ses-01"
input_dir = Path("/scratch/jdrussell3/mrtrix3")
input_dwi = Path(input_dir,str(dwi_pre + "_preproc_dwi.nii"))
input_bval = Path(input_dir,str(dwi_pre + "_dwi.bval"))
input_bvec = Path(input_dir, str(dwi_pre + "_dwi.bvec"))

output_dir = "/scratch/jdrussell3/mrtrix3"
output_dir_eddyqc = Path(output_dir, "eddy_qc")
temp_dir = "/tmp"
eddy_options = "'--verbose --slm=linear '"

dwi_raw = Path(output_dir, str(dwi_pre + "_dwi.mif"))
dwi_den = Path(output_dir, str(dwi_pre + "_dwi_den.mif"))
dwi_den_deg = Path(output_dir, str(dwi_pre + "_dwi_den_deg.mif"))
dwi_den_deg_preproc = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc.mif"))
dwi_den_deg_preproc_unb = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb.mif"))
dwi_den_deg_preproc_unb_b0s = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_b0s.mif"))
dwi_den_deg_preproc_unb_meanb0 = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0.mif"))
dwi_den_deg_preproc_unb_meanb0NII = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0.nii"))
dwi_den_deg_preproc_unb_meanb0maskroot = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0"))
dwi_den_deg_preproc_unb_meanb0maskNIIGZ = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0_mask.nii.gz"))
dwi_den_deg_preproc_unb_meanb0mask = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0_mask.mif"))
dwi_den_deg_preproc_unb_meanb0mask_templ = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0_mask_templ.mif"))
dwi_den_deg_preproc_unb_meanb0mask_ups = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0_mask_ups.mif"))
response_wm = Path(output_dir, str(dwi_pre + "_response_wm.txt"))
response_gm = Path(output_dir, str(dwi_pre + "_response_gm.txt"))
response_csf = Path(output_dir, str(dwi_pre + "_response_csf.txt"))
wmfod = Path(output_dir, str(dwi_pre + "_wmfod.mif"))
gmfod = Path(output_dir, str(dwi_pre + "_gmfod.mif"))
csffod = Path(output_dir, str(dwi_pre + "_csffod.mif"))
wmfod_norm = Path(output_dir, str(dwi_pre + "_wmfod_norm.mif"))
gmfod_norm = Path(output_dir, str(dwi_pre + "_gmfod_norm.mif"))
csffod_norm = Path(output_dir, str(dwi_pre + "_csffod_norm.mif"))

group_average_response = Path(output_dir, "sub-023_ses-01_response.txt")
output_fod = Path(output_dir, "sub-023_ses-01_fod.mif")
mask = "/scratch/jdrussell3/dipytest/meanb0_brain_mask.nii.gz"
mask_template = "/scratch/jdrussell/"



#%%
def mrtrix_preproc(input_dir, output_dir, dwi_pre, eddy_options):
    #Setting variables for processing
    dwi_raw = Path(output_dir, str(dwi_pre + "_dwi.mif"))
    dwi_den = Path(output_dir, str(dwi_pre + "_dwi_den.mif"))
    dwi_den_deg = Path(output_dir, str(dwi_pre + "_dwi_den_deg.mif"))
    dwi_den_deg_preproc = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc.mif"))
    dwi_den_deg_preproc_unb = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb.mif"))
    dwi_den_deg_preproc_unb_b0s = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_b0s.mif"))
    dwi_den_deg_preproc_unb_meanb0 = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0.mif"))
    dwi_den_deg_preproc_unb_meanb0NII = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0.nii"))
    dwi_den_deg_preproc_unb_meanb0maskroot = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0"))
    dwi_den_deg_preproc_unb_meanb0maskNIIGZ = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0_mask.nii.gz"))
    dwi_den_deg_preproc_unb_meanb0mask = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0_mask.mif"))
    dwi_den_deg_preproc_unb_meanb0mask_templ = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0_mask_templ.mif"))
    dwi_den_deg_preproc_unb_meanb0mask_ups = Path(output_dir, str(dwi_pre + "_dwi_den_deg_preproc_unb_meanb0_mask_ups.mif"))
    response_wm = Path(output_dir, str(dwi_pre + "_response_wm.txt"))
    response_gm = Path(output_dir, str(dwi_pre + "_response_gm.txt"))
    response_csf = Path(output_dir, str(dwi_pre + "_response_csf.txt"))
    wmfod = Path(output_dir, str(dwi_pre + "_wmfod.mif"))
    gmfod = Path(output_dir, str(dwi_pre + "_gmfod.mif"))
    csffod = Path(output_dir, str(dwi_pre + "_csffod.mif"))
    wmfod_norm = Path(output_dir, str(dwi_pre + "_wmfod_norm.mif"))
    gmfod_norm = Path(output_dir, str(dwi_pre + "_gmfod_norm.mif"))
    csffod_norm = Path(output_dir, str(dwi_pre + "_csffod_norm.mif"))
    #1. Convert to MIF - assumes denoising/deringing already done.
    !mrconvert -force -nthreads 12 -fslgrad $input_bvec $input_bval $input_dwi $dwi_den_deg
    #2. Denoise
    !dwidenoise -force -nthreads 12 $dwi_raw $dwi_den
    #3. Remove Gibbs rings
    !mrdegibbs -force -nthreads 12 $dwi_den $dwi_den_deg
    #4. Preprocess
    !dwipreproc -force -info -nthreads 12 $dwi_den_deg $dwi_den_deg_preproc -pe_dir AP -rpe_none -tempdir $temp_dir -eddy_options $eddy_options -eddyqc_all $output_dir_eddyqc
    #5. Bias correction
    !dwibiascorrect -force -nthreads 12 -ants $dwi_den_deg_preproc $dwi_den_deg_preproc_unb
    #6. Mask generation
    ##a. Extract b0s
    !dwiextract -force -nthreads 12 -bzero $dwi_den_deg_preproc_unb $dwi_den_deg_preproc_unb_b0s
    ##b. Compute mean b0
    !mrmath -force -nthreads 12 -axis 3 $dwi_den_deg_preproc_unb_b0s mean $dwi_den_deg_preproc_unb_meanb0
    ##c. Convert mean b0 to NII
    !mrconvert -force -nthreads 12 $dwi_den_deg_preproc_unb_meanb0 $dwi_den_deg_preproc_unb_meanb0NII
    ##d. Create maskk
    !bet2 $dwi_den_deg_preproc_unb_meanb0NII $dwi_den_deg_preproc_unb_meanb0maskroot -m
    ##e. Convert mask back to MIF
    !mrconvert -force -nthreads 12 $dwi_den_deg_preproc_unb_meanb0maskNIIGZ $dwi_den_deg_preproc_unb_meanb0mask

#%%
def mrtrix_fit():
    #7. Generate 3-tissue response function
    !dwi2response dhollander $dwi_den_deg_preproc_unb $response_wm $response_gm $response_csf
    #8. Upsampling
    #a. Upsampling data
    %%run
    !/Volumes/Users/jdrussell3/apps/MRtrix3Tissue/bin/mrgrid $dwi_den_deg_preproc_unb regrid $dwi_den_deg_preproc_unb_ups -voxel 1      
    #b. Upsampling mask
    !/Volumes/Users/jdrussell3/apps/MRtrix3Tissue/bin/mrgrid $dwi_den_deg_preproc_unb_meanb0mask regrid $dwi_den_deg_preproc_unb_meanb0mask_templ -template $dwi_den_deg_preproc_unb_ups -interp linear -datatype bit 
    #c. Filtering mask
    !/Volumes/Users/jdrussell3/apps/MRtrix3Tissue/bin/maskfilter $dwi_den_deg_preproc_unb_meanb0mask_templ median $dwi_den_deg_preproc_unb_meanb0mask_ups

    ##!!!!!!!!!!STOP!!!!!!!!!!##
    #Generate response functions for each subject, then average them together
  
#%%
def mrtrix_group():
    #9. 3-Tissue Constrained Spherical Deconvolution for Single-Shell data
    !/Volumes/Users/jdrussell3/apps/MRtrix3Tissue/bin/ss3t_csd_beta1 $dwi_den_deg_preproc_unb_ups $response_wm $wmfod $response_gm $gmfod $response_csf $csffod -mask $dwi_den_deg_preproc_unb_meanb0mask_ups
    #10. 3-Tissue Bias Field Correction/Global Intensity Normalisation
    !/Volumes/Users/jdrussell3/apps/MRtrix3Tissue/bin/mtnormalise $wmfod $wmfod_norm $gmfod $gmfod_norm $csffod $csffod_norm -mask $dwi_den_deg_preproc_unb_meanb0mask_ups

#%%
mrtrix_preproc(dwi_pre, eddy_options)

#%%
mrtrix_fit()

#%%
%%javascript
Jupyter.notebook.execute_cells([0])

#%%
def dti_review(subject_id, input_dwi, output_dir):
    review_dir = Path(output_dir, "manual_review")
    # if review_dir.exists():
    #     shutil.rmtree(review_dir)
    # print(review_dir)
    # review_dir.mkdir()
    # review_dir_baseout = str(review_dir) + "/img_"

    # !fslsplit $input_dwi $review_dir_baseout -t
    # niis = review_dir.glob('*.nii*')
    # for nii in niis:
    #     slice = nii.stem.split('.')[0]
    #     outputPNG = Path(review_dir, str(slice + '.png'))
    #     print("Exporting slice image: " + str(outputPNG))
    #     !slicer $nii -L -a $outputPNG 
    png_viewer = PNGViewer(str(review_dir), subject_id)
    png_viewer.writeHTML()

    #png_viewer.runPNGViewer()


#%%
dti_review('23', input_dwi, output_dir)


#%%
