
import sys
import os
from lib.Converters import converters
from lib.Converters import makefmaps
import pathlib
import argparse

scanstoskip = ('Screen_Save', 'SSFSE', '.FA', '.AvDC', '.Trace', 'B1_Cali')
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
        self.studypath = pathlib.PosixPath(self.studypath)
        self.outputpath = pathlib.PosixPath(self.outputpath)
        if self.inputidfile == None:
            for subjdir in sorted(self.studypath.iterdir()):
                print("\n" + "*"*35 + "STARTING PARTICIPANT: " + subjdir.parts[-1] + "\n" + "*"*35)
                dcm_path = pathlib.PosixPath(subjdir, "dicoms")
                for filename in sorted(dcm_path.glob('*.tgz')):
                    if not any(x in filename.name for x in scanstoskip):
                        conv = converters.tgz2NIFTI(filename, self.outputpath)
        else:
            with open(self.inputidfile, 'r') as idfile:
                sids = idfile.readlines()
                sids = [s.strip('\n') for s in sids]
                subjdirs = (subjdir for subjdir in sorted(self.studypath.iterdir()) if any(x in str(subjdir) for x in sids))             
                for subjdir in subjdirs:
                    print("\n" + "*"*35 + "\n" + "STARTING PARTICIPANT: " + subjdir.parts[-1] + "\n" + "*"*35)
                    dcm_path = pathlib.PosixPath(subjdir, "dicoms")
                    bids_participantID, bids_scansession = converters.tgz2NIFTI.getfmapinfo(subjdir)
                    fmapdir = pathlib.PosixPath(self.outputpath, bids_participantID, bids_scansession, 'fmap')
                    for filename in sorted(dcm_path.glob('*.tgz')):
                        if not any(x in filename.name for x in scanstoskip):                  
                            converters.tgz2NIFTI(filename, self.outputpath)
                    makefmaps.make_fmaps('EPI', fmapdir, self.outputpath, bids_participantID, bids_scansession)
                    makefmaps.make_fmaps('DTI', fmapdir, self.outputpath, bids_participantID, bids_scansession)
                    print("\n" + "#"*35 + "\n" + "COMPLETED PARTICIPANT: " + subjdir.parts[-1] + "\n" + "#"*35)

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

