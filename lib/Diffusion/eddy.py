from pathlib import Path
import subprocess
import sys
import shutil
import time
from datetime import timedelta

class runeddy():

    def __init__(self, inputdwi, bvec, bval, outputpath, subjdir, sesdir):
        self.inputdwi = Path(inputdwi)
        self.procdir = self.inputdwi.parent
        self.outputpath = Path(outputpath)
        self.bvec = bvec
        self.bval = bval
        self.subjdir = Path(subjdir)
        self.sesdir = Path(sesdir)
        self.main()


    def eddyprep(self):
        self.eddydir = Path(self.procdir / 'eddy')
        self.eddydir.mkdir(exist_ok=True)
        allb0s = self.eddydir / 'allb0s.nii.gz'
        meanb0 = self.eddydir / 'meanb0.nii.gz'
        meanb0_brain = self.eddydir/ 'meanb0_brain.nii.gz'
        self.meanb0_brain_mask = self.eddydir / 'meanb0_brain_mask.nii.gz'

        subprocess.run(['fslroi', self.inputdwi, allb0s, '0', '7'], stdout=sys.stdout, stderr=sys.stderr)
        subprocess.run(['fslmaths', allb0s, '-Tmean', meanb0], stdout=sys.stdout, stderr=sys.stderr) 
        subprocess.run(['bet', meanb0, meanb0_brain, '-m', '-f', '0.3'], stdout=sys.stdout, stderr=sys.stderr)

        self.acqparams = self.eddydir / 'acqparams.txt'
        self.index = self.eddydir / 'index.txt'
        #acqparams file is 0 1 0 0.14484 for youthptsd
        with open(self.acqparams, 'w') as acqfile:
            acqfile.write("0 1 0 0.14484")
        with open(self.index, 'w') as indexfile:
            getnvols = subprocess.Popen(['fslval', self.inputdwi, 'dim4'], stdout=subprocess.PIPE)
            nvols = getnvols.stdout.read()
            for i in range(int(nvols)):
                indexfile.write("1 ")

    def eddy_fsl(self):
        self.basename = self.inputdwi.name[:14]
        self.eddy_out_basename = str(self.eddydir / self.basename)
        timeStarted = time.time()
        subprocess.run(['time','eddy_openmp', '-v', '--imain='+str(self.inputdwi), '--mask='+str(self.meanb0_brain_mask), '--index='+str(self.index), 
        '--acqp='+str(self.acqparams), '--bvecs='+str(self.bvec), '--bvals='+str(self.bval), '--out='+self.eddy_out_basename, '--cnr_maps',
        '--residuals', '--repol'], stdout=sys.stdout, stderr=sys.stderr)
        timeEnded = time.time()
        eddyRunTime = timeStarted - timeEnded
        eddyRunLog = Path(self.outputpath / 'eddyRunTimes.log')
        with open(eddyRunLog, 'w+') as f:
            f.write(str('Eddy correction took ' + str(timedelta(seconds=eddyRunTime)) + ' for subject ' + subjdir.name + ', ' + sesdir.name + '\n'))

    
    def eddy_quad(self):
        self.eddyqadir = Path(self.eddydir / 'QA')
        subprocess.run(['eddy_quad', self.eddy_out_basename, '-idx', self.index, '-par', self.acqparams, '-m', self.meanb0_brain_mask, 
        '-b', self.bval, '-g', self.bvec, '-o', self.eddyqadir, '-v'])

    def posteddy(self):
        dwi_eddycorr = Path(self.eddydir / str(self.basename + '.nii.gz'))
        dwi_eddycorr2proc = Path(self.procdir / str(self.basename + '_eddycorr.nii.gz'))
        shutil.copy(dwi_eddycorr, dwi_eddycorr2proc)

        bvals = Path(self.procdir / 'preproc' / str(self.basename + '_dwi.bval'))
        bvals2proc = Path(self.procdir / str(self.basename + '_dwi.bval'))
        shutil.copy(bvals, bvals2proc)

        bvecs = Path(self.eddydir / str(self.basename + '.eddy_rotated_bvecs'))
        bvecs2proc = Path(self.procdir / str(self.basename + '_eddycorr.bvec'))
        shutil.copy(bvecs, bvecs2proc)

        brainmask = Path(self.eddydir / str('meanb0_brain_mask.nii.gz'))
        brainmask2proc = Path(self.procdir / str('meanb0_brain_mask.nii.gz'))
        shutil.copy(brainmask, brainmask2proc)

    def main(self):
        self.eddyprep()
        self.eddy_fsl()
        self.eddy_quad()
        self.posteddy()