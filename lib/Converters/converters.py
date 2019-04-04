import bz2
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile

#from lib.Converters import makefmaps
from lib.Utils import tools


class tgz2NIFTI():

    fmapassoclist = list()

    def __init__(self, studypath, outputpath, scanstoskip, inputidfile):
        self.studypath = pathlib.PosixPath(studypath)
        outputpath = pathlib.PosixPath(outputpath)

        # Did a subject ID list get passed? If so, parse it, use its contents
        if inputidfile == None:
            subjdirs = sorted(self.studypath.iterdir())
        else:
            with open(inputidfile, 'r') as idfile:
                sids = idfile.readlines()
                sids = [s.strip('\n') for s in sids]
                subjdirs = (subjdir for subjdir in sorted(self.studypath.iterdir()) if any(x in str(subjdir) for x in sids))

        # For each subject directory, print a starting message, then loop across all TGZ archives in the /dicoms/ subdirectory
        # as long as those filenames don't contain any of the strings in the scanstoskip directory
        for subjdir in subjdirs:
            startsubjdir_str = ''.join(['NOW CONVERTING PARTICIPANT: ', subjdir.parts[-1]])
            print('\n' + '#'*(len(startsubjdir_str)) + '\n' + startsubjdir_str + '\n' + '#'*(len(startsubjdir_str)) + '\n')

            self.dcm_path = pathlib.PosixPath(subjdir, 'dicoms')
            for fname in sorted(self.dcm_path.glob('*.tgz')):
                if not any(x in fname.name for x in scanstoskip):
                    self.unpack_tgz(fname)
                    self.getbidsparams(outputpath)
                    self.conv_dcms()
                    self.cleanup()
            self.fixfmaps()

    def unpack_tgz(self, tgzfile): 
        tgz_fpath = pathlib.PosixPath(tgzfile)
        tgz_fname = tgz_fpath.name
        fullid = str(tgz_fpath.parts[-3])
        if fullid[-2] == 'C':
            self.timept = fullid[-1]
            self.subjid = fullid.split('_')[0]
        elif fullid.__contains__('rescan'):
            self.timept = 2
            self.subjid = fullid[1:4]
        else:
            self.timept = 1
            self.subjid = fullid[1:4]
        self.tmpdir = pathlib.PosixPath(tempfile.mkdtemp(dir='/tmp'))
        shutil.copy(tgz_fpath, self.tmpdir)
        tgz_file_tmp = pathlib.PosixPath(self.tmpdir, tgz_fname)
        tgz_file_open = tarfile.open(tgz_file_tmp, 'r:gz')

        scanstart_str = ''.join(['\n','STARTING SCAN ', tgz_fname])
        print('='*(len(scanstart_str)-1) + scanstart_str + '\n' + '='*(len(scanstart_str)-1))
        print(tools.stru('\nCOPYING AND DECOMPRESSING ARCHIVE FILE') + '...' + '\n')

        tgz_file_open.extractall(path=self.tmpdir)
        tgz_dcm_dirname = os.path.commonprefix(tgz_file_open.getnames())
        self.tgz_dcm_dirpath = pathlib.PosixPath(self.tmpdir, tgz_dcm_dirname)

    def getbidsparams(self, outputpath):

        # Get the name of the directory holding the unpacked scan archive (e.g., s0003.MPRAGE)
        self.raw_scandirname = str(self.tgz_dcm_dirpath.parts[-1])

        # Get the scan type (e.g., MPRAGE)
        self.raw_scantype = self.raw_scandirname.split('.')[1]

        # Get the scan's sequence number (e.g., 0003) as an integer
        raw_seqno = int(self.raw_scandirname.split('.')[0][1:])

        # Get the wave number (time point) as an integer
        raw_timept = int(self.timept)

        # Pull the scan's description from the first .DCM file's header and use it as the BIDS acquisition label
        dcm = pydicom.dcmread(os.path.join(self.tgz_dcm_dirpath, 'i.000001.dcm'))
        bids_acqlabel = str(dcm.SeriesDescription)

        # Remove BIDS-prohibited characters from the acquisition label
        for c in ['(', ')', '-', '_', ' ', '/', 'FieldMap:', ':']:
            if c in bids_acqlabel:
                bids_acqlabel = bids_acqlabel.replace(c, '')
        bids_acqlabel = 'acq-' + bids_acqlabel

        # Empty the following BIDS parameter labels (in case they're already set)
        bids_runno = ''
        bids_tasklabel = ''
        bids_pedir = ''
        bids_tasklabel = ''

        # For EPI scans, create a run number label
        if self.raw_scantype.__contains__('EPI_'):
            bids_tasklabel = bids_acqlabel.replace('acq-', 'task-').replace('EPI','')
            bids_acqlabel = ''

            # Add all similarly named EPI scans to a list, sorted by sequence number.
            # If the scan to be processed is a member of that list, its run number is equal to its index in the list
            taskscan_list = list(scan.name for scan in sorted(self.dcm_path.glob('*.tgz')) if str(scan).__contains__(self.raw_scantype))
            if len(taskscan_list) > 1:
                for item in taskscan_list.__iter__():
                    if self.raw_scandirname in item:
                        i = taskscan_list.index(item)
                        epi_runcount = i + 1
                        bids_runno = 'run-' + str(epi_runcount)

        # If the scan is a 'WATER_Fieldmap' (magnitude volume), create a run number label (to differentiate multiple magnitude volumes)
        if self.raw_scantype.__contains__('WATER_Fieldmap'):
            fmapmaglist = list(scan.name for scan in sorted(self.dcm_path.glob('*.tgz')) if str(scan).__contains__(self.raw_scantype))
            for item in fmapmaglist.__iter__():
                if self.raw_scandirname in item:
                    i = fmapmaglist.index(item)
                    fmapmag_runcount = i + 1
                    bids_runno = 'run-' + str(fmapmag_runcount)

        # If the scan is a 'FieldMap_Fieldmap' (real fieldmap volume), create a run number label
        if self.raw_scantype.__contains__('FieldMap_Fieldmap'):
            fmapfmaplist = list(scan.name for scan in sorted(self.dcm_path.glob('*.tgz')) if str(scan).__contains__(self.raw_scantype))
            for item in fmapfmaplist.__iter__():
                if self.raw_scandirname in item:
                    i = fmapfmaplist.index(item)
                    fmapfmap_runcount = i + 1
                    bids_runno = 'run-' + str(fmapfmap_runcount)

        # If the scan is a NODDI (i.e., a DWI) parse the phase encoding polarity from the filename and create a phase encoding direction label (PA=0; AP=1)
        if self.raw_scantype.__contains__('NODDI'):
            if self.raw_scantype.__contains__('pepolar0'):
                bids_pedir = 'dir-PA'
            elif self.raw_scantype.__contains__('pepolar1'):
                bids_pedir = 'dir-AP'

        # Create the BIDS participant ID label
        bids_participantID = 'sub-' + self.subjid

        # Create the BIDS wave (timepoint) label - two digits
        self.bids_scansession = 'ses-' + str(self.timept).zfill(2)

        # Create the BIDS scan modality label (e.g., '_T1w')
        bids_scanmode = tools.scan2bidsmode(self.raw_scantype)

        # Print out the BIDS parameters for this scan
        print(tools.stru('PARSING BIDS PARAMETERS') + '...')
        print('Participant:', bids_participantID)
        print('Wave:', self.bids_scansession)
        if len(bids_acqlabel) > 0:
            print('ACQ Label:', bids_acqlabel.replace('acq-',''))
        print('Modality Label:', bids_scanmode)
        if len(bids_tasklabel) > 0:
            print('Task Label:', bids_tasklabel.replace('task-',''))
        if bids_runno:
            print('Run #:',bids_runno.replace('run-',''))
        if len(bids_pedir) > 0:
            print('Phase Encoding Label:', bids_pedir)

        # Collecting all the BIDS parameters in a list
        dlist = [bids_participantID]
        dlist.append(self.bids_scansession)
        if len(bids_tasklabel) > 0:
            dlist.append(bids_tasklabel)
        if len(bids_acqlabel) > 0:
            dlist.append(bids_acqlabel)
        if len(bids_runno) > 0:
            dlist.append(bids_runno)
        if len(bids_pedir) > 0:
            dlist.append(bids_pedir)
        dlist.append(bids_scanmode)

        # Joining the BIDS parameter list items into an underscore delimited string
        self.dcm2niix_label = '_'.join(dlist)

        # Setting the BIDS output directory
        self.bids_outdir = pathlib.Path(outputpath, bids_participantID, self.bids_scansession, tools.scan2bidsdir(self.raw_scandirname))

    def conv_dcms(self):

        # Make the BIDS output directory for this specific scan, overwriting the directory if it exists
        os.makedirs(self.bids_outdir, exist_ok=True)

        # Start converting the scans using Chris Rorden's dcm2niix, providing the BIDS label created above
        print('\n' + tools.stru('BEGINNING SCAN CONVERSION') + '...')
        subprocess.run(['dcm2niix','-f', self.dcm2niix_label,
                        '-o', self.bids_outdir, self.tgz_dcm_dirpath])

        # If the scan is an fmri ('EPI'), append the taskname to the BIDS sidecar file
        if self.raw_scantype.__contains__('EPI_'):
            jsonfilepath = pathlib.PosixPath(self.bids_outdir, self.dcm2niix_label + '.json')
            with open(jsonfilepath) as jsonfile:
                sidecar = json.load(jsonfile)
            sidecar['TaskName'] = self.raw_scantype
            sidecar['MultibandAccelerationFactor'] = 3
            with open(jsonfilepath, 'w') as f:
                json.dump(sidecar, f, indent=4)
        
        # If the scan is a WATER_Fieldmap (magnitude image), grab the names of scans since the last 
        # WATER_Fieldmap.  We'll add these to the 'IntendedFor' field in the BIDS sidecar.  
        if self.raw_scantype.__contains__('WATER'):
            jsonfilepath = pathlib.PosixPath(self.bids_outdir, self.dcm2niix_label + '.json')
            print(jsonfilepath)
            with open(jsonfilepath) as jsonfile:
                sidecar = json.load(jsonfile)
            sidecar['IntendedFor'] = self.fmapassoclist
            with open(jsonfilepath, 'w') as f:
                json.dump(sidecar, f, indent=4) 
            self.fmapassoclist = list()
        else:
        # If the scan is NOT a WATER_Fieldmap, add the scan's path to a running list of scans associated with an upcoming fieldmap
            try:
                self.fmapassoclist
                if self.raw_scantype.__contains__('EPI') or self.raw_scantype.__contains__('NODDI'):
                    self.fmapassoclist.append(self.bids_scansession + '/' + tools.scan2bidsdir(self.raw_scandirname) + '/' + self.dcm2niix_label + '.nii')
            except NameError:
                self.fmapassoclist = list(self.dcm2niix_label + '.nii')

        print(tools.stru('\nSCAN ' + self.tgz_dcm_dirpath.parts[-1] + ' COMPLETED!\n'))
 
    def cleanup(self):
        # Delete the temporary directory we created above
        shutil.rmtree(self.tmpdir)

    def fixfmaps(self):
        fmap_dir = pathlib.PurePosixPath(self.bids_outdir).parent / 'fmap'

        # BIDS requires an 'IntendedFor' value in each Fieldmap scan's json sidecar.  This field is originally (and inappropriately) recorded in the 
        # magnitude scan's (WATER_Fieldmap) json.  Below, get the value from the magnitude scan's json, move it to the fieldmap scan's json.
        # Then delete the magnitude json (it's not required for BIDS).  Then remove the string WATER in the magnitude file names, thus 
        # making them match the fieldmap filenames.  WHEW....
        for magjson in pathlib.Path(fmap_dir).glob('*magnitude.json'):
            magjson_parts = str(magjson).split(sep='.')
            magjson_name = str(magjson).split(sep='.')[0]
            magjson_suffix = str(magjson).split(sep='.')[1]
            fmap_pre = str(magjson.name).split('WATER')[0]

            if magjson_name.__contains__('run-1'):
                fmapjson = fmap_pre + 'Fieldmap3D_run-1_fieldmap.json'
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
                fmapjson = fmap_pre + 'Fieldmap3D_run-2_fieldmap.json'
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
                fmapjson = fmap_pre + 'Fieldmap3D_run-3_fieldmap.json'
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

        for fname in pathlib.Path(fmap_dir).iterdir():
            if str(fname).__contains__('WATER'):
                newfname = str(fname).replace('WATER','')
                fname.rename(newfname)

class bz2NIFTI():

    def __init__(self, input_bz2_scandir, outputpath):
        self.input_bz2_scandir = input_bz2_scandir
        self.outputpath = outputpath
        self.unpack_bz2()

    def unpack_bz2(self):
        bz2_dpath = pathlib.PurePath(self.input_bz2_scandir)
        print(bz2_dpath)
        bz2_dname = bz2_dpath.parts[-1]
        print(bz2_dname)
        fullid = str(bz2_dpath.parts[-3]).replace('_','')
        print(fullid)
        tmpdir = tempfile.mkdtemp(dir='/tmp', suffix=fullid)
        if fullid.__contains__('rescan'):
            self.subjid = fullid.replace('rescan','')
            timept = 2
        else:
            timept = 1
            self.subjid = fullid
        shutil.copytree(bz2_dpath, tmpdir)
        bz2_dir_tmp = pathlib.PurePath(tmpdir, bz2_dname)
        for bz2_file in sorted(bz2_dir_tmp.glob('*.bz2')):
            bz2_fpath = pathlib.PurePath(bz2_dir_tmp, bz2_file)
            dcm_fpath = pathlib.PurePath(bz2_dir_tmp, bz2_file.replace('.bz2',''))
            with open(dcm_fpath, 'wb') as newfile, open(bz2_fpath, 'rb') as oldfile:
                decompressor = bz2.BZ2Decompressor()
                for data in iter(lambda: oldfile.read(100 * 1024), b''):
                    newfile.write(decompressor.decompress(data))
        self.raw_scanpath = bz2_dir_tmp
