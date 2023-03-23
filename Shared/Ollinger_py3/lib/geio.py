#!/usr/bin/env python

import sys
import os
#import platform
from wbl_util import get_library_name

#machtype = platform.machine()
#ostype = sys.platform
#pyversion = sys.version[0]

#x = platform.platform().lower().split('-')
#if 'linux' in sys.platform:
#    geio = 'GEio_' + x[0] +'_'+ x[-3] + ''.join(x[-2].split('.')) + '_' +  platform.processor() + '_py' + ''.join(platform.python_version().split('.')[:2])
#elif 'darwin' in sys.platform:
#    geio = 'GEio_' + x[0] + ''.join(x[1].split('.')[:2]) + '_' +  platform.architecture()[0] + '_py' + ''.join(platform.python_version().split('.')[:2])
#else:
#    geio = 'unknown'

geio = get_library_name('GEio')
print(geio)
print(os.environ['LD_LIBRARY_PATH'])

exec('from %s import _extent_threshold, reslice_3d, _scatter_add, get_ge_header' % geio)


def pyextent_threshold(image, hght_thresh, extent_lower_thresh, extent_upper_thresh):
    _extent_threshold(image, hght_thresh, \
                            int(extent_lower_thresh), int(extent_upper_thresh))



def pyreslice_3d(image, Rin, dims_out):
    imgout = reslice_3d(image.astype(float), Rin.astype(float), dims_out)
    return imgout

def pyget_ge_header(fname, slot):
    hdrlist = get_ge_header(fname, slot)
    return hdrlist


