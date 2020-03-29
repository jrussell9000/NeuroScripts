# YouthPTSD DTI Processing Notebook

## 01.03.20 @ 11:21:41

Here's a helpful script taken from https://github.com/gsudre/lab_notes/blob/master/001-dti_processing_for_PNC_data.md
that parses all the eddy output into a csv file listing the movement parameters (outliers, volumes removed, etc.)

```bash
out_fname=~/tmp/mvmt_report.csv;
echo "id,Noutliers,PROPoutliers,NoutVolumes,norm.trans,norm.rot,RMS1stVol,RMSprevVol" > $out_fname;
for m in `cat ~/tmp/pnc`; do 
    echo 'Collecting metrics for' $m;
    if [ -e ${m}/eddy_s2v_unwarped_images.eddy_outlier_report ]; then
        noutliers=`cat ${m}/eddy_s2v_unwarped_images.eddy_outlier_report | wc -l`;
        # figuring out the percetnage of total slices the outliers represent
        nslices=`tail ${m}/eddy_s2v_unwarped_images.eddy_outlier_map | awk '{ print NF; exit } '`;
        nvol=`cat ${m}/dwi_cvec.dat | wc -l`;
        let totalSlices=$nslices*$nvol;
        pctOutliers=`echo "scale=4; $noutliers / $totalSlices" | bc`;
        # figuring out how many volumes were completely removed (row of 1s)
        awk '{sum=0; for(i=1; i<=NF; i++){sum+=$i}; sum/=NF; print sum}' \
            ${m}/eddy_s2v_unwarped_images.eddy_outlier_map > outlier_avg.txt;
        nOutVols=`grep -c -e "^1$" outlier_avg.txt`;
        1d_tool.py -infile ${m}/eddy_s2v_unwarped_images.eddy_movement_over_time \
            -select_cols '0..2' -collapse_cols euclidean_norm -overwrite \
            -write trans_norm.1D;
        trans=`1d_tool.py -infile trans_norm.1D -show_mmms | \
            tail -n -1 | awk '{ print $8 }' | sed 's/,//'`;
        1d_tool.py -infile ${m}/eddy_s2v_unwarped_images.eddy_movement_over_time \
            -select_cols '3..5' -collapse_cols euclidean_norm -overwrite \
            -write rot_norm.1D;
        rot=`1d_tool.py -infile rot_norm.1D -show_mmms | \
            tail -n -1 | awk '{ print $8 }' | sed 's/,//'`;
        1d_tool.py -infile ${m}/eddy_s2v_unwarped_images.eddy_movement_rms \
            -show_mmms > mean_rms.txt;
        vol1=`head -n +2 mean_rms.txt | awk '{ print $8 }' | sed 's/,//'`;
        pvol=`tail -n -1 mean_rms.txt | awk '{ print $8 }' | sed 's/,//'`;
    else
        echo "Could not find outlier report for $m"
        noutliers='NA';
        pctOutliers='NA';
        nOutVols='NA';
        trans='NA';
        rot='NA';
        vol1='NA';
        pvol='NA';
    fi;
    echo $m, $noutliers, $pctOutliers, $nOutVols, $trans, $rot, $vol1, $pvol >> $out_fname;
done
```

## 01.03.20 @ 11:21:37

The script below should gather all the tract values (FA, MD, RD, AD) and enter them into a CSV file by subject

```bash
mydir=/lscratch/${SLURM_JOBID}/
weighted_tracts=~/tmp/pnc_weighted_tracts.csv;
row="id";
for t in `cut -d" " -f 1 /data/NCR_SBRB/software/autoPtx/structureList`; do
    for m in fa ad rd; do
        row=${row}','${t}_${m};
    done
done
echo $row > $weighted_tracts;
for m in `cat /data/NCR_SBRB/pnc/dti_fdt/converted.txt`; do
    echo $m;
    row="${m}";
    cd /data/NCR_SBRB/pnc/dti_fdt/preproc/$m &&
    for t in `cut -d" " -f 1 /data/NCR_SBRB/software/autoPtx/structureList`; do
        if [ -e ../../tracts/${m}/${t}/tracts/tractsNorm.nii.gz ]; then
            # tract mask is higher dimension!
            3dresample -master dti_FA.nii.gz -prefix ${mydir}/mask.nii \
                -inset ../../tracts/${m}/${t}/tracts/tractsNorm.nii.gz \
                -rmode NN -overwrite &&
            nvox=`3dBrickStat -count -non-zero ${mydir}/mask.nii 2>/dev/null` &&
            if [ $nvox -gt 0 ]; then
                if [ -e dti_FA.nii.gz ]; then
                    fa=`3dmaskave -q -mask ${mydir}/mask.nii dti_FA.nii.gz 2>/dev/null`;
                else
                    fa='NA';
                fi;
                # had to increment lines piecewise because of some racing condition
                row=${row}','${fa};
                if [ -e dti_L1.nii.gz ]; then
                    ad=`3dmaskave -q -mask ${mydir}/mask.nii dti_L1.nii.gz 2>/dev/null`;
                else
                    ad='NA'
                fi;
                row=${row}','${ad};
                if [ -e dti_L2.nii.gz ] && [ -e dti_L3.nii.gz ]; then
                    3dcalc -a dti_L2.nii.gz -b dti_L3.nii.gz -expr "(a + b) / 2" \
                        -prefix ${mydir}/RD.nii -overwrite 2>/dev/null &&
                    rd=`3dmaskave -q -mask ${mydir}/mask.nii ${mydir}/RD.nii 2>/dev/null`;
                else
                    rd='NA';
                fi;
                row=${row}','${rd};
            else
                echo "No nonzero voxels in mask for $t" &&
                row=${row}',NA,NA,NA';
            fi;
        else
            echo "No tractsNorm for $t" &&
            row=${row}',NA,NA,NA';
        fi;
    done
    echo $row >> $weighted_tracts;
done
```