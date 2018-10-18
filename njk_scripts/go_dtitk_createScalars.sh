#!/usr/bin/env bash

export HOME=/home/`whoami`

chmod -R a=wrx ./
export PATH=$PWD:$PATH

smoption=EDS
#lengthscale=0.5
lengthscale=1

myImage=$1

fa=$2
tr=$3
ad=$4
rd=$5
pd=$6
rgb=$7


TVtool -in $myImage -fa -out $fa
TVtool -in $myImage -tr -out $tr
TVtool -in $myImage -ad -out $ad 
TVtool -in $myImage -rd -out $rd
TVtool -in $myImage -pd -out $pd
TVtool -in $myImage -rgb -out $rgb

touch test.txt

SVGaussianSmoothing -in $fa -fwhm  2 2 2
SVGaussianSmoothing -in $tr -fwhm  2 2 2
SVGaussianSmoothing -in $ad -fwhm  2 2 2
SVGaussianSmoothing -in $rd -fwhm  2 2 2
SVGaussianSmoothing -in $pd -fwhm  2 2 2

ls -ltr


