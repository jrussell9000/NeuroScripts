#!/usr/bin/env python

import sys
import os

from numpy import zeros, float, array

if len(sys.argv) < 2:
    print "Usage: demean_motion <filename>"
    sys.exit()

fname = sys.argv[1]
f = open(fname, 'r')
lines = f.readlines()
f.close()

N = len(lines)
output = zeros([6,N], float)

i = 0
for line in lines:
    data = array(map(float, line.split()[1:7]))
    output[:,i] = data
    i += 1

for i in xrange(6):
    output[i,:] -= output[i,:].mean()

outfile = fname.replace('.txt','')
outfile = outfile.replace('.1D','')
outfile = '%s_demean.txt' % outfile
f = open(outfile, 'w')
for i in xrange(N):
    f.write('%f' % output[0,i])
    for j in xrange(1,6):
        f.write('\t%f' % output[j,i])
    f.write('\n')
f.close()


print 'Demeaned motion parameters written to %s' % outfile
