import os,sys,shutil
import Utils as util
import DataCorrection as datacorr
import DistortionCorrection as distcorr
import EddyCorrection as eddycorr
import Masking as mask
import ModelFitting.DTI as dtifit
import ModelFitting.NODDI as noddifit

study_dir = '/study/dean_k99/Studies/hartwell/'
processingCode_dir = study_dir + 'ProcessingCode/'
processedDataDirectory = study_dir + 'AnalyzedSubjects/'

###DEFINE STUDY SPECIFIC PARAMETERS###
study_dwi_bvals = processingCode_dir + 'dwi_bvals.bval'
study_dwi_bvecs = processingCode_dir + 'dwi_bvecs.bvec'
study_dwi_index = processingCode_dir + 'dwi_index.txt'
study_dwi_acqparam = processingCode_dir + 'dwi_acqparams.txt'
study_b0s_bvals = processingCode_dir + 'b0s_bvals.bval'
study_b0s_bvecs = processingCode_dir + 'b0s_bvecs.bvec'
study_b0s_index = processingCode_dir + 'b0s_index.txt'
study_b0s_acqparam = processingCode_dir + 'b0s_acqparams.txt'

slice_order_file = processingCode_dir + 'slice_order_file.txt'
###########################

input = sys.argv[1:]
subject_id = input[0]
username = 'dean'

#AVAILABLE OPTIONS FOR DTI/FWE-DTI/DKI ALGORITHMS
#dti_fit_method: WLS, LS/OLS, NLLS, RESTORE
#fwe_fit_method: WLS, NLLS
#dki_fit_method: WLS, OLS

#Define directories and image paths
subj_proc_path = processedDataDirectory + subject_id + '/'
raw_data_dir = subj_proc_path+'/rawData/'
preprocess_dir = subj_proc_path+'/preprocessed/'
dti_wls_results_dir = subj_proc_path+'/DTI_WLS/'
dti_nls_results_dir = subj_proc_path+'/DTI_NLS/'
dti_restore_results_dir = subj_proc_path+'/DTI_RESTORE/'
dti_camino_wls_results_dir = subj_proc_path + '/DTI_CAMINO_WLS/'
dti_camino_restore_results_dir = subj_proc_path + '/DTI_CAMINO_RESTORE/'
dti_mrtrix_results_dir = subj_proc_path + '/DTI_MRTRIX/'
amico_results_dir = subj_proc_path+'/AMICO-NODDI/'

if not os.path.exists(subj_proc_path):
    os.mkdir(subj_proc_path)
if not os.path.exists(preprocess_dir):
    os.mkdir(preprocess_dir)

##################################
##################################
##### PROCESSING STARTS HERE #####
##################################
##################################

#First, merge the two PE_POLAR directions
input_dwi = raw_data_dir + 'dwi.nii.gz'
input_b0s = raw_data_dir + 'b0s.nii.gz'
output_dwi = preprocess_dir + 'dwi.nii.gz'
output_bvals = preprocess_dir + 'bvals.bval'
output_bvecs = preprocess_dir + 'bvecs.bvec'
output_index = preprocess_dir + 'index.txt'
output_acqparams = preprocess_dir + 'acqparams.txt'

if not os.path.exists(output_dwi):
    print 'Merging Multi-Phase Encoding Data...'
    util.merge_multiple_phase_encodes(input_dwi, study_dwi_bvals, study_dwi_bvecs, study_dwi_index, study_dwi_acqparam, input_b0s, study_b0s_bvals, study_b0s_bvecs, study_b0s_index, study_b0s_acqparam, output_dwi, output_bvals, output_bvecs, output_index, output_acqparams)

#Next, remove noise and then correct for Gibbs ringing
input_dwi = preprocess_dir + 'dwi.nii.gz'
output_dwi = preprocess_dir + 'dwi.denoise.nii.gz'
output_noise = preprocess_dir + 'noise.map.nii.gz'
if not os.path.exists(output_dwi):
    print 'Running Noise Correction..'
    datacorr.denoise_mrtrix(input_dwi, output_dwi, output_noise)

input_dwi = preprocess_dir + 'dwi.denoise.nii.gz'
output_dwi = preprocess_dir + 'dwi.denoise.gibbs.nii.gz'
if not os.path.exists(output_dwi):
    print 'Running Gibbs Correction...'
    datacorr.mrdegibbs_mrtrix(input_dwi, output_dwi)

#Run top-up
input_dwi = preprocess_dir + 'dwi.denoise.gibbs.nii.gz'
input_bvals = preprocess_dir + 'bvals.bval'
input_index = preprocess_dir + 'index.txt'
input_acqparams = preprocess_dir + 'acqparams.txt'
config_file = '/study/dean_k99/Studies/hartwell/ProcessingCode/b02b0.cnf'
output_topup_base = preprocess_dir + 'topup_results'
output_topup_field= preprocess_dir + 'topup_results_field'
if not os.path.exists(output_topup_field+'.nii.gz'):
    print 'Running Top-Up...'
    distcorr.topup_fsl(input_dwi, input_bvals,input_index, input_acqparams, output_topup_base, config_file, output_topup_field)

#Next, run EDDY with top-up results
input_dwi = preprocess_dir + 'dwi.denoise.gibbs.nii.gz'
input_bvals = preprocess_dir + 'bvals.bval'
input_bvecs = preprocess_dir + 'bvecs.bvec'
input_index = preprocess_dir + 'index.txt'
input_acqparams = preprocess_dir + 'acqparams.txt'
output_dwi = preprocess_dir + 'dwi.denoise.gibbs.eddy.nii.gz'
output_bvecs = preprocess_dir + 'bvecs_eddy.rotated.bvecs'
topup_base = preprocess_dir + 'topup_results'
external_b0=''
repol_option=1
data_shelled_option=1
mb_option=''
cuda_option='TRUE'
mporder=60
slice_order = slice_order_file
if not os.path.exists(output_dwi):
    print 'Running EDDY...'
    eddycorr.eddy_fsl(input_dwi, input_bvals, input_bvecs, input_index, input_acqparams, output_dwi, output_bvecs, topup_base, external_b0, repol_option, data_shelled_option, mb_option, cuda_option, mporder, slice_order)

#Next, remove outliers determined by EDDY and threshold of data to remove:
input_dwi = preprocess_dir + 'dwi.denoise.gibbs.eddy.nii.gz'
input_bvals = preprocess_dir + 'bvals.bval'
input_bvecs = preprocess_dir + 'bvecs_eddy.rotated.bvecs'
input_index = preprocess_dir + 'index.txt'
input_report_file = preprocess_dir + 'dwi.denoise.gibbs.eddy.eddy_outlier_map'
output_dwi = preprocess_dir + 'dwi.denoise.gibbs.eddy.corr.nii.gz'
output_bvals = preprocess_dir + 'corr_bvals.bval'
output_bvecs = preprocess_dir + 'corr_bvecs.bvec'
output_index = preprocess_dir + 'corr_index.txt'
output_removed_imgs_dir = preprocess_dir + '/removedImages'
method='Threshold'
percent_threshold = 0.15
if not os.path.exists(output_dwi):
    print 'Running Outlier Correction...'
    util.remove_outlier_imgs(input_dwi, input_bvals, input_bvecs, input_index, input_report_file, output_dwi, output_bvals, output_bvecs, output_index, output_removed_imgs_dir, method, percent_threshold)

#Create Mask
input_dwi = preprocess_dir + 'dwi.denoise.gibbs.eddy.corr.nii.gz'
input_bvals = preprocess_dir + 'corr_bvals.bval'
input_bvecs = preprocess_dir + 'corr_bvecs.bvec'
output_dwi = preprocess_dir + 'dwi.denoise.gibbs.eddy.corr.masked.nii.gz'
output_mask = preprocess_dir + 'mask.nii.gz'
if not os.path.exists(output_dwi):
    print 'Masking data...'
    mask.mask_mrtrix(input_dwi, input_bvals, input_bvecs, output_mask, output_dwi)


dti_wls_results_dir = subj_proc_path+'/DTI_WLS/'
dti_nls_results_dir = subj_proc_path+'/DTI_NLS/'
dti_restore_results_dir = subj_proc_path+'/DTI_RESTORE/'
dti_camino_wls_results_dir = subj_proc_path + '/DTI_CAMINO_WLS/'
dti_camino_restore_results_dir = subj_proc_path + '/DTI_CAMINO_RESTORE/'
dti_mrtrix_results_dir = subj_proc_path + '/DTI_MRTRIX/'

dti_model_fit_method = 'WLS'

if not os.path.exists(dti_wls_results_dir + 'dti_FA.nii.gz'):
    print 'Fitting tensor model with WLS...'
    input_mask = preprocess_dir + 'mask.nii.gz'
    dtifit.fit_dti_dipy(input_dwi, input_bvals, input_bvecs, dti_results_dir, dti_model_fit_method, input_mask)

if not os.path.exists(dti_wls_results_dir + 'dti_FA.nii.gz'):
    print 'Fitting tensor model with WLS...'
    input_mask = preprocess_dir + 'mask.nii.gz'
    dtifit.fit_dti_dipy(input_dwi, input_bvals, input_bvecs, dti_results_dir, dti_model_fit_method, input_mask)

if not os.path.exists(dti_wls_results_dir + 'dti_FA.nii.gz'):
    print 'Fitting tensor model with WLS...'
    input_mask = preprocess_dir + 'mask.nii.gz'
    dtifit.fit_dti_dipy(input_dwi, input_bvals, input_bvecs, dti_results_dir, dti_model_fit_method, input_mask)

if not os.path.exists(dti_wls_results_dir + 'dti_FA.nii.gz'):
    print 'Fitting tensor model with WLS...'
    input_mask = preprocess_dir + 'mask.nii.gz'
    dtifit.fit_dti_dipy(input_dwi, input_bvals, input_bvecs, dti_results_dir, dti_model_fit_method, input_mask)

if not os.path.exists(dti_wls_results_dir + 'dti_FA.nii.gz'):
    print 'Fitting tensor model with WLS...'
    input_mask = preprocess_dir + 'mask.nii.gz'
    dtifit.fit_dti_dipy(input_dwi, input_bvals, input_bvecs, dti_results_dir, dti_model_fit_method, input_mask)




if not os.path.exists(amico_results_dir + 'noddi_FICVF.nii.gz'):
    print 'Fitting AMICO-NODDI model...'
    noddifit.fit_noddi_amico(input_dwi, input_bvals, input_bvecs, input_mask, amico_results_dir)






