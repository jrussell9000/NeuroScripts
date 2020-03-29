#!/usr/bin/env python3
# coding: utf-8

import argparse
import shutil
import sys
from pathlib import Path

# lib_folder = Path(inspect.getfile(inspect.currentframe())).parents[2] / 'lib'
lib_folder = Path(__file__).resolve().parents[1] / 'lib'

if (lib_folder.is_dir()):
    sys.path.insert(0, str(lib_folder))
else:
    sys.stderr.write('Unable to locate python library location ("lib") in parent of current folder')
    sys.exit(1)

import converters  # noqa: E402

scanstoskip = ('3dir', 'ADC', 'FA', 'CMB', 'ssfse', 'assetcal', 'cardiac', '3Plane', 
               'Screen_Save', 'SSFSE', '.FA', '.AvDC', '.Trace', 'B1_Cali', 'ORIG_MPRAGE')
subjectstoskip = ('')


class run():

    def __init__(self):
        self.parseArgs()
        self.main()

    def parseArgs(self):
        ap = argparse.ArgumentParser()
        ap.add_argument("-s", "--studypath", required=True,
                        help="Study directory containing subject folders downloaded \
                        from the scanner (e.g., /Volumes/Studies/Herringa/ \
                        YouthPTSD). This script will look for a 'dicoms' \
                        subdirectory within each subject directory. These \
                        DICOM directories may be organized in one of two \
                        different fashions. \
                        \
                        Before 2018 (ish) - Scans are stored in directories \
                                            are structured as: \
                                            SUBJID/dicoms/sYY_ZZZZ \
                                            where SUBJID is the alphanumeric \
                                            subject ID, YY is a two-digit \
                                            integer reflecting the scan's \
                                            order in the sequence (e.g., 04), \
                                            and ZZZZ is an alpha string \
                                            describing the scan type (e.g., \
                                            bravo). DICOMs in each scan \
                                            directory (e.g., s04_bravo) are \
                                            contained in spanned '.bz2' archives. Detailed \
                                            scan parameters are provided in YAML and pickle- \
                                            encoded files within each scan directory.  \
                                            An 'info.txt' file in the 'dicom' directory \
                                            contains (limited) plain-text information about \
                                            each scan in the sequence. \
                        \
                          2018 and beyond - Scans are stored in directories are structured as \
                                            SUBJID/dicoms, where SUBJID is the alphanumeric \
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
        ap.add_argument("-if", "--idfile", required=False, help="Optional path to \
                        a text file listing the subject IDs to be processed.")
        ap.add_argument("-i", "--ids", nargs='*', required=False, help="Path to a list of \
                        subject IDs to process.")
        ap.add_argument("-f", "--format", required=False, help="Archive file \
                        format and directory structure for the raw files. \
                        Possible options are TGZ or BZ2 (old format): \
                            BZ2 - Scans are stored in directories are structured as: \
                                      SUBJID/dicoms/sYY_ZZZZ \
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
                                  SUBJID/dicoms, where SUBJID is the alphanumeric \
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
        ap.add_argument("-o", "--outputpath", required=True, help="The path to the \
                        directory within which the BIDS structured output will be stored.")
        args = vars(ap.parse_args())
        if len(args) < 1:
            ap.print_usage()
            sys.exit(1)

        self.studypath = Path(args["studypath"])
        self.ids = args["ids"]
        self.inputidfile = args["idfile"]
        self.format = args["format"]
        self.outputpath = Path(args["outputpath"])

    def main(self):
        if self.outputpath.exists():
            shutil.rmtree(self.outputpath)
        convert = converters.convertScans(self.studypath, self.outputpath, scanstoskip,
                                          self.inputidfile, self.ids)

if __name__ == '__main__':
    r = run()
