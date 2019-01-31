
import sys
import os
from lib.Converters import converters
import pathlib
import argparse

scanstoskip = ('Screen_Save', 'SSFSE', 'FASep', 'AvDCSep', 'TraceSep')
subjectstoskip = ('')
p = pathlib.Path('/home/justin/1111_C1/dicoms')

class run():

    def initialize(self):
        ap = argparse.ArgumentParser()
        ap.add_argument("-s", "--studypath", required=True,
                        help="Directory containing subject folders downloaded \
                        from the scanner. Will look for subject folders \
                        each containing a 'dicoms' directory. Each scan is \
                        expected to be contained in a reflectively named \
                        directory (e.g., s04_bravo). Raw scan files are dcm \
                        series files compressed into a multiple file bz2 archive.")
        ap.add_argument("-i", "--ids", required=False, help="Optional path to \
        a text file listing the subject IDs to be processed.")
        ap.add_argument("-o", "--outputpath", required=True)
        args = vars(ap.parse_args())

        self.studypath = args["studypath"]
        self.inputidfile = args["ids"]
        self.outputpath = args["outputpath"]
   

    def convertscans_tgz(self):
        # if not self.inputidfile == None:
        #     with open(self.inputidfile, 'r') as idfile:
        #         sids = idfile.readlines()
        #         sids = [s.strip('\n') for s in sids]
        #         subjs = (sid_dir for sid_dir in sorted(os.listdir(self.studypath)) if any(x in str(sid_dir) for x in sids))
        # else:
        # subjs = (sid_dir for sid_dir in sorted(os.listdir(self.studypath)) if not any(x in str(sid_dir) for x in subjectstoskip))
        dcm_path = pathlib.PosixPath(self.studypath, "dicoms")
        self.studypath = pathlib.PosixPath(self.studypath)
        for subjdir in sorted(self.studypath.iterdir()):
            dcm_path = pathlib.PosixPath(subjdir, "dicoms")
            for filename in sorted(dcm_path.glob('*.tgz')):
                if not any(x in filename.name for x in scanstoskip):
                    conv = converters.tgz2NIFTI(filename, '/home/justin/pyout')

    def convertscans_bz2(self):
        self.studypath = pathlib.PosixPath(self.studypath)
        for subjdir in sorted(self.studypath.iterdir()):
            dicomspath = pathlib.PosixPath(subjdir, "dicoms")
            scandirs = (scandir for scandir in sorted(dicomspath.iterdir()) if scandir.is_dir() \
            if not any(x in str(scandir) for x in scanstoskip))
            for scandir in scandirs:
                conv = converters.bz2NIFTI(scandir, '/home/justin/pyout')

if __name__ == '__main__':
    r = run()
    r.initialize()
    r.convertscans()
