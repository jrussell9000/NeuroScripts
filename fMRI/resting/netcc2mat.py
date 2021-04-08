from pathlib import Path
import numpy as np
import scipy.io
import shutil

netcc_dir = Path('/fast_scratch/jdr/resting/NetCorrs')
mat_dir = netcc_dir / 'mat'
if mat_dir.exists():
    shutil.rmtree(mat_dir)
mat_dir.mkdir()

for netcc_file in netcc_dir.glob('*.netcc'):
    subjdir = netcc_file.name[:14]
    netcc = np.loadtxt(netcc_file, comments='#')
    netcc = np.delete(netcc, [0, 1], 0)
    scipy.io.savemat(mat_dir / (subjdir + '.mat'), {'netcc': netcc})
