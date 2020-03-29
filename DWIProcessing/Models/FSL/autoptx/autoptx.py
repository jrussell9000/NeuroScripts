from pathlib import Path
import shutil, os, subprocess
import pandas as pd
from joblib import parallel_backend, delayed, Parallel

# 1. Iterate over each subject and session directory in BIDS_Processed.  For each
# subject/session with preprocessed DTI data (i.e., directory 'dwi' exists)...

autoptxproc_dir = Path("/Volumes/Vol6/YouthPTSD/autoptx")
bidsproc_dir = Path("/Volumes/Vol6/YouthPTSD/BIDS_Processed")

ses_dirs = lambda: (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-01')  # noqa: E731
                    if Path(ses_dir / 'dwi').exists())

# 2. Create NIFTI versions of the preprocessed scans and b0 brain masks, then copy these,
#    the bvals and bvecs to a new sub-XXX_ses-0Y directory. In the new directory, name the files
#    'data.nii' (dti), 'nodif_brain_mask.nii' (mask), 'bvals', and 'bvecs'.


def autoptx_prep(ses_dir):

    ses_dir = ses_dir
    subj_dir = ses_dir.parent
    preproc_dir = ses_dir / 'dwi' / 'preprocessed'
    subjroot = "_".join([subj_dir.name, ses_dir.name])

    input_dwi = preproc_dir / (subjroot + "_ppd.mif")
    input_dwimask = preproc_dir / (subjroot + "_mask_ppd.mif")
    input_bvals = preproc_dir / (subjroot + "_ppd.bval")
    input_bvecs = preproc_dir / (subjroot + "_ppd.bvec")
    autoptxsubj_dir = autoptxproc_dir / subjroot
    autoptxsubj_dir.mkdir(exist_ok=True)
    output_dwi = autoptxsubj_dir / ("data.nii")
    output_dwimask = autoptxsubj_dir / "nodif_brain_mask.nii"
    output_bvals = autoptxsubj_dir / 'bvals'
    output_bvecs = autoptxsubj_dir / 'bvecs'
    subprocess.run(['mrconvert', '-force', input_dwi, output_dwi])
    subprocess.run(['mrconvert', '-force', input_dwimask, output_dwimask])
    shutil.copy(input_bvals, output_bvals)
    shutil.copy(input_bvecs, output_bvecs)


with parallel_backend("loky", inner_max_num_threads=4):
    results = Parallel(n_jobs=16, verbose=1)(
        delayed(autoptx_prep)(ses_dir) for ses_dir in sorted(ses_dirs()))
# 3. Run autoPtx_1_preproc, which will create a autoptxproc/'preproc' directory, then
#    for each subject_ses:
#    -Run dtifit (fit the diffusion tensor model for each voxel), and put output in sub-XXX_ses-0Y
#    -Estimate (but not apply) the linear (affine matrix) and non-linear (warp) transformiations (nat2std; nat2std_warp)
#     registering the FA to FMRIB58_FA_1mm (nat2std)
#    -Compute the inverse non-linear transformation (std2nat_warp)
#    -Run bedpostx_gpu and output to sub-XXX_ses-0Y.bedpostX
#    -Create a native space reference volume of the FA in 1mm cubic voxels (will only contain orientation, no voxel data)
#    -Create a subjectList file in 'preproc' containing the folder names of all preprocessed subjects
#
# os.chdir(autoptxproc_dir)
# subprocess.run(['/Users/jdrussell3/apps/fsl/autoptx/autoPtx_1_preproc'])

# 4. Run autoPtx_2_preproc, which will create 'jobs', log', and 'tracts' directories in autoptxproc,
#    for each tract in the structureList file in the autoPtx application directory (lists each tract (L and R) to be 
#    extracted, the number of seeds to use in probalistic tractography, and the maximum run time; change this as necessary):
#       -Create a 'commands_#' file containing a list of command strings to submit to fsl_sub, one for each subject_ses in subjectList
#       -Submit the commands file to fsl_sub
#
#    Each command string in 'commands_#' will call trackSubjectStruct (use the v2 version) which will perform a bunch of registration
#    steps, then run probabilistic tractography, and ultimately output tractsNorm in the 'tracts' directory, which will contain all tracts
#    specified in the structureList file.  
#    
#    PROBLEMS!!! 
#     1. The CUDA-enabled version of probtrackx2 randomly crashes on our GPUs with an out of memory error.  These commands will need to be
#        manually re-run.
#     2. The 'v2' copy of trackSubjectStruct includes code to randomly select one of the two THOR gpus at runtime, for load-balancing.  Not the most
#        ideal solution, but whatever.
#     3. Need to ensure that trackSubjectStruct is calling a version of probtrackx2_gpu compatible with the currently installed CUDA libraries (e.g., 10.1)
#
#           subprocess.run(['/Users/jdrussell3/apps/autoptx/autoPtx_1_launchTractography'])


# 5. Get data
# autoptxproc_dir = Path("/Volumes/Vol6/YouthPTSD/autoptx")
# tractsall_dir = autoptxproc_dir / 'tracts'

# df = pd.DataFrame(columns=['ID', 'Tract', 'FA', 'AD', 'RD', 'MD', 'nVox'])
# for subjses_dir in sorted(tractsall_dir.glob('sub-*')):
#     print("-------------------------" + \
#           "\n----    " + subjses_dir.name + "    ----" + \
#           "-------------------------")
#     for struct_dir in sorted(subjses_dir.glob('*')):
#         tractsNorm = struct_dir / 'tracts' / 'tractsNorm.nii.gz'
#         print(struct_dir.name)
#         if tractsNorm.exists():
#             dti_FA = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_FA.nii.gz'
#             dti_mask = autoptxproc_dir / 'preproc' / subjses_dir.name / str('dti_mask_' + struct_dir.name + '.nii.gz')
#             subprocess.run(['3dresample', '-master', dti_FA, '-prefix', dti_mask, '-inset', tractsNorm, '-rmode', 'NN', '-overwrite'])
#             nvox = subprocess.run(['3dBrickStat', '-count', '-non-zero', dti_mask], stdout=subprocess.PIPE).stdout.strip().decode()
#             fa = subprocess.run(['3dmaskave', '-q', '-mask', dti_mask, dti_FA], stdout=subprocess.PIPE).stdout.strip().decode()

#             dti_L1 = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_L1.nii.gz'
#             ad = subprocess.run(['3dmaskave', '-q', '-mask', dti_mask, dti_L1], stdout=subprocess.PIPE).stdout.strip().decode()

#             dti_L2 = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_L2.nii.gz'
#             dti_L3 = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_L3.nii.gz'
#             dti_RD = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_RD.nii.gz'
#             subprocess.run(['3dcalc', '-a', dti_L2, '-b', dti_L3, '-expr', '(a + b) / 2', '-prefix', dti_RD, '-overwrite'])
#             rd = subprocess.run(['3dmaskave', '-q', '-mask', dti_mask, dti_RD], stdout=subprocess.PIPE).stdout.strip().decode()

#             dti_MD = autoptxproc_dir / 'preproc' / subjses_dir.name / 'dti_MD.nii.gz'
#             md = subprocess.run(['3dmaskave', '-q', '-mask', dti_mask, dti_MD], stdout=subprocess.PIPE).stdout.strip().decode()

#             df = df.append({'ID' : subjses_dir.name, 'Tract' : struct_dir.name, 'FA' : fa, 'AD' : ad, 'RD' : rd, 'MD' : md, 'nVox' : nvox}, ignore_index=True)

# export_csv = df.to_csv(r'/Volumes/Vol6/YouthPTSD/xtract/test.csv', header=True)



