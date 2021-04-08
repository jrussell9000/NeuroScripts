from pathlib import Path
import shutil
import subprocess
from joblib import parallel_backend, delayed, Parallel


def proc2scratch(scratch_dir, bidsproc_dir, subj_dir, ses_dir):
    preproc_dir = bidsproc_dir / subj_dir.name / ses_dir.name / 'dwi' / 'preprocessed'

    # Create temporary scratch directory to hold the preprocessed files
    scratch_out = scratch_dir / subj_dir.name / ses_dir.name
    scratch_out.mkdir(exist_ok=True, parents=True)

    # Copy the files from BIDS_Processed to the scratch directory
    files = (file for file in preproc_dir.glob("*") if file.is_file())
    for file in files:
        shutil.copy2(file, scratch_out)


def dtifit_run(ses_dir):
    subj_dir = ses_dir.parent
    subjroot = "_".join([subj_dir.name, ses_dir.name])
    source_dir = scratch_dir / subj_dir.name / ses_dir.name
    sourcedwi = source_dir / (subjroot + "_ppd.mif")
    sourcedwimask = source_dir / (subjroot + "_mask_ppd.mif")
    sourcebvec = source_dir / (subjroot + "_ppd.bvec")
    sourcebval = source_dir / (subjroot + "_ppd.bval")

    logfile = ses_dir / (subjroot + "_ppd.txt")

    with open(logfile, 'a') as log:

        # Make a 'tbss' directory inside the scratch directory that will hold the dtifit output
        tbss_dir = source_dir / 'tbss'
        tbss_dir.mkdir(exist_ok=True)

        # Copy the bvec and bval files to the tbss directory
        bvec = tbss_dir / (subjroot + "_ppd.bvec")
        bval = tbss_dir / (subjroot + "_ppd.bval")
        shutil.copy(sourcebvec, bvec)
        shutil.copy(sourcebval, bval)

        # Convert the DWI and DWI mask volumes to NII and put them in the TBSS directory
        dwinii = tbss_dir / (subjroot + "_ppd.nii")
        dwimasknii = tbss_dir / (subjroot + "_mask_ppd.nii")

        subprocess.run(['mrconvert', '-force', sourcedwi, dwinii], stdout=log, stderr=subprocess.STDOUT)
        subprocess.run(['mrconvert', '-force', sourcedwimask, dwimasknii], stdout=log, stderr=subprocess.STDOUT)

        # Run FSL's dtifit on the contents of the TBSS directory
        tbssbasename = Path(tbss_dir, subjroot)
        subprocess.run(['dtifit', '-V', '-k', dwinii, '-m', dwimasknii, '-r', bvec, '-b', bval, '-o', tbssbasename],
                       stdout=log, stderr=subprocess.STDOUT)


def back2proc(scratch_dir, bidsproc_dir, subj_dir, ses_dir):
    subj_dir = ses_dir.parent
    tbss_dir = scratch_dir / subj_dir.name / ses_dir.name / 'tbss'

    # Create a subject and session specific subdirectory to hold the files for TBSS processing (dwi/fsl/tbss)
    bidsproc_dir = bidsproc_dir / subj_dir.name / ses_dir.name / 'dwi' / 'fsl' / 'tbss'
    if bidsproc_dir.exists():
        shutil.rmtree(bidsproc_dir)

    # Copy the contents of the 'TBSS' scratch directory to its new location in BIDS_Processed
    shutil.copytree(tbss_dir, bidsproc_dir)

    # Remove the 'TBSS' scratch directory
    shutil.rmtree(Path(scratch_dir / subj_dir.name))


def run_all(subj_dir):

    bidsproc_dir = Path("/Users/jdrussell3/youthptsd/BIDS_Processed")
    scratch_dir = Path("/scratch/jdrussell3/tbssproc")
    scratch_dir.mkdir(exist_ok=True)

    ses_dirs = lambda: (ses_dir for ses_dir in bidsproc_dir.glob('*/ses-01')  # noqa: E731
                    if Path(ses_dir / 'dwi').exists())

    for ses_dir in ses_dirs:
        # Only run the script if the subject and session in BIDS_Processed has DWI data
        dwi_dir = ses_dir / 'dwi'
        if not dwi_dir.exists():
            next
        proc2scratch(scratch_dir, bidsproc_dir, subj_dir, ses_dir)
        dtifit_run(scratch_dir, subj_dir, ses_dir)
        back2proc(scratch_dir, bidsproc_dir, subj_dir, ses_dir)


bidsproc_dir = Path("/Users/jdrussell3/youthptsd/BIDS_Processed")
scratch_dir = Path("/scratch/jdrussell3/tbssproc")
scratch_dir.mkdir(exist_ok=True)

subj_dirs = (subj_dir for subj_dir in bidsproc_dir.iterdir() if subj_dir.is_dir())
with parallel_backend("loky", inner_max_num_threads=4):
    results = Parallel(n_jobs=4, verbose=1)(delayed(run_all)(subj_dir) for subj_dir in sorted(subj_dirs))
