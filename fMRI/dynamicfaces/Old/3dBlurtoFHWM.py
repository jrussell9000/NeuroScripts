from pathlib import Path
import subprocess
from joblib import parallel_backend, Parallel, delayed

BIDS_fmriprep = Path('/fast_scratch/jdr/dynamicfaces/BIDS_fmriprep/fmriprep/')


def smoothing(ses_dir):
    subjses_root = str(ses_dir.parent.name + "_" + ses_dir.name)
    func_dir = ses_dir / 'func'
    betas_input = func_dir / str(subjses_root + '_betas_motionDerivs.nii.gz')
    betas_output = func_dir / str(subjses_root + '_betas_motionDerivs_smooth6mm.nii.gz')
    subprocess.run(['3dmerge', '-1blur_fwhm', '6.0', '-prefix', betas_output, betas_input])
    # subprocess.run(['3dBlurToFWHM', '-input', betas_input, '-prefix', betas_output, '-FHWM', '6'])


ses_dirs = (ses_dir for ses_dir in BIDS_fmriprep.glob('*/ses-*'))

with parallel_backend("loky", inner_max_num_threads=2):
    results = Parallel(n_jobs=32, verbose=1)(
        delayed(smoothing)(ses_dir) for ses_dir in sorted(ses_dirs))
