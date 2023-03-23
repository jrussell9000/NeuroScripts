import pandas as pd
from pathlib import Path

pconncsv_dir = Path('/fast_scratch/jdr/ABCD/ABCD_3165_Pipe/pconns_working/pconn_csv')
dfs = [] 

for pconncsv in pconncsv_dir.glob('*.csv'):
    dfs.append(pd.read_csv(pconncsv))
    print(pconncsv)

len(dfs)