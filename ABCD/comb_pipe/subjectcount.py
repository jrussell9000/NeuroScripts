import os
import pandas as pd
import subprocess
from joblib import parallel_backend, delayed, Parallel

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

manifest_path = '/fast_scratch/jdr/ABCD/ABCD_3165_Pipe/comb_pipe/datastructure_manifest.txt'

subjectIDs = pd.read_csv(manifest_path, header=1, sep='\t', usecols=['manifest_name'])['manifest_name'].str.split('.', n=1, expand=True)[0]
subjectIDs = subjectIDs.drop_duplicates().reset_index(drop=True)
subjectIDs.to_csv('subjectIDs.csv')
