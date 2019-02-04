import os
import sys
import subprocess

def denoise(input_dwi, output_dwi):
    subprocess.call(['dwidenoise', '-force', input_dwi, output_dwi])

def degibbs(input_dwi, output_dwi):
    subprocess.call(['mrdegibbs', '-force', input_dwi, output_dwi])

