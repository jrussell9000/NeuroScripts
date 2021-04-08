#!/usr/bin/env python3
# coding: utf-8

import subprocess
import os
import shutil
from pathlib import Path
from joblib import parallel_backend, delayed, Parallel

# >>>>>>>>>>>>>>>>> #
# SCRIPT PARAMETERS #
# <<<<<<<<<<<<<<<<< #

bidsproc_dir = Path('/Volumes/Vol6/YouthPTSD/BIDS_Processed/')
template_dir = Path('/fast_scratch/jdr/mrtrix/cross_sec')

if not template_dir.exists():
    template_dir.mkdir()

nCoresPerJob = "12"
nJobs = 8

mrtrix_env = os.environ.copy()
mrtrix_env["MRTRIX_NTHREADS"] = nCoresPerJob


class ss3t_prep():

    def __init__(self, ses_dir):
        self.ses_dir = ses_dir
        self.subj_dir = ses_dir.parent
        self.preproc_dir = ses_dir / 'dwi' / 'preprocessed'
        self.subjroot = "_".join([self.subj_dir.name, self.ses_dir.name])
        self.main(ses_dir)

    def makedirs(self):
        self.proc_dir = self.ses_dir / 'dwi' / 'processed'
        if not self.proc_dir.exists():
            self.proc_dir.mkdir()

        self.mrtrix_dir = self.proc_dir / 'mrtrix'
        if not self.mrtrix_dir.exists():
            self.mrtrix_dir.mkdir()

        self.ss3t_dir = self.mrtrix_dir / 'ss3t'
        if self.ss3t_dir.exists():
            shutil.rmtree(self.ss3t_dir)
        self.ss3t_dir.mkdir()

        self.response_dir = template_dir / 'response_files'
        if not self.response_dir.exists():
            self.response_dir.mkdir()

        self.response_wm_dir = self.response_dir / 'wm'
        if not self.response_wm_dir.exists():
            self.response_wm_dir.mkdir()

        self.response_gm_dir = self.response_dir / 'gm'
        if not self.response_gm_dir.exists():
            self.response_gm_dir.mkdir()

        self.response_csf_dir = self.response_dir / 'csf'
        if not self.response_csf_dir.exists():
            self.response_csf_dir.mkdir()

    def dwi2response(self):
        self.dwi_ppd = self.preproc_dir / (self.subjroot + '_ppd.mif')
        self.dwi_mask_ppd = self.preproc_dir / (self.subjroot + '_mask_ppd.mif')
        self.response_wm = self.ss3t_dir / (self.subjroot + '_response_wm.txt')
        self.response_gm = self.ss3t_dir / (self.subjroot + '_response_gm.txt')
        self.response_csf = self.ss3t_dir / (self.subjroot + '_response_csf.txt')
        os.chdir('/tmp')
        subprocess.run(['dwi2response', '-scratch', '/tmp/', '-mask', self.dwi_mask_ppd,
                        'dhollander', self.dwi_ppd, self.response_wm, self.response_gm, self.response_csf],
                       env=mrtrix_env, stdout=self.log, stderr=subprocess.STDOUT)

    def copyResponseFiles(self):
        shutil.copy2(self.response_wm, self.response_wm_dir)
        shutil.copy2(self.response_gm, self.response_gm_dir)
        shutil.copy2(self.response_csf, self.response_csf_dir)

    def main(self, ses_dir):
        if not template_dir.exists():
            template_dir.mkdir()
        log_dir = template_dir / 'logs'
        if not log_dir.exists():
            log_dir.mkdir()
        ss3tprep_log_dir = log_dir / 'ss3t_prep'
        if not ss3tprep_log_dir.exists():
            ss3tprep_log_dir.mkdir()
        logfile = ss3tprep_log_dir / (self.subjroot + "_ss3t_prep.log")
        with open(logfile, 'w') as self.log:
            try:
                self.makedirs()
                self.dwi2response()
                self.copyResponseFiles()
            except subprocess.CalledProcessError as e:
                self.log.write('ERROR: SS3T File Preparation FAILED with error: ' + str(e.output))
                next
            self.log.write("%"*40 + "\n" + "\t ----DONE---- \n" + "%"*40)


def mean_response(template_dir):

    response_dir = template_dir / 'response_files'

    os.chdir(response_dir)
    os.system('responsemean -force wm/*.txt group_average_response_wm.txt')
    os.system('responsemean -force gm/*.txt group_average_response_gm.txt')
    os.system('responsemean -force csf/*.txt group_average_response_csf.txt')
    group_average_response_wm = Path(response_dir / 'group_average_response_wm.txt')
    group_average_response_gm = Path(response_dir / 'group_average_response_gm.txt')
    group_average_response_csf = Path(response_dir / 'group_average_response_csf.txt')
    return group_average_response_wm, group_average_response_gm, group_average_response_csf


class ss3t():

    def __init__(self, ses_dir, grpavgresp_wm, grpavgresp_gm, grpavgresp_csf):
        self.subj_dir = ses_dir.parent
        self.preproc_dir = ses_dir / 'dwi' / 'preprocessed'
        self.subjroot = "_".join([self.subj_dir.name, ses_dir.name])
        self.proc_dir = ses_dir / 'dwi' / 'processed'
        self.mrtrix_dir = self.proc_dir / 'mrtrix'
        self.ss3t_dir = self.mrtrix_dir / 'ss3t'

        self.grpavgresp_wm = grpavgresp_wm
        self.grpavgresp_gm = grpavgresp_gm
        self.grpavgresp_csf = grpavgresp_csf

        self.input_dwi = self.preproc_dir / (self.subjroot + '_ppd.mif')
        self.input_mask = self.preproc_dir / (self.subjroot + '_mask_ppd.mif')
        self.main(ses_dir)

    def ss3t_csd(self):
        self.wmfod = self.ss3t_dir / (self.subjroot + '_wmfod.mif')
        self.gm = self.ss3t_dir / (self.subjroot + '_gm.mif')
        self.csf = self.ss3t_dir / (self.subjroot + '_csf.mif')
        subprocess.run(['ss3t_csd_beta1', '-force', self.input_dwi, self.grpavgresp_wm, self.wmfod, self.grpavgresp_gm,
                        self.gm, self.grpavgresp_csf, self.csf, '-mask', self.input_mask],
                       env=mrtrix_env, stdout=self.log, stderr=subprocess.STDOUT)

    def normalize(self):
        self.wmfod_norm = self.ss3t_dir / (self.subjroot + '_wmfod_norm.mif')
        self.gm_norm = self.ss3t_dir / (self.subjroot + '_gm_norm.mif')
        self.csf_norm = self.ss3t_dir / (self.subjroot + '_csf_norm.mif')
        subprocess.run(['mtnormalise', self.wmfod, self.wmfod_norm, self.gm, self.gm_norm, self.csf, self.csf_norm,
                        '-mask', self.input_mask], env=mrtrix_env, stdout=self.log, stderr=subprocess.STDOUT)

    def main(self, ses_dir):
        log_dir = template_dir / 'logs'
        if not log_dir.exists():
            log_dir.mkdir()
        ss3t_log_dir = log_dir / 'ss3t'
        if not ss3t_log_dir.exists():
            ss3t_log_dir.mkdir()
        logfile = ss3t_log_dir / (self.subjroot + "_ss3t.log")
        with open(logfile, 'w') as self.log:
            try:
                self.ss3t_csd()
                self.normalize()
            except subprocess.CalledProcessError as e:
                self.log.write('ERROR: SS3T FAILED with error: ' + str(e.output))
                next
            self.log.write("%"*40 + "\n" + "\t ----DONE---- \n" + "%"*40)


def ss3tprep_container(ses_dir):
    c = ss3t_prep(ses_dir)  # noqa: F841


def ss3t_container(ses_dir):
    c = ss3t(ses_dir, group_average_response_wm, group_average_response_gm, group_average_response_csf)  # noqa: F841


ses_dirs = lambda: (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-01')  # noqa: E731
                    if Path(ses_dir / 'dwi').exists())

with parallel_backend("loky", inner_max_num_threads=nCoresPerJob):
    results = Parallel(n_jobs=nJobs, verbose=1)(
        delayed(ss3tprep_container)(ses_dir) for ses_dir in sorted(ses_dirs()))

group_average_response_wm, group_average_response_gm, group_average_response_csf = mean_response(template_dir)

with parallel_backend("loky", inner_max_num_threads=nCoresPerJob):
    results = Parallel(n_jobs=nJobs, verbose=1)(
        delayed(ss3t_container)(ses_dir) for ses_dir in sorted(ses_dirs()))
