
import pickle
import dicom
import numpy as np
import sys
import csv


filename = "/home/justin/scans/s14_dti.pickle"
pickle_file = open(filename, 'r')
picklist1 = pickle.load(pickle_file)
# fileout = "test.txt"
# f = open(fileout, 'wb')
# f.write(picklist1)

dcminf = pickle.load(open(filename, 'rb'))
s_dcminf = str(dcminf)
f = open("test.txt", 'wb')
f.write(s_dcminf)
