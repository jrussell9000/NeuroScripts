#!/bin/csh -f
#
# processtopup
#
# Pre-process GE DICOM files and then calls fsl topup tools to perform unwarping
# 
#
# Requires: FSL 5& above tools (TOPUP) from fMRIB 
#           AFNI tools from NIH
#  
# Calls:  several AFNI and FSL commands
#
# What this script does:
#  1) Perform TOPUP distortion correction on GE MR750 DTI dicom data.  
#
# Version History
#  1.0 11/16/2012 EG created by modifying the ppge4 code to work with FSL topup tools.
#  1.1 04/09/2013 KL modifed to work with the DTI TOPUP protocols. 
# 
# Send Comments/Questions to eghobrial@ucsd.edu or kunlu@ucsd.edu.
#

set VERSION = '$Id$';
set inputargs = ($argv);
set DateStr = "`date '+%y%m%d%H%M'`"

set dir1 = (); 
set dir2 = (); 
set tmpdir = 'tmp';
set outstem = ();
set TR = ();
set dsnum = ();
set isodd = 0;
set docleanup = 1;
set bonum = 1;
set nslices = 0;
set cleanup = 0;
set PrintHelp = 0;
set diffdirnum = 0;
set postfix = '.nii.gz';
set pedir1 = 0;
set pedir2 = 1;
set pedir3 = 0;
set txtfname = 'my_acq_para.txt';

if($#argv == 0) goto usage_exit;
set n = `echo $argv | grep version | wc -l` 
if($n != 0) then
  echo $VERSION
  exit 0;
endif
set n = `echo $argv | grep help | wc -l` 
if($n != 0) then
  set PrintHelp = 1;
  goto usage_exit;
endif

goto parse_args;
parse_args_return:


goto check_params;
check_params_return:


## Get/Create tmp directory ##
mkdir -p $tmpdir
if( ! -e $tmpdir) then
  echo "ERROR: cannot find tmp dir $tmpdir"
  exit 1;
endif 


set curdir = `pwd`;


#readout time is set to 1.0 here. The true read out need to be calcucated 
#which will be added later.  This does not affect the TOPUP unwarping, but will 
#scale the estimated fieldmap.  
set ro_time = 1.0
#echo ""
#echo "*****INFO: EPI readout time = $ro_time sec ()"

#to3d will read TR from header if TR=0
set TR = 0

#start 
if ($dsnum == 1 ) then
echo $curdir/$dir1
cd $curdir/$dir1
set f1 = `ls i*.1`
set l2 = `dicom_hdr $f1 | grep "0019 10e0"`
set diffdirnum  = `echo "$l2" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 24 content = $l2"
echo "INFO: Num of Diff Directions = $diffdirnum "
echo ""
set l4 = `dicom_hdr $f1 | grep "0019 10df"`
set bonum  = `echo "$l4" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 23 content = $l4"
echo "INFO: Num of b0 = $bonum "
echo ""

find . -type f -name 'i*' | sort > $curdir/$tmpdir/flist
set fl = `cat $curdir/$tmpdir/flist | wc -l`
echo "num of files = $fl"

@ nofsets = $diffdirnum + $bonum
echo "num of sets $nofsets"
set nslices =  `echo " $fl / $nofsets " | bc -l | awk '{printf "%.0f",$1}'`
echo "total number of slices $nslices"

#check if we have odd number of slices

set rem = `expr $nslices \% 2`
if ($rem == 0) then
   echo "even number of slices"
else
   echo "odd number of slices"
   set isodd = 1
endif


set cmd = (to3d -prefix dtiap$postfix -time:zt $nslices $nofsets $TR alt+z i*)
echo $cmd 
$cmd

echo "****************  "
echo $isodd

if ($isodd == 1) then
 echo "odd number of slices. script will remove the last slice"
@ decval = 1
@ newnum = $nslices - $decval
   3dZcutup -prefix dtiap1$postfix -keep 1 $newnum dtiap$postfix
mv dtiap1$postfix $curdir/$tmpdir/dtiap$postfix
rm -f dtiap$postfix
else
mv dtiap$postfix $curdir/$tmpdir/dtiap$postfix
endif
endif

if ($dsnum == 2) then
echo $curdir/$dir1
cd $curdir/$dir1
set f1 = `ls i*.1`
set l2 = `dicom_hdr $f1 | grep "0019 10e0"`
set diffdirnum  = `echo "$l2" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 24 content = $l2"
echo "INFO: Num of Diff Directions = $diffdirnum "
echo ""
set l4 = `dicom_hdr $f1 | grep "0019 10df"`
set bonum  = `echo "$l4" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 23 content = $l4"
echo "INFO: Num of b0 = $bonum "
echo ""


find . -type f -name 'i*' | sort > $curdir/$tmpdir/flist
set fl = `cat $curdir/$tmpdir/flist | wc -l`
echo "num of files = $fl"

@ nofsets = $diffdirnum + $bonum
echo "num of sets $nofsets"
set nslices =  `echo " $fl / $nofsets " | bc -l | awk '{printf "%.0f",$1}'`
echo "total number of slices $nslices"

#check if we have odd number of slices


set rem = `expr $nslices \% 2`
if ($rem == 0) then
   echo "even number of slices"
else
   echo "odd number of slices"
   set isodd = 1
endif



set cmd = (to3d -prefix dtiap$postfix -time:zt $nslices $nofsets $TR alt+z i*)
echo $cmd 
$cmd

echo "****************  "
echo $isodd

if ($isodd == 1) then
 echo "odd number of slices script will remove the last slice"
@ decval = 1
@ newnum = $nslices - $decval
   3dZcutup -prefix dtiap1$postfix -keep 1 $newnum dtiap$postfix
mv dtiap1$postfix $curdir/$tmpdir/dtiap$postfix
rm -f dtiap$postfix
else
mv dtiap$postfix $curdir/$tmpdir/dtiap$postfix
endif


echo $curdir/$dir2
cd $curdir/$dir2

set f1 = `ls i*.1`
set l2 = `dicom_hdr $f1 | grep "0019 10e0"`
set diffdirnum  = `echo "$l2" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 24 content = $l2"
echo "INFO: Num of Diff Directions = $diffdirnum "
echo ""
set l4 = `dicom_hdr $f1 | grep "0019 10df"`

set bonum  = `echo "$l4" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 23 content = $l4"
echo "INFO: Num of b0 = $bonum "
echo ""

find . -type f -name 'i*' | sort > $curdir/$tmpdir/flist1
set fl = `cat $curdir/$tmpdir/flist | wc -l`
echo "num of files = $fl"

@ nofsets = $diffdirnum + $bonum
echo "num of sets $nofsets"

set nslices =  `echo " $fl / $nofsets " | bc -l | awk '{printf "%.0f",$1}'`
echo "total number of slices $nslices"

set rem = `expr $nslices \% 2`
if ($rem == 0) then
   echo "even number of slices"
else
   echo "odd number of slices"
   set isodd = 1
endif


set cmd = (to3d -prefix dtipa$postfix -time:zt $nslices $nofsets $TR alt+z i*)
echo $cmd 
$cmd

if ($isodd == 1) then
 echo "odd number of slices script will remove the last slice"
@ decval = 1
@ newnum = $nslices - $decval
   3dZcutup -prefix dtipa1$postfix -keep 1 $newnum dtipa$postfix
mv dtipa1$postfix $curdir/$tmpdir/dtipa$postfix
rm -f dtipa$postfix
else
mv dtipa$postfix $curdir/$tmpdir/dtipa$postfix
endif
endif

#Protocol III Kun tricked system to create images with 1 B0 and 1 with no diff on.

if ($dsnum == 3) then
echo $curdir/$dir1
cd $curdir/$dir1
set f1 = `ls i*.1`
set l2 = `dicom_hdr $f1 | grep "0019 10e0"`
set diffdirnum  = `echo "$l2" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 24 content = $l2"
echo "INFO: Num of Diff Directions = $diffdirnum "
echo ""

find . -type f -name 'i*' | sort > $curdir/$tmpdir/flist
set fl = `cat $curdir/$tmpdir/flist | wc -l`
echo "num of files = $fl"

@ nofsets = 2
echo "num of sets $nofsets"
set nslices =  `echo " $fl / $nofsets " | bc -l | awk '{printf "%.0f",$1}'`
echo "total number of slices $nslices"
#check if we have odd number of slices
set rem = `expr $nslices \% 2`
if ($rem == 0) then
   echo "even number of slices"
else
   echo "odd number of slices"
   set isodd = 1
endif

set cmd = (to3d -prefix dtiap$postfix -time:zt $nslices $nofsets $TR alt+z i*)
echo $cmd 
$cmd
echo "****************  "
echo $isodd
if ($isodd == 1) then
 echo "odd number of slices script will remove the last slice"
@ decval = 1
@ newnum = $nslices - $decval
   3dZcutup -prefix dtiap1$postfix -keep 1 $newnum dtiap$postfix
mv dtiap1$postfix $curdir/$tmpdir/dtiap$postfix
rm -f dtiap$postfix
else
mv dtiap$postfix $curdir/$tmpdir/dtiap$postfix

endif


echo $curdir/$dir2
cd $curdir/$dir2
set f1 = `ls i*.1`
set l2 = `dicom_hdr $f1 | grep "0019 10e0"`
set diffdirnum  = `echo "$l2" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 24 content = $l2"
echo "INFO: Num of Diff Directions = $diffdirnum "
echo ""


find . -type f -name 'i*' | sort > $curdir/$tmpdir/flist1
set fl = `cat $curdir/$tmpdir/flist | wc -l`
echo "num of files = $fl"

@ nofsets = 2
echo "num of sets $nofsets"

set nslices =  `echo " $fl / $nofsets " | bc -l | awk '{printf "%.0f",$1}'`
echo "total number of slices $nslices"

set rem = `expr $nslices \% 2`
if ($rem == 0) then
   echo "even number of slices"
else
   echo "odd number of slices"
   set isodd = 1
endif


set cmd = (to3d -prefix dtipa$postfix -time:zt $nslices $nofsets $TR alt+z i*)
echo $cmd 
$cmd

if ($isodd == 1) then
 echo "odd number of slices script will remove the last slice"
@ decval = 1
@ newnum = $nslices - $decval
   3dZcutup -prefix dtipa1$postfix -keep 1 $newnum dtipa$postfix
mv dtipa1$postfix $curdir/$tmpdir/dtipa$postfix
rm -f dtipa$postfix
else
mv dtipa$postfix $curdir/$tmpdir/dtipa$postfix

endif

echo $curdir/$dir3
cd $curdir/$dir3
set f1 = `ls i*.1`
set l2 = `dicom_hdr $f1 | grep "0019 10e0"`
set diffdirnum  = `echo "$l2" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 24 content = $l2"
echo "INFO: Num of Diff Directions = $diffdirnum "
echo ""
set l4 = `dicom_hdr $f1 | grep "0019 10df"`
set bonum  = `echo "$l4" | awk -F// '{printf "%.0f",$3}'`
echo ""
echo "UserData 23 content = $l4"
echo "INFO: Num of b0 = $bonum "
echo ""

find . -type f -name 'i*' | sort > $curdir/$tmpdir/flist3
set fl = `cat $curdir/$tmpdir/flist3 | wc -l`
echo "num of files = $fl"

@ nofsets = $diffdirnum + $bonum
echo "num of sets $nofsets"
set nslices =  `echo " $fl / $nofsets " | bc -l | awk '{printf "%.0f",$1}'`
echo "total number of slices $nslices"

set rem = `expr $nslices \% 2`
if ($rem == 0) then
   echo "even number of slices"
else
   echo "odd number of slices"
   set isodd = 1
endif

set cmd = (to3d -prefix dti$postfix -time:zt $nslices $nofsets $TR alt+z i*)
echo $cmd 
$cmd


if ($isodd == 1) then
 echo "odd number of slices script will remove the last slice"
@ decval = 1
@ newnum = $nslices - $decval
   3dZcutup -prefix dti1$postfix -keep 1 $newnum dti$postfix
mv dti1$postfix $curdir/$tmpdir/dti$postfix
rm -f dti$postfix
else
mv dti$postfix $curdir/$tmpdir/dti$postfix
endif


endif #dsnum=3



cd $curdir/$tmpdir
#copy the default configuration file
cp $FSLDIR/etc/flirtsch/b02b0.cnf .


echo "Calling FSL TOPUP (may take a while)"

#User have only one data acquired using inhouse PSD
if ($dsnum == 1) then
	fslroi dtiap$postfix b0dtipaflipped$postfix 0 1
	fslroi dtiap$postfix b0dtiap$postfix 1 1

set cmd = (fslroi dtiap$postfix dti$postfix 1 $nofsets)
echo $cmd
$cmd
	3dLRflip -AP -prefix b0dtipa.nii.gz b0dtipaflipped.nii.gz
	fslmerge -t bothb0$postfix b0dtiap$postfix b0dtipa$postfix


if (! -e $txtfname) then
    echo "0 1 0 $ro_time" >> $txtfname
    echo "0 -1 0 $ro_time" >> $txtfname
endif
 
	topup --imain=bothb0$postfix --datain=my_acq_para.txt --config=b02b0.cnf --fout=fmap --iout=b0good --out=my_topup_results -v
	applytopup --imain=dti --inindex=1 --datain=my_acq_para.txt --topup=my_topup_results --method=jac --interp=spline --out=$outstem
endif

#User aquired two full DTI data sets with reversed polarity
if ($dsnum == 2) then
	fslroi dtiap$postfix b0dtiap$postfix 0 $bonum
	fslroi dtipa$postfix b0dtipa$postfix 0 $bonum
	fslmerge -t bothb0$postfix b0dtiap$postfix b0dtipa$postfix

set i = 1;
set j = 1;
if (! -e $txtfname) then
  while ($i <= $bonum)
    echo "0 1 0 $ro_time" >> $txtfname
    @ i = $i + 1
  end
  while ($j <= $bonum)
    echo "0 -1 0 $ro_time" >> $txtfname
    @ j = $j + 1
  end
endif

	topup --imain=bothb0$postfix --datain=my_acq_para.txt --config=b02b0.cnf --fout=fmap --iout=b0good --out=my_topup_results -v
	applytopup --imain=dtiap,dtipa --inindex=1,2 --datain=my_acq_para.txt --topup=my_topup_results --out=$outstem
endif

#User aquired two calibration scans with reversed polarity and one full DTI
if ($dsnum == 3) then

	fslmerge -t bothb0$postfix dtiap$postfix dtipa$postfix

#resample calibration scan if there is a dimension mismatch between the calibration and DTI
# Check matrix size and resample fmap data if needed (KL):
set matcal = `fslinfo bothb0$postfix | awk '{if($1 == "dim1") print $2}; {if($1 == "dim2") print $2}; {if($1 == "dim3") print $2}'`


set matdti = `fslinfo dti$postfix | awk '{if($1 == "dim1") print $2}; {if($1 == "dim2") print $2}; {if($1 == "dim3") print $2}'`

if (($matcal[1] != $matdti[1]) || ($matcal[2] != $matdti[2]) || ($matcal[3] != $matdti[3])) then
echo "**************************** WARNING ****************************************"
echo "WARNING: calibration data does not match the DTI data !"
echo "Resampling the calibration to DTI ... "
echo "*****************************************************************************"

set cmd=(3dresample -master  dti$postfix -prefix bothb0_rs$postfix -inset bothb0$postfix)
echo $cmd
$cmd
else
echo "check ... calibration matches the DTI data ... OK"
cp bothb0$postfix bothb0_rs$postfix
endif

if (! -e $txtfname) then
    echo "0 1 0 $ro_time" >> $txtfname
    echo "0 1 0 $ro_time" >> $txtfname
    echo "0 -1 0 $ro_time" >> $txtfname
    echo "0 -1 0 $ro_time" >> $txtfname
endif

# register DTI with calibration scan KL
	3dvolreg -twopass -twodup -base bothb0_rs$postfix\[{0}\] -prefix dti_regb0$postfix dti${postfix}\[{0}\]
        3drotate -rotparent dti_regb0$postfix -prefix dti_reg$postfix dti$postfix

	topup --imain=bothb0_rs$postfix --datain=my_acq_para.txt --config=b02b0.cnf --fout=fmap --iout=b0good --out=my_topup_results -v      

	applytopup --imain=dti_reg --inindex=1 --datain=my_acq_para.txt --topup=my_topup_results --method=jac --interp=spline --out=$outstem
endif

cd $curdir
cp $tmpdir/$outstem$postfix .


echo "topup done"



if($docleanup) then
  
  echo "Deleting files in $tmpdir"
  rm -rf $tmpdir
endif


exit 0;


parse_args:
set cmdline = ($argv);
while( $#argv != 0 )

  set flag = $argv[1]; shift;

  switch($flag)

    case "-dsnum":
      if ( $#argv == 0) goto arg1err;
      set dsnum = $argv[1]; shift;
      breaksw

    case "-d1":
      if ( $#argv == 0) goto arg1err;
      set dir1 = $argv[1]; shift;
      breaksw

   case "-d2":
      if ( $#argv == 0) goto arg1err;
      set dir2 = $argv[1]; shift;
      breaksw

    case "-d3":
      if ( $#argv == 0) goto arg1err;
      set dir3 = $argv[1]; shift;
      breaksw


    case "-o":
      if ( $#argv == 0) goto arg1err;
      set outstem = $argv[1]; shift;
      breaksw

    case "-tmpdir":
      if ( $#argv == 0) goto arg1err;
      set tmpdir = $argv[1]; shift;
      breaksw


    case "-nocleanup":
      set docleanup = 0;
      breaksw


    default:
      echo ERROR: Flag $flag unrecognized. 
      echo $cmdline
      exit 1
      breaksw
  endsw

end

goto parse_args_return;
############--------------##################

############--------------##################
check_params:
 if ($#dsnum == 0) then
    echo "ERROR: must specify dsnum (1,2, or 3)"
    exit 1;
 endif

 if ($dsnum == 1) then
  if($#dir1 == 0) then
    echo "ERROR: must specify a DTI directory"
    exit 1;
  endif
  if ( ! -e $dir1) then
    echo "ERROR: $dir1 does not exist!"
    exit 1;
  endif
 endif

if ($dsnum == 2) then
  if($#dir1 == 0) then
    echo "ERROR: must specify a DTI directory"
    exit 1;
  endif
if($#dir2 == 0) then
    echo "ERROR: must specify a second DTI directory"
    exit 1;
  endif
  if ( ! -e $dir1) then
    echo "ERROR: $dir1 does not exist!"
    exit 1;
  endif
if ( ! -e $dir2) then
    echo "ERROR: $dir2 does not exist!"
    exit 1;
  endif
 endif


if ($dsnum == 3) then
  if($#dir1 == 0) then
    echo "ERROR: must specify a calibration directory"
    exit 1;
  endif
if($#dir2 == 0) then
    echo "ERROR: must specify a second calibration directory"
    exit 1;
  endif
if($#dir3 == 0) then
    echo "ERROR: must specify a DTI directory"
    exit 1;
  endif
  if ( ! -e $dir1) then
    echo "ERROR: $dir1 does not exist!"
    exit 1;
  endif
if ( ! -e $dir2) then
    echo "ERROR: $dir2 does not exist!"
    exit 1;
  endif
if ( ! -e $dir3) then
    echo "ERROR: $dir3 does not exist!"
    exit 1;
  endif

 endif


  if($#outstem == 0) then
    echo "ERROR: must specify an output stem"
    exit 1;
  endif


goto check_params_return;
############--------------##################

############--------------##################
arg1err:
  echo "ERROR: flag $flag requires one argument"
  exit 1
############--------------##################


usage_exit:
    echo "Name"
    echo "     processtopup  - Processes GE DTI DiCOM files to correct geometric distortion"
    echo "                     using FSL TOPUP "
    echo ""
    echo "System requirements"
    echo "     AFNI - AFNI_2011 and up, 32bit version or 64bit version"
    echo "     FSL  - FSL5.0 and up "
    echo "     (Environment Variable FSLOUTPUTTYPE must be set to NIFTI_GZ)" 
    echo "     (Environment Variable FSLDIR must be set and piont to the FSL installation folder) "
    echo ""
    echo "Synopsis"
    echo "     processtopup -dsnum <num of DTI dir> -d1 <DTI data dir> [-d2 <DTI data dir> -d3 <DTI data dir> <options>] -o <outstem>"
    echo ""
    echo "Required Arguments"
    echo "     -dsnum <number of DTI data dir, 1, 2 or 3>"
    echo "     if -dsnum 1"
    echo "         -d1 <DTI data dir>"
    echo "     if -dsnum 2"
    echo "         -d1 <DTI_fwd data dir>"
    echo "         -d2 <DTI_rvs data dir>"
    echo "     if -dsum 3"
    echo "         -d1 <Cal1 dir>"
    echo "         -d2 <Cal2 dir>" 
    echo "         -d3 <DTI data dir> "
    echo "         (NOTE:  -d1 and -d3 must have the same phase encoding direction) "
    echo "     -o <unwarpped voluem filename stem>"
    echo " "
 
    echo ""
    echo "Optional Arguments"
    echo "     -tmpdir 	      : specify temporary directory name"
    echo "     -nocleanup     : disables removal of temporary files"
    echo "" 
    echo "Outputs"
    echo "     <outstem> - unwarpped volume filename stem" 
    echo ""
    echo "Version"
    echo "     "$VERSION
    echo ""
    echo "Credits"
    echo "     FSL library" 
    echo ""
    echo "Reporting Bugs"
    echo "     Report bugs to eghobrial@ucsd.edu or kunlu@ucsd.edu"
    echo ""



  if($PrintHelp) \
  cat $0 | awk 'BEGIN{prt=0}{if(prt) print $0; if($1 == "BEGINHELP") prt = 1 }'

exit 1;


#---- Everything below here is printed out as part of help -----#
BEGINHELP
