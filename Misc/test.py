#!/usr/bin/env python2.7
import dicom
import argparse
import pickle
import os
import warnings
import json

class Depickler():
    def initialize(self):
        ap = argparse.ArgumentParser()
        ap.add_argument("-p", "--picklefile", required=True)
        args = vars(ap.parse_args())
        picklefile = args["picklefile"]
        cwd = os.getcwd()
        self.picklepath = os.path.join(cwd,picklefile)
        print(self.picklepath)

    def un_pickle(self):
        apicklefile = open(self.picklepath, "r")
        apickle = pickle.load(apicklefile)
        type(apickle).__name__
        adict = dict(apickle)
        del adict['native_header']['DicomInfo']
        print(adict)
        # json.dumps(apickle['native_header'])
        #print(str(apickle['native_header']['SeriesDescription']))


if __name__ == '__main__':
    p = Depickler()
    p.initialize()
    p.un_pickle()
