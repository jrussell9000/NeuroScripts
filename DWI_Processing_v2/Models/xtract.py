from pathlib import Path
import shutil, os, subprocess, time
from joblib import parallel_backend, delayed, Parallel
from random import randint

xtractproc_dir = Path("/Volumes/Vol6/YouthPTSD/xtract")

def run_xtract(bedpostxsubj_dir):
    subjses = bedpostxsubj_dir.name.split(".")[0]
    xtractout_dir = xtractproc_dir / (subjses + ".xtract")
    xtractout_dir.mkdir(exist_ok=True)
    subprocess.run(['xtract', '-bpx', bedpostxsubj_dir, '-out', xtractout_dir, '-species', 'HUMAN', '-gpu', '-native'])

    # See http://mindhive.mit.edu/node/1322
        a.	Diffusion to Structural: 

flirt –in nodif_brain –ref highres_brain_only.nii.gz –omat dif2highres.mat –searchrx -90 90 –searchry -90 90 –searchrz -90 90 –dof 6 –cost mutualinfo

        b.	Structural to diffusion: 

convert_xfm –omat highres2dif.mat –inverse dif2highres.mat

        c.	Structural to Standard:

flirt –in highres_brain_only.nii.gz –ref /usr/share/fsl/data/standard/avg152T1_brain.nii.gz –omat highres2standard.mat –searchrx -90 90 –searchry -90 90 –searchrz -90 90 –dof 12 –cost corratio

        d.	Standard to Structural:

convert_xfm –omat standard2highres.mat –inverse highres2standard.mat

        e.	Diffusion to Standard:

convert_xfm –omat dif2standard.mat –concat highres2standard.mat dif2highres.mat

        f.	Standard to Diffusion:

convert_xfm –omat standard2dif.mat –inverse dif2standard.mat



bedpostxsubj_dirs = (bedpostxsubj_dir for bedpostxsubj_dir in sorted(xtractproc_dir.glob('sub-003*bedpostX')))
for bedpostxsubj_dir in bedpostxsubj_dirs:
    run_xtract(bedpostxsubj_dir)
# with parallel_backend("loky", inner_max_num_threads=8):
#     results = Parallel(n_jobs=8, verbose = 1)(delayed(run_bedpostx)(subj_dir) for subj_dir in sorted(subj_dirs))
