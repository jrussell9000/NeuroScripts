#!/usr/bin/env python

ID = "$Id: wisc_dicom.py 675 2012-08-02 19:33:19Z vack $"[1:-1]

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
        sign, dot, cross, put, identity, empty, argmax, byte, logical_and, \
        equal, logical_xor
import struct
from wbl_util import except_msg, Timer, Translate
#from math_bic import print_matrix
import bz2
import gzip
import zlib
import string
from datetime import datetime
import tarfile
import dicom as dc
from dicom import filereader
from cStringIO import StringIO

ID = "$Id: wisc_dicom.py 675 2012-08-02 19:33:19Z vack $"[1:-1]


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

hdrkeys = [('imagetime', (0x0008,0x0033)), \
    ('ReconstructionDiameter', (0x0018,0x1100)), \
    ('Rows', (0x0028,0x0010)), \
    ('Columns', (0x0028,0x0011)), \
    ('LocationsInAcquisition', (0x0021,0x104f)), \
    ('PixelSpacing', (0x0028,0x0030)), \
    ('SliceThickness', (0x0018,0x0050)), \
    ('SpacingBetweenSlices', (0x0018,0x0088)),  \
#    ('NumberPhaseEncodes', (0x0018,0x0089)), \ JMO 1/4/11
    ('RepetitionTime', (0x0018,0x0080)), \
    ('TriggerTime', (0x0018,0x1060)), \
    ('SmallestImagePixelValue', (0x0028,0x0106)), \
    ('LargestImagePixelValue', (0x0028,0x0107)), \
    ('SeriesPlane', (0x0019,0x1017)), \
    ('FirstScanRas', (0x0019,0x1018)), \
    ('FirstScanLocation', (0x0019,0x1019)), \
    ('PulseSequenceMode', (0x0019,0x109b)), \
    ('ImagesInSeries', (0x0025,0x1007)), \
    ('PulseSequence', (0x0027,0x1032)), \
    ('GEImagingMode', (0x0027,0x1031)), \
    ('ImageDimensionX', (0x0027,0x1060)), \
    ('ImageDimensionY', (0x0027,0x1061)), \
    ('BitsStored', (0x0028,0x0101)), \
    ('SeriesDescription', (0x0008,0x103e)), \
    ('PlaneType', (0x0027,0x1035)), \
    ('InstanceNumber', (0x0020,0x0013)), \
    ('InstitutionName', (0x0008,0x0080)), \
    ('LastScanRas', (0x0019,0x101a)), \
    ('LastScanLocation', (0x0019,0x101b)), \
    ('ImagePosition', (0x0020,0x0032)), \
    ('AcquisitionGroupLength', (0x0018,0x0000)), \
    ('RawDataRunNumber', (0x0019,0x10a2)), \
    ('ImageOrientation', (0x0020,0x0037)), \
    ('ProtocolName', (0x0018,0x1030)), \
    ('SeriesDescription', (0x0008,0x103e)), \
    ('StudyDate', (0x0008,0x0020)), \
    ('StudyID', (0x0020,0x0010)), \
    ('StudyDescription', (0x0008,0x1030)), \
    ('PatientId', (0x0010,0x0020)), \
    ('PatientBirthDate', (0x0010,0x0030)), \
    ('PatientPosition', (0x0018,0x5100)), \
    ('AcquisitionMatrix', (0x0018,0x1310)), \
    ('AcquisitionTime', (0x0008,0x0032)), \
    ('SeriesTime', (0x0008,0x0031)), \
    ('ImagesInAcquisition', (0x0020,0x1002)), \
    ('ImageFormat', (0x0008,0x0008)), \
    ('SliceLocation', (0x0020,0x1041)), \
    ('PatientAge', (0x0010,0x1010)), \
    ('PatientWeight', (0x0010,0x1030)), \
    ('PatientSex', (0x0010,0x0040)), \
    ('PatientAge', (0x0010,0x1010)), \
    ('PatientWeight', (0x0010,0x1030)), \
    ('PatientName', (0x0010,0x0010)), \
    ('OperatorName', (0x0008,0x1070)), \
    ('ImageDimensionX', (0x0027,0x1060)), \
    ('ImageDimensionY', (0x0027,0x1061)), \
    ('SeriesNumber', (0x0020,0x0011)), \
    ('SeriesNumber', (0x0020,0x0011)), \
    ('ActualSeriesDateTime', (0x0009,0x10e9)), \
    ('ImageActualDate', (0x0009,0x1027)), \
    ('AcquisitionNumber', (0x0020,0x0012)), \
    ('Transmit Coil Name', (0x0019,0x109f)), \
    ('Manufacturer', (0x0008,0x0070)), \
    ('BitsStored', (0x0028,0x0101)), \
    ('BitsAllocated', (0x0028,0x0100)), \
#    ('TransferSyntax', (0xTransferSyntax)), \
    ('ImageType', (0x0008,0x0008)), \
    ('ImagingMode', (0x0018,0x0023)), \
    ('HighBit', (0x0028,0x0102)), \
#    ('InstitutionAddress', (0x0008,0x0081)), \ JMO 1/3/11
    ('ManufacturersModel', (0x0008,0x1090)), \
    ('SoftwareVersion', (0x0018,0x1020)),  \
    ('RequestingPhysician', (0x0008,0x0090)), \
    ('PixelRepresentation', (0x0028,0x0103)), \
    ('ImageLengthBytes', (0x7fe0,0x0000)), \
    ('AnalogReceiverGain', (0x0019,0x1095)), \
    ('DigitalReceiverGain', (0x0019,0x1096)), \
    ('ActualReceiveGainAnalog', (0x0019,0x108a)), \
    ('ActualReceiveGainDigital', (0x0019,0x108b)), \
    ('SwapPhaseFrequency', (0x0019,0x108f)), \
    ('PauseInterval', (0x0019,0x1090)), \
    ('PulseTime', (0x0019,0x1091)), \
    ('SliceOffsetOnFrequencyAxis', (0x0019,0x1092)), \
    ('CenterFrequency', (0x0019,0x1093)), \
    ('TransmitGain', (0x0019,0x1094)), \
    ('ActualTransmitGain', (0x0019,0x10f9)), \
    ('Modality', (0x0008,0x0060))]

pet_hdrkeys = [ \
    ('RescaleIntercept', (0x0028,0x1052)), \
    ('RescaleSlope', (0x0028,0x1053)), \
    ('TracerName', (0x0009,0x1036)), \
    ('RadioNuclideName', (0x0009,0x103e)), \
    ('ActualFrameDuration', (0x0018,0x1242)), \
    ('FrameReferenceTime', (0x0054,0x1300)), \
    ('SliceSensitivityFactor', (0x0054,0x1320)), \
    ('DecayFactor', (0x0054,0x1321)), \
    ('DeadTimeFactor', (0x0054,0x1324)), \
    ('DoseCalibrationFactor', (0x0054,0x1322))]

mri_hdrkeys = [ \
    ('FlipAngle', (0x0018,0x1314)), \
    ('EchoTime', (0x0018,0x0081)), \
    ('InversionTime', (0x0018,0x0082)), \
    ('NumberOfExcitations', (0x0027,0x1062)), \
    ('EchoTrainLength', (0x0018,0x0091)), \
    ('DisplayFieldOfView', (0x0019,0x101e)), \
    ('EchoNumber', (0x0018,0x0086)), \
    ('ReceiveCoilName', (0x0018,0x1250)), \
    ('EffEchoSpacing', (0x0043,0x102c)), \
    ('NumberOfAverages', (0x0018,0x0083)), \
    ('ScanningSequence', (0x0018,0x0020)), \
    ('GEImageType', (0x0043,0x102f)), \
    ('PixelBandwidth', (0x0018,0x0095)), \
    ('EchoNumber', (0x0018,0x0086)), \
    ('NumberOfEchos', (0x0019,0x107e)), \
    ('SecondEcho', (0x0019,0x107d)), \
    ('PhaseEncDir', (0x0018,0x1312)), \
    ('SwapPhaseFrequency', (0x0019,0x108f)), \
    ('PulseSequence', (0x0027,0x1032)), \
    ('PulseSequenceName', (0x0019,0x109c)), \
    ('InternalPulseSequenceName', (0x0019,0x109e)), \
    ('PulseSequenceDate', (0x0019,0x109d)), \
    ('AnalogRcvrGain', (0x0019,0x1095)), \
    ('DigitalRcvrGain', (0x0019,0x1096)), \
    ('EchoNumber', (0x0018,0x0086)), \
    ('SequenceVariant', (0x0018,0x0021)), \
    ('NumberOfAverages', (0x0018,0x0083)), \
    ('ScanOptions', (0x0018,0x0022)), \
    ('FieldStrength', (0x0018,0x0087)), \
    ('SequenceName', (0x0018,0x0024)), \
    ('SAR', (0x0018,0x1316)), \
    ('VariableFlipAngleFlag', (0x0018,0x1315)),  \
    ('PercentPhaseFieldOfView', (0x0018,0x0094)), \
    ('FastPhases', (0x0019,0x10f2)), \
#    ('DummyScans', (0x0043,0x1076)), \
#    ('DerivedClass', (0x0051,0x1001)), \ JMO 1/3/11
#    ('DerivedType', (0x0051,0x1002)), \ JMO 1/3/11
#    ('DerivedParam1', (0x0051,0x1003)), \ JMO 1/3/11
#    ('DerivedParam2', (0x0051,0x1004)), \ JMO 1/3/11
#    ('NumDirections', (0x0051,0x1005)), \ JMO 1/3/11
#    ('BValue', (0x0051,0x100b)), \ JMO 1/3/11
    ('DiffusionDir0', (0x0021,0x105a)), \
    ('DiffusionDir1', (0x0019,0x10d9)), \
    ('DiffusionDir2', (0x0019,0x10df)), \
    ('DiffusionDir3', (0x0019,0x10e0)), \
    ('ImagingOptions', (0x0027,0x1033)), \
    ('UserData0', (0x0019,0x10a7)), \
    ('UserData1', (0x0019,0x10a8)), \
    ('UserData2', (0x0019,0x10a9)), \
    ('UserData3', (0x0019,0x10aa)), \
    ('UserData4', (0x0019,0x10ab)), \
    ('UserData5', (0x0019,0x10ac)), \
    ('UserData6', (0x0019,0x10ad)), \
    ('UserData7', (0x0019,0x10ae)), \
    ('UserData8', (0x0019,0x10af)), \
    ('UserData9', (0x0019,0x10b0)), \
    ('UserData10', (0x0019,0x10b1)), \
    ('UserData11', (0x0019,0x10b2)), \
    ('UserData12', (0x0019,0x10b3)), \
    ('UserData13', (0x0019,0x10b4)), \
    ('UserData14', (0x0019,0x10b5)), \
    ('UserData15', (0x0019,0x10b6)), \
    ('UserData16', (0x0019,0x10b7)), \
    ('UserData17', (0x0019,0x10b8)), \
    ('UserData18', (0x0019,0x10b9)), \
    ('UserData19', (0x0019,0x10ba)), \
    ('UserData20', (0x0019,0x10bb)), \
    ('UserData21', (0x0019,0x10bc)), \
    ('UserData22', (0x0019,0x10bd)), \
    ('Number3DSlabs', (0x0021,0x1056)), \
    ('LocsPerSlab', (0x0021,0x1057)), \
    ('Overlaps', (0x0021,0x1058)), \
    ('MosaicMatrixSize', (0x0051,0x100b)), \
    ('MosaicNumberImages', (0x0019,0x100a)), \
    ('AcquisitionDuration', (0x0019,0x105a)) 
#    ('MosaicMatrixSize', (0x0051,0x100b)), \ JMO 1/3/11
#    ('BValueDiffusionWeighting', (0x0019,0x100c)), \ JMO 1/3/11
#    ('DiffusionGradientDirection', (0x0019,0x100e)), \ JMO 1/3/11
#    ('DiffusionMatrix', (0x0019,0x1027') JMO 1/3/11
    ]
    
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
        for i in xrange(3):
            path = fullpath + ['','.bz2', '.gz'][i]
            if os.path.exists(path):
                break
        else:
            return None
    f = apply( open_funcs[i], (path, 'r'))

    if f is None:
        raise IOError('open_gzbz2: Could not open: %s\n' % file1)
    else:
        return f

class DicomTar():
    """
    Directly access dicom files stored in an uncompressed tar file.  It is assumed that the tar file contains one DICOM series.
    """

    def __init__(self, tarname):
        """
        Open archive. Determine compression type, test if members are dicom files.
        Assumes that filenames follow the convention <stem>.nnnn.<compression type> where 
        <stem> is the stem extracted from the input filename.
        nnnnn is the InstanceNumber with leading zeros, and <compression type> is .gz, .bz2, or ""
        """
        try:
            self.tar = tarfile.open(tarname, 'r')
        except tarfile.ReadError:
            self.isTar = False
            return
        self.mbrs = self.tar.getmembers()
        for mbr in self.mbrs:
            if mbr.name[-4].isdigit():
                self._MemberTraits(mbr.name, -0, '')
                break
            elif  mbr.name[-8:-4].isdigit()  and mbr.name[-4:] == '.bz2':
                self._MemberTraits(mbr.name, -4, '.bz2')
                break
            elif  mbr.name[-8:-4].isdigit()  and mbr.name[-3:] == '.gz':
                self._MemberTraits(mbr.name, -4, '.gz')
                break

        data0 = self.GetSlice(slice_id=1)

        if data0[128:132] == "DICM":
            self.isTar = True
        else:
            self.isTar =  False

    def _MemberTraits(self, mbrname, iend, compress):
        """
        Determine file basename (less extension) and type of compression. 
        """
        nsuff = 3
        N = len(mbrname)
        while True:
            if not mbrname[N+iend-nsuff:N+iend].isdigit():
                self.nsuff = nsuff - 1
                break
            else:
                nsuff += 1
        self.fmt = '%%s.%%0%dd%%s' % self.nsuff
        self.compress = compress
        self.stem = mbrname[:iend-self.nsuff-1]

    def GetNames(self):
        """
        Get names of members of the archive
        """
        return self.tar.getnames()

    def GetSlice(self, mbrname=None, slice_id=None, nbytes=None):
        """
        Return slice with suffix "slice_id", e.g., <stem>.0002[.bz2]
        """
        # print(mbrname)
        # print(slice_id)
        if slice_id is not None:
            mbrname = self.fmt % (self.stem, slice_id, self.compress)
        if not mbrname.endswith(self.compress):
            mbrname += self.compress
        try:
            # print(mbrname)
            data = self.tar.extractfile(mbrname).read()
        except KeyError:
            data = self.tar.extractfile(mbrname.replace('.bz2','').\
                                                    replace('.gz','')).read()
        if self.compress == '.bz2':
            if nbytes is None:
#                x =  bz2.decompress(data)
                return  bz2.decompress(data)   
            else:
                bz = bz2.BZ2Decompressor()
                data = ''
                i = 0
                while len(data) < nbytes:
                    data +=  bz.decompress(data[i*nbytes:(i+1)*nbytes])
                    i += 1
                return(data[:nbytes])

        elif self.compress == '.gz':
            if nbytes is None:
                return zlib.decompress(data)
            else:
                return zlib.decompress(data, nbytes)
        else:
            return data

    def Close(self):
        self.tar.close()
    

##***********************
#def get_exam_list(exam):
##***********************
#
#    """
#    Purpose: Search for dicom files in GE's database and find out 
#    what is in them.
#    """
#
##    Get list of study directories.
#    top = '/export/home1/sdc_image_pool/images'
#    topdirs = os.listdir(top)
#    exampaths = []
#    for dr in topdirs:
#        subdir = "%s/%s" % (top, dr)
#        examdirs = os.listdir(subdir)
#        for examdir in examdirs:
#            if examdir[:4] != 'core':
#                exampaths.append("%s/%s" % (subdir, examdir))
#
#    exam_info = []
#    examm1 = ""
#    exams = []
#    for exampath in exampaths:
#        examseries = os.listdir(exampath)
##       Loop over each series in the exam
#        for series in examseries:
#            seriespath = "%s/%s" % (exampath, series)
#            slices = os.listdir(seriespath)
#            if len(slices) > 0:
##               Read the header from the first slice to get the exam number.
#                filename = '%s/%s'% (seriespath, slices[0])
#                hdr = read_ge_dicom_header(filename)
#                examno = hdr['exam']
#                if exam == 0 or examno == exam:
#                    if examno != examm1:
##                       This is a new exam.
#                        exams.append(examno)
#                    exam_info.append((examno, seriespath, slices[0]))
#            examm1 = examno
##        if examno != exam:
##            break
#    return(exams, exam_info)

class IsDicom():
    """
    Test if a file is in DICOM format. Relevent attributes are:
    isdicom: True if members are in dicom format
    isdir: True if dicom member is a directory containing a series rather than a single file.
    istar: True if the dicom files are stored in a tar archive.
    """
    def __init__(self, fname):
        if os.path.basename(fname).startswith('.'):
#           Skip resource forks on OSX systems.
            self.isdicom =  False
            self.isdir = False
            self.istar = False
            self.fname = None
            return
        elif fname.endswith('.dcm'):
            self.isdicom =  True
            self.isdir = False
            self.istar = False
            self.fname = fname
            return 
        elif os.path.isdir(fname):
            dname = fname
            self.isdir = True
            try:
                fnames = os.listdir(fname)
            except:
                self.isdicom = False
                self.istar = False
                return
        else:
            dname = ''
            fnames = [fname]
            self.isdir = False

        self.fname = None
        for fname in fnames:
            infile = os.path.join(dname, fname)
            try:
                if fname.endswith('.tar'):
                    self.tarobj = DicomTar(infile)
                    self.isdicom = self.tarobj.isTar
                    self.istar =  self.tarobj.isTar
                    if self.istar:
                        self.isfile = False
                        self.isdir = False
                    self.fname = fname
                    break
                else:
                    f = open_gzbz2(infile, 'r')
                    if f is None:
                        continue
                    f.seek(128)
                    dicm_code = f.read(4)
                    f.close()
                    if dicm_code == "DICM":
                        self.isdicom = True
                        self.istar = False
                        self.fname = fname
                        return
            except (IOError, OSError):
                 continue
        else:
            self.isdicom= False
            self.isdir = False
            self.isfile = False
            self.istar = False

    def __call__(self):
        return self.isdicom


#******************
def isdicom(fname):
#******************

    """
    Determine if a file is in dicom format. 
    Return: True or False
    """

    if os.path.basename(fname).startswith('.'):
        return False
    if fname.endswith('.dcm') and not os.path.basename(fname).startswith('.'):
        return True

    if os.path.isdir(fname):
        return False
    else:
        if fname.endswith('.tar'):
            dt = DicomTar(fname)
            return dt.isTar
        else:
            f = open_gzbz2(fname, 'r') #XXXX
            if f is None:
                return False
            f.seek(128)
            dicm_code = f.read(4)
            f.close()
            if dicm_code == "DICM":
                return True
            else:
                return False

class Dicom():
    """
    Purpose: Provide high level interface to dicom header and image.
    Public methods: 
    """
    def __init__(self, filename=None, nhdr=None, data=None, scan=False):
        """
        Purpose: Read header on initialization and save data.
        Inputs: filename, the name directory for file containing the data.
        """
        self.tarobj = None
        self.data = None
        self.scanned = False
        self.nhdr = None
        if data is not None:
            fname = filename
            self.nfiles = 1
            self.data = data
            filename = None
            self.dirname = None
        elif not filename:
            raise RuntimeError( \
            'Neither filename nor data were present while creating Dicom object.')
        else:
#           Look for a tarfile containing the individual slices.
#            if os.path.isdir(filename):
            isd = IsDicom(filename)
            if not isd.isdicom:
                raise RuntimeError('Invalid dicom file: %s' % filename)
            elif isd.isdir:
                fname = self.CheckDirectory(filename)
            elif isd.istar:
                self.tarobj = isd.tarobj
                self.dirname = ''
                fname = None
            else:
                fname = os.path.abspath(filename)
                self.dirname = os.path.dirname(fname)
            
        self.filename = filename

#       Create a Dicom object
        if data is not None:
            dataset = self._DicomHeader(data=data)
        elif self.tarobj is not None:
            dataset = self._DicomHeader(data=self.tarobj.GetSlice(slice_id=1))
        else:
            dataset = self._DicomHeader(fname=fname)

        if dataset is None:
            raise RuntimeError( \
                        '_DicomHeader: Could not parse header, %s\n' % fname)
            return None

        if nhdr is None:
            self.dicominfo = None
            self.nhdr = self._GetNativeHeader(dataset, scan=scan)
        else:
            self.nhdr = nhdr
            self.dicominfo = self.nhdr.get('DicomInfo', None)
            if self.dicominfo is not None:
                self.nhdr['LocationsInAcquisition'] = self.dicominfo['dims']['zdim']

        if self.dicominfo is not None:
            self.scanned = True
        else:
            self.scanned = False

        self.filename = filename

    def CheckDirectory(self, dname):
        """
        Return True if <dname> is a directory containing at least one dicom file.
        """
        self.dirname = dname
        files = os.listdir(self.dirname)
        files.sort()
        self.nfiles = len(files)
        for f in files: 
            fname = "%s/%s" % (dname, f)
            if os.path.isdir(fname):
                continue
            elif fname.endswith('.yaml'):
                continue
            elif os.path.basename(fname).startswith('.'):
#               Resource fork file under osx
                continue
            elif fname.endswith('.bz2') or isdicom(fname):
                break
            try:
#               See if it's a tarfile.
                self.tarobj = DicomTar(fname)
                if not self.tarobj.isTar:
                    self.tarobj = None
                    fname = None
                    continue
                
                    break
            except: continue
        return fname

    def _DicomHeader(self, fname=None, data=None):
        """
        Create a dicom object using the pydicom module.
        """

        if data is None and isinstance(fname, str):
            f = open_gzbz2(fname, 'r')
        elif isinstance(data, str):
            f = StringIO(data)
        else:
            raise RuntimeError('Filename (%s) and data are invalid.' % fname)
        try:
            dataset = dc.read_file(f, stop_before_pixels=False)
            x = dataset.pixel_array
        except filereader.InvalidDicomError, errmsg:
            if fname is None:
                raise IOError('Invalid dicom file: None\n%s\n%s\n' % \
                                                (errmsg, ' '.join(sys.argv)))
            else:
                raise IOError('Invalid dicom file: %s\n%s\n' % (fname, errmsg))
#       Get rid of the image data to prevent huge memory cost.
        f.close()
        return dataset

  #  def get_value(self, dataset, tag, default=None):
  #      if dataset.has_key(tag):
  #          x = dataset[tag]
  #          return (x.VR, 0, x.value)
  #      else:
# #           print 'Tag not found: (%04x, %04x)' % (tag[0], tag[1])
  #          return (0, 0, default)

    def Anonymize(self, output_dir=None):
        """
        Remove patient name and birthdate (except the year) from the header.
        If output_dir is provided, the input image will be left
        unchanged and the anonymized version will be written to
        output_dir.
        This can also be done using the _ScanInfo method.
        """
        if self.tarobj is not None:
            raise RuntimeError('Anonymize method does not support tar dicom format.')
        fnames = os.listdir(self.dirname)
        for fname in fnames:
            if fname.endswith('.gz') or fname.endswith('.bz2'):
                return 1
            fullname = '%s/%s' % (self.dirname, fname)
            ds = self._DicomHeader(fullname)
            pntag = ds[(0x0010, 0x0010)]
            pn = pntag.value
            pnlgth = len(pn)
            pnoff = pntag.file_tell
            
#            pnlgth = self.pn_tag['length']
#            pnoff = self.pn_tag['offset']
            newtag = self.PatientNameTranslation(pn) #self.data[pnoff:pnoff+pnlgth])

            f = open(fullname, 'r+') #XXXX
            f.seek(pnoff)
            f.write(newtag)

            bdtag = ds[(0x0010, 0x0010)]
            bd = bdtag.value
            bdlgth = len(bd)
            bdoff = bdtag.file_tell
#            bdlgth = self.pbd_tag['length']
#            bdoff = self.pbd_tag['offset']
            newbd = self.PatientBirthDateTranslate(bd)
#                                        self.data[bdoff:bdoff+bdlgth])
            f.seek(bdoff)
            f.write(newbd)
            f.close()
        return 0
        
    def get_slice_fast(self, start_image, fullpath):
        """
        Read a single dicom slice.
        nhdr: Native dicom header (read with scan=true)
        start_image: Beginning of binary data in bytes.
        fullpath: Fully qualified path to the file.
        """

        if self.tarobj is None:
#            if isdicom(fullpath):
#                continue
            if os.path.exists(fullpath):
                f = open_gzbz2(fullpath, 'r') #XXXX
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
        else:
            imgdata = self.tarobj.GetSlice(os.path.basename(fullpath))
            f = StringIO(imgdata)
        dataset = dc.read_file(f)
        f.close()
       # return dataset.pixel_array
        if  hasattr(dataset, 'pixel_array'):
            return dataset.pixel_array
        else:
            raise RuntimeError('Dicom file contains no data: %s' % fullpath)

    def get_series(self, dname=None, dtype=None, frame=None, mtype=None):
        """
        Read a dicom series for the specified directory.
        dname: Directory containing the data. Default is value specified at init
        dtype: Data type of output array.
        frame: Single frame to be read.
        mtype: Single type to be read (type is the fifth dimension).
        """

        if dtype is None:
            dtype = int16
        if dname is not None:
            self.dirname = dname

        if self.nhdr is None:
            sys.stderr.write( \
                '\nread_dicom_file: Could not read header from %s\n\n'%filename)
            return None


        dims = self.dicominfo['dims']
        dirname = dims['dirname']
        if len(dirname) > 0:
            dirname = '%s/' % dirname

#        if self.modality == 'MR':
        if self.nhdr['Modality'] == 'MR':
            self.nhdr['EchoTimes'] = dims['EchoTimes']
            self.nhdr['FlipAngles'] = dims.get('FlipAngles', [])

        if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
            self.mosaic = True
        else:
            self.mosaic = False
        xdim = self.nhdr['Columns']
        ydim = self.nhdr['Rows']
        self.rows_mosaic = self.nhdr.get('RowsMosaic',ydim)
        self.cols_mosaic = self.nhdr.get('ColsMosaic',xdim)

        zdim = self.nhdr['LocationsInAcquisition']
        if frame is None:
            tdim = dims['tdim']
        else:
            tdim = 1
        if mtype < 0:
            mdim = dims['TypeDim']
        else:
            mdim = 1
        if frame > -1:
            frames = [frame]
            frm0 = frame
        else:
            frames = range(dims['tdim'])
            frm0 = 0

        if mtype < 0:
            mtypes = range(dims['TypeDim'])
        else:
            mtypes = [mtype]

        self.image = zeros([mdim, tdim, zdim, ydim, xdim], dtype)

        if mdim  > 1:
            self.nhdr['ndim'] = 5
        elif tdim >  1:
            self.nhdr['ndim'] = 4
        elif zdim > 1:
            self.nhdr['ndim'] = 3
        else:
            self.nhdr['ndim'] = 2

        if 'MOSAIC'in self.nhdr['ImageFormat'][-1] and len(self.nhdr['mosaic_slclocs']) < 4:
            self.nhdr['mosaic_slclocs'] = self._GetMosaicSliceLocations(self.nhdr)
        dprefix = self.dicominfo.get('prefix', None)
        compress = self.dicominfo.get('compress', None)
        ndig = self.dicominfo.get('ndig', 4) # Guess at 4 digits?
        # print("NDIG IS %s" % ndig)
        # print(self.dicominfo['dims'].get('FilenameFormat'))
        #if self.dicominfo['dims'].get('FilenameFormat', None) is not None:
            #fmt = self.dicominfo['dims']['FilenameFormat']
        #elif dprefix is not None:
        fmt = '%s.%%0%dd%s' % (dprefix, ndig, compress)
#        print 200, fmt
        
        zdims = range(zdim)
        for m in mtypes:
            for t in frames:
                if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
#                   Unpack image from Mosaic format (A Siemens format 
#                   consisting of a Montage of images in one frame).
                    inst = '%d_%d' % (m, t)
                    if self.dicominfo.has_key(inst):
                        path, start_image = self.dicominfo[inst]
                        if dprefix is not None:
#                           Convert compressed format.
                            path = fmt % path
                    else:
                        raise RuntimeError(\
                        'self.dicominfo does not have instance %s' % inst)
                    img = self.get_slice_fast(\
                                        start_image, '%s/%s' % (dirname,path))
                    for z in range(zdim):
                        x0, y0 = self.nhdr['mosaic_slclocs'][z]
                        self.image[m, t, z, :, :] =  \
                            img[y0:y0+ydim, x0:x0+xdim].astype(dtype)
                else:
                    for z in zdims:
#                    for z in range(zdim):
                        inst = '%d_%d_%d' % (m, t, z)
                        path, start_image = self.dicominfo[inst]
                        # print(path, start_image)
                        # print(fmt)
                        if dprefix is not None:
#                           Convert compressed format.
                            path = fmt % path
                        fname =('%s/%s' % (dirname,path)).replace(' ','')
                        if mtype < 0:
#                           Reading mdim indices.
                            mout = m
                        else:
#                           Only reading a single misc dim .
                            mout = 0
                        # print(start_image, fname)
                        self.image[mout,t-frm0,z,:,:] = \
                                    self.get_slice_fast(start_image, fname)

        return self.image.squeeze()

    def GetNativeHeader(self, dataset, scan=False):
        """
        Construct the native header.  This header is a dictionary including 
        selected dicom tags along with geometric information for the slice 
        axis.  Slice axis information assumes that the data will be read by 
        the file_io.readfile() method, since it imposes a slice ordering.

        The item "DicomInfo" contains an ordered list specifying filenames and
        a "dims" dictionary specifying the starting location, ending location
        slice ordering etc.

        If scan is True, each file in the series will be read to infer slice axis information. Otherwise a single file will be read and a partial header created.
        """
        if hasattr(self, 'nhdr'):
            return self.nhdr
        else:
            self.nhdr = self._GetNativeHeader(dataset, scan=scan)
            return self.nhdr

    def _GetNativeHeader(self, dataset, scan=False):
        """
        Read detect manufacturer and check for supported format.
        """
        manf = dataset[(0x0008,0x0070)].value

        self.transfer_syntax = ('%s' % dataset.file_meta[(0x0002,0x0010)].\
                    __dict__['_value'].__str__).split("'")[-2]
        self.MediaStorageSopClassUid = ('%s' % dataset.file_meta[\
                    (0x0002,0x0002)].__dict__['_value'].__str__).split("'")[-2]

        if self.MediaStorageSopClassUid == \
                                    MEDIA_STORAGE_SOP_CLASS_SCREEN_CAPTURE:
            self.image_type = 'ScreenCapture'
        elif self.MediaStorageSopClassUid == MEDIA_STORAGE_SOP_CLASS_UID:
            self.image_type = 'Supported'
        else:
            self.image_type = 'Unsupported'

        if manf.startswith('GE MEDICAL') or manf.startswith('GEMS'):
            self.nhdr = self._GetNativeGEHeader(dataset, scan=scan)
        elif manf.replace(' ','') == 'SIEMENS':
            self.nhdr = self._GetNativeSiemensHeader(dataset)
        else:
            raise RuntimeError('Dicom manufacturer not supported: %s' % manf)

        self.nhdr['MediaStorageSopClassUid'] = self.MediaStorageSopClassUid 
        self.nhdr['ImageType'] = self.image_type
        if self.image_type == 'Supported':
            self.nhdr['ImageData'] = True
        else:
            self.nhdr['ImageData'] = False
        return self.nhdr

    def GetDicomTags(self, dataset):
        """
        Read dicom tags and store in native_header.
        """
        self.modality = dataset[(0x0008,0x0060)].value
        if self.modality is None:
            sys.stderr.write("GetNativeGEHeader : Error reading header.\n")
            return None
        elif self.modality == 'PT':
            modality_keys = pet_hdrkeys
        elif self.modality == 'MR':
            modality_keys = mri_hdrkeys
        else:
            modality_keys = []

        nhdr = {'filetype':'dicom'}
#       Read the header from low-level dictionary.
        for entry in hdrkeys + modality_keys:
            try:
                nhdr[entry[0]] = dataset[entry[1]].value
            except KeyError:
                nhdr[entry[0]] = None

        if nhdr.get('FirstScanRas', None) is not None:
#           This causes some bugs.
            nhdr['FirstScanRas'] = nhdr['FirstScanRas'].strip()
        if isinstance(nhdr.get('FirstScanLocation', None), str):
            nhdr['FirstScanLocation'] = float(nhdr['FirstScanLocation'])
        if isinstance(nhdr.get('LastScanLocation', None), str):
            nhdr['LastScanLocation'] = float(nhdr['LastScanLocation'])
        if isinstance(nhdr.get('DisplayFieldOfView', None), str):
            nhdr['DisplayFieldOfView'] = float(nhdr['DisplayFieldOfView'])

        x = nhdr.get('RequestingPhysician', None)
        if isinstance(x, dc.valuerep.PersonName):
            nhdr['RequestingPhysician'] = x.family_comma_given()
        x = nhdr.get('PatientName', None)
        if isinstance(x, dc.valuerep.PersonName):
            nhdr['PatientName'] = x.family_comma_given()

        if nhdr['PatientWeight'] is None:
            nhdr['PatientWeight'] = -1
        return nhdr

    def GetOrientation(self, nhdr):
        """
        Create the transformation matrix from image coordinates to RAI coordinates.
        """
        xdim = nhdr['Columns']
        ydim = nhdr['Rows']
        xsize = nhdr['PixelSpacing'][0]
        ysize = nhdr['PixelSpacing'][1]

        if 'MOSAIC'in nhdr['ImageFormat'][-1]:
#           Compute origin. Mosaic images specify the starting location as the 
#           "upper" left corner of the entire, nonexistent mosaic (go figure).
            dx = xsize*(nhdr['ColsMosaic'] - xdim  )/2.
            dy = ysize*(nhdr['RowsMosaic'] - ydim  )/2.
            nhdr['Columns'] = xdim
            nhdr['Rows'] = ydim
#            image_position[zaxis] = nhdr['SliceLocation']
        else:
            dx = 0.
            dy = 0.

        R = dicom_to_rot44(nhdr['ImageOrientation'], nhdr['ImagePosition'], \
                                            nhdr['StartRas'], nhdr['StartLoc'])

        image_position = R[:3,3].tolist()
        return R, image_position

    def _GetNativeGEHeader(self, dataset, scan=False):
        """
        Purpose: Get the entire header.
        Returns: A dictionary containing the entire header.
        If "scan" is true, each file will be read to ensure that the 
        third, fourth, and fifth dimensions are correct.
        """

#        if self.scanned:
#            scan = True
        self.manf = 'GE'
        self.mosaic = False
        
#       Read tags and store into header.
        if dataset is None:
            return None
        else:
            nhdr = self.GetDicomTags(dataset)

#       Convert posix time to human-readable time.
        nhdr['FileName'] = self.filename
        if isinstance(nhdr['ActualSeriesDateTime'], int):
            nhdr['SeriesDateTime'] = datetime.fromtimestamp(\
                nhdr['ActualSeriesDateTime']).strftime('%d%b%Y_%X')
        else:
            nhdr['SeriesDateTime'] = nhdr['ActualSeriesDateTime']


        if nhdr['SpacingBetweenSlices'] is not None and \
                            nhdr['SliceThickness'] is not None:
            nhdr['SliceGap'] = nhdr['SpacingBetweenSlices'] - nhdr['SliceThickness']
        else:
            nhdr['SliceGap'] = 0
            nhdr['SpacingBetweenSlices'] = nhdr['SliceThickness']

        if not nhdr['Manufacturer']:
            nhdr['Manufacturer'] = ''
        
        nhdr['RawImageType'] = nhdr['ImageType']
        nhdr['Channel'] = idx_to_type.get(nhdr['GEImageType'], 0)
        nhdr['ImageType'] = idx_to_type.get(nhdr['GEImageType'], '')

        nhdr['RowsMosaic'] = nhdr['Rows']
        nhdr['ColsMosaic'] = nhdr['Columns']
        self.rows_mosaic = nhdr['RowsMosaic']
        self.cols_mosaic = nhdr['ColsMosaic']

        nhdr = self.SetDerivedParameters(nhdr, scan, dataset=dataset)

        return nhdr

    def SetDerivedParameters(self, nhdr, scan, dataset=None):
        """
        Infer slice axis information.
        """

        if scan == True:
#           Read every file in the directory to find out what is really
#           there and where each slice is located.
            self.scanned = True
            if os.path.isdir(self.filename):
                self.dicominfo = self._ScanDicomFiles(dataset, nhdr)
                if self.dicominfo is None:
                    raise RuntimeError("Error while scanning dicom files.")
            else:
                self.dicominfo = None

        if self.filename is not None:
            if os.path.isdir(self.filename):
                self.nfiles = self._GetNumberDicoms(nhdr)
            else:
                self.nfiles = 1
            nhdr['LocationsInAcquisition'] = self.nfiles
            nhdr['ImagesInSeries'] = self.nfiles
            if self.nfiles < nhdr['ImagesInAcquisition']:
#               Fix for GE derived images.
                nhdr['ImagesInAcquisition'] = nhdr['ImagesInSeries']

#            if self.manf == 'GE':
#                if  not os.path.isdir(self.filename):
#                    nhdr['LocationsInAcquisition'] = 1
#                else:
#                    nhdr['LocationsInAcquisition'] = self.nfiles
            nhdr['Localizer'] = None

        if nhdr.has_key('DicomInfo'):
#           All files were scanned, use results to load the header.
            dims = self.dicominfo['dims']
            if not self.mosaic and dims['zdim'] > 1:
#               Start and Endloc meaningless for mosaic format.
                nhdr['SpacingBetweenSlices'] = \
                        abs(dims['EndLoc'] - dims['StartLoc'])/(dims['zdim'] - 1.)
            nhdr['LocationsInAcquisition'] = dims['zdim']
            nhdr['ImagesInSeries'] = dims['zdim']*dims['tdim']
            nhdr['NumberOfFrames'] = dims['tdim']
            nhdr['TypeDim'] = dims['TypeDim']
            nhdr['EchoTimes'] = dims['EchoTimes']
            nhdr['ImagePosition'] = dims['ImagePosition']
            nhdr['Localizer'] = dims['Localizer']
            nhdr['StartRas'] = dims['StartRas']
            nhdr['StartLoc'] = dims['StartLoc']
            nhdr['EndLoc'] = dims['EndLoc']
            nhdr['dirname'] = dims['dirname']
            nhdr['DicomInfo'] = self.dicominfo
            nhdr['FlipAngles'] = dims.get('FlipAngles', None)
            nhdr['SliceOrder'] = dims['SliceOrder']
        elif self.modality == 'MR' and nhdr['PulseSequenceName'] is not None \
                            and  'epiRT' in nhdr['PulseSequenceName']:
            nhdr['NumberOfFrames'] = nhdr['FastPhases']
            nhdr['TypeDim'] = self.nfiles/ \
                (nhdr['LocationsInAcquisition']*nhdr['FastPhases'])
            nhdr['SliceOrder'] = 'unknown'
            nhdr['StartRas'] = nhdr['FirstScanRas']
            nhdr['StartLoc'] = nhdr['FirstScanLocation']
            nhdr['EndLoc'] = nhdr['FirstScanLocation']
    #        if not self.mosaic:
#   #            Start and Endloc meaningless for mosaic format.
    #            nhdr['SpacingBetweenSlices'] = abs(dims['EndLoc'] - \
    #                    dims['StartLoc'])/(nhdr['LocationsInAcquisition'] - 1.)
        elif nhdr['LocationsInAcquisition'] and nhdr['ImagesInSeries']:
            nhdr['NumberOfFrames'] = (
                nhdr['ImagesInSeries']/nhdr['LocationsInAcquisition'])
            nhdr['TypeDim'] = 1
            nhdr['SliceOrder'] = 'unknown'
            nhdr['StartRas'] = nhdr['FirstScanRas']
            nhdr['StartLoc'] = nhdr['FirstScanLocation']
            nhdr['EndLoc'] = nhdr['FirstScanLocation']
        else:
#           Unrecognized header, return what we have.
            nhdr['ndim'] = 1
            nhdr['NumberOfFrames'] = 1
            nhdr['TypeDim'] = 1
            nhdr['SliceOrder'] = 'unknown'
            nhdr['StartRas'] = nhdr['FirstScanRas']
            nhdr['StartLoc'] = nhdr['FirstScanLocation']
            nhdr['EndLoc'] = nhdr['FirstScanLocation']
            return nhdr


#       Fix weirdness in early ASL dicom files.
        psdname = nhdr.get('PulseSequenceName',None)
        if psdname is not None and '3dfsepcasl' in psdname:
            nhdr['ImagesInSeries'] = nhdr['LocationsInAcquisition']

#       Update the origin in the transformation matrix.
        nhdr['R'], nhdr['image_position'] = self.GetOrientation(nhdr)

        if (int(nhdr['ImagesInSeries']) % \
             int(nhdr['LocationsInAcquisition'])) != 0 and \
             not nhdr.get('Localizer'):
            errstr = \
            'Missing slice(s): Number of slices acquired is not evenly\n' \
            '\t\tdivisible by the number of slices per frame. ***\n' + \
            '\tDicom directory: %s\n' % self.filename + \
            '\tNumber of slices acquired: %d\n' % nhdr['ImagesInSeries']+\
            '\tNumber of slices per frame: %d\n' % \
                                    nhdr['LocationsInAcquisition'] + \
            '\tNumber of image types per series: %d\n' % nhdr['TypeDim']
            print(errstr)

        if nhdr['TypeDim']  > 1:
            nhdr['ndim'] = 5
        elif nhdr['NumberOfFrames'] >  1:
            nhdr['ndim'] = 4
        elif nhdr['LocationsInAcquisition']  > 1:
            nhdr['ndim'] = 3
        else:
            nhdr['ndim'] = 2

        return nhdr


    def _GetNativeSiemensHeader(self, dataset):
        """
        Purpose: Get the entire header.
        Returns: A dictionary containing the entire header.
        If "scan" is true, each file will be read to ensure that the 
        third, fourth, and fifth dimensions are correct.
        if "scanned" is true, it will be assumed that the data have already
        been scanned that the dicominfo attribute is correct.
        """

        if dataset is None:
            return None
        self.manf = 'Siemens'

        scan = True
        nhdr = self.GetDicomTags(dataset)

        nhdr['FileName'] = self.filename

#       Convert posix time to human-readable time.
        if isinstance(nhdr['ActualSeriesDateTime'], int):
            nhdr['SeriesDateTime'] = \
                 datetime.fromtimestamp( \
                        nhdr['ActualSeriesDateTime']).strftime('%d%b%Y_%X')
        else:
            nhdr['SeriesDateTime'] = nhdr['ActualSeriesDateTime']

    
        if not nhdr['Manufacturer']:
            nhdr['Manufacturer'] = ''
        
        nhdr['RawImageType'] = nhdr['ImageType']
        nhdr['Channel'] = idx_to_type.get(nhdr['GEImageType'], 0)
        nhdr['ImageType'] = idx_to_type.get(nhdr['GEImageType'], '')

        if 'MOSAIC'in nhdr['ImageFormat'][-1]:
            self.mosaic = True
            nhdr['RowsMosaic'] = nhdr['Rows']
            nhdr['ColsMosaic'] = nhdr['Columns']
            if nhdr.get('MosaicMatrixSize', None) is not None:
                xy_dims = nhdr['MosaicMatrixSize'].split('*')
                if not xy_dims[0][-1].isdigit():
                    xy_dims[0] = xy_dims[0][:-1]
                if not xy_dims[1][-1].isdigit():
                    xy_dims[1] = xy_dims[1][:-1]
                nhdr['Rows'] = int(xy_dims[0])
                nhdr['Columns'] = int(xy_dims[1])
            else:
                nhdr['Rows'] = nhdr['AcquisitionMatrix'][1]
                nhdr['Columns'] = nhdr['AcquisitionMatrix'][1]
        else:
            self.mosaic = False
            nhdr['RowsMosaic'] = nhdr['Rows']
            nhdr['ColsMosaic'] = nhdr['Columns']
        self.rows_mosaic = nhdr['RowsMosaic']
        self.cols_mosaic = nhdr['ColsMosaic']

        nhdr['PulseSequenceName'] = nhdr['SequenceName']
           

        if 'MOSAIC'in nhdr['ImageFormat'][-1]:
            nhdr['mosaic_slclocs'] = self._GetMosaicSliceLocations(nhdr)
#            if nhdr.has_key('mosaic_slclocs'):
            nhdr['MosaicNumberImages'] = len(nhdr['mosaic_slclocs'])

        nhdr = self.SetDerivedParameters(nhdr, scan, dataset=dataset)
        return nhdr

    def isdicom(self, fname):
        """
        Return True if data is in DICOM format.
        """
        if self.tarobj is None:
            return isdicom(fname)
        else:
            return self.tarobj.isTar


    def _GetNumberDicoms(self, nhdr):
        """
        Return number of DICOM files.
        """
#       Get number of frames. Assumes mdim = 1
        ndicom = 0
        if len(self.dirname) == 0:
            ndicom = 1
        else:
            if self.tarobj is None:
                fnames = os.listdir(self.dirname)
                dname = '%s/' % self.dirname
            else:
                fnames = self.tarobj.GetNames()
                dname = ''
            for fname in fnames:
                fullfile = "%s%s" % (dname, fname)
                if self.isdicom(fullfile):
                    ndicom = ndicom + 1
        return ndicom

    def _GetMosaicSliceLocations(self, nhdr):
        """
        Return number of slices for a volume stored in mosaic format.
        """
        mosaic_slclocs = []
        n = 0
        for y in xrange(nhdr['RowsMosaic']/nhdr['Rows']):
            for x in xrange(nhdr['ColsMosaic']/nhdr['Columns']):
                if n < nhdr['MosaicNumberImages']:
                    mosaic_slclocs.append((x*nhdr['Columns'], \
                                               y*nhdr['Rows']))
                n += 1
        return mosaic_slclocs

    def FreeData(self):
        """
        Free binary data. Otherwise it won't be garbage collected.
        """
        if hasattr(self, 'data'):
            delattr(self, 'data')
            self.data = None

    def Free(self):
        self.FreeData()
#        if self.dataset is not None:
#            del self.dataset


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



    def _ScanDicomFiles(self, dataset0, nhdr, anonymize=False):
        """
        Create a directory specifying the name, time, type and position of 
        each slice.
        """

#       Initialize scanning process.
        sd = ScanDicomSlices(dataset0, nhdr=nhdr, dname=self.dirname)

#       Retrieve info from each file.
        if self.tarobj is None:
            fnames = os.listdir(self.dirname)
            fnames.sort()
            for fname in fnames:
                suffix = fname.split('.')[-1]
                if suffix not in ('txt', 'log', 'yaml', 'pickle', 'tar'):
                    if isdicom('%s/%s' % (self.dirname, fname)):
                        sd.NextSlice(fname=fname, anonymize=anonymize)
        else:
            fnames = self.tarobj.GetNames()
            fnames.sort()
            for fname in fnames:
                sd.NextSlice(fname=fname, anonymize=anonymize, \
                                          data=self.tarobj.GetSlice(fname))

        sd._ScanProcess()
        return sd.dicominfo

class ScanDicomSlices(Dicom):
    """
    Object for reading header for every dicom file in a directory and creates a dictionary summarizing the results. 
    """
    def __init__(self, data, nhdr=None, dname='.'):
        self.dirname = dname
        self.scanned = False
        self.filename = None
        self.dicominfo = None
        self.nfiles = 0
        if nhdr is not None:
            self.nhdr = nhdr
            if not isinstance(data, str):
                dataset = data
        elif isinstance(data, str):
            dataset = self._DicomHeader(data=data)
            self.nhdr = self.GetNativeHeader(dataset)
        else:
#           Data must already be a pydicom dataset.
            self.nhdr = self.GetNativeHeader(data)
            dataset = data
        self._ScanInit(dataset)

        self.localizer = False
        self.image_orientation0 = dataset[(0x0020,0x0037)].value
        self.image_orientation = array(self.image_orientation0).\
                                    round().astype(int).reshape([2,3])
        self.slice_location = dataset[(0x0020,0x1041)].value


    @classmethod
    def FromFiles(klass, file_list):
        first_file = os.path.abspath(file_list[0])
        dirname = os.path.dirname(first_file)
        with open(first_file, 'r') as f:
            data = f.read()
        sds = klass(data, dname=dirname)
        for fname in file_list:
            with open(fname, 'r') as f:
                data = f.read()
            sds.NextSlice(data=data, fname=fname)
        return sds

    def NextSlice(self, data=None, fname=None, fname_format=None, anonymize=False):
        """
        Add another slice to the dicominfo catalog.
        """
        if isinstance(data, str):
            dataset = self._DicomHeader(data=data)
            data_out = data
        elif isinstance(data, dc.dataset.FileDataset):
            dataset = data
            data_out = None
        elif isinstance(fname, str):
            f = open_gzbz2('%s/%s' % (self.dirname, fname), 'r')
            data_out = f.read()
            f.close()
            dataset = self._DicomHeader(data=data_out)
        else:
            raise RuntimeError('Unknown data type: %s' % type(data))
        full_fname = self.ScanInfo(dataset, fname_format=fname_format, \
                                   fname=fname)

        if anonymize:
            data_out = self.Anonymize(dataset, data_out)

        return full_fname, data_out

    def Process(self):
        """
        Process the summary info to create the DicomInfo dictionary defining slice-axis parameters.
        """
        self._ScanProcess()
        self.scanned = True
        self.nhdr = self.SetDerivedParameters(self.nhdr, False)
        return (self.dicominfo)

    def _ScanInit(self, dataset=None):
        """
        Initialize data for scanning a dicom directory.
        """
        if 'MOSAIC'in self.nhdr.get('ImageFormat',[''])[-1]:
#           Must check to see where slices are stored for Mosaic format.
            if  hasattr(dataset, 'pixel_array'):
                img = dataset.pixel_array
            else:
                raise RuntimeError('Dicom file contains no data: %s' % fullpath)
            self.nhdr['mosaic_slclocs'] = self._GetMosaicSliceLocations(self.nhdr)
        self.nfiles = 0
        img_pos = self.nhdr['ImageOrientation']
        if img_pos is not None:
            img_pos = map(float, img_pos)
            test = array(map(abs,[img_pos[0]+img_pos[3], img_pos[1]+img_pos[4],\
                                  img_pos[2]+img_pos[5]]))
            self.slice_idx = test.argmin()
        else:
            self.slice_idx = 0
        self.image_position = None

#       First scan all the files and get the data.
        self.info = {} # Directory of dicom files.

    def Anonymize(self, ds, data):
        """
        Anonymize patient name.
        """
        pntag = ds[(0x0010, 0x0010)]
        pn = pntag.value
        pnlgth = len(pn)
        pnoff = pntag.file_tell
        pn = self.PatientNameTranslation(pn) 
        newpn = fromstring(pn, ubyte)
        ndata = fromstring(data,ubyte)
        ndata[pnoff:pnoff+pnlgth] = newpn
        self.newpn = newpn.tostring()

#       Anonymize birthdate.
        bdtag = ds[(0x0010, 0x0010)]
        bd = bdtag.value
        bdlgth = len(bd)
        bdoff = bdtag.file_tell
        self.newbd = self.PatientBirthDateTranslate(bd)
        self.newbd = fromstring(self.newbd,ubyte)
        ndata[bdoff:bdoff+bdlgth] = self.newbd
        self.newbd = self.newbd.tostring()

        return ndata.tostring()


    def ScanInfo(self, ds, fname_format=None, fname=None):
        """
        Extract relevant info from a given slice.
        <ds>: the dataset for the current slice
        <fname_format>: format string for that can be used to write the slice names, e.g., s02_epi.%04d
        <fname>
        """


#       Check to see if this is a localizer.
        if self.image_orientation0 != ds[(0x0020,0x0037)].value:
            self.localizer = True

        if ds.has_key((0x0020,0x0013)):
            InstanceNumber = int(ds[(0x0020,0x0013)].value)
        else:
            if isinstance(fname, str):
                raise RuntimeError('Invalid dicom file: %s' % fname)
            else:
                raise RuntimeError('Invalid dicom dataset')

        self.instance = InstanceNumber
        if InstanceNumber == 1 or self.image_position is None:
#           Starting image position is that for the first file acquired.
            self.image_position = ds[(0x0020,0x0032)].value

        if fname_format:
            fullfile = (fname_format % InstanceNumber).replace(' ','')
        elif isinstance(fname, str):
            fullfile = ("%s/%s" % (self.dirname, fname)).replace(' ','')
        else:
            fullfile = 'None'
        Manufacturer = ds[(0x0008,0x0070)].value.strip()      # tmp
        ImageFormat = ds[(0x0008,0x0008)].value #[2]     # tmp
        try:
            Modality = ds[(0x0008,0x0060)].value.strip()
        except:
            errmsg = 'ScanDicomFiles: Invalid modality (%s) for %s\n' % \
                                                    (Modality, fullfile)
            sys.stderr.write(errmsg)
            raise RuntimeError(errmsg)
        if Manufacturer.startswith('GE MEDICAL') or \
                Manufacturer == 'GEMS':
            GEImageType = ds[(0x0043,0x102f)].value
            if GEImageType is not None:
                ImageType = GEImageType
            else:
#               If GE doesn't supply their own key, assume it \
#               is alway magnitude.
                ImageType = 'Magnitude'

            AcqTime = int(100*float(ds[(0x0008,0x0032)].value[2]))
            self.mosaic = False
        elif Manufacturer == 'SIEMENS':
            if 'MOSAIC' in ImageFormat[-1]:
                self.mosaic = True
            else:
                self.mosaic = False
            ImageType = ds[(0x0008,0x0008)].value[2]
            ImageType = siemens_type_to_idx.get(ImageType, 0)
            AcqTime = int(100*float(ds[(0x0008,0x0032)].value[2]))
        elif self.nhdr['Manufacturer'].replace(' ','').lower() == \
                                        'philipsmedicalsystems':
            ImageType = ds[(0x0008,0x0008)].value[2]
            ImageType =  phillips_type_to_idx.get( \
                            [self.nhdr['ImageType'][2]],'Magnitude')
            TemporalPosition = int(ds[(0x0020,0x0100)].value[2])
            AcqTime = TemporalPosition
            self.mosaic = False
        else: # Hope that Siemens encoding works for Phillips etc. \
#               It won't work for GE.
            ImageType = ds[(0x0008,0x0008)].value[2]
            ImageType = siemens_type_to_idx[ImageType]
            AcqTime = int(100*float(ds[(0x0008,0x0032)].value[2]))
            self.mosaic = False

        ImagePosition = ds[(0x0020,0x0032)].value
        SliceLocation = ds[(0x0020,0x1041)].value
        x = ds.get((0x0020,0x0012), None)
        if x is None:
            AcquisitionNumber = 0
        else:
            AcquisitionNumber = x.value
#        AcquisitionNumber = ds[(0x0020,0x0012)].value
        SeriesNumber = ds[(0x0020,0x0011)].value
        if ds.has_key((0x0018,0x0088)):
            SpacingBetweenSlices = ds[(0x0018,0x0088)].value
        else:
            SpacingBetweenSlices = 0.

#       This is no longer used. Made obsolete by switch to pydicom.
        start_image = -1

        EchoTime = ds[(0x0018,0x0081)].value
        FlipAngle = ds[(0x0018,0x1314)].value
        t_inst = AcqTime*1000 + InstanceNumber
        self.nfiles += 1
        key = "%05d_%013d_%s" % (int(10*EchoTime), t_inst, ImageType)
        self.info[key] = (os.path.basename(fullfile), AcqTime, \
                ImagePosition[self.slice_idx], ImageType, EchoTime, \
                t_inst, start_image, FlipAngle, InstanceNumber)
        return fullfile

    def _ScanProcess(self):
        """
        Process information obtained by reading all slices.
        """

#       Find unique values.
        unique_pos = {}
        unique_type = {}
        unique_tes = {}
        unique_flips = {}
        for inst in self.info.keys():
            item = self.info[inst]
            if not unique_pos.has_key(item[2]):
                unique_pos[item[2]] = inst
            if not unique_type.has_key(item[3]):
                unique_type[item[3]] = inst
            if not unique_tes.has_key(item[4]):
                unique_tes[item[4]] = True
            if not unique_flips.has_key(item[7]):
                unique_flips[item[7]] = True

        unique_z = unique_pos.keys()
        unique_z.sort()
#       Sort type dimension.
        unique_typ = unique_type.keys()
        unique_typ.sort()

#       Images are sorted by low -> high echo time.
        EchoTimes = unique_tes.keys()
        EchoTimes.sort()
        FlipAngles = unique_flips.keys()
        FlipAngles.sort()

        unique_t_inst = self.info.keys()
        unique_t_inst.sort()

        mdim = len(unique_typ)
        if self.nhdr.has_key('mosaic_slclocs'):
#           Siemens mosaic format.
            zdim = len(self.nhdr['mosaic_slclocs'])
            tdim = len(unique_t_inst)/mdim
            mosaic = True
        else:
            zdim = len(unique_z)
            mosaic = False
            tdim = len(unique_t_inst)/zdim/mdim
        if tdim == 0:
            tdim = 1
        if float(self.nfiles) % float(zdim) and self.filename:
            if self.localizer:
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
        if self.mosaic:
            zmin = self.slice_location
            zmax = zmin  + (zdim - 1) *self.nhdr['SpacingBetweenSlices']
        else:
            zarray = array(unique_z)
            zmin = zarray.min()
            zmax = zarray.max()

#       Determine if slice locations should be flipped.
        action = {'I':'norev', \
                  'S':'rev', \
                  'A':'norev', \
                  'P':'rev', \
                  'R':'rev', \
                  'L':'norev'}
        revras = {'I':'S', \
                  'S':'I', \
                  'A':'P', \
                  'P':'A', \
                  'R':'L', \
                  'L':'R'}
        z0 = self.info[unique_t_inst[0]][2]
        z1 = self.info[unique_t_inst[mdim*len(unique_z)-1]][2]
        if self.nhdr['FirstScanRas'] is not None:
            start_ras = self.nhdr['FirstScanRas']
        else:
            A = zeros((2,3), float)
            A[0,:3] = self.nhdr['ImageOrientation'][:3]
            A[1,:3] = self.nhdr['ImageOrientation'][3:]
            zaxis = int(dot(abs(A), arange(3)).sum())
            start_ras = 'IAR'[zaxis-1]

        if start_ras in 'RAI' and z0 > z1 or start_ras in 'LPS' and z1 < z0:
#           Force starting location to be consist with self.info
            start_ras = revras[start_ras]

        if action[start_ras] == 'rev':
#           Flip the axis to get it in a standard orientation
            unique_z.reverse()
            start_ras = revras[start_ras]

#       Get the starting and ending locations.
        k0 = mdim*unique_z.index(self.info[unique_t_inst[0]][2])
        k1 = mdim*unique_z.index(self.info[unique_t_inst[mdim*len(unique_z)-1]][2])
        start_loc =  self.info[unique_t_inst[k0]][2]
        end_loc =  self.info[unique_t_inst[k1]][2]

#       Get format string for filename.  This is required to read dicoms
#       written by something other than upload_data.
        # fmt_string = self.GetFormatString()

#       Create an entry for each file specifying its position in image array.
        self.dicominfo = {}
        times = zeros([mdim, zdim], integer)
        prefix, compress, ndig = self.CompressInfo(self.info[unique_t_inst[0]])
        for inst in unique_t_inst:
#           instance keys are a number encoded with time and instance number.
#           These keys will sort in order of ascending time for both GE 
#           and Siemens headers.
            item = self.info[inst]
            z = unique_z.index(item[2])
            m = unique_typ.index(item[3]) #* mdim*EchoTimes.index(item[4])
            t = int(times[m, z])
            times[m, z] = t + 1
            if mosaic:
                key = '%d_%d' % (m, t)
            else:
                key = '%d_%d_%d' % (m, t, z)
            fnum = item[8]
            self.dicominfo[key] = (int(fnum), item[6])

#       Get the slice ordering for later use.
        slice_spacing = self.nhdr['SliceThickness'] + self.nhdr['SliceGap']
        if self.dicominfo.has_key('0_0_1'):
            test = self.dicominfo['0_0_1'][0] - self.dicominfo['0_0_0'][0]
        else:
            test = 1
        if test > 0:
            slice_order = 'alt+z'
        else:
            slice_order = 'alt-z'
#            raise RuntimeError('Could not determine slice_order')
        
        self.scanned = True
        dims = {
               'StartLoc':start_loc,
               'EndLoc':end_loc,
               'StartRas':start_ras,
               'zdim':zdim, 
               'tdim':tdim,
               'TypeDim':mdim,
               'dirname':self.dirname,
               'EchoTimes':EchoTimes,
               'FlipAngles':FlipAngles,
               'Localizer':self.localizer,
               'SliceOrder':slice_order,
               #'FilenameFormat':fmt_string, \
               'ImagePosition':self.image_position}
        self.dicominfo['dims'] = dims
        self.dicominfo['compress'] = compress
        self.dicominfo['prefix'] = prefix
        self.dicominfo['ndig'] = ndig
        self.nhdr['DicomInfo'] = self.dicominfo

#    def GetFormatString(self):
#        """
#        Create a format string for the individual dicom file names by inferring it from one or more filenames.
#        """
#        filenames = sorted([info[0] for info in self.info.values()])
#        longest = max(len(fn) for fn in filenames)
#        #TODO: Try changing to rjust
#        filenames_padded = [fn.ljust(longest) for fn in filenames]
#        template = filenames_padded[0]
#        template_ubyte = fromstring(template, ubyte)
#        msk = ones(longest, dtype=bool)
#
#        # There's no point if there's just one file.
#        if len(filenames) == 1:
#            return template+"%s"
#
#        for fn in filenames_padded:
#            logical_and(msk, equal(fromstring(fn, ubyte),template_ubyte), msk)
#
#        tst = logical_xor(msk[1:], msk[:-1])
#        # Digits with values that change correspond "True" elements in tst
#        digs = nonzero(where(tst == True, 1, 0))[0]
#        dig0 = digs[0] + 1
#        if digs.shape[0] == 2:
#            dig1 = digs[1] + 1
#        else:
#            dig1 = longest
#        return template[:dig0] + '%%0%dd' % (dig1 - dig0) + template[dig1:]

    def CompressInfo(self, item):
        fname = item[0]
        if fname.endswith('.bz2'):
            compress = '.bz2'
        elif fname.endswith('.gz'):
            compress = '.gz'
        else:
            compress = ''
        wds = fname.split('.')
#        print 999, item, wds, len(wds[1])
        return wds[0], compress, len(wds[1])


#*************************************************************************
def dicom_to_rot44(ImageOrientation, image_position, start_ras, start_loc):
#*************************************************************************
    """
    Purpose: 
        Convert dicom header variables to a 4x4 transform matrix.
    Arguments:
        ImageOrientation: Value for image orientation key (0x020,0x0037)
        image_position: Value for image position key (0x0020,0x0032)
        start_ras: Single letter in 'RAS' defining the starting slice position.
        start_loc: Starting slice location in mm.
    Returns:
        4x4 transformation matrix.
    """


#   First two columns are given in dicom header. The third is +/- the 
#   cross-product of the first two.  The sign is determined by the ordering 
#   of the slices as formatted in "read_ge_dicom" in dicom.py
#   ImageOrientation defines the rotation from LAI coordinates to 
#   image coordinates.
    R = zeros([4, 4], float)
    R[0,:3] = ImageOrientation[:3]
    R[1,:3] = ImageOrientation[3:]
    R[2,:3] = abs(cross(R[0,:3],R[1,:3]))

    zaxis = int(dot(abs(R[:3,:3]),arange(3))[2])
    R = R.transpose()  # Invert to get rotation from image to RAI
    R[3, 3] = 1.

#   Ensure correct sign for the slice dimension.
    image_position[zaxis] = start_loc
    if start_ras is not None and start_ras in 'LPS':
        R[zaxis, :3] = -abs(R[zaxis, :3])

    R[:3,3] = image_position

    return R
