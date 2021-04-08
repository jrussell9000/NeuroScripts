from pathlib import Path
import subprocess

T1s_dir = Path('/fast_scratch/jdr/amygseg/T1s')
T2s_dir = Path('/fast_scratch/jdr/amygseg/T2s')


def amygseg(T1recon_dir):
    T1recon_dir = Path(T1recon_dir)
    subjroot = T1recon_dir.name
    print(subjroot)
    print(T1recon_dir)
    T2scan = T2s_dir / (subjroot + '_acq-AxT2FLAIRCOPYDTI_T2w.nii')
    subprocess.run(['segmentHA_T2.sh', subjroot, T2scan, 'JDR', '1', T1s_dir])

for T1recon_dir in T1s_dir.glob('sub-*'):
    amygseg(T1recon_dir)
