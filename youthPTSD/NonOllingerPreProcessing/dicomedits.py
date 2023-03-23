import pydicom
import dicom_numpy
from pydicom import pydicom_series
import tarfile
import subprocess
import shutil
from pathlib import Path
import nibabel as nib

ollpreprocdir = Path('/fast_scratch/jdr/YouthPTSD/OllingerPreproc')
TEdiff = 3

rsPath = Path("/fast_scratch/jdr/YouthPTSD/OllingerPreproc/_142rescantest/run_1/sub-142_ses-02_task-Resting_bold.nii")

img = nib.load(rsPath)

affine = img.affine

data = img.get_fdata()

data0 = data[:,:,:,4:146:1]

newimg = nib.Nifti1Image(data0, affine)

nib.save(newimg, "/fast_scratch/jdr/YouthPTSD/OllingerPreproc/_142rescantest/run_1/test2.nii")


# print(img.header.get_data_shape())

# vol0 = img.slicer[:, :, :, 4:146]

# print(vol0.header.get_data_shape())

# test = nib.Nifti1Image(vol0, affine)

# nib.save(test, "test.nii")
