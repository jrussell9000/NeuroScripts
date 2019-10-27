import sys
import os
import subprocess
import argparse
import shutil

from lib.Utils import Logger
from pathlib import Path, PosixPath
from lib.Diffusion.preprocessing import dwipreproc
from lib.Diffusion.eddy import runeddy
from lib.Utils.tools import manuallyReviewDWI

class run():

    def initialize(self):
        ap = argparse.ArgumentParser()
        ap.add_argument("-s", "--studypath", required=True,
                        help="BIDS-format directory containing DWI scans to be \
                        pre-processed. Will operate on each session directory within \
                        each subject directory.")
        ap.add_argument("-i", "--ids", required=False, help="Optional path to \
                        a text file listing the subject IDs to be processed.")
        ap.add_argument("-o", "--outputpath", required=True)
        args = vars(ap.parse_args())

        self.studypath = Path(args["studypath"])
        self.inputidfile = args["ids"]
        self.outputpath = Path(args["outputpath"])
    
    def preproc(self, subjdir, sesdir):
        procdir = Path(self.outputpath / subjdir.name / sesdir.name)
        dwi2eddy = Path(procdir / str(subjdir.name + '_' + sesdir.name + '_preproc_dwi.nii'))
        dwidir = Path(sesdir, 'dwi')
        anatdir = Path(sesdir, 'anat')
        fmapdir = Path(sesdir, 'fmap')

        
        for f in dwidir.glob('*'):
            if f.suffix == ('.nii'):
                dwiscan = f
            if f.suffix == ('.bvec'):
                bvec = f
            if f.suffix == ('.bval'):
                bval = f
            if f.suffix == ('.json'):
                dwijson = f
            else:
                next

        for f in fmapdir.glob('*.nii'):
            if f.name.__contains__('DTI_magnitude1.nii'):
                mag = f
            if f.name.__contains__('RealFieldmapDTIrads'):
                fieldmap_rads = f

        subjstr = str("STARTING SUBJECT: " + str(subjdir.name.upper() + ", " + sesdir.name.upper()))
        print("\n".join(['#'*len(subjstr), subjstr, '#'*len(subjstr)]))
        dwipreproc(dwiscan, bvec, bval, dwijson, fieldmap_rads, mag, self.outputpath, subjdir.name, sesdir.name)
        runeddy(dwi2eddy, bvec, bval, self.outputpath, subjdir, sesdir)

    def main(self):
        try:
            self.initialize()
        except:
            sys.exit(1)

        subjdirs = (subjdir for subjdir in self.studypath.iterdir() if subjdir.is_dir())
        for subjdir in sorted(subjdirs):
       
            sesdirs = (sesdir for sesdir in subjdir.iterdir() if sesdir.is_dir())
            for sesdir in sorted(sesdirs):
                
                try:
                    self.preproc(subjdir, sesdir)
                except Exception as e:
                    print(e)
                    errfile = Path(self.outputpath / 'error_log.txt')
                    with open(errfile, 'a+') as errorfile:
                        errorfile.write(str('Error processing ' + subjdir.name + ', ' + sesdir.name + '\n' + str(e) + '\n'))
                    next
                
if __name__ == '__main__':
    r = run()
    r.main()

