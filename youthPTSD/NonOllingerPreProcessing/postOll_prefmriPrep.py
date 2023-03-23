import nibabel as nib
import numpy as np
import os
import pydicom
import shutil
import subprocess
import tarfile

from pathlib import Path
from scipy import ndimage
from sqlalchemy import null

ollpreprocdir = Path('/fast_scratch/jdr/YouthPTSD/OllingerPreproc')
TEdiff = 3
TRstoRemove = 4
FWHM = '3'
fsl_env = os.environ.copy()
fsl_env["FSLOUTPUTTYPE"] = "NIFTI"


class converttgz():

    dir2scan_dict = {
        "bravo": ["acq-axialFSPGR_T1w", "anat"],
        "resting": ["task-Resting_bold", "run_1"],
        "dynamic": ["task-DynamicFaces_bold", "run_1"],
        "emo": ["task-EmoReg_bold", "run_1"],
        "fieldmap_epi": ["acq-FieldmapEPI_bold", "fieldmap"],
        "fieldmap_dti": ["acq-FieldmapDTI_bold", "fieldmap"],
        "axt2flair": ["acq-axialFLAIR_T2w", "anat"],
        "dti_asset": ["acq-axialASSET_dwi", "dwi"]
    }

    def __init__(self, subj, tgzfile):
        self.subjses = "_".join([str("sub-" + subj[1:4]), ("ses-02" if "rescan" in subj else "ses-01")])
        self.subj_dir = Path(ollpreprocdir, subj)
        tgz_outdir = self.unpack(tgzfile)
        scantype = self.convert(tgzfile, tgz_outdir)
        if "task" in scantype:
            self.trimTRs()
        if scantype in ['acq-FieldmapEPI_bold', 'acq-FieldmapDTI_bold']:
            makefmap(self.subj_dir, self.subjses, scantype)
            #applyfmap(

    def unpack(self, tgzfile):
        with tarfile.open(tgzfile, 'r:gz') as tar:
            tgz_outdir = Path(tgzfile.parent, tar.next().name)
            tar.extractall(path=tgzfile.parent)
        return (tgz_outdir)

    def convert(self, tgzfile, tgz_outdir):
        for key in self.dir2scan_dict.keys():
            if key in tgzfile.name.lower():
                scantype = self.dir2scan_dict[key][0]
                outdirname = self.dir2scan_dict[key][1]
                break
            else:
                scantype = "nomatch"
        self.d2n_label = "_".join([self.subjses, scantype])
        self.d2n_outdir = Path(self.subj_dir, outdirname)
        self.d2n_outdir.mkdir(exist_ok=True)
        conv_cmd = ["dcm2niix", "-f", self.d2n_label, "-o", self.d2n_outdir, tgz_outdir]
        # print(conv_cmd)
        subprocess.run(conv_cmd)
        shutil.rmtree(tgz_outdir)
        return (scantype)

    def trimTRs(self):
        epi_path = Path(self.d2n_outdir, self.d2n_label).with_suffix(".nii")
        epi_img = nib.load(epi_path)
        epi_data = epi_img.get_fdata()
        epi_hdr = epi_img.header
        epi_affine = epi_img.affine
        epi_nTRs = epi_data.shape[3]
        trs2remove = TRstoRemove - 1
        trs2retain = np.arange(trs2remove, epi_nTRs, 1)
        epi_data_short = epi_data[:, :, :, trs2retain]
        epi_img_short = nib.Nifti1Image(epi_data_short, epi_affine, epi_hdr)
        epi_pathout = Path(self.d2n_outdir, self.d2n_label).with_suffix(".nii")
        nib.save(epi_img_short, epi_pathout)


class makefmap():

    def __init__(self, subjdir, subjses, scantype):
        # dicompath = Path(ollpreprocdir, subj, "dicoms")
        self.scantype = str(scantype)
        self.subjses = subjses
        self.subjdir = subjdir
        self.fmapdir = Path(self.subjdir, "fieldmap")

        # self.get_dcmhdr(tgzfile)
        fmaplist = self.getfmaps()
        mag1_mask_dil1_path = self.alignanat(fmaplist)
        phs1path, phs2path = self.computePhase(fmaplist, mag1_mask_dil1_path)
        phs1_unw_path, phs2_unw_path = self.unwrapPhase(fmaplist, phs1path, phs2path, mag1_mask_dil1_path)
        self.computePhaseDiff(phs1_unw_path, phs2_unw_path)
        self.cleanup()

    def get_dcmhdr(self, tgzfile):
        taroutdir = os.path.join(tgzfile.parent, tgzfile.name[7:-4])
        fmapdcm = pydicom.dcmread(Path("/".join([taroutdir, "i.000001.dcm"])))
        return (fmapdcm)

    def getfmaps(self):
        mag1path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1.nii"]))
        mag2path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1a.nii"]))
        img1path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1_imaginary.nii"]))
        img2path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1_imaginarya.nii"]))
        real1path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1_real.nii"]))
        real2path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1_reala.nii"]))
        fmaplist = [mag1path, mag2path, img1path, img2path, real1path, real2path]
        return (fmaplist)

    def alignanat(self, fmaplist):
        anatroot = Path(self.subjdir, "anat", "_".join([self.subjses, "acq-axialFSPGR_T1w.nii"]))
        anat_resamp_path = Path(self.fmapdir, "_".join([self.subjses, "acq-axialFSPGR_T1w_resamp2mag_e1.nii"]))

        subprocess.run(['3dresample', '-debug', '1', '-prefix', anat_resamp_path, '-inset', anatroot, '-master',
                        fmaplist[0]])
        anat_reg_path = Path(self.fmapdir, "_".join([self.subjses, "acq-axialFSPGR_T1w_reg2mag_e1.nii"]))

        subprocess.run(['3dvolreg', '-rotcom', '-Fourier', '-twopass', '-prefix', anat_reg_path, '-verbose', '-base',
                        anat_resamp_path, fmaplist[0]])
        mag1_noskull_path = fmaplist[0].with_name("_".join([self.subjses, self.scantype, "e1_noskull"]))

        subprocess.run(['bet', fmaplist[0], mag1_noskull_path, '-v', '-B', '-m', '-f', '.55', '-g', '0'], env=fsl_env)
        mag1_mask_path = fmaplist[0].with_name("_".join([self.subjses, self.scantype, "e1_noskull_mask.nii"]))

        mag1_mask_ero_path = fmaplist[0].with_name("_".join([self.subjses, self.scantype, "e1_noskull_mask_ero.nii.gz"]))
        subprocess.run(['fslmaths', mag1_mask_path, '-kernel', 'gauss', FWHM, '-ero', mag1_mask_ero_path])

        return (mag1_mask_ero_path)

    def computePhase(self, fmaplist, mag1_mask_ero_path):
        imag1_img = nib.load(fmaplist[2])
        imag1_data = imag1_img.get_fdata()
        imag2_img = nib.load(fmaplist[3])
        imag2_data = imag2_img.get_fdata()

        real1_img = nib.load(fmaplist[4])
        real1_data = real1_img.get_fdata()
        real2_img = nib.load(fmaplist[5])
        real2_data = real2_img.get_fdata()

        affine = real1_img.affine

        phs1_data = np.arctan2(imag1_data, real1_data)
        phs2_data = np.arctan2(imag2_data, real2_data)

        mag1_mask_dil1 = nib.load(mag1_mask_ero_path).get_fdata()

        phs1_data *= mag1_mask_dil1
        phs2_data *= mag1_mask_dil1
        phs1_path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1_phase1.nii"]))
        phs2_path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1_phase2.nii"]))
        phs1_img = nib.Nifti1Image(phs1_data, affine)
        phs2_img = nib.Nifti1Image(phs2_data, affine)
        nib.save(phs1_img, phs1_path)
        nib.save(phs2_img, phs2_path)
        return (phs1_path, phs2_path)

    def unwrapPhase(self, fmaplist, phs1path, phs2path, mag1_mask_dil1_path):
        phs1_unw_path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1_phase1_unw.nii"]))
        phs2_unw_path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "e1_phase2_unw.nii"]))
        mag1path = fmaplist[0]
        mag2path = fmaplist[1]
        subprocess.run(['prelude', '-a', mag1path, '-p', phs1path, '-u', phs1_unw_path, '-v',
                        '-m', mag1_mask_dil1_path])
        subprocess.run(['prelude', '-a', mag2path, '-p', phs2path, '-u', phs2_unw_path, '-v',
                        '-m', mag1_mask_dil1_path])
        return (phs1_unw_path, phs2_unw_path)

    def computePhaseDiff(self, phs1_unw_path, phs2_unw_path):
        phs_diff_path = Path(self.fmapdir, "_".join([self.subjses, self.scantype, "phasediff.nii"]))
        #subprocess.run(['fslmaths', phs1_unw_path, "-sub", phs2_unw_path, "-mul", "1000", "-div", "3", phs_diff_path,
        #                "-odt", "float"])

    def rescale(self):
        null

    def cleanup(self):
        null
        # for nii in self.fmapdir.glob("*_e1*"):
        #     os.remove(nii)

# class fmapCorrect():

#     def __init__(self):

# fslmaths phase1_unwrapped_rad -sub phase0_unwrapped_rad -mul 1000 -div TEdiff fieldmap_rads -odt float
# subjlist = ["_142rescan", "_148rescan", "_149rescan", "_153rescan", "_154rescan", "_155rescan", "_156rescan",
# "_157rescan"]

# for z in *.dcm; do bzip2 $z; done
# for z in *.dcm.bz2; do mv $z "${z%.*.*}.bz2"; done

subjlist = ["_142rescantest"]

for subj in subjlist:
    for tgzfile in sorted(Path(ollpreprocdir, subj, "dicoms").glob("*.tgz")):
        converttgz(subj, tgzfile)
