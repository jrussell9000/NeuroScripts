import sys
import os
import subprocess
import pathlib
from pathlib import Path, PosixPath
import shutil
import glob
import fnmatch
from distutils.dir_util import copy_tree
from lib.Converters import fieldmaps as fmaps
import lib.Diffusion

# Copy necessary subject files\folders to a processing directory

class dwipreproc():

    def __init__(self, dwi_in, bvec_in, bval_in, dwijson_in, fmap_in, mag_in, procdir, subj, ses):
        
        self.dwi_in = dwi_in
        self.bvec_in = Path(bvec_in)
        self.bval_in = Path(bval_in)
        self.dwijson_in = Path(dwijson_in)
        self.fmap_in = Path(fmap_in)
        self.mag_in = Path(mag_in)
        self.procdir = Path(procdir, subj, ses)
        self.main()

    def makesubjprocdirs(self):
        if self.procdir.exists():
            shutil.rmtree(self.procdir)
        self.procdir.mkdir(exist_ok=True, parents=True)

        self.preprocdir = Path(self.procdir / 'preproc')
        self.preprocdir.mkdir(exist_ok=True, parents=True)

        print("==Copying files to processing directory==","\n")
        self.basename = self.dwi_in.name[:14]

        self.dwi = self.preprocdir / str(self.basename + '_dwi_orig.nii')
        shutil.copy(self.dwi_in, self.dwi)

        self.dwijson = self.preprocdir / str(self.basename + '_dwi.json')
        shutil.copy(self.dwijson_in, self.dwijson)

        self.bvec = self.preprocdir / str(self.basename + '_dwi.bvec')
        shutil.copy(self.bvec_in, self.bvec)

        self.bval = self.preprocdir / str(self.basename + '_dwi.bval')
        shutil.copy(self.bval_in, self.bval)

        self.fmap = self.preprocdir / str(self.basename + '_fmap.nii')
        shutil.copy(self.fmap_in, self.fmap)

        self.mag = self.preprocdir / str(self.basename + '_mag.nii')
        shutil.copy(self.mag_in, self.mag)
    
    def fieldmapcorrection(self):

        #Skull strip the reference
        print("==Skull stripping the reference image==\n")
        mag_brain = self.preprocdir / str(self.basename + '_mag_brain.nii.gz')
        subprocess.run(['bet2', self.mag, mag_brain, '-f', '0.3'])

        #Mask and correct the fieldmap
        print("==Masking and correcting the fieldmap==","\n")
        fmap_brain = self.preprocdir / str(self.basename + '_fmap_brain.nii.gz')
        subprocess.run(['fslmaths', self.fmap, '-mas', mag_brain, fmap_brain])
        fmap_brain_corr = self.preprocdir / str(self.basename + '_fmap_brain_corr.nii.gz')
        subprocess.run(['fugue', '-v', '--loadfmap='+str(fmap_brain), '--smooth3=1.0', '--despike', '--savefmap='+str(fmap_brain_corr)], stdout=sys.stdout, stderr=sys.stderr)

        #Warp the reference image
        print("\n==Warping the reference image==","\n")
        mag_brain_warped = self.preprocdir / str(self.basename + '_mag_brain_warped.nii.gz')
        subprocess.run(['fugue', '-v', '-i', mag_brain, '--unwarpdir=y', '--dwell=0.000568', '--loadfmap='+str(fmap_brain_corr), '-s', '0.5', '-w', mag_brain_warped], stdout=sys.stdout, stderr=sys.stderr)
        
        #Extract the b0 images from the DWI series, output their mean, and skull strip it
        print("\n==Computing the brain-extracted mean B0==","\n")
        allb0s = self.preprocdir / str(self.basename + '_allb0s.nii.gz')
        meanb0 = self.preprocdir / str(self.basename + '_meanb0.nii.gz')
        meanb0_brain = self.preprocdir / str(self.basename + '_meanb0_brain.nii.gz')
        subprocess.run(['fslroi', self.dwi, allb0s, '0', '7'])
        subprocess.run(['fslmaths', allb0s, '-Tmean', meanb0])
        subprocess.run(['bet2', meanb0, meanb0_brain, '-f', '0.3'])
        
        #Align warped reference to the mean b0
        print("==Registering warped magnitude to mean B0==","\n")
        mag_brain_warped_aligned = self.preprocdir / str(self.basename + '_mag_brain_warped_aligned.nii.gz')
        mag_matrix = self.preprocdir / str(self.basename + '_mag2dwi.mat')
        subprocess.run(['flirt', '-in', mag_brain_warped, '-ref', meanb0_brain, '-out', mag_brain_warped_aligned, '-omat', mag_matrix, '-dof', '6'], stdout=sys.stdout, stderr=sys.stderr)
        
        #Apply the transformation matrix to the fieldmap
        print("==Aligning the corrected fieldmap with the mean B0==","\n")
        fmap_brain_corr_warped = self.preprocdir / str(self.basename + '_fmap_brain_corr_warped.nii.gz')
        subprocess.run(['flirt', '-in', fmap_brain_corr, '-ref', meanb0_brain, '-applyxfm', '-init', mag_matrix, '-out', fmap_brain_corr_warped], stdout=sys.stdout, stderr=sys.stderr)
        
        #Undistort the DWI series
        print("==Undistorting the full DWI series==","\n")
        self.dwifmapcorr = self.preprocdir / str(self.basename + '_fmapcorr_dwi.nii.gz')
        subprocess.run(['fugue', '-v', '-i', self.dwi, '--unwarpdir=y', '--dwell=0.000568', '--loadfmap='+str(fmap_brain_corr_warped), '-u', self.dwifmapcorr], stdout=sys.stdout, stderr=sys.stderr)
        #DWELL TIME = EffectiveEchoSpacing!!! per https://www.fmrib.ox.ac.uk/primers/intro_primer/ExBox19/IntroBox19.html

    def mrconvert2mif(self):
        self.dwi_mif = self.preprocdir / str(self.basename + '_fmapcorr_dwi.mif')
        subprocess.run(['mrconvert', '-force', '-json_import', self.dwijson, '-fslgrad', self.bvec, self.bval, self.dwifmapcorr, self.dwi_mif])

    def denoise(self):
        self.dwi_mif_den = self.preprocdir / str(self.basename + '_den.mif')
        subprocess.run(['dwidenoise', '-force', self.dwi_mif, self.dwi_mif_den])

    def degibbs(self):
        self.dwi_mif_den_deg = self.preprocdir / str(self.basename + '_den_deg.mif')
        subprocess.run(['mrdegibbs', '-force', self.dwi_mif_den, self.dwi_mif_den_deg])

    def mrconvert2nii(self):
        self.dwi_nii_den_deg = self.procdir / str(self.basename + '_preproc_dwi.nii')
        subprocess.run(['mrconvert', '-force', self.dwi_mif_den_deg, self.dwi_nii_den_deg])
    
    # def getpreprocdwi(self):
    #     self.dwi_nii_den_deg = '/Users/jdrussell3/pyout/sub-004/ses-01/sub-004_ses-01_dwi_orig.nii'
    #     return(self.dwi_nii_den_deg)

    def main(self):
        self.makesubjprocdirs()
        self.fieldmapcorrection()
        self.mrconvert2mif()
        self.denoise()
        self.degibbs()
        self.mrconvert2nii()      

if __name__ == '__main__':

    pp = dwipreproc()
    pp.__main__()

