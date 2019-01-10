#!/usr/bin/env bash

export HOME=/home/`whoami`

chmod -R a=wrx .
export PATH=$PWD:$PATH

template=$1
affineInv=$2

mkdir templateDir
mv $template templateDir

ls *Affine.txt > myAffineTransforms.txt


# average affine inverse transforms. -- OBVIOUSLY, 1 indicates inverse. :-/ 
affine3DShapeAverage myAffineTransforms.txt templateDir/$template $affineInv 1





