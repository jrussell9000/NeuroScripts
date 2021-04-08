import math
import pandas as pd
import subprocess
from joblib import parallel_backend, delayed, Parallel
from pathlib import Path

BIDS_fmriprep = Path('/fast_scratch/jdr/resting/BIDS_fmriprep/fmriprep/')


class fmriprep2AFNI():

    def __init__(self, ses_dir):
        self.ses_dir = Path(ses_dir)
        self.subj_dir = ses_dir.parent
        self.subjroot = "_".join([self.subj_dir.name, self.ses_dir.name])
        self.main(self.ses_dir)

    def loadconfounds(self):
        self.func_dir = BIDS_fmriprep / self.subj_dir.name / self.ses_dir.name / 'func'
        confounds_tsv = self.func_dir / str(self.subjroot +
                                            '_task-EPIresting_desc-confounds_timeseries.tsv')

        self.confounds = pd.read_csv(confounds_tsv, delimiter='\t')

    def extractconfounds(self):
        for col in self.confounds.columns:
            if str(col)[:3] == "rot":
                self.confounds[col] = self.confounds[col]*(180/math.pi)

        csf = self.confounds[['csf']].copy()
        self.csfpath = self.func_dir / str(self.subjroot + '_CSF.1D')
        csf.to_csv(self.csfpath, sep='\t', index=False, header=False)

        wm = self.confounds[['white_matter']].copy()
        self.wmpath = self.func_dir / str(self.subjroot + '_WM.1D')
        wm.to_csv(self.wmpath, sep='\t', index=False, header=False)

        motion = self.confounds[['trans_x', 'trans_y', 'trans_z', 'rot_x', 'rot_y', 'rot_z']].copy()
        self.motionpath = self.func_dir / str(self.subj_dir.name + '_' + self.ses_dir.name + '_motion.1D')
        motion.to_csv(self.motionpath, sep='\t', index=False, header=False)

        # How many non-steady state TRs did fmriprep find? (i.e., how many columns in the confounds file start with
        # "non_steady_state_outlier")
        self.nonSteadyStateCount = self.confounds.loc[:,self.confounds.columns.str.startswith("non_steady_state_outlier").shape[1]
        self.nonSteadyStatepath = self.func_dir / str(self.subj_dir.name + '_' self.ses_dir.name + '_nonsteadystate.1D')

    def addconfounds(self):
        self.csf_demean = self.func_dir / str(self.subj_dir.name + '_' + self.ses_dir.name + '_CSF_demean.1D')
        subprocess.run(['1d_tool.py', '-infile', self.csfpath, '-set_nruns', '1', '-overwrite', '-demean',
                        '-write', self.csf_demean])

        self.wm_demean = self.func_dir / str(self.subj_dir.name + '_' + self.ses_dir.name + '_WM_demean.1D')
        subprocess.run(['1d_tool.py', '-infile', self.wmpath, '-set_nruns', '1', '-overwrite', '-demean',
                        '-write', self.wm_demean])

        self.motion_demean = self.func_dir / str(self.subj_dir.name + '_' + self.ses_dir.name + '_motion_demean.1D')
        subprocess.run(['1d_tool.py', '-infile', self.motionpath, '-set_nruns', '1', '-overwrite', '-demean',
                        '-write', self.motion_demean])

        self.motion_demean_deriv = self.func_dir / str(self.subj_dir.name + '_' + self.ses_dir.name +
                                                       '_motion_demean_deriv.1D')
        subprocess.run(['1d_tool.py', '-infile', self.motionpath, '-set_nruns', '1', '-overwrite', '-demean',
                        '-derivative', '-write', self.motion_demean_deriv])

        self.motion_censor_prefix = self.func_dir / str(self.subj_dir.name + '_' + self.ses_dir.name + '_motion')
        subprocess.run(['1d_tool.py', '-infile', self.motionpath, '-set_nruns', '1', '-overwrite', '-show_censor_count',
                        '-censor_prev_TR', '-censor_motion', '0.25', self.motion_censor_prefix])

    def compileConfounds(self):
        self.motion_censor_file = self.func_dir / str(self.subj_dir.name + '_' + self.ses_dir.name + '_motion_censor.1D')
        NumTRs = sum(1 for line in open(self.motion_censor_file))
        notCensored = subprocess.run(['1dsum', self.motion_censor_file], stdout=subprocess.PIPE, text=True).stdout
        totalCensored = int(NumTRs) - int(notCensored)
        percentCensored = totalCensored / NumTRs * 100
        compiledMotionFile = BIDS_fmriprep / 'ses-01_censorSummary_0.25mm.txt'
        f = open(compiledMotionFile, 'a')
        f.write(self.subj_dir.name + ": " + str(percentCensored) + '\n')

    def main(self, ses_dir):
        self.loadconfounds()
        self.extractconfounds()
        self.addconfounds()
        #self.compileConfounds()


ses_dirs = (ses_dir for ses_dir in BIDS_fmriprep.glob('*/ses-01'))


def container(ses_dir):
    c = fmriprep2AFNI(ses_dir)  # noqa: F841


with parallel_backend("loky", inner_max_num_threads=8):
    results = Parallel(n_jobs=1, verbose=1)(
        delayed(container)(ses_dir) for ses_dir in sorted(ses_dirs))
