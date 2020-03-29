import os
import nibabel as nib
from pathlib import Path


# def removeOutlierData(input_dwi, input_bval, input_bvec, input_index, input_report_file, output_dwi, output_bval,
#                       output_bvec, output_index, output_removed_imgs_dir, percent_threshold=0.1):
    
#     report_data = np.loadtxt(input_report_file, skiprows=1)  # Skip the first row in the file as it contains text information
#     numberOfVolumes = report_data.shape[0]
#     numberOfSlices = report_data.shape[1] #Calculate the number of slices per volume

#     #Calculate the threshold at which we will deem acceptable/unacceptable.
#     threshold=np.round(float(percent_threshold)*numberOfSlices)

#     sum_data = np.sum(report_data, axis=1);
#     badVols = sum_data>=threshold
#     goodVols=sum_data<threshold
#     vols_to_remove = np.asarray(np.where(badVols)).flatten()
#     vols_to_keep = np.asarray(np.where(goodVols)).flatten()

#     #Now, correct the DWI data
#     dwi_img = nib.load(input_dwi)
#     bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
#     index = np.loadtxt(input_index)
#     aff = dwi_img.get_affine()
#     sform = dwi_img.get_sform()
#     qform = dwi_img.get_qform()
#     dwi_data = dwi_img.get_data()

#     data_to_keep= np.delete(dwi_data, vols_to_remove, 3)
#     bvals_to_keep = np.delete(bvals, vols_to_remove)
#     bvecs_to_keep = np.delete(bvecs, vols_to_remove, 0)
#     index_to_keep = np.delete(index, vols_to_remove)

#     data_to_remove= dwi_data[:,:,:,vols_to_remove]
#     bvals_to_remove = bvals[vols_to_remove,]
    
#     ##Write the bvals, bvecs, index, and corrected image data
#     np.savetxt(output_index, index_to_keep, fmt='%i')
#     np.savetxt(output_bval, bvals_to_keep, fmt='%i')
#     np.savetxt(output_bvec, np.transpose(bvecs_to_keep), fmt='%.5f')

#     corr_img = nib.Nifti1Image(data_to_keep.astype(np.float32), aff, dwi_img.header)
#     corr_img.set_sform(sform)
#     corr_img.set_qform(qform)
#     nib.save(corr_img , output_dwi)

#     if len(vols_to_remove) != 0:
#     	os.mkdir(output_removed_imgs_dir)
#     	imgs_to_remove= nib.Nifti1Image(data_to_remove.astype(np.float32), aff, dwi_img.header)
#     	imgs_to_remove.set_sform(sform)
#     	imgs_to_remove.set_qform(qform)
#     	nib.save(imgs_to_remove, output_removed_imgs_dir+'/imgsRemoved.nii.gz')
#     	np.savetxt(output_removed_imgs_dir+'/bvals_removed.txt', bvals_to_remove, fmt='%i', newline=" ")
#     	np.savetxt(output_removed_imgs_dir+'/volumes_removed.txt', vols_to_remove, fmt='%i', newline=" ")
