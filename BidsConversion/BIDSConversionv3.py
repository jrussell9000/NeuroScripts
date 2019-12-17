
import sys
import os
from lib.Converters import converters
from lib.Converters import makefmaps
from lib.tools.PNGViewer import PNGViewer
import pathlib
import argparse

scanstoskip = ('3Plane', 'Screen_Save', 'SSFSE', '.FA', '.AvDC', '.Trace', 'B1_Cali', 'ORIG_MPRAGE')
subjectstoskip = ('')

class run():

    def initialize(self):
        ap = argparse.ArgumentParser()
        ap.add_argument("-s", "--studypath", required=True,
                        help="Study directory containing subject folders downloaded \
                        from the scanner (e.g., /Volumes/Studies/Herringa/YouthPTSD). \
                        This script will look for a 'dicoms' subdirectory within each subject \
                        directory.  \
                        These dicom directories may be organized in one of two different fashions. \
                        \
                        Before 2018 (ish) - Scans are stored in directories are structured as: \
                                            SUBJID\dicoms\sYY_ZZZZ \
                                            where SUBJID is the alphanumeric subject ID, \
                                            YY is a two-digit integer reflecting the scan's \
                                            order in the sequence (e.g., 04), and ZZZZ is an \
                                            alpha string describing the scan type (e.g., bravo). \
                                            DICOMs in each scan directory (e.g., s04_bravo) are \
                                            contained in spanned '.bz2' archives. Detailed \
                                            scan parameters are provided in YAML and pickle- \
                                            encoded files within each scan directory.  \
                                            An 'info.txt' file in the 'dicom' directory \
                                            contains (limited) plain-text information about \
                                            each scan in the sequence. \
                            \
                          2018 and beyond - Scans are stored in directories are structured as \
                                            SUBJID\dicoms, where SUBJID is the alphanumeric \
                                            subject ID. DICOMS are stored in '.tgz' archive \
                                            files with naming convention: \
                                                EKKKKK.sYYYYY.ZZZZZ.tgz \
                                            where KKKKK is the HERI unique identifier for the \
                                            scan session, YYYYY is the sequence or sub-sequence \
                                            number (e.g., s0022 or s2200), and ZZZZZ is an \
                                            alphanumeric string (e.g., MPRAGE) describing the \
                                            scan.  An info.EKKKKK.txt file in the 'dicom' \
                                            directory contains (limited) plain-text information \
                                            about each scan in the sequence.")
        ap.add_argument("-i", "--ids", required=False, help="Optional path to \
                        a text file listing the subject IDs to be processed.")
                        # OR a space-delimited list of subject IDs to process
        ap.add_argument("-f", "--format", required=False, help="Archive file \
                        format and directory structure for the raw files. \
                        Possible options are TGZ or BZ2 (old format): \
                            BZ2 - Scans are stored in directories are structured as: \
                                      SUBJID\dicoms\sYY_ZZZZ \
                                  where SUBJID is the alphanumeric subject ID, \
                                  YY is a two-digit integer reflecting the scan's \
                                  order in the sequence (e.g., 04), and ZZZZ is an \
                                  alpha string describing the scan type (e.g., bravo). \
                                  DICOMs in each scan directory (e.g., s04_bravo) are \
                                  contained in spanned '.bz2' archives. Detailed \
                                  scan parameters are provided in YAML and pickle- \
                                  encoded files within each scan directory.  \
                                  An 'info.txt' file in the 'dicom' directory \
                                  contains (limited) plain-text information about \
                                  each scan in the sequence. \
                            \
                            TGZ - Scans are stored in directories are structured as \
                                  SUBJID\dicoms, where SUBJID is the alphanumeric \
                                  subject ID. DICOMS are stored in '.tgz' archive \
                                  files with naming convention: \
                                      EKKKKK.sYYYYY.ZZZZZ.tgz \
                                  where KKKKK is the HERI unique identifier for the \
                                  scan session, YYYYY is the sequence or sub-sequence \
                                  number (e.g., s0022 or s2200), and ZZZZZ is an \
                                  alphanumeric string (e.g., MPRAGE) describing the \
                                  scan.  An info.EKKKKK.txt file in the 'dicom' \
                                  directory contains (limited) plain-text information \
                                  about each scan in the sequence.")
        ap.add_argument("-o", "--outputpath", required=True, help="The fully qualified \
            path to the directory within which the BIDS structured output will be stored.")
        args = vars(ap.parse_args())

        self.studypath = pathlib.PosixPath(args["studypath"])
        self.inputidfile = args["ids"]
        self.format = args["format"]
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
                conv = converters.bz2NIFTI(scandir, self.outputpath)

if __name__ == '__main__':
    r = run()
    r.initialize()
    if r.format in ('TGZ','tgz'):
        r.convertscans_tgz()
    elif r.format in ('BZ2','bz2'):
        r.convertscans_bz2()
        


