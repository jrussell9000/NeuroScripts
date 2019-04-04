
import sys
import os
from lib.Converters import converters
from lib.Converters import makefmaps
import pathlib
import argparse

scanstoskip = ('3Plane', 'Screen_Save', 'SSFSE', '.FA', '.AvDC', '.Trace', 'B1_Cali')
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

        self.studypath = pathlib.PosixPath(args["studypath"])
        self.inputidfile = args["ids"]
        self.outputpath = pathlib.PosixPath(args["outputpath"])
    
    def convertscans_tgz(self):
        conv = converters.tgz2NIFTI(self.studypath, self.outputpath, scanstoskip, self.inputidfile)

    def convertscans_bz2(self):
        self.studypath = pathlib.PurePath(self.studypath)
        for subjdir in sorted(self.studypath.iterdir()):
            dicomspath = pathlib.PurePath(subjdir, "dicoms")
            scandirs = (scandir for scandir in sorted(dicomspath.iterdir()) if scandir.is_dir() \
            if not any(x in str(scandir) for x in scanstoskip))
            for scandir in scandirs:
                conv = converters.bz2NIFTI(scandir, '/home/justin/pyout')

if __name__ == '__main__':
    r = run()
    r.initialize()
    r.convertscans_tgz()

