from pathlib import Path
import shutil

# This script prepends dwi volumes from the YouthPTSD study with the participants experiment group,
# and handedness as necessary for TBSS.

# Controls with ambidextrous, left, or right handedness
con_AH = ['sub-061', 'sub-062', 'sub-099']
con_LH = []
con_RH = ['sub-001', 'sub-003', 'sub-004', 'sub-005', 'sub-006', 'sub-009', 'sub-011',
          'sub-013', 'sub-014', 'sub-025', 'sub-042', 'sub-043', 'sub-044', 'sub-057',
          'sub-058', 'sub-059', 'sub-060', 'sub-064', 'sub-071', 'sub-076', 'sub-085',
          'sub-087', 'sub-089', 'sub-090', 'sub-092', 'sub-093', 'sub-094', 'sub-097',
          'sub-100', 'sub-106', 'sub-112', 'sub-117', 'sub-125', 'sub-128', 'sub-134',
          'sub-135', 'sub-140', 'sub-142', 'sub-145', 'sub-148', 'sub-149', 'sub-156',
          'sub-157']

# PTSD with ambidextrous, left, or right handedness
pts_AH = ['sub-031', 'sub-082', 'sub-127']
pts_LH = ['sub-026', 'sub-028', 'sub-036', 'sub-131']
pts_RH = ['sub-012', 'sub-019', 'sub-020', 'sub-021', 'sub-023', 'sub-024', 'sub-029',
          'sub-035', 'sub-037', 'sub-041', 'sub-045', 'sub-050', 'sub-056', 'sub-065',
          'sub-068', 'sub-070', 'sub-073', 'sub-075', 'sub-078', 'sub-079', 'sub-084',
          'sub-086', 'sub-091', 'sub-101', 'sub-104', 'sub-108', 'sub-118', 'sub-122',
          'sub-124', 'sub-129', 'sub-132', 'sub-133', 'sub-138', 'sub-139', 'sub-141',
          'sub-146', 'sub-147', 'sub-151', 'sub-153', 'sub-154', 'sub-155']

# Trauma-Exposed Controls with right handedness
tec_RH = ['sub-081', 'sub-107', 'sub-111', 'sub-114']

fadir = Path('/fast_scratch/jdr/dipy/FAs')
tbssdir = Path('/fast_scratch/jdr/dipy/tbss_proc')
for file in sorted(fadir.iterdir()):
    if file.is_file() and file.suffix == '.gz':
        sub = file.name.split('_')[0]
        if any(sub in con for con in con_AH):
            fa2file = Path(tbssdir, file.name)
            shutil.copy(file, Path(tbssdir, fa2file.name))
            subnum = sub[-3:]
            newname = Path(tbssdir, str('CON_AH_' + fa2file.name))
            fa2file.rename(newname)
        if any(sub in con for con in con_RH):
            fa2file = Path(tbssdir, file.name)
            shutil.copy(file, Path(tbssdir, fa2file.name))
            subnum = sub[-3:]
            newname = Path(tbssdir, str('CON_RH_' + fa2file.name))
            fa2file.rename(newname)
        if any(sub in p for p in pts_AH):
            fa2file = Path(tbssdir, file.name)
            shutil.copy(file, Path(tbssdir, fa2file.name))
            subnum = sub[-3:]
            newname = Path(tbssdir, str('PTS_AH_' + fa2file.name))
            fa2file.rename(newname)
        if any(sub in p for p in pts_LH):
            fa2file = Path(tbssdir, file.name)
            shutil.copy(file, Path(tbssdir, fa2file.name))
            subnum = sub[-3:]
            newname = Path(tbssdir, str('PTS_LH_' + fa2file.name))
            fa2file.rename(newname)
        if any(sub in p for p in pts_RH):
            fa2file = Path(tbssdir, file.name)
            shutil.copy(file, Path(tbssdir, fa2file.name))
            subnum = sub[-3:]
            newname = Path(tbssdir, str('PTS_RH_' + fa2file.name))
            fa2file.rename(newname)
        if any(sub in p for p in tec_RH):
            fa2file = Path(tbssdir, file.name)
            shutil.copy(file, Path(tbssdir, fa2file.name))
            subnum = sub[-3:]
            newname = Path(tbssdir, str('TEC_RH_' + fa2file.name))
            fa2file.rename(newname)
