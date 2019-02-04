import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import bz2
import pydicom
import json
from lib.Utils import tools

class make_fmaps():

    def __init__(self, scan_type, fmap_dir, outputpath, participantID, sessiondir):
        self.scan_type = scan_type
        self.fmap_dir = fmap_dir
        self.outputpath = outputpath
        self.bids_participantID = participantID
        self.bids_scansessiondir = sessiondir
        self.make_fmap()

    def make_fmap(self):
        gen = (rawfmapfile for rawfmapfile in self.fmap_dir.glob('*.nii'))

        # dcm2niix will automatically split the different echo scans into separate files (shorter TE time is the first volume)
        for rawfmapfile in gen:
            if str(rawfmapfile).__contains__(self.scan_type):
                if str(rawfmapfile).__contains__('_e1a.'):
                    rawfmapfile_2 = str(rawfmapfile)
                elif str(rawfmapfile).__contains__('_e1.'):
                    rawfmapfile_1 = str(rawfmapfile)
                else:
                    next

        # Stop and go next if both echo files aren't there (can't process the phase difference)
        if not('rawfmapfile_2' in locals() and 'rawfmapfile_1' in locals()):
            return None

        os.chdir(self.fmap_dir)

        # Create file and volume strings to pass to AFNI's 3DCalc; 0=Magnitude, 2=First phase image 3=Second phase image
        rawfmapfile_1v0 = str(rawfmapfile_1 + '[0]')
        rawfmapfile_1v2 = str(rawfmapfile_1 + '[2]')
        rawfmapfile_1v3 = str(rawfmapfile_1 + '[3]')
        rawfmapfile_2v0 = str(rawfmapfile_2 + '[0]')
        rawfmapfile_2v2 = str(rawfmapfile_2 + '[2]')
        rawfmapfile_2v3 = str(rawfmapfile_2 + '[3]')

        #self.scan_type = str(self.scan_type)

        # Create filenames for the in-processing scans (distinguish by type)
        # and assign the names to variables which we will pass to 3DCalc
        if self.scan_type.__contains__('EPI'):
            wrappedphasefile = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_wrapped_phasediff')
            magoutfile1 = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_magnitude1')
            magoutfile2 = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_magnitude2')
            phasediffileRads = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_phasediff_rads')
            phasediffileHz = rawfmapfile_1.replace(
                '_epirawfmap_e1', '_phasediff')
            # Append the BIDS sidecar for each fieldmap with the name of the associated scan file
            fmap_intendedfor_path = os.path.join(
                self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'func')
            fmap_intendedfor_dict = {}
            for scan in os.listdir(fmap_intendedfor_path):
                if scan.endswith('.nii'):
                    fmap_intendedfor_dict.setdefault("IntendedFor", []).append(
                        self.bids_scansessiondir + '/func/' + scan)
            print("\n" + tools.stru("CREATING FIELD MAP FOR EPI SCANS:"))
        elif self.scan_type.__contains__('DTI'):
            wrappedphasefile = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_wrapped_phasediff')
            magoutfile1 = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_magnitude1')
            magoutfile2 = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_magnitude2')
            phasediffileRads = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_phasediff_rads')
            phasediffileHz = rawfmapfile_1.replace(
                '_dwirawfmap_e1', '_phasediff')
            # Append the BIDS sidecar for each fieldmap with the name of the associated scan file
            fmap_intendedfor_path = os.path.join(
                self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'dwi')
            fmap_intendedfor_dict = {}
            for scan in os.listdir(fmap_intendedfor_path):
                if scan.endswith('.nii'):
                    fmap_intendedfor_dict.setdefault("IntendedFor", []).append(
                        self.bids_scansessiondir + '/dwi/' + scan)
            print("\n" + tools.stru("CREATING FIELD MAP FOR DTI SCANS:"))

        # Set the formulas and parameters to be passed to 3DCalc
        calc_computephase = "atan2((b*c-d*a),(a*c+b*d))"
        calc_extractmag = "a"
        te_diff = 3
        calc_rads2hz = "a*1000/" + str(te_diff)

        # Append the echo times to the BIDS sidecar for this fieldmap
        fmap_description = {
            "EchoTime1": ".007",
            "EchoTime2": ".010"
        }
        fmap_description.update(fmap_intendedfor_dict)
        json_phasediffile = phasediffileHz.replace(".nii", ".json")
        with open(json_phasediffile, 'w') as outfile:
            json.dump(fmap_description, outfile)

        # Run the fieldmap conversion using Rasmus' method (3DCalc, FSL Prelude, then convert from rads to Hz)
        # If any process fails, print an error to the console and go next
        try:
            print("\n" + tools.stru("Step 1") + ": Computing the phase difference from the raw fieldmap volumes")
            # -Computing the phase difference from the raw fieldmap volume
            subprocess.call(["3dcalc", "-float", "-a", rawfmapfile_1v2, "-b", rawfmapfile_1v3, "-c", rawfmapfile_2v2, "-d", rawfmapfile_2v3,
                            "-expr", "atan2((b*c-d*a),(a*c+b*d))", "-prefix", wrappedphasefile])

            print("\n" + tools.stru("Step 2") + ": Extracting magnitude image")
            # -Extract magnitude image from first raw fieldmap volume
            subprocess.call(["3dcalc", "-a", rawfmapfile_1v0,
                            "-expr", calc_extractmag, "-prefix", magoutfile1])

            # print("\n" + tools.stru("Step 3") + ": Extracting magnitude image #2")
            # # -Extract magnitude image from second raw fieldmap volume
            # subprocess.call(["3dcalc", "-a", rawfmapfile_2v0,
            #                 "-expr", calc_extractmag, "-prefix", magoutfile2])

            print("\n" + tools.stru("Step 3") + ": Unwrapping the phase difference using FSL's 'prelude'")
            # -Unwrap the phase difference file
            subprocess.call(["prelude", "-v", "-p", wrappedphasefile,
                            "-a", magoutfile1, "-o", phasediffileRads])
            phasediffileRads = phasediffileRads + '.gz'

            print("\n" + tools.stru("Step 4") + ": Converting the phase difference from radians to Hz")
            # -Convert the phase difference file from rads to Hz
            # -Formula for conversion: "a" x 1000 / x ; where x is the abs. value of the difference in TE between the two volumes
            subprocess.call(["3dcalc", "-a", phasediffileRads,
                            "-expr", calc_rads2hz, "-prefix", phasediffileHz])

        except OSError as e:
            print("ERROR MAKING FIELDMAPS: " + e)
            pass

        # Cleanup unnecessary fieldmap files and old sidecar files
        try:
            os.remove(wrappedphasefile)
            os.remove(phasediffileRads)
            os.remove(rawfmapfile_1)
            os.remove(rawfmapfile_1.replace('.nii', '.json'))
            os.remove(rawfmapfile_2)
            os.remove(rawfmapfile_2.replace('.nii', '.json'))
        except OSError as e:
            print(e)
            pass