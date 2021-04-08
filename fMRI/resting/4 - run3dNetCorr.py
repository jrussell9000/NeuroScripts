from pathlib import Path
import subprocess
import shutil
from joblib import parallel_backend, Parallel, delayed

BIDS_fmriprep = Path('/fast_scratch/jdr/resting/BIDS_fmriprep/fmriprep')
BN_Atlas = Path('/Users/jdrussell3/youthptsd/ROIs/HumanBrainnetomeAtlas/BN_Atlas_246_2mm.nii')


def runNetCorr(ses_dir):
    subjses_root = str(ses_dir.parent.name + "_" + ses_dir.name)
    func_dir = ses_dir / 'func'
    func_errts = func_dir / str(subjses_root +
                                "_task-EPIresting_space-MNI152NLin6Asym_desc-smoothAROMAnonaggr_bold_PSC_errts.nii.gz")
    fconn_dir = func_dir / 'fconn'
    if fconn_dir.exists():
        shutil.rmtree(fconn_dir)
        fconn_dir.mkdir()
    else:
        fconn_dir.mkdir()

    netcc_prefix = fconn_dir / str(subjses_root)
    subprocess.run(['3dNetCorr', '-inset', func_errts, '-in_rois', BN_Atlas, '-prefix', netcc_prefix])

def main(ses_dir):
    runNetCorr(ses_dir)

ses_dirs = (ses_dir for ses_dir in BIDS_fmriprep.glob('*/ses-01'))

with parallel_backend("loky", inner_max_num_threads=1):
    results = Parallel(n_jobs=16, verbose=1)(
        delayed(main)(ses_dir) for ses_dir in sorted(ses_dirs))
