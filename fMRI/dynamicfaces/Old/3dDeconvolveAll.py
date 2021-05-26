from pathlib import Path
import subprocess
from joblib import parallel_backend, Parallel, delayed

scriptname = '/Users/jdrussell3/NeuroScripts/fMRI/dynamicfaces/3dDeconvolvescript.sh'
BIDS_fmriprep = Path('/fast_scratch/jdr/dynamicfaces/BIDS_fmriprep/fmriprep/')


def runscript(ses_dir):
    subprocess.run(['bash', scriptname, ses_dir.parent.name, ses_dir.name])


ses_dirs = (ses_dir for ses_dir in BIDS_fmriprep.glob('*/ses-*'))

with parallel_backend("loky", inner_max_num_threads=4):
    results = Parallel(n_jobs=32, verbose=1)(
        delayed(runscript)(ses_dir) for ses_dir in sorted(ses_dirs))
