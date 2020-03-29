import string, os, sys, subprocess, shutil, time
from glob import glob

import numpy as np
#import matplotlib.pyplot as plt

#Neuroimaging Modules
import dicom
import nibabel as nib
import dipy.reconst.dti as dti

from dipy.segment.mask import median_otsu
from dipy.denoise.nlmeans import nlmeans
from dipy.denoise.noise_estimate import estimate_sigma
from dipy.core.gradients import gradient_table
from dipy.io import read_bvals_bvecs
from dipy.reconst.dti import fractional_anisotropy
from dipy.external.fsl import write_bvals_bvecs
from dipy.io.bvectxt import reorient_vectors

from ..PNGViewer.PNGViewer import PNGViewer

if sys.platform == 'linux2':
    eddy='eddy_openmp'
    eddy_cuda='eddy_cuda8.0'
    fitmcmd_exe = os.path.dirname(__file__)+'/bin/linux/fitmcmicro'
    fitmicro_exe = os.path.dirname(__file__)+'/bin/linux/fitmicrodt'
else:
    eddy='eddy'
    fitmcmd_exe = os.path.dirname(__file__)+'/bin/mac/fitmcmicro'
    fitmicro_exe = os.path.dirname(__file__)+'/bin/mac/fitmicrodt'

def setupDirectories(output_dir, preprocess_dir, field_map_dir=""):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(preprocess_dir):
        os.makedirs(preprocess_dir)
    if not field_map_dir == "":
	os.makedirs(field_map_dir)

def convertDcmToNifti_mriConvert(dwi_dcm_dir, output_dwi, output_index='', output_acqparams=''):

    src_dcms = glob(dwi_dcm_dir+"/*.dcm")
    os.system("mri_convert -i " + src_dcms[0] + " -o " + output_dwi)

    dcmData = dicom.read_file(src_dcms[0])
    echoSpacing = dcmData[0x0043, 0x102c].value
    phaseEncodeDir = dcmData[0x0043, 0x108a].value

    nii = nib.load(output_dwi)
    xDim = nii.header.get_data_shape()[0]
    numImages = nii.header.get_data_shape()[3]

    acqFourthColumn = 0.5*float(xDim)*(0.001)*float(float(echoSpacing)/1000)

    if output_index != '' and output_acqparams != '':
    	indexFile = open(output_index, "w")
    	acqFile = open(output_acqparams, "w")

   	for i in range(int(numImages)):
        	indexFile.write("1 ")

        if "ROW" in phaseEncodeDir:
         	acqFile.write(" 0 -1 0 " + str(acqFourthColumn) + "\n")
        else:
            	acqFile.write(" -1 0 0 " + str(acqFourthColumn) + "\n")

    	indexFile.close()
    	acqFile.close()

def convertDcmToNifti_dcm2nii(dwi_dcm_dir, output_dwi, output_index='', output_acqparams=''):
    
    os.chdir(dwi_dcm_dir)
    os.system('dcm2nii *')
    os.system('mv *.nii.gz ' + output_dwi)
    
    if (output_index!='') and (output_acqparams!=''):
        src_dcms = glob(dwi_dcm_dir+'/*.dcm')
        dcmData = dicom.read_file(src_dcms[0])
        echoSpacing = dcmData[0x0043, 0x102c].value
        phaseEncodeDir = dcmData[0x0043, 0x108a].value
        
        nii = nib.load(output_dwi)
        xDim = nii.header.get_data_shape()[0]
        numImages = nii.header.get_data_shape()[3]
        
        acqFourthColumn = 0.5*float(xDim)*(0.001)*float(float(echoSpacing)/1000)
        
        indexFile = open(output_index, 'w')
        acqFile = open(output_acqparams, 'w')
        
        for i in range(int(numImages)):
            indexFile.write('1 ')
            
            if 'ROW' in phaseEncodeDir:
                acqFile.write(' 0 -1 0 ' + str(acqFourthColumn) + '\n')
            else:
                acqFile.write(' -1 0 0 ' + str(acqFourthColumn) + '\n')

        indexFile.close()
        acqFile.close()


def manuallyReviewDWI(subject_id, input_dwi, manual_corr_dir, output_file):
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

def performDWICorrection(input_dwi, input_bval, input_bvec, input_index, input_acqparam, output_dwi, output_bval, output_bvec, output_index, output_acqparam, img_corr_file):
    
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
    index = np.loadtxt(input_index)
    acqparams = np.loadtxt(input_acqparam)
    img = nib.load(input_dwi)
    data = img.get_data()

    aff = img.get_affine()
    sform = img.get_sform()
    qform = img.get_qform()

    #First, check to see if bvals, bvecs and image file have the same lengths. If not, correct the bvals, and bvecs to match the images
    numImages = img.header.get_data_shape()[3]
    numBvals = bvals.shape[0]
    indices_to_remove = np.arange(numImages, numBvals)
    bvals = np.delete(bvals, indices_to_remove)
    bvecs = np.delete(bvecs, indices_to_remove, 0)

    #First read in the file that contains the images to remove
    imgs_to_remove = open(img_corr_file, 'r').readlines()
    imgs_to_remove = imgs_to_remove[1:len(imgs_to_remove)] #Always remove the first element
    
    manual_correction_dir = os.path.dirname(img_corr_file) + '/tmp/'
    os.mkdir(manual_correction_dir)
    os.system('fslsplit ' + input_dwi + ' ' + manual_correction_dir + 'img_ -t')
    
    if len(imgs_to_remove) != 0 and imgs_to_remove[0] != '""':
        indices = []
        imgs_to_remove_list = []

        for img in imgs_to_remove:
            img_to_remove = img.split(".")[0][1:]
            imgs_to_remove_list.append(manual_correction_dir + img_to_remove + ".nii.gz")
            indices.append(int(img_to_remove.split("_")[1]))

        #Remove the elements
        data_corr = np.delete(data, indices, 3)
        bvals_corr = np.delete(bvals, indices)
        bvecs_corr = np.delete(bvecs, indices, 0)
        index_corr = np.delete(index, indices)
        acqparams_corr = np.delete(acqparams, indices, 0)

        corr_img = nib.Nifti1Image(data_corr,aff)
        corr_img.set_sform(sform)
        corr_img.set_qform(qform)

        nib.save(corr_img, output_dwi)
        
        N = len(bvals_corr)
        fmt = '%f ' * N + ' \n'
        
        open(output_bval, 'wt').write(fmt % tuple(bvals_corr))

        bvf = open(output_bvec, 'wt')
        for dim_vals in bvecs_corr.T:
            bvf.write(fmt % tuple(dim_vals))
        bvf.close()

        np.savetxt(output_index, index_corr, fmt='%.5f')
        np.savetxt(output_acqparam, acqparams_corr, fmt='%.5f')


    else:
        nib.save(img, output_dwi)
        np.savetxt(output_index, index)
        np.savetxt(output_acqparam, acqparams)

        N = len(bvals)
        fmt = '   %e' * N + '\n'

        open(output_bval, 'wt').write(fmt % tuple(bvals))
        
        bvf = open(output_bvec, 'wt')
        for dim_vals in bvecs.T:
            bvf.write(fmt % tuple(dim_vals))
        bvf.close()

    os.system('rm -rf ' + manual_correction_dir)

def performNoiseCorrection(input_dwi, output_dwi, output_noise=''):

    if(output_noise != ''):
        os.system('dwidenoise ' + input_dwi + ' ' + output_dwi + ' -noise ' + output_noise + ' -quiet -force')
    else:
        os.system('dwidenoise ' + input_dwi + ' ' + output_dwi + ' -quiet -force')

def performGibbsCorrection(input_dwi, output_dwi):
    #This function uses MRTRix to perform Gibbs ringing correction
    os.system('mrdegibbs ' + input_dwi + ' ' + output_dwi  + ' -quiet -force')

def mergeMultiEncodeDWI(input_dwi_up, input_bvals_up, input_bvecs_up, input_index_up, input_dwi_down, input_bvals_down, input_bvecs_down, input_index_down, output_dwi, output_bvals, output_bvecs, output_index):
    
    #First, get the size of the images
    img_up = nib.load(input_dwi_up)
    img_dn = nib.load(input_dwi_down)
    
    bvals_up, bvecs_up = read_bvals_bvecs(input_bvals_up, input_bvecs_up)
    bvals_dn, bvecs_dn = read_bvals_bvecs(input_bvals_down, input_bvecs_down)
    
    index_up = np.loadtxt(input_index_up)
    index_dn = np.loadtxt(input_index_down)
    
    numImages_up = img_up.header.get_data_shape()[3]
    numImages_dn = img_dn.header.get_data_shape()[3]
    
    numBvals_up = bvals_up.shape[0]
    numBvals_dn = bvals_dn.shape[0]
    
    
    indices_to_remove_up = np.arange(numImages_up, numBvals_up)
    indices_to_remove_dn = np.arange(numImages_dn, numBvals_dn)

    bvals_up = np.delete(bvals_up, indices_to_remove_up)
    bvecs_up = np.delete(bvecs_up, indices_to_remove_up, 0)
    index_up = np.delete(index_up, indices_to_remove_up)
    
    bvals_dn = np.delete(bvals_dn, indices_to_remove_dn)
    bvecs_dn = np.delete(bvecs_dn, indices_to_remove_dn, 0)
    index_dn = np.delete(index_dn, indices_to_remove_up)
    
    
    #Read in the DWI ACQPARAMS FILE, DETERMINE WHICH IMAGES CORRESPOND TO UP AND DOWN, AND MERGE INTO SEPARATE FILES
    os.system('fslmerge -t ' + output_dwi + ' ' + input_dwi_up + ' ' + input_dwi_down)

    bvals = np.concatenate((bvals_up, bvals_dn), axis=0)
    bvecs = np.concatenate((bvecs_up, bvecs_dn), axis=0)
    index = np.concatenate((index_up, index_dn), axis=0)
    
    np.savetxt(output_bvals, bvals, fmt='%i', newline=' ')
    np.savetxt(output_bvecs, bvecs.transpose(), fmt='%.8f')
    np.savetxt(output_index, index, fmt='%i', newline=' ')
    
#    output_dir_base = os.path.dirname(output_bvals)
#    write_bvals_bvecs(bvals,bvecs,output_dir_base,'tmp_')
#    os.rename(output_dir_base+'/tmp_bvals', output_bvals)
#    os.rename(output_dir_base+'/tmp_bvecs', output_bvecs)


def correctBvecs(input_bvecs, output_bvecs, new_x, new_y, new_z):

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


def performTopUp(input_dwi, input_bvals, input_index, input_acqparams, output_topup_base, config_file='', field_output=''):

    #First, find the indices of the B0 images
    dwi_img = nib.load(input_dwi)
    aff = dwi_img.get_affine()
    sform = dwi_img.get_sform()
    qform = dwi_img.get_qform()
    dwi_data = dwi_img.get_data()
    
    bvals = np.loadtxt(input_bvals)
    index = np.loadtxt(input_index)
    acqparams = np.loadtxt(input_acqparams)
    ii = np.where(bvals == 0)

    b0_data = dwi_data[:,:,:,np.asarray(ii).flatten()]
    b0_indices = index[ii].astype(int)
    b0_acqparams=acqparams[b0_indices-1]
    
    output_dir = os.path.dirname(output_topup_base)
    tmp_acqparams = output_dir + '/tmp.acqparams.txt'
    tmp_b0 = output_dir + '/tmp.B0.nii.gz'
    
    b0_imgs = nib.Nifti1Image(b0_data, aff, dwi_img.header)
    nib.save(b0_imgs, tmp_b0)
    np.savetxt(tmp_acqparams, b0_acqparams, fmt='%.8f')
    
    topup_command='topup --imain='+tmp_b0+' --datain='+tmp_acqparams+' --out='+output_topup_base
    
    if config_file != '':
        topup_command += ' --config='+config_file
    if field_output != '':
        topup_command += ' --fout='+field_output

    os.system(topup_command)
    os.system('rm -rf ' + output_dir + '/tmp*')

def performEddyCorrection(input_dwi, input_bvec, output_dwi, output_bvec, output_log):
    eddy_output_basename = output_dwi[0:len(output_dwi)-7]
    logFile = eddy_output_basename + '.ecclog'

    if os.path.exists(logFile):
        os.remove(logFile)
    
    command = 'eddy_correct ' + input_dwi + ' ' + eddy_output_basename + ' 0'
    os.system(command)

    os.system("mv " + logFile + " " + output_log)

    #Rotate b-vecs after doing the eddy correction
    os.system('fdt_rotate_bvecs ' + input_bvec+ ' ' + output_bvec + ' ' + output_log)

def performEddy(input_dwi, input_bval, input_bvec, input_index, input_acqparam, output_dwi, output_bvec, topup_base='', external_b0='', repol=0, data_shelled=0, mb='', cuda='', mporder=0, slice_order='', mask_img=''):

    output_dir = os.path.dirname(output_dwi)
    tmp_mask = output_dir + '/tmp_mask.nii.gz'
    
    if mask_img == '':
        tmp_dwi = output_dir + '/tmp_img.nii.gz'
        os.system('fslroi ' + input_dwi + ' ' + tmp_dwi + ' 0 1')
        os.system('bet ' + tmp_dwi + ' ' + output_dir + '/tmp -m')
    else:
        os.system('cp ' + mask_img + ' ' + tmp_mask)

    eddy_output_basename = output_dwi[0:len(output_dwi)-7]
    if cuda != '':
        command = eddy_cuda + ' --imain=' + input_dwi + ' --mask=' + tmp_mask + ' --index=' + input_index + ' --acqp=' + input_acqparam + ' --bvecs=' + input_bvec + ' --bvals=' + input_bval + ' --out='  + eddy_output_basename
    else:
        command = eddy + ' --imain=' + input_dwi + ' --mask=' + tmp_mask + ' --index=' + input_index + ' --acqp=' + input_acqparam + ' --bvecs=' + input_bvec + ' --bvals=' + input_bval + ' --out='  + eddy_output_basename

    if topup_base != '':
        command += ' --topup='+topup_base
    if external_b0 != '':
        command += ' --field='+external_b0
    if repol != 0:
        command += ' --repol '
    if data_shelled != 0:
        command += ' --data_is_shelled '
    if mb != '':
        command += ' --mb ' + mb
    if mporder != 0 and slice_order != '':
        command += ' --niter=8 --fwhm=10,8,4,2,0,0,0,0 --ol_type=both --mporder='+str(mporder)+' --s2v_niter=5 --slspec='+slice_order + ' --s2v_lambda=1 --s2v_interp=trilinear'
  
    print command
    os.system(command)
    #Rotate b-vecs after doing the eddy correction
    os.system('mv ' + eddy_output_basename+'.eddy_rotated_bvecs ' + output_bvec)

    #Remove temporary mask
    os.system('rm -rf ' + tmp_mask)
    if mask_img == '':
        os.system('rm -rf ' + tmp_dwi)

def removeOutlierData(input_dwi, input_bval, input_bvec, input_index, input_report_file, output_dwi, output_bval, output_bvec, output_index, output_removed_imgs_dir, percent_threshold=0.1):
    
    report_data = np.loadtxt(input_report_file, skiprows=1) #Skip the first row in the file as it contains text information
    numberOfVolumes = report_data.shape[0]
    numberOfSlices = report_data.shape[1] #Calculate the number of slices per volume

    #Calculate the threshold at which we will deem acceptable/unacceptable.
    threshold=np.round(float(percent_threshold)*numberOfSlices)

    sum_data = np.sum(report_data, axis=1);
    badVols = sum_data>=threshold
    goodVols=sum_data<threshold
    vols_to_remove = np.asarray(np.where(badVols)).flatten()
    vols_to_keep = np.asarray(np.where(goodVols)).flatten()

    #Now, correct the DWI data
    dwi_img = nib.load(input_dwi)
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
    index = np.loadtxt(input_index)
    aff = dwi_img.get_affine()
    sform = dwi_img.get_sform()
    qform = dwi_img.get_qform()
    dwi_data = dwi_img.get_data()

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


def reorientImages(input_dwi, input_bval, input_bvec, output_dwi, output_bval, output_bvec, new_x, new_y, new_z, new_r, new_a, new_s):

    os.system("fslswapdim " + input_dwi + " " + new_x + " " + new_y + " " + new_z + " " + output_dwi)

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

def createMask(input_dwi, output_mask, output_dwi=''):

    img = nib.load(input_dwi)
    data = img.get_data()
    masked_data, mask = median_otsu(data, 2,2)

    aff = img.get_affine()
    sform = img.get_sform()
    qform = img.get_qform()

    #Save these files
    masked_img = nib.Nifti1Image(masked_data.astype(np.float32), aff, img.header)
    mask_img = nib.Nifti1Image(mask.astype(np.float32), aff,  img.header)

    masked_img.set_sform(sform)
    masked_img.set_qform(qform)
    mask_img.set_sform(sform)
    mask_img.set_qform(qform)

    nib.save(mask_img, output_mask)

    if output_dwi != '':
        nib.save(masked_img, output_dwi)

def createMask_skullStrip(input_dwi, output_mask, output_dwi=''):

    output_root, img = os.path.split(output_mask)

    tmpImg = output_root + '/tmp.nii.gz'
    tmpMask = output_root + '/tmp_mask.nii.gz'

    os.system('fslroi ' + input_dwi + ' ' + tmpImg + ' 0 1')
    os.system('3dSkullStrip -input ' + tmpImg + ' -prefix ' + tmpMask)

    os.system('fslmaths ' + tmpMask + ' -bin ' + output_mask)
    
    if output_dwi != '':
        os.system('fslmaths ' + input_dwi + ' -mas ' + output_mask + ' ' + output_dwi)

    os.system('rm -rf ' + tmpImg)
    os.system('rm -rf ' + tmpMask)

def createMask_bet(input_dwi, output_mask, output_dwi='', f_threshold=''):
    
    output_root, img = os.path.split(output_mask)
    tmpImg = output_root + '/tmp.nii.gz'
    tmpMask = output_root + '/tmp_mask.nii.gz'
    
    os.system('fslroi ' + input_dwi + ' ' + tmpImg + ' 0 1')
    
    if f_threshold != '':
        os.system('bet ' + tmpImg + ' ' + tmpMask + ' -f ' + f_threshold)
    else:
        os.system('bet ' + tmpImg + ' ' + tmpMask)
    
    os.system('fslmaths ' + tmpMask + ' -bin ' + output_mask)
    
    if output_dwi != '':
        os.system('fslmaths ' + input_dwi + ' -mas ' + output_mask + ' ' + output_dwi)

    os.system('rm -rf ' + tmpImg)
    os.system('rm -rf ' + tmpMask)

def createMask_mrtrix(input_dwi, input_bval, input_bvec, output_mask, output_dwi=''):

    output_dir = os.path.dirname(output_dwi)
    tmp_dwi = output_dir + '/tmp.dwi.mif'
    os.system('mrconvert -fslgrad '+ input_bvec + ' ' + input_bval + ' ' + input_dwi + ' ' + tmp_dwi)
    os.system('dwi2mask ' +  tmp_dwi + ' ' + output_mask + ' -quiet')
    
    if output_dwi != '':
        os.system('fslmaths ' + input_dwi + ' -mas ' + output_mask + ' ' + output_dwi)

    os.system('rm -rf ' + output_dir + '/tmp*')

def fieldMapCorrection_fugue(input_dwi, input_fm, input_fm_ref, output_dwi, field_map_dir, unwarpdir, dwellTime, fm_ref_mask_img=''):

    if not os.path.exists(field_map_dir):
        os.mkdir(field_map_dir)
    
    #Skull-strip the reference
    if input_fm_ref.endswith(".nii"):
        input_fm_ref_base = input_fm_ref[0:len(input_fm_ref)-4]
    else:
        input_fm_ref_base = input_fm_ref[0:len(input_fm_ref)-7]

    fm_ref_mask = input_fm_ref_base + ".mask.nii.gz"
    if fm_ref_mask_img == '':
        os.system("bet " + input_fm_ref + " " + fm_ref_mask)
    else:
	os.system('fslmaths ' + input_fm_ref + ' -mas ' + fm_ref_mask_img + ' ' + fm_ref_mask)

    if input_fm.endswith(".nii"):
        input_fm_base = input_fm[0:len(input_fm)-4]
    else:
        input_fm_base = input_fm[0:len(input_fm)-7]

    fm_rads = input_fm_base + ".rads.nii.gz"

    #Now scale the field map and mask
    os.system("fslmaths " + input_fm + " -mul 6.28 -mas " + fm_ref_mask + " " + fm_rads)
  

    input_fm_ref_warp = input_fm_ref_base + ".warp.nii.gz"
    #Warp the reference image
    print "fugue -i " + fm_ref_mask + " --unwarpdir="+unwarpdir + " --dwell="+dwellTime + " --loadfmap="+fm_rads + " -w " + input_fm_ref_warp
    os.system("fugue -i " + fm_ref_mask + " --unwarpdir="+unwarpdir + " --dwell="+dwellTime + " --loadfmap="+fm_rads + " -w " + input_fm_ref_warp)

    dwi_ref = field_map_dir + "/dwi_ref.nii.gz"
    os.system("fslroi " + input_dwi + " " + dwi_ref + " 0 1" )

    #Align warped reference to the dwi data
    fm_ref_warp_align = input_fm_ref_base + ".warp.aligned.nii.gz"
    fm_ref_mat = input_fm_ref_base + "_2_dwi.mat"
    os.system("flirt -in " + input_fm_ref_warp + " -ref " + dwi_ref + " -out " + fm_ref_warp_align + " -omat " + fm_ref_mat)

    #Apply this to the field map
    fm_rads_warp = input_fm_base + ".rads.warp.nii.gz"
    os.system("flirt -in " + fm_rads + " -ref " + dwi_ref + " -applyxfm -init " + fm_ref_mat + " -out " + fm_rads_warp)

    #Now, undistort the image
    os.system("fugue -i " + input_dwi + " --icorr --unwarpdir="+unwarpdir + " --dwell="+dwellTime + " --loadfmap="+fm_rads_warp+" -u " + output_dwi)


def prep_externalFieldMap(input_dwi, input_fm, input_fm_ref, dwellTime, unwarpdir, field_map_dir):
    
    if not os.path.exists(field_map_dir):
        os.mkdir(field_map_dir)
    
    #Skull-strip the reference
    if input_fm_ref.endswith(".nii"):
        input_fm_ref_base = input_fm_ref[0:len(input_fm_ref)-4]
    else:
        input_fm_ref_base = input_fm_ref[0:len(input_fm_ref)-7]
    
    fm_ref_mask = input_fm_ref_base + ".mask.nii.gz"

    os.system("bet " + input_fm_ref + " " + fm_ref_mask)

    if input_fm.endswith(".nii"):
        input_fm_base = input_fm[0:len(input_fm)-4]
    else:
        input_fm_base = input_fm[0:len(input_fm)-7]

    fm_rads = input_fm_base + ".rads.nii.gz"
    
    #Now scale the field map and mask
    os.system("fslmaths " + input_fm + " -mul 6.28 -mas " + fm_ref_mask + " " + fm_rads)
    
    input_fm_ref_warp = input_fm_ref_base + ".warp.nii.gz"
    #Warp the reference image
    os.system("fugue -i " + fm_ref_mask + " --unwarpdir="+unwarpdir + " --dwell="+dwellTime + " --loadfmap="+fm_rads + " -w " + input_fm_ref_warp)
    
    dwi_ref = field_map_dir + "/dwi_ref.nii.gz"
    os.system("fslroi " + input_dwi + " " + dwi_ref + " 0 1" )
    
    #Align warped reference to the dwi data
    fm_ref_warp_align = input_fm_ref_base + ".warp.aligned.nii.gz"
    fm_ref_mat = input_fm_ref_base + "_2_dwi.mat"
    os.system("flirt -in " + input_fm_ref_warp + " -ref " + dwi_ref + " -out " + fm_ref_warp_align + " -omat " + fm_ref_mat)
    
    #Apply this to the field map
    fm_rads_warp = input_fm_base + ".rads.warp.nii.gz"
    os.system("flirt -in " + fm_rads + " -ref " + dwi_ref + " -applyxfm -init " + fm_ref_mat + " -out " + fm_rads_warp)

    fm_hz_warp = input_fm_base + ".hz.warp.nii.gz"
    os.system("fslmaths " + fm_rads_warp + " -mul 0.1592 " + fm_hz_warp)


def removeNoise(input_dwi, input_bval, input_bvec, mask_image, output_dwi):

    img = nib.load(input_dwi)
    data = img.get_data()
    mask = nib.load(mask_image).get_data()
    aff = img.get_affine()
    sform = img.get_sform()
    qform = img.get_qform()

    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]

    sigma = estimate_sigma(data)
    sigma = np.mean(sigma[ii])

    den = nlmeans(data,sigma=sigma, mask=mask)

    den_img = nib.Nifti1Image(den.astype(np.float32), aff, img.header)
    den_img.set_sform(sform)
    den_img.set_qform(qform)
    nib.save(den_img, output_dwi)

def fit_dti_model(input_dwi, input_bval, input_bvec, output_dir, fit_type='', mask='', bmax='', mask_tensor='T'):

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    img = nib.load(input_dwi)
    data = img.get_data()
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)

    if mask != '':
        mask_data = nib.load(mask).get_data()

    aff = img.get_affine()
    sform = img.get_sform()
    qform = img.get_qform()

    if bmax != "":
        jj = np.where(bvals >= bmax)
        bvals = np.delete(bvals, jj)
        bvecs = np.delete(bvecs, jj, 0)
        data = np.delete(data, jj , axis=3)

    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]
    b0_average = np.mean(data[:,:,:,ii], axis=3)

    gtab = gradient_table(bvals, bvecs)

    if fit_type == 'RESTORE':
        sigma = estimate_sigma(data)
        #calculate the average sigma from the b0's
        sigma = 2.00*np.mean(sigma[ii])

        dti_model = dti.TensorModel(gtab, fit_method='RESTORE', sigma=sigma)
        
        if mask != '':
            dti_fit = dti_model.fit(data, mask_data)
        else:
            dti_fit = dti_model.fit(data)

    elif fit_type != 'RESTORE' and fit_type != '':
        dti_model = dti.TensorModel(gtab, fit_method=fit_type)
        
        if mask != '':
            dti_fit = dti_model.fit(data, mask_data)
        else:
            dti_fit = dti_model.fit(data)

    else:
        dti_model = dti.TensorModel(gtab)
        
        if mask != '':
            dti_fit = dti_model.fit(data, mask_data)
        else:
            dti_fit = dti_model.fit(data)

    estimate_data = dti_fit.predict(gtab, S0=b0_average)
    residuals = np.absolute(data - estimate_data)

    evecs = dti_fit.evecs.astype(np.float32)
    evals = dti_fit.evals.astype(np.float32)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    #Define output imgs
    output_evecs = output_dir + '/dti_eigenvectors.nii.gz'
    output_tensor = output_dir + '/dti_tensor.nii.gz'
    dti_tensor_spd = output_dir + '/dti_tensor_spd.nii.gz'
    output_tensor_norm = output_dir + '/dti_tensor_norm.nii.gz'
    dti_tensor_spd_masked = output_dir + '/dti_tensor_spd_masked.nii.gz'
    norm_mask = output_dir + '/norm_mask.nii.gz'
    output_V1 = output_dir + '/dti_V1.nii.gz'
    output_V2 = output_dir + '/dti_V2.nii.gz'
    output_V3 = output_dir + '/dti_V3.nii.gz'
    output_L1 = output_dir + '/dti_L1.nii.gz'
    output_L2 = output_dir + '/dti_L2.nii.gz'
    output_L3 = output_dir + '/dti_L3.nii.gz'

    output_fa = output_dir + '/dti_FA.nii.gz'
    output_md = output_dir + '/dti_MD.nii.gz'
    output_rd = output_dir + '/dti_RD.nii.gz'
    output_ad = output_dir + '/dti_AD.nii.gz'

    output_res = output_dir + '/dti_residuals.nii.gz'

    evecs_img = nib.Nifti1Image(evecs, img.get_affine(), img.header)
    nib.save(evecs_img, output_evecs)

    dti_V1 = evecs[:,:,:,:,0]
    V1_img = nib.Nifti1Image(dti_V1,aff,img.header)
    V1_img.set_sform(sform)
    V1_img.set_qform(qform)
    nib.save(V1_img, output_V1)

    dti_V2 = evecs[:,:,:,:,1]
    V2_img = nib.Nifti1Image(dti_V2,aff,img.header)
    V2_img.set_sform(sform)
    V2_img.set_qform(qform)
    nib.save(V2_img, output_V2)

    dti_V3 = evecs[:,:,:,:,2]
    V3_img = nib.Nifti1Image(dti_V3,aff,img.header)
    V3_img.set_sform(sform)
    V3_img.set_qform(qform)
    nib.save(V3_img, output_V3)

    dti_L1 = evals[:,:,:,0]
    L1_img = nib.Nifti1Image(dti_L1,aff,img.header)
    L1_img.set_sform(sform)
    L1_img.set_qform(qform)
    nib.save(L1_img, output_L1)

    dti_L2 = evals[:,:,:,1]
    L2_img = nib.Nifti1Image(dti_L2,aff,img.header)
    L2_img.set_sform(sform)
    L2_img.set_qform(qform)
    nib.save(L2_img, output_L2)

    dti_L3 = evals[:,:,:,2]
    L3_img = nib.Nifti1Image(dti_L3,aff,img.header)
    L3_img.set_sform(sform)
    L3_img.set_qform(qform)
    nib.save(L3_img, output_L3)

    res_img = nib.Nifti1Image(residuals.astype(np.float32), aff,img.header)
    res_img.set_sform(sform)
    res_img.set_qform(qform)
    nib.save(res_img, output_res)

    os.chdir(output_dir)
    os.system('TVFromEigenSystem -basename dti -type FSL -out ' + output_tensor)
    os.system('TVtool -in ' + output_tensor + ' -scale 1000.00 -out ' + output_tensor)
    os.system('rm -rf dti_V* dti_L*')

    #Create the SPD
    os.system('TVtool -in ' + output_tensor + ' -spd -out ' + dti_tensor_spd)

    if mask_tensor == 'T':
        os.system('TVtool -in ' + dti_tensor_spd + ' -norm -out ' + output_tensor_norm)
        os.system('BinaryThresholdImageFilter ' +  output_tensor_norm + ' ' + norm_mask + ' 0.01 3.0 1 0')
        os.system('TVtool -in ' + dti_tensor_spd + ' -mask ' + norm_mask + ' -out ' + dti_tensor_spd_masked)
        os.system('TVEigenSystem -in ' + dti_tensor_spd_masked + ' -type FSL')

        #Calculate Eigenvectors and Eigenvalues, FA, MD, RD, AD
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -fa -out ' + output_fa)
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -rd -out ' + output_rd)
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -ad -out ' + output_ad)
        os.system('TVtool -in ' + dti_tensor_spd_masked + ' -tr -out ' + output_md)
        os.system('fslmaths ' + output_md + ' -div 3.0 ' + output_md)

    else:
        #Calculate FA, MD, RD, AD
        os.system('TVEigenSystem -in ' + dti_tensor_spd + ' -type FSL')
        os.system('TVtool -in ' + dti_tensor_spd + ' -fa -out ' + output_fa)
        os.system('TVtool -in ' + dti_tensor_spd + ' -rd -out ' + output_rd)
        os.system('TVtool -in ' + dti_tensor_spd + ' -ad -out ' + output_ad)
        os.system('TVtool -in ' + dti_tensor_spd + ' -tr -out ' + output_md)
        os.system('fslmaths ' + output_md + ' -div 3.0 ' + output_md)


def fit_dti_model_camino(input_dwi, input_bval, input_bvec, output_dir, fit_type='', mask='', bmax=''):

    #First create temporary camino style data
    camino_dwi = output_dir + '/tmp.dwi.Bfloat'
    camino_scheme = output_dir + '/tmp.dwi.scheme'
    camino_tensor = output_dir + '/tmp.dti.Bfloat'
    os.system('image2voxel -4dimage ' + input_dwi + ' -outputfile ' + camino_dwi)
    os.system('fsl2scheme -bvecfile ' + input_bvec + ' -bvalfile ' + input_bval + ' > ' + camino_scheme)

    if fit_type == 'RESTORE':
        data = nib.load(input_dwi).get_data()
        bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec)
        values = np.array(bvals)
        ii = np.where(values == bvals.min())[0]
        sigma = estimate_sigma(data)
        sigma = np.mean(sigma[ii])

        #FIT TENSOR
        os.system('modelfit -inputfile ' + camino_dwi + ' -schemefile ' + camino_scheme + ' -model restore -sigma ' + str(sigma) + ' -bgmask ' + mask + ' -outputfile ' + camino_tensor)

    elif fit_type == 'WLLS':
        os.system('modelfit -inputfile ' + camino_dwi + ' -schemefile ' + camino_scheme + ' -model ldt_wtd -bgmask ' + mask + ' -outputfile ' + camino_tensor)
                  
    elif fit_type == 'NLLS':
        os.system('modelfit -inputfile ' + camino_dwi + ' -schemefile ' + camino_scheme + ' -model nldt_pos -bgmask ' + mask + ' -outputfile ' + camino_tensor)
                  
    else:
        os.system('modelfit -inputfile ' + camino_dwi + ' -schemefile ' + camino_scheme + ' -model ldt -bgmask ' + mask + ' -outputfile ' + camino_tensor)
                
    #Convert the data back to NIFTI
    output_root = output_dir + 'dti_'
    os.system('dt2nii -inputfile ' + camino_tensor + ' -gzip -inputdatatype double -header ' + input_dwi + ' -outputroot ' + output_root)


    #Define the output file paths
    output_tensor = output_dir + '/dti_tensor.nii.gz'
    output_tensor_spd = output_dir + '/dti_tensor_spd.nii.gz'
    output_tensor_norm = output_dir + '/dti_tensor_norm.nii.gz'
    norm_mask = output_dir + '/norm_mask.nii.gz'
    output_tensor_spd_masked = output_dir + '/dti_tensor_spd_masked.nii.gz'

    output_V1 = output_dir + '/dti_V1.nii.gz'
    output_V2 = output_dir + '/dti_V2.nii.gz'
    output_V3 = output_dir + '/dti_V3.nii.gz'
    output_L1 = output_dir + '/dti_L1.nii.gz'
    output_L2 = output_dir + '/dti_L2.nii.gz'
    output_L3 = output_dir + '/dti_L3.nii.gz'
    
    output_fa = output_dir + '/dti_FA.nii.gz'
    output_md = output_dir + '/dti_MD.nii.gz'
    output_rd = output_dir + '/dti_RD.nii.gz'
    output_ad = output_dir + '/dti_AD.nii.gz'
    
    output_res = output_dir + '/dti_residuals.nii.gz'

    os.system('TVtool -in ' + output_root + 'dt.nii.gz -scale 1e9 -out ' + output_tensor)
    os.system('TVtool -in ' + output_tensor + ' -spd -out ' + output_tensor_spd)
    os.system('TVtool -in ' + output_tensor_spd + ' -norm -out ' + output_tensor_norm)
    os.system('BinaryThresholdImageFilter ' +  output_tensor_norm + ' ' + norm_mask + ' 0.01 3.0 1 0')
    os.system('TVtool -in ' + output_tensor_spd + ' -mask ' + norm_mask + ' -out ' + output_tensor_spd_masked)
    os.system('TVFromEigenSystem -basename dti -type FSL -out ' + output_tensor_spd_masked)

    #Calculate FA, MD, RD, AD
    os.system('TVtool -in ' + output_tensor_spd_masked + ' -fa -out ' + output_fa)
    os.system('TVtool -in ' + output_tensor_spd_masked + ' -rd -out ' + output_rd)
    os.system('TVtool -in ' + output_tensor_spd_masked + ' -ad -out ' + output_ad)
    os.system('TVtool -in ' + output_tensor_spd_masked + ' -tr -out ' + output_md)
    os.system('fslmaths ' + output_md + ' -div 3.00 ' + output_md)

    #Output the eigenvectors and eigenvalues
    os.system('TVEigenSystem -in ' + output_tensor_spd_masked + ' -type FSL')
    dti_basename=nib.filename_parser.splitext_addext(output_tensor_spd_masked)
    os.system('mv ' + dti_basename + '_V1.nii.gz ' + output_V1)
    os.system('mv ' + dti_basename + '_V2.nii.gz ' + output_V2)
    os.system('mv ' + dti_basename + '_V3.nii.gz ' + output_V3)
    os.system('mv ' + dti_basename + '_L1.nii.gz ' + output_L1)
    os.system('mv ' + dti_basename + '_L2.nii.gz ' + output_L2)
    os.system('mv ' + dti_basename + '_L3.nii.gz ' + output_L3)

    #Clean up files
    os.system('rm -rf ' + dti_basename +'_[V,L]* ' + output_dir + '/tmp*')


def fit_fwdti_model(input_dwi, input_bval, input_bvec, output_dir, fit_method='', mask=''):

    import dipy.reconst.fwdti as fwdti
    
    if fit_method=='':
        fit_method = 'WLS'

    img = nib.load(input_dwi)
    data = img.get_data()
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec,)
    gtab = gradient_table(bvals, bvecs)

    if mask != '':
        mask_data = nib.load(mask).get_data()

    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]
    b0_average = np.mean(data[:,:,:,ii], axis=3)
    
    fwidtimodel = fwdti.FreeWaterTensorModel(gtab, fit_method)

    if mask!='':
        fwidti_fit = fwidtimodel.fit(data, mask_data)
    else:
        fwidti_fit = fwidtimodel.fit(data)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    output_evecs = output_dir + '/fwe_dti_eigenvectors.nii.gz'
    output_evals = output_dir + '/fwe_dti_eigenvalues.nii.gz'

    output_fa = output_dir + '/fwe_dti_FA.nii.gz'
    output_md = output_dir + '/fwe_dti_MD.nii.gz'
    output_rd = output_dir + '/fwe_dti_RD.nii.gz'
    output_ad = output_dir + '/fwe_dti_AD.nii.gz'
    output_f = output_dir + '/fwe_dti_F.nii.gz'

    #Calculate Parameters for FWDTI Model
    evals_img = nib.Nifti1Image(fwidti_fit.evals.astype(np.float32), img.get_affine(),img.header)
    nib.save(evals_img, output_evals)
    os.system('fslreorient2std ' + output_evals + ' ' + output_evals)
    
    evecs_img = nib.Nifti1Image(fwidti_fit.evecs.astype(np.float32), img.get_affine(),img.header)
    nib.save(evecs_img, output_evecs)
    os.system('fslreorient2std ' + output_evecs+ ' ' + output_evecs)
    
    fwidti_fa = fwidti_fit.fa
    fwidti_fa_img = nib.Nifti1Image(fwidti_fa.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_fa_img, output_fa)
    os.system('fslreorient2std ' + output_fa + ' ' + output_fa)
    
    fwidti_md = fwidti_fit.md
    fwidti_md_img = nib.Nifti1Image(fwidti_md.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_md_img, output_md)
    os.system('fslreorient2std ' + output_md+ ' ' + output_md)

    fwidti_ad = fwidti_fit.ad
    fwidti_ad_img = nib.Nifti1Image(fwidti_ad.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_ad_img, output_ad)
    os.system('fslreorient2std ' + output_ad+ ' ' + output_ad)
    
    fwidti_rd = fwidti_fit.rd
    fwidti_rd_img = nib.Nifti1Image(fwidti_rd.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_rd_img, output_rd)
    os.system('fslreorient2std ' + output_rd+ ' ' + output_rd)

    fwidti_f = fwidti_fit.f
    fwidti_f_img = nib.Nifti1Image(fwidti_f.astype(np.float32), img.get_affine(),img.header)
    nib.save(fwidti_f_img, output_f)
    os.system('fslreorient2std ' + output_f+ ' ' + output_f)


def fit_dki_model(input_dwi, input_bval, input_bvec, output_dir, fit_method='', mask='', include_micro_fit='FALSE'):

    import dipy.reconst.dki as dki
    import scipy.ndimage.filters as filters
    
    if fit_method == '':
        fit_method = 'OLS'

    img = nib.load(input_dwi)
    data = img.get_data()
    bvals, bvecs = read_bvals_bvecs(input_bval, input_bvec,)
    gtab = gradient_table(bvals, bvecs)
    
    if mask != '':
        mask_data = nib.load(mask).get_data()

    values = np.array(bvals)
    ii = np.where(values == bvals.min())[0]
    b0_average = np.mean(data[:,:,:,ii], axis=3)

    #Recommended to smooth data:
    fwhm = 1.25
    gauss_std = fwhm / np.sqrt(8 * np.log(2))  # converting fwhm to Gaussian std
    data_smooth = np.zeros(data.shape)
    for v in range(data.shape[-1]):
        data_smooth[..., v] = filters.gaussian_filter(data[..., v], sigma=gauss_std)

    dkimodel = dki.DiffusionKurtosisModel(gtab, fit_method)

    if mask != '':
        dkifit = dkimodel.fit(data_smooth, mask_data)
    else:
        dkifit = dkimodel.fit(data_smooth)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    output_evecs = output_dir + '/dki_eigenvectors.nii.gz'
    output_evals = output_dir + '/dki_eigenvalues.nii.gz'

    output_fa = output_dir + '/dki_FA.nii.gz'
    output_md = output_dir + '/dki_MD.nii.gz'
    output_rd = output_dir + '/dki_RD.nii.gz'
    output_ad = output_dir + '/dki_AD.nii.gz'
    output_mk = output_dir + '/dki_MK.nii.gz'
    output_ak = output_dir + '/dki_AK.nii.gz'
    output_rk = output_dir + '/dki_RK.nii.gz'

    #Calculate Parameters for Kurtosis Model
    evals_img = nib.Nifti1Image(dkifit.evals.astype(np.float32), img.get_affine(),img.header)
    nib.save(evals_img, output_evals)
    os.system('fslreorient2std ' + output_evals+ ' ' + output_evals)

    evecs_img = nib.Nifti1Image(dkifit.evecs.astype(np.float32), img.get_affine(),img.header)
    nib.save(evecs_img, output_evecs)
    os.system('fslreorient2std ' + output_evecs+ ' ' + output_evecs)

    dki_fa = dkifit.fa
    dki_fa_img = nib.Nifti1Image(dki_fa.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_fa_img, output_fa)
    os.system('fslreorient2std ' + output_fa+ ' ' + output_fa)

    dki_md = dkifit.md
    dki_md_img = nib.Nifti1Image(dki_md.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_md_img, output_md)
    os.system('fslreorient2std ' + output_md+ ' ' + output_md)

    dki_ad = dkifit.ad
    dki_ad_img = nib.Nifti1Image(dki_ad.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_ad_img, output_ad)
    os.system('fslreorient2std ' + output_ad+ ' ' + output_ad)

    dki_rd = dkifit.rd
    dki_rd_img = nib.Nifti1Image(dki_rd.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_rd_img, output_rd)
    os.system('fslreorient2std ' + output_rd+ ' ' + output_rd)

    MK = dkifit.mk(0, 3)
    AK = dkifit.ak(0, 3)
    RK = dkifit.rk(0, 3)

    dki_mk_img = nib.Nifti1Image(MK.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_mk_img, output_mk)
    os.system('fslreorient2std ' + output_mk+ ' ' + output_mk)

    dki_ak_img = nib.Nifti1Image(AK.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_ak_img, output_ak)
    os.system('fslreorient2std ' + output_ak+ ' ' + output_ak)

    dki_rk_img = nib.Nifti1Image(RK.astype(np.float32), img.get_affine(),img.header)
    nib.save(dki_rk_img, output_rk)
    os.system('fslreorient2std ' + output_rk+ ' ' + output_rk)

    if include_micro_fit == 'TRUE':
        
        import dipy.reconst.dki_micro as dki_micro
        well_aligned_mask = np.ones(data.shape[:-1], dtype='bool')

        # Diffusion coefficient of linearity (cl) has to be larger than 0.4, thus
        # we exclude voxels with cl < 0.4.
        cl = dkifit.linearity.copy()
        well_aligned_mask[cl < 0.4] = False

        # Diffusion coefficient of planarity (cp) has to be lower than 0.2, thus
        # we exclude voxels with cp > 0.2.
        cp = dkifit.planarity.copy()
        well_aligned_mask[cp > 0.2] = False

        # Diffusion coefficient of sphericity (cs) has to be lower than 0.35, thus
        # we exclude voxels with cs > 0.35.
        cs = dkifit.sphericity.copy()
        well_aligned_mask[cs > 0.35] = False

        # Removing nan associated with background voxels
        well_aligned_mask[np.isnan(cl)] = False
        well_aligned_mask[np.isnan(cp)] = False
        well_aligned_mask[np.isnan(cs)] = False

        dki_micro_model = dki_micro.KurtosisMicrostructureModel(gtab, fit_method)
        dki_micro_fit = dki_micro_model.fit(data_smooth, mask=well_aligned_mask)

        output_awf = output_dir + '/dki_micro_AWF.nii.gz'
        output_tort = output_dir + '/dki_micro_TORT.nii.gz'
        dki_micro_awf = dki_micro_fit.awf
        dki_micro_tort = dki_micro_fit.tortuosity

        dki_micro_awf_img = nib.Nifti1Image(dki_micro_awf.astype(np.float32), img.get_affine(),img.header)
        nib.save(dki_micro_awf_img, output_awf)
        os.system('fslreorient2std ' + output_awf+ ' ' + output_awf)

        dki_micro_tort_img = nib.Nifti1Image(dki_micro_tort.astype(np.float32), img.get_affine(),img.header)
        nib.save(dki_micro_tort_img, output_tort)
        os.system('fslreorient2std ' + output_tort+ ' ' + output_awf)


def fit_noddi_model_matlab(noddi_bin, username, input_dwi, input_bval, input_bvec, input_mask, output_dir):

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    

    shutil.copyfile(input_dwi, output_dir+"/mergedImages.nii.gz")
    os.system("fslchfiletype NIFTI " + output_dir+"/mergedImages.nii.gz")

    shutil.copyfile(input_mask, output_dir+"/roi_mask.nii.gz")
    os.system("fslchfiletype NIFTI " + output_dir+"/roi_mask.nii.gz")

    shutil.copyfile(input_bval, output_dir+"/noddi_bvals.bval")
    shutil.copyfile(input_bvec, output_dir+"/noddi_bvecs.bvec")


    #if the condor analysis directory is there, remove it to avoid duplicating results
    if os.path.exists(output_dir + "/CONDOR_NODDI/"):
        os.system("rm -rf " + output_dir + "/CONDOR_NODDI/")


    #Next, to run the NODDI on CONDOR, we need to first, run Nagesh's bash scripts to:
    #1 Prep using MATLAB function (performs chunking, etc...)
    #2 Copy noddi_fitting_condor and other needed condor files
    #3 Make Dag
    #4 Submit Dag


    print "\tSubmitting dataset to CONDOR for processing...."
    #First, change directory to the directory where the condor scripts are located
    os.chdir(noddi_bin + "/noddiCondor/")

    print "\t\tPrepping data for CONDOR...."
    #Next, run the prep script
    os.system("matlab -nodesktop -nosplash -nojvm -r \"noddiCondorPrep('"+noddi_bin+"','" + output_dir +"')\"")

    print "\t\tCopying noddi_fitting_condor executable...."
    #Run the copy script
    os.system("sh copy_noddi_fitting_condor.sh " + noddi_bin + " " + output_dir + "/CONDOR_NODDI/")

    print "\t\tMaking DAG FILE...."
    #Make the DAG file
    os.system("sh makedag.sh " + output_dir + "/CONDOR_NODDI/")

    #Submit the dag file to the condor node
    print "\t\tSUBMITTING DAG FILE...."
    #Submit the DAG to CONDOR
    os.system("ssh "+username+"@medusa.keck.waisman.wisc.edu 'sh " + noddi_bin + "/noddiCondor/submit_dag.sh " + output_dir + "/CONDOR_NODDI/" +"'")

def fit_noddi_model_amico(input_dwi, input_bval, input_bvec, input_mask, output_dir):
    
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    import amico
    amico.core.setup()

    ae = amico.Evaluation(output_dir, '')
    
    os.chdir(output_dir)
    amico_dwi = output_dir + '/NODDI_data.nii.gz'
    amico_bval = output_dir + '/NODDI_protocol.bvals'
    amico_bvec = output_dir + '/NODDI_protocol.bvecs'
    amico_scheme = output_dir + '/NODDI_protocol.scheme'
    amico_mask = output_dir + '/roi_mask.nii.gz'
    shutil.copy2(input_dwi, amico_dwi)
    shutil.copy2(input_bval, amico_bval)
    shutil.copy2(input_bvec, amico_bvec)
    shutil.copy2(input_mask, amico_mask)
    
    amico.util.fsl2scheme(amico_bval, amico_bvec)
    ae.load_data(dwi_filename = 'NODDI_data.nii.gz', scheme_filename = 'NODDI_protocol.scheme', mask_filename = 'roi_mask.nii.gz', b0_thr = 0)
    ae.set_model('NODDI')
    ae.generate_kernels()
    ae.load_kernels()
    ae.fit()
    ae.save_results()

    amico_dir = output_dir + '/AMICO/NODDI/FIT_dir.nii.gz'
    amico_ICVF = output_dir + '/AMICO/NODDI/FIT_ICVF.nii.gz'
    amico_ISOVF = output_dir + '/AMICO/NODDI/FIT_ISOVF.nii.gz'
    amico_OD = output_dir + '/AMICO/NODDI/FIT_OD.nii.gz'

    noddi_dir = output_dir + '/noddi_directions.nii.gz'
    noddi_ICVF = output_dir + '/noddi_FICVF.nii.gz'
    noddi_ISOVF = output_dir + '/noddi_FISO.nii.gz'
    noddi_OD = output_dir + '/noddi_ODI.nii.gz'

    shutil.copy2(amico_dir, noddi_dir)
    shutil.copy2(amico_ICVF, noddi_ICVF)
    shutil.copy2(amico_ISOVF, noddi_ISOVF)
    shutil.copy2(amico_OD, noddi_OD)

    os.system('fslreorient2std ' + noddi_ICVF+ ' ' + noddi_ICVF)
    os.system('fslreorient2std ' + noddi_ISOVF+ ' ' + noddi_ISOVF)
    os.system('fslreorient2std ' + noddi_OD+ ' ' + noddi_OD)
    os.system('fslreorient2std ' + noddi_dir+ ' ' + noddi_dir)

    shutil.rmtree(output_dir + '/AMICO')
    shutil.rmtree(output_dir + '/kernels')
    os.system('rm -rf ' + amico_dwi + ' ' + amico_bval + ' ' + amico_bvec + ' ' + amico_scheme + ' ' + amico_mask)

def fit_mcmd_model(input_dwi, input_bval, input_bvec, input_mask, output_dir):
    
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    tmp_output_image = output_dir + 'tmp.nii.gz'
    command = fitmcmd_exe + ' ' + input_dwi + ' ' + tmp_output_image + ' --bvals ' + input_bval + ' --bvecs ' + input_bvec + ' --mask ' + input_mask
    os.system(command)

    tmp_dir=output_dir + '/tmp/'
    tmp_basename = tmp_dir + 'img_'
    os.mkdir(tmp_dir)
    os.system('fslsplit ' + tmp_output_image + ' ' + tmp_basename + ' -t')

    mcmd_intra = output_dir + '/mcmd_INTRA.nii.gz'
    mcmd_diff = output_dir + '/mcmd_DIFF.nii.gz'
    mcmd_extratrans = output_dir + '/mcmd_EXTRATRANS.nii.gz'
    mcmd_extramd = output_dir + '/mcmd_EXTRAMD.nii.gz'

    shutil.copy2(tmp_basename+'0000.nii.gz', mcmd_intra)
    shutil.copy2(tmp_basename+'0001.nii.gz', mcmd_diff)
    shutil.copy2(tmp_basename+'0002.nii.gz', mcmd_extratrans)
    shutil.copy2(tmp_basename+'0003.nii.gz', mcmd_extramd)

    os.system('fslreorient2std ' + mcmd_intra+ ' ' + mcmd_intra)
    os.system('fslreorient2std ' + mcmd_diff+ ' ' + mcmd_diff)
    os.system('fslreorient2std ' + mcmd_extratrans+ ' ' + mcmd_extratrans)
    os.system('fslreorient2std ' + mcmd_extramd+ ' ' + mcmd_extramd)

    shutil.rmtree(tmp_dir)
    os.remove(tmp_output_image)


def fit_microdt_model(input_dwi, input_bval, input_bvec, input_mask, output_dir):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    tmp_output_image = output_dir + 'tmp.nii.gz'
    command = fitmicro_exe + ' ' + input_dwi + ' ' + tmp_output_image + ' --bvals ' + input_bval + ' --bvecs ' + input_bvec + ' --mask ' + input_mask
    os.system(command)

    tmp_dir=output_dir + '/tmp/'
    tmp_basename = tmp_dir + 'img_'
    os.mkdir(tmp_dir)
    os.system('fslsplit ' + tmp_output_image + ' ' + tmp_basename + ' -t')
    
    micro_long = output_dir + '/micro_LONG.nii.gz'
    micro_trans = output_dir + '/micro_TRANS.nii.gz'
    micro_fa = output_dir + '/micro_FA.nii.gz'
    micro_fapow = output_dir + '/micro_faPow3.nii.gz'
    micro_md = output_dir + '/micro_MD.nii.gz'
    
    shutil.copy2(tmp_basename+'0000.nii.gz', micro_long)
    shutil.copy2(tmp_basename+'0001.nii.gz', micro_trans)
    shutil.copy2(tmp_basename+'0002.nii.gz', micro_fa)
    shutil.copy2(tmp_basename+'0003.nii.gz', micro_fapow)
    shutil.copy2(tmp_basename+'0004.nii.gz', micro_md)

    os.system('fslreorient2std ' + micro_long+ ' ' + micro_long)
    os.system('fslreorient2std ' + micro_trans+ ' ' + micro_trans)
    os.system('fslreorient2std ' + micro_fa+ ' ' + micro_fa)
    os.system('fslreorient2std ' + micro_fapow+ ' ' + micro_fapow)
    os.system('fslreorient2std ' + micro_md+ ' ' + micro_md)
    
    shutil.rmtree(tmp_dir)
    os.remove(tmp_output_image)
