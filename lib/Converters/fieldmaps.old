
import subprocess
import os
from pathlib import PurePath, Path
import pathlib
import json

class makefmaps():

    def __init__(self, fmapdir, fmaptype):
        self.fmap_dir = Path(fmapdir)
        os.chdir(self.fmap_dir)
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

        # if self.rawfmapfile_2 is None or self.rawfmapfile_1 is None:
        #     print("No fieldmap files found...")
        #     return None

    def computephase(self):
        real1 = str(self.rawfmapfile_1 + '[2]')
        real2 = str(self.rawfmapfile_2 + '[2]')
        imag1 = str(self.rawfmapfile_1 + '[3]')
        imag2 = str(self.rawfmapfile_2 + '[3]')     
        subprocess.call(["3dcalc", "-float", "-a", real1, "-b", imag1, "-c", real2, "-d", imag2, "-expr", 
        "(atan2((b*c-d*a),(a*c+b*d)))", "-prefix", "tmp.wrappedphasediff.nii.gz"])
    
    def extractmag(self):
        self.mag1 = self.rawfmapfile_1.replace("_rawfmap_e1","_magnitude1")
        subprocess.call(["3dcalc", "-a", str(self.rawfmapfile_1 + '[0]'), "-expr", "a", "-prefix", self.mag1])
    
    def stripmag(self):
        self.mag1_brain = self.rawfmapfile_1.replace("_rawfmap_e1", "_magnitude1_brain")
        subprocess.call(["bet2", self.mag1, self.mag1_brain])
    
    def erodemag(self):
        self.mag1_brain_ero = self.rawfmapfile_1.replace("_rawfmap_e1", "_magnitude1_brain_ero")
        subprocess.call(["fslmaths", self.mag1_brain, "-ero", self.mag1_brain_ero])

    def registermask(self):
        self.mag1_brain_ero_reg = self.mag1_brain = self.rawfmapfile_1.replace("_rawfmap_e1", "_magnitude1_brain_ero_reg")
        subprocess.call(["3dresample", "-master", "tmp.wrappedphasediff.nii.gz", "-prefix", self.mag1_brain_ero_reg, "-input", self.mag1_brain_ero])

    def prelude(self):
        subprocess.call(["prelude", "-v", "-p", "tmp.wrappedphasediff.nii.gz", "-a", self.mag1_brain_ero, "-o", "tmp.phasediff.rads.nii.gz", 
        "-m", self.mag1_brain_ero_reg])

    def orient2LPI(self):
        self.realfieldmap_rads = self.rawfmapfile_1.replace("_rawfmap_e1","rads_fmap").replace("Fieldmap","RealFieldmap")
        subprocess.call(["3dresample", "-input", "tmp.phasediff.rads.nii.gz", "-prefix", self.realfieldmap_rads, "-orient", "LPI"])

    def conv2Hz(self):
        self.realfieldmap_Hz = self.rawfmapfile_1.replace("_rawfmap_e1","Hz_fmap").replace("Fieldmap","RealFieldmap")
        subprocess.call(["3dcalc", "-a", self.realfieldmap_rads, "-expr", "a*0.1592", "-prefix", self.realfieldmap_Hz])

    def appendsidecar(self):

        # Append the BIDS sidecar for each fieldmap with the name of the associated scan file
        fmapjson = self.rawfmapfile_1.replace('.nii','.json')
        realfmapjson = self.realfieldmap_Hz.replace('.nii','.json')

        with open(fmapjson) as jsonfile:
            sidecar = json.load(jsonfile)
            sidecar['EchoTime1'] = '.007'
            sidecar['EchoTime2'] = '.010'
            sidecar['Units'] = 'Hz'

            if self.fmaptype == "DTI":
                fmaps = Path(self.fmap_dir)
                fmap_intendedfor_path = fmaps.parents[0] / 'dwi'
                scanlist = (scan for scan in fmap_intendedfor_path.iterdir() if str(scan).endswith('.nii'))
                fmapassoclist=[]
                for scan in scanlist:
                    fmapassoclist.append(str(Path(*scan.parts[-4:])))
                sidecar['IntendedFor'] = fmapassoclist
                
                tempfiles = (tempfile for tempfile in self.fmap_dir.iterdir() if any([tempfile.name.startswith('tmp.'),tempfile.name.__contains__('DTI_rawfmap_e1')]))
                for tempfile in tempfiles:
                    os.remove(tempfile)
                
                with open(realfmapjson, 'w+') as outfile:
                    json.dump(sidecar, outfile, indent=4)

            if self.fmaptype == "EPI":
                fmaps = Path(self.fmap_dir)
                fmap_intendedfor_path = fmaps.parents[0] / 'func'
                scanlist = (scan for scan in fmap_intendedfor_path.iterdir() if scan.name.endswith('.nii'))
                fmapassoclist=[]
                for scan in scanlist:
                    fmapassoclist.append(str(Path(*scan.parts[-4:])))
                sidecar['IntendedFor'] = fmapassoclist

                tempfiles = (tempfile for tempfile in self.fmap_dir.iterdir() if any([tempfile.name.startswith('tmp.'),tempfile.name.__contains__('EPI_rawfmap_e1')]))
                for tempfile in tempfiles:
                    os.remove(tempfile)
                
                with open(realfmapjson, 'w+') as outfile:
                    json.dump(sidecar, outfile, indent=4)

    # def fugue(self):
    #     self.dwicorr = self.dwi.parent / Path(str(self.dwi.parts[-1]).replace(".nii", ".corr.nii"))
    #     print(str(self.dwicorr))
    #     subprocess.call(["fugue", "-v", "-i", self.dwi, "--loadfmap="+str(self.phasediff_rads), "--dwell=0.000568", "-u", self.dwicorr])

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
        #self.fugue()

# if __name__ == '__main__':
#     mc = makefmaps()
#     mc.main()