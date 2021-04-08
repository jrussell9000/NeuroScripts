from pathlib import Path
import subprocess
from joblib import parallel_backend, delayed, Parallel

T1s_dir = Path('/fast_scratch/jdr/amygseg/T1s')
nCoresPerJob = "12"
nJobs = 8


def thalseg(T1recon_dir):
    T1recon_dir = Path(T1recon_dir)
    subjroot = T1recon_dir.name
    subprocess.run(['segmentThalamicNuclei.sh', subjroot, T1s_dir])


with parallel_backend("loky", inner_max_num_threads=nCoresPerJob):
    results = Parallel(n_jobs=nJobs, verbose=1)(
        delayed(thalseg)(T1recon_dir) for T1recon_dir in sorted(T1s_dir.glob('sub-*')))
