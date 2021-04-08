#!/usr/bin/env python3
# coding: utf-8

# >>>>>>>>>>>>>>>>> #
# This script takes as input QSIprep's preprocessed output and reconstruction
# i.e., qsiprep and qsirecon and creates DTI metric based connectomes e.g.,
# sub-001_ses-01_mean_FA_connectome; see tck2connectome -help for more info
# Currently, this script is set to output Brainnetome connectomes.
# <<<<<<<<<<<<<<<<< #

import subprocess
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

qsiprep_dir = Path('/fast_scratch/jdr/BIDS_qsiprep/qsiprep/')
qsirecon_dir = Path('/fast_scratch/jdr/BIDS_qsiprep/qsirecon/')


class dwipreproc():

    def __init__(self, ses_dir):
        self.ses_dir = Path(ses_dir)
        self.subj_dir = ses_dir.parent
        self.subjroot = "_".join([self.subj_dir.name, self.ses_dir.name])
        self.main(self.ses_dir)

    def dwi2tensor(self):
        self.dwipreproc_dir = self.ses_dir / 'dwi'
        dwipreproc = self.dwipreproc_dir / str(self.subjroot + '_acq-AxDTIASSET_space-T1w_desc-preproc_dwi.nii.gz')
        bfile = self.dwipreproc_dir / str(self.subjroot + '_acq-AxDTIASSET_space-T1w_desc-preproc_dwi.b')
        self.tensor = self.dwipreproc_dir / str(self.subjroot + '_tensor.nii.gz')
        subprocess.run(['dwi2tensor', '-force', '-grad', bfile, dwipreproc, self.tensor])

    def tensor2FA(self):
        self.FA = self.dwipreproc_dir / str(self.subjroot + '_FA.nii.gz')
        self.RD = self.dwipreproc_dir / str(self.subjroot + '_RD.nii.gz')
        self.AD = self.dwipreproc_dir / str(self.subjroot + '_AD.nii.gz')
        self.MD = self.dwipreproc_dir / str(self.subjroot + '_MD.nii.gz')
        subprocess.run(['tensor2metric', '-force', self.tensor, '-fa', self.FA, '-rd', self.RD, '-ad', self.AD, '-adc',
                        self.MD])

    def tcksample(self):
        self.dwirecon_dir = qsirecon_dir / self.subj_dir.name / self.ses_dir.name / 'dwi'
        self.tracks = self.dwirecon_dir / str(self.subjroot +
                                              '_acq-AxDTIASSET_space-T1w_desc-preproc_space-T1w_desc-tracks_ifod2.tck')
        self.mean_FA_streamline = self.dwirecon_dir / str(self.subjroot + '_mean_FA_per_streamline.csv')
        self.mean_RD_streamline = self.dwirecon_dir / str(self.subjroot + '_mean_RD_per_streamline.csv')
        self.mean_AD_streamline = self.dwirecon_dir / str(self.subjroot + '_mean_AD_per_streamline.csv')
        self.mean_MD_streamline = self.dwirecon_dir / str(self.subjroot + '_mean_MD_per_streamline.csv')
        subprocess.run(['tcksample', '-force', self.tracks, self.FA, self.mean_FA_streamline, '-stat_tck', 'mean'])
        subprocess.run(['tcksample', '-force', self.tracks, self.RD, self.mean_RD_streamline, '-stat_tck', 'mean'])
        subprocess.run(['tcksample', '-force', self.tracks, self.AD, self.mean_AD_streamline, '-stat_tck', 'mean'])
        subprocess.run(['tcksample', '-force', self.tracks, self.MD, self.mean_MD_streamline, '-stat_tck', 'mean'])

    def tck2connectome(self):
        self.brainnetome_atlas = self.dwirecon_dir / str(self.subjroot +
                                                         '_acq-AxDTIASSET_space-T1w_desc-preproc_space-T1w_desc-brainnetome246_atlas.mif.gz')  # noqa: E501

        self.mean_FA_connectome = self.dwirecon_dir / str(self.subjroot + '_mean_FA_brainnetome246_connectome.csv')
        self.mean_RD_connectome = self.dwirecon_dir / str(self.subjroot + '_mean_RD_brainnetome246_connectome.csv')
        self.mean_AD_connectome = self.dwirecon_dir / str(self.subjroot + '_mean_AD_brainnetome246_connectome.csv')
        self.mean_MD_connectome = self.dwirecon_dir / str(self.subjroot + '_mean_MD_brainnetome246_connectome.csv')

        subprocess.run(['tck2connectome', '-force', self.tracks, self.brainnetome_atlas, self.mean_FA_connectome,
                        '-scale_file', self.mean_FA_streamline, '-stat_edge', 'mean'])
        subprocess.run(['tck2connectome', '-force', self.tracks, self.brainnetome_atlas, self.mean_RD_connectome,
                        '-scale_file', self.mean_RD_streamline, '-stat_edge', 'mean'])
        subprocess.run(['tck2connectome', '-force', self.tracks, self.brainnetome_atlas, self.mean_AD_connectome,
                        '-scale_file', self.mean_AD_streamline, '-stat_edge', 'mean'])
        subprocess.run(['tck2connectome', '-force', self.tracks, self.brainnetome_atlas, self.mean_MD_connectome,
                        '-scale_file', self.mean_MD_streamline, '-stat_edge', 'mean'])

    def main(self, ses_dir):
        self.dwi2tensor()
        self.tensor2FA()
        self.tcksample()
        self.tck2connectome()


# Running parallel jobs
ses_dirs = lambda: (ses_dir for ses_dir in qsiprep_dir.glob('*/ses-*'))  # noqa: E731

# Test subject
# ses_dirs = lambda: (ses_dir for ses_dir in qsiprep_dir.glob('*/ses-01')  # noqa: E731
#                     if ses_dir.parent.name == 'sub-001')


def container(ses_dir):
    c = dwipreproc(ses_dir)  # noqa: F841


with parallel_backend("loky", inner_max_num_threads=1):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(container)(ses_dir) for ses_dir in sorted(ses_dirs()))
