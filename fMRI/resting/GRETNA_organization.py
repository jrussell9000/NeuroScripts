from pathlib import Path
import shutil

nii_dir = Path('/fast_scratch/jdr/resting/GRETNA/FunRaw')


def organize(nii):
    nii = Path(nii)
    subjroot = nii.name.split('_')[0]
    print(subjroot)
    nii_subj_dir = nii_dir / subjroot
    nii_subj_dir.mkdir()
    shutil.copy(nii, nii_subj_dir)


for nii in nii_dir.glob('*.nii'):
    organize(nii)
