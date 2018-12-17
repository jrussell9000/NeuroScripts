#!/usr/bin/env bash

set -e
# preproc_done_dir=$1
# working_dir=$2
# anat_dir=$3

#Directory to the OASIS Templates from the ANTs GitHub page (MICCAI2012-Multi-Atlas-Challenge-Data)
INPUT_DIR="/home/jdrussell3/ceda_scans/1000_C1/dicoms"
ANTSTEMPLATES="/home/jdrussell3/apps/ants/ants-templates/MICCAI2012-Multi-Atlas-Challenge-Data"
preproc_done_dir="/home/jdrussell3/ceda_scans/1000_C1/dwi_processing/preproc"
working_dir="/home/jdrussell3/ceda_scans/1000_C1/dwi_processing/mrtrixproc"
anat_dir="/home/jdrussell3/ceda_scans/1000_C1/dwi_processing/anat"

mrtrix_dir=$(command -v mrview)
if [ -z "${mrtrix_dir}" ]; then
  printf "MRTrix3 not found. Verify that MRTrix3 is included in the path"
else
  mrtrix_dir=${mrtrix_dir%/*/*}
fi

# Make temporary directories for processing
tmp_dir() {
  unset rand
  unset TMP
  rand=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 8 | head -n 1)
  TMP=/tmp/proc_${rand}
  mkdir "${TMP}"
}

if [ -d "${working_dir}" ]; then
  rm -rf "${working_dir}"
fi
mkdir "${working_dir}"

#Bring in the finished preprocessed scan file
mrconvert -fslgrad "${preproc_done_dir}"/PA_AP.bvec "${preproc_done_dir}"/PA_AP.bval "${preproc_done_dir}"/eddy_unwarped_images.nii.gz "${working_dir}"/dwi.mif


cd "${working_dir}" || exit

#MASK CREATION
dwi2mask dwi.mif dwi_mask.mif
maskfilter dwi_mask.mif dilate dwi_mask_dilated.mif -npass 3

#SPHERICAL DECONVOLUTION
dwi2response dhollander dwi.mif response_wm.txt response_gm.txt response_csf.txt -mask dwi_mask.mif

#CREATING THE FIBER ORIENTATION DISTRIBUTION FOR EACH TISSUE TYPE
dwi2fod msmt_csd dwi.mif response_wm.txt FOD_WM.mif response_gm.txt FOD_GM.mif response_csf.txt FOD_CSF.mif -mask dwi_mask_dilated.mif -lmax 10,0,0

#-For checking the results of FOD
mrconvert FOD_WM.mif FOD_WM_temp.mif -coord 3 0 
mrcat FOD_CSF.mif FOD_GM.mif FOD_WM_temp.mif tissues.mif -axis 3
rm FOD_WM_temp.mif

#ANATOMICAL PROCESSING

#-Dicom to Nifti conversion
if [ -d "${anat_dir}" ]; then
  rm -rf "${anat_dir}"
fi
mkdir "${anat_dir}"

for file in "${INPUT_DIR}"/*MPRAGE*.tgz; do
  tmp_dir
  cp "$file" "$TMP"
  tar xf "$TMP"/"$(basename "${file}")" -C "$TMP" 
  dcm2niix -z y "$TMP"
  imcp "$TMP"/*.nii.gz "${anat_dir}"/T1.nii.gz
  #cp "$TMP"/*.bval "$OUTPUT_DIR"/raw/"$pos_enc".bval - Must use the bval and bvec files from the scanner, values in dicoms are incorrect
  #cp "$TMP"/*.bvec "$OUTPUT_DIR"/raw/"$pos_enc".bvec
  cp "$TMP"/*.json "${anat_dir}"/T1.json
  rm -rf "${TMP}"
done

#-Skull Stripping
#--Copying necessary ANTs template files to anat_dir
cp "${ANTSTEMPLATES}"/T_template0.nii.gz "${ANTSTEMPLATES}"/T_template0_BrainCerebellumProbabilityMask.nii.gz \
"${ANTSTEMPLATES}"/T_template0_BrainCerebellumRegistrationMask.nii.gz "${anat_dir}"
#--Running antsBrainExtraction
antsBrainExtraction.sh -d 3 -a "${anat_dir}"/T1.nii.gz -e "${anat_dir}"/T_template0.nii.gz \
-m "${anat_dir}"/T_template0_BrainCerebellumProbabilityMask.nii.gz -o output -f "${anat_dir}"/T_template0_BrainCerebellumRegistrationMask.nii.gz
#--Copying T1.nii.gz, skull-stripped brain, and brain mask to working_dir and converting th MIF
mrconvert "${anat_dir}"/T1.nii.gz "${working_dir}"/T1.mif
mrconvert "${anat_dir}"/outputBrainExtractionBrain.nii.gz "${working_dir}"/T1brain.mif
mrconvert "${anat_dir}"/outputBrainExtractionMask.nii.gz "${working_dir}"/T1mask.mif -datatype bit

#T1->DWI REGISTRATION

#-Extracing mean b0 volume for histogram matching
dwiextract "${working_dir}"/dwi.mif -bzero "${working_dir}"/dwib0.mif
mrcalc "${working_dir}"/dwib0.mif 0.0 -max "${working_dir}"/dwib0_0max.mif
mrmath "${working_dir}"/dwib0_0max.mif mean -axis 3 "${working_dir}"/dwimeanb0.mif

#-Matching histograms before registration
#--Multiplying the inverse of the mean b0 volume by its mask
mrcalc 1 "${working_dir}"/dwimeanb0.mif -div "${working_dir}"/dwi_mask.mif -mult "${working_dir}"/dwimeanb0_toHistmatch.mif
#--Changing the histogram of the dwi_meanb0_div volume to match the skull-stripped T1; outputting the new DWI volume as dwi_histmatch_T1ss.mif
mrhistmatch nonlinear "${working_dir}"/dwimeanb0_toHistmatch.mif "${working_dir}"/T1brain.mif "${working_dir}"/dwimeanb0_histmatch.mif \
-mask_input "${working_dir}"/dwi_mask.mif -mask_target "${working_dir}"/T1mask.mif

#--Multiplying the inverse of the skull stripped brain image by its maskmask
mrcalc 1 "${working_dir}"/T1brain.mif -div "${working_dir}"/T1mask.mif -mult "${working_dir}"/T1brain_toHistmatch.mif
#--Changing the histogram of the skull-stripped T1 volume to match the dwi_meanb0_div image; outputting the new T1 volume as T1_histm
mrhistmatch nonlinear "${working_dir}"/T1brain_toHistmatch.mif "${working_dir}"/dwimeanb0.mif "${working_dir}"/T1brain_histmatch.mif \
-mask_input "${working_dir}"/T1mask.mif -mask_target "${working_dir}"/dwi_mask.mif

#-Cross registering the histogram matched volumes
#--Registering the skull stripped brain volume to the T1-histogram matched DWI volume (i.e., registering DWI>T1)
mrregister -force "${working_dir}"/T1brain.mif "${working_dir}"/dwimeanb0_histmatch.mif -type rigid -mask1 "${working_dir}"/T1mask.mif \
-mask2 "${working_dir}"/dwi_mask.mif -rigid "${working_dir}"/rigid_T1_regto_dwiHistmatch.txt
#--Registering the DWI-histogram matched T1 volume to the mean b0 volume
mrregister -force "${working_dir}"/T1brain_histmatch.mif "${working_dir}"/dwimeanb0.mif -type rigid -mask1 "${working_dir}"/T1mask.mif \
-mask2 "${working_dir}"/dwi_mask.mif -rigid "${working_dir}"/rigid_T1brainHistmatch_regto_dwimeanb0.txt

#-Registering the T1 to the DWI
#--Averge the two transformation matrices to create a final T1 to dwi matrix
transformcalc -force "${working_dir}"/rigid_T1_regto_dwiHistmatch.txt "${working_dir}"/rigid_T1brainHistmatch_regto_dwimeanb0.txt \
average "${working_dir}"/rigid_T1_regto_dwi.txt

#--Register the original T1 volume to the DWI volume using a linear transform with the previously create matrix; output as T1_registered
mrtransform -force "${working_dir}"/T1.mif "${working_dir}"/T1_registered.mif -linear "${working_dir}"/rigid_T1_regto_dwi.txt
#--Register the T1 mask to the DWI volume..., use the registered T1 as a template; output as T1_mask_registered
mrtransform -force "${working_dir}"/T1mask.mif "${working_dir}"/T1mask_registered.mif -linear "${working_dir}"/rigid_T1_regto_dwi.txt \
-template "${working_dir}"/T1_registered.mif -interp nearest -datatype bit

#GENERATE 5TT IMAGE 
5ttgen fsl "${working_dir}"/T1_registered.mif "${working_dir}"/5TT.mif -mask "${working_dir}"/T1_mask_registered.mif

#PARCELLATE THE REGISTERED T1
#-Make the recon_dir directory where recon-all will be run; delete and recreate it if it exists
recon_dir="${anat_dir}"/recon
if [ -d "$recon_dir" ] ; then
  rm -rf "${recon_dir}"
fi
mkdir "${recon_dir}"
cd "${recon_dir}" || exit 1

#-Copying the necessary files to the recon_dir directory 
cp "${working_dir}"/T1_registered.mif "${recon_dir}"
mrconvert "${recon_dir}"/T1_registered.mif T1.nii

#-Link the fsaverage files required by recon-all to the recon_dir directory where reconstruction will be run
ln -s "$SUBJECTS_DIR"/fsaverage "${recon_dir}"/fsaverage
ln -s "$SUBJECTS_DIR"/rh.EC_average "${recon_dir}"/rh.EC_average
ln -s "$SUBJECTS_DIR"/lh.EC_average "${recon_dir}"/lh.EC_average

#-Create a FreeSurfer subject named "freesurfer" inside the recon_dir, and input the T1_registered.nii volume
recon-all -sd "${recon_dir}" -subjid freesurfer -i "${working_dir}"/T1_registered.nii

#-Run recon-all on the subject "freesurfer" located in the recon_dir
time recon-all -sd "${recon_dir}" -subjid freesurfer -all -mprage

#-Change from the default FreeSurfer parcellation to the HCPMMP parcellation
#!!!!Does fsaverage containi the HCPMMP annotations, or do we need to get them?
anat_dir="/home/jdrussell3/ceda_scans/1000_C1/dwi_processing/anat"
recon_dir="${anat_dir}"/recon
hemispheres="lh rh"
for hemi in $hemispheres; do
    SUBJECTS_DIR="${recon_dir}"
    mri_surf2surf --srcsubject fsaverage --trgsubject freesurfer --hemi "${hemi}" --sval-annot "${SUBJECTS_DIR}"/fsaverage/label/"${hemi}".HCPMMP1.annot \
    --tval "${SUBJECTS_DIR}"/freesurfer/label/"${hemi}".HCPMMP1.annot
done

#-Map the cortical labels from the HCPMMP parcellation to the volume segmentation
mri_aparc2aseg --s freesurfer --old-ribbon --annot HCPMMP1 --o aparc.HCPMMP1+aseg.mgz

#-The labels in the lookup tables for FreeSurfer aren't numbered continuously - this command fixes that
labelconvert -force "${recon_dir}"/aparc.HCPMMP1+aseg.mgz "${mrtrix_dir}"/share/mrtrix3/labelconvert/hcpmmp1_original.txt \
"${mrtrix_dir}"/share/mrtrix3/labelconvert/hcpmmp1_ordered.txt "${working_dir}"/parc_init.mif

#-Fixing the graymatter labeling (?)
labelsgmfix -force parc_init.mif "${working_dir}"/T1_registered.mif "${mrtrix_dir}"/share/mrtrix3/labelconvert/hcpmmp1_ordered.txt "${working_dir}"/parc.mif
#rm parc_init.mif

#n_nodes=$(mrstats parc.mif -output max)
#n_streamlines=$((500 * n_nodes * $((n_nodes -1)) ))

cd "${working_dir}" || exit

#!!!Do we want a separate directory for track processing?
# trackproc_dir="${working_dir}"/trackproc
# if [ -d "${trackproc_dir}" ]; then
#   rm -rf "${trackproc_dir}"
# fi
# mkdir "${trackproc_dir}"
# cd "${trackproc_dir}" || exit

tckgen "${working_dir}"/FOD_WM.mif "${working_dir}"/tractogram.tck -act "${working_dir}"/5TT.mif -backtrack -crop_at_gmwmi -maxlength 250 -power 0.33 -select 10000000 -seed_dynamic "${working_dir}"/FOD_WM.mif

tcksift2 "${working_dir}"/tractogram.tck "${working_dir}"/FOD_WM.mif "${working_dir}"/weights.csv -act "${working_dir}"/5TT.mif -out_mu "${working_dir}"/mu.txt -fd_scale_gm

tckmap tractogram.tck -tck_weights_in weights.csv -template FOD_WM.mif -precise track.mif
mu=$(cat mu.txt)
mrcalc track.mif "${mu}" -mult tdi_native.mif

tckmap tractogram.tck -tck_weights_in weights.csv -template vis.mif -vox 1 -datatype uint16 tdi_highres.mif

tck2connectome tractogram.tck parc.mif connectome.csv -tck_weights_in weights.csv -out_assignments assignments.csv
tck2connectome tractogram.tck parc.mif meanlength.csv -tck_weights_in weights.csv -scale_length -stat_edge mean
connectome2tck tractogram.tck assignments.csv exemplars.tck -tck_weights_in weights.csv -exemplars parc.mif -files single
label2mesh parc.mif nodes.obj
meshfilter nodes.obj smooth nodes_smooth.obj


