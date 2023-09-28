#!/usr/bin/env python

ID = "$Id: dicom.py 221 2010-01-02 17:21:29Z jmo $"[1:-1]

# Written by John Ollinger
#
# University of Wisconsin, 8/16/09

#Copyright (c) 2006-2007, John Ollinger, University of Wisconsin
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are
#met:
#
#    * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ** This software was designed to be used only for research purposes. **
# ** Clinical uses are not recommended, and have never been evaluated. **
# ** This software comes with no warranties of any kind whatsoever,    **
# ** and may not be useful for anything.  Use it at your own risk!     **
# ** If these terms are not acceptable, you aren't allowed to use the code.**
# Purpose: Read dicom headers and images.

# By John Ollinger, University of Wisconsin

import sys
import os
from numpy import int8, int16, int32, float32, float64, float, \
        fromstring, ones, zeros, reshape, int, arange, take, array, \
        nonzero, integer, int32, reshape, where, ubyte, ushort, short, \
        sign, dot, cross, put, identity, apply
import struct
from wimage_lib import except_msg, Timer, Translate
import bz2
import gzip
import string
from datetime import datetime

ID = "$Id: dicom.py 221 2010-01-02 17:21:29Z jmo $"[1:-1]
def echo_ID():
    return ID
#NAME = ID.split()[1]
#REV = ID.split()[2]
#DATE = ID.split()[3:6][:-1]
#info = '%s: rev %s, last commit: %s@%s' % (NAME, REV, DATE[0], DATE[1][:-1])

BLOCKSIZE = 12288
EXPLICIT = 0
IMPLICIT = 1

# Actions to take while parsing dicom header.
NOBREAK = 0
BREAK = 1
CONTINUE = 2

MEDIA_STORAGE_SOP_CLASS_UID = '1.2.840.10008.5.1.4.1.1.4'
MEDIA_STORAGE_SOP_CLASS_SCREEN_CAPTURE = '1.2.840.10008.5.1.4.1.1.7'

# Convert Siemens image type to number.

translate_name = Translate(string.ascii_letters,'x'*len(string.ascii_letters))
translate_printing = Translate(string.ascii_letters, string.ascii_letters)
blankout_alpha = Translate(string.ascii_letters,' '*len(string.ascii_letters))

idx_to_type = {0:'Magnitude', 1: 'Phase', 2:'Imaginary', 3:'Real'}
ge_type_to_idx = {'Magnitude':0, 'Phase':1, 'Imaginary':2, 'Real':3} 
#ge_type_to_idx = {0:3, 1:2, 2:1, 3:0} 
siemens_type_to_idx = {'R':3, 'I':2, 'P':1, 'M':0} 
phillips_type_to_idx = {'R_SE':3, 'I_SE':2, 'P_SE':1, 'M_SE':0, \
                        'R_GE':3, 'I_GE':2, 'P_GE':1, 'M_GE':0,} 
type_to_idx = {'Real':3, 'Imaginary':2, 'Phase':1, 'Magnitude':0} 
idx_to_type = {3:'Real', 2:'Imaginary', 1:'Phase', 0:'Magnitude'} 

hdrkeys = [('imagetime', '0008,0033'), \
    ('ReconstructionDiameter', '0018,1100'), \
    ('Rows', '0028,0010'), \
    ('Columns', '0028,0011'), \
    ('LocationsInAcquisition', '0021,104f'), \
    ('PixelSpacing', '0028,0030'), \
    ('SliceThickness', '0018,0050'), \
    ('SpacingBetweenSlices', '0018,0088'),  \
    ('NumberPhaseEncodes', '0018,0089'), \
    ('RepetitionTime', '0018,0080'), \
    ('SmallestImagePixelValue', '0028,0106'), \
    ('LargestImagePixelValue', '0028,0107'), \
    ('SeriesPlane', '0019,1017'), \
    ('FirstScanRas', '0019,1018'), \
    ('FirstScanLocation', '0019,1019'), \
    ('ImagesInSeries', '0025,1007'), \
    ('PulseSequence', '0027,1032'), \
    ('ImageDimensionX', '0027,1060'), \
    ('ImageDimensionY', '0027,1061'), \
    ('BitsStored', '0028,0101'), \
    ('SeriesDescription', '0008,103e'), \
    ('PlaneType', '0027,1035'), \
    ('InstanceNumber', '0020,0013'), \
    ('InstitutionName', '0008,0080'), \
    ('LastScanRas', '0019,101a'), \
    ('LastScanLocation', '0019,101b'), \
    ('ImagePosition', '0020,0032'), \
    ('AcquisitionGroupLength', '0018,0000'), \
    ('ImageOrientation', '0020,0037'), \
    ('ProtocolName', '0018,1030'), \
    ('SeriesDescription', '0008,103e'), \
    ('StudyDate', '0008,0020'), \
    ('StudyID', '0020,0010'), \
    ('StudyDescription', '0008,1030'), \
    ('PatientId', '0010,0020'), \
    ('PatientBirthDate', '0010,0030'), \
    ('ImagePosition', '0020,0032'), \
    ('PatientPosition', '0018,5100'), \
    ('AcquisitionMatrix', '0018,1310'), \
    ('AcquisitionTime', '0008,0032'), \
    ('SeriesTime', '0008,0031'), \
    ('ImagesInAcquisition', '0020,1002'), \
    ('ImageFormat', '0008,0008'), \
    ('SliceLocation', '0020,1041'), \
    ('PatientAge', '0010,1010'), \
    ('PatientWeight', '0010,1030'), \
    ('PatientSex', '0010,0040'), \
    ('PatientAge', '0010,1010'), \
    ('PatientWeight', '0010,1030'), \
    ('PatientName', '0010,0010'), \
    ('ImageDimensionX', '0027,1060'), \
    ('ImageDimensionY', '0027,1061'), \
    ('SeriesNumber', '0020,0011'), \
    ('StartImage', 'StartImage'), \
    ('SeriesNumber', '0020,0011'), \
    ('ActualSeriesDateTime', '0009,10e9'), \
    ('AcquisitionNumber', '0020,0012'), \
    ('Transmit Coil Name', '0018,1251'), \
    ('Manufacturer', '0008,0070'), \
    ('BitsStored', '0028,0101'), \
    ('BitsAllocated', '0028,0100'), \
    ('TransferSyntax', 'TransferSyntax'), \
    ('ImageType', '0008,0008'), \
    ('ImagingMode', '0018,0023'), \
    ('HighBit', '0028,0102'), \
    ('InstitutionAddress', '0008,0081'), \
    ('ManufacturersModel', '0008,1090'), \
    ('SoftwareVersion', '0018,1020'),  \
    ('RequestingPhysician', '0032,1032'), \
    ('PixelRepresentation','0028,0103'), \
    ('ImageLengthBytes','7fe0,0000'), \
    ('Modality', '0008,0060')]

pet_hdrkeys = [ \
    ('RescaleIntercept', '0028,1052'), \
    ('RescaleSlope', '0028,1053'), \
    ('TracerName', '0009,1036'), \
    ('RadioNuclideName', '0009,103e'), \
    ('ActualFrameDuration', '0018,1242'), \
    ('FrameReferenceTime', '0054,1300'), \
    ('SliceSensitivityFactor', '0054,1320'), \
    ('DecayFactor', '0054,1321'), \
    ('DeadTimeFactor', '0054,1324'), \
    ('DoseCalibrationFactor', '0054,1322')]

mri_hdrkeys = [ \
    ('FlipAngle', '0018,1314'), \
    ('EchoTime', '0018,0081'), \
    ('InversionTime', '0018,0082'), \
    ('NumberOfExcitations', '0027,1062'), \
    ('EchoTrainLength', '0018,0091'), \
    ('DisplayFieldOfView','0019,101e'), \
    ('EchoNumber', '0018,0086'), \
    ('ReceiveCoilName', '0018,1250'), \
    ('EffEchoSpacing', '0043,102c'), \
    ('NumberOfAverages', '0018,0083'), \
    ('ScanningSequence', '0018,0020'), \
    ('GEImageType', '0043,102f'), \
    ('PixelBandwidth', '0018,0095'), \
    ('EchoNumber', '0018,0086'), \
    ('NumberOfEchos', '0019,107e'), \
    ('SecondEcho', '0019,107d'), \
    ('PhaseEncDir', '0018,1312'), \
    ('SwapPhaseFrequency', '0019,108f', -1), \
    ('PulseSequence', '0027,1032', ''), \
    ('PulseSequenceName', '0019,109c', ''), \
    ('InternalPulseSequenceName', '0019,109e'), \
    ('PulseSequenceDate', '0019,109d'), \
    ('AnalogRcvrGain', '0019,1095'), \
    ('DigitalRcvrGain', '0019,1096'), \
    ('EchoNumber', '0018,0086'), \
    ('SequenceVariant', '0018,0021'), \
    ('NumberOfAverages', '0018,0083'), \
    ('ScanOptions', '0018,0022'), \
    ('FieldStrength', '0018,0087'), \
    ('SequenceName', '0018,0024'), \
    ('SAR', '0018,1316'), \
    ('VariableFlipAngleFlag', '0018,1315'),  \
    ('PercentPhaseFieldOfView', '0018,0094'), \
    ('FastPhases','0019,10f2'), \
    ('DerivedClass','0051,1001'), \
    ('DerivedType','0051,1002'), \
    ('DerivedParam1','0051,1003'), \
    ('DerivedParam2','0051,1004'), \
    ('NumDirections','0051,1005'), \
    ('BValue','0051,100b'), \
    ('DiffusionDir0','0021,105a'), \
    ('DiffusionDir1','0019,10d9'), \
    ('DiffusionDir2','0019,10df'), \
    ('DiffusionDir3','0019,10e0'), \
    ('BValue','0051,100b'), \
    ('ImagingOptions', '0027,1033'), \
    ('UserData0','0019,10a7'), \
    ('UserData1','0019,10a8'), \
    ('UserData2','0019,10a9'), \
    ('UserData3','0019,10aa'), \
    ('UserData4','0019,10ab'), \
    ('UserData5','0019,10ac'), \
    ('UserData6','0019,10ad'), \
    ('UserData7','0019,10ae'), \
    ('UserData8','0019,10af'), \
    ('UserData9','0019,10b0'), \
    ('UserData10','0019,10b1'), \
    ('UserData11','0019,10b2'), \
    ('UserData12','0019,10b3'), \
    ('UserData13','0019,10b4'), \
    ('UserData14','0019,10b5'), \
    ('UserData15','0019,10b6'), \
    ('UserData16','0019,10b7'), \
    ('UserData17','0019,10b8'), \
    ('UserData18','0019,10b9'), \
    ('UserData19','0019,10ba'), \
    ('UserData20','0019,10bb'), \
    ('UserData21','0019,10bc'), \
    ('UserData22','0019,10bd')]
    
# ImagingOptions maps the iopt variable in psdiopt.h
# ImagingMode maps the imode variable in epic.h

open_funcs = [ open, bz2.BZ2File, gzip.GzipFile]

def open_gzbz2(fullpath, mode='r'):
    """
    Open plain, gzipped, or bunzipped file as required.
    """

    if fullpath.endswith('.bz2'):
        path = fullpath
        i = 1
    elif fullpath.endswith('.gz'):
        path = fullpath
        i = 2
    else:
#       No suffix.
        for i in range(3):
            path = fullpath + ['','.bz2', '.gz'][i]
            if os.path.exists(path):
                break
        else:
            return None
    f = numpy.apply( open_funcs[i], (path, 'r'))

    if f is None:
        raise IOError('open_gzbz2: Could not open: %s\n' % file1)
    else:
        return f

#***********************
def get_exam_list(exam):
#***********************

    """
    Purpose: Search for dicom files in GE's database and find out 
    what is in them.
    """

#    Get list of study directories.
    top = '/export/home1/sdc_image_pool/images'
    topdirs = os.listdir(top)
    exampaths = []
    for dr in topdirs:
        subdir = "%s/%s" % (top, dr)
        examdirs = os.listdir(subdir)
        for examdir in examdirs:
            if examdir[:4] != 'core':
                exampaths.append("%s/%s" % (subdir, examdir))

    exam_info = []
    examm1 = ""
    exams = []
    for exampath in exampaths:
        examseries = os.listdir(exampath)
#       Loop over each series in the exam
        for series in examseries:
            seriespath = "%s/%s" % (exampath, series)
            slices = os.listdir(seriespath)
            if len(slices) > 0:
#               Read the header from the first slice to get the exam number.
                filename = '%s/%s'% (seriespath, slices[0])
                hdr = read_ge_dicom_header(filename)
                examno = hdr['exam']
                if exam == 0 or examno == exam:
                    if examno != examm1:
#                       This is a new exam.
                        exams.append(examno)
                    exam_info.append((examno, seriespath, slices[0]))
            examm1 = examno
#        if examno != exam:
#            break
    return(exams, exam_info)

#******************
def isdicom(fname):
#******************

    """
    Determine if a file is in dicom format. 
    Return: True or False
    """

    if fname.endswith('.dcm'):
        return True
    if os.path.isdir(fname):
        return False
    f = open_gzbz2(fname, 'r')
    if f is None:
        return False
    try:
        f.seek(128)
        dicm_code = f.read(4)
        f.close()
        if dicm_code == "DICM":
            return True
        else:
            return False
    except IOError:
         return False



# Table defining types of entries.
# AE: Application entity
# AS: Age string
# AT: Attribute tag
# CS: Code string
# DA: Date
# DS: Decimal string
# DT: Date Time
# FL: Floating point single
# FD: Floating point double
# IS: Integer string
# LO: Long string
# LT: Long text
# OB: Other Byte String
# OF: Other Float String
# OW: Other Word String
# PN: Person Name
# SH: Short String
# SL: Signed Long
# SQ: Sequence of Items
# SS: Signed Short
# ST: Short Text
# TM: Time
# UI: Unique Identifier (UID)
# UL: Unsigned Long
# UN: Unknown
# US: Unsigned Short
# UT: Unlimited Text

# Each entry contains the tuple: 
# (bytes_to_skip, format_of_VL_entry, length_of_VL_entry, 
#  format_of_value, size_of_value)
lgth_tab = { \
    'AE':(0, "<h", 2, "s", 0), \
    'AS':(0, "<h", 2, "s", 0), \
    'AT':(0, "<h", 2, "s", 0), \
    'CS':(0, "<h", 2, "s", 0), \
    'DA':(0, "<h", 2, "s", 0), \
    'DS':(0, "<h", 2, "s", 0), \
    'DT':(0, "<h", 2, "s", 0), \
    'FL':(0, "<h", 2, "<f", 4), \
    'FD':(0, "<h", 2, "<d", 8), \
    'IS':(0, "<h", 2, "s", 0), \
    'LO':(0, "<h", 2, "s", 0), \
    'LT':(0, "<h", 2, "s", 0), \
    'OB':(2, "<I", 4, "s", -1), \
    'OF':(2, "<I", 4, "s", -1), \
    'OW':(2, "<I", 4, "s", 0), \
    'OX':(0, "<I", 4, "s", 0), \
    'PN':(0, "<h", 2, "s", 0), \
    'SH':(0, "<h", 2, "s", 0), \
    'SL':(0, "<h", 2, "<i", 4), \
    'SQ':(2, "<I", 4, "s", 0), \
    'SS':(0, "<h", 2, "<h", 2), \
    'ST':(0, "<h", 2, "s", 0), \
    'TM':(0, "<h", 2, "s", 0), \
    'UI':(0, "<h", 2, "s", 0), \
    'UL':(0, "<h", 2, "<L", 4), \
    'UN':(2, "<I", 4, "<H", 2), \
    'US':(0, "<h", 2, "s", 0), \
    'UT':(2, "<i", 4, "s", 0), \
    'DL':(0, "<I", 4, "s", 0), \
    'UN':(0, "<I", 4, "<h", 4)}

#    'UL':(0, "I", 4, "=L", 4), \  # For screen save ImageType
class DicomRawHeader(object):
    """
    Low level class used for reading reading the header.  It can provide 
    fast, direct access to the header but it is intended to be subclassed.

    Private methods: _ParseHeader(filename)
            Attributes: header. A dictionary with keys equal to the dicom 
            element codes in a string format.

    filename: Filename of a single dicom file.
    """
    def __init__(self, dct=None):
        self.special_actions = { \
                        '7fe0,0010':self._StartImageData, \
                        '7fe0,0000':self._ImageLength, \
                        '0002,0010':self._TransferSyntax, \
#                        '0002,0002':self._SOPClassName, \
                        'fffe,e00d':self._Delimiter, \
                        'fffe,e000':self._Delimiter, \
                        'fffe,e0dd':self._Delimiter}

        self.decode_value = { \
                        'SQ':self._NestedSequenceItem, \
                        'OB':self._NestedBinaryItem, \
                        'OW':self._PaletteItem, \
                        'OX':self._ImageItem}

        self.decode_type = {  'DS':(self._NumberString, float, 4), \
                        'IS':(self._NumberString, int, 4), \
                        'LO':(self._NumberString, long, 4), \
                        'SH':(self._NumberString, int, 2), \
                        'US':(self._Scalar, '<H', 2), \
                        'SS':(self._Scalar, '<h', 2), \
                        'FL':(self._Scalar, '<f', 4), \
                        'FD':(self._Scalar, '<d', 8), \
                        'SL':(self._Scalar, '<l', 4), \
                        'UL':(self._Scalar, '<L', 4), \
                        'CS':(self._CodeString, 0, 1),\
                        'DA':(self._ScalarString, 0, 1), \
                        'SH':(self._ScalarString, 0, 1), \
                        'LO':(self._ScalarString, 0, 1), \
                        'UN':(self._ScalarString, 0, 1)} # Unknown

# Items not in list have reserved_lgth of 0
        self.reserved_lgth = {  'OB':0, \
                                'OF':0, \
                                'OW':0, \
                                'SQ':0, \
                                'UN':0, \
                                'UT':0} 

        if dct is None:
#           Initialize the dictionary.
            self.dct = get_dict()
        else:
            self.dct = dct


    def _ParseHeader(self, filename=None, data=None):
        """
        Purpose: Read header and store.
        Returns: A dictionary. Keys are the dicom tags in the format "7fe0,0010"
                               Each entry is tuple containing the data type, 
                               keyword, and value.
                            
        """

        self.filename = filename
        self.process = True
        self.sq_seqs = {}
        if data:
            self.data = data
        else:
            f = open_gzbz2(filename, "rb")
            self.data = f.read()
            f.close()
        self.flen = len(self.data)
        magic_code = self.data[128:132]

        if magic_code == "DICM": #.endswith("DICM"):
#           File is in dicom format with explicit transfer syntax for now.
            self.syntax = EXPLICIT
        else:
#           Rewind and try implicit syntax.
            fmt = "<H H 2s"
            h1, h2, VR = struct.unpack(fmt, self.data[132:138])
            if lgth_tab.has_key(VR):
#               This is a valid VR, assume explicit syntax but missing
#               128 byte pad, magic code. Hope for meta data.
                self.syntax = EXPLICIT
            else:
#               Assume implicit syntax with no pad, magic code. If wrong, 
#               the program will abort later and return "None".
                self.syntax = IMPLICIT


#       Determine the format and set parameters accordingly.
        if self.syntax == EXPLICIT:
#           If the first value of VR is valid, assume transfer syntax
#           is explicit for now.  This might change if the transfer
#           syntax item is encountered.
            self.idx = 132
            self.lkey = 6
        else:
#           Handle the case encountered with some Siemens files.  
#           The transfer syntax is 1.2.840.10008.1.2, i.e., implicit syntax
#           and Intel-endian, but the transfer item and the "DICM" magic
#           code are not present.  Assume this encoding if encoding is not
#           explicit. Scary, but it works for some *.dcm files.
            self.idx = 0
            self.lkey = 4
        self.action = CONTINUE

#       Read the dicom file and create a dictionary relating tags to values.
        self.hdr = {'UnsupportedSyntax':False}
###        self.syntax = IMPLICIT
        while (self.idx < self.flen):

#           First read the item code and VR if explict encoding.
            fmt = "<HH2s"
            h1, h2, VR = struct.unpack(fmt, self.data[self.idx:self.idx+6])
            self.key = "%04x,%04x" % (h1, h2)
            if VR == 'UN':
                VR = self.dct.get(self.key, ('UN'))[0]
            if lgth_tab.has_key(VR):
                self.syntax = EXPLICIT
                self.VRlgth = 2
                self.lkey = 4 + self.VRlgth
            else:
                self.syntax = IMPLICIT
                VR = self.dct.get(self.key, ('UN'))[0]
                self.VRlgth = 0
                if h1 != 0x0002:
                    self.lkey = 4
                else:
                    self.lkey = 4
                    self.lkey += self.reserved_lgth.get(VR, 0)
                    
#            sys.stdout.write('\nsyntax: %d, idx: 0x%x, (%d), key: %s VR: __%s__' % \
#                        (self.syntax, self.idx, self.idx, self.key, VR))
            self.idx += self.lkey

#           Process special item keys, e.g. nested sequences, delimiters, 
#           and image data.
            apply(self.special_actions.get \
                                    (self.key, self._NoOp), ([VR]))
            if self.action == BREAK:
                break
            elif self.action == CONTINUE:
                continue
            self.action = NOBREAK

            if self.syntax == IMPLICIT or VR not in lgth_tab:
#               If syntax for file or item is implicit, look up the key.
                VR = self.dct.get(self.key, ('UN',0))[0]
#                sys.stdout.write(', xVR: __%s__ ' % VR)

          #  if VR == 'UL':
#         #       sys.stdout.write('\n')
          #      s = ""
          #      for c in self.data[self.idx-self.lkey:self.idx+10]:
          #          if c.isdigit():
          #              s = "%s%x" % (s,int(c))
          #          elif c.isalnum(): 
          #              s = "%s%s" % (s,c)
          #          else:
          #              s = "%s_0x%x" % (s,fromstring(c,ubyte))
          #       sys.stdout.write(" data: __%s__" % s)

#           Lookup the characteristics of this item
            self.pinfo = lgth_tab.get(VR.strip(), None)
            if self.pinfo is None:
#               Couldn't find tag, abort.
                sys.stderr.write( \
                    '\nKeyError in read_dicomheader: %s , VR=__%s__\n\n'% \
                    (self.key, VR.strip()))
                self.hdr = None
                return None

#           Decode the tag format tuple retrieved above.
            skip, fmt_VL, lgth_VL, self.dfmt, self.sizeof = self.pinfo
            if self.syntax == IMPLICIT: # and h1 > 0x002:
                skip = 0  # JMO 12/31/09
                self.pinfo = [0, self.pinfo[1], self.pinfo[2], self.pinfo[3], self.pinfo[4]]
                lgth_VL = 4
                fmt_VL = '<I'
            sVL = self.data[self.idx+skip:self.idx+skip+lgth_VL]
#            sys.stdout.write(' skip: %d, lgth_VL: %d, fmt_VL: %s, sVL: %d' %\
#                             (skip, lgth_VL, fmt_VL,len(sVL)))
###            if self.VL <= 0:
###                sys.stderr.write('\n_ParseHeader: Could not parse header of %s\n' % filename)
###                return None
            self.VL = struct.unpack(fmt_VL, sVL)[0]
#            sys.stdout.write(' VL: 0x%x (%d) ' % (self.VL, self.VL))
#            sys.stdout.write('info(skip, fmt_VL, lgth_VL, dfmt, sizeof, VL): %d %s %d %s %d, VL: 0x%2x' % \
#                    ( skip, fmt_VL, lgth_VL, self.dfmt, self.sizeof,self.VL))
            if self.VL == 0xffffffff:
                self.VL = 0
            elif self.VL < 0 or self.VL > len(self.data): 
#                sys.stdout.write(' len(self.data): 0x%x' % len(self.data))
                raise RuntimeError( \
                '\n_ParseHeader: Could not parse header of %s\n' % filename)

            if h1 == 16 and h2 == 16:
#               This is patient_name, save info for anonymization.
                self.pn_tag ={'offset':self.idx,'length':self.VL}
            elif h1 == 16 and h2 == 48:
                self.pbd_tag ={'offset':self.idx,'length':self.VL}

            self.idx += skip + lgth_VL

            value = apply(self.decode_value.get(VR, self._DefaultItem), ())
#            sys.stdout.write(', value: __%s__' % (value))

#           Convert value.
            decoder, format, unit_lgth = self.decode_type.get(VR,  \
                                    (self._NoDecode, 0, 0))
            if self.process:
#               Get item value, i.e., Start of image data, transfer syntax
#               Don't process non-image items such as icon image sequences.
                data_value = apply(decoder, (value, format, unit_lgth))
                self.hdr[self.key] = (VR, self.VL, data_value)
#                sys.stdout.write(', value: __%s__' % (data_value))
#                sys.stdout.write(' idx: 0x%04x' % self.idx)
#        keys = self.hdr.keys()
#        keys.sort()
#        for key in keys:
#            print key, self.hdr[key]
        return self.hdr

    def _NoOp(self, VR):
        self.action = NOBREAK
        return NOBREAK

    def _StartImageData(self, VR):
        skip, fmt_VL, lgth_VL, self.dfmt, self.sizeof = lgth_tab[VR.strip()]
        self.VL = struct.unpack("<I", self.data[self.idx+skip: \
                                    self.idx+skip+lgth_VL])[0]
        self.start_image = self.idx+skip+lgth_VL
        self.hdr['StartImage'] = ("UL", 4, self.idx+skip+lgth_VL)
        self.action = BREAK
        return BREAK

    def _ImageLength(self, VR):
        skip, fmt_VL, lgth_VL, self.dfmt, self.sizeof = lgth_tab[VR.strip()]
        if self.syntax == IMPLICIT:
            skip = 2
        self.VL = struct.unpack("<h", self.data[self.idx: \
                                                self.idx+lgth_VL])[0]
        img_lgth = struct.unpack(self.dfmt, \
                    self.data[self.idx+skip+lgth_VL:self.idx+skip+lgth_VL+self.VL])[0]
#        sys.stdout.write('\nVL: %d img_lgth: %d' % (self.VL, img_lgth))
        self.hdr[self.key] = (VR, self.VL, img_lgth)
        self.idx += lgth_VL + self.VL + skip
        self.action = CONTINUE # JMO 12/30/09
        return CONTINUE # JMO 12/30/09

    def _SOPClassName(self, VR):
        pass
#        sys.exit(1)

    def _TransferSyntax(self, VR):
#       Transfer syntax is always in explicit in this module. Decode it.
        skip, fmt_VL, lgth_VL, dfmt, sizeof = lgth_tab.get(VR.strip(), None)
        sVL = self.data[self.idx+skip:self.idx+skip+lgth_VL]
        self.VL = struct.unpack(fmt_VL, sVL)[0]
        self.idx = self.idx + skip + lgth_VL
        code = self.data[self.idx:self.idx+self.VL-1]
        code = translate_printing(code)
        newcode = ''
        for c in code:
            if c.isalnum() or c == '.':
                newcode += c
        code = newcode
        self.hdr['TransferSyntax'] = [code]
        self.idx = self.idx + self.VL
        self.action = CONTINUE
        if code == '1.2.840.10008.1.2':
            self.syntax = IMPLICIT
            self.hdr['Endian'] = 'Big'
        elif code == '1.2.840.10008.1':
#           Save screen syntax
            self.syntax = EXPLICIT
            self.hdr['Endian'] = 'Big'
            self.hdr['UnsupportedSyntax'] = True
            self.action = BREAK
        elif code == '1.2.840.10008.1.2.1':
            self.syntax = EXPLICIT
            self.hdr['Endian'] = 'Big'
        elif code == '1.2.840.10008.1.2.2':
            self.syntax = EXPLICIT
            self.hdr['Endian'] = 'Little'
        else:
            self.hdr = None
            raise IOError('Transfer syntax (%s) is not supported.' % code + \
                          'Could not read %s' % self.filename)
        return CONTINUE


    def _Delimiter(self, dummy):
#       Item or sequence delimiter. (Clunie calls this a "NONE" item)
        self.VL = struct.unpack("<I", self.data[self.idx+4:self.idx+8])[0]
#        self.VL = struct.unpack("I", self.data[self.idx:self.idx+4])[0]
        if self.VL == 0xffffffff:
            self.VL = 0
        if self.syntax == EXPLICIT:
            self.idx = self.idx + 2
        else:
            self.idx = self.idx + 4
        self.action = CONTINUE
        return CONTINUE

    def _NestedSequenceItem(self):
#       This is data in a separate module.  Module designations are ignored, 
#       so these items are extraneous.
        if self.syntax == EXPLICIT:
            self.idx = self.idx + 0
        else:
            self.idx = self.idx - 2
        self.action = CONTINUE
        self.image_sequence = self.dct.get(self.key, ['unknown','unknown'])[1]
        if self.image_sequence == 'IconImageSequence':
#           Some Siemens files have icons in them.
            self.process = False
   #     elif self.image_sequence != 'ReferencedImageSequence' and \
   #                                     self.image_sequence.lower() != 'none':
#  #         Only process a given sequence type once.
   #         self.process = False
        else:
            self.process = True
#        print 900, self.image_sequence
        return CONTINUE

    def _NestedBinaryItem(self):
#       Binary data.  Don't load it.
#        sys.stdout.write('\n_NestedBinaryItem: VL: %d' % self.VL)
        if self.syntax == EXPLICIT:
            self.idx = self.idx + self.VL
        else:
            skip, fmt_VL, lgth_VL, self.dfmt, self.sizeof = self.pinfo
            self.idx = self.idx - (skip + lgth_VL)
            sVL = self.data[self.idx:self.idx+lgth_VL]
            self.VL = struct.unpack(fmt_VL, sVL)[0]
            self.idx = self.idx + lgth_VL +  self.VL
        self.action = NOBREAK

        return('')

    def _PaletteItem(self):
#        self.key = 'StartImage'
#        self.start_image = self.idx + self.VL
        self.idx = self.idx + self.VL
        self.action = NOBREAK
        return('')

    def _ImageItem(self):
#       This is the image.  Remember where it is but don't load it.
        self.key = 'StartImage'
        self.start_image = self.idx + self.VL
        self.idx = self.idx + self.VL + 132
        self.action = NOBREAK
        return('')

    def _DefaultItem(self):
#       This is called from almost all items.
        value = self.data[self.idx:self.idx+self.VL]
        self.idx = self.idx + self.VL
        self.action = NOBREAK
        return value

    def _NumberString(self, value, conversion, unit_lgth):
#       Value is an array delimited by "\\"
        words = value.split("\\")
        try:
            cval =  map(conversion, words)
        except ValueError:
            cval = value
        if len(cval) == 1:
            cval = cval[0]
        return cval

    def _CodeString(self, value, dummy, unit_lgth):
#       Value is an array of strings, but with coded meaning.
        val =  value.split("\\")
        if len(val) == 1:
            val = val[0]
        return val

    def _ScalarString(self, value, dummy, unit_lgth):
#       Value is a single string or an unknown type.
        if isinstance(value, str):
            if len(value) == 1:
                value = value[0]
        return value 

    def _Scalar(self, value, code, unit_lgth):
#      Value is one or more numerical, scalar values.
        # Value is one or more numerical, scalar values.
        el_no = self.VL/unit_lgth
        # Code might be prefixed with format character
        if code[0] in ('=', '<', '>', '!', '@'):
            whole_code = '%s%d%s' % (code[0], el_no, code[1:])
        else:
            whole_code = '%d%s'% (el_no, code)
#       whole_code = '%d%s'% (self.VL/unit_lgth, code)
        cval = struct.unpack(whole_code, value)
        if len(cval) == 1:
            cval = cval[0]
        return cval

    def _NoDecode(self, value, dummy, dummy1):
#       This is called for items that will not be decoded. Returns the 
#       input string which may or may not be printable.
        return value


class Dicom(DicomRawHeader):
    """
    Purpose: Provide high level interface to dicom header and image.
    Public methods: 
    """
    def __init__(self, filename=None, nhdr=None, data=None):
        """
        Purpose: Read header on initialization and save data.
        Inputs: filename, the name directory to be read or of a single file.
        Public methods: 
            get_value(tag): Return value of a dicom tag.
            get_keyword(tag): Return keyword of tag.
            get_keyword_value(tag): Return keyword and value of a dicom tag.  
            read_image(): Return image from the file specified at init. The
                image is returned as the native number type. (images stored
                in 12-bit packed format are returned as short integers.
            get_series(): Returns all images in the current directory. Images
                in mosaic are unpacked. Images can have up to five dimensions:
                x, y, z, time, and misc.  The miscellaneous dimension will
                only be used if it can be unambiguously determined. For 
                example, if a series contains real, imaginary, magnitude,
                and phase components of images acquired at two different 
                echo times, the time dimension will be four and the misc
                dimension will be 2.
            get_native_header(scan=False): Returns the 
                "entire" header.  Not all dicom keys are returned in the
                interest of efficiency.  The header is a dictionary with
                keywords derived from the dicom dictionary description. The
                default action is the return the header for a single 
                dicom file.  This will be incomplete because a single does
                not completely describe the data: the slice direction is 
                by the reading program and it is impossible to tell if 
                multiple sets of data are stored in a single directory.  For
                example, on a GE scanner, multiple acquisitions will be stored 
                in the same directory - one for each time the scan button is 
                clicked.  These might be acquired with different  parameters
                (such as flip angle, TR, TE etc).  The only way to reliably
                read them is to open every file in the directory and examine
                the header.  If scan=True, this will done.  The scan=False
                must be used carefully and is only supplied because scanning 
                the directory is very inefficient (since EPIs often have > 
                10000 files per directory.
        """

#        self.timer = Timer()
        DicomRawHeader.__init__(self)

        if data is not None:
            file1 = filename
            self.nfiles = 1
            self.data = data
            filename = None
            self.dirname = None
        elif not filename:
            raise RuntimeError( \
            'Neither filename nor data were present while creating Dicom object.')
        else:
            if os.path.isdir(filename):
                self.dirname = filename
                files = os.listdir(self.dirname)
                self.nfiles = len(files)
                for f in files: 
                    file1 = "%s/%s" % (filename, f)
                    if os.path.isdir(file1):
                        continue
                    if file1.endswith('.yaml'):
                        continue
                    elif file1.endswith('.bz2') or isdicom(file1):
                        break
                self.data = None
            else:
#               This must be a filename.
                self.dirname = os.path.dirname(filename)
                file1 = filename
                self.data = None
                self.nfiles = 1

        
        if nhdr is None:
            self.hdr = self._ParseHeader(file1, data=data)
            if self.hdr is None:
                raise RuntimeError( \
                '_ParseHeader: Could not parse header, %s\n' % file1)
                return None
            elif self.hdr['UnsupportedSyntax']:
                if self.hdr['TransferSyntax'][0] == '1.2.840.10008.1':
                    mesg = 'This is a screen-capture file.'
                else:
                    mesg = ''
                raise IOError( \
                'Transfer syntax (%s) is not supported for:\n  %s\n' % \
                (self.hdr['TransferSyntax'], file1) + '\n\t--- %s ---\n' %mesg)
                
        else:
            self.hdr = None

        if nhdr is not None:
            self.dicominfo = nhdr.get('dicominfo', None)
        else:
            self.dicominfo = None
        if self.dicominfo is not None:
            self.scan = True
        else:
            self.scan = False

        self.filename = filename
        self.flip_slice_order = False

        if self.hdr is not None:
#           Retrieve pixel characteristics.
            MediaStorageSopClassUid = (self.hdr.get('0002,0002', -1)[2]).strip().lstrip()
            while not MediaStorageSopClassUid[-1].isalnum():
                MediaStorageSopClassUid = MediaStorageSopClassUid[:-1]
            if MediaStorageSopClassUid == MEDIA_STORAGE_SOP_CLASS_SCREEN_CAPTURE:
#               This is the storage class for "secondary screen captures". These
#               are not supported.
   #             self.hdr = None
   #             return
                tmp = self.hdr.get('0028,0101', -1)
                if isinstance(tmp, tuple):
                    self.bits_stored = int(tmp[2])
                else:
                    self.bits_stored = int(tmp)
                self.high_bit = self.hdr['0028,0102'][2]
#               PixelRepresentation, 1=signed, 0=unsigned
                self.signed = self.hdr['0028,0103'][2] 
                self.rows = self.hdr['0028,0010'][2]
                self.cols = self.hdr['0028,0011'][2]
                self.bits_alloc = self.hdr['0028,0100'][2]
            elif MediaStorageSopClassUid != MEDIA_STORAGE_SOP_CLASS_UID:
                mesg = \
                'Unrecognized storage class: __%s__\nsupported class: __%s__\nFile: %s\n' % \
                (MediaStorageSopClassUid, MEDIA_STORAGE_SOP_CLASS_UID, filename)
                raise RuntimeError(mesg)
            tmp = self.hdr.get('0028,0101', -1)
            if isinstance(tmp, tuple):
                self.bits_stored = int(tmp[2])
            else:
                self.bits_stored = int(tmp)
            if self.bits_stored  < 0:
                if filename is None:
                    name = '<buffer>'
                else:
                    name = filename
#                sys.stderr.write('Could not access raw header for %s\n' % name)
                print '\n200 ',tmp, self.bits_stored
                errstr = 'Error parsing dicom header: %s' % name
                raise RuntimeError(errstr)
#            self.bits_stored = self.hdr['0028,0101'][2]
            self.high_bit = self.hdr['0028,0102'][2]
#           PixelRepresentation, 1=signed, 0=unsigned
            self.signed = self.hdr['0028,0103'][2] 
            self.rows = self.hdr['0028,0010'][2]
            self.cols = self.hdr['0028,0011'][2]
            self.bits_alloc = self.hdr['0028,0100'][2]
        else:
            self.bits_stored = nhdr['BitsStored']
            if not nhdr.has_key('BitsAllocated'):
#               Workaround for cases where yaml files omits BitsAllocated.
                self.hdr = self._ParseHeader(file1, data=data)
                nhdr['BitsAllocated'] = self.hdr['0028,0100'][2]
            self.bits_alloc = nhdr['BitsAllocated']

            self.high_bit = nhdr['HighBit']
            self.signed = nhdr['PixelRepresentation']
            self.rows = nhdr['Rows']
            self.cols = nhdr['Columns']

        self.slice_size = self.cols*self.rows*self.bits_stored/8
        self.encoding = ('%d_%d'% (self.bits_stored, self.bits_alloc))
 
        self.image_conversion = {'8_8':self._stored8_alloc8, \
                                '16_16':self._stored16_alloc16, \
                                '32_32':self._stored32_alloc32, \
                                '12_12':self._stored12_alloc12, \
                                '12_16':self._stored12_alloc16}
#        sys.stdout.write( ' 3a ' + self.time.ReadTimer() + '\n')

    def get_value(self, tag, default=None):
        """
        Purpose: Return the value of a Dicom tag.
        Inputs: key: A dicom tag in the form "7fe0,0010"
                filename: filename to be read.
        Outputs: The value of the tag.
        """
        return self.hdr.get(tag,[default])[-1]

    def Anonymize(self, output_dir=None):
        """
        Remove patient name from header.
        If output_dir is provided, the input image will be left
        unchanged and the anonymized version will be written to
        output_dir.
        """
        fnames = os.listdir(self.dirname)
        for fname in fnames:
            if fname.endswith('.gz') or fname.endswith('.bz2'):
                return 1
            fullname = '%s/%s' % (self.dirname, fname)
            hdr = self._ParseHeader(fullname)
            if hdr is None:
                continue
            pnlgth = self.pn_tag['length']
            pnoff = self.pn_tag['offset']
            newtag = self.PatientNameTranslation(self.data[pnoff:pnoff+pnlgth])

            f = open(fullname, 'r+')
            f.seek(pnoff)
            f.write(newtag)

            pnlgth = self.pbd_tag['length']
            pnoff = self.pbd_tag['offset']
            newbd = self.PatientBirthDateTranslate(\
                                        self.data[pnoff:pnoff+pnlgth])
            f.seek(pnoff)
            f.write(newbd)
            f.close()
        return 0
        

    def get_keyword(self, key):
        """
        Purpose: Return the keyword corresponding to a Dicom tag.
        Inputs: key: A Dicom tag.
        Notes: Assumes that the class was initialized with a filename.
        """
        return(self.dct[key][1])

    def get_keyword_value(self, tag):
        """
        Purpose: Return the keyword and value of a Dicom tag.
        Inputs: key: A dicom tag in the form "7fe0,0010"
        Outputs: The value of the key.
        Notes: Assumes that the class was initialized with a filename.
        """
        if self.dct.has_key(tag) and self.hdr.has_key(tag):
            return((self.dct[tag][1], self.hdr[tag][-1]))
        else:
            return None

    def get_slice_fast(self, start_image, fullpath):
        """
        Read a single dicom slice.
        nhdr: Native dicom header (read with scan=true)
        start_image: Beginning of binary data in bytes.
        fullpath: Fully qualified path to the file.
        """

        if os.path.exists(fullpath):
            f = open_gzbz2(fullpath, 'r')
        elif fullpath.endswith('.bz2') and os.path.exists(fullpath[:-4]):
            f = open_gzbz2(fullpath[:-4], 'r')
        elif fullpath.endswith('.gz') and os.path.exists(fullpath[:-3]):
            f = open_gzbz2(fullpath[:-3], 'r')
        elif os.path.exists(fullpath + '.bz2'):
            fullpath = fullpath + '.bz2'
            f = open_gzbz2(fullpath[:-4], 'r')
        else:
            errstr = 'File does not exist: %s' % fullpath + \
                     except_msg('get_slice_fast')
            raise IOError(errstr)
        f.seek(start_image)
#        self.imgdata = f.read(self.slice_size)
        self.imgdata = f.read()
        f.close()
        apply(self.image_conversion.get(self.encoding, self._not_supported), ())
        return  reshape(self.img, [self.rows, self.cols])
        
    def read_image(self):
#       Purpose: Read a single image from disk
#       Inputs: fdata: file object containing image to be read.
#               hdr: header as read by the read() function.

        start_image = self.hdr['StartImage'][2]

        encoding = ('%d_%d'% (self.bits_stored, self.bits_stored))
        self.imgdata = self.data[start_image:]
        apply(self.image_conversion.get(encoding, self._not_supported), ())
        if self.modality == 'PT':
#           PET data get rescaled.
            self.img = self.nhdr['RescaleSlope']*self.img.astype(float) + \
                        self.nhdr['RescaleIntercept']
        return  reshape(self.img, [self.cols, self.rows])

    def _not_supported(self):
        print "Images with pixel %d bits long with %d bits allocated " + \
         "per pixel are not supported" % (self.bits_stored, self.bits_stored)
        return(None)

    def _stored8_alloc8(self):
#       Byte.
        self.img = fromstring(self.imgdata, int8)
        if not self.signed:
            self.img = where(self.img>0, self.img, 256+self.img)

    def _stored16_alloc16(self):
#       Short integer.
        if not self.signed:
            self.img = fromstring(self.imgdata, ushort)
        else:
            self.img = fromstring(self.imgdata, short)

    def _stored32_alloc32(self):
#       Integer
        self.img = fromstring(self.imgdata, int)
        if not self.signed:
            self.img = where(self.img>0, self.img, 2**32+self.img)

    def _stored12_alloc12(self):
#       12 bit pixels are packed into 16 bit words.
        img = fromstring(self.imgdata[:self.rows*self.cols*3/2], int16)
        self.img = zeros(self.rows*self.cols, int16)
        idx = 3*arange(self.rows*self.cols/4)
        jdx = 4*arange(self.rows*self.cols/4)
        img1 = take(img, idx) & 0xFFF
        put(self.img, jdx, img1)
        img1 = ((take(img, idx)/4096) & 0xf) + (take(img, idx+1)*16 & 0x0ff0)
        put(self.img, jdx+1, img1)
        img1 = ((take(img, idx+1)/256) & 0xff) + (take(img, idx+2)*256 & 0x0f00)
        put(self.img, jdx+2, img1)
        img1 = (take(img, idx+2)/15) & 0xfff
        put(self.img, jdx+3, img1)
        if self.signed:
            where(self.img > 2047, 2047-self.img, self.img)

    def _stored12_alloc16(self):
#       Each pixel is 12 bits long and padded with 4 unused bits.
        if self.high_bit == 11:
            self.img = fromstring( \
                        self.imgdata[:self.rows*self.cols*2], int16)
            if self.signed:
                where(self.img > 2047, 2047-self.img, self.img)
        elif self.high_bit == 15:
            self.img = fromstring(self.imgdata[:self.rows*self.cols*2], int16)
            if self.signed:
#               Shift down sign bit.
                self.img = self.img/16
            else:
#               Shift right one, mask off sign bit, then shift another 3.
                self.img = ((self.img/2) & 0x7fff)/8

    def get_series(self, dirname=None, dtype=None, frame=-1, mtype=-1):

        if dtype is None:
            dtype = int16
        if dirname is not None:
            self.dirname = dirname

        if self.scan is False:
            nhdr = self.get_native_header(scan=True)
        else:
            nhdr = self.nhdr
        if nhdr is None:
            sys.stderr.write( \
                '\nread_dicom_file: Could not read header from %s\n\n'%filename)
            return None

        dims = self.dicominfo['dims']
        dirname = dims['dirname']

#        if self.modality == 'MR':
        if self.nhdr['Modality'] == 'MR':
            self.nhdr['EchoTimes'] = dims['EchoTimes']

        if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
            xdim = self.nhdr['AcquisitionMatrix'][0]
            ydim = self.nhdr['AcquisitionMatrix'][0]
            self.mosaic = True
        else:
            xdim = self.nhdr['Columns']
            ydim = self.nhdr['Rows']
            self.mosaic = False

        zdim = self.nhdr['LocationsInAcquisition']
        tdim = frame > -1 and 1 or dims['tdim']
        mdim = mtype > -1 and 1 or dims['TypeDim']
        if frame > -1:
            frames = [frame]
            frm0 = frame
        else:
            frames = range(dims['tdim'])
            frm0 = 0

        if mtype > -1:
            mtypes = [mtype]
        else:
            mtypes = range(dims['TypeDim'])

        self.image = zeros([mdim, tdim, zdim, ydim, xdim], dtype)

        if mdim  > 1:
            self.nhdr['ndim'] = 5
        elif tdim >  1:
            self.nhdr['ndim'] = 4
        elif zdim > 1:
            self.nhdr['ndim'] = 3
        else:
            self.nhdr['ndim'] = 2
        
#        for inst in self.dicominfo.keys():
        for m in mtypes:
            for t in frames:
#                self.ActualFrameDuration = self.get_value('0018,1242')
                if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
#                   Unpack image from Mosaic format (A Siemens format 
#                   consisting of a Montage of images in one frame).
                    inst = '%d_%d' % (m, t)
                    if self.dicominfo.has_key(inst):
                        path, start_image = self.dicominfo[inst]
                    else:
                        raise RuntimeError(\
                        'self.dicominfo does not have instance %s' % inst)
                    img = self.get_slice_fast(\
                                        start_image, '%s/%s' % (dirname,path))
                    for z in range(zdim):
                        y0, x0 = self.mosaic_slcloc[z]
                        self.image[m, t, zdim-z-1, :, :] =  \
                            img[x0:x0+xdim, y0:y0+ydim].astype(dtype)
                else:
                    for z in range(zdim):
                        inst = '%d_%d_%d' % (m, t, z)
                        path, start_image = self.dicominfo[inst]
                        fname =('%s/%s' % (dirname,path)).replace(' ','')
                        self.image[m,t-frm0,z,:,:] = self.get_slice_fast(start_image, fname)

        return self.image

    def get_native_header(self, scan=False, scanned=False):
        """
        Purpose: Get the entire header.
        Returns: A dictionary containing the entire header.
        If "scan" is true, each file will be read to ensure that the 
        third, fourth, and fifth dimensions are correct.
        if "scanned" is true, it will be assumed that the data have already
        been scanned that the dicominfo attribute is correct.
        """

        if self.hdr is None:
            return None

        if scanned:
            scan = True

#        sys.stdout.write( ' 1d ' + self.timer.ReadTimer() )
#       Keys to extract from the dicom header vary with modality.
        self.modality = self.get_value('0008,0060')
        if self.modality is None:
            sys.stderr.write("get_native_header: Error reading header.\n")
            return None
        elif self.modality == 'PT':
            modality_keys = pet_hdrkeys
        elif self.modality == 'MR':
            modality_keys = mri_hdrkeys
        else:
            modality_keys = []

        self.nhdr = {'filetype':'dicom'}
#       Read the header from low-level dictionary.
        for entry in hdrkeys + modality_keys:
            self.nhdr[entry[0]] = self.get_value(entry[1])
        if not self.nhdr['ImagesInSeries']:
#           Assume a single frame image.
            self.nhdr['ImagesInSeries'] = 1

#       Convert posix time to human-readable time.
        if isinstance(self.nhdr['ActualSeriesDateTime'], float):
            self.nhdr['SeriesDateTime'] = \
            datetime.fromtimestamp(self.nhdr['ActualSeriesDateTime']).ctime()
        else:
            self.nhdr['SeriesDateTime'] = self.nhdr['ActualSeriesDateTime']

        if self.modality == 'MR':
            if self.nhdr["PulseSequenceName"] is None:
                if self.nhdr.has_key("InternalPulseSequenceName"):
                    self.nhdr["PulseSequenceName"] = \
                         self.nhdr.get("InternalPulseSequenceName",'Unknown')
                else:
                    self.nhdr["PulseSequenceName"] = \
                                    self.nhdr.get("PulseSequence", 'Unknown')
        if  self.nhdr["PulseSequenceName"] is None:
             self.nhdr["PulseSequenceName"] = 'Unknown'
        self.nhdr['FileName'] = self.filename
        if self.nhdr['SpacingBetweenSlices'] is not None and \
                            self.nhdr['SliceThickness'] is not None:
            self.nhdr['SliceGap'] = self.nhdr['SpacingBetweenSlices'] - self.nhdr['SliceThickness']
        else:
            self.nhdr['SliceGap'] = 0
            self.nhdr['SpacingBetweenSlices'] = self.nhdr['SliceThickness']

        if not self.nhdr['Manufacturer']:
            self.nhdr['Manufacturer'] = ''
        
        if self.nhdr.get('Manufacturer','').startswith('GE MEDICAL') or \
                            self.nhdr.get('Manufacturer','').startswith('GEMS'):
            if self.nhdr.get('GEImageType',None) == None:
                self.nhdr['GEImageType'] = ge_type_to_idx['Magnitude']
            self.nhdr['RawImageType'] = self.nhdr['ImageType']
            self.nhdr['ImageType'] = self.nhdr['GEImageType']
        elif self.nhdr.get('Manufacturer','').replace(' ','') == 'SIEMENS':
            self.nhdr['ImageType'] = siemens_type_to_idx.get(self.nhdr['ImageType'][2], 0)
            if self.modality == 'MR':
                self.nhdr['PulseSequenceName'] = self.nhdr['SequenceName']
                self.nhdr['InternalPulseSequenceName'] = self.nhdr['SequenceName']
        elif self.nhdr.get('Manufacturer','').replace(' ','').lower() == \
                                                'philipsmedicalsystems':
            self.nhdr['ImageType'] =  phillips_type_to_idx.get( \
                                    self.nhdr['ImageType'][2],'Magnitude')
        else: # Hope that Siemens encoding works.
#               It won't work for GE.
            self.nhdr['ImageType'] = siemens_type_to_idx.get(self.nhdr['ImageType'][2], 0)
        self.nhdr['Channel'] = idx_to_type.get(self.nhdr['ImageType'], 0)
        self.nhdr['ImageType'] = idx_to_type[self.nhdr['ImageType']]

        if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
            self.nhdr['RowsMosaic'] = self.nhdr['Rows']
            self.nhdr['ColsMosaic'] = self.nhdr['Columns']

        if scanned:
            dims = self.dicominfo['dims']
            self.nhdr['SpacingBetweenSlices'] = \
                (dims['EndLoc'] - dims['StartLoc'])/(dims['zdim'] - 1.)
        if scan == True and scan != self.scan:
#           Read every file in the directory to find out what is really
#           there and where each slice is located.
            self.scan = True
            if scanned:
                status = True
            else:
                status = self._ScanDicomFiles()
            dims = self.dicominfo['dims']
            self.nhdr['SpacingBetweenSlices'] = \
                (dims['EndLoc'] - dims['StartLoc'])/(dims['zdim'] - 1.)
            if status is None:
                sys.stderr.write(\
                "get_native_header: Error while scanning files.\n")
                return None
#        elif self.nhdr['ImagesInSeries'] is None:
#           Assume that slices are ordered so position increases. Then zdir = 1.
        if self.filename:
            if os.path.isdir(self.filename):
                self._FastScanDicomFiles()

        if scan:
            if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
                self.nhdr['LocationsInAcquisition'] = len(self.mosaic_slcloc)
            elif self.nhdr['PulseSequenceName'].strip() != '3-Plane':
                self.nhdr['LocationsInAcquisition'] = dims['zdim']
        else:
            if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
                self.nhdr['LocationsInAcquisition'] =  \
                 (self.nhdr['RowsMosaic']*self.nhdr['ColsMosaic'])/ \
                            self.nhdr['AcquisitionMatrix'][0]**2
                self.mosaic_slcloc = arange(self.nhdr['LocationsInAcquisition'])
            elif self.nhdr['ImagesInAcquisition'] is not None:
                self.nhdr['LocationsInAcquisition'] = \
                                        self.nhdr['ImagesInAcquisition']
            else:
                self.nhdr['LocationsInAcquisition'] = \
                                        self.nhdr['ImagesInSeries']

        psdname = self.nhdr.get('PulseSequenceName',None)
        if psdname is not None and '3dfsepcasl' in psdname:
            self.nhdr['ImagesInSeries'] = self.nhdr['LocationsInAcquisition']

        if self.nhdr['AcquisitionMatrix']:
            xdim = self.nhdr['AcquisitionMatrix'][0]
            ydim = self.nhdr['AcquisitionMatrix'][0]
            xsize = self.nhdr['PixelSpacing'][0]
            ysize = self.nhdr['PixelSpacing'][1]
            image_position = self.nhdr['ImagePosition']
            R = dicom_to_rot44(self.nhdr['ImageOrientation'], ones([3],float), \
                xsize, ysize, self.nhdr['SpacingBetweenSlices'], xdim, ydim, \
                self.nhdr['LocationsInAcquisition'], self.flip_slice_order)[0]
            if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
#               Images stored as a mosaic that must be broken up.

                ncol = float(self.nhdr['ColsMosaic']/xdim)
                nrow  = len(self.mosaic_slcloc)/ncol
                if scan:
                    self.nhdr['ImagePosition'][2] = dims['StartLoc']

#               Compute origin. Mosaic images specify the starting location as the 
#               "upper" left corner of the entire, nonexistent mosaic (go figure).
                dx = xsize*(self.nhdr['ColsMosaic'] - xdim  )/2.
                dy = ysize*(self.nhdr['RowsMosaic'] - ydim  )/2.
                self.nhdr['Columns'] = xdim
                self.nhdr['Rows'] = ydim
            else:
                dx = 0.
                dy = 0.
#                if scan:
#                    self.nhdr['LocationsInAcquisition'] = dims['zdim']
        else:
            xdim = 1
            ydim = 1
            dx = 1.
            dy = 1.
            R = identity(4).astype(float)
            image_position = zeros(3, float)
            self.nhdr['ndim'] = 2
            self.nhdr['NumberOfFrames'] = 1
            self.nhdr['TypeDim'] = 1
            self.nhdr['LocationsInAcquisition'] = 1
            self.nhdr['ImagesInSeries'] = 1
            self.nhdr['Rows'] = 1
            self.nhdr['Columns'] = 1
            self.nhdr['PixelSpacing'] = [1., 1.]

        zaxis = int(dot(R[:3,:3].transpose(),arange(3))[2])
        if scan:
            image_position[zaxis] = dims['StartLoc']
        if sign(R[zaxis,:3].sum()) == sign(image_position[zaxis]):
#           Invalid transformation matrix, flip the starting point.
            dz = -(self.nhdr['LocationsInAcquisition'] - 1)* \
                                self.nhdr['SpacingBetweenSlices']
        else:
            dz = 0

        offset =  dot(R[:3,:3], array([dx, dy, dz]))
        image_position =  image_position + offset
        if self.dicominfo is not None:
            dims['StartLoc'] =  image_position[2]# + offset[2]
        #image_position[:2] =  image_position[:2] + offset[:2]

        self.nhdr['ImagePosition'] = image_position
        R[:3,3] = image_position
        self.nhdr['R'] = R

        if scan == True:
            self.scan = True
            self.nhdr['StartLoc'] = dims['StartLoc']
            self.nhdr['EndLoc'] = dims['EndLoc']
            self.nhdr['TypeDim'] = dims['TypeDim']
            self.nhdr['NumberOfFrames'] = dims['tdim']
            self.nhdr['dirname'] = dims['dirname']
            self.nhdr['DicomInfo'] = self.dicominfo
            self.nhdr['EchoTimes'] = dims['EchoTimes']
        elif self.modality == 'MR' and \
                self.nhdr['PulseSequenceName'] is not None and \
                self.nhdr['PulseSequenceName'].strip() == 'epiRT' and  \
                self.nhdr['Manufacturer'] == 'GE MEDICAL SYSTEMS':
            self.nhdr['NumberOfFrames'] = self.nhdr['FastPhases']
#            self.nhdr['TypeDim'] = self.nhdr['ImagesInSeries']/ \
            self.nhdr['TypeDim'] = self.nfiles/ \
                (self.nhdr['LocationsInAcquisition']*self.nhdr['FastPhases'])
        elif self.nhdr['LocationsInAcquisition'] or self.nhdr['ImagesInSeries']:
            if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
                self.nhdr['NumberOfFrames'] = self.nhdr['ImagesInSeries']
            else:
#                self.nhdr['LocationsInAcquisition'] = \
#                                    self.nhdr['ImagesInSeries']
                self.nhdr['NumberOfFrames'] = self.nhdr['ImagesInSeries']/ \
                                    self.nhdr['LocationsInAcquisition']
            self.nhdr['TypeDim'] = 1
        else:
#           Unrecognized header, return what we have.
            self.nhdr['ndim'] = 1
            self.nhdr['NumberOfFrames'] = 1
            self.nhdr['TypeDim'] = 1
            return self.nhdr

        if float(self.nhdr['ImagesInSeries']) % \
            float(self.nhdr['LocationsInAcquisition']) and self.data is None:
            raise IOError(\
            'Missing slice(s): Number of slices acquired is not evenly\n' \
            '\t\tdivisible by the number of slices per frame. ***\n' + \
            '\tDicom directory: %s\n' % self.filename + \
            '\tNumber of slices acquired: %d\n' % self.nhdr['ImagesInSeries']+\
            '\tNumber of slices per frame: %d\n' % \
                                    self.nhdr['LocationsInAcquisition'] + \
            '\tNumber of image types per series: %d\n' % self.nhdr['TypeDim'])

        if self.nhdr['TypeDim']  > 1:
            self.nhdr['ndim'] = 5
        elif self.nhdr['NumberOfFrames'] >  1:
            self.nhdr['ndim'] = 4
        elif self.nhdr['LocationsInAcquisition']  > 1:
            self.nhdr['ndim'] = 3
        else:
            self.nhdr['ndim'] = 2

        return self.nhdr

    def _FastScanDicomFiles(self):
#       Get number of frames. Assumes mdim = 1
        ndicom = 0
        if len(self.dirname) == 0:
            ndicom = 1
        else:
            files = os.listdir(self.dirname)
            for fname in files:
                fullfile = "%s/%s" % (self.dirname, fname)
                if isdicom(fullfile):
                    ndicom = ndicom + 1
        self.nhdr['ImagesInSeries'] = ndicom

    def _ScanInit(self):
        """
        Initialize data for scanning a dicom directory.
        """
        if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
#           Must check to see where slices are stored for Mosaic format.
            self.read_image()
            xdim = self.nhdr['AcquisitionMatrix'][0]
            ydim = self.nhdr['AcquisitionMatrix'][0]
            self.mosaic_slcloc = []
            img = self.img.reshape(self.nhdr['Rows'],self.nhdr['Columns'])
            for y in range(self.nhdr['Rows']/ydim):
                for x in range(self.nhdr['Columns']/xdim):
                    if img[y*ydim:(y+1)*ydim,x*xdim:(x+1)*xdim].sum() != 0:
                        self.mosaic_slcloc.append((x*xdim,y*ydim))
        self.nfiles = 0
        img_pos = self.nhdr['ImageOrientation']
        if img_pos is not None:
            img_pos = map(float, img_pos)
            test = array(map(abs,[img_pos[0]+img_pos[3], img_pos[1]+img_pos[4],\
                                  img_pos[2]+img_pos[5]]))
            self.slice_idx = test.argmin()
        else:
            self.slice_idx = 0

#       First scan all the files and get the data.
        self.info = {} # Directory of dicom files.


    def PatientNameTranslation(self, patname):
        """ 
        Create anonymized PatientName field. Allowable fields are:
            - [a-z,A-z]<numbers>,
            - <numbers>[a-z,A-z], or
            - sub<numbers>
        where [a-z,A-z] represents any single alphabetic character and
        <numbers> represents any positive integer.
        """
        wds = patname.split()
        newname = ""
        for wd in patname.split():
#           Check for 
            checkname = blankout_alpha(wd).replace(' ','')
            if wd.isdigit() or len(checkname) > 2 or \
              (wd.startswith('sub') and wd[3:].isdigit()) or \
              (wd[0].isalpha() and wd[1:].isdigit()) or \
              (wd[-1].isalpha() and wd[:-1].isdigit()):
#               Check for legal subfields.
                newname += '%s ' % wd.strip()
        else:
            #newname = patname.translate(self.translation_table)
            newname = translate_name(patname)
        self.pn = newname
        return newname

    def PatientBirthDateTranslate(self, birthdate):
        """
        Returns year of birth (removes month and day).
        """
        if len(birthdate) == 8:
            birthdate = birthdate[:4] + 4*' '
        else:
            birthdate = len(birthdate)*'x'
        return birthdate

    def _ScanInfo(self, fname=None, data=None, fname_format=None, \
                                                    anonymize=False):
        """
        Extract relevant info from a give slice.
        """
        if data is not None:
            dcm = Dicom(data=data)
            if fname_format:
                InstanceNumber = int(dcm.get_value('0020,0013',0))
                fullfile = (fname_format % InstanceNumber).replace(' ','')
            else:
                fullfile = None
        else:
            fullfile = ("%s/%s" % (self.dirname, fname)).replace(' ','')
            if not isdicom(fullfile):
                return
            dcm = Dicom(fullfile)

        if anonymize:
#           Anonymize patient name.
            pnlgth = dcm.pn_tag['length']
            pnoff = dcm.pn_tag['offset']
            pn = self.PatientNameTranslation(dcm.data[pnoff:pnoff+pnlgth])
            newpn = fromstring(pn, ubyte)
#            print '10 pn: __%s__, newpn: __%s__, %d, %d %d %d' % \
#                    (self.pn,newpn.tostring(),pnoff,pnlgth,newpn.size,len(pn))
            ndata = fromstring(dcm.data,ubyte)
            ndata[pnoff:pnoff+pnlgth] = newpn
            self.newpn = newpn.tostring()

#           Anonymize birthdate.
            pnlgth = dcm.pbd_tag['length']
            pnoff = dcm.pbd_tag['offset']
            self.newbd = self.PatientBirthDateTranslate(\
                                        dcm.data[pnoff:pnoff+pnlgth])
            self.newbd = fromstring(self.newbd,ubyte)
            ndata[pnoff:pnoff+pnlgth] = self.newbd
            dcm.data = ndata.tostring()
            self.newbd = self.newbd.tostring()
        else:
            dcm.data = data
        self.data = dcm.data

#        nhdr = read_ge_dicom_header(file)
#        if isinstance(dcm.hdr,dict):
        if dcm is not None:
#           Skip non-dicom files in the directory.
            InstanceNumber = int(dcm.get_value('0020,0013',0))
            self.instance = InstanceNumber
            Manufacturer = dcm.get_value('0008,0070','').strip()      # tmp
            ImageFormat = dcm.get_value('0008,0008','')      # tmp
            Modality = dcm.get_value('0008,0060','Fail').strip()
            if Modality == 'Fail':
                sys.stderr.write('ScanDicomFiles: Invalid dicom file: %s\n'%fullfile)
                return None
            if Manufacturer.startswith('GE MEDICAL') or \
                    Manufacturer == 'GEMS':
                GEImageType = dcm.get_value('0043,102f')
                if GEImageType is not None:
                    ImageType = GEImageType
                else:
#                   If GE doesn't supply their own key, assume it \
#                   is alway magnitude.
                    ImageType = 'Magnitude'

                AcqTime = int(100*float(dcm.get_value('0008,0032', default=0)))
                self.mosaic = False
            elif Manufacturer == 'SIEMENS':
                if 'MOSAIC' in ImageFormat[-1]:
                    self.mosaic = True
                else:
                    self.mosaic = False
                ImageType = dcm.get_value('0008,0008', '')[2]
                ImageType = siemens_type_to_idx.get(ImageType, 0)
                AcqTime = int(100*float(dcm.get_value('0008,0032')))
            elif self.nhdr['Manufacturer'].replace(' ','').lower() == \
                                            'philipsmedicalsystems':
                ImageType = dcm.get_value('0008,0008', '')[2]
                ImageType =  phillips_type_to_idx.get( \
                                [self.nhdr['ImageType'][2]],'Magnitude')
                TemporalPosition = int(dcm.get_value('0020,0100'))
                AcqTime = TemporalPosition
                self.mosaic = False
            else: # Hope that Siemens encoding works for Phillips etc. \
#                   It won't work for GE.
                ImageType = dcm.get_value('0008,0008', '')[2]
                ImageType = siemens_type_to_idx[ImageType]
                AcqTime = int(100*float(dcm.get_value('0008,0032')))
                self.mosaic = False

            ImagePosition = dcm.get_value('0020,0032', default=[0.,0.,0.])
            AcquisitionNumber = dcm.get_value('0020,0012') # tmp
            SeriesNumber = dcm.get_value('0020,0011')
            SpacingBetweenSlices = dcm.get_value('0018,0088')
            start_image = dcm.get_value('StartImage')
            EchoTime = dcm.get_value('0018,0081', default=0)
            t_inst = AcqTime*1000 + InstanceNumber
            self.nfiles += 1
            key = "%05d_%013d_%s" % (int(10*EchoTime), t_inst, ImageType)
            self.info[key] = (os.path.basename(fullfile), AcqTime, \
                    ImagePosition[self.slice_idx], ImageType, EchoTime, \
                    t_inst, start_image)
            return fullfile



    def _ScanProcess(self):
        """
        Process information obtained by reading all slices.
        """
#       Determine sort direction along slice axis.
        image_orientation = array(self.get_value('0020,0037',\
                            default=[1.,0.,0.,0.,1.,0.])).\
                                    round().astype(int).reshape([2,3])
        test = dot(abs(image_orientation), array([1., 2., 4.])).sum()
        if abs(test-3.) < .001:
#           Axial view. Sort in order of increasing slice location. (I->S)
            self.flip_slice_order = False
        elif abs(test-5.) < .001:
#           Coronal view. Sort in order of increasing slice location. (A->P)
            self.flip_slice_order = False
        elif abs(test-6.) < .001:
#           Sagittal view. Sort in order of decreasing slice location. (L->R)
            self.flip_slice_order = True
            

#       Find unique values.
        unique_pos = {}
        unique_type = {}
        unique_tes = {}
        for inst in self.info.keys():
            item = self.info[inst]
            if not unique_pos.has_key(item[2]):
                unique_pos[item[2]] = inst
            if not unique_type.has_key(item[3]):
                unique_type[item[3]] = inst
            if not unique_tes.has_key(item[4]):
                unique_tes[item[4]] = item[-2]

#       Sort and get dimensions
        unique_z = unique_pos.keys()
        unique_z.sort()
        if self.flip_slice_order:
#           Flip sort order so sagittals are in ASL coordinates.
            unique_z.reverse()
        unique_typ = unique_type.keys()
        unique_typ.sort()

#       Return Echo Times in order acquired.
   #     tmp = {}
   #     for key in unique_tes.keys():
   #         tmp[unique_tes[key]] = key
   #     keys = tmp.keys()
   #     keys.sort()
   #     EchoTimes = []
   #     for key in keys:
   #         EchoTimes.append(tmp[key])

#       Images are sorted by low -> high echo time.
        EchoTimes = unique_tes.keys()
        EchoTimes.sort()

        unique_t_inst = self.info.keys()
        unique_t_inst.sort()

        mdim = len(unique_typ)
        zdim = len(unique_z)
        tdim = len(unique_t_inst)/zdim/mdim
        if tdim == 0:
            tdim = 1
        if float(self.nfiles) % float(zdim) and self.filename:
            if self.nhdr['PulseSequenceName'].lower().strip() == '3-plane' or \
               'tfi2d1' in self.nhdr['PulseSequenceName'].lower().strip():
                mdim = 1
                tdim = 1
                zdim = len(unique_t_inst)
            else:
                raise RuntimeError(\
                'Missing slice(s): Number of slices acquired is not evenly\n' \
                '\t\tdivisible by the number of slices per frame. ***\n' + \
                '\tDicom directory: %s\n' % self.filename + \
                '\tNumber of slices acquired: %d\n' % len(unique_t_inst) + \
                '\tNumber of slices per frame: %d\n' % zdim + \
                '\tNumber of image types per series: %d\n' % mdim)
            

#       Find starting and ending slice locations.
        zarray = array(unique_z)
        zmin = zarray.min()
        zmax = zarray.max()

#       Create an entry for each file specifying its position in image array.
        self.dicominfo = {}
        times = zeros([mdim, zdim], integer)
        for inst in unique_t_inst:
#           instance keys are start with number encoded with time and instance number.
#           These keys will sort in order of ascending time for both GE and Siemens headers.
            item = self.info[inst]
            z = unique_z.index(item[2])
            m = unique_typ.index(item[3]) #* mdim*EchoTimes.index(item[4])
            t = int(times[m, z])
            times[m, z] = t + 1
            if self.mosaic:
                key = '%d_%d' % (m, t)
            else:
                key = '%d_%d_%d' % (m, t, z)
#            self.dicominfo[key] = [item[0], z, t, m, start_image]
            self.dicominfo[key] = [item[0], item[6]]
#            if z == 0:
#                print key, self.dicominfo[key]
        
        self.dicominfo['dims'] = {\
                'StartLoc':zmin, \
                'EndLoc':zmax, \
                'zdim':zdim,  \
                'tdim':tdim, \
                'TypeDim':mdim, \
                'dirname':self.dirname, \
                'EchoTimes':EchoTimes}

    def _ScanDicomFiles(self, anonymize=False):
        """
        Create a directory specifying the name, time, type and position of 
        each slice.
        """

#       Initialize scanning process.
        self._ScanInit()

#       Retrieve info from each file.
        files = os.listdir(self.dirname)
        for fname in files:
            self._ScanInfo(fname, anonymize=anonymize)

        self._ScanProcess()
        return (self.dicominfo)

class ScanDicomSlices(Dicom):
    def __init__(self, data):
        Dicom.__init__(self, data=data)
        self.get_native_header()
        self.dirname = '.'
#        self.dcm = Dicom(data=slice)
        self._ScanInit()

    def NextSlice(self, data, fname_format=None, anonymize=False):
        """
        Add another slice to the dicominfo catalog.
        """
        full_fname = self._ScanInfo(data=data, fname_format=fname_format, \
                                               anonymize=anonymize)
        return full_fname

    def Process(self):
        self._ScanProcess()
        return (self.dicominfo)

    def get_scanned_nhdr(self):
        self.get_native_header(self, scanned=True)
        return self.nhdr

#*************************************************************************
def dicom_to_rot44(ImageOrientation, image_position, xsize, ysize, zsize, \
                            xdim, ydim, zdim, flip_slice_order=False):
#*************************************************************************
    """
    Purpose: 
        Convert dicom header variables to a 4x4 transform matrix.
    Arguments:
        ImageOrientation: Value for image orientation key (0x020,0x0037)
        image_position: Value for image position key (0x0020,0x0032)
        xsize, ysize, zsize: Voxel size.
        xdim, ydim, zdim: Image dimensions.
        flip_slice_order: Direction of slice axis sort. The default action of
            this package is to sort the slice axis in the I->S, R->L and A->P 
            directions. If flip_slice_order is True, these orders will be 
            reversed. This is useful for sagittal images, because the default
            action would yield images in the ASR orientation. Setting 
            flip_slice_order to True selects the standard ASL orientation. This
            maintains compatibility with software that ignores orientation
            information in the header.
    Returns:
        4x4 transformation matrix.
    """

    R = zeros([4, 4], float)

#   First two columns are given in dicom header. The third is +/- the 
#   cross-product of the first two.  The sign is determined by the ordering 
#   of the slices as formatted in "read_ge_dicom" in dicom.py
#   ImageOrientation defines the rotation from LAI coordinates to 
#   image coordinates.
    R[0,:3] = ImageOrientation[:3]
    R[1,:3] = ImageOrientation[3:]
    if flip_slice_order:
        R[2,:3] = -abs(cross(R[0,:3],R[1,:3]))
    else:
        R[2,:3] =  abs(cross(R[0,:3],R[1,:3]))

    R = R.transpose()  # Invert to get rotation from image to RAI
    R[3, 3] = 1.
    Rsize = dot(abs(R[:3,:3]), array([xsize, ysize, zsize]))

    R[:3, 3] = image_position

    return(R, Rsize)


#**************
def get_dict():
#**************
    """
     Purpose: Return the entire dicom dictionary.
    """


# The following code is automatically generated by merge_dic.py 
    return {'0000,0000': ('UL' 'Group0000Length'), \
'0000,0001': ('UL', 'Group0000LengthToEnd'), \
'0000,0002': ('UI', 'AffectedSopClassUid'), \
'0000,0003': ('UI', 'RequestedSopClassUid'), \
'0000,0010': ('SH', 'RecognitionCode'), \
'0000,0100': ('US', 'CommandField'), \
'0000,0110': ('US', 'MessageId'), \
'0000,0120': ('US', 'MessageIdBeingRespondedTo'), \
'0000,0200': ('AE', 'Initiator'), \
'0000,0300': ('AE', 'Receiver'), \
'0000,0400': ('AE', 'FindLocation'), \
'0000,0600': ('AE', 'MoveDestination'), \
'0000,0700': ('US', 'Priority'), \
'0000,0800': ('US', 'DataSetType'), \
'0000,0850': ('US', 'NumberOfMatches'), \
'0000,0860': ('US', 'ResponseSequenceNumber'), \
'0000,0900': ('US', 'Status'), \
'0000,0901': ('AT', 'OffendingElement'), \
'0000,0902': ('LO', 'ErrorComment'), \
'0000,0903': ('US', 'ErrorId'), \
'0000,1000': ('UI', 'AffectedSopInstanceUid'), \
'0000,1001': ('UI', 'RequestedSopInstanceUid'), \
'0000,1002': ('US', 'EventTypeId'), \
'0000,1005': ('AT', 'AttributeIdentifierList'), \
'0000,1008': ('US', 'ActionTypeId'), \
'0000,1012': ('UI', 'RequestedSopInstanceUidList'), \
'0000,1020': ('US', 'NumberOfRemainingSuboperations'), \
'0000,1021': ('US', 'NumberOfCompletedSuboperations'), \
'0000,1022': ('US', 'NumberOfFailedSuboperations'), \
'0000,1023': ('US', 'NumberOfWarningSuboperations'), \
'0000,1030': ('AE', 'MoveOriginatorApplicationEntityTitle'), \
'0000,1031': ('US', 'MoveOriginatorMessageId'), \
'0000,5010': ('LO', 'MessageSetId'), \
'0000,5020': ('LO', 'EndMessageSetId'), \
'0002,0000': ('UL', 'FileMetaInformationGroupLength'), \
'0002,0001': ('OB', 'FileMetaInformationVersion'), \
'0002,0002': ('UI', 'MediaStorageSopClassUid'), \
'0002,0003': ('UI', 'MediaStorageSopInstanceUid'), \
'0002,0010': ('UI', 'TransferSyntaxUid'), \
'0002,0012': ('UI', 'ImplementationClassUid'), \
'0002,0013': ('SH', 'ImplementationVersionName'), \
'0002,0016': ('AE', 'SourceApplicationEntityTitle'), \
'0002,0100': ('UI', 'PrivateInformationCreatorUid'), \
'0002,0102': ('OB', 'PrivateInformation'), \
'0004,0000': ('UL', 'Group0004Length'), \
'0004,1130': ('CS', 'FilesetId'), \
'0004,1141': ('CS', 'FilesetDescriptorFileFileId'), \
'0004,1142': ('CS', 'FilesetDescriptorFileFormat'), \
'0004,1200': ('UL', 'RootDirectoryEntitysFirstDirectoryRecordOffset'), \
'0004,1202': ('UL', 'RootDirectoryEntitysLastDirectoryRecordOffset'), \
'0004,1212': ('US', 'FilesetConsistenceFlag'), \
'0004,1220': ('SQ', 'DirectoryRecordSequence'), \
'0004,1400': ('UL', 'NextDirectoryRecordOffset'), \
'0004,1410': ('US', 'RecordInuseFlag'), \
'0004,1420': ('UL', 'ReferencedLowerlevelDirectoryEntityOffset'), \
'0004,1430': ('CS', 'DirectoryRecordType'), \
'0004,1432': ('UI', 'PrivateRecordUid'), \
'0004,1500': ('CS', 'ReferencedFileId'), \
'0004,1504': ('UL', 'MRDRDirectoryRecordOffset'), \
'0004,1510': ('UI', 'ReferencedSopClassUidInFile'), \
'0004,1511': ('UI', 'ReferencedSopInstanceUidInFile'), \
'0004,1512': ('UI', 'ReferencedTransferSyntaxUIDinFile'), \
'0004,1600': ('UL', 'NumberOfReferences'), \
'0008,0000': ('UL', 'Group0008Length'), \
'0008,0001': ('UL', 'Group0008LengthToEnd'), \
'0008,0005': ('CS', 'SpecificCharacterSet'), \
'0008,0008': ('CS', 'ImageType'), \
'0008,0010': ('SH', 'RecognitionCode'), \
'0008,0012': ('DA', 'InstanceCreationDate'), \
'0008,0013': ('TM', 'InstanceCreationTime'), \
'0008,0014': ('UI', 'InstanceCreatorUid'), \
'0008,0016': ('UI', 'SopClassUid'), \
'0008,0018': ('UI', 'SopInstanceUid'), \
'0008,0020': ('DA', 'StudyDate'), \
'0008,0021': ('DA', 'SeriesDate'), \
'0008,0022': ('DA', 'AcquisitionDate'), \
'0008,0023': ('DA', 'ContentDate'), \
'0008,0024': ('DA', 'OverlayDate'), \
'0008,0025': ('DA', 'CurveDate'), \
'0008,002a': ('DT', 'AcquisitionDatetime'), \
'0008,0030': ('TM', 'StudyTime'), \
'0008,0031': ('TM', 'SeriesTime'), \
'0008,0032': ('TM', 'AcquisitionTime'), \
'0008,0033': ('TM', 'ContentTime'), \
'0008,0034': ('TM', 'OverlayTime'), \
'0008,0035': ('TM', 'CurveTime'), \
'0008,0040': ('US', 'DataSetType'), \
'0008,0041': ('SH', 'DataSetSubtype'), \
'0008,0042': ('CS', 'NuclearMedicineSeriesType'), \
'0008,0050': ('SH', 'AccessionNumber'), \
'0008,0052': ('CS', 'Query/retrieveLevel'), \
'0008,0054': ('AE', 'RetrieveAeTitle'), \
'0008,0056': ('CS', 'InstanceAvailability'), \
'0008,0058': ('AE', 'FailedSopInstanceUidList'), \
'0008,0060': ('CS', 'Modality'), \
'0008,0061': ('CS', 'ModalitiesinStudy'), \
'0008,0064': ('CS', 'ConversionType'), \
'0008,0068': ('CS', 'PresentationIntentType'), \
'0008,0070': ('LO', 'Manufacturer'), \
'0008,0080': ('LO', 'InstitutionName'), \
'0008,0081': ('ST', 'InstitutionAddress'), \
'0008,0082': ('SQ', 'InstitutionCodeSequence'), \
'0008,0090': ('PN', 'ReferringPhysicianName'), \
'0008,0092': ('ST', 'ReferringPhysicianAddress'), \
'0008,0094': ('SH', 'ReferringPhysicianTelephoneNumbers'), \
'0008,0100': ('SH', 'CodeValue'), \
'0008,0102': ('SH', 'CodingSchemeDesignator'), \
'0008,0103': ('SH', 'CodingSchemeVersion'), \
'0008,0104': ('LO', 'CodeMeaning'), \
'0008,0105': ('CS', 'MappingResource'), \
'0008,0106': ('DT', 'ContextGroupVersion'), \
'0008,0107': ('DT', 'ContextGroupLocalVersion'), \
'0008,010b': ('CS', 'CodeSetExtensionFlag'), \
'0008,010c': ('UI', 'PrivateCodingSchemeCreatorUID'), \
'0008,010d': ('UI', 'CodeSetExtensionCreatorUID'), \
'0008,010f': ('CS', 'ContextIdentifier'), \
'0008,0201': ('SH', 'TimezoneOffsetFromUTC'), \
'0008,1000': ('SH', 'NetworkId'), \
'0008,1010': ('SH', 'StationName'), \
'0008,1030': ('LO', 'StudyDescription'), \
'0008,1032': ('SQ', 'ProcedureCodeSequence'), \
'0008,103e': ('LO', 'SeriesDescription'), \
'0008,1040': ('LO', 'InstitutionalDepartmentName'), \
'0008,1048': ('PN', 'PhysiciansofRecord'), \
'0008,1050': ('PN', 'AttendingPhysicianName'), \
'0008,1060': ('PN', 'NameOfPhysicianReadingStudy'), \
'0008,1070': ('PN', 'OperatorName'), \
'0008,1080': ('LO', 'AdmittingDiagnosesDescription'), \
'0008,1084': ('SQ', 'AdmittingDiagnosisCodeSequence'), \
'0008,1090': ('LO', 'ManufacturerModelName'), \
'0008,1100': ('SQ', 'ReferencedResultsSequence'), \
'0008,1110': ('SQ', 'ReferencedStudySequence'), \
'0008,1111': ('SQ', 'ReferencedStudyComponentSequence'), \
'0008,1115': ('SQ', 'ReferencedSeriesSequence'), \
'0008,1120': ('SQ', 'ReferencedPatientSequence'), \
'0008,1125': ('SQ', 'ReferencedVisitSequence'), \
'0008,1130': ('SQ', 'ReferencedOverlaySequence'), \
'0008,113a': ('SQ', 'ReferencedWaveformSequence'), \
'0008,1140': ('SQ', 'ReferencedImageSequence'), \
'0008,1145': ('SQ', 'ReferencedCurveSequence'), \
'0008,114a': ('SQ', 'ReferencedInstanceSequence'), \
'0008,1150': ('UI', 'ReferencedSopClassUid'), \
'0008,1155': ('UI', 'ReferencedSopInstanceUid'), \
'0008,115a': ('UI', 'SOPClassesSupported'), \
'0008,1160': ('IS', 'ReferencedFrameNumber'), \
'0008,1195': ('UI', 'TransactionUID'), \
'0008,1197': ('US', 'FailureReason'), \
'0008,1198': ('SQ', 'FailedSOPSequence'), \
'0008,1199': ('SQ', 'ReferencedSOPSequence'), \
'0008,2111': ('ST', 'DerivationDescription'), \
'0008,2112': ('SQ', 'SourceImageSequence'), \
'0008,2120': ('SH', 'StageName'), \
'0008,2122': ('IS', 'StageNumber'), \
'0008,2124': ('IS', 'NumberOfStages'), \
'0008,2127': ('SH', 'ViewName'), \
'0008,2128': ('IS', 'ViewNumber'), \
'0008,2129': ('IS', 'NumberOfEventTimers'), \
'0008,212a': ('IS', 'NumberOfViewsInStage'), \
'0008,2130': ('DS', 'EventElapsedTime'), \
'0008,2132': ('LO', 'EventTimerName'), \
'0008,2142': ('IS', 'StartTrim'), \
'0008,2143': ('IS', 'StopTrim'), \
'0008,2144': ('IS', 'RecommendedDisplayFrameRate'), \
'0008,2200': ('CS', 'TransducerPosition'), \
'0008,2204': ('CS', 'TransducerOrientation'), \
'0008,2208': ('CS', 'AnatomicStructure'), \
'0008,2218': ('SQ', 'AnatomicRegionSequence'), \
'0008,2220': ('SQ', 'AnatomicRegionModifierSequence'), \
'0008,2228': ('SQ', 'PrimaryAnatomicStructureSequence'), \
'0008,2229': ('SQ', 'AnatomicStructureSpaceorRegionSequence'), \
'0008,2230': ('SQ', 'PrimaryAnatomicStructureModifierSequence'), \
'0008,2240': ('SQ', 'TransducerPositionSequence'), \
'0008,2242': ('SQ', 'TransducerPositionModifierSequence'), \
'0008,2244': ('SQ', 'TransducerOrientationSequence'), \
'0008,2246': ('SQ', 'TransducerOrientationModifierSequence'), \
'0008,4000': ('SH', 'Group0008Comments'), \
'0009,0000': ('UL', 'GroupLength'), \
'0009,0010': ('LO', 'Privatecreator'), \
'0009,1002': ('SH', 'SuiteId'), \
'0009,1004': ('SH', 'ProductId'), \
'0009,1027': ('SL', 'ImageActualDate'), \
'0009,1030': ('SH', 'ServiceId'), \
'0009,1031': ('SH', 'MobileLocationNumber'), \
'0009,10e3': ('UI', 'EquipmentUid'), \
'0009,10e7': ('UL', 'ExamRecordChecksum'), \
'0009,10e9': ('SL', 'ActualSeriesDataTimeStamp'), \
'0010,0000': ('UL', 'Group0010Length'), \
'0010,0010': ('PN', 'PatientName'), \
'0010,0020': ('LO', 'PatientId'), \
'0010,0021': ('LO', 'IssuerOfPatientId'), \
'0010,0030': ('DA', 'PatientBirthDate'), \
'0010,0032': ('TM', 'PatientBirthTime'), \
'0010,0040': ('CS', 'PatientSex'), \
'0010,0042': ('SH', 'PatientSocialSecurityNumber'), \
'0010,0050': ('SQ', 'PatientInsurancePlanCodeSequence'), \
'0010,0101': ('SQ', 'PatientsPrimaryLanguageCodeSequence'), \
'0010,0102': ('SQ', 'PatientsPrimaryLanguageCodeModifierSequence'), \
'0010,1000': ('LO', 'OtherPatientIds'), \
'0010,1001': ('PN', 'OtherPatientNames'), \
'0010,1005': ('PN', 'PatientMaidenName'), \
'0010,1010': ('AS', 'PatientAge'), \
'0010,1020': ('DS', 'PatientSize'), \
'0010,1030': ('DS', 'PatientWeight'), \
'0010,1040': ('LO', 'PatientAddress'), \
'0010,1050': ('SH', 'InsurancePlanIdentification'), \
'0010,1060': ('PN', 'PatientMothersMaidenName'), \
'0010,1080': ('LO', 'MilitaryRank'), \
'0010,1081': ('LO', 'BranchOfService'), \
'0010,1090': ('LO', 'MedicalRecordLocator'), \
'0010,2000': ('LO', 'MedicalAlerts'), \
'0010,2110': ('LO', 'ContrastAllergies'), \
'0010,2150': ('LO', 'CountryOfResidence'), \
'0010,2152': ('LO', 'RegionOfResidence'), \
'0010,2154': ('SH', 'PatientTelephoneNumbers'), \
'0010,2160': ('SH', 'EthnicGroup'), \
'0010,2180': ('SH', 'Occupation'), \
'0010,21a0': ('CS', 'SmokingStatus'), \
'0010,21b0': ('LT', 'AdditionalPatientHistory'), \
'0010,21c0': ('US', 'PregnancyStatus'), \
'0010,21d0': ('DA', 'LastMenstrualDate'), \
'0010,21f0': ('LO', 'PatientReligiousPreference'), \
'0010,4000': ('LT', 'PatientComments'), \
'0018,0000': ('UL', 'Group0018Length'), \
'0018,0010': ('LO', 'Contrast/bolusAgent'), \
'0018,0012': ('SQ', 'ContrastBolusAgentSequence'), \
'0018,0014': ('SQ', 'ContrastBolusAdministrationRouteSequence'), \
'0018,0015': ('CS', 'BodyPartExamined'), \
'0018,0020': ('CS', 'ScanningSequence'), \
'0018,0021': ('CS', 'SequenceVariant'), \
'0018,0022': ('CS', 'ScanOptions'), \
'0018,0023': ('CS', 'MrAcquisitionType'), \
'0018,0024': ('SH', 'SequenceName'), \
'0018,0025': ('CS', 'AngioFlag'), \
'0018,0026': ('SQ', 'InterventionDrugInformationSequence'), \
'0018,0027': ('TM', 'InterventionDrugStopTime'), \
'0018,0028': ('DS', 'InterventionDrugDose'), \
'0018,0029': ('SQ', 'InterventionDrugCodeSequence'), \
'0018,002a': ('SQ', 'AdditionalDrugSequence'), \
'0018,0030': ('LO', 'Radionuclide'), \
'0018,0031': ('LO', 'Radiopharmaceutical'), \
'0018,0032': ('DS', 'EnergyWindowCenterline'), \
'0018,0033': ('DS', 'EnergyWindowTotalWidth'), \
'0018,0034': ('LO', 'InterventionDrugName'), \
'0018,0035': ('TM', 'InterventionDrugStartTime'), \
'0018,0036': ('SQ', 'InterventionalTherapySequence'), \
'0018,0037': ('CS', 'TherapyType'), \
'0018,0038': ('CS', 'InterventionalStatus'), \
'0018,0039': ('CS', 'TherapyDescription'), \
'0018,0040': ('IS', 'CineRate'), \
'0018,0050': ('DS', 'SliceThickness'), \
'0018,0060': ('DS', 'Kvp'), \
'0018,0070': ('IS', 'CountsAccumulated'), \
'0018,0071': ('CS', 'AcquisitionTerminationCondition'), \
'0018,0072': ('DS', 'EffectiveSeriesDuration'), \
'0018,0073': ('CS', 'AcquisitionStartCondition'), \
'0018,0074': ('IS', 'AcquisitionStartConditionData'), \
'0018,0075': ('IS', 'AcquisitionTerminationConditionData'), \
'0018,0080': ('DS', 'RepetitionTime'), \
'0018,0081': ('DS', 'EchoTime'), \
'0018,0082': ('DS', 'InversionTime'), \
'0018,0083': ('DS', 'NumberOfAverages'), \
'0018,0084': ('DS', 'ImagingFrequency'), \
'0018,0085': ('SH', 'ImagedNucleus'), \
'0018,0086': ('IS', 'EchoNumber'), \
'0018,0087': ('DS', 'MagneticFieldStrength'), \
'0018,0088': ('DS', 'SpacingBetweenSlices'), \
'0018,0089': ('IS', 'NumberOfPhaseEncodingSteps'), \
'0018,0090': ('DS', 'DataCollectionDiameter'), \
'0018,0091': ('IS', 'EchoTrainLength'), \
'0018,0093': ('DS', 'PercentSampling'), \
'0018,0094': ('DS', 'PercentPhaseFieldOfView'), \
'0018,0095': ('DS', 'PixelBandwidth'), \
'0018,1000': ('LO', 'DeviceSerialNumber'), \
'0018,1004': ('LO', 'PlateId'), \
'0018,1010': ('LO', 'SecondaryCaptureDeviceId'), \
'0018,1011': ('LO', 'HardcopyCreationDeviceID'), \
'0018,1012': ('DA', 'DateOfSecondaryCapture'), \
'0018,1014': ('TM', 'TimeOfSecondaryCapture'), \
'0018,1016': ('LO', 'SecondaryCaptureDeviceManufacturer'), \
'0018,1017': ('LO', 'HardcopyDeviceManufacturer'), \
'0018,1018': ('LO', 'SecondaryCaptureDeviceManufacturerModelName'), \
'0018,1019': ('LO', 'SecondaryCaptureDeviceSoftwareVersion'), \
'0018,101a': ('LO', 'HardcopyDeviceSoftwareVersion'), \
'0018,101b': ('LO', 'HardcopyDeviceManfuacturersModelName'), \
'0018,1020': ('LO', 'SoftwareVersion'), \
'0018,1022': ('SH', 'VideoImageFormatAcquired'), \
'0018,1023': ('LO', 'DigitalImageFormatAcquired'), \
'0018,1030': ('LO', 'ProtocolName'), \
'0018,1040': ('LO', 'Contrast/bolusRoute'), \
'0018,1041': ('DS', 'Contrast/bolusVolume'), \
'0018,1042': ('TM', 'Contrast/bolusStartTime'), \
'0018,1043': ('TM', 'Contrast/bolusStopTime'), \
'0018,1044': ('DS', 'Contrast/bolusTotalDose'), \
'0018,1045': ('IS', 'SyringeCounts'), \
'0018,1046': ('DS', 'ContrastFlowRates'), \
'0018,1047': ('DS', 'ContrastFlowDurations'), \
'0018,1048': ('CS', 'ContrastBolusIngredient'), \
'0018,1049': ('DS', 'ContrastBolusIngredientConcentration'), \
'0018,1050': ('DS', 'SpatialResolution'), \
'0018,1060': ('DS', 'TriggerTime'), \
'0018,1061': ('LO', 'TriggerSourceOrType'), \
'0018,1062': ('IS', 'NominalInterval'), \
'0018,1063': ('DS', 'FrameTime'), \
'0018,1064': ('LO', 'FramingType'), \
'0018,1065': ('DS', 'FrameTimeVector'), \
'0018,1066': ('DS', 'FrameDelay'), \
'0018,1067': ('DS', 'ImageTriggerDelay'), \
'0018,1068': ('DS', 'MultiplexGroupTimeOffset'), \
'0018,1069': ('DS', 'TriggerTimeOffset'), \
'0018,106a': ('CS', 'SynchronizationTrigger'), \
'0018,106c': ('US', 'SynchronizationChannel'), \
'0018,106e': ('UL', 'TriggerSamplePosition'), \
'0018,1070': ('LO', 'RadionuclideRoute'), \
'0018,1071': ('DS', 'RadionuclideVolume'), \
'0018,1072': ('TM', 'RadionuclideStartTime'), \
'0018,1073': ('TM', 'RadionuclideStopTime'), \
'0018,1074': ('DS', 'RadionuclideTotalDose'), \
'0018,1075': ('DS', 'RadionuclideHalfLife'), \
'0018,1076': ('DS', 'RadionuclidePositronFraction'), \
'0018,1077': ('DS', 'RadiopharmaceuticalSpecificActivity'), \
'0018,1080': ('CS', 'BeatRejectionFlag'), \
'0018,1081': ('IS', 'LowRrValue'), \
'0018,1082': ('IS', 'HighRrValue'), \
'0018,1083': ('IS', 'IntervalsAcquired'), \
'0018,1084': ('IS', 'IntervalsRejected'), \
'0018,1085': ('LO', 'PvcRejection'), \
'0018,1086': ('IS', 'SkipBeats'), \
'0018,1088': ('IS', 'HeartRate'), \
'0018,1090': ('IS', 'CardiacNumberOfImages'), \
'0018,1094': ('IS', 'TriggerWindow'), \
'0018,1100': ('DS', 'ReconstructionDiameter'), \
'0018,1110': ('DS', 'DistanceSourceToDetector'), \
'0018,1111': ('DS', 'DistanceSourceToPatient'), \
'0018,1114': ('DS', 'EstimatedRadiographicMagnificationFactor'), \
'0018,1120': ('DS', 'Gantry/detectorTilt'), \
'0018,1121': ('DS', 'GantryDetectorSlew'), \
'0018,1130': ('DS', 'TableHeight'), \
'0018,1131': ('DS', 'TableTraverse'), \
'0018,1134': ('CS', 'TableMotion'), \
'0018,1135': ('DS', 'TableVerticalIncrement'), \
'0018,1136': ('DS', 'TableLateralIncrement'), \
'0018,1137': ('DS', 'TableLongitudinalIncrement'), \
'0018,1138': ('DS', 'TableAngle'), \
'0018,113a': ('CS', 'TableType'), \
'0018,1140': ('CS', 'RotationDirection'), \
'0018,1141': ('DS', 'AngularPosition'), \
'0018,1142': ('DS', 'RadialPosition'), \
'0018,1143': ('DS', 'ScanArc'), \
'0018,1144': ('DS', 'AngularStep'), \
'0018,1145': ('DS', 'CenterOfRotationOffset'), \
'0018,1146': ('DS', 'RotationOffset'), \
'0018,1147': ('CS', 'FieldOfViewShape'), \
'0018,1149': ('IS', 'FieldOfViewDimensions'), \
'0018,1150': ('IS', 'ExposureTime'), \
'0018,1151': ('IS', 'XrayTubeCurrent'), \
'0018,1152': ('IS', 'Exposure'), \
'0018,1153': ('IS', 'ExposureinuAs'), \
'0018,1154': ('DS', 'AveragePulseWidth'), \
'0018,1155': ('CS', 'RadiationSetting'), \
'0018,1156': ('CS', 'RectificationType'), \
'0018,115a': ('CS', 'RadiationMode'), \
'0018,115e': ('DS', 'ImageAreaDoseProduct'), \
'0018,1160': ('SH', 'FilterType'), \
'0018,1161': ('LO', 'TypeofFilters'), \
'0018,1162': ('DS', 'IntensifierSize'), \
'0018,1164': ('DS', 'ImagerPixelSpacing'), \
'0018,1166': ('CS', 'Grid'), \
'0018,1170': ('IS', 'GeneratorPower'), \
'0018,1180': ('SH', 'Collimator/gridName'), \
'0018,1181': ('CS', 'CollimatorType'), \
'0018,1182': ('IS', 'FocalDistance'), \
'0018,1183': ('DS', 'XFocusCenter'), \
'0018,1184': ('DS', 'YFocusCenter'), \
'0018,1190': ('DS', 'FocalSpot'), \
'0018,1191': ('CS', 'AnodeTargetMaterial'), \
'0018,11a0': ('DS', 'BodyPartThickness'), \
'0018,11a2': ('DS', 'CompressionForce'), \
'0018,1200': ('DA', 'DateOfLastCalibration'), \
'0018,1201': ('TM', 'TimeOfLastCalibration'), \
'0018,1210': ('SH', 'ConvolutionKernel'), \
'0018,1240': ('DS', 'Upper/lowerPixelValues'), \
'0018,1242': ('IS', 'ActualFrameDuration'), \
'0018,1243': ('IS', 'CountRate'), \
'0018,1244': ('US', 'PreferredPlaybackSequencing'), \
'0018,1250': ('SH', 'ReceivingCoil'), \
'0018,1251': ('SH', 'TransmitCoilName'), \
'0018,1260': ('SH', 'PlateType'), \
'0018,1261': ('LO', 'PhosphorType'), \
'0018,1300': ('IS', 'ScanVelocity'), \
'0018,1301': ('CS', 'WholeBodyTechnique'), \
'0018,1302': ('IS', 'ScanLength'), \
'0018,1310': ('US', 'AcquisitionMatrix'), \
'0018,1312': ('CS', 'InplanePhaseEncodingDirection'), \
'0018,1314': ('DS', 'FlipAngle'), \
'0018,1315': ('CS', 'VariableFlipAngleFlag'), \
'0018,1316': ('DS', 'Sar'), \
'0018,1318': ('DS', 'Db/dt'), \
'0018,1400': ('LO', 'AcquisitionDeviceProcessingDescription'), \
'0018,1401': ('LO', 'AcquisitionDeviceProcessingCode'), \
'0018,1402': ('CS', 'CassetteOrientation'), \
'0018,1403': ('CS', 'CassetteSize'), \
'0018,1404': ('US', 'ExposuresOnPlate'), \
'0018,1405': ('IS', 'RelativeXrayExposure'), \
'0018,1450': ('CS', 'ColumnAngulation'), \
'0018,1460': ('DS', 'TomoLayerHeight'), \
'0018,1470': ('DS', 'TomoAngle'), \
'0018,1480': ('DS', 'TomoTime'), \
'0018,1490': ('CS', 'TomoType'), \
'0018,1491': ('CS', 'TomoClass'), \
'0018,1495': ('IS', 'NumberofTomosynthesisSourceImages'), \
'0018,1500': ('CS', 'PositionerMotion'), \
'0018,1508': ('CS', 'PositionerType'), \
'0018,1510': ('DS', 'PositionerPrimaryAngle'), \
'0018,1511': ('DS', 'PositionerSecondaryAngle'), \
'0018,1520': ('DS', 'PositionerPrimaryAngleIncrement'), \
'0018,1521': ('DS', 'PositionerSecondaryAngleIncrement'), \
'0018,1530': ('DS', 'DetectorPrimaryAngle'), \
'0018,1531': ('DS', 'DetectorSecondaryAngle'), \
'0018,1600': ('CS', 'ShutterShape'), \
'0018,1602': ('IS', 'ShutterLeftVerticalEdge'), \
'0018,1604': ('IS', 'ShutterRightVerticalEdge'), \
'0018,1606': ('IS', 'ShutterUpperHorizontalEdge'), \
'0018,1608': ('IS', 'ShutterLowerHorizontalEdge'), \
'0018,1610': ('IS', 'CenterofCircularShutter'), \
'0018,1612': ('IS', 'RadiusofCircularShutter'), \
'0018,1620': ('IS', 'VerticesofthePolygonalShutter'), \
'0018,1622': ('US', 'ShutterPresentationValue'), \
'0018,1623': ('US', 'ShutterOverlayGroup'), \
'0018,1628': ('FD', 'ReferencePixelPhysicalValueX'), \
'0018,1700': ('CS', 'CollimatorShape'), \
'0018,1702': ('IS', 'CollimatorLeftVerticalEdge'), \
'0018,1704': ('IS', 'CollimatorRightVerticalEdge'), \
'0018,1706': ('IS', 'CollimatorUpperHorizontalEdge'), \
'0018,1708': ('IS', 'CollimatorLowerHorizontalEdge'), \
'0018,1710': ('IS', 'CenterofCircularCollimator'), \
'0018,1712': ('IS', 'RadiusofCircularCollimator'), \
'0018,1720': ('IS', 'VerticesofthePolygonalCollimator'), \
'0018,1800': ('CS', 'AcquisitionTimeSynchronized'), \
'0018,1801': ('SH', 'TimeSource'), \
'0018,1802': ('CS', 'TimeDistributionProtocol'), \
'0018,2001': ('IS', 'PageNumberVector'), \
'0018,2002': ('SH', 'FrameLabelVector'), \
'0018,2003': ('DS', 'FramePrimaryAngleVector'), \
'0018,2004': ('DS', 'FrameSecondaryAngleVector'), \
'0018,2005': ('DS', 'SliceLocationVector'), \
'0018,2006': ('SH', 'DisplayWindowLabelVector'), \
'0018,2010': ('DS', 'NominalScannedPixelSpacing'), \
'0018,2020': ('CS', 'DigitizingDeviceTransportDirection'), \
'0018,2030': ('DS', 'RotationofScannedFilm'), \
'0018,3100': ('CS', 'IVUSAcquisition'), \
'0018,3101': ('DS', 'IVUSPullbackRate'), \
'0018,3102': ('DS', 'IVUSGatedRate'), \
'0018,3103': ('IS', 'IVUSPullbackStartFrameNumber'), \
'0018,3104': ('IS', 'IVUSPullbackStopFrameNumber'), \
'0018,3105': ('IS', 'LesionNumber'), \
'0018,4000': ('SH', 'Group0018Comments'), \
'0018,5000': ('SH', 'OutputPower'), \
'0018,5010': ('LO', 'TransducerData'), \
'0018,5012': ('DS', 'FocusDepth'), \
'0018,5020': ('LO', 'PreprocessingFunction'), \
'0018,5021': ('LO', 'PostprocessingFunction'), \
'0018,5022': ('DS', 'MechanicalIndex'), \
'0018,5024': ('DS', 'ThermalIndex'), \
'0018,5026': ('DS', 'CranialThermalIndex'), \
'0018,5027': ('DS', 'SoftTissueThermalIndex'), \
'0018,5028': ('DS', 'SoftTissuefocusThermalIndex'), \
'0018,5029': ('DS', 'SoftTissuesurfaceThermalIndex'), \
'0018,5030': ('IS', 'DynamicRange'), \
'0018,5040': ('IS', 'TotalGain'), \
'0018,5050': ('IS', 'DepthOfScanField'), \
'0018,5100': ('CS', 'PatientPosition'), \
'0018,5101': ('CS', 'ViewPosition'), \
'0018,5104': ('SQ', 'ProjectionEponymousNameCodeSequence'), \
'0018,5210': ('DS', 'ImageTransformationMatrix'), \
'0018,5212': ('DS', 'ImageTranslationVector'), \
'0018,6000': ('DS', 'Sensitivity'), \
'0018,6011': ('SQ', 'SequenceOfUltrasoundRegions'), \
'0018,6012': ('US', 'RegionSpatialFormat'), \
'0018,6014': ('US', 'RegionDataType'), \
'0018,6016': ('UL', 'RegionFlags'), \
'0018,6018': ('UL', 'RegionLocationMinX0'), \
'0018,601a': ('UL', 'RegionLocationMinY0'), \
'0018,601c': ('UL', 'RegionLocationMaxX1'), \
'0018,601e': ('UL', 'RegionLocationMaxY1'), \
'0018,6020': ('SL', 'ReferencePixelX0'), \
'0018,6022': ('SL', 'ReferencePixelY0'), \
'0018,6024': ('US', 'PhysicalUnitsXDirection'), \
'0018,6026': ('US', 'PhysicalUnitsYDirection'), \
'0018,6028': ('FD', 'ReferencePixelPhysicalValueX'), \
'0018,602a': ('FD', 'ReferencePixelPhysicalValueY'), \
'0018,602c': ('FD', 'PhysicalDeltaX'), \
'0018,602e': ('FD', 'PhysicalDeltaY'), \
'0018,6030': ('UL', 'TransducerFrequency'), \
'0018,6031': ('CS', 'TransducerType'), \
'0018,6032': ('UL', 'PulseRepetitionFrequency'), \
'0018,6034': ('FD', 'DopplerCorrectionAngle'), \
'0018,6036': ('FD', 'SterringAngle'), \
'0018,6038': ('UL', 'DopplerSampleVolumeXPosition'), \
'0018,603a': ('UL', 'DopplerSampleVolumeYPosition'), \
'0018,603c': ('UL', 'TmlinePositionX0'), \
'0018,603e': ('UL', 'TmlinePositionY0'), \
'0018,6040': ('UL', 'TmlinePositionX1'), \
'0018,6042': ('UL', 'TmlinePositionY1'), \
'0018,6044': ('US', 'PixelComponentOrganization'), \
'0018,6046': ('UL', 'PixelComponentOrganization'), \
'0018,6048': ('UL', 'PixelComponentRangeStart'), \
'0018,604a': ('UL', 'PixelComponentRangeStop'), \
'0018,604c': ('US', 'PixelComponentPhysicalUnits'), \
'0018,604e': ('US', 'PixelComponentDataType'), \
'0018,6050': ('UL', 'NumberOfTableBreakPoints'), \
'0018,6052': ('UL', 'TableOfXBreakPoints'), \
'0018,6054': ('FD', 'TableOfYBreakPoints'), \
'0018,6056': ('UL', 'NumberofTableEntries'), \
'0018,6058': ('UL', 'TableofPixelValues'), \
'0018,605a': ('FL', 'TableofParameterValues'), \
'0018,7000': ('CS', 'DetectorConditionsNominalFlag'), \
'0018,7001': ('DS', 'DetectorTemperature'), \
'0018,7004': ('CS', 'DetectorType'), \
'0018,7005': ('CS', 'DetectorConfiguration'), \
'0018,7006': ('LT', 'DetectorDescription'), \
'0018,7008': ('LT', 'DetectorMode'), \
'0018,700a': ('SH', 'DetectorID'), \
'0018,700c': ('DA', 'DateofLastDetectorCalibration'), \
'0018,700e': ('TM', 'TimeofLastDetectorCalibration'), \
'0018,7010': ('IS', 'ExposuresonDetectorSinceLastCalibration'), \
'0018,7011': ('IS', 'ExposuresonDetectorSinceManufactured'), \
'0018,7012': ('DS', 'DetectorTimeSinceLastExposure'), \
'0018,7014': ('DS', 'DetectorActiveTime'), \
'0018,7016': ('DS', 'DetectorActivationOffsetFromExposure'), \
'0018,701a': ('DS', 'DetectorBinning'), \
'0018,7020': ('DS', 'DetectorElementPhysicalSize'), \
'0018,7022': ('DS', 'DetectorElementSpacing'), \
'0018,7024': ('CS', 'DetectorActiveShape'), \
'0018,7026': ('DS', 'DetectorActiveDimensions'), \
'0018,7028': ('DS', 'DetectorActiveOrigin'), \
'0018,7030': ('DS', 'FieldofViewOrigin'), \
'0018,7032': ('DS', 'FieldofViewRotation'), \
'0018,7034': ('CS', 'FieldofViewHorizontalFlip'), \
'0018,7040': ('LT', 'GridAbsorbingMaterial'), \
'0018,7041': ('LT', 'GridSpacingMaterial'), \
'0018,7042': ('DS', 'GridThickness'), \
'0018,7044': ('DS', 'GridPitch'), \
'0018,7046': ('IS', 'GridAspectRatio'), \
'0018,7048': ('DS', 'GridPeriod'), \
'0018,704c': ('DS', 'GridFocalDistance'), \
'0018,7050': ('CS', 'FilterMaterial'), \
'0018,7052': ('DS', 'FilterThicknessMinimum'), \
'0018,7054': ('DS', 'FilterThicknessMaximum'), \
'0018,7060': ('CS', 'ExposureControlMode'), \
'0018,7062': ('LT', 'ExposureControlModeDescription'), \
'0018,7064': ('CS', 'ExposureStatus'), \
'0018,7065': ('DS', 'PhototimerSetting'), \
'0018,8150': ('DS', 'ExposureTime'), \
'0018,8151': ('DS', 'XRayTubeCurrent'), \
'0019,0000': ('UL', 'GroupLength'), \
'0019,0010': ('LO', 'Privatecreator'), \
'0019,100f': ('DS', 'HorizontalFrameOfReference'), \
'0019,1011': ('SS', 'SeriesContrast'), \
'0019,1012': ('SS', 'LastPseq'), \
'0019,1017': ('SS', 'SeriesPlane'), \
'0019,1018': ('LO', 'FirstScanRas'), \
'0019,1019': ('DS', 'FirstScanLocation'), \
'0019,101a': ('LO', 'LastScanRas'), \
'0019,101b': ('DS', 'LastScanLocation'), \
'0019,101e': ('DS', 'DisplayFieldOfView'), \
'0019,105a': ('FL', 'AcquisitionDuration'), \
'0019,107d': ('DS', 'SecondEcho'), \
'0019,107e': ('SS', 'NumberOfEchos'), \
'0019,107f': ('DS', 'TableDelta'), \
'0019,1081': ('SS', 'Contiguous'), \
'0019,1084': ('DS', 'PeakSar'), \
'0019,1087': ('DS', 'CardiacRepetitionTime'), \
'0019,1088': ('SS', 'ImagesPerCardiacCycle'), \
'0019,108a': ('SS', 'ActualReceiveGainAnalog'), \
'0019,108b': ('SS', 'ActualReceiveGainDigital'), \
'0019,108d': ('DS', 'DelayAfterTrigger'), \
'0019,108f': ('SS', 'SwapPhaseFrequency'), \
'0019,1090': ('SS', 'PauseInterval'), \
'0019,1091': ('DS', 'PulseTime'), \
'0019,1092': ('SL', 'SliceOffsetOnFrequencyAxis'), \
'0019,1093': ('DS', 'CenterFrequency'), \
'0019,1094': ('SS', 'TransmitGain'), \
'0019,1095': ('SS', 'AnalogReceiverGain'), \
'0019,1096': ('SS', 'DigitalReceiverGain'), \
'0019,1097': ('SL', 'BitmapDefiningCvs'), \
'0019,109b': ('SS', 'PulseSequenceMode'), \
'0019,109c': ('LO', 'PulseSequenceName'), \
'0019,109d': ('DT', 'PulseSequenceDate'), \
'0019,109e': ('LO', 'InternalPulseSequenceName'), \
'0019,109f': ('SS', 'TransmittingCoil'), \
'0019,10a0': ('SS', 'SurfaceCoilType'), \
'0019,10a1': ('SS', 'ExtremityCoilFlag'), \
'0019,10a2': ('SL', 'RawDataRunNumber'), \
'0019,10a3': ('UL', 'CalibratedFieldStrength'), \
'0019,10a4': ('SS', 'SatFatWaterBone'), \
'0019,10a7': ('DS', 'UserData0'), \
'0019,10a8': ('DS', 'UserData1'), \
'0019,10a9': ('DS', 'UserData2'), \
'0019,10aa': ('DS', 'UserData3'), \
'0019,10ab': ('DS', 'UserData4'), \
'0019,10ac': ('DS', 'UserData5'), \
'0019,10ad': ('DS', 'UserData6'), \
'0019,10ae': ('DS', 'UserData7'), \
'0019,10af': ('DS', 'UserData8'), \
'0019,10b0': ('DS', 'UserData9'), \
'0019,10b1': ('DS', 'UserData10'), \
'0019,10b2': ('DS', 'UserData11'), \
'0019,10b3': ('DS', 'UserData12'), \
'0019,10b4': ('DS', 'UserData13'), \
'0019,10b5': ('DS', 'UserData14'), \
'0019,10b6': ('DS', 'UserData15'), \
'0019,10b7': ('DS', 'UserData16'), \
'0019,10b8': ('DS', 'UserData17'), \
'0019,10b9': ('DS', 'UserData18'), \
'0019,10ba': ('DS', 'UserData19'), \
'0019,10bb': ('DS', 'UserData20'), \
'0019,10bc': ('DS', 'UserData21'), \
'0019,10bd': ('DS', 'UserData22'), \
'0019,10be': ('DS', 'ProjectionAngle'), \
'0019,10c0': ('SS', 'SaturationPlanes'), \
'0019,10c2': ('SS', 'SatLocationR'), \
'0019,10c3': ('SS', 'SatLocationL'), \
'0019,10c4': ('SS', 'SatLocationA'), \
'0019,10c5': ('SS', 'SatLocationP'), \
'0019,10c6': ('SS', 'SatLocationH'), \
'0019,10c7': ('SS', 'SatLocationF'), \
'0019,10c8': ('SS', 'SatThicknessRL'), \
'0019,10c9': ('SS', 'SatThicknessAP'), \
'0019,10ca': ('SS', 'SatThicknessHF'), \
'0019,10cb': ('SS', 'PrescribedFlowAxis'), \
'0019,10cc': ('SS', 'VelocityEncoding'), \
'0019,10cd': ('SS', 'ThicknessDisclaimer'), \
'0019,10ce': ('SS', 'PrescanType'), \
'0019,10cf': ('SS', 'PrescanStatus'), \
'0019,10d2': ('SS', 'ProjectionAlgorithm'), \
'0019,10d3': ('SH', 'ProjectionAlgorithm'), \
'0019,10d5': ('SS', 'FractionalEcho'), \
'0019,10d7': ('SS', 'CardiacPhases'), \
'0019,10d8': ('SS', 'VariableEchoFlag'), \
'0019,10d9': ('DS', 'ConcatenatedSat'), \
'0019,10df': ('DS', 'UserData'), \
'0019,10e0': ('DS', 'UserData'), \
'0019,10e2': ('DS', 'VelocityEncodeScale'), \
'0019,10f2': ('SS', 'FastPhases'), \
'0019,10f9': ('DS', 'TransmissionGain'), \
'0020,0000': ('UL', 'Group0020Length'), \
'0020,000d': ('UI', 'StudyInstanceUid'), \
'0020,000e': ('UI', 'SeriesInstanceUid'), \
'0020,0010': ('SH', 'StudyID'), \
'0020,0011': ('IS', 'SeriesNumber'), \
'0020,0012': ('IS', 'AcquisitionNumber'), \
'0020,0013': ('IS', 'InstanceNumber'), \
'0020,0014': ('IS', 'IsotopeNumber'), \
'0020,0015': ('IS', 'PhaseNumber'), \
'0020,0016': ('IS', 'IntervalNumber'), \
'0020,0017': ('IS', 'TimeSlotNumber'), \
'0020,0018': ('IS', 'AngleNumber'), \
'0020,0019': ('IS', 'ItemNumber'), \
'0020,0020': ('CS', 'PatientOrientation'), \
'0020,0022': ('US', 'OverlayNumber'), \
'0020,0024': ('US', 'CurveNumber'), \
'0020,0026': ('IS', 'LookupTableNumber'), \
'0020,0030': ('DS', 'ImagePosition'), \
'0020,0032': ('DS', 'ImagePosition'), \
'0020,0035': ('DS', 'ImageOrientation'), \
'0020,0037': ('DS', 'ImageOrientation'), \
'0020,0050': ('DS', 'Location'), \
'0020,0052': ('UI', 'FrameOfReferenceUid'), \
'0020,0060': ('CS', 'Laterality'), \
'0020,0062': ('CS', 'ImageLaterality'), \
'0020,0070': ('SH', 'ImageGeometryType'), \
'0020,0080': ('UI', 'MaskingImageUid'), \
'0020,0100': ('IS', 'TemporalPositionIdentifier'), \
'0020,0105': ('IS', 'NumberOfTemporalPositions'), \
'0020,0110': ('DS', 'TemporalResolution'), \
'0020,0200': ('UI', 'SynchronizationFrameofReferenceUID'), \
'0020,1000': ('IS', 'SeriesInStudy'), \
'0020,1001': ('IS', 'AcquisitionsInSeries'), \
'0020,1002': ('IS', 'ImagesInAcquisition'), \
'0020,1004': ('IS', 'AcquisitionInStudy'), \
'0020,1020': ('SH', 'Reference'), \
'0020,1040': ('LO', 'PositionReferenceIndicator'), \
'0020,1041': ('DS', 'SliceLocation'), \
'0020,1070': ('IS', 'OtherStudyNumbers'), \
'0020,1200': ('IS', 'NumberOfPatientRelatedStudies'), \
'0020,1202': ('IS', 'NumberOfPatientRelatedSeries'), \
'0020,1204': ('IS', 'NumberOfPatientRelatedImages'), \
'0020,1206': ('IS', 'NumberOfStudyRelatedSeries'), \
'0020,1208': ('IS', 'NumberOfStudyRelatedImages'), \
'0020,1209': ('IS', 'NumberofSeriesRelatedInstances'), \
'0020,3100': ('SH', 'SourceImageIds'), \
'0020,3401': ('SH', 'ModifyingDeviceId'), \
'0020,3402': ('SH', 'ModifiedImageId'), \
'0020,3403': ('SH', 'ModifiedImageDate'), \
'0020,3404': ('SH', 'ModifyingDeviceManufacturer'), \
'0020,3405': ('SH', 'ModifiedImageTime'), \
'0020,3406': ('SH', 'ModifiedImageDescription'), \
'0020,4000': ('LT', 'ImageComments'), \
'0020,5000': ('US', 'OriginalImageIdentification'), \
'0020,5002': ('SH', 'OriginalImageIdentificationNomenclature'), \
'0021,0000': ('UL', 'GroupLength'), \
'0021,0010': ('LO', 'Privatecreator'), \
'0021,1035': ('SS', 'SeriesFromWhichPrescribed'), \
'0021,1036': ('SS', 'ImageFromWhichPrescribed'), \
'0021,1037': ('SS', 'ScreenFormat'), \
'0021,104f': ('SS', 'LocationsInAcquisition'), \
'0021,1050': ('SS', 'GraphicallyPrescribed'), \
'0021,1051': ('DS', 'RotationFromSourceXRot'), \
'0021,1052': ('DS', 'RotationFromSourceYRot'), \
'0021,1053': ('DS', 'RotationFromSourceZRot'), \
'0021,1056': ('SL', 'IntegerSlop'), \
'0021,1057': ('SL', 'IntegerSlop'), \
'0021,1058': ('SL', 'IntegerSlop'), \
'0021,1059': ('SL', 'IntegerSlop'), \
'0021,105a': ('SL', 'IntegerSlop'), \
'0021,105b': ('DS', 'FloatSlop'), \
'0021,105c': ('DS', 'FloatSlop'), \
'0021,105d': ('DS', 'FloatSlop'), \
'0021,105e': ('DS', 'FloatSlop'), \
'0021,105f': ('DS', 'FloatSlop'), \
'0021,1081': ('DS', 'AutoWindowLevelAlpha'), \
'0021,1082': ('DS', 'AutoWindowLevelBeta'), \
'0021,1083': ('DS', 'AutoWindowLevelWindow'), \
'0021,1084': ('DS', 'AutoWindowLevelLevel'), \
'0023,0000': ('UL', 'GroupLength'), \
'0023,0010': ('LO', 'Privatecreator'), \
'0023,1070': ('FD', 'StartTimeSecsInFirstAxial'), \
'0023,1074': ('SL', 'NumberOfUpdatesToHeader'), \
'0023,107d': ('SS', 'IndicatesIfStudyHasCompleteInfo'), \
'0025,0000': ('UL', 'GroupLength'), \
'0025,0010': ('LO', 'Privatecreator'), \
'0025,1006': ('SS', 'LastPulseSequenceUsed'), \
'0025,1007': ('SL', 'ImagesInSeries'), \
'0025,1010': ('SL', 'LandmarkCounter'), \
'0025,1011': ('SS', 'NumberOfAcquisitions'), \
'0025,1014': ('SL', 'IndicatesNumberOfUpdatesToHeader'), \
'0025,1017': ('SL', 'SeriesCompleteFlag'), \
'0025,1018': ('SL', 'NumberOfImagesArchived'), \
'0025,1019': ('SL', 'LastInstanceNumberUsed'), \
'0025,101a': ('SH', 'PrimaryReceiverSuiteAndHost'), \
'0025,101b': ('OB', 'ProtocolDataBlockCompressed'), \
'0027,0000': ('UL', 'GroupLength'), \
'0027,0010': ('LO', 'Privatecreator'), \
'0027,1006': ('SL', 'ImageArchiveFlag'), \
'0027,1010': ('SS', 'ScoutType'), \
'0027,1030': ('SH', 'ForeignImageRevision'), \
'0027,1031': ('SS', 'ImagingMode'), \
'0027,1032': ('SS', 'PulseSequence'), \
'0027,1033': ('UL', 'ImagingOptions'), \
'0027,1035': ('SS', 'PlaneType'), \
'0027,1040': ('SH', 'RasLetterOfImageLocation'), \
'0027,1041': ('FL', 'ImageLocation'), \
'0027,1060': ('FL', 'ImageDimensionX'), \
'0027,1061': ('FL', 'ImageDimensionY'), \
'0027,1062': ('FL', 'NumberOfExcitations'), \
'0028,0000': ('UL', 'Group0028Length'), \
'0028,0002': ('US', 'SamplesPerPixel'), \
'0028,0004': ('CS', 'PhotometricInterpretation'), \
'0028,0005': ('US', 'ImageDimensions'), \
'0028,0006': ('US', 'PlanarConfiguration'), \
'0028,0008': ('IS', 'NumberOfFrames'), \
'0028,0009': ('AT', 'FrameIncrementPointer'), \
'0028,0010': ('US', 'Rows'), \
'0028,0011': ('US', 'Columns'), \
'0028,0012': ('US', 'Planes'), \
'0028,0014': ('US', 'UltrasoundColorDataPresent'), \
'0028,0030': ('DS', 'PixelSpacing'), \
'0028,0031': ('DS', 'ZoomFactor'), \
'0028,0032': ('DS', 'ZoomCenter'), \
'0028,0034': ('IS', 'PixelAspectRatio'), \
'0028,0040': ('SH', 'ImageFormat'), \
'0028,0050': ('SH', 'ManipulatedImage'), \
'0028,0051': ('CS', 'CorrectedImage'), \
'0028,0060': ('SH', 'CompressionCode'), \
'0028,0100': ('US', 'Rows'), \
'0028,0101': ('US', 'BitsStored'), \
'0028,0102': ('US', 'HighBit'), \
'0028,0103': ('US', 'PixelRepresentation'), \
'0028,0104': ('US', 'SmallestValidPixelValue'), \
'0028,0105': ('US', 'LargestValidPixelValue'), \
'0028,0106': ('US', 'SmallestImagePixelValue'), \
'0028,0107': ('US', 'LargestImagePixelValue'), \
'0028,0108': ('US', 'SmallestPixelValueInSeries'), \
'0028,0109': ('US', 'LargestPixelValueInSeries'), \
'0028,0110': ('[US, SS]' 'SmallestImagePixelValueinPlane'), \
'0028,0111': ('[US, SS]' 'LargestImagePixelValueinPlane'), \
'0028,0120': ('US', 'PixelPaddingValue'), \
'0028,0200': ('US', 'ImageLocation'), \
'0028,0300': ('CS', 'QualityControlImage'), \
'0028,0301': ('CS', 'BurnedInAnnotation'), \
'0028,1040': ('CS', 'PixelIntensityRelationship'), \
'0028,1041': ('SS', 'PixelIntensityRelationshipSign'), \
'0028,1050': ('DS', 'WindowCenter'), \
'0028,1051': ('DS', 'WindowWidth'), \
'0028,1052': ('DS', 'RescaleIntercept'), \
'0028,1053': ('DS', 'RescaleSlope'), \
'0028,1054': ('LO', 'RescaleType'), \
'0028,1055': ('LO', 'WindowCenter&WidthExplanation'), \
'0028,1080': ('SH', 'GrayScale'), \
'0028,1090': ('CS', 'RecommendedViewingMode'), \
'0028,1100': ('US', 'GrayLookupTableDescriptor'), \
'0028,1101': ('US', 'RedPaletteColorLookupTableDescriptor'), \
'0028,1102': ('US', 'GreenPaletteColorLookupTableDescriptor'), \
'0028,1103': ('US', 'BluePaletteColorLookupTableDescriptor'), \
'0028,1199': ('UI', 'PaletteColorLookupTableUID'), \
'0028,1200': ('US', 'GrayLookupTableData'), \
'0028,1201': ('US', 'RedPaletteColorLookupTableData'), \
'0028,1202': ('US', 'GreenPaletteColorLookupTableData'), \
'0028,1203': ('US', 'BluePaletteColorLookupTableData'), \
'0028,1221': ('OW', 'SegmentedRedPaletteColorLookupTableData'), \
'0028,1222': ('OW', 'SegmentedGreenPaletteColorLookupTableData'), \
'0028,1223': ('OW', 'SegmentedBluePaletteColorLookupTableData'), \
'0028,1300': ('CS', 'ImplantPresent'), \
'0028,1350': ('CS', 'PartialView'), \
'0028,1351': ('ST', 'PartialViewDescription'), \
'0028,2110': ('CS', 'LossyImageCompression'), \
'0028,2112': ('DS', 'LossyImageCompressionRatio'), \
'0028,3000': ('SQ', 'ModalityLutSequence'), \
'0028,3002': ('US', 'LutDescriptor'), \
'0028,3003': ('LO', 'LutExplanation'), \
'0028,3004': ('LO', 'MadalityLutType'), \
'0028,3006': ('US', 'LutData'), \
'0028,3010': ('SQ', 'VoiLutSequence'), \
'0028,3110': ('SQ', 'SoftcopyVOILUTSequence'), \
'0028,4000': ('SH', 'Group0028Comments'), \
'0028,5000': ('SQ', 'BiPlaneAcquisitionSequence'), \
'0028,6010': ('US', 'RepresentativeFrameNumber'), \
'0028,6020': ('US', 'FrameNumbersofInterestFOI'), \
'0028,6022': ('LO', 'FramesofInterestDescription'), \
'0028,6030': ('US', 'MaskPointers'), \
'0028,6040': ('US', 'RWavePointer'), \
'0028,6100': ('SQ', 'MaskSubtractionSequence'), \
'0028,6101': ('CS', 'MaskOperation'), \
'0028,6102': ('US', 'ApplicableFrameRange'), \
'0028,6110': ('US', 'MaskFrameNumbers'), \
'0028,6112': ('US', 'ContrastFrameAveraging'), \
'0028,6114': ('FL', 'MaskSubpixelShift'), \
'0028,6120': ('SS', 'TIDOffset'), \
'0028,6190': ('ST', 'MaskOperationExplanation'), \
'0029,0000': ('UL', 'GroupLength'), \
'0029,0010': ('LO', 'Privatecreator'), \
'0029,0011': ('LO', 'Privatecreator'), \
'0029,0012': ('LO', 'Privatecreator'), \
'0029,1008': ('CS', 'CsaImageHeaderType'), \
'0029,1009': ('LO', 'CsaImageHeaderVersion'), \
'0029,1010': ('OB', 'CsaImageHeaderInfo'), \
'0029,1015': ('SL', 'LowerRangeOfPixels'), \
'0029,1016': ('SL', 'LowerRangeOfPixels'), \
'0029,1017': ('SL', 'LowerRangeOfPixels'), \
'0029,1018': ('CS', 'CsaSeriesHeaderType'), \
'0029,1019': ('LO', 'CsaSeriesHeaderVersion'), \
'0029,1020': ('OB', 'CsaSeriesHeaderInfo'), \
'0029,1026': ('SS', 'VersionOfHeaderStructure'), \
'0029,1034': ('SL', 'AdvantageCompOverflow'), \
'0029,1035': ('SL', 'AdvantageCompUnderflow'), \
'0029,1131': ('LO', 'PmtfInformation1'), \
'0029,1132': ('UL', 'PmtfInformation2'), \
'0029,1133': ('UL', 'PmtfInformation3'), \
'0029,1134': ('CS', 'PmtfInformation4'), \
'0029,1260': ('UN', ''), \
'0032,0000': ('UL', 'Group0032Length'), \
'0032,000a': ('CS', 'StudyStatusId'), \
'0032,000c': ('CS', 'StudyPriorityId'), \
'0032,0012': ('LO', 'StudyIdIssuer'), \
'0032,0032': ('DA', 'StudyVerifiedDate'), \
'0032,0033': ('TM', 'StudyVerifiedTime'), \
'0032,0034': ('DA', 'StudyReadDate'), \
'0032,0035': ('TM', 'StudyReadTime'), \
'0032,1000': ('DA', 'ScheduledStudyStartDate'), \
'0032,1001': ('TM', 'ScheduledStudyStartTime'), \
'0032,1010': ('DA', 'ScheduledStudyStopDate'), \
'0032,1011': ('TM', 'ScheduledStudyStopTime'), \
'0032,1020': ('LO', 'ScheduledStudyLocation'), \
'0032,1021': ('AE', 'ScheduledStudyLocationAeTitle'), \
'0032,1030': ('LO', 'ReasonForStudy'), \
'0032,1032': ('PN', 'RequestingPhysician'), \
'0032,1033': ('LO', 'RequestingService'), \
'0032,1040': ('DA', 'StudyArrivalDate'), \
'0032,1041': ('TM', 'StudyArrivalTime'), \
'0032,1050': ('DA', 'StudyCompletionDate'), \
'0032,1051': ('TM', 'StudyCompletionTime'), \
'0032,1055': ('CS', 'StudyComponentStatusId'), \
'0032,1060': ('LO', 'RequestedProcedureDescription'), \
'0032,1064': ('SQ', 'RequestedProcedureCodeSequence'), \
'0032,1070': ('LO', 'RequestedContrastAgent'), \
'0032,4000': ('LT', 'StudyComments'), \
'0038,0000': ('UL', 'Group0038Length'), \
'0038,0004': ('SQ', 'ReferencedPatientAliasSequence'), \
'0038,0008': ('CS', 'VisitStatusId'), \
'0038,0010': ('LO', 'AdmissinId'), \
'0038,0011': ('LO', 'IssuerOfAdmissionId'), \
'0038,0016': ('LO', 'RouteOfAdmissions'), \
'0038,001a': ('DA', 'ScheduledAdmissinDate'), \
'0038,001b': ('TM', 'ScheduledAdissionTime'), \
'0038,001c': ('DA', 'ScheduledDischargeDate'), \
'0038,001d': ('TM', 'ScheduledDischargeTime'), \
'0038,001e': ('LO', 'ScheduledPatientInstitutionResidence'), \
'0038,0020': ('DA', 'AdmittingDate'), \
'0038,0021': ('TM', 'AdmittingTime'), \
'0038,0030': ('DA', 'DischargeDate'), \
'0038,0032': ('TM', 'DischargeTime'), \
'0038,0040': ('LO', 'DischargeDiagnosisDescription'), \
'0038,0044': ('SQ', 'DischargeDiagnosisCodeSequence'), \
'0038,0050': ('LO', 'SpecialNeeds'), \
'0038,0300': ('LO', 'CurrentPatientLocation'), \
'0038,0400': ('LO', 'PatientInstitutionResidence'), \
'0038,0500': ('LO', 'PatientState'), \
'0038,4000': ('LT', 'VisitComments'), \
'003a,0004': ('CS', 'WaveformOriginality'), \
'003a,0005': ('US', 'NumberofWaveformChannels'), \
'003a,0010': ('UL', 'NumberofWaveformSamples'), \
'003a,001a': ('DS', 'SamplingFrequency'), \
'003a,0020': ('SH', 'MultiplexGroupLabel'), \
'003a,0200': ('SQ', 'ChannelDefinitionSequence'), \
'003a,0202': ('IS', 'WaveformChannelNumber'), \
'003a,0203': ('SH', 'ChannelLabel'), \
'003a,0205': ('CS', 'ChannelStatus'), \
'003a,0208': ('SQ', 'ChannelSourceSequence'), \
'003a,0209': ('SQ', 'ChannelSourceModifiersSequence'), \
'003a,020a': ('SQ', 'SourceWaveformSequence'), \
'003a,020c': ('LO', 'ChannelDerivationDescription'), \
'003a,0210': ('DS', 'ChannelSensitivity'), \
'003a,0211': ('SQ', 'ChannelSensitivityUnitsSequence'), \
'003a,0212': ('DS', 'ChannelSensitivityCorrectionFactor'), \
'003a,0213': ('DS', 'ChannelBaseline'), \
'003a,0214': ('DS', 'ChannelTimeSkew'), \
'003a,0215': ('DS', 'ChannelSampleSkew'), \
'003a,0218': ('DS', 'ChannelOffset'), \
'003a,021a': ('US', 'WaveformBitsStored'), \
'003a,0220': ('DS', 'FilterLowFrequency'), \
'003a,0221': ('DS', 'FilterHighFrequency'), \
'003a,0222': ('DS', 'NotchFilterFrequency'), \
'003a,0223': ('DS', 'NotchFilterBandwidth'), \
'0040,0000': ('UL', 'GroupLength'), \
'0040,0001': ('AE', 'ScheduledStationAETitle'), \
'0040,0002': ('DA', 'ScheduledProcedureStepStartDate'), \
'0040,0003': ('TM', 'ScheduledProcedureStepStartTime'), \
'0040,0004': ('DA', 'ScheduledProcedureStepEndDate'), \
'0040,0005': ('TM', 'ScheduledProcedureStepEndTime'), \
'0040,0006': ('PN', 'ScheduledPerformingPhysiciansName'), \
'0040,0007': ('LO', 'ScheduledProcedureStepDescription'), \
'0040,0008': ('SQ', 'ScheduledProtocolCodeSequence'), \
'0040,0009': ('SH', 'ScheduledProcedureStepID'), \
'0040,000a': ('SQ', 'StageCodeSequence'), \
'0040,0010': ('SH', 'ScheduledStationName'), \
'0040,0011': ('SH', 'ScheduledProcedureStepLocation'), \
'0040,0012': ('LO', 'PreMedication'), \
'0040,0020': ('CS', 'ScheduledProcedureStepStatus'), \
'0040,0100': ('SQ', 'ScheduledProcedureStepSequence'), \
'0040,0220': ('SQ', 'ReferencedNonImageCompositeSOPInstanceSequence'), \
'0040,0241': ('AE', 'PerformedStationAETitle'), \
'0040,0242': ('SH', 'PerformedStationName'), \
'0040,0243': ('SH', 'PerformedLocation'), \
'0040,0244': ('DA', 'PerformedProcedureStepStartDate'), \
'0040,0245': ('TM', 'PerformedProcedureStepStartTime'), \
'0040,0250': ('DA', 'PerformedProcedureStepEndDate'), \
'0040,0251': ('TM', 'PerformedProcedureStepEndTime'), \
'0040,0252': ('CS', 'PerformedProcedureStepStatus'), \
'0040,0253': ('SH', 'PerformedProcedureStepId'), \
'0040,0254': ('LO', 'PerformedProcedureStepDescription'), \
'0040,0255': ('LO', 'PerformedProcedureTypeDescription'), \
'0040,0260': ('SQ', 'PerformedProtocolCodeSequence'), \
'0040,0270': ('SQ', 'ScheduledStepAttributesSequence'), \
'0040,0275': ('SQ', 'RequestAttributesSequence'), \
'0040,0280': ('ST', 'CommentsonthePerformedProcedureStep'), \
'0040,0293': ('SQ', 'QuantitySequence'), \
'0040,0294': ('DS', 'Quantity'), \
'0040,0295': ('SQ', 'MeasuringUnitsSequence'), \
'0040,0296': ('SQ', 'BillingItemSequence'), \
'0040,0300': ('US', 'TotalTimeofFluoroscopy'), \
'0040,0301': ('US', 'TotalNumberofExposures'), \
'0040,0302': ('US', 'EntranceDose'), \
'0040,0303': ('US', 'ExposedArea'), \
'0040,0306': ('DS', 'DistanceSourcetoEntrance'), \
'0040,0307': ('DS', 'DistanceSourcetoSupport'), \
'0040,030e': ('SQ', 'ExposureDoseSequence'), \
'0040,0310': ('ST', 'CommentsonRadiationDose'), \
'0040,0312': ('DS', 'XRayOutput'), \
'0040,0314': ('DS', 'HalfValueLayer'), \
'0040,0316': ('DS', 'OrganDose'), \
'0040,0318': ('CS', 'OrganExposed'), \
'0040,0320': ('SQ', 'BillingProcedureStepSequence'), \
'0040,0321': ('SQ', 'FilmConsumptionSequence'), \
'0040,0324': ('SQ', 'BillingSuppliesandDevicesSequence'), \
'0040,0330': ('SQ', 'ReferencedProcedureStepSequence'), \
'0040,0340': ('SQ', 'PerformedSeriesSequence'), \
'0040,0400': ('LT', 'CommentsontheScheduledProcedureStep'), \
'0040,050a': ('LO', 'SpecimenAccessionNumber'), \
'0040,0550': ('SQ', 'SpecimenSequence'), \
'0040,0551': ('LO', 'SpecimenIdentifier'), \
'0040,0555': ('SQ', 'AcquisitionContextSequence'), \
'0040,0556': ('ST', 'AcquisitionContextDescription'), \
'0040,059a': ('SQ', 'SpecimenTypeCodeSequence'), \
'0040,06fa': ('LO', 'SlideIdentifier'), \
'0040,071a': ('SQ', 'ImageCenterPointCoordinatesSequence'), \
'0040,072a': ('DS', 'XoffsetinSlideCoordinateSystem'), \
'0040,073a': ('DS', 'YoffsetinSlideCoordinateSystem'), \
'0040,074a': ('DS', 'ZoffsetinSlideCoordinateSystem'), \
'0040,08d8': ('SQ', 'PixelSpacingSequence'), \
'0040,08da': ('SQ', 'CoordinateSystemAxisCodeSequence'), \
'0040,08ea': ('SQ', 'MeasurementUnitsCodeSequence'), \
'0040,1001': ('SH', 'RequestedProcedureID'), \
'0040,1002': ('LO', 'ReasonfortheRequestedProcedure'), \
'0040,1003': ('SH', 'RequestedProcedurePriority'), \
'0040,1004': ('LO', 'PatientTransportArrangements'), \
'0040,1005': ('LO', 'RequestedProcedureLocation'), \
'0040,1008': ('LO', 'ConfidentialityCode'), \
'0040,1009': ('SH', 'ReportingPriority'), \
'0040,1010': ('PN', 'NamesofIntendedRecipientsofResults'), \
'0040,1400': ('LT', 'RequestedProcedureComments'), \
'0040,2001': ('LO', 'ReasonfortheImagingServiceRequest'), \
'0040,2004': ('DA', 'IssueDateofImagingServiceRequest'), \
'0040,2005': ('TM', 'IssueTimeofImagingServiceRequest'), \
'0040,2008': ('PN', 'OrderEnteredBy'), \
'0040,2009': ('SH', 'OrderEnterersLocation'), \
'0040,2010': ('SH', 'OrderCallbackPhoneNumber'), \
'0040,2016': ('LO', 'PlacerOrderNumberImagingServiceRequest'), \
'0040,2017': ('LO', 'FillerOrderNumberImagingServiceRequest'), \
'0040,2400': ('LT', 'ImagingServiceRequestComments'), \
'0040,3001': ('LO', 'ConfidentialityConstraintonPatientDataDescription'), \
'0040,4001': ('CS', 'GeneralPurposeScheduledProcedureStepStatus'), \
'0040,4002': ('CS', 'GeneralPurposePerformedProcedureStepStatus'), \
'0040,4003': ('CS', 'GeneralPurposeScheduledProcedureStepPriority'), \
'0040,4004': ('SQ', 'ScheduledProcessingApplicationsCodeSequence'), \
'0040,4005': ('DT', 'ScheduledProcedureStepStartDateandTime'), \
'0040,4006': ('CS', 'MultipleCopiesFlag'), \
'0040,4007': ('SQ', 'PerformedProcessingApplicationsCodeSequence'), \
'0040,4009': ('SQ', 'HumanPerformerCodeSequence'), \
'0040,4011': ('DT', 'ExpectedCompletionDateandTime'), \
'0040,4015': ('SQ', 'ResultingGeneralPurposePerformedProcedureStepsSequence'), \
'0040,4016': ('SQ', 'ReferencedGeneralPurposeScheduledProcedureStepSequence'), \
'0040,4018': ('SQ', 'ScheduledWorkitemCodeSequence'), \
'0040,4019': ('SQ', 'PerformedWorkitemCodeSequence'), \
'0040,4020': ('CS', 'InputAvailabilityFlag'), \
'0040,4021': ('SQ', 'InputInformationSequence'), \
'0040,4022': ('SQ', 'RelevantInformationSequence'), \
'0040,4023': ('UI', 'ReferencedGeneralPurposeScheduledProcedureStepTransactionUID'), \
'0040,4025': ('SQ', 'ScheduledStationNameCodeSequence'), \
'0040,4026': ('SQ', 'ScheduledStationClassCodeSequence'), \
'0040,4027': ('SQ', 'ScheduledStationGeographicLocationCodeSequence'), \
'0040,4028': ('SQ', 'PerformedStationNameCodeSequence'), \
'0040,4029': ('SQ', 'PerformedStationClassCodeSequence'), \
'0040,4030': ('SQ', 'PerformedStationGeographicLocationCodeSequence'), \
'0040,4031': ('SQ', 'RequestedSubsequentWorkitemCodeSequence'), \
'0040,4032': ('SQ', 'NonDICOMOutputCodeSequence'), \
'0040,4033': ('SQ', 'OutputInformationSequence'), \
'0040,4034': ('SQ', 'ScheduledHumanPerformersSequence'), \
'0040,4035': ('SQ', 'ActualHumanPerformersSequence'), \
'0040,4036': ('LO', 'HumanPerformersOrganization'), \
'0040,4037': ('PN', 'HumanPerformersName'), \
'0040,8302': ('DS', 'EntranceDoseinmGy'), \
'0040,a010': ('CS', 'RelationshipType'), \
'0040,a027': ('LO', 'VerifyingOrganization'), \
'0040,a030': ('DT', 'VerificationDateTime'), \
'0040,a032': ('DT', 'ObservationDateTime'), \
'0040,a040': ('CS', 'ValueType'), \
'0040,a043': ('SQ', 'ConceptnameCodeSequence'), \
'0040,a050': ('CS', 'ContinuityOfContent'), \
'0040,a073': ('SQ', 'VerifyingObserverSequence'), \
'0040,a075': ('PN', 'VerifyingObserverName'), \
'0040,a088': ('SQ', 'VerifyingObserverIdentificationCodeSequence'), \
'0040,a0b0': ('US', 'ReferencedWaveformChannels'), \
'0040,a120': ('DT', 'DateTime'), \
'0040,a121': ('DA', 'Date'), \
'0040,a122': ('TM', 'Time'), \
'0040,a123': ('PN', 'PersonName'), \
'0040,a124': ('UI', 'UID'), \
'0040,a130': ('CS', 'TemporalRangeType'), \
'0040,a132': ('UL', 'ReferencedSamplePositions'), \
'0040,a136': ('US', 'ReferencedFrameNumbers'), \
'0040,a138': ('DS', 'ReferencedTimeOffsets'), \
'0040,a13a': ('DT', 'ReferencedDatetime'), \
'0040,a160': ('UT', 'TextValue'), \
'0040,a168': ('SQ', 'ConceptCodeSequence'), \
'0040,a170': ('SQ', 'PurposeofReferenceCodeSequence'), \
'0040,a180': ('US', 'AnnotationGroupNumber'), \
'0040,a195': ('SQ', 'ModifierCodeSequence'), \
'0040,a300': ('SQ', 'MeasuredValueSequence'), \
'0040,a30a': ('DS', 'NumericValue'), \
'0040,a360': ('SQ', 'PredecessorDocumentsSequence'), \
'0040,a370': ('SQ', 'ReferencedRequestSequence'), \
'0040,a372': ('SQ', 'PerformedProcedureCodeSequence'), \
'0040,a375': ('SQ', 'CurrentRequestedProcedureEvidenceSequence'), \
'0040,a385': ('SQ', 'PertinentOtherEvidenceSequence'), \
'0040,a491': ('CS', 'CompletionFlag'), \
'0040,a492': ('LO', 'CompletionFlagDescription'), \
'0040,a493': ('CS', 'VerificationFlag'), \
'0040,a504': ('SQ', 'ContentTemplateSequence'), \
'0040,a525': ('SQ', 'IdenticalDocumentsSequence'), \
'0040,a730': ('SQ', 'ContentSequence'), \
'0040,b020': ('SQ', 'AnnotationSequence'), \
'0040,db00': ('CS', 'TemplateIdentifier'), \
'0040,db06': ('DT', 'TemplateVersion'), \
'0040,db07': ('DT', 'TemplateLocalVersion'), \
'0040,db0b': ('CS', 'TemplateExtensionFlag'), \
'0040,db0c': ('UI', 'TemplateExtensionOrganizationUID'), \
'0040,db0d': ('UI', 'TemplateExtensionCreatorUID'), \
'0040,db73': ('UL', 'ReferencedContentItemIdentifier'), \
'0043,0000': ('UL', 'GroupLength'), \
'0043,0010': ('LO', 'Privatecreator'), \
'0043,1001': ('SS', 'BitmapOfPrescanOptions'), \
'0043,1002': ('SS', 'GradientOffsetInX'), \
'0043,1003': ('SS', 'GradientOffsetInY'), \
'0043,1004': ('SS', 'GradientOffsetInZ'), \
'0043,1006': ('SS', 'NumberOfEpiShots'), \
'0043,1007': ('SS', 'ViewsPerSegment'), \
'0043,1008': ('SS', 'RespiratoryRateInBpm'), \
'0043,1009': ('SS', 'RespiratoryTriggerPoint'), \
'0043,100a': ('SS', 'TypeOfReceiverUsed'), \
'0043,100b': ('DS', 'PeakRateOfChangeOfGradientField'), \
'0043,100c': ('DS', 'LimitsInUnitsOfPercent'), \
'0043,100d': ('DS', 'PsdEstimatedLimit'), \
'0043,100e': ('DS', 'PsdEstimatedLimitInTeslaPerSecond'), \
'0043,1010': ('US', 'WindowValue'), \
'0043,101c': ('SS', 'GeImageIntegrity'), \
'0043,101d': ('SS', 'LevelValue'), \
'0043,1028': ('OB', 'UniqueImageIdentifier'), \
'0043,1029': ('OB', 'HistogramTables'), \
'0043,102a': ('OB', 'UserDefinedData'), \
'0043,102c': ('SS', 'EffectiveEchoSpacing'), \
'0043,102d': ('SH', 'StringSlopField1'), \
'0043,102e': ('SH', 'StringSlopField2'), \
'0043,102f': ('SS', 'ImageType'), \
'0043,1030': ('SS', 'VasCollapseFlag'), \
'0043,1032': ('SS', 'VasFlags'), \
'0043,1033': ('FL', 'NegScanSpacing'), \
'0043,1034': ('IS', 'OffsetFrequency'), \
'0043,1035': ('UL', 'UserUsageTag'), \
'0043,1036': ('UL', 'UserFillMapMsw'), \
'0043,1037': ('UL', 'UserFillMapLsw'), \
'0043,1038': ('FL', 'User25ToUser48'), \
'0043,1039': ('IS', 'SlopInteger6ToSlopInteger9'), \
'0043,1060': ('IS', 'SlopInteger10ToSlopInteger17'), \
'0043,1061': ('UI', 'ScannerStudyEntityUid'), \
'0043,1062': ('SH', 'ScannerStudyId'), \
'0043,106f': ('DS', 'ScannerTableEntry+GradientCoilSelected'), \
'0043,107d': ('US', 'Unknown1'), \
'0043,1080': ('LO', 'Unknown2'), \
'0043,1081': ('LO', 'Coil'), \
'0043,1082': ('LO', 'Config'), \
'0043,1083': ('DS', 'Unknown3'), \
'0043,1084': ('LO', 'Unknown4'), \
'0043,1089': ('LO', 'FdaLevels'), \
'0043,108a': ('CS', 'Unknown4'), \
'0043,1090': ('LO', 'SarIntervals'), \
'0043,1091': ('DS', 'Unknown5'), \
'0043,1096': ('CS', 'Mode'), \
'0043,1097': ('LO', 'Unknown6'), \
'0050,0004': ('CS', 'CalibrationImage'), \
'0050,0010': ('SQ', 'DeviceSequence'), \
'0050,0014': ('DS', 'DeviceLength'), \
'0050,0016': ('DS', 'DeviceDiameter'), \
'0050,0017': ('CS', 'DeviceDiameterUnits'), \
'0050,0018': ('DS', 'DeviceVolume'), \
'0050,0019': ('DS', 'IntermarkerDistance'), \
'0050,0020': ('LO', 'DeviceDescription'), \
'0054,0010': ('US', 'EnergyWindowVector'), \
'0054,0011': ('US', 'NumberofEnergyWindows'), \
'0054,0012': ('SQ', 'EnergyWindowInformationSequence'), \
'0054,0013': ('SQ', 'EnergyWindowRangeSequence'), \
'0054,0014': ('DS', 'EnergyWindowLowerLimit'), \
'0054,0015': ('DS', 'EnergyWindowUpperLimit'), \
'0054,0016': ('SQ', 'RadiopharmaceuticalInformationSequence'), \
'0054,0017': ('IS', 'ResidualSyringeCounts'), \
'0054,0018': ('SH', 'EnergyWindowName'), \
'0054,0020': ('US', 'DetectorVector'), \
'0054,0021': ('US', 'NumberofDetectors'), \
'0054,0022': ('SQ', 'DetectorInformationSequence'), \
'0054,0030': ('US', 'PhaseVector'), \
'0054,0031': ('US', 'NumberofPhases'), \
'0054,0032': ('SQ', 'PhaseInformationSequence'), \
'0054,0033': ('US', 'NumberofFramesinPhase'), \
'0054,0036': ('IS', 'PhaseDelay'), \
'0054,0038': ('IS', 'PauseBetweenFrames'), \
'0054,0050': ('US', 'RotationVector'), \
'0054,0051': ('US', 'NumberofRotations'), \
'0054,0052': ('SQ', 'RotationInformationSequence'), \
'0054,0053': ('US', 'NumberofFramesinRotation'), \
'0054,0060': ('US', 'RRIntervalVector'), \
'0054,0061': ('US', 'NumberofRRIntervals'), \
'0054,0062': ('SQ', 'GatedInformationSequence'), \
'0054,0063': ('SQ', 'DataInformationSequence'), \
'0054,0070': ('US', 'TimeSlotVector'), \
'0054,0071': ('US', 'NumberofTimeSlots'), \
'0054,0072': ('SQ', 'TimeSlotInformationSequence'), \
'0054,0073': ('DS', 'TimeSlotTime'), \
'0054,0080': ('US', 'SliceVector'), \
'0054,0081': ('US', 'NumberofSlices'), \
'0054,0090': ('US', 'AngularViewVector'), \
'0054,0100': ('US', 'TimeSliceVector'), \
'0054,0101': ('US', 'NumberofTimeSlices'), \
'0054,0200': ('DS', 'StartAngle'), \
'0054,0202': ('CS', 'TypeofDetectorMotion'), \
'0054,0210': ('IS', 'TriggerVector'), \
'0054,0211': ('US', 'NumberofTriggersinPhase'), \
'0054,0220': ('SQ', 'ViewCodeSequence'), \
'0054,0222': ('SQ', 'ViewModifierCodeSequence'), \
'0054,0300': ('SQ', 'RadionuclideCodeSequence'), \
'0054,0302': ('SQ', 'AdministrationRouteCodeSequence'), \
'0054,0304': ('SQ', 'RadiopharmaceuticalCodeSequence'), \
'0054,0306': ('SQ', 'CalibrationDataSequence'), \
'0054,0308': ('US', 'EnergyWindowNumber'), \
'0054,0400': ('SH', 'ImageID'), \
'0054,0410': ('SQ', 'PatientOrientationCodeSequence'), \
'0054,0412': ('SQ', 'PatientOrientationModifierCodeSequence'), \
'0054,0414': ('SQ', 'PatientGantryRelationshipCodeSequence'), \
'0054,1000': ('CS', 'SeriesType'), \
'0054,1001': ('CS', 'Units'), \
'0054,1002': ('CS', 'CountsSource'), \
'0054,1004': ('CS', 'ReprojectionMethod'), \
'0054,1100': ('CS', 'RandomsCorrectionMethod'), \
'0054,1101': ('LO', 'AttenuationCorrectionMethod'), \
'0054,1102': ('CS', 'DecayCorrection'), \
'0054,1103': ('LO', 'ReconstructionMethod'), \
'0054,1104': ('LO', 'DetectorLinesofResponseUsed'), \
'0054,1105': ('LO', 'ScatterCorrectionMethod'), \
'0054,1200': ('DS', 'AxialAcceptance'), \
'0054,1201': ('IS', 'AxialMash'), \
'0054,1202': ('IS', 'TransverseMash'), \
'0054,1203': ('DS', 'DetectorElementSize'), \
'0054,1210': ('DS', 'CoincidenceWindowWidth'), \
'0054,1220': ('CS', 'SecondaryCountsType'), \
'0054,1300': ('DS', 'FrameReferenceTime'), \
'0054,1310': ('IS', 'PrimaryPromptsCountsAccumulated'), \
'0054,1311': ('IS', 'SecondaryCountsAccumulated'), \
'0054,1320': ('DS', 'SliceSensitivityFactor'), \
'0054,1321': ('DS', 'DecayFactor'), \
'0054,1322': ('DS', 'DoseCalibrationFactor'), \
'0054,1323': ('DS', 'ScatterFractionFactor'), \
'0054,1324': ('DS', 'DeadTimeFactor'), \
'0054,1330': ('US', 'ImageIndex'), \
'0054,1400': ('CS', 'CountsIncluded'), \
'0054,1401': ('CS', 'DeadTimeCorrectionFlag'), \
'0060,3000': ('SQ', 'HistogramSequence'), \
'0060,3002': ('US', 'HistogramNumberofBins'), \
'0060,3004': ('[US, SS]' 'HistogramFirstBinValue'), \
'0060,3006': ('[US, SS]' 'HistogramLastBinValue'), \
'0060,3008': ('US', 'HistogramBinWidth'), \
'0060,3010': ('LO', 'HistogramExplanation'), \
'0060,3020': ('UL', 'HistogramData'), \
'0070,0001': ('SQ', 'GraphicAnnotationSequence'), \
'0070,0002': ('CS', 'GraphicLayer'), \
'0070,0003': ('CS', 'BoundingBoxAnnotationUnits'), \
'0070,0004': ('CS', 'AnchorPointAnnotationUnits'), \
'0070,0005': ('CS', 'GraphicAnnotationUnits'), \
'0070,0006': ('ST', 'UnformattedTextValue'), \
'0070,0008': ('SQ', 'TextObjectSequence'), \
'0070,0009': ('SQ', 'GraphicObjectSequence'), \
'0070,0010': ('FL', 'BoundingBoxTopLeftHandCorner'), \
'0070,0011': ('FL', 'BoundingBoxBottomRightHandCorner'), \
'0070,0012': ('CS', 'BoundingBoxTextHorizontalJustification'), \
'0070,0014': ('FL', 'AnchorPoint'), \
'0070,0015': ('CS', 'AnchorPointVisibility'), \
'0070,0020': ('US', 'GraphicDimensions'), \
'0070,0021': ('US', 'NumberofGraphicPoints'), \
'0070,0022': ('FL', 'GraphicData'), \
'0070,0023': ('CS', 'GraphicType'), \
'0070,0024': ('CS', 'GraphicFilled'), \
'0070,0041': ('CS', 'ImageHorizontalFlip'), \
'0070,0042': ('US', 'ImageRotation'), \
'0070,0052': ('SL', 'DisplayedAreaTopLeftHandCorner'), \
'0070,0053': ('SL', 'DisplayedAreaBottomRightHandCorner'), \
'0070,005a': ('SQ', 'DisplayedAreaSelectionSequence'), \
'0070,0060': ('SQ', 'GraphicLayerSequence'), \
'0070,0062': ('IS', 'GraphicLayerOrder'), \
'0070,0066': ('US', 'GraphicLayerRecommendedDisplayGrayscaleValue'), \
'0070,0067': ('US', 'GraphicLayerRecommendedDisplayRGBValue'), \
'0070,0068': ('LO', 'GraphicLayerDescription'), \
'0070,0080': ('CS', 'PresentationLabel'), \
'0070,0081': ('LO', 'PresentationDescription'), \
'0070,0082': ('DA', 'PresentationCreationDate'), \
'0070,0083': ('TM', 'PresentationCreationTime'), \
'0070,0084': ('PN', 'PresentationCreatorsName'), \
'0070,0100': ('CS', 'PresentationSizeMode'), \
'0070,0101': ('DS', 'PresentationPixelSpacing'), \
'0070,0102': ('IS', 'PresentationPixelAspectRatio'), \
'0070,0103': ('FL', 'PresentationPixelMagnificationRatio'), \
'0088,0000': ('UL', 'Group0088Length'), \
'0088,0130': ('SH', 'StorageMediaFilesetId'), \
'0088,0140': ('UI', 'StorageMediaFilesetUid'), \
'0088,0200': ('SQ', 'IconImageSequence'), \
'0088,0904': ('LO', 'TopicTitle'), \
'0088,0906': ('ST', 'TopicSubject'), \
'0088,0910': ('LO', 'TopicAuthor'), \
'0088,0912': ('LO', 'TopicKeyWords'), \
'0100,0410': ('CS', 'SOPInstanceStatus'), \
'0100,0420': ('DT', 'SOPAuthorizationDateandTime'), \
'0100,0424': ('LT', 'SOPAuthorizationComment'), \
'0100,0426': ('LO', 'AuthorizationEquipmentCertificationNumber'), \
'0400,0005': ('US', 'MACIDnumber'), \
'0400,0010': ('UI', 'MACCalculationTransferSyntaxUID'), \
'0400,0015': ('CS', 'MACAlgorithm'), \
'0400,0020': ('AT', 'DataElementsSigned'), \
'0400,0100': ('UI', 'DigitalSignatureUID'), \
'0400,0105': ('DT', 'DigitalSignatureDateTime'), \
'0400,0110': ('CS', 'CertificateType'), \
'0400,0115': ('OB', 'CertificateofSigner'), \
'0400,0120': ('OB', 'Signature'), \
'0400,0305': ('CS', 'CertifiedTimestampType'), \
'0400,0310': ('OB', 'CertifiedTimestamp'), \
'2000,0000': ('UL', 'Group2000Length'), \
'2000,0010': ('IS', 'NumberOfCopies'), \
'2000,001e': ('SQ', 'PrinterConfigurationSequence'), \
'2000,0020': ('CS', 'PrintPriority'), \
'2000,0030': ('CS', 'MediumType'), \
'2000,0040': ('CS', 'FilmDestination'), \
'2000,0050': ('LO', 'FilmSessionLabel'), \
'2000,0060': ('IS', 'MemoryAllocation'), \
'2000,0061': ('IS', 'MaximumMemoryAllocation'), \
'2000,0062': ('CS', 'ColorImagePrintingFlag'), \
'2000,0063': ('CS', 'CollationFlag'), \
'2000,0065': ('CS', 'AnnotationFlag'), \
'2000,0067': ('CS', 'ImageOverlayFlag'), \
'2000,0069': ('CS', 'PresentationLUTFlag'), \
'2000,006a': ('CS', 'ImageBoxPresentationLUTFlag'), \
'2000,00a0': ('US', 'MemoryBitDepth'), \
'2000,00a1': ('US', 'PrintingBitDepth'), \
'2000,00a2': ('SQ', 'MediaInstalledSequence'), \
'2000,00a4': ('SQ', 'OtherMediaAvailableSequence'), \
'2000,00a8': ('SQ', 'SupportedImageDisplayFormatsSequence'), \
'2000,0500': ('SQ', 'ReferencedFilmBoxSequence'), \
'2000,0510': ('SQ', 'ReferencedStoredPrintSequence'), \
'2010,0000': ('UL', 'Group2010Length'), \
'2010,0010': ('ST', 'ImageDisplayFormat'), \
'2010,0030': ('CS', 'AnnotationDisplayFormatId'), \
'2010,0040': ('CS', 'FilmOrientation'), \
'2010,0050': ('CS', 'FilmSizeId'), \
'2010,0052': ('CS', 'PrinterResolutionID'), \
'2010,0054': ('CS', 'DefaultPrinterResolutionID'), \
'2010,0060': ('CS', 'MagnificationType'), \
'2010,0080': ('CS', 'SmoothingType'), \
'2010,00a6': ('CS', 'DefaultMagnificationType'), \
'2010,00a7': ('CS', 'OtherMagnificationTypesAvailable'), \
'2010,00a8': ('CS', 'DefaultSmoothingType'), \
'2010,00a9': ('CS', 'OtherSmoothingTypesAvailable'), \
'2010,0100': ('CS', 'BorderDensity'), \
'2010,0110': ('CS', 'EmptyImageDensity'), \
'2010,0120': ('US', 'MinDensity'), \
'2010,0130': ('US', 'MaxDensity'), \
'2010,0140': ('CS', 'Trim'), \
'2010,0150': ('ST', 'ConfigurationInformation'), \
'2010,0152': ('LT', 'ConfigurationInformationDescription'), \
'2010,0154': ('IS', 'MaximumCollatedFilms'), \
'2010,015e': ('US', 'Illumination'), \
'2010,0160': ('US', 'ReflectedAmbientLight'), \
'2010,0376': ('DS', 'PrinterPixelSpacing'), \
'2010,0500': ('SQ', 'ReferencedFilmSessionSequence'), \
'2010,0510': ('SQ', 'ReferencedBasicImageBoxSequence'), \
'2010,0520': ('SQ', 'ReferencedBasicAnnotationBoxSequence'), \
'2020,0000': ('UL', 'Group2020Length'), \
'2020,0010': ('US', 'ImagePosition'), \
'2020,0020': ('CS', 'Polarity'), \
'2020,0030': ('DS', 'RequestedImageSize'), \
'2020,0040': ('CS', 'RequestedDecimateCropBehavior'), \
'2020,0050': ('CS', 'RequestedResolutionID'), \
'2020,00a0': ('CS', 'RequestedImageSizeFlag'), \
'2020,00a2': ('CS', 'DecimateCropResult'), \
'2020,0110': ('SQ', 'PreformattedGreyscaleImageSequence'), \
'2020,0111': ('SQ', 'PreformattedColorImageSequence'), \
'2020,0130': ('SQ', 'ReferencedImageOverlayBoxSequence'), \
'2020,0140': ('SQ', 'ReferencedVoiLutSequence'), \
'2030,0000': ('UL', 'Group2030Length'), \
'2030,0010': ('US', 'AnnotationPosition'), \
'2030,0020': ('LO', 'TextString'), \
'2040,0000': ('UL', 'Group2040Length'), \
'2040,0010': ('SQ', 'ReferencedOverlayPlaneSequence'), \
'2040,0011': ('US', 'RefencedOverlayPlaneGroups'), \
'2040,0020': ('SQ', 'OverlayPixelDataSequence'), \
'2040,0060': ('CS', 'OverlayMagnificationType'), \
'2040,0070': ('CS', 'OverlaySmoothingType'), \
'2040,0072': ('CS', 'OverlayorImageMagnification'), \
'2040,0074': ('US', 'MagnifytoNumberofColumns'), \
'2040,0080': ('CS', 'OverlayForegroundDensity'), \
'2040,0082': ('CS', 'OverlayBackgroundDensity'), \
'2040,0090': ('CS', 'OverlayMode'), \
'2040,0100': ('CS', 'ThresholdDensity'), \
'2040,0500': ('SQ', 'ReferencedImageBoxSequence'), \
'2050,0010': ('SQ', 'PresentationLUTSequence'), \
'2050,0020': ('CS', 'PresentationLUTShape'), \
'2050,0500': ('SQ', 'ReferencedPresentationLUTSequence'), \
'2100,0000': ('UL', 'Group2100Length'), \
'2100,0010': ('SH', 'PrintJobID'), \
'2100,0020': ('CS', 'ExecutionStatus'), \
'2100,0030': ('CS', 'ExecutionStatusInfo'), \
'2100,0040': ('DA', 'CreationDate'), \
'2100,0050': ('TM', 'CreationTime'), \
'2100,0070': ('AE', 'Originator'), \
'2100,0140': ('AE', 'DestinationAE'), \
'2100,0160': ('SH', 'OwnerID'), \
'2100,0170': ('IS', 'NumberofFilms'), \
'2100,0500': ('SQ', 'ReferencedPrintJobSequence'), \
'2110,0000': ('UL', 'Group2110Length'), \
'2110,0010': ('CS', 'PrinterStatus'), \
'2110,0020': ('CS', 'PrinterStatusInfo'), \
'2110,0030': ('ST', 'PrinterName'), \
'2110,0099': ('SH', 'PrintQueueID'), \
'2120,0010': ('CS', 'QueueStatus'), \
'2120,0050': ('SQ', 'PrintJobDescriptionSequence'), \
'2120,0070': ('SQ', 'ReferencedPrintJobSequence'), \
'2130,0010': ('SQ', 'PrintManagementCapabilitiesSequence'), \
'2130,0015': ('SQ', 'PrinterCharacteristicsSequence'), \
'2130,0030': ('SQ', 'FilmBoxContentSequence'), \
'2130,0040': ('SQ', 'ImageBoxContentSequence'), \
'2130,0050': ('SQ', 'AnnotationContentSequence'), \
'2130,0060': ('SQ', 'ImageOverlayBoxContentSequence'), \
'2130,0080': ('SQ', 'PresentationLUTContentSequence'), \
'2130,00a0': ('SQ', 'ProposedStudySequence'), \
'2130,00c0': ('SQ', 'OriginalImageSequence'), \
'3002,0002': ('SH', 'RTImageLabel'), \
'3002,0003': ('LO', 'RTImageName'), \
'3002,0004': ('ST', 'RTImageDescription'), \
'3002,000a': ('CS', 'ReportedValuesOrigin'), \
'3002,000c': ('CS', 'RTImagePlane'), \
'3002,000d': ('DS', 'XRayImageReceptorTranslation'), \
'3002,000e': ('DS', 'XRayImageReceptorAngle'), \
'3002,0010': ('DS', 'RTImageOrientation'), \
'3002,0011': ('DS', 'ImagePlanePixelSpacing'), \
'3002,0012': ('DS', 'RTImagePosition'), \
'3002,0020': ('SH', 'RadiationMachineName'), \
'3002,0022': ('DS', 'RadiationMachineSAD'), \
'3002,0024': ('DS', 'RadiationMachineSSD'), \
'3002,0026': ('DS', 'RTImageSID'), \
'3002,0028': ('DS', 'SourcetoReferenceObjectDistance'), \
'3002,0029': ('IS', 'FractionNumber'), \
'3002,0030': ('SQ', 'ExposureSequence'), \
'3002,0032': ('DS', 'MetersetExposure'), \
'3002,0034': ('DS', 'DiaphragmPosition'), \
'3004,0001': ('CS', 'DVHType'), \
'3004,0002': ('CS', 'DoseUnits'), \
'3004,0004': ('CS', 'DoseType'), \
'3004,0006': ('LO', 'DoseComment'), \
'3004,0008': ('DS', 'NormalizationPoint'), \
'3004,000a': ('CS', 'DoseSummationType'), \
'3004,000c': ('DS', 'GridFrameOffsetVector'), \
'3004,000e': ('DS', 'DoseGridScaling'), \
'3004,0010': ('SQ', 'RTDoseROISequence'), \
'3004,0012': ('DS', 'DoseValue'), \
'3004,0040': ('DS', 'DVHNormalizationPoint'), \
'3004,0042': ('DS', 'DVHNormalizationDoseValue'), \
'3004,0050': ('SQ', 'DVHSequence'), \
'3004,0052': ('DS', 'DVHDoseScaling'), \
'3004,0054': ('CS', 'DVHVolumeUnits'), \
'3004,0056': ('IS', 'DVHNumberofBins'), \
'3004,0058': ('DS', 'DVHData'), \
'3004,0060': ('SQ', 'DVHReferencedROISequence'), \
'3004,0062': ('CS', 'DVHROIContributionType'), \
'3004,0070': ('DS', 'DVHMinimumDose'), \
'3004,0072': ('DS', 'DVHMaximumDose'), \
'3004,0074': ('DS', 'DVHMeanDose'), \
'3006,0002': ('SH', 'StructureSetLabel'), \
'3006,0004': ('LO', 'StructureSetName'), \
'3006,0006': ('ST', 'StructureSetDescription'), \
'3006,0008': ('DA', 'StructureSetDate'), \
'3006,0009': ('TM', 'StructureSetTime'), \
'3006,0010': ('SQ', 'ReferencedFrameofReferenceSequence'), \
'3006,0012': ('SQ', 'RTReferencedStudySequence'), \
'3006,0014': ('SQ', 'RTReferencedSeriesSequence'), \
'3006,0016': ('SQ', 'ContourImageSequence'), \
'3006,0020': ('SQ', 'StructureSetROISequence'), \
'3006,0022': ('IS', 'ROINumber'), \
'3006,0024': ('UI', 'ReferencedFrameofReferenceUID'), \
'3006,0026': ('LO', 'ROIName'), \
'3006,0028': ('ST', 'ROIDescription'), \
'3006,002a': ('IS', 'ROIDisplayColor'), \
'3006,002c': ('DS', 'ROIVolume'), \
'3006,0030': ('SQ', 'RTRelatedROISequence'), \
'3006,0033': ('CS', 'RTROIRelationship'), \
'3006,0036': ('CS', 'ROIGenerationAlgorithm'), \
'3006,0038': ('LO', 'ROIGenerationDescription'), \
'3006,0039': ('SQ', 'ROIContourSequence'), \
'3006,0040': ('SQ', 'ContourSequence'), \
'3006,0042': ('CS', 'ContourGeometricType'), \
'3006,0044': ('DS', 'ContourSlabThickness'), \
'3006,0045': ('DS', 'ContourOffsetVector'), \
'3006,0046': ('IS', 'NumberofContourPoints'), \
'3006,0048': ('IS', 'ContourNumber'), \
'3006,0049': ('IS', 'AttachedContours'), \
'3006,0050': ('DS', 'ContourData'), \
'3006,0080': ('SQ', 'RTROIObservationsSequence'), \
'3006,0082': ('IS', 'ObservationNumber'), \
'3006,0084': ('IS', 'ReferencedROINumber'), \
'3006,0085': ('SH', 'ROIObservationLabel'), \
'3006,0086': ('SQ', 'RTROIIdentificationCodeSequence'), \
'3006,0088': ('ST', 'ROIObservationDescription'), \
'3006,00a0': ('SQ', 'RelatedRTROIObservationsSequence'), \
'3006,00a4': ('CS', 'RTROIInterpretedType'), \
'3006,00a6': ('PN', 'ROIInterpreter'), \
'3006,00b0': ('SQ', 'ROIPhysicalPropertiesSequence'), \
'3006,00b2': ('CS', 'ROIPhysicalProperty'), \
'3006,00b4': ('DS', 'ROIPhysicalPropertyValue'), \
'3006,00c0': ('SQ', 'FrameofReferenceRelationshipSequence'), \
'3006,00c2': ('UI', 'RelatedFrameofReferenceUID'), \
'3006,00c4': ('CS', 'FrameofReferenceTransformationType'), \
'3006,00c6': ('DS', 'FrameofReferenceTransformationMatrix'), \
'3006,00c8': ('LO', 'FrameofReferenceTransformationComment'), \
'3008,0010': ('SQ', 'MeasuredDoseReferenceSequence'), \
'3008,0012': ('ST', 'MeasuredDoseDescription'), \
'3008,0014': ('CS', 'MeasuredDoseType'), \
'3008,0016': ('DS', 'MeasuredDoseValue'), \
'3008,0020': ('SQ', 'TreatmentSessionBeamSequence'), \
'3008,0022': ('IS', 'CurrentFractionNumber'), \
'3008,0024': ('DA', 'TreatmentControlPointDate'), \
'3008,0025': ('TM', 'TreatmentControlPointTime'), \
'3008,002a': ('CS', 'TreatmentTerminationStatus'), \
'3008,002b': ('SH', 'TreatmentTerminationCode'), \
'3008,002c': ('CS', 'TreatmentVerificationStatus'), \
'3008,0030': ('SQ', 'ReferencedTreatmentRecordSequence'), \
'3008,0032': ('DS', 'SpecifiedPrimaryMeterset'), \
'3008,0033': ('DS', 'SpecifiedSecondaryMeterset'), \
'3008,0036': ('DS', 'DeliveredPrimaryMeterset'), \
'3008,0037': ('DS', 'DeliveredSecondaryMeterset'), \
'3008,003a': ('DS', 'SpecifiedTreatmentTime'), \
'3008,003b': ('DS', 'DeliveredTreatmentTime'), \
'3008,0040': ('SQ', 'ControlPointDeliverySequence'), \
'3008,0042': ('DS', 'SpecifiedMeterset'), \
'3008,0044': ('DS', 'DeliveredMeterset'), \
'3008,0048': ('DS', 'DoseRateDelivered'), \
'3008,0050': ('SQ', 'TreatmentSummaryCalculatedDoseReferenceSequence'), \
'3008,0052': ('DS', 'CumulativeDosetoDoseReference'), \
'3008,0054': ('DA', 'FirstTreatmentDate'), \
'3008,0056': ('DA', 'MostRecentTreatmentDate'), \
'3008,005a': ('IS', 'NumberofFractionsDelivered'), \
'3008,0060': ('SQ', 'OverrideSequence'), \
'3008,0062': ('AT', 'OverrideParameterPointer'), \
'3008,0064': ('IS', 'MeasuredDoseReferenceNumber'), \
'3008,0066': ('ST', 'OverrideReason'), \
'3008,0070': ('SQ', 'CalculatedDoseReferenceSequence'), \
'3008,0072': ('IS', 'CalculatedDoseReferenceNumber'), \
'3008,0074': ('ST', 'CalculatedDoseReferenceDescription'), \
'3008,0076': ('DS', 'CalculatedDoseReferenceDoseValue'), \
'3008,0078': ('DS', 'StartMeterset'), \
'3008,007a': ('DS', 'EndMeterset'), \
'3008,0080': ('SQ', 'ReferencedMeasuredDoseReferenceSequence'), \
'3008,0082': ('IS', 'ReferencedMeasuredDoseReferenceNumber'), \
'3008,0090': ('SQ', 'ReferencedCalculatedDoseReferenceSequence'), \
'3008,0092': ('IS', 'ReferencedCalculatedDoseReferenceNumber'), \
'3008,00a0': ('SQ', 'BeamLimitingDeviceLeafPairsSequence'), \
'3008,00b0': ('SQ', 'RecordedWedgeSequence'), \
'3008,00c0': ('SQ', 'RecordedCompensatorSequence'), \
'3008,00d0': ('SQ', 'RecordedBlockSequence'), \
'3008,00e0': ('SQ', 'TreatmentSummaryMeasuredDoseReferenceSequence'), \
'3008,0100': ('SQ', 'RecordedSourceSequence'), \
'3008,0105': ('LO', 'SourceSerialNumber'), \
'3008,0110': ('SQ', 'TreatmentSessionApplicationSetupSequence'), \
'3008,0116': ('CS', 'ApplicationSetupCheck'), \
'3008,0120': ('SQ', 'RecordedBrachyAccessoryDeviceSequence'), \
'3008,0122': ('IS', 'ReferencedBrachyAccessoryDeviceNumber'), \
'3008,0130': ('SQ', 'RecordedChannelSequence'), \
'3008,0132': ('DS', 'SpecifiedChannelTotalTime'), \
'3008,0134': ('DS', 'DeliveredChannelTotalTime'), \
'3008,0136': ('IS', 'SpecifiedNumberofPulses'), \
'3008,0138': ('IS', 'DeliveredNumberofPulses'), \
'3008,013a': ('DS', 'SpecifiedPulseRepetitionInterval'), \
'3008,013c': ('DS', 'DeliveredPulseRepetitionInterval'), \
'3008,0140': ('SQ', 'RecordedSourceApplicatorSequence'), \
'3008,0142': ('IS', 'ReferencedSourceApplicatorNumber'), \
'3008,0150': ('SQ', 'RecordedChannelShieldSequence'), \
'3008,0152': ('IS', 'ReferencedChannelShieldNumber'), \
'3008,0160': ('SQ', 'BrachyControlPointDeliveredSequence'), \
'3008,0162': ('DA', 'SafePositionExitDate'), \
'3008,0164': ('TM', 'SafePositionExitTime'), \
'3008,0166': ('DA', 'SafePositionReturnDate'), \
'3008,0168': ('TM', 'SafePositionReturnTime'), \
'3008,0200': ('CS', 'CurrentTreatmentStatus'), \
'3008,0202': ('ST', 'TreatmentStatusComment'), \
'3008,0220': ('SQ', 'FractionGroupSummarySequence'), \
'3008,0223': ('IS', 'ReferencedFractionNumber'), \
'3008,0224': ('CS', 'FractionGroupType'), \
'3008,0230': ('CS', 'BeamStopperPosition'), \
'3008,0240': ('SQ', 'FractionStatusSummarySequence'), \
'3008,0250': ('DA', 'TreatmentDate'), \
'3008,0251': ('TM', 'TreatmentTime'), \
'300a,0002': ('SH', 'RTPlanLabel'), \
'300a,0003': ('LO', 'RTPlanName'), \
'300a,0004': ('ST', 'RTPlanDescription'), \
'300a,0006': ('DA', 'RTPlanDate'), \
'300a,0007': ('TM', 'RTPlanTime'), \
'300a,0009': ('LO', 'TreatmentProtocols'), \
'300a,000a': ('CS', 'TreatmentIntent'), \
'300a,000b': ('LO', 'TreatmentSites'), \
'300a,000c': ('CS', 'RTPlanGeometry'), \
'300a,000e': ('ST', 'PrescriptionDescription'), \
'300a,0010': ('SQ', 'DoseReferenceSequence'), \
'300a,0012': ('IS', 'DoseReferenceNumber'), \
'300a,0014': ('CS', 'DoseReferenceStructureType'), \
'300a,0015': ('CS', 'NominalBeamEnergyUnit'), \
'300a,0016': ('LO', 'DoseReferenceDescription'), \
'300a,0018': ('DS', 'DoseReferencePointCoordinates'), \
'300a,001a': ('DS', 'NominalPriorDose'), \
'300a,0020': ('CS', 'DoseReferenceType'), \
'300a,0021': ('DS', 'ConstraintWeight'), \
'300a,0022': ('DS', 'DeliveryWarningDose'), \
'300a,0023': ('DS', 'DeliveryMaximumDose'), \
'300a,0025': ('DS', 'TargetMinimumDose'), \
'300a,0026': ('DS', 'TargetPrescriptionDose'), \
'300a,0027': ('DS', 'TargetMaximumDose'), \
'300a,0028': ('DS', 'TargetUnderdoseVolumeFraction'), \
'300a,002a': ('DS', 'OrganatRiskFullvolumeDose'), \
'300a,002b': ('DS', 'OrganatRiskLimitDose'), \
'300a,002c': ('DS', 'OrganatRiskMaximumDose'), \
'300a,002d': ('DS', 'OrganatRiskOverdoseVolumeFraction'), \
'300a,0040': ('SQ', 'ToleranceTableSequence'), \
'300a,0042': ('IS', 'ToleranceTableNumber'), \
'300a,0043': ('SH', 'ToleranceTableLabel'), \
'300a,0044': ('DS', 'GantryAngleTolerance'), \
'300a,0046': ('DS', 'BeamLimitingDeviceAngleTolerance'), \
'300a,0048': ('SQ', 'BeamLimitingDeviceToleranceSequence'), \
'300a,004a': ('DS', 'BeamLimitingDevicePositionTolerance'), \
'300a,004c': ('DS', 'PatientSupportAngleTolerance'), \
'300a,004e': ('DS', 'TableTopEccentricAngleTolerance'), \
'300a,0051': ('DS', 'TableTopVerticalPositionTolerance'), \
'300a,0052': ('DS', 'TableTopLongitudinalPositionTolerance'), \
'300a,0053': ('DS', 'TableTopLateralPositionTolerance'), \
'300a,0055': ('CS', 'RTPlanRelationship'), \
'300a,0070': ('SQ', 'FractionGroupSequence'), \
'300a,0071': ('IS', 'FractionGroupNumber'), \
'300a,0078': ('IS', 'NumberofFractionsPlanned'), \
'300a,0079': ('IS', 'NumberofFractionPatternDigitsPerDay'), \
'300a,007a': ('IS', 'RepeatFractionCycleLength'), \
'300a,007b': ('LT', 'FractionPattern'), \
'300a,0080': ('IS', 'NumberofBeams'), \
'300a,0082': ('DS', 'BeamDoseSpecificationPoint'), \
'300a,0084': ('DS', 'BeamDose'), \
'300a,0086': ('DS', 'BeamMeterset'), \
'300a,00a0': ('IS', 'NumberofBrachyApplicationSetups'), \
'300a,00a2': ('DS', 'BrachyApplicationSetupDoseSpecificationPoint'), \
'300a,00a4': ('DS', 'BrachyApplicationSetupDose'), \
'300a,00b0': ('SQ', 'BeamSequence'), \
'300a,00b2': ('SH', 'TreatmentMachineName'), \
'300a,00b3': ('CS', 'PrimaryDosimeterUnit'), \
'300a,00b4': ('DS', 'SourceAxisDistance'), \
'300a,00b6': ('SQ', 'BeamLimitingDeviceSequence'), \
'300a,00b8': ('CS', 'RTBeamLimitingDeviceType'), \
'300a,00ba': ('DS', 'SourcetoBeamLimitingDeviceDistance'), \
'300a,00bc': ('IS', 'NumberofLeafJawPairs'), \
'300a,00be': ('DS', 'LeafPositionBoundaries'), \
'300a,00c0': ('IS', 'BeamNumber'), \
'300a,00c2': ('LO', 'BeamName'), \
'300a,00c3': ('ST', 'BeamDescription'), \
'300a,00c4': ('CS', 'BeamType'), \
'300a,00c6': ('CS', 'RadiationType'), \
'300a,00c7': ('CS', 'HighDoseTechniqueType'), \
'300a,00c8': ('IS', 'ReferenceImageNumber'), \
'300a,00ca': ('SQ', 'PlannedVerificationImageSequence'), \
'300a,00cc': ('LO', 'ImagingDeviceSpecificAcquisitionParameters'), \
'300a,00ce': ('CS', 'TreatmentDeliveryType'), \
'300a,00d0': ('IS', 'NumberofWedges'), \
'300a,00d1': ('SQ', 'WedgeSequence'), \
'300a,00d2': ('IS', 'WedgeNumber'), \
'300a,00d3': ('CS', 'WedgeType'), \
'300a,00d4': ('SH', 'WedgeID'), \
'300a,00d5': ('IS', 'WedgeAngle'), \
'300a,00d6': ('DS', 'WedgeFactor'), \
'300a,00d8': ('DS', 'WedgeOrientation'), \
'300a,00da': ('DS', 'SourcetoWedgeTrayDistance'), \
'300a,00e0': ('IS', 'NumberofCompensators'), \
'300a,00e1': ('SH', 'MaterialID'), \
'300a,00e2': ('DS', 'TotalCompensatorTrayFactor'), \
'300a,00e3': ('SQ', 'CompensatorSequence'), \
'300a,00e4': ('IS', 'CompensatorNumber'), \
'300a,00e5': ('SH', 'CompensatorID'), \
'300a,00e6': ('DS', 'SourcetoCompensatorTrayDistance'), \
'300a,00e7': ('IS', 'CompensatorRows'), \
'300a,00e8': ('IS', 'CompensatorColumns'), \
'300a,00e9': ('DS', 'CompensatorPixelSpacing'), \
'300a,00ea': ('DS', 'CompensatorPosition'), \
'300a,00eb': ('DS', 'CompensatorTransmissionData'), \
'300a,00ec': ('DS', 'CompensatorThicknessData'), \
'300a,00ed': ('IS', 'NumberofBoli'), \
'300a,00ee': ('CS', 'CompensatorType'), \
'300a,00f0': ('IS', 'NumberofBlocks'), \
'300a,00f2': ('DS', 'TotalBlockTrayFactor'), \
'300a,00f4': ('SQ', 'BlockSequence'), \
'300a,00f5': ('SH', 'BlockTrayID'), \
'300a,00f6': ('DS', 'SourcetoBlockTrayDistance'), \
'300a,00f8': ('CS', 'BlockType'), \
'300a,00fa': ('CS', 'BlockDivergence'), \
'300a,00fc': ('IS', 'BlockNumber'), \
'300a,00fe': ('LO', 'BlockName'), \
'300a,0100': ('DS', 'BlockThickness'), \
'300a,0102': ('DS', 'BlockTransmission'), \
'300a,0104': ('IS', 'BlockNumberofPoints'), \
'300a,0106': ('DS', 'BlockData'), \
'300a,0107': ('SQ', 'ApplicatorSequence'), \
'300a,0108': ('SH', 'ApplicatorID'), \
'300a,0109': ('CS', 'ApplicatorType'), \
'300a,010a': ('LO', 'ApplicatorDescription'), \
'300a,010c': ('DS', 'CumulativeDoseReferenceCoefficient'), \
'300a,010e': ('DS', 'FinalCumulativeMetersetWeight'), \
'300a,0110': ('IS', 'NumberofControlPoints'), \
'300a,0111': ('SQ', 'ControlPointSequence'), \
'300a,0112': ('IS', 'ControlPointIndex'), \
'300a,0114': ('DS', 'NominalBeamEnergy'), \
'300a,0115': ('DS', 'DoseRateSet'), \
'300a,0116': ('SQ', 'WedgePositionSequence'), \
'300a,0118': ('CS', 'WedgePosition'), \
'300a,011a': ('SQ', 'BeamLimitingDevicePositionSequence'), \
'300a,011c': ('DS', 'LeafJawPositions'), \
'300a,011e': ('DS', 'GantryAngle'), \
'300a,011f': ('CS', 'GantryRotationDirection'), \
'300a,0120': ('DS', 'BeamLimitingDeviceAngle'), \
'300a,0121': ('CS', 'BeamLimitingDeviceRotationDirection'), \
'300a,0122': ('DS', 'PatientSupportAngle'), \
'300a,0123': ('CS', 'PatientSupportRotationDirection'), \
'300a,0124': ('DS', 'TableTopEccentricAxisDistance'), \
'300a,0125': ('DS', 'TableTopEccentricAngle'), \
'300a,0126': ('CS', 'TableTopEccentricRotationDirection'), \
'300a,0128': ('DS', 'TableTopVerticalPosition'), \
'300a,0129': ('DS', 'TableTopLongitudinalPosition'), \
'300a,012a': ('DS', 'TableTopLateralPosition'), \
'300a,012c': ('DS', 'IsocenterPosition'), \
'300a,012e': ('DS', 'SurfaceEntryPoint'), \
'300a,0130': ('DS', 'SourcetoSurfaceDistance'), \
'300a,0134': ('DS', 'CumulativeMetersetWeight'), \
'300a,0180': ('SQ', 'PatientSetupSequence'), \
'300a,0182': ('IS', 'PatientSetupNumber'), \
'300a,0184': ('LO', 'PatientAdditionalPosition'), \
'300a,0190': ('SQ', 'FixationDeviceSequence'), \
'300a,0192': ('CS', 'FixationDeviceType'), \
'300a,0194': ('SH', 'FixationDeviceLabel'), \
'300a,0196': ('ST', 'FixationDeviceDescription'), \
'300a,0198': ('SH', 'FixationDevicePosition'), \
'300a,01a0': ('SQ', 'ShieldingDeviceSequence'), \
'300a,01a2': ('CS', 'ShieldingDeviceType'), \
'300a,01a4': ('SH', 'ShieldingDeviceLabel'), \
'300a,01a6': ('ST', 'ShieldingDeviceDescription'), \
'300a,01a8': ('SH', 'ShieldingDevicePosition'), \
'300a,01b0': ('CS', 'SetupTechnique'), \
'300a,01b2': ('ST', 'SetupTechniqueDescription'), \
'300a,01b4': ('SQ', 'SetupDeviceSequence'), \
'300a,01b6': ('CS', 'SetupDeviceType'), \
'300a,01b8': ('SH', 'SetupDeviceLabel'), \
'300a,01ba': ('ST', 'SetupDeviceDescription'), \
'300a,01bc': ('DS', 'SetupDeviceParameter'), \
'300a,01d0': ('ST', 'SetupReferenceDescription'), \
'300a,01d2': ('DS', 'TableTopVerticalSetupDisplacement'), \
'300a,01d4': ('DS', 'TableTopLongitudinalSetupDisplacement'), \
'300a,01d6': ('DS', 'TableTopLateralSetupDisplacement'), \
'300a,0200': ('CS', 'BrachyTreatmentTechnique'), \
'300a,0202': ('CS', 'BrachyTreatmentType'), \
'300a,0206': ('SQ', 'TreatmentMachineSequence'), \
'300a,0210': ('SQ', 'SourceSequence'), \
'300a,0212': ('IS', 'SourceNumber'), \
'300a,0214': ('CS', 'SourceType'), \
'300a,0216': ('LO', 'SourceManufacturer'), \
'300a,0218': ('DS', 'ActiveSourceDiameter'), \
'300a,021a': ('DS', 'ActiveSourceLength'), \
'300a,0222': ('DS', 'SourceEncapsulationNominalThickness'), \
'300a,0224': ('DS', 'SourceEncapsulationNominalTransmission'), \
'300a,0226': ('LO', 'SourceIsotopeName'), \
'300a,0228': ('DS', 'SourceIsotopeHalfLife'), \
'300a,022a': ('DS', 'ReferenceAirKermaRate'), \
'300a,022c': ('DA', 'AirKermaRateReferenceDate'), \
'300a,022e': ('TM', 'AirKermaRateReferenceTime'), \
'300a,0230': ('SQ', 'ApplicationSetupSequence'), \
'300a,0232': ('CS', 'ApplicationSetupType'), \
'300a,0234': ('IS', 'ApplicationSetupNumber'), \
'300a,0236': ('LO', 'ApplicationSetupName'), \
'300a,0238': ('LO', 'ApplicationSetupManufacturer'), \
'300a,0240': ('IS', 'TemplateNumber'), \
'300a,0242': ('SH', 'TemplateType'), \
'300a,0244': ('LO', 'TemplateName'), \
'300a,0250': ('DS', 'TotalReferenceAirKerma'), \
'300a,0260': ('SQ', 'BrachyAccessoryDeviceSequence'), \
'300a,0262': ('IS', 'BrachyAccessoryDeviceNumber'), \
'300a,0263': ('SH', 'BrachyAccessoryDeviceID'), \
'300a,0264': ('CS', 'BrachyAccessoryDeviceType'), \
'300a,0266': ('LO', 'BrachyAccessoryDeviceName'), \
'300a,026a': ('DS', 'BrachyAccessoryDeviceNominalThickness'), \
'300a,026c': ('DS', 'BrachyAccessoryDeviceNominalTransmission'), \
'300a,0280': ('SQ', 'ChannelSequence'), \
'300a,0282': ('IS', 'ChannelNumber'), \
'300a,0284': ('DS', 'ChannelLength'), \
'300a,0286': ('DS', 'ChannelTotalTime'), \
'300a,0288': ('CS', 'SourceMovementType'), \
'300a,028a': ('IS', 'NumberofPulses'), \
'300a,028c': ('DS', 'PulseRepetitionInterval'), \
'300a,0290': ('IS', 'SourceApplicatorNumber'), \
'300a,0291': ('SH', 'SourceApplicatorID'), \
'300a,0292': ('CS', 'SourceApplicatorType'), \
'300a,0294': ('LO', 'SourceApplicatorName'), \
'300a,0296': ('DS', 'SourceApplicatorLength'), \
'300a,0298': ('LO', 'SourceApplicatorManufacturer'), \
'300a,029c': ('DS', 'SourceApplicatorWallNominalThickness'), \
'300a,029e': ('DS', 'SourceApplicatorWallNominalTransmission'), \
'300a,02a0': ('DS', 'SourceApplicatorStepSize'), \
'300a,02a2': ('IS', 'TransferTubeNumber'), \
'300a,02a4': ('DS', 'TransferTubeLength'), \
'300a,02b0': ('SQ', 'ChannelShieldSequence'), \
'300a,02b2': ('IS', 'ChannelShieldNumber'), \
'300a,02b3': ('SH', 'ChannelShieldID'), \
'300a,02b4': ('LO', 'ChannelShieldName'), \
'300a,02b8': ('DS', 'ChannelShieldNominalThickness'), \
'300a,02ba': ('DS', 'ChannelShieldNominalTransmission'), \
'300a,02c8': ('DS', 'FinalCumulativeTimeWeight'), \
'300a,02d0': ('SQ', 'BrachyControlPointSequence'), \
'300a,02d2': ('DS', 'ControlPointRelativePosition'), \
'300a,02d4': ('DS', 'ControlPoint3DPosition'), \
'300a,02d6': ('DS', 'CumulativeTimeWeight'), \
'300c,0002': ('SQ', 'ReferencedRTPlanSequence'), \
'300c,0004': ('SQ', 'ReferencedBeamSequence'), \
'300c,0006': ('IS', 'ReferencedBeamNumber'), \
'300c,0007': ('IS', 'ReferencedReferenceImageNumber'), \
'300c,0008': ('DS', 'StartCumulativeMetersetWeight'), \
'300c,0009': ('DS', 'EndCumulativeMetersetWeight'), \
'300c,000a': ('SQ', 'ReferencedBrachyApplicationSetupSequence'), \
'300c,000c': ('IS', 'ReferencedBrachyApplicationSetupNumber'), \
'300c,000e': ('IS', 'ReferencedSourceNumber'), \
'300c,0020': ('SQ', 'ReferencedFractionGroupSequence'), \
'300c,0022': ('IS', 'ReferencedFractionGroupNumber'), \
'300c,0040': ('SQ', 'ReferencedVerificationImageSequence'), \
'300c,0042': ('SQ', 'ReferencedReferenceImageSequence'), \
'300c,0050': ('SQ', 'ReferencedDoseReferenceSequence'), \
'300c,0051': ('IS', 'ReferencedDoseReferenceNumber'), \
'300c,0055': ('SQ', 'BrachyReferencedDoseReferenceSequence'), \
'300c,0060': ('SQ', 'ReferencedStructureSetSequence'), \
'300c,006a': ('IS', 'ReferencedPatientSetupNumber'), \
'300c,0080': ('SQ', 'ReferencedDoseSequence'), \
'300c,00a0': ('IS', 'ReferencedToleranceTableNumber'), \
'300c,00b0': ('SQ', 'ReferencedBolusSequence'), \
'300c,00c0': ('IS', 'ReferencedWedgeNumber'), \
'300c,00d0': ('IS', 'ReferencedCompensatorNumber'), \
'300c,00e0': ('IS', 'ReferencedBlockNumber'), \
'300c,00f0': ('IS', 'ReferencedControlPointIndex'), \
'300e,0002': ('CS', 'ApprovalStatus'), \
'300e,0004': ('DA', 'ReviewDate'), \
'300e,0005': ('TM', 'ReviewTime'), \
'300e,0008': ('PN', 'ReviewerName'), \
'4000,0000': ('UL', 'Group4000Length'), \
'4000,0010': ('SH', 'Arbitray'), \
'4000,4000': ('LT', 'Group4000Comments'), \
'4008,0000': ('UL', 'Group4008Length'), \
'4008,0040': ('SH', 'ResultsId'), \
'4008,0042': ('LO', 'ResultsIdIssuer'), \
'4008,0050': ('SQ', 'ReferencedInterpretationSequence'), \
'4008,0100': ('DA', 'InterpretationRecordedDate'), \
'4008,0101': ('TM', 'InterpretationRecordedTime'), \
'4008,0102': ('PN', 'InterpretationRecorder'), \
'4008,0103': ('LO', 'ReferenceToRecordedSound'), \
'4008,0108': ('DA', 'InterpretationTranscriptionTime'), \
'4008,0109': ('TM', 'InterpretationTranscriptionTime'), \
'4008,010a': ('PN', 'InterpretationTranscriber'), \
'4008,010b': ('ST', 'InterpretationText'), \
'4008,010c': ('PN', 'InterpretationAuthor'), \
'4008,0111': ('SQ', 'InterpretationApproverSequence'), \
'4008,0112': ('DA', 'InterpretationApprovalDate'), \
'4008,0113': ('TM', 'InterpretationApprovalTime'), \
'4008,0114': ('PN', 'PhysicianApprovingInterpretation'), \
'4008,0115': ('LT', 'InterpretationDiagnosisDescription'), \
'4008,0117': ('SQ', 'DiagnosisCodeSequence'), \
'4008,0118': ('SQ', 'ResultsDistributionListSequence'), \
'4008,0119': ('PN', 'DistributionName'), \
'4008,011a': ('LO', 'DistributionAddress'), \
'4008,0200': ('SH', 'InterpretationId'), \
'4008,0202': ('LO', 'InterpretationIdIssuer'), \
'4008,0210': ('CS', 'InterpretationTypeId'), \
'4008,0212': ('CS', 'InterpretationStatusId'), \
'4008,0300': ('ST', 'Impression'), \
'4008,4000': ('SH', 'Group4008Comments'), \
'4ffe,0001': ('SQ', 'MACParametersSequence'), \
'5000,0000': ('UL', 'Group5000Length'), \
'5000,0005': ('US', 'CurveDimensions'), \
'5000,0010': ('US', 'NumberOfPoints'), \
'5000,0020': ('CS', 'TypeOfData'), \
'5000,0022': ('LO', 'CurveDescription'), \
'5000,0030': ('SH', 'AxisUnits'), \
'5000,0040': ('SH', 'AxisLabels'), \
'5000,0103': ('US', 'DataValueRepresentation'), \
'5000,0104': ('US', 'MinimumCoordinateValue'), \
'5000,0105': ('US', 'MaximumCoordinateValue'), \
'5000,0106': ('SH', 'CurveRange'), \
'5000,0110': ('US', 'CurveDataDescriptor'), \
'5000,0112': ('US', 'CoordinateStartValue'), \
'5000,0114': ('US', 'CoordinateStepValue'), \
'5000,2000': ('US', 'AudioType'), \
'5000,2002': ('US', 'AudioSampleFormat'), \
'5000,2004': ('US', 'NumberOfChannels'), \
'5000,2006': ('UL', 'NumberOfSamples'), \
'5000,2008': ('UL', 'SampleRate'), \
'5000,200a': ('UL', 'TotalTime'), \
'5000,200c': ('OX', 'AudioSampleData'), \
'5000,200e': ('LT', 'AudioComments'), \
'5000,3000': ('OX', 'CurveData'), \
'5400,0100': ('SQ', 'WaveformSequence'), \
'5400,0110': ('[OB, OW]', 'ChannelMinimumValue'), \
'5400,0112': ('[OB, OW]', 'ChannelMaximumValue'), \
'5400,1004': ('US', 'WaveformBitsAllocated'), \
'5400,1006': ('CS', 'WaveformSampleInterpretation'), \
'5400,100a': ('[OB, OW]', 'WaveformPaddingValue'), \
'5400,1010': ('[OB, OW]', 'WaveformData'), \
'6000,0000': ('UL', 'Group6000Length'), \
'6000,0010': ('US', 'Rows'), \
'6000,0011': ('US', 'Columns'), \
'6000,0015': ('IS', 'NumberOfFramesInOverlay'), \
'6000,0040': ('CS', 'OverlayType'), \
'6000,0050': ('SS', 'Origin'), \
'6000,0060': ('SH', 'CompressionCode'), \
'0028,0100': ('US', 'BitsAllocated'), \
'6000,0102': ('US', 'BitPosition'), \
'6000,0110': ('SH', 'OverlayFormat'), \
'6000,0200': ('US', 'OverlayLocation'), \
'6000,1100': ('US', 'OverlayDescriptorGray'), \
'6000,1101': ('US', 'OverlayDescriptorRed'), \
'6000,1102': ('US', 'OverlayDescriptorGreen'), \
'6000,1103': ('US', 'OverlayDescriptorBlue'), \
'6000,1200': ('US', 'OverlaysGray'), \
'6000,1201': ('US', 'OverlaysRed'), \
'6000,1202': ('US', 'OverlaysGreen'), \
'6000,1203': ('US', 'OverlaysBlue'), \
'6000,1301': ('IS', 'RoiArea'), \
'6000,1302': ('DS', 'RoiMean'), \
'6000,1303': ('DS', 'RoiStandardDeviation'), \
'6000,3000': ('OW', 'OverlayData'), \
'6000,4000': ('SH', 'Group6000Comments'), \
'7fe0,0000': ('UL', 'GroupLength'), \
'7fe0,0010': ('OX', 'PixelData'), \
'7fe1,1010': ('OB', 'CSAData'), \
'fffa,fffa': ('SQ', 'DigitalSignaturesSequence'), \
'fffc,fffc': ('OB', 'DataSetTrailingPadding'), \
'fffe,e000': ('SQ', 'Item'), \
'fffe,e00d': ('DL', 'ItemDelimitationItem'), \
'fffe,e0dd': ('DL', 'SequenceDelimitationItem')}


if __name__ == '__main__':
    sys.stdout.write('%s\n' % ID)