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
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(e, exc_type, fname, exc_tb.tb_lineno)
        else:
            self.cleanup()

    def announce(self):
        scanstart_str = ''.join(['\n', 'STARTING FIELDMAP PROCESSING: ', self.fmaptype])
        print('\n'+'='*(len(scanstart_str)-1) +
              scanstart_str + '\n' +
              '='*(len(scanstart_str)-1))

    def getrawfiles(self):

        gen = (rawfmapfile for rawfmapfile in self.fmap_dir.glob('*.nii')
               if rawfmapfile.name.__contains__(self.fmaptype))
        for rawfmapfile in gen:
            if str(rawfmapfile).__contains__('_e1a.'):
                self.rawfmapfile_2 = str(rawfmapfile)
            elif str(rawfmapfile).__contains__('_e1.'):
                self.rawfmapfile_1 = str(rawfmapfile)
            else:
                next

        try:
            self.rawfmapfile_2 or self.rawfmapfile_1
        except AttributeError:
            quit

    def computephase(self):
        real1 = str(self.rawfmapfile_1 + '[2]')
        real2 = str(self.rawfmapfile_2 + '[2]')
        imag1 = str(self.rawfmapfile_1 + '[3]')
        imag2 = str(self.rawfmapfile_2 + '[3]')
        print("\n" + tools.stru("Step 1") + ": Computing the wrapped phase difference from the raw fieldmap volumes (3dcalc)")  # noqa: E501
        subprocess.call(["3dcalc", "-float", "-a", real1, "-b", imag1, "-c", real2, "-d", imag2, "-expr",
                         "(atan2((b*c-d*a),(a*c+b*d)))", "-prefix", str(self.fmap_dir)+"/tmp.wrappedphasediff.nii"])

    def extractmag(self):
        print("\n" + tools.stru("Step 2") + ": Extracting magnitude image (3dcalc")
        self.mag1 = self.rawfmapfile_1.replace("_rawfmap_e1", "_magnitude1")
        subprocess.call(["3dcalc", "-a", str(self.rawfmapfile_1 + '[0]'), "-expr", "a", "-prefix", self.mag1])

    def stripmag(self):
        print("\n" + tools.stru("Step 3") + ": Skull-stripping magnitude image (bet2)")
        self.mag1_brain = self.rawfmapfile_1.replace("_rawfmap_e1", "_magnitude1_brain")
        subprocess.call(["bet2", self.mag1, self.mag1_brain])

    def erodemag(self):
        print("\n" + tools.stru("Step 4") + ": Eroding magnitude image brain (1 voxel; fslmaths -ero)")
        self.mag1_brain_ero = self.rawfmapfile_1.replace("_rawfmap_e1", "_magnitude1_brain_ero")
        subprocess.call(["fslmaths", self.mag1_brain, "-ero", self.mag1_brain_ero])

    def registermask(self):
        print("\n" + tools.stru("Step 5") + ": Registering magnitude image to wrapped phase difference (3dresample)")
        self.mag1_brain_ero_reg = self.mag1_brain = self.rawfmapfile_1.replace("_rawfmap_e1",
                                                                               "_magnitude1_brain_ero_reg")
        subprocess.call(["3dresample", "-master", str(self.fmap_dir)+"/tmp.wrappedphasediff.nii", "-prefix",
                         self.mag1_brain_ero_reg, "-input", self.mag1_brain_ero])

    def prelude(self):
        print("\n" + tools.stru("Step 6") + ": Unwrapping the phase difference (prelude)")
        subprocess.call(["prelude", "-v", "-p", str(self.fmap_dir)+"/tmp.wrappedphasediff.nii", "-a",
                         self.mag1_brain_ero, "-o", str(self.fmap_dir)+"/tmp.phasediff.rads.nii.gz", "-m",
                         self.mag1_brain_ero_reg])

    def orient2LPI(self):
        print("\n" + tools.stru("Step 7") + ": Setting the orientation to LPI (3dresample)")
        self.realfieldmap_rads = self.rawfmapfile_1.replace("_rawfmap_e1", "rads_phasediff").replace("Fieldmap",
                                                                                                     "")
        subprocess.call(["3dresample", "-input", str(self.fmap_dir)+"/tmp.phasediff.rads.nii.gz", "-prefix",
                         self.realfieldmap_rads, "-orient", "LPI"])

    def conv2Hz(self):
        print("\n" + tools.stru("Step 8") + ": Converting the phase difference from radians to Hz (3dcalc)")
        self.realfieldmap_Hz = self.rawfmapfile_1.replace("_rawfmap_e1", "Hz_phasediff").replace("Fieldmap", "")
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
                    fmapassoclist.append(str(Path(*scan.parts[-3:])))
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
                    fmapassoclist.append(str(Path(*scan.parts[-3:])))
                sidecar['IntendedFor'] = fmapassoclist

                tempfiles = (tempfile for tempfile in self.fmap_dir.iterdir() if
                             any([tempfile.name.startswith('tmp.'), tempfile.name.__contains__('EPI_rawfmap_e1')]))
                for tempfile in tempfiles:
                    os.remove(tempfile)

                with open(realfmapjson, 'w+') as outfile:
                    json.dump(sidecar, outfile, indent=4)

    def cleanup(self):
        print("\n" + tools.stru("Step 10") + ": Cleaning up...\n")
        globstr = str('*' + self.fmaptype + '*rawfmap*')
        for rawfmap in self.fmap_dir.glob(globstr):
            os.remove(rawfmap)
        for brain_nii in self.fmap_dir.glob('*brain*'):
            os.remove(brain_nii)
        for radfile in self.fmap_dir.glob('*rads*'):
            os.remove(radfile)
        for tmp in self.fmap_dir.glob('tmp*'):
            os.remove(tmp)

    def main(self):
        self.announce()
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
    mc = make_fmaps()
    mc.main()
