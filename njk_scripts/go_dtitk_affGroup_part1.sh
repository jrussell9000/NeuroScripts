#!/usr/bin/env bash

export HOME=/home/`whoami`

chmod -R a=wrx .
export PATH=$PWD:$PATH

template=$1
avgAffineInv=$2
img=$3
intrans=$4
outputFile=$5
outtrans=$6

ls -ltr 
more $intrans

echo affine3Dtool -in $intrans -compose $avgAffineInv -out $outtrans
affine3Dtool -in $intrans -compose $avgAffineInv -out $outtrans

more $outtrans
echo affineSymTensor3DVolume -in $img -trans $outtrans -target $template -out $outputFile
affineSymTensor3DVolume -in $img -trans $outtrans -target $template -out $outputFile





