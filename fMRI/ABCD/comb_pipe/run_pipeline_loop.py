import os
import pandas as pd
import subprocess
from joblib import parallel_backend, delayed, Parallel

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

manifest_path = '/Users/jdrussell3/NeuroScripts/fMRI/ABCD/comb_pipe/datastructure_manifest.txt'

subjectIDs = pd.read_csv(manifest_path, header=1, sep='\t', usecols=['manifest_name'])['manifest_name'].str.split('.', n=1, expand=True)[0]
subjectIDs = subjectIDs.drop_duplicates().reset_index(drop=True)


def run_pipeline(subjid):
    subprocess.run(['/fast_scratch/jdr/ABCD/ABCD_3165_Pipe/comb_pipe/run_pipeline_v2.sh', subjid])


subjIDs = (subjID for index, subjID in subjectIDs.items())

with parallel_backend("loky", inner_max_num_threads=2):
    results = Parallel(n_jobs=8, verbose=1)(
        delayed(run_pipeline)(subjID) for subjID in subjIDs)
