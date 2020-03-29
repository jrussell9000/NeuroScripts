#!/usr/bin/env python3
# coding: utf-8

import shutil
import subprocess
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel


# fba_dir = Path('/scratch/jdrussell3/mrtrix/fba/cross_sec')
# wmfod_long_templ = Path('/scratch/jdrussell3/dti_longproc/youthptsd_wmfod_long_template.mif')
# bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
# common_mask_dir = fba_dir / 'common_mask_creation'
# if common_mask_dir.exists():
#     shutil.rmtree(common_mask_dir)
# common_mask_dir.mkdir()


# Steps in this pipeline are organized according to:
# https://mrtrix.readthedocs.io/en/latest/fixel_based_analysis/mt_fibre_density_cross-section.html
# but using SS3T from MRTrix3Tissue
fba_dir = Path('/scratch/jdrussell3/mrtrix/fba/cross_sec')
bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed')


class fba():

    def __init__(self, ses_dir):
        self.ses_dir = Path(ses_dir)
        self.main(ses_dir)

    def loadsubj(self):
        self.subj_dir = self.ses_dir.parent
        self.subjroot = "_".join([self.subj_dir.name, self.ses_dir.name])
        self.preproc_dir = self.ses_dir / 'dwi' / 'preprocessed'
        self.proc_dir = self.ses_dir / 'dwi' / 'processed'
        self.ss3t_dir = self.proc_dir / 'mrtrix' / 'ss3t'
        self.wmfod_norm = self.ss3t_dir / (self.subjroot + '_wmfod_norm.mif')
        self.subj2templwarp = self.ss3t_dir / (self.subjroot + '_subj2templwarp.mif')
        self.dwi_mask_ppd = self.preproc_dir / (self.subjroot + '_mask_ppd.mif')
        self.subj2templwarp = self.ss3t_dir / (self.subjroot + '_subj2templwarp.mif')
        self.templ2subjwarp = self.ss3t_dir / (self.subjroot + '_templ2subjwarp.mif')
        print(self.subj_dir)
        # return ss3t_dir, subjroot, wmfod_norm, subj2templwarp

    # Step 10 - Register all subject FOD images to the FOD template

    def regfod2templ(self):
        self.wmfod_templ = fba_dir / 'wmfod_template.mif'
        subprocess.run(['mrregister', '-force', self.wmfod_norm, '-mask1', self.dwi_mask_ppd, self.wmfod_templ, '-nl_warp',
                        self.subj2templwarp, self.templ2subjwarp])

    # Step 11 - Compute the template mask (intersection of all subject masks in template space)

    def warpMasks2Templ(self):
        self.common_mask_dir = fba_dir / 'common_mask_creation'
        if not self.common_mask_dir.exists():
            self.common_mask_dir.mkdir()
        self.dwi_mask_ppd_reg2templ = self.common_mask_dir / (self.subjroot + '_mask_ppd_reg2templ.mif')
        subprocess.run(['mrtransform', self.dwi_mask_ppd, '-warp', self.subj2templwarp, '-interp', 'nearest',
                        '-datatype', 'bit', self.dwi_mask_ppd_reg2templ])

    def computeTemplMask(self):
        mifstrs = []
        for mif in list(self.common_mask_dir.glob('*.mif')):
            mifstrs.append(str(mif))
        common_mask_paths = ' '.join(mifstrs)
        self.mask_templ = fba_dir / 'template_mask.mif'
        subprocess.run(['mrmath', common_mask_paths, 'min', self.mask_templ, '-datatype', 'bit'])

    # Step 12 - Compute a white matter template analysis fixel mask (defines fixels for statistical analysis)

    def segmentFODTempl(self):
        self.fixelmask_dir = fba_dir / 'fixel_mask'
        if self.fixelmask_dir.exists():
            shutil.rmtree(self.fixelmask_dir)
        subprocess.run(['fod2fixel', '-mask', self.mask_templ, '-fmls_peak_value', '0.06',
                        self.wmfod_templ, self.fixelmask_dir])

    # Step 13 - Warp FOD images to template space

    def warpFODs2Templ(self):
        self.wmfod_norm_reg2templ_notreoriented = fba_dir / (self.subjroot +
                                                             '_wmfod_norm_reg2templ_notreoriented.mif')
        subprocess.run(['mrtransform', '-force', '-warp', self.subj2templwarp, '-reorient_fod', 'no', self.wmfod_norm,
                        self.wmfod_norm_reg2templ_notreoriented])

    # Step 14 - Segment FOD images to estimate fixels and their apparent density fiber

    def segmentSubjFODs(self):
        self.fixel_reg2templ_notreoriented_dir = fba_dir / 'fixel_reg2templ_notreoriented'
        if self.fixel_reg2templ_notreoriented_dir.exists():
            shutil.rmtree(self.fixel_reg2templ_notreoriented_dir)
        self.fiber_density_notreoriented = str(self.subjroot + '_fd.mif')
        subprocess.run(['fod2fixel', '-mask', self.mask_templ, self.wmfod_norm_reg2templ_notreoriented,
                        self.fixel_reg2templ_notreoriented_dir, '-afd', self.fiber_density_notreoriented])

    # Step 15 - Reorient fixels (subject fixels to template space)

    def reorientFixels(self):
        self.fixel_reg2templ_dir = fba_dir / 'fixel_reg2templ'
        if self.fixel_reg2templ_dir.exists():
            shutil.rmtree(self.fixel_reg2templ_dir)
        subprocess.run(['fixelreorient', '-force', self.fixel_reg2templ_notreoriented_dir, self.subj2templwarp,
                        self.fixel_reg2templ_dir])

    # Step 16 - Assign subject fixels to template fixels

    def subjfxls2templfxls(self):
        self.subj_FD_reoriented = self.fixel_reg2templ_dir / (self.subjroot + '_fd.mif')
        FD = fba_dir / 'FD'
        subj_FD_matched = str(self.subjroot + '_fd.mif')
        subprocess.run(['fixelcorrespondence', self.subj_FD_reoriented, self.fixel_mask_dir, FD,
                        subj_FD_matched])

    def main(self, ses_dir):
        self.loadsubj()
        self.regfod2templ()
        self.warpMasks2Templ()
        self.computeTemplMask()
        self.segmentFODTempl()
        self.warpFODs2Templ()
        self.segmentSubjFODs()
        self.reorientFixels()
        self.subjfxls2templfxls()


def container(ses_dir):
    f = fba(ses_dir)


ses_dirs = (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-01') if Path(ses_dir / 'dwi').exists())

with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=1, verbose=10)(
        delayed(container)(ses_dir) for ses_dir in sorted(ses_dirs))
