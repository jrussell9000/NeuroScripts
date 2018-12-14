import string, os, sys, subprocess, shutil, time
from glob import glob

import nibabel as nib
import numpy as np

from dipy.segment.mask import median_otsu
from dipy.denoise.nlmeans import nlmeans
from dipy.denoise.noise_estimate import estimate_sigma
from dipy.io import read_bvals_bvecs
from dipy.io.bvectxt import reorient_vectors

from PNGViewer import PNGViewer

def setup_directories(output_dir, preprocess_dir, field_map_dir=''):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(preprocess_dir):
        os.makedirs(preprocess_dir)
    if not field_map_dir == '':
        os.makedirs(field_map_dir)

def check_dwi_acquisition_params(input_dwi, input_bval, input_bvec, input_index, output_bval, output_bvec, output_index, output_sliceOrder=''):
    
    dwi_img = nib.load(input_dwi)
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
    index = np.loadtxt(input_index)
    
    numberOfVolumes = dwi_img.header.get_data_shape()[3]
    numberOfSlices  = dwi_img.header.get_data_shape()[2]
    
    if bvals.shape[0] != numberOfVolumes:
        indices_to_remove = np.arange(numberOfVolumes, bvals_up.shape[0])
        bvals = np.delete(bvals, indices_to_remove)
        bvecs = np.delete(bvecs, indices_to_remove, 0)
        index = np.delete(index, indices_to_remove)

    np.savetxt(output_index, index, fmt='%i')
    np.savetxt(output_bval, bvals, fmt='%i')
    np.savetxt(output_bvec, np.transpose(bvecs), fmt='%.5f')

    #Create slice order flile
    if output_sliceOrder != '':
        slice_order = np.concatenate((np.arange(0,numberOfSlices,2),np.arange(1,numberOfSlices,2)),axis=0)
        np.savetxt(output_sliceOrder, slice_order, fmt='%i')



def manually_review_dwi(input_dwi, manual_corr_dir, output_file):
    if os.path.exists(manual_corr_dir):
        shutil.rmtree(manual_corr_dir)

    os.mkdir(manual_corr_dir)

    #First split the DWIs into individual volumes
    os.system('fslsplit ' + input_dwi + ' ' + manual_corr_dir + '/img_ -t')

    for nii in glob(manual_corr_dir + '*.nii*'):
        basename = nii.split('/')[len(nii.split('/'))-1]
        slice = basename.split('.')[0]
        outputPNG = manual_corr_dir + slice + '.png'
        os.system('slicer ' + nii + ' -L -a ' + outputPNG)

    #Run the manual correction
    png_viewer = PNGViewer(manual_corr_dir, subject_id)
    png_viewer.runPNGViewer()

    try:
        input('Please press enter after reviewing DWIs...')
    except SyntaxError:
        pass

    png_viewer.cleanupURL()
    os.system('mv ~/Downloads/Unknown* ' + output_file)
    shutil.rmtree(manual_corr_dir)

def remove_outlier_imgs(input_dwi, input_bval, input_bvec, input_index, input_report_file, output_dwi, output_bval, output_bvec, output_index, output_removed_imgs_dir, method='Threshold', percent_threshold=0.1):
    
    #Now, correct the DWI data
    dwi_img = nib.load(input_dwi)
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
    index = np.loadtxt(input_index)
    aff = dwi_img.get_affine()
    sform = dwi_img.get_sform()
    qform = dwi_img.get_qform()
    dwi_data = dwi_img.get_data()
    
    report_data = np.loadtxt(input_report_file, skiprows=1) #Skip the first row in the file as it contains text information
    numberOfVolumes = report_data.shape[0]
    
    if method == 'Threshold':
        numberOfSlices = report_data.shape[1] #Calculate the number of slices per volume
    
        #Calculate the threshold at which we will deem acceptable/unacceptable.
        threshold=np.round(float(percent_threshold)*numberOfSlices)
        sum_data = np.sum(report_data, axis=1);
        badVols = sum_data>=threshold
        goodVols=sum_data<threshold
        vols_to_remove = np.asarray(np.where(badVols)).flatten()
        vols_to_keep = np.asarray(np.where(goodVols)).flatten()

    elif method == 'Manual':
        if len(imgs_to_remove) != 0 and imgs_to_remove[0] != '""':
            vols_to_remove = []
        
            for img in report_data:
                img_to_remove = img.split('.')[0][1:]
                vols_to_remove.append(int(img_to_remove.split('_')[1]))
                    
            vols_to_remove = vols_to_remove.flatten()
            vols_to_keep = np.delete(np.arange(numberOfVolumes),vols_to_remove).flatten()

    data_to_keep= np.delete(dwi_data, vols_to_remove, 3)
    bvals_to_keep = np.delete(bvals, vols_to_remove)
    bvecs_to_keep = np.delete(bvecs, vols_to_remove, 0)
    index_to_keep = np.delete(index, vols_to_remove)
    
    data_to_remove= dwi_data[:,:,:,vols_to_remove]
    bvals_to_remove = bvals[vols_to_remove,]
    
    ##Write the bvals, bvecs, index, and corrected image data
    np.savetxt(output_index, index_to_keep, fmt='%i')
    np.savetxt(output_bval, bvals_to_keep, fmt='%i')
    np.savetxt(output_bvec, np.transpose(bvecs_to_keep), fmt='%.5f')
    
    corr_img = nib.Nifti1Image(data_to_keep.astype(np.float32), aff, dwi_img.header)
    corr_img.set_sform(sform)
    corr_img.set_qform(qform)
    nib.save(corr_img , output_dwi)
    
    if len(vols_to_remove) != 0:
        os.mkdir(output_removed_imgs_dir)
        imgs_to_remove= nib.Nifti1Image(data_to_remove.astype(np.float32), aff, dwi_img.header)
        imgs_to_remove.set_sform(sform)
        imgs_to_remove.set_qform(qform)
        nib.save(imgs_to_remove, output_removed_imgs_dir+'/imgsRemoved.nii.gz')
        np.savetxt(output_removed_imgs_dir+'/bvals_removed.txt', bvals_to_remove, fmt='%i', newline=" ")
        np.savetxt(output_removed_imgs_dir+'/volumes_removed.txt', vols_to_remove, fmt='%i', newline=" ")


def merge_multiple_phase_encodes(input_dwi_up, input_bvals_up, input_bvecs_up, input_index_up, input_acqparam_up, input_dwi_down, input_bvals_down, input_bvecs_down, input_index_down, input_acqparam_down, output_dwi, output_bvals, output_bvecs, output_index, output_acqparam):
    
    #First, get the size of the images
    img_up = nib.load(input_dwi_up)
    img_dn = nib.load(input_dwi_down)
    
    bvals_up, bvecs_up = read_bvals_bvecs(input_bvals_up, input_bvecs_up)
    bvals_dn, bvecs_dn = read_bvals_bvecs(input_bvals_down, input_bvecs_down)
    
    index_up = np.loadtxt(input_index_up)
    index_dn = np.loadtxt(input_index_down)
    
    acqparam_up = np.loadtxt(input_acqparam_up)
    acqparam_dn = np.loadtxt(input_acqparam_down)
    
    numImages_up = img_up.header.get_data_shape()[3]
    numImages_dn = img_dn.header.get_data_shape()[3]
    
    if bvals_up.shape[0] != numImages_up:
        indices_to_remove_up = np.arange(numImages_up, bvals_up.shape[0])
        bvals_up = np.delete(bvals_up, indices_to_remove_up)
        bvecs_up = np.delete(bvecs_up, indices_to_remove_up, 0)
    
    if bvals_dn.shape[0] != numImages_dn:
        indices_to_remove_dn = np.arange(numImages_dn, bvals_dn.shape[0])
        bvals_dn = np.delete(bvals_dn, indices_to_remove_dn)
        bvecs_dn = np.delete(bvecs_dn, indices_to_remove_dn, 0)

    
    #Read in the DWI ACQPARAMS FILE, DETERMINE WHICH IMAGES CORRESPOND TO UP AND DOWN, AND MERGE INTO SEPARATE FILES
    os.system('fslmerge -t ' + output_dwi + ' ' + input_dwi_up + ' ' + input_dwi_down)

    bvals = np.concatenate((bvals_up, bvals_dn), axis=0)
    bvecs = np.concatenate((bvecs_up, bvecs_dn), axis=0)
    index = np.concatenate((index_up, 2*index_dn), axis=0)
    acqparam = np.vstack((acqparam_up, acqparam_dn))

    
    np.savetxt(output_bvals, bvals, fmt='%i', newline=' ')
    np.savetxt(output_bvecs, bvecs.transpose(), fmt='%.8f')
    np.savetxt(output_index, index, fmt='%i', newline=' ')
    np.savetxt(output_acqparam, acqparam, fmt='%.5f')

def reorient_dwi_imgs(input_dwi, input_bval, input_bvec, output_dwi, output_bval, output_bvec, new_x, new_y, new_z, new_r, new_a, new_s):
    
    os.system('fslswapdim ' + input_dwi + ' ' + new_x + ' ' + new_y + ' ' + new_z + ' ' + output_dwi)
    
    #Now reorient the bvecs
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
    
    new_orient = new_r+new_a+new_s
    r_bvecs = reorient_vectors(bvecs, 'ras', new_orient, axis=1)
    
    N = len(bvals)
    fmt = '   %e' * N + '\n'
    
    open(output_bval, 'wt').write(fmt % tuple(bvals))
    
    bvf = open(output_bvec, 'wt')
    for dim_vals in r_bvecs.T:
        bvf.write(fmt % tuple(dim_vals))
    bvf.close()

def reorient_bvecs(input_bvecs, output_bvecs, new_x, new_y, new_z):

    bvecs = np.loadtxt(input_bvecs)
    permute = np.array([0, 1, 2])

    if new_x[0] == "x" and new_y[0] == "z" and new_z[0] == "y":
        permute = np.array([0, 2, 1])
    elif new_x[0] == "y" and new_y[0] == "x" and new_z[0] == "z":
        permute = np.array([1, 0, 2])
    elif new_x[0]== "y" and new_y[0] == "z" and new_z[0] == "x":
        permute = np.array([1, 2, 0])
    elif new_x[0] == "z" and new_y[0] == "y" and new_z[0] == "x":
        permute = np.array([2, 1, 0])
    elif new_x[0] == "z" and new_y[0] == "x" and new_z[0] == "y":
        permute = np.array([2, 0, 1])

    new_bvecs = np.empty(bvecs.shape)
    new_bvecs[0] = bvecs[permute[0]]
    new_bvecs[1] = bvecs[permute[1]]
    new_bvecs[2] = bvecs[permute[2]]


    if len(new_x) == 2 and new_x[1] == "-":
        new_bvecs[0] = -1.00*new_bvecs[0]
    if len(new_y) == 2 and new_y[1] == "-":
        new_bvecs[1] = -1.00*new_bvecs[1]
    if len(new_z) == 2 and new_z[1] == "-":
        new_bvecs[2] = -1.00*new_bvecs[2]

    np.savetxt(output_bvecs, new_bvecs, fmt='%.10f')

def convert_bvals_bvecs_to_fsl(input_bval_file, input_bvec_file, output_bval_file, output_bvec_file):
    input_bval = open(input_bval_file).read().splitlines()
    input_bvec = open(input_bvec_file).read().splitlines()
    
    number_of_volumes = len(input_bval)
    
    bvals = np.empty([number_of_volumes, 1])
    bvecs = np.empty([number_of_volumes, 3])

    for i in range(0,len(input_bval)):
        bvals[i] = int(float(input_bval[i].split(" ")[2]))

        bvecs[i,0] = float(input_bvec[i].split(" ")[2])
        bvecs[i,1] = float(input_bvec[i].split(" ")[3])
        bvecs[i,2] = float(input_bvec[i].split(" ")[4])

    np.savetxt(output_bval_file, bvals, fmt='%i')
    np.savetxt(output_bvec_file, np.transpose(bvecs), fmt='%.5f')





