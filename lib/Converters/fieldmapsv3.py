
import subprocess
import os
from pathlib import PurePath, Path
import json
import argparse
import nibabel as nib
import numpy as np
import os
from scipy.ndimage import binary_dilation, median_filter
from pydicom.filereader import dcmread
import pydicom.pydicom_series as dcmseries
from datetime import datetime
import struct
import bz2
import gzip

BLOCKSIZE = 12288
EXPLICIT = 0
IMPLICIT = 1

# Actions to take while parsing dicom header.
NOBREAK = 0
BREAK = 1
CONTINUE = 2

MEDIA_STORAGE_SOP_CLASS_UID = '1.2.840.10008.5.1.4.1.1.4'
MEDIA_STORAGE_SOP_CLASS_SCREEN_CAPTURE = '1.2.840.10008.5.1.4.1.1.7'

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

class makefmaps():

    def __init__(self):
        ap = argparse.ArgumentParser()
        ap.add_argument("-s", "--studypath", required=False,
                        help="Folder containing DICOM fieldmap files converted "
                        "using dcm2niix.")
        args = vars(ap.parse_args())
        self.studypath = args["studypath"]
        self.studypath = Path("/fast_scratch/jdr/resting/BIDS_fmapTest")
        ses_dirs = [ses_dir for ses_dir in sorted(self.studypath.glob('*/ses-*'))
                    if Path(ses_dir / 'fmap').exists()]
        for ses_dir in ses_dirs:
            self.main(ses_dir)

    def findfmapfiles(self, ses_dir):
        rawFileSuffixes_dict = {
            "1_e1.nii": "magnitude1",
            "1_e1a.nii": "magnitude2",
            "1_imaginary.nii": "imaginary1",
            "1_imaginarya.nii": "imaginary2",
            "1_ph.nii": "phase1",
            "1_pha.nii": "phase2",
            "1_real.nii": "real1",
            "1_reala.nii": "real2"
        }

        self.rawfmap_dir = ses_dir / 'fmap' / 's14_fmap'

        self.fmap_dir = ses_dir / 'fmap'
        rawfmapFiles = (
            rawfmapfile for rawfmapfile in self.fmap_dir.glob('*e1*.nii*'))
        rawFilesDict = {}
        for rawfmapfile in rawfmapFiles:
            suffix = rawfmapfile.name.split('_e')[1]
            fileType = ''.join(
                [val for key, val in rawFileSuffixes_dict.items() if suffix in key])
            rawFilesDict[fileType] = Path(self.fmap_dir / rawfmapfile)
        return (rawFilesDict)

    #def getfmapFiles(self, rawFilesDict):

    def get_value(self, tag, default=None):
        """
        Purpose: Return the value of a Dicom tag.
        Inputs: key: A dicom tag in the form "7fe0,0010"
                filename: filename to be read.
        Outputs: The value of the tag.
        """
        return (self.hdr.get(tag, [default])[-1])

    open_funcs = [open, bz2.BZ2File, gzip.GzipFile]

    def open_gzbz2(self, fullpath, mode='r'):
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
            # No suffix.
            for i in np.xrange(3):
                path = fullpath + ['','.bz2', '.gz'][i]
                if os.path.exists(path):
                    break
            else:
                return None
        f = np.apply(self.open_funcs[i], (path, 'r'))

        if f is None:
            raise IOError('open_gzbz2: Could not open: %s\n' % path)
        else:
            return f

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
            f = self.open_gzbz2(filename, "rb")
            self.data = f.read()
            f.close()
        self.flen = len(self.data)
        magic_code = self.data[128:132]

        if magic_code == "DICM":  #.endswith("DICM"):
        # File is in dicom format with explicit transfer syntax for now.
            self.syntax = EXPLICIT
        else:
        # Rewind and try implicit syntax.
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
            if VR in lgth_tab:
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
            np.apply(self.special_actions.get \
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
            self.VL = np.struct.unpack(fmt_VL, sVL)[0]
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

            value = np.apply(self.decode_value.get(VR, self._DefaultItem), ())
#            sys.stdout.write(', value: __%s__' % (value))

#           Convert value.
            decoder, format, unit_lgth = self.decode_type.get(VR,  \
                                    (self._NoDecode, 0, 0))
            if self.process:
#               Get item value, i.e., Start of image data, transfer syntax
#               Don't process non-image items such as icon image sequences.
                data_value = np.apply(decoder, (value, format, unit_lgth))
                self.hdr[self.key] = (VR, self.VL, data_value)
#                sys.stdout.write(', value: __%s__' % (data_value))
#                sys.stdout.write(' idx: 0x%04x' % self.idx)
#        keys = self.hdr.keys()
#        keys.sort()
#        for key in keys:
#            print key, self.hdr[key]
        return(self.hdr)

    def get_native_header(self, scan=False, scanned=False):
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

        modality_keys = [ \
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

        self.rawfmap_prefix = self.rawfmap_dir.name[:3]

        lstFilesDCM = []
        for dirName, subdirList, fileList in os.walk(self.rawfmap_dir):
            for filename in fileList:
                if self.rawfmap_prefix in filename.lower() and filename[-4:].isdigit():
                    lstFilesDCM.append(os.path.join(dirName, filename))

        RefDs = dcmread(lstFilesDCM[0])
        self.hdr = RefDs.items

        ConstPixelDims = (int(RefDs.Rows), int(RefDs.Columns), len(lstFilesDCM))
        ConstPixelSpacing = (float(RefDs.PixelSpacing[0]), float(RefDs.PixelSpacing[1]), float(RefDs.SliceThickness))

        x = np.arange(0.0, (ConstPixelDims[0] + 1) * ConstPixelSpacing[0], ConstPixelSpacing[0])
        y = np.arange(0.0, (ConstPixelDims[1] + 1) * ConstPixelSpacing[1], ConstPixelSpacing[1])
        z = np.arange(0.0, (ConstPixelDims[2] + 1) * ConstPixelSpacing[2], ConstPixelSpacing[2])

        ArrayDicom = np.zeros(ConstPixelDims, dtype=RefDs.pixel_array.dtype)

        # loop through all the DICOM files
        for filenameDCM in lstFilesDCM:
            # read the file
            ds = dcmread(filenameDCM)
            # store the raw image data
            ArrayDicom[:, :, lstFilesDCM.index(filenameDCM)] = ds.pixel_array

        self.nhdr = {'filetype':'dicom'}

        # Read the header from low-level dictionary.
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

        if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
            self.nhdr['LocationsInAcquisition'] = len(self.mosaic_slcloc)
        elif self.nhdr['PulseSequenceName'].strip() != '3-Plane':
            self.nhdr['LocationsInAcquisition'] = dims['zdim']

        psdname = self.nhdr.get('PulseSequenceName',None)
        if psdname is not None and '3dfsepcasl' in psdname:
            self.nhdr['ImagesInSeries'] = self.nhdr['LocationsInAcquisition']

        if self.nhdr['AcquisitionMatrix']:
            xdim = self.nhdr['AcquisitionMatrix'][0]
            ydim = self.nhdr['AcquisitionMatrix'][0]
            xsize = self.nhdr['PixelSpacing'][0]
            ysize = self.nhdr['PixelSpacing'][1]
            image_position = self.nhdr['ImagePosition']
            R = dicom_to_rot44(self.nhdr['ImageOrientation'], np.ones([3],float), \
                xsize, ysize, self.nhdr['SpacingBetweenSlices'], xdim, ydim, \
                self.nhdr['LocationsInAcquisition'], self.flip_slice_order)[0]
            if 'MOSAIC'in self.nhdr['ImageFormat'][-1]:
#               Images stored as a mosaic that must be broken up.

                ncol = float(self.nhdr['ColsMosaic']/xdim)
                nrow  = len(self.mosaic_slcloc)/ncol
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
            R = np.identity(4).astype(float)
            image_position = np.zeros(3, float)
            self.nhdr['ndim'] = 2
            self.nhdr['NumberOfFrames'] = 1
            self.nhdr['TypeDim'] = 1
            self.nhdr['LocationsInAcquisition'] = 1
            self.nhdr['ImagesInSeries'] = 1
            self.nhdr['Rows'] = 1
            self.nhdr['Columns'] = 1
            self.nhdr['PixelSpacing'] = [1., 1.]

        zaxis = int(np.dot(R[:3,:3].transpose(), np.arange(3))[2])

        if np.sign(R[zaxis,:3].sum()) == np.sign(image_position[zaxis]):
#           Invalid transformation matrix, flip the starting point.
            dz = -(self.nhdr['LocationsInAcquisition'] - 1)* \
                                self.nhdr['SpacingBetweenSlices']
        else:
            dz = 0

        offset = np.dot(R[:3,:3], np.array([dx, dy, dz]))
        image_position =  image_position + offset
        if self.dicominfo is not None:
            dims['StartLoc'] =  image_position[2]# + offset[2]
        #image_position[:2] =  image_position[:2] + offset[:2]

        self.nhdr['ImagePosition'] = image_position
        R[:3,3] = image_position
        self.nhdr['R'] = R

        self.scan = True
        self.nhdr['StartLoc'] = dims['StartLoc']
        self.nhdr['EndLoc'] = dims['EndLoc']
        self.nhdr['TypeDim'] = dims['TypeDim']
        self.nhdr['NumberOfFrames'] = dims['tdim']
        self.nhdr['dirname'] = dims['dirname']
        self.nhdr['DicomInfo'] = self.dicominfo
        self.nhdr['EchoTimes'] = dims['EchoTimes']

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

        # Uses 'pydicom_series.py' from pydicom/contrib-pydicom which returns a list of separate dicom
        # 'series' based on matching series UID numbers in header. Here, we only get one item in the list.
        # self.rawfmap = dcmseries.read_files(str(self.rawfmap_dir), showProgress=False, readPixelData=False)[0]
        # self.rawfmap_hdr = self.rawfmap.info
        # self.rawfmap_data = self.rawfmap.get_pixel_array()

        # self.real1 = nib.load(rawFilesDict["real1"])
        # self.real1_data = self.real1.get_fdata()
        # self.imag1 = nib.load(rawFilesDict["imaginary1"])
        # self.imag1_data = self.imag1.get_fdata()

        # self.real2 = nib.load(rawFilesDict["real2"])
        # self.real2_data = self.real2.get_fdata()
        # self.imag2 = nib.load(rawFilesDict["imaginary2"])
        # self.imag2_data = self.imag2.get_fdata()

    def checkEchoTimes(self, rawFilesDict):
        phase1json = Path(str(rawFilesDict["phase1"]).split('nii')[0] + 'json')
        phase2json = Path(str(rawFilesDict["phase2"]).split('nii')[0] + 'json')

        with open(phase1json, 'r') as f:
            phase1json_data = json.load(f)
            phase1_echo = phase1json_data['EchoTime']

        with open(phase2json, 'r') as f:
            phase2json_data = json.load(f)
            phase2_echo = phase2json_data['EchoTime']

        if phase2_echo > phase1_echo:
            self.delay = phase2_echo - phase1_echo
        else:
            self.delay = phase1_echo - phase2_echo

    def computeMagnitudes(self):
        mag1_data = np.sqrt(self.real1_data**2 + self.imag1_data**2)
        mag1_data = mag1_data - min(mag1_data.flatten('F'))
        mag1_scalef = 65535 / max(mag1_data.flatten('F'))
        mag1_data = mag1_data * mag1_scalef
        mag1_hdr = nib.Nifti2Header()
        self.mag1_out = nib.Nifti2Image(mag1_data, self.real1.affine, mag1_hdr)
        nib.save(self.mag1_out, self.fmap_dir / 'magnitude_e1.nii.gz')

        mag2_data = np.sqrt(self.real2_data**2 + self.imag2_data**2)
        mag2_data = mag2_data - min(mag2_data.flatten('F'))
        mag2_scalef = 65535 / max(mag2_data.flatten('F'))
        mag2_data = mag2_data * mag2_scalef
        mag2_hdr = nib.Nifti2Header()
        self.mag2_out = nib.Nifti2Image(mag2_data, self.real2.affine, mag2_hdr)
        nib.save(self.mag2_out, self.fmap_dir / 'magnitude_e2.nii.gz')

    def RegisterFmapToT1(self, ses_dir):
        # Register shortest TE magnitude image with anatomical.
        anatdir = ses_dir / 'anat'
        # Probably only one T1w scan, but in case there's multiple, grab the first one
        anatfile = [anat for anat in anatdir.glob("*_T1w.nii*")][0]
        anat = anatdir / anatfile
        mag1 = self.fmap_dir / 'magnitude_e1.nii.gz'
        if anatfile.name.endswith('.gz'):
            anat_resamp = self.fmap_dir / \
                str(anatfile.name).replace('.nii.gz', '_resampled.nii')
        else:
            anat_resamp = self.fmap_dir / \
                str(anatfile.name).replace('.nii', '_resampled.nii')

        #  Resample the anatomical data to the fieldmap image size.
        if anat_resamp.exists():
            os.remove(anat_resamp)
        subprocess.run(['3dresample', '-prefix', anat_resamp, '-inset',
                        anat, '-master', mag1], stdout=subprocess.PIPE, text=True).stdout

        self.mag1_reg2anat = self.fmap_dir / mag1.name.replace('e1', 'e1_reg2anat')
        if self.mag1_reg2anat.exists():
            os.remove(self.mag1_reg2anat)
        # Register the field-map magnitude to the anatomical.
        subprocess.run(['3dvolreg', '-rotcom', '-Fourier', '-twopass', '-prefix', self.mag1_reg2anat,
                        '-verbose', '-base', anat_resamp, mag1], stdout=subprocess.PIPE, text=True).stdout


# ????????????????
#         fd = os.popen(cmd)
#         lines = fd.read()
#         fd.close()
#         lines = lines.split('\n')
#         chg_perm("%s_reg.nii" % anat_resamp)

# #       Extract the rotate command from the 3dvolreg output.
#         for line in lines:
#             if "3drotate" in line and len(line.split()) > 3:
#                 tmpfile = "%s/3drotate_%s_cmd.txt" % (self.outdir,hdr['plane'])
#                 i = 0
#                 while os.access(tmpfile,F_OK):
#                     i = i + 1
#                     tmpfile = "%s/3drotate_%s_cmd_%d.txt" % \
#                                                 (self.outdir,hdr['plane'],i)
#                 sys.stdout.write(\
#                 "Fragmentary rotate command written to: %s\n" % tmpfile)
#                 ftmp = open(tmpfile,"w")
#                 ftmp.write(line.strip())
#                 ftmp.close()
#                 break


    def StripBrain(self, ses_dir):
        # Create brain mask.
        if self.mag1_reg2anat.name.endswith('.gz'):
            self.mag1_reg2anat_brain = self.fmap_dir / \
                str(self.mag1_reg2anat.name).replace(
                    'reg2anat.nii.gz', 'reg2anat_brain')
        else:
            self.mag1_reg2anat_brain = self.fmap_dir / \
                str(self.mag1_reg2anat.name).replace(
                    'reg2anat.nii', 'reg2anat_brain')
        self.mask = self.fmap_dir / \
            str(self.mag1_reg2anat.name).replace('reg2anat', 'reg2anat_brain_mask')

        if self.mask.exists():
            os.remove(self.mask)

        subprocess.run(
            ['bet2', self.mag1_reg2anat, self.mag1_reg2anat_brain, '-m', '-f', '.3', '-v'])
        self.mask = self.fmap_dir / \
            str(self.mag1_reg2anat.name).replace('reg2anat', 'reg2anat_brain_mask')

    def createMask(self):
        # Read mask created by bet.
        mask_affine = nib.load(self.mag1_reg2anat).affine
        mask = nib.load(self.mask).get_fdata()
        struct = np.ones([1, 3, 3], float)
        self.fmap_mask = binary_dilation(mask, struct, 1).astype(mask.dtype)
        fmap_mask_hdr = nib.Nifti2Header()
        self.fmap_mask_out = nib.Nifti2Image(self.fmap_mask, mask_affine, fmap_mask_hdr)
        nib.save(self.fmap_mask_out, self.fmap_dir / 'fieldmap_mask.nii')

    def computePhases(self):
        self.phase1_data = np.arctan2(self.imag1_data, self.real1_data)
        phase1_hdr = nib.Nifti2Header()
        self.phase1_out = nib.Nifti2Image(
            self.phase1_data, self.real1.affine, phase1_hdr)
        nib.save(self.phase1_out, self.fmap_dir / 'phase_e1.nii.gz')

        self.phase2_data = np.arctan2(self.imag2_data, self.real2_data)
        phase2_hdr = nib.Nifti2Header()
        self.phase2_out = nib.Nifti2Image(
            self.phase2_data, self.real2.affine, phase2_hdr)
        nib.save(self.phase2_out, self.fmap_dir / 'phase_e2.nii.gz')

    def unwrapPhases(self):
        fmap_mask = self.fmap_dir / 'fieldmap_mask.nii'
        mag1 = self.fmap_dir / 'magnitude_e1.nii.gz'
        phase1 = self.fmap_dir / 'phase_e1.nii.gz'
        phase1_unwrpd = self.fmap_dir / 'phase_e1_unwrapd.nii.gz'
        subprocess.run(['prelude', '-a', mag1, '-p', phase1, '-u',
                        phase1_unwrpd, '-m', fmap_mask, '-v'])

        mag2 = self.fmap_dir / 'magnitude_e2.nii.gz'
        phase2 = self.fmap_dir / 'phase_e2.nii.gz'
        phase2_unwrpd = self.fmap_dir / 'phase_e2_unwrapd.nii.gz'
        subprocess.run(['prelude', '-a', mag2, '-p', phase2, '-u',
                        phase2_unwrpd, '-m', fmap_mask, '-v'])

    def createFieldmap(self):
        self.phs1 = nib.load(
            self.fmap_dir / 'phase_e1_unwrapd.nii.gz').get_fdata()
        self.phs2 = nib.load(
            self.fmap_dir / 'phase_e2_unwrapd.nii.gz').get_fdata()

        """ Subtract unwrapped phase maps, scale, set centroid to zero."""
#        mask = where(abs(self.fmap) > 0.,1.,0.)
        self.fmap = self.fmap_mask * (self.phs2 - self.phs1)

        # Phase change in radians/sec.
        self.fmap = 1000. * self.fmap / self.delay

#       Create coarse mask guaranteed not to remove brain voxels.
        self.coarse_mask = np.where(self.fmap_mask +
                                    np.where(self.fmap != 0., 1, 0), 1., 0.)

#       Filter with a median filter 3 pixels square.  This removes
#       single-pixel outliers.
        median_filter(self.fmap, size=3, mode='constant', cval=0.)

        # Set correction to zero at the centroid of the image.
        msk = np.where(abs(self.fmap) > 0., 1., 0.)
        sumall = sum(msk.flat)  # Collapse over z dimension.
        tmp = sum(msk, 0)  # Collapse over z dimension.
        x_centroid = np.dot(np.arange(self.xdim).astype(
            float), sum(tmp, 0))/sumall
        y_centroid = np.dot(np.arange(self.ydim).astype(
            float), sum(tmp, 1))/sumall
        z_centroid = np.dot(np.arange(self.zdim).astype(float),
                            sum(np.reshape(msk, [self.zdim, self.ydim * self.xdim]), 1)) / sumall
        ix_centroid = int(x_centroid + .5)
        iy_centroid = int(y_centroid + .5)
        iz_centroid = int(z_centroid + .5)

        print("XYZ centers of mass: %f, %f, %f") % \
            (x_centroid, y_centroid, z_centroid)
        print("XYZ centers of mass coordinates: %d, %d, %d") % \
            (ix_centroid, iy_centroid, iz_centroid)
#        print "Value of phase difference at center of mass: %f" % \
#                        self.fmap[iz_centroid,iy_centroid,ix_centroid]
        ctr_value = self.fmap[iz_centroid, iy_centroid, ix_centroid]
        self.fmap = msk * (self.fmap - ctr_value)

    def writeFieldmap(self, ses_dir):
        self.fmap_file = self.fmap_dir / '_'.join([ses_dir.parent.name, ses_dir.name, 'acq-EPIHz_fieldmap.nii'])
        nib.save(self.fmap, self.fmap_file)


#       Write coarse mask.
#        hdr_mask = self.hdr_out.copy()
#        hdr_mask['datatype'] = 'short'
#        writefile(self.coarse_mask_file, self.coarse_mask, hdr_mask)

    # def orient2LPI(self):
    #     self.realfieldmap_rads = self.rawfmapfile_1.replace("_rawfmap_e1","rads_fmap").replace("Fieldmap","RealFieldmap")
    #     subprocess.call(["3dresample", "-input", "tmp.phasediff.rads.nii.gz", "-prefix", self.realfieldmap_rads, "-orient", "LPI"])

    # def conv2Hz(self):
    #     self.realfieldmap_Hz = self.rawfmapfile_1.replace("_rawfmap_e1","Hz_fmap").replace("Fieldmap","RealFieldmap")
    #     subprocess.call(["3dcalc", "-a", self.realfieldmap_rads, "-expr", "a*0.1592", "-prefix", self.realfieldmap_Hz])

    # def appendsidecar(self):

    #     # Append the BIDS sidecar for each fieldmap with the name of the associated scan file
    #     fmapjson = self.rawfmapfile_1.replace('.nii','.json')
    #     realfmapjson = self.realfieldmap_Hz.replace('.nii','.json')

    #     with open(fmapjson) as jsonfile:
    #         sidecar = json.load(jsonfile)
    #         sidecar['EchoTime1'] = '.007'
    #         sidecar['EchoTime2'] = '.010'
    #         sidecar['Units'] = 'Hz'

    #         if self.fmaptype == "DTI":
    #             fmaps = Path(self.fmap_dir)
    #             fmap_intendedfor_path = fmaps.parents[0] / 'dwi'
    #             scanlist = (scan for scan in fmap_intendedfor_path.iterdir() if str(scan).endswith('.nii'))
    #             fmapassoclist=[]
    #             for scan in scanlist:
    #                 fmapassoclist.append(str(Path(*scan.parts[-4:])))
    #             sidecar['IntendedFor'] = fmapassoclist

    #             tempfiles = (tempfile for tempfile in self.fmap_dir.iterdir() if any([tempfile.name.startswith('tmp.'),tempfile.name.__contains__('DTI_rawfmap_e1')]))
    #             for tempfile in tempfiles:
    #                 os.remove(tempfile)

    #             with open(realfmapjson, 'w+') as outfile:
    #                 json.dump(sidecar, outfile, indent=4)

    #         if self.fmaptype == "EPI":
    #             fmaps = Path(self.fmap_dir)
    #             fmap_intendedfor_path = fmaps.parents[0] / 'func'
    #             scanlist = (scan for scan in fmap_intendedfor_path.iterdir() if scan.name.endswith('.nii'))
    #             fmapassoclist=[]
    #             for scan in scanlist:
    #                 fmapassoclist.append(str(Path(*scan.parts[-4:])))
    #             sidecar['IntendedFor'] = fmapassoclist

    #             tempfiles = (tempfile for tempfile in self.fmap_dir.iterdir() if any([tempfile.name.startswith('tmp.'),tempfile.name.__contains__('EPI_rawfmap_e1')]))
    #             for tempfile in tempfiles:
    #                 os.remove(tempfile)

    #             with open(realfmapjson, 'w+') as outfile:
    #                 json.dump(sidecar, outfile, indent=4)

    # def fugue(self):
    #     self.dwicorr = self.dwi.parent / Path(str(self.dwi.parts[-1]).replace(".nii", ".corr.nii"))
    #     print(str(self.dwicorr))
    #     subprocess.call(["fugue", "-v", "-i", self.dwi, "--loadfmap="+str(self.phasediff_rads), "--dwell=0.000568", "-u", self.dwicorr])

    def main(self, ses_dir):
        rawFilesDict = self.findfmapfiles(ses_dir)
        self.get_native_header(scan=True)
        # self.getfmapFiles(rawFilesDict)
        # self.checkEchoTimes(rawFilesDict)
        # self.computeMagnitudes()
        # self.computePhases()
        # mag1_reg2anat = self.RegisterFmapToT1(ses_dir)
        # self.StripBrain(ses_dir)
        # self.createMask()
        # self.unwrapPhases()
        # self.createFieldmap()
        # self.writeFieldmap()
        # self.computephase()
        # self.extractmag()
        # self.stripmag()
        # self.erodemag()
        # self.registermask()
        # self.prelude()
        # self.orient2LPI()
        # self.conv2Hz()
        # self.appendsidecar()
        # self.fugue()


if __name__ == '__main__':
    mc = makefmaps()


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

class Header(SubHeader, NativeHeader):
    """
    Purpose:
        Read native header, create sub-header, and pack into a single 
        dictionary to comprise the header.
    Methods:
        __init__(filename,scan=False
            Reads header.
            Arguments:
                filename: filename to be read.
            Keyword:
                scan: only has meaning for the dicom format. If true, every
                file in the directory is examined.
        get_header(scan=False)
            Keyword:
                scan: only has meaning for the dicom format. If true, every
                file in the directory is examined.
            Returns:
                header: A dictionary containing elements common to all file
                    types, a sub-header, and the native header.
      Attributes:
             header.
    """
    def __init__(self, path=None, scan=False, native_header=None, \
                 ignore_yaml=False):

        self.hdr = None
        self.shdr = {}
        self.nhdr = None
        self.scan = scan
        self.filetype_to_nhdrmeth = {\
            'dicom':self._get_dicom_header, \
            'brik':self._get_afni_header, \
            'ni1':self._get_nifti_header, \
            'n+1':self._get_nifti_header, \
            'analyze':self._get_analyze_header, \
            'tes':self._get_voxbo_header, \
            'ge_data':self._get_GE_ipfile_header, \
            'ge_ifile':self._get_GE_ipfile_header, \
            'none':self._get_none_header}
        self.filetype_to_shdrmeth = {\
            'dicom':self._get_dicom_shdr, \
            'brik':self._get_afni_shdr, \
            'ni1':self._get_nifti_shdr, \
            'n+1':self._get_nifti_shdr, \
            'analyze':self._get_analyze_shdr, \
            'tes':self._get_voxbo_shdr, \
            'ge_data':self._get_GE_ipfile_shdr, \
            'ge_ifile':self._get_GE_ipfile_shdr, \
            'none':self._get_none_shdr}
        self.filename = path

        if native_header:
            self.nhdr = native_header
        elif not ignore_yaml:
            if os.path.isdir(path):
#               Check for yaml file.
                files = os.listdir(path)
                if len(files) > 10:
                    for fname in files:
#                       Look for a yaml file.
                        if fname.endswith('.yaml'):
#                           It contained the header. 
#                            fname = os.path.abspath(fname)
                            fname = '%s/%s' % (path, fname)
                            self.ReadYaml(fname)
                            break
            elif path.endswith('.yaml'):
                self.ReadYaml(path)

        if self.hdr is None:  
            self.hdr = self.get_header(scan=scan)

    def ReadYaml(self, fname):
        """
        Read header from yaml file. It has apparently already been read
        and then rewritten in this format.
        """
        dirname = os.path.dirname(fname)
        self.hdr = self.read_hdr_from_yaml(fname)
        if self.hdr is None:
            return
        if self.hdr.has_key('imgfile'):
            if isinstance(self.hdr['imgfile'], tuple):
                iname = self.hdr['imgfile'][0].\
                            join(self.hdr['imgfile'][1])
            else:
                iname = self.hdr['imgfile']
            self.hdr['imgfile'] = '%s/%s' % \
                (dirname, os.path.basename(iname))
#                (dirname, os.path.basename(self.hdr['imgfile']))
        if self.hdr.has_key('native_header'):
            nhdr = self.hdr['native_header']
            if nhdr.has_key('DicomInfo'):
                nhdr['DicomInfo']['dims']['dirname'] = dirname
            if nhdr.get('FileName', None):
                nhdr['FileName'] = '%s/%s' % \
                    (dirname, os.path.basename(nhdr['FileName']))
            nhdr['dirname'] = dirname
        if self.hdr['filetype'] == 'dicom':
            if os.path.exists(self.hdr['imgfile']):
                dicom_name = self.hdr['imgfile']
            else:
                dirname = os.path.dirname(fname)
                fnames = os.listdir(dirname)
                for fname in fnames:
                    fullname = '%s/%s' % (dirname, fname)
                    if isdicom(fullname):
                        dicom_name = fullname
                        break
                else:
                    self.dcm = None
                    return
            self.dcm = Dicom(dicom_name, nhdr=self.hdr['native_header'])
            if self.hdr is not None:
                self.shdr = self.hdr['subhdr']
                self.dcm.nhdr = self.hdr['native_header']
                self.nhdr = self.dcm.nhdr
                if self.nhdr.has_key('DicomInfo'):
                    self.dcm.dicominfo = self.nhdr['DicomInfo']
                    dims = self.dcm.dicominfo['dims']
                    self.dcm.scan = True
                    self.scan = True
                else:
                    self.dcm.scan = False
                    self.scan = False
 
    def get_header(self, scan=False):
#       Fill in header fields from prototype header.
    
#        if  (self.scan or (not scan and self.scan is not None):
        if self.hdr is not None and self.scan == scan:
            return self.hdr
        if self.filename:
            self.hdrname, self.hdrsuffix = get_hdrname(self.filename)
            self.filetype = file_type(self.hdrname)
        else:
            self.filetype = self.nhdr['filetype']
        if self.filetype is None:
            return None
#        sys.stdout.write( ' 3c ' + self.timer.ReadTimer())
        self.file_nhdr_meth = self.filetype_to_nhdrmeth[self.filetype]
        self.file_shdr_meth = self.filetype_to_shdrmeth[self.filetype]
        self.shdr = self._get_none_shdr

#       Read native header.
        if self.nhdr is not None:
            if self.nhdr.has_key('dicominfo'):
                self.scan = True
            else:
                self.scan = False
        else:
            self.nhdr = apply(self.file_nhdr_meth, ([scan]))
            self.scan = scan
#        sys.stdout.write( ' 4c ' + self.timer.ReadTimer() )

        if self.nhdr is None:
            self.hdr = None
            return None

#       Read subheader.
        self.shdr = apply(self.file_shdr_meth, ())
#        sys.stdout.write( ' 5c ' + self.timer.ReadTimer())
        orient_string = R_to_orientstring(self.protohdr['R'])
        if self.filename:
            if self.filetype == 'dicom':
                imgfile = os.path.splitext(self.filename)[0]
            else:
                imgfile = os.path.splitext(self.filename)[0] + \
                        hexts.get(self.hdrsuffix, self.hdrsuffix)
        else:
            imgfile = ''
        if self.protohdr['dims'][5] > 1:
            ndim = 5
        elif self.protohdr['dims'][4] > 1:
            ndim = 4
        elif self.protohdr['dims'][3] > 1:
            ndim = 3
        else:
            ndim = 2
        dims = ones([6],int)
        sizes = zeros([5],float)
        dims[:ndim] = self.protohdr['dims'][1:ndim+1]
        sizes[:ndim] = self.protohdr['sizes'][:ndim]
        self.hdr = {'xdim':long(self.protohdr['dims'][1]), \
            'ydim':long(self.protohdr['dims'][2]), \
            'zdim':long(self.protohdr['dims'][3]), \
            'tdim':long(self.protohdr['dims'][4]), \
            'mdim':long(self.protohdr['dims'][5]), \
            'dims':dims.astype(long), \
            'ndim':ndim, \
            'xsize':self.protohdr['sizes'][0], \
            'ysize':self.protohdr['sizes'][1], \
            'zsize':self.protohdr['sizes'][2], \
            'tsize':self.protohdr['sizes'][3], \
            'msize':self.protohdr['sizes'][4], \
            'sizes':sizes, \
            'x0':self.protohdr['origin'][0], \
            'y0':self.protohdr['origin'][1], \
            'z0':self.protohdr['origin'][2], \
            'num_voxels':self.protohdr['vox_info'][0], \
            'bitpix':self.protohdr['vox_info'][1], \
            'datatype':self.protohdr['vox_info'][2], \
            'swap':self.protohdr['vox_info'][3], \
            'start_binary':self.protohdr['vox_info'][4], \
            'scale_factor':self.protohdr['scale'][0], \
            'scale_offset':self.protohdr['scale'][1], \
            'R':self.protohdr['R'], \
            'orientation':orient_string, \
            'plane':orientstring_to_plane(orient_string), \
            'filetype':self.filetype, \
            'imgfile':imgfile, \
            'subhdr':self.shdr, \
            'native_header':self.nhdr}
#        sys.stdout.write( ' 5d ' + self.timer.ReadTimer() + '\n')
        return self.hdr

    def convert_to_yaml(self):
        add_ndarray_to_yaml()
        hdr1 = self.hdr.copy()
        hdr1['imgfile'] = os.path.basename(hdr1['imgfile'])
        return yaml.dump(self.hdr)

    def write_hdr_to_yaml(self, filename):
        """
        Write header to a yaml-encoded file.
        """
        if self.scan == False and self.hdr['filetype'] == 'dicom':
            raise UsageError(\
            "Cannot write dicom headers to a yaml file unless the scan option is True.\nfile: %s" % filename)
#       Tell yaml how to handle numpy arrays.
        add_ndarray_to_yaml()
        hdr1 = self.hdr.copy()
        hdr1['imgfile'] = os.path.basename(hdr1['imgfile'])
        try:
            f = open(filename, "wb")
            f.write(yaml_magic_code) # Write the magic code.
            f.write(yaml.dump(self.hdr))
            f.close()
        except IOError:
            raise IOError(\
            'file_io:: Could not write to yaml file: %s' % filename)

    def read_hdr_from_yaml(self, filename):
        """
        Read header from a yaml-encoded file.
        """
        try:
            f = open_gzbz2(filename, "rb")
        except IOError:
            raise IOError(\
            'file_io:: Could not read from yaml file: %s' % filename)
        code = f.read(len(yaml_magic_code))
        if code != yaml_magic_code:
            f.close()
            hdr = None
#            raise UsageError(\
#            'file_io: Invalid magic code in alleged  yaml file: %s' % filename)
        else:
#           Tell yaml how to handle numpy arrays.
            add_ndarray_to_yaml()
            hdr = yaml.load(f.read())
            f.close()
        return hdr


        
#***************************
def rot44_inv(M, dims, sizes):
#***************************

    """ 
    Invert a 4x4 transformation matrix with a unitary rotation matrix.
        dims: 3x1 vector of image dimensions, array((xdim, ydim, zdim))
        sizes: 3x1 vector of voxel sizes, array((xsize, ysize, zsize))
        dims and sizes are both specified in the original coordinate system.
    """

    Minv = zeros([4, 4], float)
    dsizes = diag(sizes)
    R = dot(M[:3, :3], dsizes)
    x0in = M[:3, 3]
    fov = (dims - 1.)*sizes
    direction = dot(R.transpose(), abs(R)) # dir = -1 for reversed traversals
    flips = ((identity(3) - direction)/2).round()
    x0 = dot(R.transpose(), dot(dsizes, x0in)) + dot(flips, fov)
    Minv[:3, :3] = dot(dsizes, R.transpose())

    Minv[:3, 3] = x0 #dot(dsizes, x0)
    return Minv