from pathlib import Path
import shutil, os, subprocess
from lib.Utils.PNGViewer.PNGViewer import PNGViewer

BIDSproc_dir = Path("/Volumes/Vol6/YouthPTSD/BIDS_processed")

for subjdir in sorted(BIDSproc_dir.glob('sub*')):
    for sesdir in sorted(subjdir.glob('ses*')):
        for dwidir in sesdir.glob('dwi'):

            subjroot = "_".join([subjdir.name, sesdir.name])
            preproc_dir = dwidir / 'preprocessed'
            qc_dir = preproc_dir / 'QC'
            preprocdwi = preproc_dir / (subjroot + "_ppd.mif")
            preprocdwinii = qc_dir / (subjroot + "_ppd.nii")
            subprocess.run(['mrconvert', preprocdwi, preprocdwinii])
            basename = qc_dir / subjroot
            afni_basename = qc_dir / (subjroot + ".nii")              
                
            subprocess.run(['3dTsplit4D', '-prefix', afni_basename, rawdwi])
            print("Slicing done for subject " + str(subjdir))
                
            for dwivol in sorted(qc_dir.glob('*.nii')):
                aslice = dwivol.stem
                outputPNG = Path(qc_dir, str(aslice + '.png'))
                subprocess.run(['slicer', dwivol, '-L', '-a', outputPNG])
            png_viewer = PNGViewer(str(qc_dir), str(basename))
            print("Output manual review HTML for " + str(subjdir))

            files_to_cleanup = qc_dir.glob('*.nii')
            for file in files_to_cleanup:
                os.remove(file)
            print("Cleanup done.")