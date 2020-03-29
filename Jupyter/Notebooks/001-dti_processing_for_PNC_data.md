# 2019-01-15 12:12:36

I'm following the directions from
https://fsl.fmrib.ox.ac.uk/fslcourse/lectures/practicals/fdt1/index.html to run
the DTI pipeline on the PNC data we just downloaded.

It doesn't seem like FSL can deal with DICOMs, so the first step is to convert
them to NIFTI. I used Paul's tool to do it, and based on his e-mail I just need:

```bash
fat_proc_convert_dcm_dwis  \
        -indir  "DTI_35dir/* DTI_36dir/*"                 \
        -prefix  OFILE
```

For each subject. That generates 71 bvals, 71 vecs, and a .nii.gz with 71 bricks
(each 128 x 128 x 70). Now, we can go on with either the FATCAT or the FSL
pipeline, knowing that there is no need for DRBUDDI.

# 2019-01-18 10:44:08

Following Paul's recommendations by e-mail, let's run one subject all the way.
And by that, I mean including TORTOISE, but assuming that no volumes are bad so
I don't have to do the visual QC.

```bash
cd /data/NCR_SBRB/pnc/dti
tar -zxvf ../600009963128_1.tar.gz
module load afni
Dimon -infile_prefix "600009963128/T1_3DAXIAL/Dicoms/*.dcm" -gert_to3d_prefix 600009963128_t1.nii.gz -gert_create_dataset
fat_proc_convert_dcm_dwis -indir  "600009963128/DTI_35dir/* 600009963128/DTI_36dir/*" -prefix 600009963128_dwi
rm -rf 600009963128
@SSwarper -input 600009963128_t1.nii.gz -base TT_N27_SSW.nii.gz -subid 600009963128
fat_proc_imit2w_from_t1w -inset 600009963128_t1_ax.nii.gz -prefix 600009963128_t2_ax_immi -mask anatSS.600009963128.nii
# I got the phase information after using ImportDICOM tool from TORTOISE and checking the .list file
DIFFPREP --dwi 600009963128_dwi.nii --bvecs 600009963128_dwi_rvec.dat --bvals 600009963128_dwi_bval.dat --structural 600009963128_t2_ax_immi.nii --phase vertical
@GradFlipTest -in_dwi 600009963128_dwi_DMC.nii -in_col_matT 600009963128_dwi_DMC.bmtxt -prefix 600009963128_GradFlipTest_rec.txt
my_flip=`cat 600009963128_GradFlipTest_rec.txt`;
fat_proc_dwi_to_dt \
    -in_dwi       600009963128_dwi_DMC.nii                    \
    -in_col_matT  600009963128_dwi_DMC.bmtxt                  \
    -in_struc_res 600009963128_dwi_DMC_structural.nii               \
    -in_ref_orig  600009963128_dwi_DMC_template.nii          \
    -prefix       600009963128_dwi                           \
    -mask_from_struc                                   \
    $my_flip
fat_proc_decmap                                     \
    -in_fa       dt_FA.nii.gz     \
    -in_v1       dt_V1.nii.gz     \
    -mask        600009963128_dwi_mask.nii.gz  \
    -prefix      DEC
```

Note that we'll need to stop in the middle to allow for the IRTAs to do the
visual QC. So, let's create a wrapper script that does some of the steps above:

```bash
cd /data/NCR_SBRB/pnc
for m in `cat have_imaging.txt`; do
    echo "bash ~/research_code/dti/tortoise_pnc_wrapper.sh ${m}" >> swarm.tortoise;
done;
swarm -g 10 -t 16 --job-name tortoise --time 4:00:00 -f swarm.tortoise \
    -m afni,TORTOISE --partition quick --logdir trash
```

# 2019-01-29 10:38:23

I was chatting with Ryan, and apparently their approach for GenR is to process
all volumes all the time. Then, use quantitative variables to figure out which
subjects to remove. We can try that approach here, especially considering that
we will likely run DTIPrep to get some additional QC metrics, and we rarely ever
use the subjects when we remove more than a couple volumes anyways.

So, let's run the first 100 subjects in the new TORTOISE pipeline, then we can do
the same for the FSL pipeline once I have that working.

```bash
cd /data/NCR_SBRB/pnc
for m in `cat first100.txt`; do
    echo "bash ~/research_code/dti/tortoise_pnc_wrapper.sh ${m}" >> swarm.tortoise;
done;
swarm -g 10 -t 16 --job-name tortoise --time 4:00:00 -f swarm.tortoise \
    -m afni,TORTOISE --partition quick --logdir trash
```

For the FSL pipeline, we can do something like this:

```bash
fslroi dwi b0 0 1
bet b0 b0_brain -m -f 0.2
idx=''; for i in {1..71}; do a=$a' '1; done; echo $a > index.txt
echo "0 -1 0 0.102" > acqparams.txt
eddy_openmp --imain=dwi --mask=b0_brain_mask --index=index.txt --acqp=acqparams.txt --bvecs=dwi_cvec.dat --bvals=dwi_bval.dat --fwhm=0 --flm=quadratic --out=eddy_unwarped_images --cnr_maps --repol --mporder=6

# OR

sinteractive --gres=gpu:k20x:1
module load CUDA/7.5
eddy_cuda --imain=dwi --acqp=acqparams.txt --index=index.txt --mask=b0_brain_mask --bvals=dwi_bval.dat --bvecs=dwi_cvec.dat --out=eddy_s2v_unwarped_images --niter=8 --fwhm=10,6,4,2,0,0,0,0 --repol --ol_type=both --mporder=8 --s2v_niter=8 --slspec=my_slspec.txt --cnr_maps

dtifit --data=eddy_s2v_unwarped_images --mask=b0_brain_mask --bvals=dwi_bval.dat --bvecs=dwi_cvec.dat --sse --out=dti

```

I got the parameters for acquisition from running dcm2niix_afni on both DTI
sequences (35 and 35), and then looking for Phase, PE, and Echo in the jsons. In
the end, they matched the example in
https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/eddy/Faq#How_do_I_know_what_to_put_into_my_--acqp_file.

I also used the json to construct the myslspec.txt file, using the Matlab code
from
https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/eddy/Faq#How_should_my_--slspec_file_look.3F

So, I put all of that in a script, which I ran like this:

```bash
cd /data/NCR_SBRB/pnc
for m in `cat first100.txt`; do
    echo "bash ~/research_code/dti/fdt_pnc_wrapper.sh ${m}" >> swarm.fdt;
done;
swarm -g 4 --job-name fdt --time 4:00:00 -f swarm.fdt --partition gpu \
    --logdir trash_fdt --gres=gpu:k80:2
```

# 2019-02-12 17:38:14

I made a few changes to the fdt wrapper to include Qc pictures and warping to
the FMRIB58 space. The results look decent, so it's time to run it for everybody
and start looking at the QC pictures. I'll then write wrappers to grab the
motion and outlier parameters, as well as something to collect the tract
averages, brain QC images (to be more organized for easy QCing), do the rest of the TBSS analysis, and also output the SSE and CNR maps
for further QCing.

Let's go ahead and all 647 overnight.

# 2019-02-13 11:31:26

I'll ignore the CNR maps for now. We have plenty here after chaking the brain
masks, warping, and SSE. We're also looking for numbers of outliers and movement
variables, so let's grab those.

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

Note that Ryan's output usually comes from bedpostX, so I'll still need to run
that. Or I can just go for a regular average over the mask mean. For example,
see Ryan's e-mail from December 06, 2016 10:11 AM.

I'm not going to go the CAMINO way, but we might end up running autoPtx. Need to
see how it looks at Biowulf though:

https://hpc.nih.gov/apps/fsl.html

Ryan's pipeline seems to spit out both OLS and RESTORE estimates, and he says
they're highly correlated. Just so we don't have to jump between programs, let's
stic to the OLS etimates for now.

For bedpostx, I did something like this:

```bash
ln -s eddy_s2v_unwarped_images.nii.gz data.nii.gz
ln -s dwi_bval.dat bvals
ln -s eddy_s2v_unwarped_images.eddy_rotated_bvecs bvecs
ln -s b0_brain_mask.nii.gz nodif_brain_mask.nii.gz
bedpostx ./
```

and that schedules a whole bunch of swarms just for the single subject. Over 60,
I'd say, wach of 2 cores, 2h. Shouldn't take too long to run in parallel, but
that's per subject, so it'll take a while. It can run faster if I use GPU, but
then I'm limited on how many GPUs I can allocate. Let's think more about it
later. But the command would be bedpostx_gpu.

Also note that from Joelle's e-mails, we should only do one fiber orientation for our data,
instead of 2 that is default in bedpost.

Before I go nuts running bedpost on everyone, let's collect the QC that's
already finished:

```bash
mkdir /data/NCR_SBRB/pnc/dti_fdt/summary_QC
cd /data/NCR_SBRB/pnc/dti_fdt/summary_QC/
mkdir brainmask
mkdir transform
mkdir DEC
mkdir SSE
for m in `cat ../myids.txt`; do
    cp ../${m}/QC/brain_mask.axi.png brainmask/${m}.axi.png
    cp ../${m}/QC/brain_mask.sag.png brainmask/${m}.sag.png
    cp ../${m}/QC/brain_mask.cor.png brainmask/${m}.cor.png

    cp ../${m}/QC/FA_transform.axi.png transform/${m}.axi.png
    cp ../${m}/QC/FA_transform.sag.png transform/${m}.sag.png
    cp ../${m}/QC/FA_transform.cor.png transform/${m}.cor.png

    cp ../${m}/QC/DEC_qc_dec_sca07.axi.png DEC/${m}.axi.png
    cp ../${m}/QC/DEC_qc_dec_sca07.sag.png DEC/${m}.sag.png
    cp ../${m}/QC/DEC_qc_dec_sca07.cor.png DEC/${m}.cor.png

    cp ../${m}/QC/sse.axi.png SSE/${m}.axi.png
    cp ../${m}/QC/sse.cor.png SSE/${m}.cor.png
    cp ../${m}/QC/sse.sag.png SSE/${m}.sag.png
done
```

To fill in the QC spreadsheet, we check who converted properly:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
for m in `cat ../have_imaging.txt`; do
    nvol=`cat ${m}/dwi_cvec.dat | wc -l`;
    if [ ! $nvol = 71 ]; then
        echo $m,$nvol >> ~/tmp/conversion_errors.txt;
    fi;
done
```

Then, check that all brain masks were created:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
for m in `cat converted.txt`; do
    if [[ -e ${m}/QC/brain_mask.axi.png && -e ${m}/b0_brain_mask.nii.gz ]]; then
        echo $m,y >> ~/tmp/mask_status.txt;
    else
        echo $m,n >> ~/tmp/mask_status.txt;
    fi;
done
```

And then who has eddy:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
for m in `cat converted.txt`; do
    if [[ -e ${m}/eddy_s2v_unwarped_images.eddy_rotated_bvecs && -e ${m}/eddy_s2v_unwarped_images.nii.gz ]]; then
        echo $m,y >> ~/tmp/eddy_status.txt;
    else
        echo $m,n >> ~/tmp/eddy_status.txt;
    fi;
done
```

To run bedpostx, I'll split the data into 6, so that each account can run a GPU
to its limit and then a CPU one. Things might go faster that way.

```bash
for m in `cat xaf`; do
    cd /data/NCR_SBRB/pnc/dti_fdt/${m};
    ln -s eddy_s2v_unwarped_images.nii.gz data.nii.gz;
    ln -s dwi_bval.dat bvals;
    ln -s eddy_s2v_unwarped_images.eddy_rotated_bvecs bvecs;
    ln -s b0_brain_mask.nii.gz nodif_brain_mask.nii.gz;
    bedpostx_gpu -n 1 ./;
done
```

Run autoPtx first to make sure everything is fine!!!!

I had to make some changes to how I'm approaching this. That's just because
running autoPtx makes life much easier, but it redoes some of the steps I was
doing in the wrapper before. So, let's stop the wrapper right before we
calculate dtifit (which is done by autoPtx), and we can generate the QC pictures
afterwards. 

autoPtx expects the data in the same format as what we'd send for bedpostx, so
let's do that formatting first. But keep in mind that symlinks don't work, and
the data is in the end moved to preproc. So, let's actually copy them, because I
don't want to risk losing the eddy output:

```bash
# run in helix so we don't overload BW filesystem
for m in `cat xac`; do
    echo Copying $m;
    cd /data/NCR_SBRB/pnc/dti_fdt/${m};
    cp eddy_s2v_unwarped_images.nii.gz data.nii.gz;
    cp dwi_bval.dat bvals;
    cp eddy_s2v_unwarped_images.eddy_rotated_bvecs bvecs;
    cp b0_brain_mask.nii.gz nodif_brain_mask.nii.gz;
done
```

Then, we run autoPtx. We can split it by users because it adds everything to the
same directory, and just increments the final subject list.

Run it a long interactive session, because even though it schedules bedpostx, it
still runs all kinds of registrations through FSL, so biowulf headnode won't cut
it!

```bash
data='';
for m in `cat xaf`; do
    data=$data' '${m}/data.nii.gz;
done
/data/NCR_SBRB/software/autoPtx/autoPtx_1_preproc $data;
```

And of course we still need part 2 when we're done.

# 2019-02-20 10:58:43

I changed the part 2 script so run the scans split between two accounts.
Hopefully there won't be issues with permissions...

But I had to reduce the number of subjects per file because we CPU recruitment
limits in the cluster. Let's try only 100. And still, better to only fire new
ones when nothing else is queued (running is OK).


It creates one swarm per tract, with one job per subject in each tract. So,
nsubjects * ntracts. I might need to use the subject file as an argument to
split it across accounts.

But I don't need to wait for the second part to do:

```bash
for m in `cat ../xab`; do
    bash ~/research_code/dti/fdt_pnc_TBSS_and_QC.sh ${m};
done
```

Now we need to copy the QC images again:

```bash
qc_dir=/data/NCR_SBRB/pnc/dti_fdt/summary_QC/
img_dir=/data/NCR_SBRB/pnc/dti_fdt/preproc/
for m in `cat ~/tmp/pnc_qc.txt`; do
    cp $img_dir/${m}/QC/FA_transform.axi.png $qc_dir/transform/${m}.axi.png
    cp $img_dir/${m}/QC/FA_transform.sag.png $qc_dir/transform/${m}.sag.png
    cp $img_dir/${m}/QC/FA_transform.cor.png $qc_dir/transform/${m}.cor.png

    cp $img_dir/${m}/QC/DEC_qc_dec_sca07.axi.png $qc_dir/DEC/${m}.axi.png
    cp $img_dir/${m}/QC/DEC_qc_dec_sca07.sag.png $qc_dir/DEC/${m}.sag.png
    cp $img_dir/${m}/QC/DEC_qc_dec_sca07.cor.png $qc_dir/DEC/${m}.cor.png

    cp $img_dir/${m}/QC/sse.axi.png $qc_dir/SSE/${m}.axi.png
    cp $img_dir/${m}/QC/sse.cor.png $qc_dir/SSE/${m}.cor.png
    cp $img_dir/${m}/QC/sse.sag.png $qc_dir/SSE/${m}.sag.png
done
```

# 2019-02-22 10:07:06

While the IRTAs QC the resulting images, I'll go ahead and start copying data to
shaw/PNC_DTI. I'm using Globus web interface, because I'll go for all
directories for now. This is justa  way to keep the results in our servers in
case I need to make room in BW.

# 2019-03-01 15:55:07

Let's also do some quick verification of the quality of the mean FA metric... do
we see the Bi-gaussian distribution that was a problem in the past with the NCR
data? In the end, we'll use the TBSS pipeline, but it depends on a good
transformation to the template space. Since this is a quick check, we don't want
to depend on that, so let's derive per subject masks, and then we can just
calculate the mean FA based on that mask. It's quite similar to what we use in
the master QC sheet:

```bash
mydir=/lscratch/${SLURM_JOBID}/
mean_props=~/tmp/mean_props.csv;
echo "id,mean_fa,mean_ad,mean_rd,nvox" > $mean_props;
for m in `cat ~/tmp/pnc`; do
    echo $m;
    cd /data/NCR_SBRB/pnc/dti_fdt/preproc/$m &&
    if [ -e dti_FA.nii.gz ]; then
        3dcalc -a dti_FA.nii.gz -expr "step(a-.2)" -prefix ${mydir}/my_mask.nii 2>/dev/null &&
        fa=`3dmaskave -q -mask ${mydir}/my_mask.nii dti_FA.nii.gz 2>/dev/null` &&
        ad=`3dmaskave -q -mask ${mydir}/my_mask.nii dti_L1.nii.gz 2>/dev/null` &&
        3dcalc -a dti_L2.nii.gz -b dti_L3.nii.gz -expr "(a + b) / 2" \
            -prefix ${mydir}/RD.nii 2>/dev/null &&
        rd=`3dmaskave -q -mask ${mydir}/my_mask.nii ${mydir}/RD.nii 2>/dev/null` &&
        nvox=`3dBrickStat -count -non-zero ${mydir}/my_mask.nii 2>/dev/null` &&
        echo ${m},${fa},${ad},${rd},${nvox} >> $mean_props;
        rm ${mydir}/*nii;
    else
        echo ${m},NA,NA,NA,NA >> $mean_props;
    fi
done
```

![](images/2019-03-01-18-08-08.png)

So, let's go ahead and calculate the movement variables again, for these 564 IDs
we're waiting for visual QC (see above).

# 2019-03-05 15:42:44

Based on what I'm reading about autoPtx, probtrackx, and also reading the
trackSubjectStruct script from autoPtx, our main result is tractsNorm, which
combines forward and inverse (when needed), and then normalizes by waypoints.
The maximum there is also 1, which I'd think it's a good way to scale the
different voxels. 

The QC pictures only make use of autoPtx1 output, so let's make sure all
autoPtx2 ran for everyone:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt/tracts
for s in `cat ~/tmp/pnc`; do
    if [ ! -e ${s}/fmi/tracts/tractsNorm.nii.gz ]; then
        echo $s >> ../preproc/missing;
    fi;
done
# edit the script first
/data/NCR_SBRB/software/autoPtx/autoPtx_2_launchTractography
```

Then, it should just be a matter of weighting the property maps by tractNorm:

```bash
mydir=/lscratch/${SLURM_JOBID}/
weighted_tracts=~/tmp/weighted_tracts.csv;
row="id";
for t in `cut -d" " -f 1 /data/NCR_SBRB/software/autoPtx/structureList`; do
    for m in fa ad rd; do
        row=${row}','${t}_${m};
    done
done
echo $row > $weighted_tracts;
for m in `head -n 3 ~/tmp/pnc`; do
    echo $m;
    row="${m}";
    cd /data/NCR_SBRB/pnc/dti_fdt/preproc/$m &&
    for t in `cut -d" " -f 1 /data/NCR_SBRB/software/autoPtx/structureList`; do
        if [ -e ../../tracts/${m}/${t}/tracts/tractsNorm.nii.gz ]; then
            # tract mask is higher dimension!
            3dresample -master dti_FA.nii.gz -prefix ${mydir}/mask.nii \
                -inset ../../tracts/${m}/${t}/tracts/tractsNorm.nii.gz \
                -rmode NN -overwrite &&
            fa=`3dmaskave -q -mask ${mydir}/mask.nii dti_FA.nii.gz` &&
            ad=`3dmaskave -q -mask ${mydir}/mask.nii dti_L1.nii.gz` &&
            3dcalc -a dti_L2.nii.gz -b dti_L3.nii.gz -expr "(a + b) / 2" \
                -prefix ${mydir}/RD.nii 2>/dev/null &&
            rd=`3dmaskave -q -mask ${mydir}/mask.nii ${mydir}/RD.nii` &&
            row=${row}','${fa}','${ad}','${rd};
            rm ${mydir}/*nii;
        else
            row=${row}',NA,NA,NA';
        fi;
    done
    echo $row >> $weighted_tracts;
done
```

# 2019-03-07 11:49:18

And finally merge everything:

```r
> a = read.csv('PNC_weighted_tracts.csv')
> dim(a)
[1] 564  82
> b = read.csv('../FDT_QC/PNC/mvmt_report.csv')
> m = merge(a,b,by='id')
> dim(m)
[1] 564  89
> d = read.csv('../FDT_QC/PNC/mean_props.csv')
> m = merge(m,d,by='id')
> dim(m)
[1] 564  93
> library(gdata)
> yn = read.xls('../FDT_QC/PNC_DTI_QC_FEB.28.xlsx')
> m = merge(m,yn,by.x='id',by.y='PNC_ID')
> dim(m)
[1] 564 100
> write.csv(m, file='PNC_WNH_tracts_with_QC.csv', row.names=F)
```

But there were LOTS of NAs for some tracts... weird. Let me see what's going on.
So, the issue is that many tracts have norm 0! Not sure what's going on there...
let's see if we can quantify it.

```bash
maxvox=~/tmp/maxvox.csv;
row="id";
for t in `cut -d" " -f 1 /data/NCR_SBRB/software/autoPtx/structureList`; do
        row=${row}','${t};
done
echo $row > $maxvox;
for m in `cat ~/tmp/pnc`; do
    echo ${m}
    cd /data/NCR_SBRB/pnc/dti_fdt
    row="${m}";
    for d in `cut -d" " -f 1 /data/NCR_SBRB/software/autoPtx/structureList`; do
        if [ -e tracts/${m}/${d}/tracts/tractsNorm.nii.gz ]; then
            val=`3dBrickStat -slow tracts/${m}/${d}/tracts/tractsNorm.nii.gz`;
        else
            val='NA'
        fi
        row=${row}','${val}
    done
    echo $row >> $maxvox;
done
```

So, the code above gives us the top normative number in each mask. As we can
see, there are many masks that have a norm of zero, which is quite weird.
Basically, we were never able to determine the voxels that belong to the those
tracts in the scan? Looks weird to me...

It also doesn't look like it was just autoPtx sunning out of time... yeah, I
checked some of the output from above and I find it hard to believe that CST_L
was only found in 2 out of the 565 scans... what's going on?

# 2019-03-08 18:45:04

Still not sure of what's going on... it's not a permissions issue (I did one of
the new subjects all under my account), it's not my scripts screwing it up (I
ran FDT and autoPtx by themselves), and it's not the bedpostx model either (I
tried n = 1 and model 2). I still get cgc, cst as 0... maybe there's something
wrong with the transform? Or maybe the coverage of those areas?

I could also try running the averaging script for well-know tracts to to check
for sanity.

# 2019-03-14 15:46:11

```bash
mydir=/lscratch/${SLURM_JOBID}/
weighted_tracts=pnc_weighted_tracts.csv;
# copying everything locally first to avoid racing conditions
cd $mydir
cp /data/NCR_SBRB/software/autoPtx/structureList .
row="id";
for t in `cut -d" " -f 1 structureList`; do
    for m in fa ad rd; do
        row=${row}','${t}_${m};
    done
done
echo $row > $weighted_tracts;
for m in `head -n 4 /data/NCR_SBRB/pnc/dti_fdt/converted.txt`; do
    echo ${m}
    rm -rf preproc tracts
    mkdir preproc tracts
    cp /data/NCR_SBRB/pnc/dti_fdt/preproc/${m}/dti_??.nii.gz preproc/
    cp -r /data/NCR_SBRB/pnc/dti_fdt/tracts/${m}/* tracts/
    row="${m}";
    for t in `cut -d" " -f 1 structureList`; do
        if [ -e tracts/${t}/tracts/tractsNorm.nii.gz ]; then
            # tract mask is higher dimension!
            3dresample -master preproc/dti_FA.nii.gz -prefix ./mask.nii \
                -inset tracts/${t}/tracts/tractsNorm.nii.gz \
                -rmode NN -overwrite &&
            avg=`3dmaskave -quiet mask.nii 2>/dev/null` &&
            if [ $avg != 0 ]; then
                fa=`3dmaskave -q -mask ./mask.nii preproc/dti_FA.nii.gz` &&
                ad=`3dmaskave -q -mask ./mask.nii preproc/dti_L1.nii.gz` &&
                3dcalc -a preproc/dti_L2.nii.gz -b preproc/dti_L3.nii.gz \
                    -expr "(a + b) / 2" -prefix ./RD.nii &&
                rd=`3dmaskave -q -mask ./mask.nii ./RD.nii` &&
                row=${row}','${fa}','${ad}','${rd};
            else
                # found nothing in the mask!
                row=${row}',NA,NA,NA';
            fi
            rm ${mydir}/*nii;
        else
            row=${row}',NA,NA,NA';
        fi;
    done
    echo $row >> $weighted_tracts;
done
```

The other tracts look reasonable, but I'm not getting anything for CST, which is
quite weird. Let see if we can visualize the transform again...

# 2019-03-25 16:20:56

I sent an e-mail to the FSL list but nothing. Ryan gave a good idea to check for
Y flips, and that's what I'm doing. I ran the FATCAT tool and it actually
suggested a Y flip.

https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/FATCAT/GradFlipTest.html

It does so by trying all possible flips, and reporting the one that yields the
most tracts overall (by a lot, like 2 or 3 times the others).

```bash
@GradFlipTest -in_dwi eddy_s2v_unwarped_images.nii.gz -in_row_vec eddy_s2v_unwarped_images.eddy_rotated_bvecs -in_bvals dwi_bval.dat
1dDW_Grad_o_Mat++ -in_row_vec eddy_s2v_unwarped_images.eddy_rotated_bvecs -out_row_vec bvecs `cat GradFlipTest_rec.txt`
```

So, I'm actually running a test of doing the flip before and after eddy. When I
did it before eddy, the eddy result didn't look like it needed the flip, which
is encouraging. I'm now running bedpostX in both test cases, and seeing if it
makes a difference. Ideally, I'll get the same result in both, and I'll only
need to flip the results of eddy, and redo bedpostX for everything. It could
also happen that I'll need to re-run eddy for everything. Worst case scenario is
that neither one makes a difference, in which case I'm back to waiting for an
answer from FSL folks.

# 2019-03-26 08:26:05

Well, still not working. Let's try to repeat all steps slowly, including isomorphic sampling and grad flip, as a last resort...

```bash
s=605235766122;
cd ~/data/tmp
mkdir ${s}
cd ${s}
tar -zxf /data/NCR_SBRB/pnc/${s}_1.tar.gz
module load CUDA/7.5
module load fsl
module load afni

fat_proc_convert_dcm_dwis \
    -indir  "${s}/DTI_35dir/* ${s}/DTI_36dir/*" \
    -prefix dwi -no_qc_view
rm -rf ${s}

# flipping vectors and isomorphic sampling right away
3dresample -dxyz 1.875 1.875 1.875 -prefix dwi.nii.gz \
    -input dwi.nii.gz -overwrite
@GradFlipTest -in_dwi dwi.nii.gz \
    -in_row_vec dwi_rvec.dat -in_bvals dwi_bval.dat
1dDW_Grad_o_Mat++ -in_row_vec dwi_rvec.dat \
    -out_row_vec bvecs `cat GradFlipTest_rec.txt`

# FSL takes bvecs in the 3 x volumes format
fslroi dwi b0 0 1
bet b0 b0_brain -m -f 0.2
idx=''; for i in {1..71}; do 
    a=$a' '1;
done;
echo $a > index.txt
echo "0 -1 0 0.102" > acqparams.txt

cp /data/NCR_SBRB/pnc/dti_fdt/my_slspec.txt ./
eddy_cuda --imain=dwi --acqp=acqparams.txt --index=index.txt \
    --mask=b0_brain_mask --bvals=dwi_bval.dat --bvecs=bvecs \
    --out=eddy_s2v_unwarped_images --repol

cp eddy_s2v_unwarped_images.nii.gz data.nii.gz;
cp dwi_bval.dat bvals;
cp bvecs old_bvecs
cp eddy_s2v_unwarped_images.eddy_rotated_bvecs bvecs;
cp b0_brain_mask.nii.gz nodif_brain_mask.nii.gz;

cd ../
/data/NCR_SBRB/software/autoPtx/autoPtx_1_preproc ${s}/data.nii.gz
/data/NCR_SBRB/software/autoPtx/autoPtx_2_launchTractography
```

Still, no luck... what if we erode the mask?

```bash
s=605235766122;
cd ~/data/tmp
mkdir ${s}
cd ${s}
tar -zxf /data/NCR_SBRB/pnc/${s}_1.tar.gz
module load CUDA/7.5
module load fsl
module load afni

fat_proc_convert_dcm_dwis \
    -indir  "${s}/DTI_35dir/* ${s}/DTI_36dir/*" \
    -prefix dwi -no_qc_view
rm -rf ${s}

# flipping vectors and isomorphic sampling right away
3dresample -dxyz 1.875 1.875 1.875 -prefix dwi.nii.gz \
    -input dwi.nii.gz -overwrite
@GradFlipTest -in_dwi dwi.nii.gz \
    -in_row_vec dwi_rvec.dat -in_bvals dwi_bval.dat
1dDW_Grad_o_Mat++ -in_row_vec dwi_rvec.dat \
    -out_row_vec bvecs `cat GradFlipTest_rec.txt`

# FSL takes bvecs in the 3 x volumes format
fslroi dwi b0 0 1
bet b0 b0_brain -m -f 0.2

#eroding
f=b0_brain_mask
X=`${FSLDIR}/bin/fslval $f dim1`; X=`echo "$X 2 - p" | dc -`
Y=`${FSLDIR}/bin/fslval $f dim2`; Y=`echo "$Y 2 - p" | dc -`
Z=`${FSLDIR}/bin/fslval $f dim3`; Z=`echo "$Z 2 - p" | dc -`
$FSLDIR/bin/fslmaths $f -min 1 -ero -roi 1 $X 1 $Y 1 $Z 0 1 ${f}_eroded

idx=''; for i in {1..71}; do
    a=$a' '1;
done;
echo $a > index.txt
echo "0 -1 0 0.102" > acqparams.txt

cp /data/NCR_SBRB/pnc/dti_fdt/my_slspec.txt ./
eddy_cuda --imain=dwi --acqp=acqparams.txt --index=index.txt \
    --mask=b0_brain_mask_eroded --bvals=dwi_bval.dat --bvecs=bvecs \
    --out=eddy_s2v_unwarped_images --repol

cp eddy_s2v_unwarped_images.nii.gz data.nii.gz;
cp dwi_bval.dat bvals;
cp bvecs old_bvecs
cp eddy_s2v_unwarped_images.eddy_rotated_bvecs bvecs;
cp b0_brain_mask_eroded.nii.gz nodif_brain_mask.nii.gz;

cd ../
/data/NCR_SBRB/software/autoPtx/autoPtx_1_preproc ${s}/data.nii.gz
/data/NCR_SBRB/software/autoPtx/autoPtx_2_launchTractography
```


```bash
fslreorient2std dwi dwi_reorient
#just checking directions
$FSLDIR/bin/dtifit --sse -k dwi -o dti -m b0_brain_mask_eroded \
    -r dwi_rvec.dat -b dwi_bval.dat
```

I thin just doing the standard flip should do it? Not even eroding the mask, because the mask for the sample data subject doesn't look that clean either. Let's see:

```bash
s=605235766122;
cd ~/data/tmp
mkdir ${s}
cd ${s}
tar -zxf /data/NCR_SBRB/pnc/${s}_1.tar.gz
module load CUDA/7.5
module load fsl
module load afni

fat_proc_convert_dcm_dwis \
    -indir  "${s}/DTI_35dir/* ${s}/DTI_36dir/*" \
    -prefix dwi -no_qc_view
rm -rf ${s}
fslreorient2std dwi dwi_reorient
immv dwi_reorient dwi

# FSL takes bvecs in the 3 x volumes format
fslroi dwi b0 0 1
bet b0 b0_brain -m -f 0.2

idx=''; for i in {1..71}; do
    a=$a' '1;
done;
echo $a > index.txt
echo "0 -1 0 0.102" > acqparams.txt

cp /data/NCR_SBRB/pnc/dti_fdt/my_slspec.txt ./
# eddy_cuda --imain=dwi --acqp=acqparams.txt --index=index.txt \
#     --mask=b0_brain_mask --bvals=dwi_bval.dat --bvecs=dwi_rvec.dat \
#     --out=eddy_s2v_unwarped_images --repol

eddy_cuda --imain=dwi --acqp=acqparams.txt --index=index.txt \
    --mask=b0_brain_mask --bvals=dwi_bval.dat --bvecs=dwi_rvec.dat \
    --out=eddy_s2v_unwarped_images --niter=8 --fwhm=10,6,4,2,0,0,0,0 \
    --repol --ol_type=both --mporder=8 --s2v_niter=8 \
    --slspec=my_slspec.txt --cnr_maps

cp eddy_s2v_unwarped_images.nii.gz data.nii.gz;
cp dwi_bval.dat bvals;
cp eddy_s2v_unwarped_images.eddy_rotated_bvecs bvecs;
cp b0_brain_mask.nii.gz nodif_brain_mask.nii.gz;

cd ../
/data/NCR_SBRB/software/autoPtx/autoPtx_1_preproc ${s}/data.nii.gz

### later

/data/NCR_SBRB/software/autoPtx/autoPtx_2_launchTractography
```

# 2019-03-27 11:10:15

OK, so this is working! So, the main thing was the fslreorient2std bit. So,
let's implement that in the script and run everybody!

# 2019-03-29 16:45:38

Since we have new data that is working now, let's regenerate the QC images. The brainmask is the only one that we actually run before eddy. Because I already ran eddy, let's do it manually here:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
for m in `cat converted.txt`; do
    cd /data/NCR_SBRB/pnc/dti_fdt/${m}
    mkdir QC
    @chauffeur_afni                             \
        -ulay  dwi.nii.gz[0]                         \
        -olay  b0_brain_mask.nii.gz                        \
        -opacity 4                              \
        -prefix   QC/brain_mask              \
        -montx 6 -monty 6                       \
        -set_xhairs OFF                         \
        -label_mode 1 -label_size 3             \
        -do_clean
done
```

Then, the other processing/QC images:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
for m in `cat converted.txt`; do
    bash ~/research_code/dti/fdt_TBSS_and_QC.sh /data/NCR_SBRB/pnc/dti_fdt/preproc/${m};
done
```

# 2019-03-31 11:43:32

And we finish by gathering the tract values:

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
                fa=`3dmaskave -q -mask ${mydir}/mask.nii dti_FA.nii.gz 2>/dev/null` &&
                ad=`3dmaskave -q -mask ${mydir}/mask.nii dti_L1.nii.gz 2>/dev/null` &&
                3dcalc -a dti_L2.nii.gz -b dti_L3.nii.gz -expr "(a + b) / 2" \
                    -prefix ${mydir}/RD.nii 2>/dev/null &&
                rd=`3dmaskave -q -mask ${mydir}/mask.nii ${mydir}/RD.nii 2>/dev/null` &&
                row=${row}','${fa}','${ad}','${rd};
            else
                row=${row}',NA,NA,NA';
            fi;
        else
            row=${row}',NA,NA,NA';
        fi;
    done
    echo $row >> $weighted_tracts;
done
```

# 2019-04-09 14:46:01

Just for good measure, let's do this again because I noticed that the RD mask
was not being overwritten in the NCR cohort:

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

# 2019-04-10 16:19:28

I started running the other PNC images (non-WNH). I broke it up in sets of 10
just so it makes life easier when running bedpost later:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
rm swarm.fdt
for m in `cat xaa`; do
    echo "bash ~/research_code/dti/fdt_pnc_wrapper.sh ${m}" >> swarm.fdt;
done;
swarm -g 4 --time 4:00:00 -f swarm.fdt --partition gpu \
    --logdir trash_fdt --gres=gpu:k80:1 --job-name fdta
```

# 2019-04-12 17:41:05

Because we are already starting bedpost, we can do at least the brainmask QC
right away.

But I actually found out that many IDs died (113 out of 834). What happened?
Let's first make sure they have both DTI directories inside their tarballs:

```bash
for m in `cat /data/NCR_SBRB/pnc/dti_fdt/pnc_other_imaging.txt`; do
    if [ ! -e /data/NCR_SBRB/pnc/dti_fdt/${m}/dwi.nii.gz ]; then
        echo $m >> /data/NCR_SBRB/pnc/dti_fdt/error_conversion1.txt;
    fi;
done

for m in `cat /data/NCR_SBRB/pnc/dti_fdt/error_conversion1.txt`; do
    echo $m;
    if tar -tf /data/NCR_SBRB/pnc/${m}_1.tar.gz ${m}/DTI_35dir ${m}/DTI_36dir >/dev/null 2>&1; then
        echo $m should have converted;
    fi;
done
```

Yep, apparently all of them were indeed missing at least one of the directories.
Oh well. Let's create brain masks for everything that got converted then.


```bash
module load afni
cd /lscratch/${SLURM_JOBID}
for m in `cat /data/NCR_SBRB/pnc/dti_fdt/converted.txt`; do
    echo $m;
    mkdir ${m};
    cp /data/NCR_SBRB/pnc/dti_fdt/${m}/dwi.nii.gz \
        /data/NCR_SBRB/pnc/dti_fdt/${m}/b0_brain_mask.nii.gz ${m};
done

for m in `cat /data/NCR_SBRB/pnc/dti_fdt/converted.txt`; do
    cd /lscratch/${SLURM_JOBID}/${m}
    mkdir QC
    @chauffeur_afni                             \
        -ulay  dwi.nii.gz[0]                         \
        -olay  b0_brain_mask.nii.gz                        \
        -opacity 4                              \
        -prefix   QC/brain_mask              \
        -montx 6 -monty 6                       \
        -set_xhairs OFF                         \
        -label_mode 1 -label_size 3             \
        -do_clean;
    cp -r QC /data/NCR_SBRB/pnc/dti_fdt/${m}/;
done
```

Given the number of fails in bedpost, let's check which ones had successful
eddy, then we can just redo the bedpost splits, and rerun just the ones that
have failed.

```bash
cd /data/NCR_SBRB/pnc/dti_fdt/
for m in `cat converted.txt`; do
    if [ ! -e ${m}/eddy_s2v_unwarped_images.nii.gz ]; then
        echo $m >> need_eddy.txt;
    fi;
done
```

And I re-ran eddy just for those IDs. But they were all bad, in the sense that
they didn't have both DTI directories in the tarball, or had errors when running
eddy in the complete file. Well, we move on...

# 2019-04-14 19:55:29

While we wait on bedpost, let's fire up all the splits that were done:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
rm swarm.track
for m in `cat xab xac xad xae xaf`; do 
    echo "bash ~/research_code/dti/run_trackSubjectStruct.sh $m" >> swarm.track;
done
swarm -t 29 -g 52 -f swarm.track --job-name track --time 10:00:00 \
        --logdir trash_track -m fsl --gres=lscratch:10;
```

And since we have some sinteractive sessions open, let's also run the other QC
pictures for the IDs that should have finished bedpost by now:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt/;
for m in `cat xaa xab xac xad xae xaf`; do
    echo $m;
    mkdir /lscratch/${SLURM_JOBID}/${m};
    cp preproc/${m}/dti* \
       preproc/${m}/data.nii.gz \
       preproc/${m}/*mask* \
       preproc/${m}/*warp* /lscratch/${SLURM_JOBID}/${m};
done

for m in `cat xaa xab xac xad xae xaf`; do
    echo "==== $m ====";
    bash ~/research_code/dti/fdt_TBSS_and_QC.sh /lscratch/${SLURM_JOBID}/${m};
    cp -r cd /lscratch/${SLURM_JOBID}/${m}/* preproc/${m}/;
done
```

# 2019-04-17 10:15:40

I created a new converted.txt that doesn't include the IDs that failed eddy.
Now, let's check everyone for bedpost and re-run the errors:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
for m in `cat converted.txt`; do
    if [ ! -e preproc/${m}.bedpostX/mean_f1samples.nii.gz ]; then
        echo $m >> need_bedpost.txt;
    fi;
done
```

And let's collect the QC pics:

```bash
mkdir /data/NCR_SBRB/pnc/dti_fdt/summary_QC
cd /data/NCR_SBRB/pnc/dti_fdt/summary_QC/
mkdir brainmask
mkdir transform
mkdir DEC
mkdir SSE
for m in `cat ../converted.txt`; do
    echo ${m}
    cp ../${m}/QC/brain_mask.axi.png brainmask/${m}.axi.png
    cp ../${m}/QC/brain_mask.sag.png brainmask/${m}.sag.png
    cp ../${m}/QC/brain_mask.cor.png brainmask/${m}.cor.png
done

qc_dir=/data/NCR_SBRB/pnc/dti_fdt/summary_QC/
img_dir=/data/NCR_SBRB/pnc/dti_fdt/preproc/
for m in `cat ../converted.txt`; do
    echo $m;
    cp $img_dir/${m}/QC/FA_transform.axi.png $qc_dir/transform/${m}.axi.png
    cp $img_dir/${m}/QC/FA_transform.sag.png $qc_dir/transform/${m}.sag.png
    cp $img_dir/${m}/QC/FA_transform.cor.png $qc_dir/transform/${m}.cor.png

    cp $img_dir/${m}/QC/DEC_qc_dec_sca07.axi.png $qc_dir/DEC/${m}.axi.png
    cp $img_dir/${m}/QC/DEC_qc_dec_sca07.sag.png $qc_dir/DEC/${m}.sag.png
    cp $img_dir/${m}/QC/DEC_qc_dec_sca07.cor.png $qc_dir/DEC/${m}.cor.png

    cp $img_dir/${m}/QC/sse.axi.png $qc_dir/SSE/${m}.axi.png
    cp $img_dir/${m}/QC/sse.cor.png $qc_dir/SSE/${m}.cor.png
    cp $img_dir/${m}/QC/sse.sag.png $qc_dir/SSE/${m}.sag.png
done
```

# 2019-04-18 07:10:13

Finally, check who we need to re-run the tracks and compile the summary files:

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
rm complete.txt errors.txt
for s in `cat converted.txt`; do
    ndone=`grep ^ tracts/$s/*/tracts/waytotal | wc -l`;
    if [ $ndone == 27 ]; then
        echo $s >> complete.txt
    else
        echo $s >> errors.txt
    fi
done
```

```bash
cd /data/NCR_SBRB/pnc/dti_fdt
out_fname=~/tmp/pnc_others_mvmt_report.csv;
echo "id,Noutliers,PROPoutliers,NoutVolumes,norm.trans,norm.rot,RMS1stVol,RMSprevVol" > $out_fname;
for m in `cat /data/NCR_SBRB/pnc/dti_fdt/converted.txt`; do
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

```bash
mydir=/lscratch/${SLURM_JOBID}/
weighted_tracts=~/tmp/pnc_others_weighted_tracts.csv;
row="id";
for t in `cut -d" " -f 1 /data/NCR_SBRB/software/autoPtx/structureList`; do
    for m in fa ad rd; do
        row=${row}','${t}_${m};
    done
done
echo $row > $weighted_tracts;
for m in `cat /data/NCR_SBRB/pnc/dti_fdt/complete2.txt`; do
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
