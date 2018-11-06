#!/usr/bin/env bash
# JD Russell 2018
# Single tissue fixel-based fibre density and cross section processing and analyses
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/st_fibre_density_cross-section.html

while getopts 'i:o:' args; do
	case "${args}" in
  i)
    INPUT_DIR=${OPTARG}
    ;;
	o)
		PROC_DIR=${OPTARG}
		;;
	esac
done

######GLOBALS######

######FUNCTIONS#####
parse_subjs() {
	if [ -f subj_list.txt ]; then
		while read -r subjects; do
		  subj_array+=("$subjects")
	  done <subj_list.txt
  else
    find /Volumes/Studies/Herringa/YouthPTSD -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort -u | tr -d "_" >>subj_list.txt
    while read -r subjects; do
      subj_array+=("$subjects")
	  done <subj_list.txt
  fi
}

make_proc_dir() {
  if [ -d ${PROC_DIR} ]; then
    rm -rf "${PROC_DIR}"
  fi
  mkdir "${PROC_DIR}"
}

make_intnorm_dir() {
  # Making directory for global intensity normalization
  INTNORM_DIR="${PROC_DIR}"/dwiintensitynorm
  if [ -d "${INTNORM_DIR}" ]; then
    rm -rf "${INTNORM_DIR}"
  fi
  mkdir -p "${INTNORM_DIR}"/dwi_input
  mkdir "${INTNORM_DIR}"/mask_input
}

make_template_dir() {
  # Making directory to contain inputs needed to make FOD template
  TEMPLATE_DIR="${PROC_DIR}"/template
  if [ -d "${TEMPLATE_DIR}" ]; then
    rm -rf "${TEMPLATE_DIR}"
  fi
  mkdir -p "${TEMPLATE_DIR}"/fod_input
  mkdir "${TEMPLATE_DIR}"/mask_input
  mkdir "${TEMPLATE_DIR}"/log_fc
  mkdir "${TEMPLATE_DIR}"/fdc
}

copy_scanfiles() {
  for SUBJ in "${subj_array[@]}"; do
    mkdir "${PROC_DIR}"/"${SUBJ}"
    cp "${INPUT_DIR}"/"${SUBJ}"/DTI/* "${PROC_DIR}"/"${SUBJ}"
    cp "${INPUT_DIR}"/"${SUBJ}"/ANAT/* "${PROC_DIR}"/"${SUBJ}"
    mv "${PROC_DIR}"/"${SUBJ}"/"${SUBJ}"_DTI.json "${PROC_DIR}"/"${SUBJ}"/DTI.json
    mv "${PROC_DIR}"/"${SUBJ}"/"${SUBJ}"_DTI.bvec "${PROC_DIR}"/"${SUBJ}"/DTI.bvec
    mv "${PROC_DIR}"/"${SUBJ}"/"${SUBJ}"_DTI.bval "${PROC_DIR}"/"${SUBJ}"/DTI.bval
    mv "${PROC_DIR}"/"${SUBJ}"/"${SUBJ}"_DTI.nii "${PROC_DIR}"/"${SUBJ}"/DTI.nii
    mv "${PROC_DIR}"/"${SUBJ}"/"${SUBJ}"_T1.nii "${PROC_DIR}"/"${SUBJ}"/T1.nii
  done
}

######MAIN######
parse_subjs
make_proc_dir
copy_scanfiles

cd "${PROC_DIR}" || return
foreach * : mrconvert -json_import IN/DTI.json -fslgrad IN/DTI.bvec IN/DTI.bval IN/DTI.nii IN/dwi.mif
foreach * : mrconvert IN/T1.nii IN/T1.mif
foreach * : dwidenoise IN/dwi.mif IN/dwi_den.mif
foreach * : mrdegibbs IN/dwi_den.mif IN/dwi_den_deg.mif -axes 0,1
foreach * : dwipreproc IN/dwi_den_deg.mif IN/dwi_den_deg_pp.mif -rpe_none -pe_dir PA -eddy_options "--slm=linear"
foreach * : dwi2mask IN/dwi_den_deg.mif IN/dwi_temp_mask.mif
foreach * : dwibiascorrect -ants IN/dwi_den_deg_pp.mif IN/dwi_den_deg_pp_unb.mif
# make_intnorm_dir
# foreach * : ln -s IN/dwi_den_deg_pp_unb.mif "${INTNORM_DIR}"/dwi_input/IN.mif
# foreach * : ln -s IN/dwi_temp_mask.mif "${INTNORM_DIR}"/mask_input/IN.mif
# dwiintensitynorm "${INTNORM_DIR}"/dwi_input/ "${INTNORM_DIR}"/mask_input/ "${INTNORM_DIR}"/dwi_output/ "${INTNORM_DIR}"/fa_template.mif "${INTNORM_DIR}"/fa_template_wm_mask.mif
# foreach "${INTNORM_DIR}"/dwi_output/* : ln -s IN PRE/dwi_den_deg_pp_unb_norm.mif
# foreach * : dwi2response tournier IN/dwi_den_deg_pp_unb_norm.mif IN/response.txt
# average_response */response.txt "${PROC_DIR}"/group_average_response.txt
# foreach * : mrresize IN/dwi_den_deg_pp_unb_norm.mif -vox 1.3 IN/dwi_den_deg_pp_unb_norm_upsamp.mif
# foreach * : dwi2mask IN/dwi_den_deg_pp_unb_norm_upsamp.mif IN/dwi_mask_upsampled.mif
# foreach * : dwiextract IN/dwi_den_deg_pp_unb_norm_upsamp.mif IN/noB0s.mif
# foreach * : dwi2fod msmt_csd IN/noB0s.mif "${PROC_DIR}"/group_average_response.txt IN/wmfod.mif -mask IN/dwi_mask_upsampled.mif 
# make_template_dir
# foreach * : ln -s IN/wmfod.mif "${TEMPLATE_DIR}"/fod_input/PRE.mif
# foreach * : ln -s IN/dwi_mask_upsampled.mif "${TEMPLATE_DIR}"/mask_input/PRE.mif
# population_template "${TEMPLATE_DIR}"/fod_input -mask_dir "${TEMPLATE_DIR}"/mask_input "${TEMPLATE_DIR}"/wmfod_template.mif -voxel_size 1.3
# foreach * : mrregister IN/wmfod.mif -mask1 IN/dwi_mask_upsampled.mif "${TEMPLATE_DIR}"/wmfod_template.mif -nl_warp IN/subject2template_warp.mif IN/template2subject_warp.mif
# foreach * : mrtransform IN/dwi_mask_upsampled.mif -warp IN/subject2template_warp.mif -interp nearest -datatype bit IN/dwi_mask_in_template_space.mif
# mrmath */dwi_mask_in_template_space.mif min "${TEMPLATE_DIR}"/template_mask.mif -datatype bit
# fod2fixel -mask "${TEMPLATE_DIR}"/template_mask.mif -fmls_peak_value 0.10 "${TEMPLATE_DIR}"/wmfod_template.mif "${TEMPLATE_DIR}"/fixel_mask
# foreach * : mrtransform IN/wmfod.mif -warp IN/subject2template_warp -noreorientation IN/FOD_in_template_space_NOT_REORIENTED.mif
# foreach * : fod2fixel -mask "${TEMPLATE_DIR}"/template_mask.mif IN/FOD_in_template_space_NOT_REORIENTED.mif IN/fixel_in_template_space_NOT_REORIENTED -afd fd.mif
# foreach * : fixelreorient IN/fixel_in_template_space_NOT_REORIENTED IN/subject2template_warp.mif IN/fixel_in_template_space
# foreach * : rm -rf fixel_in_template_space_NOT_REORIENTED
# foreach * : fixelcorrespondence IN/fixel_in_template_space/fd.mif "${TEMPLATE_DIR}"/fixel_mask "${TEMPLATE_DIR}"/fd PRE.mif
# foreach * : warp2metric IN/subject2template_warp.mif -fc "${TEMPLATE_DIR}"/fixel_mask "${TEMPLATE_DIR}"/fc IN.mif
# cp "${TEMPLATE_DIR}"/fc/index.mif "${TEMPLATE_DIR}"/fc/directions.mif "${TEMPLATE_DIR}"/log_fc
# foreach * : mrcalc "${TEMPLATE_DIR}"/fc/IN.mif -log "${TEMPLATE_DIR}"/log_fc/IN.mif
# cp "${TEMPLATE_DIR}"/fc/index.mif  "${TEMPLATE_DIR}"/fdc
# cp "${TEMPLATE_DIR}"/fc/directions.mif "${TEMPLATE_DIR}"/fdc
# foreach * : mrcalc "${TEMPLATE_DIR}"/fd/IN.mif "${TEMPLATE_DIR}"/fc/IN.mif -mult "${TEMPLATE_DIR}"/fdc/IN.mif
# cd "${TEMPLATE_DIR}" || return
# tckgen -angle 22.5 -maxlen 250 -minlen 10 -power 1.0 wmfod_template.mif -seed_image template_mask.mif -mask template_mask -select 20000000 -cutoff 0.10 tracks_20_million.tck
# tcksift tracks_20_million.tck wmfod_template.mif tracks_2_million_sift.tck -term_number 2000000
# fixelcfestats fd files.txt design_matrix.txt contrast_matrix.txt tracks_2_million_sift.tck stats_fd
# fixelcfestats log_fc files.txt design_matrix.txt contrast_matrix.txt tracks_2_million_sift.tck stats_log_fc
# fixelcfestats fdc files.txt design_matrix.txt contrast_matrix.txt tracks_2_million_sift.tck stats_fdc