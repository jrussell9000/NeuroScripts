#!/usr/bin/env bash
# JD Russell 2018
# Single tissue fixel-based fibre density and cross section processing and analyses
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/st_fibre_density_cross-section.html

while getopts 'p:' args; do
	case "${args}" in
  i)
    INPUT_DIR=${OPTARG}
    ;;
	p)
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

subj_start() {
  blink=$(tput blink)$(tput setaf 1)
  normal=$(tput sgr0)
  SUBJ_F=${blink}${SUBJ}${normal}
	printf "\\n%s" "///////////////////////////////////////////"
	printf "\\n%s" "//-------------NOW PROCESSING------------//"
  printf "\\n%s" "//----------------SUBJECT #--------------//"
	printf "\\n%s" "//------------------$SUBJ_F------------------//"
	printf "\\n%s\\n" "///////////////////////////////////////////"
  SUBJ_PATH="${PROC_DIR}"/"${SUBJ}"

}

make_proc_dir() {
  if [ -d ${PROC_DIR} ]; then
    rm -rf "${PROC_DIR}"
  fi
  mkdir -p "${PROC_DIR}"
  SUBJ_PATH="${PROC_DIR}"/"${SUBJ}"
  if [ -d "${SUBJ_PATH}"/mrtrix3_proc ]; then
    rm -rfv "${SUBJ_PATH}"/mrtrix3_proc
	  mkdir -p "${SUBJ_PATH}"/mrtrix3_proc
  else
    mkdir -p "${SUBJ_PATH}"/mrtrix3_proc
  fi
  MRTRIX_PROC="${SUBJ_PATH}"/mrtrix3_proc
}

groupwise_dirs() {
  # Making directory for global intensity normalization
  intnorm_dir="${PROC_DIR}"/dwiintensitynorm
  if [ -d "${intnorm_dir}" ]; then
    rm -rf "${intnorm_dir}"
  fi
  mkdir -p "${intnorm_dir}"/dwi_input
  mkdir "${intnorm_dir}"/mask_input

  # Making directory to contain inputs needed to make FOD template
  template_dir="${PROC_DIR}"/template
  if [ -d "${template_dir}" ]; then
    rm -rf "${template_dir}"
  fi
  mkdir -p "${template_dir}"/fod_input
  mkdir "${template_dir}"/mask_input
}

copy_scanfiles() {
  cp "${SUBJ_PATH}"/DTI/* "${MRTRIX_PROC}"
  cp "${SUBJ_PATH}"/ANAT/* "${MRTRIX_PROC}"
}

conv_nii2mif() {
  cd "${MRTRIX_PROC}" || return
  mrconvert -json_import "${SUBJ}"_DTI.json -fslgrad "${SUBJ}"_DTI.bvec "${SUBJ}"_DTI.bval "${SUBJ}"_DTI.nii DTI.mif
  mrconvert "${SUBJ}"_T1.nii T1.mif
}

######MAIN######
parse_subjs
groupwise_dirs
make_proc_dir
copy_scanfiles
conv_nii2mif

foreach * : dwidenoise IN/mrtrix_proc/dwi.mif IN/mrtrix_proc/dwi_den.mif
foreach * : mrdegibbs IN/mrtrix_proc/dwi_den.mif IN/mrtrix_proc/dwi_den_deg.mif -axes 0,1
foreach * : dwipreproc IN/mrtrix_proc/dwi_den_deg.mif IN/mrtrix_proc/dwi_den_deg_pp.mif -rpe_none -pe_dir PA
foreach * : dwi2mask IN/mrtrix_proc/dwi_den_deg.mif IN/mrtrix_proc/dwi_temp_mask.mif
foreach * : dwibiascorrect -ants IN/mrtrix_proc/dwi_den_deg_pp.mif mrtrix_proc/dwi_den_deg_pp_unb.mif
mkdir -p "${intnorm_dir}"/dwi_input
mkdir "${intnorm_dir}"/mask_input
foreach * : ln -s IN/mrtrix_proc/dwi_den_deg_pp_unb.mif "${intnorm_dir}"/dwi_input/IN.mif
foreach * : ln -s IN/mrtrix_proc/dwi_temp_mask.mif "${intnorm_dir}"/mask_input/IN.mif
dwiintensitynorm "${intnorm_dir}"/dwi_input/ "${intnorm_dir}"/mask_input/ "${intnorm_dir}"/dwi_output/ "${intnorm_dir}"/fa_template.mif "${intnorm_dir}"/fa_template_wm_mask.mif
foreach "${intnorm_dir}"/dwi_output/* : ln -s IN PRE/mrtrix_proc/dwi_den_deg_pp_unb_norm.mif
foreach * : dwi2response tournier IN/mrtrix_proc/dwi_den_deg_pp_unb_norm.mif IN/mrtrix_proc/response.txt
average_response */response.txt "${PROC_DIR}"/group_average_response.txt
foreach * : mrresize IN/dwi_den_deg_pp_unb_norm.mif -vox 1.3 IN/mrtrix_proc/dwi_den_deg_pp_unb_norm_upsamp.mif
foreach * : dwi2mask IN/dwi_den_deg_pp_unb_norm_upsamp.mif IN/mrtrix_proc/dwi_mask_upsampled.mif
foreach * : dwiextract IN/dwi_den_deg_pp_unb_norm_upsamp.mif IN/mrtrix_proc/noB0s.mif
foreach * : dwi2fod msmt_csd IN/mrtrix_proc/noB0s.mif "${PROC_DIR}"/group_average_response.txt IN/mrtrix_proc/wmfod.mif -mask IN/mrtrix_proc/dwi_mask_upsampled.mif 
mkdir -p "${template_dir}"/fod_input
mkdir "${template_dir}"/mask_input
foreach * : ln -s IN/wmfod.mif "${template_dir}"/fod_input/PRE.mif
foreach * : ln -s IN/dwi_mask_upsampled.mif "${template_dir}"/mask_input/PRE.mif
population_template "${template_dir}"/fod_input -mask_dir "${template_dir}"/mask_input "${template_dir}"/wmfod_template.mif -voxel_size 1.3
foreach * : mrregister IN/wmfod.mif -mask1 IN/dwi_mask_upsampled.mif "${template_dir}"/wmfod_template.mif -nl_warp IN/subject2template_warp.mif IN/template2subject_warp.mif
foreach * : mrtransform IN/dwi_mask_upsampled.mif -warp IN/subject2template_warp.mif -interp nearest -datatype bit IN/dwi_mask_in_template_space.mif
mrmath */dwi_mask_in_template_space.mif min "${template_dir}"/template_mask.mif -datatype bit
fod2fixel -mask "${template_dir}"/template_mask.mif -fmls_peak_value 0.10 "${template_dir}"/wmfod_template.mif "${template_dir}"/fixel_mask
foreach * : mrtransform IN/wmfod.mif -warp IN/subject2template_warp -noreorientation IN/FOD_in_template_space_NOT_REORIENTED.mif
foreach * : fod2fixel -mask "${template_dir}"/template_mask.mif IN/FOD_in_template_space_NOT_REORIENTED.mif IN/fixel_in_template_space_NOT_REORIENTED -afd fd.mif
foreach * : fixelreorient IN/fixel_in_template_space_NOT_REORIENTED IN/subject2template_warp.mif IN/fixel_in_template_space
foreach * : rm -rf fixel_in_template_space_NOT_REORIENTED
foreach * : fixelcorrespondence IN/fixel_in_template_space/fd.mif "${template_dir}"/fixel_mask "${template_dir}"/fd PRE.mif
foreach * : warp2metric IN/subject2template_warp.mif -fc "${template_dir}"/fixel_mask "${template_dir}"/fc IN.mif
mkdir "${template_dir}"/log_fc
cp "${template_dir}"/fc/index.mif "${template_dir}"/fc/directions.mif "${template_dir}"/log_fc
foreach * : mrcalc "${template_dir}"/fc/IN.mif -log "${template_dir}"/log_fc/IN.mif
mkdir "${template_dir}"/fdc
cp "${template_dir}"/fc/index.mif  "${template_dir}"/fdc
cp "${template_dir}"/fc/directions.mif "${template_dir}"/fdc
foreach * : mrcalc "${template_dir}"/fd/IN.mif "${template_dir}"/fc/IN.mif -mult "${template_dir}"/fdc/IN.mif
cd "${template_dir}" || return
tckgen -angle 22.5 -maxlen 250 -minlen 10 -power 1.0 wmfod_template.mif -seed_image template_mask.mif -mask template_mask -select 20000000 -cutoff 0.10 tracks_20_million.tck
tcksift tracks_20_million.tck wmfod_template.mif tracks_2_million_sift.tck -term_number 2000000
fixelcfestats fd files.txt design_matrix.txt contrast_matrix.txt tracks_2_million_sift.tck stats_fd
fixelcfestats log_fc files.txt design_matrix.txt contrast_matrix.txt tracks_2_million_sift.tck stats_log_fc
fixelcfestats fdc files.txt design_matrix.txt contrast_matrix.txt tracks_2_million_sift.tck stats_fdc