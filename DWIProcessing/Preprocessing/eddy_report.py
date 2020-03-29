from pathlib import Path
import shutil

BIDSproc_dir = Path("/Volumes/Vol6/YouthPTSD/BIDS_Processed")
quadout_dir = Path("/Volumes/Users/jdrussell3/quads")

if not quadout_dir.exists():
    quadout_dir.mkdir()

for subjdir in sorted(BIDSproc_dir.glob('sub-*')):
    for sesdir in sorted(subjdir.glob('ses*')):
        for dwidir in sesdir.glob('dwi'):
            quad_dir = dwidir / 'preprocessed' / 'eddy' / 'quad'
            if quad_dir.exists():
                quadpdf = quad_dir / 'qc_updated.pdf'
                quadout = quadout_dir / "_".join([subjdir.name, sesdir.name, 'quad.pdf'])
                shutil.copy(quadpdf, quadout)



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