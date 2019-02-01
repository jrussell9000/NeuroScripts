import os
import sys
import subprocess

def denoise(input_dwi, output_dwi):
    subprocess.call(['dwidenoise', input_dwi, output_dwi])

def degibbs(input_dwi, output_dwi):
    subprocess.call(['mrdegibbs', input_dwi, output_dwi])

