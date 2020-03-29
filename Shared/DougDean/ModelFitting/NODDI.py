import string, os, sys, subprocess, shutil, time

def fit_noddi_matlab(noddi_bin, username, input_dwi, input_bval, input_bvec, input_mask, output_dir):

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    shutil.copyfile(input_dwi, output_dir+'/mergedImages.nii.gz')
    os.system('fslchfiletype NIFTI ' + output_dir+'/mergedImages.nii.gz')

    shutil.copyfile(input_mask, output_dir+'/roi_mask.nii.gz')
    os.system('fslchfiletype NIFTI ' + output_dir+'/roi_mask.nii.gz')

    shutil.copyfile(input_bval, output_dir+'/noddi_bvals.bval')
    shutil.copyfile(input_bvec, output_dir+'/noddi_bvecs.bvec')


    #if the condor analysis directory is there, remove it to avoid duplicating results
    if os.path.exists(output_dir + '/CONDOR_NODDI/'):
        os.system('rm -rf ' + output_dir + '/CONDOR_NODDI/')


    #Next, to run the NODDI on CONDOR, we need to first, run Nagesh's bash scripts to:
    #1 Prep using MATLAB function (performs chunking, etc...)
    #2 Copy noddi_fitting_condor and other needed condor files
    #3 Make Dag
    #4 Submit Dag

    print '\tSubmitting dataset to CONDOR for processing....'
    #First, change directory to the directory where the condor scripts are located
    os.chdir(noddi_bin + '/noddiCondor/')

    print '\t\tPrepping data for CONDOR....'
    #Next, run the prep script
    os.system('matlab -nodesktop -nosplash -nojvm -r \'noddiCondorPrep(''+noddi_bin+'','' + output_dir +'')\'')

    print '\t\tCopying noddi_fitting_condor executable....'
    #Run the copy script
    os.system('sh copy_noddi_fitting_condor.sh ' + noddi_bin + ' ' + output_dir + '/CONDOR_NODDI/')

    print '\t\tMaking DAG FILE....'
    #Make the DAG file
    os.system('sh makedag.sh ' + output_dir + '/CONDOR_NODDI/')

    #Submit the dag file to the condor node
    print '\t\tSUBMITTING DAG FILE....'
    #Submit the DAG to CONDOR
    os.system('ssh '+username+'@medusa.keck.waisman.wisc.edu ''sh ' + noddi_bin + '/noddiCondor/submit_dag.sh ' + output_dir + '/CONDOR_NODDI/'+'')

def fit_noddi_amico(input_dwi, input_bval, input_bvec, input_mask, output_dir):
    
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

