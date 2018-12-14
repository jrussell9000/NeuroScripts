import string, os, sys, subprocess, shutil, time

if sys.platform == 'linux2':
    eddy='eddy_openmp'
    eddy_cuda='eddy_cuda8.0'
else:
    eddy='eddy'

def eddy_correct_fsl(input_dwi, input_bvec, output_dwi, output_bvec, output_log):
    
    eddy_output_basename = output_dwi[0:len(output_dwi)-7]
    logFile = eddy_output_basename + '.ecclog'

    if os.path.exists(logFile):
        os.remove(logFile)
    
    command = 'eddy_correct ' + input_dwi + ' ' + eddy_output_basename + ' 0'
    os.system(command)

    os.system('mv ' + logFile + ' ' + output_log)

    #Rotate b-vecs after doing the eddy correction
    os.system('fdt_rotate_bvecs ' + input_bvec+ ' ' + output_bvec + ' ' + output_log)

def eddy_fsl(input_dwi, input_bval, input_bvec, input_index, input_acqparam, output_dwi, output_bvec, topup_base='', external_b0='', repol=0, data_shelled=0, mb='', cuda='', mporder=0, slice_order='', mask_img=''):

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
        command = eddy_cuda + ' --imain=' + input_dwi + ' --mask=' + tmp_mask + ' --index=' + input_index + ' --acqp=' + input_acqparam + ' --bvecs=' + input_bvec + ' --bvals=' + input_bval + ' --out='  + eddy_output_basename + ' --cnr_maps --residuals'
    else:
        command = eddy + ' --imain=' + input_dwi + ' --mask=' + tmp_mask + ' --index=' + input_index + ' --acqp=' + input_acqparam + ' --bvecs=' + input_bvec + ' --bvals=' + input_bval + ' --out='  + eddy_output_basename + ' --cnr_maps --residuals'

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
        command += ' --niter=10 --fwhm=10,8,6,4,4,2,2,0,0,0 --ol_type=both --mporder='+str(mporder)+' --s2v_niter=12 --slspec='+slice_order + ' --s2v_lambda=6 --s2v_interp=spline'
  
    print command
    os.system(command)
    #Rotate b-vecs after doing the eddy correction
    os.system('mv ' + eddy_output_basename+'.eddy_rotated_bvecs ' + output_bvec)

    #Remove temporary mask
    os.system('rm -rf ' + tmp_mask)
    if mask_img == '':
        os.system('rm -rf ' + tmp_dwi)

