#!/usr/bin/env bash

export HOME=/home/`whoami`

chmod -R a=wrx ./
export PATH=$PWD:$PATH

smoption=EDS
#lengthscale=0.5
lengthscale=1

template=$1
testImage=$2
outputFile=$3
trans=${outputFile/\.nii.gz/}Affine.txt


ftol=.01 
sep=`echo ${lengthscale}*4 | bc -l`

rtvCGM -SMOption $smoption -template $template -subject $testImage -sep $sep $sep $sep -ftol $ftol -outTrans $trans
#affineSymTensor3DVolume -in $subject -target $template -out $out -trans $trans -interp LEI 

ftol=.001 
sep=`echo ${lengthscale}*2 | bc -l`
rtvCGM -SMOption $smoption -template $template -subject $testImage -sep $sep $sep $sep -ftol $ftol -outTrans $trans -inTrans $trans
#affineSymTensor3DVolume -in $subject -target $template -out $out -trans $trans -interp LEI 

ftol=.01 
sep=`echo ${lengthscale}*4 | bc -l`
atvCGM -SMOption $smoption -template $template -subject $testImage -sep $sep $sep $sep -ftol $ftol -outTrans $trans -inTrans $trans
#affineSymTensor3DVolume -in $subject -target $template -out $out -trans $trans -interp LEI 

ftol=.001 
sep=`echo ${lengthscale}*2 | bc -l`
atvCGM -SMOption $smoption -template $template -subject $testImage -sep $sep $sep $sep -ftol $ftol -outTrans $trans -inTrans $trans


affineSymTensor3DVolume -in $testImage -target $template -out $outputFile -trans $trans -interp LEI 

ls 


