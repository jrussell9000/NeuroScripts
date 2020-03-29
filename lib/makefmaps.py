import os
import subprocess
import json
import sys
import tools
from pathlib import Path


class make_fmaps():

    def __init__(self, fmapdir, fmaptype):
        self.fmap_dir = Path(fmapdir)
        self.fmaptype = fmaptype
        try:
            self.main()
        except:
            print("Error processing fieldmaps...they may not exist.")
            return None

    def getrawfiles(self):
        gen = (rawfmapfile for rawfmapfile in self.fmap_dir.glob('*.nii') if rawfmapfile.name.__contains__(self.fmaptype))
        for rawfmapfile in gen:
            if str(rawfmapfile).__contains__('_e1a.'):
                self.rawfmapfile_2 = str(rawfmapfile)
            elif str(rawfmapfile).__contains__('_e1.'):
                self.rawfmapfile_1 = str(rawfmapfile)
            else:
                next    

        try:
            self.rawfmapfile_2
            self.rawfmapfile_1
        except AttributeError:
            quit

    def computephase(self):
        real1 = str(self.rawfmapfile_1 + '[2]')
        real2 = str(self.rawfmapfile_2 + '[2]')
        imag1 = str(self.rawfmapfile_1 + '[3]')
        imag2 = str(self.rawfmapfile_2 + '[3]')
        print("\n" + tools.stru("Step 1") + ": Computing the wrapped phase difference from the raw fieldmap volumes")
        subprocess.call(["3dcalc", "-float", "-a", real1, "-b", imag1, "-c", real2, "-d", imag2, "-expr",
                         "(atan2((b*c-d*a),(a*c+b*d)))", "-prefix", str(self.fmap_dir)+"/tmp.wrappedphasediff.nii.gz"])

    def extractmag(self):
        print("\n" + tools.stru("Step 2") + ": Extracting magnitude image")
        self.mag1 = self.rawfmapfile_1.replace("_rawfmap_e1", "_magnitude1")
        subprocess.call(["3dcalc", "-a", str(self.rawfmapfile_1 + '[0]'), "-expr", "a", "-prefix", self.mag1])

    def stripmag(self):
        print("\n" + tools.stru("Step 3") + ": Skull-stripping magnitude image")
        self.mag1_brain = self.rawfmapfile_1.replace("_rawfmap_e1", "_magnitude1_brain")
        subprocess.call(["bet2", self.mag1, self.mag1_brain])

    def erodemag(self):
        print("\n" + tools.stru("Step 4") + ": Eroding magnitude image brain (1 voxel)")
        self.mag1_brain_ero = self.rawfmapfile_1.replace("_rawfmap_e1.nii.gz", "_magnitude1_brain_ero.nii")
        subprocess.call(["fslmaths", self.mag1_brain, "-ero", self.mag1_brain_ero])

    def registermask(self):
        print("\n" + tools.stru("Step 5") + ": Registering magnitude image to wrapped phase difference")
        self.mag1_brain_ero_reg = self.mag1_brain = self.rawfmapfile_1.replace("_rawfmap_e1",
                                                                               "_magnitude1_brain_ero_reg")
        subprocess.call(["3dresample", "-master", str(self.fmap_dir)+"/tmp.wrappedphasediff.nii.gz", "-prefix",
                         self.mag1_brain_ero_reg, "-input", self.mag1_brain_ero])

    def prelude(self):
        print("\n" + tools.stru("Step 6") + ": Unwrapping the phase difference using FSL's PRELUDE")
        subprocess.call(["prelude", "-v", "-p", str(self.fmap_dir)+"/tmp.wrappedphasediff.nii.gz", "-a", self.mag1_brain_ero,
                         "-o", "tmp.phasediff.rads.nii.gz", "-m", self.mag1_brain_ero_reg])

    def orient2LPI(self):
        print("\n" + tools.stru("Step 7") + ": Setting the orientation to LPI")
        self.realfieldmap_rads = self.rawfmapfile_1.replace("_rawfmap_e1", "rads_phasediff").replace("Fieldmap",
                                                                                                "")
        subprocess.call(["3dresample", "-input", str(self.fmap_dir)+"/tmp.phasediff.rads.nii.gz", "-prefix",
                         self.realfieldmap_rads, "-orient", "LPI"])

    def conv2Hz(self):
        print("\n" + tools.stru("Step 8") + ": Converting the phase difference from radians to Hz")
        self.realfieldmap_Hz = self.rawfmapfile_1.replace("_rawfmap_e1", "Hz_fmap").replace("Fieldmap", "")
        subprocess.call(["3dcalc", "-a", self.realfieldmap_rads, "-expr", "a*0.1592", "-prefix", self.realfieldmap_Hz])

    def appendsidecar(self):

        print("\n" + tools.stru("Step 9") + ": Editing BIDS sidecar files as necessary")

        # Append the BIDS sidecar for each fieldmap with the name of the associated scan file
        fmapjson = self.rawfmapfile_1.replace('.nii', '.json')
        realfmapjson = self.realfieldmap_Hz.replace('.nii', '.json')

        with open(fmapjson) as jsonfile:
            sidecar = json.load(jsonfile)
            sidecar['EchoTime1'] = '.007'
            sidecar['EchoTime2'] = '.010'
            sidecar['Units'] = 'Hz'

            if self.fmaptype == "DTI":
                fmaps = Path(self.fmap_dir)
                fmap_intendedfor_path = fmaps.parents[0] / 'dwi'
                scanlist = (scan for scan in fmap_intendedfor_path.iterdir() if str(scan).endswith('.nii'))
                fmapassoclist = []
                for scan in scanlist:
                    fmapassoclist.append(str(Path(*scan.parts[-4:])))
                sidecar['IntendedFor'] = fmapassoclist

                tempfiles = (tempfile for tempfile in self.fmap_dir.iterdir() if
                             any([tempfile.name.startswith('tmp.'), tempfile.name.__contains__('DTI_rawfmap_e1')]))
                for tempfile in tempfiles:
                    os.remove(tempfile)

                with open(realfmapjson, 'w+') as outfile:
                    json.dump(sidecar, outfile, indent=4)

            if self.fmaptype == "EPI":
                fmaps = Path(self.fmap_dir)
                fmap_intendedfor_path = fmaps.parents[0] / 'func'
                scanlist = (scan for scan in fmap_intendedfor_path.iterdir() if scan.name.endswith('.nii'))
                fmapassoclist = []
                for scan in scanlist:
                    fmapassoclist.append(str(Path(*scan.parts[-4:])))
                sidecar['IntendedFor'] = fmapassoclist

                tempfiles = (tempfile for tempfile in self.fmap_dir.iterdir() if
                             any([tempfile.name.startswith('tmp.'), tempfile.name.__contains__('EPI_rawfmap_e1')]))
                for tempfile in tempfiles:
                    os.remove(tempfile)

                with open(realfmapjson, 'w+') as outfile:
                    json.dump(sidecar, outfile, indent=4)

    def main(self):
        self.getrawfiles()
        self.computephase()
        self.extractmag()
        self.stripmag()
        self.erodemag()
        self.registermask()
        self.prelude()
        self.orient2LPI()
        self.conv2Hz()
        self.appendsidecar()


if __name__ == '__main__':
    mc = makefmaps()
    mc.main()
    # def __init__(self, scan_type, fmap_dir, outputpath, participantID, sessiondir):
    #     self.scan_type = scan_type
    #     self.fmap_dir = fmap_dir
    #     self.outputpath = outputpath
    #     self.bids_participantID = participantID
    #     self.bids_scansessiondir = sessiondir
    #     self.make_fmap()

    # def make_fmap(self):
    #     gen = (rawfmapfile for rawfmapfile in self.fmap_dir.glob('*.nii'))

    #     # dcm2niix will automatically split the different echo scans into separate files
    #     # (shorter TE time is the first volume)
    #     for rawfmapfile in gen:
    #         if str(rawfmapfile).__contains__(self.scan_type):
    #             if str(rawfmapfile).__contains__('_e1a.'):
    #                 rawfmapfile_2 = str(rawfmapfile)
    #             elif str(rawfmapfile).__contains__('_e1.'):
    #                 rawfmapfile_1 = str(rawfmapfile)
    #             else:
    #                 next

    #     # Stop and go next if both echo files aren't there (can't process the phase difference)
    #     if not('rawfmapfile_2' in locals() and 'rawfmapfile_1' in locals()):
    #         return None

    #     os.chdir(self.fmap_dir)

    #     # Create file and volume strings to pass to AFNI's 3DCalc; 0=Magnitude, 2=First phase image 3=Second phase image
    #     rawfmapfile_1v0 = str(rawfmapfile_1 + '[0]')
    #     rawfmapfile_1v2 = str(rawfmapfile_1 + '[2]')
    #     rawfmapfile_1v3 = str(rawfmapfile_1 + '[3]')
    #     rawfmapfile_2v0 = str(rawfmapfile_2 + '[0]')
    #     rawfmapfile_2v2 = str(rawfmapfile_2 + '[2]')
    #     rawfmapfile_2v3 = str(rawfmapfile_2 + '[3]')

    #     # self.scan_type = str(self.scan_type)

    #     # Create filenames for the in-processing scans (distinguish by type)
    #     # and assign the names to variables which we will pass to 3DCalc
    #     if self.scan_type.__contains__('EPI'):
    #         wrappedphasefile = rawfmapfile_1.replace(
    #             '_epirawfmap_e1', '_wrapped_phasediff')
    #         magoutfile1 = rawfmapfile_1.replace(
    #             '_epirawfmap_e1', '_magnitude1')
    #         magoutfile2 = rawfmapfile_1.replace(
    #             '_epirawfmap_e1', '_magnitude2')
    #         phasediffileRads = rawfmapfile_1.replace(
    #             '_epirawfmap_e1', '_phasediff_rads')
    #         phasediffileHz = rawfmapfile_1.replace(
    #             '_epirawfmap_e1', '_phasediff')
    #         # Append the BIDS sidecar for each fieldmap with the name of the associated scan file
    #         fmap_intendedfor_path = os.path.join(
    #             self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'func')
    #         fmap_intendedfor_dict = {}
    #         for scan in os.listdir(fmap_intendedfor_path):
    #             if scan.endswith('.nii'):
    #                 fmap_intendedfor_dict.setdefault("IntendedFor", []).append(
    #                     str(self.bids_scansessiondir) + '/func/' + scan)
    #         print("\n" + tools.stru("CREATING FIELD MAP FOR EPI SCANS:"))
    #     elif self.scan_type.__contains__('DTI'):
    #         wrappedphasefile = rawfmapfile_1.replace(
    #             '_dwirawfmap_e1', '_wrapped_phasediff')
    #         magoutfile1 = rawfmapfile_1.replace(
    #             '_dwirawfmap_e1', '_magnitude1')
    #         magoutfile2 = rawfmapfile_1.replace(
    #             '_dwirawfmap_e1', '_magnitude2')
    #         phasediffileRads = rawfmapfile_1.replace(
    #             '_dwirawfmap_e1', '_phasediff_rads')
    #         phasediffileHz = rawfmapfile_1.replace(
    #             '_dwirawfmap_e1', '_phasediff')
    #         # Append the BIDS sidecar for each fieldmap with the name of the associated scan file
    #         fmap_intendedfor_path = os.path.join(
    #             self.outputpath, self.bids_participantID, self.bids_scansessiondir, 'dwi')
    #         fmap_intendedfor_dict = {}
    #         for scan in os.listdir(fmap_intendedfor_path):
    #             if scan.endswith('.nii'):
    #                 fmap_intendedfor_dict.setdefault("IntendedFor", []).append(
    #                     str(self.bids_scansessiondir) + '/dwi/' + scan)
    #         print("\n" + tools.stru("CREATING FIELD MAP FOR DTI SCANS:"))

    #     # Set the formulas and parameters to be passed to 3DCalc
    #     calc_computephase = "atan2((b*c-d*a),(a*c+b*d))"
    #     calc_extractmag = "a"
    #     te_diff = 3
    #     calc_rads2hz = "a*1000/" + str(te_diff)

    #     # Append the echo times to the BIDS sidecar for this fieldmap
    #     fmap_description = {
    #         "EchoTime1": ".007",
    #         "EchoTime2": ".010"
    #     }
    #     fmap_description.update(fmap_intendedfor_dict)
    #     json_phasediffile = phasediffileHz.replace(".nii", ".json")
    #     with open(json_phasediffile, 'w') as outfile:
    #         json.dump(fmap_description, outfile)

    #     # Run the fieldmap conversion using Rasmus' method (3DCalc, FSL Prelude, then convert from rads to Hz)
    #     # If any process fails, print an error to the console and go next
    #     try:
    #         print("\n" + tools.stru("Step 1") + ": Computing the phase difference from the raw fieldmap volumes")
    #         # -Computing the phase difference from the raw fieldmap volume
    #         subprocess.call(["3dcalc", "-float", "-a", rawfmapfile_1v2, "-b", rawfmapfile_1v3,
    #                          "-c", rawfmapfile_2v2, "-d", rawfmapfile_2v3,
    #                         "-expr", "atan2((b*c-d*a),(a*c+b*d))", "-prefix", wrappedphasefile])

    #         print("\n" + tools.stru("Step 2") + ": Extracting magnitude image")
    #         # -Extract magnitude image from first raw fieldmap volume
    #         subprocess.call(["3dcalc", "-a", rawfmapfile_1v0,
    #                         "-expr", calc_extractmag, "-prefix", magoutfile1])

    #         # print("\n" + tools.stru("Step 3") + ": Extracting magnitude image #2")
    #         # # -Extract magnitude image from second raw fieldmap volume
    #         # subprocess.call(["3dcalc", "-a", rawfmapfile_2v0,
    #         #                 "-expr", calc_extractmag, "-prefix", magoutfile2])

    #         print("\n" + tools.stru("Step 3") + ": Unwrapping the phase difference using FSL's 'prelude'")
    #         # -Unwrap the phase difference file
    #         subprocess.call(["prelude", "-v", "-p", wrappedphasefile,
    #                         "-a", magoutfile1, "-o", phasediffileRads])
    #         phasediffileRads = phasediffileRads + '.gz'

    #         print("\n" + tools.stru("Step 4") + ": Converting the phase difference from radians to Hz")
    #         # -Convert the phase difference file from rads to Hz
    #         # -Formula for conversion: "a" x 1000 / x ; where x is the abs. value of the
    #         # -difference in TE between the two volumes
    #         self.realfieldmap_Hz = self.rawfmapfile_1.replace("_rawfmap_e1","Hz_fmap").replace("Fieldmap","RealFieldmap")
    #         subprocess.call(["3dcalc", "-a", phasediffileRads,
    #                         "-expr", calc_rads2hz, "-prefix", phasediffileHz])

    #     except OSError as e:
    #         print("ERROR MAKING FIELDMAPS: " + e)
    #         pass

    #     # Cleanup unnecessary fieldmap files and old sidecar files
    #     try:
    #         os.remove(wrappedphasefile)
    #         os.remove(phasediffileRads)
    #         os.remove(rawfmapfile_1)
    #         os.remove(rawfmapfile_1.replace('.nii', '.json'))
    #         os.remove(rawfmapfile_2)
    #         os.remove(rawfmapfile_2.replace('.nii', '.json'))
    #     except OSError as e:
    #         print(e)
    #         pass
