#! /usr/bin/python3
import argparse
import os
from subprocess import call


class dwi_preproc():

    def Initialize(self):
        parser = argparse.ArgumentParser(description="DWI Preprocessing Script")
        parser.add_argument("input_file")
        args = parser.parse_args()
        # self.input_file = args
        # if not os.access(self.input_file, os.R_OK):
        #    print('Error')
        input_file = args.input_file
        # print(input_file)

    def skullstip(self):
        call('dwipreproc' & input_file)


if __name__ == '__main__':
    dp = dwi_preproc()
    dp.Initialize()
    dp.skullstip()
