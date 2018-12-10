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
dwi2fod msmt_csd dwi.mif response_wm.txt FOD_WM.mif response_gm.txt FOD_GM.mif response_csf.txt FOD_CSF.mif -mask dwi_mask_dilated.mif -lmax 10,0,0
mrconvert FOD_WM.mif FOD_WM_temp.mif -coord 3 0 
mrcat FOD_CSF.mif FOD_GM.mif FOD_WM_temp.mif tissues.mif -axis 3
rm FOD_WM_temp.mif

#ANATOMICAL PROCESSING

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

cd "${anat_dir}" || exit 1

cp "${ANTSTEMPLATES}"/T_template0.nii.gz "${ANTSTEMPLATES}"/T_template0_BrainCerebellumProbabilityMask.nii.gz \
"${ANTSTEMPLATES}"/T_template0_BrainCerebellumRegistrationMask.nii.gz "${anat_dir}"
antsBrainExtraction.sh -d 3 -a T1.nii.gz -e T_template0.nii.gz \
-m T_template0_BrainCerebellumProbabilityMask.nii.gz -o output.nii.gz -f T_template0_BrainCerebellumRegistrationMask.nii.gz

#PREPARING FILES FOR REGISTRATION
mrconvert "${anat_dir}"/T1.nii.gz "${working_dir}"/T1.mif
mrconvert "${anat_dir}"/output.nii.gzBrainExtractionBrain.nii.gz "${working_dir}"/T1_sscorr_brain.mif
mrconvert "${anat_dir}"/output.nii.gzBrainExtractionMask.nii.gz "${working_dir}"/T1_sscorr_mask.mif

cd "${working_dir}" || exit 1

dwiextract dwi.mif -bzero dwi_bzero.mif
mrcalc dwi_bzero.mif 0.0 -max dwi_bzero_0max.mif
mrmath dwi_bzero_0max.mif mean -axis 3 dwi_meanbzero.mif

mrcalc 1 dwi_meanbzero.mif -div dwi_mask.mif -mult dwi_div.mif
mrhistmatch nonlinear dwi_div.mif T1_sscorr_brain.mif dwi_pseudoT1.mif -mask_input dwi_mask.mif -mask_target T1_sscorr_mask.mif

mrcalc 1 T1_sscorr_brain.mif -div T1_sscorr_mask.mif -mult T1_div.mif 
mrhistmatch nonlinear T1_div.mif dwi_meanbzero.mif T1_pseudobzero.mif -mask_input T1_sscorr_mask.mif -mask_target dwi_mask.mif

#T1->DWI REGISTRATION
mrregister -force T1_sscorr_brain.mif dwi_pseudoT1.mif -type rigid -mask1 T1_sscorr_mask.mif -mask2 dwi_mask.mif -rigid rigid_T1_to_pseudoT1.txt
mrregister -force T1_pseudobzero.mif dwi_meanbzero.mif -type rigid -mask1 T1_sscorr_mask.mif -mask2 dwi_mask.mif -rigid rigid_pseudobzero_to_bzero.txt
transformcalc -force rigid_T1_to_pseudoT1.txt rigid_pseudobzero_to_bzero.txt average rigid_T1_to_dwi.txt
mrtransform -force T1.mif T1_registered.mif -linear rigid_T1_to_dwi.txt
mrconvert -force T1_sscorr_mask.mif T1_mask.mif -datatype bit
mrtransform -force T1_mask.mif T1_mask_registered.mif -linear rigid_T1_to_dwi.txt -template T1_registered.mif -interp nearest -datatype bit
# rm T1_sscorr_brain.mif
# rm dwi_meanbzero.mif
# rm rigid_T1_to_pseudoT1.txt
# rm rigid_pseudobzero_to_bzero.txt
# rm T1.mif
recon_dir="${anat_dir}"/recon
if [ -d "$recon_dir" ] ; then
  rm -rf "${recon_dir}"
fi
mkdir "${recon_dir}"
cp T1_registered.mif T1_mask_registered.mif "${anat_dir}"
cd "${anat_dir}" || exit 1

#GENERATE 5TT IMAGE 
fivettgen_dir=${anat_dir}/fivettgen
mkdir ${fivettgen_dir}
cp T1_registered.mif T1_mask_registered.mif "${fivettgen_dir}"
cd "${fivettgen_dir}" || exit 1
5ttgen fsl T1_registered.mif 5TT.mif -mask T1_mask_registered.mif 
5tt2vis 5tt.mif vis.mif

#PARCELLATE THE REGISTERED T1
cp T1_registered.mif T1_mask_registered.mif "${anat_dir}"
ln -s "$SUBJECTS_DIR"/fsaverage "${recon_dir}"/fsaverage
ln -s "$SUBJECTS_DIR"/rh.EC_average "${recon_dir}"/rh.EC_average
ln -s "$SUBJECTS_DIR"/lh.EC_average "${recon_dir}"/lh.EC_average

mrconvert T1_registered.mif T1_registered.nii
recon-all -sd "${recon_dir}" -subjid freesurfer -i T1_registered.nii
recon-all -sd "${recon_dir}" -subjid freesurfer -all -use-gpu

hemispheres="lh rh"
for hemi in $hemispheres; do
    SUBJECTS_DIR="${recon_dir}"
    mri_surf2surf --srcsubject fsaverage --trgsubject freesurfer --hemi "${hemi}" --sval-annot "${SUBJECTS_DIR}"/fsaverage/label/"${hemi}".HCPMMP1.annot \
    --tval "${SUBJECTS_DIR}"/freesurfer/label/"${hemi}".HCPMMP1.annot
done

mri_aparc2aseg --s freesurfer --old-ribbon --annot HCPMMP1 --o aparc.HCMMP1+aseg.mgz

labelconvert "${recon_dir}"/aparc.HCPMMP1+aseg.mgz /home/jdrussell3/apps/mrtrix3/share/mrtrix3/labelconvert/hcpmmp1_original.txt \
/home/jdrussell3/apps/mrtrix3/share/mrtrix3/labelconvert/hcpmmp1_ordered.txt parc_init.mif

labelsgmfix parc_init.mif ../T1_registered.mif /home/jdrussell3/apps/mrtrix3/share/mrtrix3/labelconvert/hcpmmp1_ordered.txt parc.mif

n_nodes=$(mrstats parc.mif -output max)
n_streamlines=$((500 * n_nodes * $((n_nodes -1)) ))
cp 5tt.mif "${anat_dir}"

cd "${working_dir}" || exit
tckgen FOD_WM.mif tractogram.tck -act 5TT.mif -backtrack -crop_at_gmwmi -maxlength 250 -power 0.33 -select 1000000 -seed_dynamic FOD_WM.mif

tcksift2 tractogram.tck FOD_WM.mif weights.csv -act 5TT.mif -out_mu mu.txt -fd_scale_gm

tckmap tractogram.tck -tck_weights_in weights.csv -template FOD_WM.mif -precise track.mif
mu=$(cat mu.txt)
mrcalc track.mif ${mu} -mult tdi_native.mif

tckmap tractogram.tck -tck_weights_in weights.csv -template vis.mif -vox 1 -datatype uint16 tdi_highres.mif

tck2connectome tractogram.tck parc.mif connectome.csv -tck_weights_in weights.csv -out_assignments assignments.csv
tck2connectome tractogram.tck parc.mif meanlength.csv -tck_weights_in weights.csv -scale_length -stat_edge mean
connectome2tck tractogram.tck assignments.csv exemplars.tck -tck_weights_in weights.csv -exemplars parc.mif -files single
label2mesh parc.mif nodes.obj
meshfilter nodes.obj smooth nodes_smooth.obj


