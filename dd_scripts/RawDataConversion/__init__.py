import string, os, sys, subprocess, shutil, time
from glob import glob

#Neuroimaging Modules
import dicom
import nibabel as nib

def create_index_acqparam_files(dcm_file, output_dwi, output_index, output_acqparams):

    dcmData = dicom.read_file(dcm_file)
    echoSpacing = dcmData[0x0043, 0x102c].value
    phaseEncodeDir = dcmData[0x0043, 0x108a].value
    assetFactor = dcmData[0x0043, 0x1083].value
    
    #Grab PEPOLAR from the series description
    series_description = dcmData[0x0008,0x103e].value
    pepolar_flag = series_description.split('_')[len(series_description.split('_'))-1]
    pepolar = int(pepolar_flag[len(pepolar_flag)-1])
    
    nii = nib.load(output_dwi)
    xDim = nii.header.get_data_shape()[0]
    numImages = nii.header.get_data_shape()[3]
        
    #Only if parallel imaging is turned on...
    acqFourthColumn = float(assetFactor[0])*float(xDim)*(0.001)*float(float(echoSpacing)/1000)
    
    indexFile = open(output_index, 'w')
    acqFile = open(output_acqparams, 'w')
    
    for i in range(int(numImages)):
        indexFile.write('1 ')

    if 'COL' in phaseEncodeDir:
        if int(pepolar) == 0:
            acqFile.write('0 1 0 ' + str(acqFourthColumn) + '\n')
        else:
            acqFile.write('0 -1 0 ' + str(acqFourthColumn) + '\n')
    else:
        if int(pepolar) == 0:
            acqFile.write('1 0 0 ' + str(acqFourthColumn) + '\n')
        else:
            acqFile.write('-1 0 0 ' + str(acqFourthColumn) + '\n')

    indexFile.close()
    acqFile.close()


def dicom_to_nifti_mri_convert(dwi_dcm_dir, output_dwi, output_index='', output_acqparams=''):

    src_dcms = glob(dwi_dcm_dir+'/*')
    os.system('mri_convert -i ' + src_dcms[0] + ' -o ' + output_dwi)

    if (output_index!='') and (output_acqparams!=''):
        create_index_acqparam_files(src_dcms[0], output_dwi, output_index, output_acqparams)

def dicom_to_nifti_dcm2nii(dwi_dcm_dir, output_dwi, output_index='', output_acqparams=''):
    
    os.chdir(dwi_dcm_dir)
    src_dcms = glob(dwi_dcm_dir+'/*')
    os.system('dcm2nii -r N -x N *')
    os.system('mv *.nii.gz ' + output_dwi)
    
    if (output_index!='') and (output_acqparams!=''):
        create_index_acqparam_files(src_dcms[0], output_dwi, output_index, output_acqparams)


























