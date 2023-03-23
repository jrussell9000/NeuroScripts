
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
import re

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
        return(rawFilesDict)

    def getfmapFiles(self, rawFilesDict):
        
        idx_to_type = {0: 'Magnitude', 1: 'Phase', 2: 'Imaginary', 3: 'Real'}
        # create an empty list
        magFilesDCM = []
        phaseFilesDCM = []
        realFilesDCM = []
        imagryFilesDCM = []
        for dirName, subdirList, fileList in os.walk(self.rawfmap_dir):
            for filename in fileList:
                if re.search(r'\d+$', filename):
                    GEImageType = dcmread(os.path.join(dirName, filename))[(0x0043, 0x102f)].value
                    if idx_to_type.get(GEImageType) == 'Magnitude':
                        magFilesDCM.append(os.path.join(dirName, filename))
                    elif idx_to_type.get(GEImageType) == 'Phase':
                        phaseFilesDCM.append(os.path.join(dirName, filename))
                    elif idx_to_type.get(GEImageType) == 'Imaginary':
                        imagryFilesDCM.append(os.path.join(dirName, filename))
                    elif idx_to_type.get(GEImageType) == 'Real':
                        realFilesDCM.append(os.path.join(dirName, filename))


        Refhdr = dcmread(magFilesDCM[0])
        # GEImageType = Refhdr[(0x0043,0x102f)].value
        Refhdr = Refhdr.items
        print(Refhdr)


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
        self.getfmapFiles(rawFilesDict)
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
