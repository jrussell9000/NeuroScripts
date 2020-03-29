

#---------------------------------
# New invocation of recon-all Mon Dec  2 13:52:57 CST 2019 

 mri_convert /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/sub-151_ses-01_acq-AXFSPGRBRAVONEW_T1w.nii /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/orig/001.mgz 

#--------------------------------------------
#@# MotionCor Mon Dec  2 13:53:38 CST 2019

 cp /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/orig/001.mgz /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/rawavg.mgz 


 mri_convert /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/rawavg.mgz /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/orig.mgz --conform 


 mri_add_xform_to_header -c /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/transforms/talairach.xfm /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/orig.mgz /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/orig.mgz 

#--------------------------------------------
#@# Talairach Mon Dec  2 13:53:49 CST 2019

 mri_nu_correct.mni --no-rescale --i orig.mgz --o orig_nu.mgz --n 1 --proto-iters 1000 --distance 50 


 talairach_avi --i orig_nu.mgz --xfm transforms/talairach.auto.xfm 

talairach_avi log file is transforms/talairach_avi.log...

 cp transforms/talairach.auto.xfm transforms/talairach.xfm 

#--------------------------------------------
#@# Talairach Failure Detection Mon Dec  2 13:55:33 CST 2019

 talairach_afd -T 0.005 -xfm transforms/talairach.xfm 


 awk -f /Volumes/apps/linux/freesurfer-current/bin/extract_talairach_avi_QA.awk /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/transforms/talairach_avi.log 


 tal_QC_AZS /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/transforms/talairach_avi.log 

#--------------------------------------------
#@# Nu Intensity Correction Mon Dec  2 13:55:34 CST 2019

 mri_nu_correct.mni --i orig.mgz --o nu.mgz --uchar transforms/talairach.xfm --n 2 


 mri_add_xform_to_header -c /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/transforms/talairach.xfm nu.mgz nu.mgz 

#--------------------------------------------
#@# Intensity Normalization Mon Dec  2 13:57:40 CST 2019

 mri_normalize -g 1 -seed 1234 -mprage nu.mgz T1.mgz 

#--------------------------------------------
#@# Skull Stripping Mon Dec  2 13:59:55 CST 2019

 mri_em_register -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mri_em_register.skull.dat -skull nu.mgz /Volumes/apps/linux/freesurfer-current/average/RB_all_withskull_2016-05-10.vc700.gca transforms/talairach_with_skull.lta 


 mri_watershed -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mri_watershed.dat -T1 -brain_atlas /Volumes/apps/linux/freesurfer-current/average/RB_all_withskull_2016-05-10.vc700.gca transforms/talairach_with_skull.lta T1.mgz brainmask.auto.mgz 


 cp brainmask.auto.mgz brainmask.mgz 

#-------------------------------------
#@# EM Registration Mon Dec  2 14:19:01 CST 2019

 mri_em_register -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mri_em_register.dat -uns 3 -mask brainmask.mgz nu.mgz /Volumes/apps/linux/freesurfer-current/average/RB_all_2016-05-10.vc700.gca transforms/talairach.lta 

#--------------------------------------
#@# CA Normalize Mon Dec  2 14:32:50 CST 2019

 mri_ca_normalize -c ctrl_pts.mgz -mask brainmask.mgz nu.mgz /Volumes/apps/linux/freesurfer-current/average/RB_all_2016-05-10.vc700.gca transforms/talairach.lta norm.mgz 

#--------------------------------------
#@# CA Reg Mon Dec  2 14:34:10 CST 2019

 mri_ca_register -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mri_ca_register.dat -nobigventricles -T transforms/talairach.lta -align-after -mask brainmask.mgz norm.mgz /Volumes/apps/linux/freesurfer-current/average/RB_all_2016-05-10.vc700.gca transforms/talairach.m3z 

#--------------------------------------
#@# SubCort Seg Mon Dec  2 17:25:54 CST 2019

 mri_ca_label -relabel_unlikely 9 .3 -prior 0.5 -align norm.mgz transforms/talairach.m3z /Volumes/apps/linux/freesurfer-current/average/RB_all_2016-05-10.vc700.gca aseg.auto_noCCseg.mgz 

#--------------------------------------
#@# CC Seg Mon Dec  2 18:26:02 CST 2019

 mri_cc -aseg aseg.auto_noCCseg.mgz -o aseg.auto.mgz -lta /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/mri/transforms/cc_up.lta _151 

#--------------------------------------
#@# Merge ASeg Mon Dec  2 18:29:42 CST 2019

 cp aseg.auto.mgz aseg.presurf.mgz 

#--------------------------------------------
#@# Intensity Normalization2 Mon Dec  2 18:29:42 CST 2019

 mri_normalize -seed 1234 -mprage -aseg aseg.presurf.mgz -mask brainmask.mgz norm.mgz brain.mgz 

#--------------------------------------------
#@# Mask BFS Mon Dec  2 18:35:15 CST 2019

 mri_mask -T 5 brain.mgz brainmask.mgz brain.finalsurfs.mgz 

#--------------------------------------------
#@# WM Segmentation Mon Dec  2 18:35:18 CST 2019

 mri_segment -mprage brain.mgz wm.seg.mgz 


 mri_edit_wm_with_aseg -keep-in wm.seg.mgz brain.mgz aseg.presurf.mgz wm.asegedit.mgz 


 mri_pretess wm.asegedit.mgz wm norm.mgz wm.mgz 

#--------------------------------------------
#@# Fill Mon Dec  2 18:39:56 CST 2019

 mri_fill -a ../scripts/ponscc.cut.log -xform transforms/talairach.lta -segmentation aseg.presurf.mgz wm.mgz filled.mgz 

#--------------------------------------------
#@# Tessellate lh Mon Dec  2 18:42:05 CST 2019

 mri_pretess ../mri/filled.mgz 255 ../mri/norm.mgz ../mri/filled-pretess255.mgz 


 mri_tessellate ../mri/filled-pretess255.mgz 255 ../surf/lh.orig.nofix 


 rm -f ../mri/filled-pretess255.mgz 


 mris_extract_main_component ../surf/lh.orig.nofix ../surf/lh.orig.nofix 

#--------------------------------------------
#@# Tessellate rh Mon Dec  2 18:42:15 CST 2019

 mri_pretess ../mri/filled.mgz 127 ../mri/norm.mgz ../mri/filled-pretess127.mgz 


 mri_tessellate ../mri/filled-pretess127.mgz 127 ../surf/rh.orig.nofix 


 rm -f ../mri/filled-pretess127.mgz 


 mris_extract_main_component ../surf/rh.orig.nofix ../surf/rh.orig.nofix 

#--------------------------------------------
#@# Smooth1 lh Mon Dec  2 18:42:26 CST 2019

 mris_smooth -nw -seed 1234 ../surf/lh.orig.nofix ../surf/lh.smoothwm.nofix 

#--------------------------------------------
#@# Smooth1 rh Mon Dec  2 18:42:36 CST 2019

 mris_smooth -nw -seed 1234 ../surf/rh.orig.nofix ../surf/rh.smoothwm.nofix 

#--------------------------------------------
#@# Inflation1 lh Mon Dec  2 18:42:46 CST 2019

 mris_inflate -no-save-sulc ../surf/lh.smoothwm.nofix ../surf/lh.inflated.nofix 

#--------------------------------------------
#@# Inflation1 rh Mon Dec  2 18:43:49 CST 2019

 mris_inflate -no-save-sulc ../surf/rh.smoothwm.nofix ../surf/rh.inflated.nofix 

#--------------------------------------------
#@# QSphere lh Mon Dec  2 18:44:48 CST 2019

 mris_sphere -q -p 6 -a 128 -seed 1234 ../surf/lh.inflated.nofix ../surf/lh.qsphere.nofix 

#--------------------------------------------
#@# QSphere rh Mon Dec  2 18:51:54 CST 2019

 mris_sphere -q -p 6 -a 128 -seed 1234 ../surf/rh.inflated.nofix ../surf/rh.qsphere.nofix 

#@# Fix Topology lh Mon Dec  2 18:58:05 CST 2019

 mris_fix_topology -mgz -sphere qsphere.nofix -inflated inflated.nofix -orig orig.nofix -out orig -ga -seed 1234 _151 lh 

#@# Fix Topology rh Mon Dec  2 19:28:55 CST 2019

 mris_fix_topology -mgz -sphere qsphere.nofix -inflated inflated.nofix -orig orig.nofix -out orig -ga -seed 1234 _151 rh 


 mris_euler_number ../surf/lh.orig 


 mris_euler_number ../surf/rh.orig 


 mris_remove_intersection ../surf/lh.orig ../surf/lh.orig 


 rm ../surf/lh.inflated 


 mris_remove_intersection ../surf/rh.orig ../surf/rh.orig 


 rm ../surf/rh.inflated 

#--------------------------------------------
#@# Make White Surf lh Mon Dec  2 19:46:21 CST 2019

 mris_make_surfaces -save-res -save-target -aseg ../mri/aseg.presurf -white white.preaparc -noaparc -whiteonly -mgz -T1 brain.finalsurfs _151 lh 

#--------------------------------------------
#@# Make White Surf rh Mon Dec  2 20:12:45 CST 2019

 mris_make_surfaces -save-res -save-target -aseg ../mri/aseg.presurf -white white.preaparc -noaparc -whiteonly -mgz -T1 brain.finalsurfs _151 rh 

#--------------------------------------------
#@# Smooth2 lh Mon Dec  2 20:30:16 CST 2019

 mris_smooth -n 3 -nw -seed 1234 ../surf/lh.white.preaparc ../surf/lh.smoothwm 

#--------------------------------------------
#@# Smooth2 rh Mon Dec  2 20:30:22 CST 2019

 mris_smooth -n 3 -nw -seed 1234 ../surf/rh.white.preaparc ../surf/rh.smoothwm 

#--------------------------------------------
#@# Inflation2 lh Mon Dec  2 20:30:28 CST 2019

 mris_inflate -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mris_inflate.lh.dat ../surf/lh.smoothwm ../surf/lh.inflated 

#--------------------------------------------
#@# Inflation2 rh Mon Dec  2 20:30:59 CST 2019

 mris_inflate -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mris_inflate.rh.dat ../surf/rh.smoothwm ../surf/rh.inflated 

#--------------------------------------------
#@# Curv .H and .K lh Mon Dec  2 20:31:30 CST 2019

 mris_curvature -w -seed 1234 lh.white.preaparc 


 mris_curvature -seed 1234 -thresh .999 -n -a 5 -w -distances 10 10 lh.inflated 

#--------------------------------------------
#@# Curv .H and .K rh Mon Dec  2 20:33:01 CST 2019

 mris_curvature -w -seed 1234 rh.white.preaparc 


 mris_curvature -seed 1234 -thresh .999 -n -a 5 -w -distances 10 10 rh.inflated 


#-----------------------------------------
#@# Curvature Stats lh Mon Dec  2 20:34:30 CST 2019

 mris_curvature_stats -m --writeCurvatureFiles -G -o ../stats/lh.curv.stats -F smoothwm _151 lh curv sulc 


#-----------------------------------------
#@# Curvature Stats rh Mon Dec  2 20:34:36 CST 2019

 mris_curvature_stats -m --writeCurvatureFiles -G -o ../stats/rh.curv.stats -F smoothwm _151 rh curv sulc 

#--------------------------------------------
#@# Sphere lh Mon Dec  2 20:34:40 CST 2019

 mris_sphere -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mris_sphere.lh.dat -seed 1234 ../surf/lh.inflated ../surf/lh.sphere 

#--------------------------------------------
#@# Sphere rh Mon Dec  2 20:57:55 CST 2019

 mris_sphere -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mris_sphere.rh.dat -seed 1234 ../surf/rh.inflated ../surf/rh.sphere 

#--------------------------------------------
#@# Surf Reg lh Mon Dec  2 21:12:52 CST 2019

 mris_register -curv -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mris_register.lh.dat ../surf/lh.sphere /Volumes/apps/linux/freesurfer-current/average/lh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif ../surf/lh.sphere.reg 


 ln -sf lh.sphere.reg lh.fsaverage.sphere.reg 

#--------------------------------------------
#@# Surf Reg rh Mon Dec  2 21:24:55 CST 2019

 mris_register -curv -rusage /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/_151/touch/rusage.mris_register.rh.dat ../surf/rh.sphere /Volumes/apps/linux/freesurfer-current/average/rh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif ../surf/rh.sphere.reg 


 ln -sf rh.sphere.reg rh.fsaverage.sphere.reg 

#--------------------------------------------
#@# Jacobian white lh Mon Dec  2 21:36:44 CST 2019

 mris_jacobian ../surf/lh.white.preaparc ../surf/lh.sphere.reg ../surf/lh.jacobian_white 

#--------------------------------------------
#@# Jacobian white rh Mon Dec  2 21:36:46 CST 2019

 mris_jacobian ../surf/rh.white.preaparc ../surf/rh.sphere.reg ../surf/rh.jacobian_white 

#--------------------------------------------
#@# AvgCurv lh Mon Dec  2 21:36:47 CST 2019

 mrisp_paint -a 5 /Volumes/apps/linux/freesurfer-current/average/lh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif#6 ../surf/lh.sphere.reg ../surf/lh.avg_curv 

#--------------------------------------------
#@# AvgCurv rh Mon Dec  2 21:36:48 CST 2019

 mrisp_paint -a 5 /Volumes/apps/linux/freesurfer-current/average/rh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif#6 ../surf/rh.sphere.reg ../surf/rh.avg_curv 

#-----------------------------------------
#@# Cortical Parc lh Mon Dec  2 21:36:50 CST 2019

 mris_ca_label -l ../label/lh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 _151 lh ../surf/lh.sphere.reg /Volumes/apps/linux/freesurfer-current/average/lh.DKaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/lh.aparc.annot 

#-----------------------------------------
#@# Cortical Parc rh Mon Dec  2 21:37:06 CST 2019

 mris_ca_label -l ../label/rh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 _151 rh ../surf/rh.sphere.reg /Volumes/apps/linux/freesurfer-current/average/rh.DKaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/rh.aparc.annot 

#--------------------------------------------
#@# Make Pial Surf lh Mon Dec  2 21:37:22 CST 2019

 mris_make_surfaces -save-res -save-target -orig_white white.preaparc -orig_pial white.preaparc -aseg ../mri/aseg.presurf -mgz -T1 brain.finalsurfs _151 lh 

#--------------------------------------------
#@# Make Pial Surf rh Mon Dec  2 21:53:41 CST 2019

 mris_make_surfaces -save-res -save-target -orig_white white.preaparc -orig_pial white.preaparc -aseg ../mri/aseg.presurf -mgz -T1 brain.finalsurfs _151 rh 

#--------------------------------------------
#@# Surf Volume lh Mon Dec  2 22:12:27 CST 2019

 vertexvol --s _151 --lh --th3 

#--------------------------------------------
#@# Surf Volume rh Mon Dec  2 22:12:30 CST 2019

 vertexvol --s _151 --rh --th3 

#--------------------------------------------
#@# Cortical ribbon mask Mon Dec  2 22:12:33 CST 2019

 mris_volmask --aseg_name aseg.presurf --label_left_white 2 --label_left_ribbon 3 --label_right_white 41 --label_right_ribbon 42 --save_ribbon _151 

#-----------------------------------------
#@# Parcellation Stats lh Mon Dec  2 22:28:22 CST 2019

 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.stats -b -a ../label/lh.aparc.annot -c ../label/aparc.annot.ctab _151 lh white 


 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.pial.stats -b -a ../label/lh.aparc.annot -c ../label/aparc.annot.ctab _151 lh pial 

#-----------------------------------------
#@# Parcellation Stats rh Mon Dec  2 22:29:42 CST 2019

 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.stats -b -a ../label/rh.aparc.annot -c ../label/aparc.annot.ctab _151 rh white 


 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.pial.stats -b -a ../label/rh.aparc.annot -c ../label/aparc.annot.ctab _151 rh pial 

#-----------------------------------------
#@# Cortical Parc 2 lh Mon Dec  2 22:30:57 CST 2019

 mris_ca_label -l ../label/lh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 _151 lh ../surf/lh.sphere.reg /Volumes/apps/linux/freesurfer-current/average/lh.CDaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/lh.aparc.a2009s.annot 

#-----------------------------------------
#@# Cortical Parc 2 rh Mon Dec  2 22:31:27 CST 2019

 mris_ca_label -l ../label/rh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 _151 rh ../surf/rh.sphere.reg /Volumes/apps/linux/freesurfer-current/average/rh.CDaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/rh.aparc.a2009s.annot 

#-----------------------------------------
#@# Parcellation Stats 2 lh Mon Dec  2 22:31:58 CST 2019

 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.a2009s.stats -b -a ../label/lh.aparc.a2009s.annot -c ../label/aparc.annot.a2009s.ctab _151 lh white 

#-----------------------------------------
#@# Parcellation Stats 2 rh Mon Dec  2 22:32:39 CST 2019

 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.a2009s.stats -b -a ../label/rh.aparc.a2009s.annot -c ../label/aparc.annot.a2009s.ctab _151 rh white 

#-----------------------------------------
#@# Cortical Parc 3 lh Mon Dec  2 22:33:18 CST 2019

 mris_ca_label -l ../label/lh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 _151 lh ../surf/lh.sphere.reg /Volumes/apps/linux/freesurfer-current/average/lh.DKTaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/lh.aparc.DKTatlas.annot 

#-----------------------------------------
#@# Cortical Parc 3 rh Mon Dec  2 22:33:39 CST 2019

 mris_ca_label -l ../label/rh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 _151 rh ../surf/rh.sphere.reg /Volumes/apps/linux/freesurfer-current/average/rh.DKTaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/rh.aparc.DKTatlas.annot 

#-----------------------------------------
#@# Parcellation Stats 3 lh Mon Dec  2 22:34:00 CST 2019

 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.DKTatlas.stats -b -a ../label/lh.aparc.DKTatlas.annot -c ../label/aparc.annot.DKTatlas.ctab _151 lh white 

#-----------------------------------------
#@# Parcellation Stats 3 rh Mon Dec  2 22:34:38 CST 2019

 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.DKTatlas.stats -b -a ../label/rh.aparc.DKTatlas.annot -c ../label/aparc.annot.DKTatlas.ctab _151 rh white 

#-----------------------------------------
#@# WM/GM Contrast lh Mon Dec  2 22:35:19 CST 2019

 pctsurfcon --s _151 --lh-only 

#-----------------------------------------
#@# WM/GM Contrast rh Mon Dec  2 22:35:26 CST 2019

 pctsurfcon --s _151 --rh-only 

#-----------------------------------------
#@# Relabel Hypointensities Mon Dec  2 22:35:32 CST 2019

 mri_relabel_hypointensities aseg.presurf.mgz ../surf aseg.presurf.hypos.mgz 

#-----------------------------------------
#@# AParc-to-ASeg aparc Mon Dec  2 22:35:59 CST 2019

 mri_aparc2aseg --s _151 --volmask --aseg aseg.presurf.hypos --relabel mri/norm.mgz mri/transforms/talairach.m3z /Volumes/apps/linux/freesurfer-current/average/RB_all_2016-05-10.vc700.gca mri/aseg.auto_noCCseg.label_intensities.txt 

#-----------------------------------------
#@# AParc-to-ASeg a2009s Mon Dec  2 22:47:26 CST 2019

 mri_aparc2aseg --s _151 --volmask --aseg aseg.presurf.hypos --relabel mri/norm.mgz mri/transforms/talairach.m3z /Volumes/apps/linux/freesurfer-current/average/RB_all_2016-05-10.vc700.gca mri/aseg.auto_noCCseg.label_intensities.txt --a2009s 

#-----------------------------------------
#@# AParc-to-ASeg DKTatlas Mon Dec  2 23:02:48 CST 2019

 mri_aparc2aseg --s _151 --volmask --aseg aseg.presurf.hypos --relabel mri/norm.mgz mri/transforms/talairach.m3z /Volumes/apps/linux/freesurfer-current/average/RB_all_2016-05-10.vc700.gca mri/aseg.auto_noCCseg.label_intensities.txt --annot aparc.DKTatlas --o mri/aparc.DKTatlas+aseg.mgz 

#-----------------------------------------
#@# APas-to-ASeg Mon Dec  2 23:17:22 CST 2019

 apas2aseg --i aparc+aseg.mgz --o aseg.mgz 

#--------------------------------------------
#@# ASeg Stats Mon Dec  2 23:17:32 CST 2019

 mri_segstats --seed 1234 --seg mri/aseg.mgz --sum stats/aseg.stats --pv mri/norm.mgz --empty --brainmask mri/brainmask.mgz --brain-vol-from-seg --excludeid 0 --excl-ctxgmwm --supratent --subcortgray --in mri/norm.mgz --in-intensity-name norm --in-intensity-units MR --etiv --surf-wm-vol --surf-ctx-vol --totalgray --euler --ctab /Volumes/apps/linux/freesurfer-current/ASegStatsLUT.txt --subject _151 

#-----------------------------------------
#@# WMParc Mon Dec  2 23:22:19 CST 2019

 mri_aparc2aseg --s _151 --labelwm --hypo-as-wm --rip-unknown --volmask --o mri/wmparc.mgz --ctxseg aparc+aseg.mgz 


 mri_segstats --seed 1234 --seg mri/wmparc.mgz --sum stats/wmparc.stats --pv mri/norm.mgz --excludeid 0 --brainmask mri/brainmask.mgz --in mri/norm.mgz --in-intensity-name norm --in-intensity-units MR --subject _151 --surf-wm-vol --ctab /Volumes/apps/linux/freesurfer-current/WMParcStatsLUT.txt --etiv 

INFO: fsaverage subject does not exist in SUBJECTS_DIR
INFO: Creating symlink to fsaverage subject...

 cd /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts; ln -s /Volumes/apps/linux/freesurfer-current/subjects/fsaverage; cd - 

#--------------------------------------------
#@# BA_exvivo Labels lh Mon Dec  2 23:38:56 CST 2019

 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA1_exvivo.label --trgsubject _151 --trglabel ./lh.BA1_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA2_exvivo.label --trgsubject _151 --trglabel ./lh.BA2_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA3a_exvivo.label --trgsubject _151 --trglabel ./lh.BA3a_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA3b_exvivo.label --trgsubject _151 --trglabel ./lh.BA3b_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA4a_exvivo.label --trgsubject _151 --trglabel ./lh.BA4a_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA4p_exvivo.label --trgsubject _151 --trglabel ./lh.BA4p_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA6_exvivo.label --trgsubject _151 --trglabel ./lh.BA6_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA44_exvivo.label --trgsubject _151 --trglabel ./lh.BA44_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA45_exvivo.label --trgsubject _151 --trglabel ./lh.BA45_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.V1_exvivo.label --trgsubject _151 --trglabel ./lh.V1_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.V2_exvivo.label --trgsubject _151 --trglabel ./lh.V2_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.MT_exvivo.label --trgsubject _151 --trglabel ./lh.MT_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.entorhinal_exvivo.label --trgsubject _151 --trglabel ./lh.entorhinal_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.perirhinal_exvivo.label --trgsubject _151 --trglabel ./lh.perirhinal_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA1_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.BA1_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA2_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.BA2_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA3a_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.BA3a_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA3b_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.BA3b_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA4a_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.BA4a_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA4p_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.BA4p_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA6_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.BA6_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA44_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.BA44_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.BA45_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.BA45_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.V1_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.V1_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.V2_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.V2_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.MT_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.MT_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.entorhinal_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.entorhinal_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/lh.perirhinal_exvivo.thresh.label --trgsubject _151 --trglabel ./lh.perirhinal_exvivo.thresh.label --hemi lh --regmethod surface 


 mris_label2annot --s _151 --hemi lh --ctab /Volumes/apps/linux/freesurfer-current/average/colortable_BA.txt --l lh.BA1_exvivo.label --l lh.BA2_exvivo.label --l lh.BA3a_exvivo.label --l lh.BA3b_exvivo.label --l lh.BA4a_exvivo.label --l lh.BA4p_exvivo.label --l lh.BA6_exvivo.label --l lh.BA44_exvivo.label --l lh.BA45_exvivo.label --l lh.V1_exvivo.label --l lh.V2_exvivo.label --l lh.MT_exvivo.label --l lh.perirhinal_exvivo.label --l lh.entorhinal_exvivo.label --a BA_exvivo --maxstatwinner --noverbose 


 mris_label2annot --s _151 --hemi lh --ctab /Volumes/apps/linux/freesurfer-current/average/colortable_BA.txt --l lh.BA1_exvivo.thresh.label --l lh.BA2_exvivo.thresh.label --l lh.BA3a_exvivo.thresh.label --l lh.BA3b_exvivo.thresh.label --l lh.BA4a_exvivo.thresh.label --l lh.BA4p_exvivo.thresh.label --l lh.BA6_exvivo.thresh.label --l lh.BA44_exvivo.thresh.label --l lh.BA45_exvivo.thresh.label --l lh.V1_exvivo.thresh.label --l lh.V2_exvivo.thresh.label --l lh.MT_exvivo.thresh.label --l lh.perirhinal_exvivo.thresh.label --l lh.entorhinal_exvivo.thresh.label --a BA_exvivo.thresh --maxstatwinner --noverbose 


 mris_anatomical_stats -th3 -mgz -f ../stats/lh.BA_exvivo.stats -b -a ./lh.BA_exvivo.annot -c ./BA_exvivo.ctab _151 lh white 


 mris_anatomical_stats -th3 -mgz -f ../stats/lh.BA_exvivo.thresh.stats -b -a ./lh.BA_exvivo.thresh.annot -c ./BA_exvivo.thresh.ctab _151 lh white 

#--------------------------------------------
#@# BA_exvivo Labels rh Mon Dec  2 23:45:09 CST 2019

 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA1_exvivo.label --trgsubject _151 --trglabel ./rh.BA1_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA2_exvivo.label --trgsubject _151 --trglabel ./rh.BA2_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA3a_exvivo.label --trgsubject _151 --trglabel ./rh.BA3a_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA3b_exvivo.label --trgsubject _151 --trglabel ./rh.BA3b_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA4a_exvivo.label --trgsubject _151 --trglabel ./rh.BA4a_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA4p_exvivo.label --trgsubject _151 --trglabel ./rh.BA4p_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA6_exvivo.label --trgsubject _151 --trglabel ./rh.BA6_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA44_exvivo.label --trgsubject _151 --trglabel ./rh.BA44_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA45_exvivo.label --trgsubject _151 --trglabel ./rh.BA45_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.V1_exvivo.label --trgsubject _151 --trglabel ./rh.V1_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.V2_exvivo.label --trgsubject _151 --trglabel ./rh.V2_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.MT_exvivo.label --trgsubject _151 --trglabel ./rh.MT_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.entorhinal_exvivo.label --trgsubject _151 --trglabel ./rh.entorhinal_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.perirhinal_exvivo.label --trgsubject _151 --trglabel ./rh.perirhinal_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA1_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.BA1_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA2_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.BA2_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA3a_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.BA3a_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA3b_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.BA3b_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA4a_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.BA4a_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA4p_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.BA4p_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA6_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.BA6_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA44_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.BA44_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.BA45_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.BA45_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.V1_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.V1_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.V2_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.V2_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.MT_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.MT_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.entorhinal_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.entorhinal_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /Volumes/Vol6/YouthPTSD/scripts/sah_scripts/freersurferScripts/fsaverage/label/rh.perirhinal_exvivo.thresh.label --trgsubject _151 --trglabel ./rh.perirhinal_exvivo.thresh.label --hemi rh --regmethod surface 


 mris_label2annot --s _151 --hemi rh --ctab /Volumes/apps/linux/freesurfer-current/average/colortable_BA.txt --l rh.BA1_exvivo.label --l rh.BA2_exvivo.label --l rh.BA3a_exvivo.label --l rh.BA3b_exvivo.label --l rh.BA4a_exvivo.label --l rh.BA4p_exvivo.label --l rh.BA6_exvivo.label --l rh.BA44_exvivo.label --l rh.BA45_exvivo.label --l rh.V1_exvivo.label --l rh.V2_exvivo.label --l rh.MT_exvivo.label --l rh.perirhinal_exvivo.label --l rh.entorhinal_exvivo.label --a BA_exvivo --maxstatwinner --noverbose 


 mris_label2annot --s _151 --hemi rh --ctab /Volumes/apps/linux/freesurfer-current/average/colortable_BA.txt --l rh.BA1_exvivo.thresh.label --l rh.BA2_exvivo.thresh.label --l rh.BA3a_exvivo.thresh.label --l rh.BA3b_exvivo.thresh.label --l rh.BA4a_exvivo.thresh.label --l rh.BA4p_exvivo.thresh.label --l rh.BA6_exvivo.thresh.label --l rh.BA44_exvivo.thresh.label --l rh.BA45_exvivo.thresh.label --l rh.V1_exvivo.thresh.label --l rh.V2_exvivo.thresh.label --l rh.MT_exvivo.thresh.label --l rh.perirhinal_exvivo.thresh.label --l rh.entorhinal_exvivo.thresh.label --a BA_exvivo.thresh --maxstatwinner --noverbose 


 mris_anatomical_stats -th3 -mgz -f ../stats/rh.BA_exvivo.stats -b -a ./rh.BA_exvivo.annot -c ./BA_exvivo.ctab _151 rh white 


 mris_anatomical_stats -th3 -mgz -f ../stats/rh.BA_exvivo.thresh.stats -b -a ./rh.BA_exvivo.thresh.annot -c ./BA_exvivo.thresh.ctab _151 rh white 

