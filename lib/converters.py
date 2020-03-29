#!/usr/bin/env python3
# coding: utf-8

import bz2
import json
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import tools
from pathlib import Path
from makefmaps import make_fmaps



# Main class
class convertScans():

    def __init__(self, studypath, outputpath, scanstoskip, inputidfile, ids):
        self.studypath = Path(studypath)

        # Did a subject ID list get passed? If so, parse it, use its contents
        if inputidfile:
            with open(inputidfile, 'r') as idfile:
                sids = idfile.readlines()
                sids = [s.strip('\n') for s in sids]
                subj_dirs = (subj_dir for subj_dir in sorted(self.studypath.iterdir())
                             if any(x in str(subj_dir) for x in sids))
        # Did a list of subject IDS get passed? If so, process only scans in those folders
        elif ids:
            subj_dirs = (subj_dir for subj_dir in sorted(self.studypath.iterdir()) if
                         any(x in subj_dir.name for x in ids))
        # Default: Process all scans in the studypath folder
        else:
            print("SUBJECT IDS NOT SPECIFIED...")
            subj_dirs = (subj_dir for subj_dir in sorted(self.studypath.iterdir()))

        for subj_dir in sorted(subj_dirs):
            print(subj_dir)

            dicoms_dir = subj_dir / 'dicoms'
            if len(list(dicoms_dir.glob('*.tgz'))) > 0:
                startsubjdir_str = ''.join(['TGZ NOW CONVERTING PARTICIPANT: ', subj_dir.name])
                print('\n' + '#'*(len(startsubjdir_str)) + '\n' + startsubjdir_str +
                      '\n' + '#'*(len(startsubjdir_str)) + '\n')
                convtgz = tgz2NIFTI(subj_dir, outputpath, scanstoskip)
            elif dicoms_dir.glob('info.txt'):
                startsubjdir_str = ''.join(['BZ2 NOW CONVERTING PARTICIPANT: ', subj_dir.name])
                print('\n' + '#'*(len(startsubjdir_str)) + '\n' + startsubjdir_str +
                      '\n' + '#'*(len(startsubjdir_str)) + '\n')
                convbz2 = bz2NIFTI(subj_dir, outputpath, scanstoskip)


# TGZ compressed archives are found in folders generated post-2018ish (after a GE update)
# e.g., CEDA, LOKI, late subject Youth PTSD
class tgz2NIFTI():

    fmapassoclist = list()

    def __init__(self, subj_dir, outputpath, scanstoskip):

        # Input and output paths to pathlib.posixpath
        self.outputpath = Path(outputpath)

        self.dicoms_dir = Path(subj_dir / 'dicoms')
        if self.dicoms_dir.exists():
            for dicom_tgz in sorted(dicoms_dir.glob('*.tgz')):
                if not any(x in dicom_tgz.name for x in scanstoskip):
                    self.unpack_tgz(dicom_tgz)
                    self.getbidsparams()
                    self.conv_dcms()
                    self.cleanup()
                if self.dicoms_dir.parent.name[0] == '_':
                    self.process_fmaps()
                else:
                    self.fixfmaps()
        else:
            nodicomdir_str = ''.join(['SKIPPING PARTICIPANT: ', subj_dir.name, ' - DICOMS SUBDIRECTORY NOT FOUND.'])
            print('\n\n' + nodicomdir_str + '\n\n')
            next

    # Parsing the dicom tgz archive file name to get the time point and subject ID, copy the file to a local temp
    # directory, then decompress it
    def unpack_tgz(self, dicom_tgz):

        # TGZ archived dicoms have naming convention: EZZZZZ.sYYYY.Scan_Description.tgz
        # where Z is an internal GE subject counter and Y is the scan's sequence number
        # If a RUN NUMBER is included, it will be in the Scan_Description text :(
        self.dicoms_dir = dicom_tgz.parents[0]

        # Locate the system's temp directory and set it to a variable
        self.tmpdir = Path(tempfile.gettempdir())

        # Copy the dicom tgz archive file to the temp directory for faster processing
        self.dicom_tmp = self.tmpdir / dicom_tgz.name
        shutil.copy(dicom_tgz, self.dicom_tmp)

        # Decompress the TGZ dicom archive in the temp directory
        dicom_tmp_open = tarfile.open(self.dicom_tmp, 'r:gz')
        scanstart_str = ''.join(['\n', 'STARTING SCAN ', self.dicom_tmp.name])
        print('='*(len(scanstart_str)-1) +
              scanstart_str + '\n' +
              '='*(len(scanstart_str)-1))

        print(tools.stru('\nCOPYING AND DECOMPRESSING ARCHIVE FILE') + '...' + '\n')
        dicom_tmp_open.extractall(path=self.tmpdir)

        # Unpacking the TGZ archive will create a directory (sYYYY.Scan_Description)
        # holding a separate .dcm file for each slice in the volume
        # Get the name and path of the unpacked directory
        self.dicom_tmp_dirname = os.path.commonprefix(dicom_tmp_open.getnames())
        self.dicom_tmp_dirpath = Path(self.tmpdir, self.dicom_tmp_dirname)

    # Parse BIDS parameters from the fully qualified path of the scan
    def getbidsparams(self):

        # Subject directories might be formatted as _XXX (time 1) or _XXXrescan (or _XXX_rescan)
        # Check if the leading character of the subject directory name is '_', and if so, set the
        # time point to 2 if the last four characters are 'rescan', 1 if they are not. Get the subjid
        # from characters 2-4.
        # If the leading charcter is NOT '_', set the time point to the last character of the
        # subject directory name, and the subject id to the charcters before the '_'
        if self.dicoms_dir.parent.name[0] == '_':
            self.subjid = self.dicoms_dir.parent.name[1:4]
            if self.dicoms_dir.parent.name[-6:] == 'rescan':
                self.timept = 2
            else:
                self.timept = 1
        else:
            self.subjid = self.dicoms_dir.parent.name.split('_')[0]
            self.timept = self.dicoms_dir.parent.name[-1]
        # Split the name of the unpacked directory to get the HERI scan description
        self.raw_scantype = self.dicom_tmp_dirname.split('.')[1]

        # # Split the name of the dicom tgz archive file's parent directory (XXXX_CY; where X is the subject id and
        # # Y is the time) to get the study wave (time point; e.g., 1, 2) and the subject ID (e.g., 1001)

        # self.subjid = self.dicoms_dir.parent.name.split('_')[0]

        # Get the scan's sequence number (e.g., 0003) as an integer
        # raw_seqno = int(self.dicom_tmp_dirname.split('.')[0][1:])

        # Get the wave number (time point) as an integer - necessary???
        # raw_timept = int(self.timept)

        # Pull the scan's description from the dicom tgz archive name
        # dcm = pydicom.dcmread(Path(self.tgz_dcm_dirpath / 'i.000001.dcm'))

        # Remove BIDS-prohibited characters from the acquisition label
        for c in ['(', ')', '-', '_', ' ', '/', 'FieldMap:', ':']:
            if c in self.raw_scantype:
                bidslabel = self.raw_scantype.replace(c, '')
        bids_acqlabel = 'acq-' + bidslabel

        # Null the following BIDS parameter labels (in case they're already set)
        bids_runno = ''
        bids_tasklabel = ''
        bids_pedir = ''
        bids_tasklabel = ''

        # Handle each scan based on the contents of its acquisition label (bids_acqlabel; if necessary...)

        # If the scan is a BRAVO (structural), create an acquisition label
        if self.raw_scantype.__contains__('BRAVO'):
            bids_acqlabel = 'AXFSPGRBRAVO'

        # If the scan is an EPI (fMRI):
        #    1. Do not create an acquisition label
        #    2. Create a task label (bids_tasklabel)
        if self.raw_scantype.__contains__('EPI_'):
            bids_acqlabel = ''
            raw_scantype_lc = self.raw_scantype.lower().replace('-', '')
            if raw_scantype_lc.__contains__('perspective'):
                bids_tasklabel = 'Perspective'
            elif raw_scantype_lc.__contains__('nback'):
                bids_tasklabel = 'N-back'
            elif raw_scantype_lc.__contains__('resting'):
                bids_tasklabel = 'Resting'

            # 3. Add all similarly named scans to a list, sorted by sequence number (e.g., sXXXX)
            taskscan_list = list(scan.name for scan in sorted(self.dicoms_dir.glob('*.tgz'))
                                 if str(scan).__contains__(self.raw_scantype))

            # 4. Set the task run number (bids_runno) equal to the current scan's index in the list
            #    This fix allows us to convert the participant-varying sequence numbers to run numbers
            if len(taskscan_list) > 1:
                for item in taskscan_list.__iter__():
                    print(item)
                    if self.raw_scantype in item:
                        i = taskscan_list.index(item)
                        epi_runcount = i + 1
                        bids_runno = 'run-' + str(epi_runcount)

        # If the scan is a 'WATER_Fieldmap' (magnitude volume), create a run number label
        # (using the process described above) to differentiate it from other magnitude volumes
        if self.raw_scantype.__contains__('WATER_Fieldmap'):
            self.fmapsneedproc = False
            bids_acqlabel = 'Magnitude'
            fmapmaglist = list(scan.name for scan in sorted(self.dicoms_dir.glob('*.tgz'))
                               if str(scan).__contains__(self.raw_scantype))
            for item in fmapmaglist.__iter__():
                if self.raw_scantype in item:
                    i = fmapmaglist.index(item)
                    fmapmag_runcount = i + 1
                    bids_runno = 'run-' + str(fmapmag_runcount)

        # If the scan is a 'FieldMap_Fieldmap' (phase difference volume), create a run number label
        # (using the process described above) to differentiate it from other phaase difference volumes
        if self.raw_scantype.__contains__('FieldMap_Fieldmap'):
            bids_acqlabel = 'FieldMap'
            fmapfmaplist = list(scan.name for scan in sorted(self.dicoms_dir.glob('*.tgz'))
                                if str(scan).__contains__(self.raw_scantype))
            for item in fmapfmaplist.__iter__():
                if self.raw_scantype in item:
                    i = fmapfmaplist.index(item)
                    fmapfmap_runcount = i + 1
                    bids_runno = 'run-' + str(fmapfmap_runcount)

        # If the scan is a NODDI, parse the phase encoding polarity from the filename
        # and create a phase encoding direction label (bids_pedir; PA=0; AP=1)
        if self.raw_scantype.__contains__('NODDI'):
            bids_acqlabel = 'NODDI'
            if self.raw_scantype.__contains__('pepolar0'):
                bids_pedir = 'dir-PA'
            elif self.raw_scantype.__contains__('pepolar1'):
                bids_pedir = 'dir-AP'

        # Create the BIDS participant ID label (e.g., sub-001)
        self.bids_participantID = 'sub-' + self.subjid

        # Create the BIDS wave (timepoint) label - two digits (e.g., ses-01)
        self.bids_scansession = 'ses-' + str(self.timept).zfill(2)

        # Create the BIDS scan modality label (e.g., '_T1w')
        bids_scanmode = tools.scan2bidsmode(self.raw_scantype)

        # Echo all the BIDS parameters for this scan
        print(tools.stru('PARSING BIDS PARAMETERS') + '...')
        print('Participant:', self.bids_participantID)
        print('Wave:', self.bids_scansession)
        if len(bids_acqlabel) > 0:
            print('ACQ Label:', bids_acqlabel.replace('acq-', ''))
        print('Modality Label:', bids_scanmode)
        if len(bids_tasklabel) > 0:
            print('Task Label:', bids_tasklabel.replace('task-', ''))
        if bids_runno:
            print('Run #:', bids_runno.replace('run-', ''))
        if len(bids_pedir) > 0:
            print('Phase Encoding Label:', bids_pedir)
        print('Raw scan type: ', self.raw_scantype)

        # Collect all the BIDS parameters into a list
        bidsparamlist = [self.bids_participantID]
        bidsparamlist.append(self.bids_scansession)
        if len(bids_tasklabel) > 0:
            bidsparamlist.append(bids_tasklabel)
        if len(bids_acqlabel) > 0:
            bidsparamlist.append(bids_acqlabel)
        if len(bids_runno) > 0:
            bidsparamlist.append(bids_runno)
        if len(bids_pedir) > 0:
            bidsparamlist.append(bids_pedir)
        bidsparamlist.append(bids_scanmode)

        # Join the BIDS parameter list items into an underscore delimited string
        self.dcm2niix_label = '_'.join(bidsparamlist)

        # Set the BIDS output directory
        self.bids_outdir = Path(self.outputpath, self.bids_participantID, self.bids_scansession,
                                tools.scan2bidsdir(self.raw_scantype))

    # Convert scans using dcm2niix, using filename self.dcm2niix_label and output directory self.bids_outdir. Then
    # run through some coding gymnastics to add tasknames, multiband acceleration, and associated fieldmaps to
    # the BIDS sidecar files
    def conv_dcms(self):

        # Make the BIDS output directory for this specific scan, overwriting the directory if it exists
        self.bids_outdir.mkdir(exist_ok=True, parents=True)

        # Start converting the scans using Chris Rorden's dcm2niix, providing the BIDS label created above
        print('\n' + tools.stru('BEGINNING SCAN CONVERSION') + '...')
        subprocess.run(['dcm2niix', '-f', self.dcm2niix_label,
                        '-o', self.bids_outdir, '-w', '2', self.dicom_tmp_dirpath])

        # If the original scan name contains HB2 (i.e., likely is a NODDI), append multiband
        # acceleration factor to the BIDS sidecar file
        if self.raw_scantype.__contains__('HB2'):
            jsonfilepath = Path(self.bids_outdir, self.dcm2niix_label + '.json')
            with open(jsonfilepath) as jsonfile:
                sidecar = json.load(jsonfile)
            sidecar['MultibandAccelerationFactor'] = 2
            with open(jsonfilepath, 'w') as f:
                json.dump(sidecar, f, indent=4)

        # If the scan is an fmri ('EPI'), append the taskname, and multiband
        # acceleration factor to the BIDS sidecar file - inclusion of MB3 in filenames is inconsistent
        if self.raw_scantype.__contains__('EPI_'):
            jsonfilepath = Path(self.bids_outdir, self.dcm2niix_label + '.json')
            with open(jsonfilepath) as jsonfile:
                sidecar = json.load(jsonfile)
            sidecar['TaskName'] = self.raw_scantype
            sidecar['MultibandAccelerationFactor'] = 3
            with open(jsonfilepath, 'w') as f:
                json.dump(sidecar, f, indent=4)

        # If the scan is a WATER_Fieldmap (magnitude image), grab the names of scans since the last
        # WATER_Fieldmap.  We'll add these to the 'IntendedFor' field in the BIDS sidecar.
        if self.raw_scantype.__contains__('WATER'):
            jsonfilepath = Path(self.bids_outdir, self.dcm2niix_label + '.json')
            print(jsonfilepath)
            with open(jsonfilepath) as jsonfile:
                sidecar = json.load(jsonfile)
            sidecar['IntendedFor'] = self.fmapassoclist
            with open(jsonfilepath, 'w') as f:
                json.dump(sidecar, f, indent=4)
            self.fmapassoclist = list()
        else:
            # If the scan is NOT a WATER_Fieldmap, but IS an EPI or NODDI add the scan's BIDS path
            # to a running list (self.fmapassoclist) of scans associated with an upcoming fieldmap.
            # If the list does not exist (NameError), create it.
            try:
                self.fmapassoclist
                if self.raw_scantype.__contains__('EPI') or self.raw_scantype.__contains__('NODDI'):
                    self.fmapassoclist.append(self.bids_scansession + '/' +
                                              tools.scan2bidsdir(self.raw_scantype) + '/' +
                                              self.dcm2niix_label + '.nii')
            except NameError:
                self.fmapassoclist = list(self.dcm2niix_label + '.nii')

        print(tools.stru('\nSCAN ' + self.dicom_tmp_dirpath.parts[-1] + ' COMPLETED!\n'))

    def cleanup(self):
        # Delete the temporary directory we created above
        # shutil.rmtree(self.dicom_tmp_dirpath)
        os.unlink(self.dicom_tmp)

    def process_fmaps(self):
        fmap_dir = Path(self.outputpath, self.bids_participantID, self.bids_scansession) / 'fmap'
        # session_dir = Path(self.outputpath, self.bids_participantID, self.bids_scansession)
        make_fmaps(fmap_dir, 'EPI')
        make_fmaps(fmap_dir, 'DTI')

    # BIDS requires an 'IntendedFor' value in each Fieldmap scan's json sidecar. This field is originally
    # (and inappropriately) recorded in the magnitude (WATER_Fieldmap) scan's sidecar file.  This CANNOT
    # be fixed above, despite hours and hours of trying.  So...
    # Below, get the value from the magnitude scans' json sidecars, and move it to the sidecar for the
    # corresponding fieldmap scan. Then, delete the magnitude scan's json sidecar file (it's not required
    # for BIDS). Next, remove the string 'WATER' in the file names of the magnitude scans.  The filenames
    # for the fieldmaps and the magnitude scans should now match, and the 'IntendedFor' fields should be
    # in the proper locations. WHEW...

    def fixfmaps(self):
        fmap_dir = Path(self.bids_outdir.parent / 'fmap')
        for magjson in pathlib.Path(fmap_dir).glob('*magnitude.json'):
            # magjson_parts = str(magjson).split(sep='.')
            magjson_name = str(magjson).split(sep='.')[0]
            # magjson_suffix = str(magjson).split(sep='.')[1]
            fmap_pre = str(magjson.name).split('Magnitude')[0]

            if magjson_name.__contains__('run-1'):
                fmapjson = fmap_pre + 'Fieldmap_run-1_fieldmap.json'
                fmapjson = pathlib.Path(fmap_dir / fmapjson)
                with open(magjson) as magjsonfile:
                    magsidecar = json.load(magjsonfile)
                    IntendedFor = magsidecar['IntendedFor']
                with fmapjson.open('r') as fmapjsonfile:
                    fmapjsonfile_dict = json.load(fmapjsonfile)
                    fmapjsonfile_dict['IntendedFor'] = IntendedFor
                    fmapjsonfile_dict['Units'] = 'Hz'
                with fmapjson.open('w') as fmapjsonfile:
                    json.dump(fmapjsonfile_dict, fmapjsonfile, indent=4)

            elif magjson_name.__contains__('run-2'):
                fmapjson = fmap_pre + 'Fieldmap_run-2_fieldmap.json'
                fmapjson = pathlib.Path(fmap_dir / fmapjson)
                with open(magjson) as magjsonfile:
                    magsidecar = json.load(magjsonfile)
                    IntendedFor = magsidecar['IntendedFor']
                with fmapjson.open('r') as fmapjsonfile:
                    fmapjsonfile_dict = json.load(fmapjsonfile)
                    fmapjsonfile_dict['IntendedFor'] = IntendedFor
                    fmapjsonfile_dict['Units'] = 'Hz'
                with fmapjson.open('w') as fmapjsonfile:
                    json.dump(fmapjsonfile_dict, fmapjsonfile, indent=4)

            elif magjson_name.__contains__('run-3'):
                fmapjson = fmap_pre + 'Fieldmap_run-3_fieldmap.json'
                fmapjson = pathlib.Path(fmap_dir / fmapjson)
                with open(magjson) as magjsonfile:
                    magsidecar = json.load(magjsonfile)
                    IntendedFor = magsidecar['IntendedFor']
                with fmapjson.open('r') as fmapjsonfile:
                    fmapjsonfile_dict = json.load(fmapjsonfile)
                    fmapjsonfile_dict['IntendedFor'] = IntendedFor
                    fmapjsonfile_dict['Units'] = 'Hz'
                with fmapjson.open('w') as fmapjsonfile:
                    json.dump(fmapjsonfile_dict, fmapjsonfile, indent=4)
            magjson.unlink()

        for fname in Path(fmap_dir).iterdir():
            if str(fname).__contains__('WATER'):
                newfname = str(fname).replace('WATER', '')
                fname.rename(newfname)


# bz2 archive files are found in folders generated pre-2018ish (before a GE update)
# e.g., Youth PTSD
class bz2NIFTI():

    def __init__(self, subj_dir, outputpath, scanstoskip):

        # Input and output paths to pathlib.posixpath
        self.outputpath = Path(outputpath)

        self.dicoms_dir = Path(subj_dir / 'dicoms')
        if self.dicoms_dir.exists():
            for scan_dir in sorted(self.dicoms_dir.glob('*')):
                if not any(x in scan_dir.name for x in scanstoskip) and scan_dir.is_dir():
                    print(scan_dir)
                    self.unpack_bz2(scan_dir)
                    self.getbidsparams()
                    self.conv_dcms()
                    self.cleanup()
            self.process_fmaps()

        else:
            nodicomdir_str = ''.join(['SKIPPING PARTICIPANT: ', subj_dir.name, ' - DICOMS SUBDIRECTORY NOT FOUND.'])
            print('\n\n' + nodicomdir_str + '\n\n')
            next

    def unpack_bz2(self, scan_dir):

        # BZip archived dicoms are located in separate subfolders with individually compressed
        # slices, using naming convention sYY_XXXX.ZZZZ.bz2, where YY is the scan's sequence number
        # X is the scan type (e.g., 'epi' or 'bravo'), and Z is the slice number
        self.dicoms_dir = scan_dir.parents[0]

        # Locate the system's temp directory and set it to a variable
        self.tmpdir = Path(tempfile.mkdtemp(dir='/tmp'))

        # Copy the scan directory to /tmp for faster processing
        scan_dir_tmp = self.tmpdir / scan_dir.name
        shutil.copytree(scan_dir, scan_dir_tmp)

        # Decompress the BZ2 files in the tmp scan directory
        for bz2_file in sorted(scan_dir_tmp.glob('*.bz2')):
            bz2_fpath = Path(scan_dir_tmp, bz2_file)
            dcm_fpath = Path(scan_dir_tmp, str(bz2_file).replace(".bz2",""))
            with open(dcm_fpath, 'wb') as newfile, open(bz2_fpath, 'rb') as oldfile:
                decompressor = bz2.BZ2Decompressor()
                for data in iter(lambda: oldfile.read(100 * 1024), b''):
                    newfile.write(decompressor.decompress(data))

        self.rawscan_dir = Path(scan_dir_tmp)

    def getbidsparams(self):

        # Subject directories might be formatted as _XXX (time 1) or _XXXrescan (or _XXX_rescan)
        # Check if the leading character of the subject directory name is '_', and if so, set the
        # time point to 2 if the last four characters are 'rescan', 1 if they are not. Get the subjid
        # from characters 2-4.
        # If the leading charcter is NOT '_', set the time point to the last character of the
        # subject directory name, and the subject id to the charcters before the '_'
        if self.dicoms_dir.parent.name[0] == '_':
            self.subjID = self.dicoms_dir.parent.name[1:4]
            if self.dicoms_dir.parent.name[-6:] == 'rescan':
                self.timept = 2
            else:
                self.timept = 1
        else:
            self.subjID = self.dicoms_dir.parent.name.split('_')[0]
            self.timept = self.dicoms_dir.parent.name[-1]
        print(self.rawscan_dir.name)
        self.rawscan_type = self.rawscan_dir.name.split('_')[1]

        # Each scan folder should contain a YAML file with the scan info
        yaml_filepath = Path(self.rawscan_dir, self.rawscan_dir.name + '.yaml')

        if not yaml_filepath.exists():
            print("ERROR: A YAML file was not found in this scan's directory: " + self.rawscan_path)
            next

        # Extract the value of the 'SeriesDescription' field from the yaml file and use it as the...
        # bids_acqlabel: a label describing each, continuous uninterrupted block of scan time (e.g., one sequence)
        with open(yaml_filepath, "r") as yfile:
            for line in yfile:
                if line.startswith("  SeriesDescription:"):
                    bids_acqlabel = line.split(': ')[1]
                    # bids_sidecar_taskname: the task name that will be recorded in the BIDS json sidecar file
                    self.bids_sidecar_taskname = bids_acqlabel.replace("\n", "")
                    bids_acqlabel = bids_acqlabel.strip()
                    for c in ['(', ')', '-', ' ', '/']:
                        if c in bids_acqlabel:
                            bids_acqlabel = bids_acqlabel.replace(c, '')
                    bids_acqlabel = bids_acqlabel.replace(" ", "")
                    bids_acqlabel = "_acq-" + bids_acqlabel
                    break

        # If the raw scan is an fmri (i.e., 'epi') get the value of the 'SeriesNumber' field from the yaml file /
        # and use it to set bids_runno: the BIDS run number field (i.e., block trial number). If the scan is an fmri /
        # use the acquisition label to set the BIDS task label, which describes the nature of the functional paradigm
        if self.rawscan_type == 'epi':
            bids_tasklabel = bids_acqlabel.replace("_acq-", "_task-")
            bids_acqlabel = ''
            with open(yaml_filepath, "r") as yfile2:
                for line in yfile2:
                    if line.startswith("  SeriesNumber: "):
                        bids_runno = line.split(': ')[1]
                        bids_runno = "_run-" + bids_runno
                        break
        else:
            bids_tasklabel = ''

        # bids_scansession(dir): the wave of data collection formatted as a BIDS label string/directory name
        self.bids_scansession = "_ses-" + str(self.timept).zfill(2)
        self.bids_scansessiondir = "ses-" + str(self.timept).zfill(2)

        # bids_scanmode: the BIDS data type of the scan (e.g., func)
        self.bids_scanmode = self.scan2bidsmode(self.rawscan_type)

        # bids_participantID: the subject ID formatted as a BIDS label string
        self.bids_participantID = "sub-" + self.subjID

        # dcm2niix_outdir: the path where the converted scan files will be written by dcm2niix
        self.dcm2niix_outdir = Path(
            self.outputpath, self.bids_participantID, self.bids_scansessiondir, self.scan2bidsdir(self.rawscan_type))

        # dcm2niix_label: the file label to be passed to dcm2niix (conv_dcms)
        self.dcm2niix_label = ''
        self.dcm2niix_label = self.bids_participantID + \
            self.bids_scansession + \
            bids_tasklabel + \
            bids_acqlabel + \
            self.bids_scanmode

        return self.bids_participantID, self.bids_scansessiondir

    # Converting the raw scan files to NIFTI format using the parameters previously specified
    def conv_dcms(self):
        print(tools.stru("Step 3") + ": Converting to NIFTI using dcm2niix and sorting into appropriate BIDS folder...\n")

        if not self.dcm2niix_outdir.exists():
            self.dcm2niix_outdir.mkdir(parents=True)

        # Running dcm2niix
        subprocess.run(["dcm2niix", "-f", self.dcm2niix_label,
                        "-o", self.dcm2niix_outdir, self.rawscan_dir])

        if self.rawscan_type == 'epi':
            jsonfilepath = self.dcm2niix_outdir / (self.dcm2niix_label + '.json')
            with open(jsonfilepath) as jsonfile:
                sidecar = json.load(jsonfile)
            sidecar['TaskName'] = self.bids_sidecar_taskname
            with open(jsonfilepath, 'w') as f:
                json.dump(sidecar, f)

        # dcm2niix creates bvecs and bval files for the 'AxT2FLAIRCOPYDTI' (T2w) scans
        # (likely because they include 'DTI'?)
        # Delete these extraneous files for BIDS compliance
        if self.rawscan_type == 'fse':
            for file in os.listdir(self.dcm2niix_outdir):
                if file.endswith(".bvec") or file.endswith(".bval"):
                    os.remove(os.path.join(self.dcm2niix_outdir, file))

    def process_fmaps(self):
        fmap_dir = Path(self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'fmap')
        print(fmap_dir)
        # session_dir = Path(self.outputpath, self.bids_participantID, self.bids_scansession)
        make_fmaps(fmap_dir, 'EPI')
        #make_fmaps(fmap_dir, 'DTI')

    # Remove the temp directory
    def cleanup(self):
        shutil.rmtree(self.tmpdir)

    def scan2bidsmode(self, modstring):
        scan2bidsmode_dict = {
            "bravo": "_T1w",
            "fse": "_T2w",
            "epi": "_bold",
            "dti": "_dwi",
            "fmap": "_rawfmap"
        }
        returnkey = "nomatch"
        for key in scan2bidsmode_dict.keys():
            if key in modstring:
                returnkey = scan2bidsmode_dict[key]
        return(returnkey)

    # Convert raw scan directory names to BIDS data type directories
    def scan2bidsdir(self, typestring):
        scan2bidsdir_dict = {
            "bravo": "anat",
            "fse": "anat",
            "epi": "func",
            "dti": "dwi",
            "fmap": "fmap"
        }
        returnkey = "nomatch"
        for key in scan2bidsdir_dict.keys():
            if key in typestring:
                returnkey = scan2bidsdir_dict[key]
        return(returnkey)
