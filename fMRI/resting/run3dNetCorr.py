from pathlib import Path
import subprocess
import shutil

RS_dir = Path('/Users/jdrussell3/fast_scratch/resting/3dNetCorr')
BN_Atlas = Path(RS_dir, 'BN_Atlas', 'BN_Atlas_246_1mm_resampled.nii')
netccout_dir = Path('/Users/jdrussell3/fast_scratch/resting/3dNetCorr/netcorr')
if netccout_dir.exists():
    shutil.rmtree(netccout_dir)
netccout_dir.mkdir()
for ts in sorted(Path(RS_dir).glob('*.nii')):
    subjdir = ts.name[:14]
    print(subjdir)
    netcc_prefix = netccout_dir / subjdir
    print(netcc_prefix)
    subprocess.run(['3dNetCorr', '-inset', ts, '-in_rois', BN_Atlas, '-prefix', netcc_prefix])
