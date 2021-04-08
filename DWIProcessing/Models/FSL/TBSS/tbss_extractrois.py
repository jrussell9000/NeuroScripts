from pathlib import Path
import os
import subprocess

JHU_Atlas = Path('/Volumes/apps/linux/fsl-current/data/atlases/JHU/JHU-ICBM-labels-1mm.nii.gz')
allFAskeleton = Path('/Volumes/Vol6/YouthPTSD/JDR/tbss/tbssproc/stats/all_FA_skeletonised.nii.gz')
meanFAskeletonmask = Path('/Volumes/Vol6/YouthPTSD/JDR/tbss/tbssproc/stats/mean_FA_skeleton_mask.nii.gz')

os.chdir('/Volumes/Vol6/YouthPTSD/JDR/tbss/tbssproc/stats')

for i in range(1, 49):
    subprocess.run(['fslmaths', JHU_Atlas, '-thr', str(i), '-uthr', str(i), '-bin', 'roimask'])
    subprocess.run(['fslmaths', 'roimask', '-mas', meanFAskeletonmask, '-bin', 'roimask'])
    roi = str(i).zfill(3)
    subprocess.run(['fslmeants', '-i', allFAskeleton, '-m', 'roimask', '-o', str('mean_roi_' + roi + '.nii.gz')])
