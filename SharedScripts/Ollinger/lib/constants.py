#!/usr/bin/env python

import math
import sys
import os
from numpy import array

ID = "$Id: constants.py 489 2011-04-27 17:06:34Z jmo $"[1:-1]

if __name__ == '__main__':
    sys.stdout.write('%s\n' % ID)
    sys.exit()

class _constants():

    def __init__(self):

#        self.apps = os.getenv('APPS')
        self.apps = '/apps'
        self.ID = ID

#       Mathematical constants.
        self.pi = math.pi
        self.e = math.e
        self.gamma_hz_gauss = 4257
        self.fwhm2sg = 1./(2.*math.sqrt(2.*math.log(2.)))
        self.rad2deg = 180./math.pi
        self.deg2rad = math.pi/180.

#       Paths for preprocessing script.
        fname = '%s/noarch/fmri_tools/etc/preproc_template.yaml' % self.apps
#        if not os.path.exists(fname):
#            fname = os.getenv('PREPROC_TEMPLATE')
        self.preproc_template_default = fname

#       File listing studies that have been processed.
        exams_file = '/study/scanner/preprocessed_exams.txt'
#        try:
#            if not os.path.exists(exams_file):
#                exams_file = '/dev/null'
#        except:
#            exams_file = '/dev/null'
        self.exams_file = exams_file

        self.primary_tmp_dir = '/scratch.local'
        self.secondary_tmp_dir = '/tmp'
#        self.primary_tmp_dir = '/tmp' # heri
#        self.secondary_tmp_dir = '/Volumes/Storage/Processing/scratch' # heri

#       SPM Paths
        self.SPM_NORM_PATH = '%s/spm5' % self.apps
        self.SPM_BATCH_PATH = '%s/spm5/toolbox' % self.apps
        self.TEMPLATE_PATH = '%s/templates' % self.apps
        self.MNI_SHAPE = [91, 109, 91]
        self.MNI_SIZE = [2., 2., 2.]
        self.MNI_ORIGIN = [90., 126., -72.]
        self.MNI_R = array([[  -1.,    0.,    0.,   90.], \
                            [   0.,   -1.,    0.,  126.], \
                            [   0.,    0.,    1.,  -72.], \
                            [   0.,    0.,    0.,    1.]])

#       NIFTI constants.
        self.NIFTI_XFORM_UNKNOWN = 0
        self.NIFTI_XFORM_SCANNER_ANAT = 1
        self.NIFTI_XFORM_ALIGNED_ANAT = 2
        self.NIFTI_XFORM_TAILARACH = 3
        self.NIFTI_XFORM_MNI_152 = 4

#       Preprocessing paths
        self.INSTALLDIR='%s/noarch' % self.apps
        self.FMRI_TOOLS_VERSION_FILE='%s/fmri_tools/version.txt' % \
                                                            self.INSTALLDIR

        self.FSLDIR = os.getenv('FSLDIR')

    class ConstError(TypeError): 
        pass

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise self.ConstError, "Can't rebind constants(%s)" % name
        self.__dict__[name] = value

    def __delattr__(self, name):
        if name in self.__dict__:
            raise self.ConstError, "Can't unbind constants(%s)" % name
        raise NameError, name

import sys 
sys.modules[__name__] = _constants()


