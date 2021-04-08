from pathlib import Path
import shutil

input_dir = Path('/scratch/jdrussell3/EmoReg_Justin_Conn/niftis/func/neg')
output_dir = Path('/scratch/jdrussell3/projects/iapsreg/dparsf/FunImgARWSDFCBsym')

for subjfile in sorted(input_dir.glob('*.nii')):
    subjid = subjfile.name[:7]
    outputsubj_dir = Path(output_dir, subjid)
    if outputsubj_dir.exists():
        shutil.copy2(subjfile, outputsubj_dir)
    else:
        outputsubj_dir.mkdir()
        shutil.copy2(subjfile, outputsubj_dir)
