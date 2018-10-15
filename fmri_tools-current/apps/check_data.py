#!/usr/bin/env python

# Written by John Ollinger
#
# University of Wisconsin, 8/16/09

#Copyright (c) 2006-2007, John Ollinger, University of Wisconsin
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are
#met:
#
#    * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ** This software was designed to be used only for research purposes. **
# ** Clinical uses are not recommended, and have never been evaluated. **
# ** This software comes with no warranties of any kind whatsoever,    **
# ** and may not be useful for anything.  Use it at your own risk!     **
# ** If these terms are not acceptable, you aren't allowed to use the code.**


#

# Purpose: Summarize data for a given study and verify that the data are
#           consistent.

# By: John Ollinger

# Data: 7/10/2008

ID = "$Id: check_data.py 622 2011-11-17 20:01:32Z appnate $"[1:-1]

import os
import sys
import time
from optparse import OptionParser
from datetime import datetime

#from preprocess import DataInfo
from file_io import Header, isImage, write_yaml, isIfile, file_type, BiopacData
from wisc_dicom import IsDicom
# from preprocess import IMGTYPES
from wbl_util import except_msg

IMGTYPES = {'efgre3d':'T1High', \
            '3dir':'T1High', \
            'bravo':'T1High', \
            'fse-xl':'T2', \
            'frfseopt':'T2', \
            'cubet2':'T2', \
            '2dfast':'fmap', \
            'epibold':'epi', \
            'fcmemp':'T1se', \
            'fse':'T2', \
            '3-plane':'localizer', \
            'epi':'epi', \
            'epirt':'epi', \
            'epirt_20':'epi', \
            'epirt_22':'epi', \
            '*epfid2d1_64':'epi', \
            'epi2':'dti', \
            'dti':'dti', \
            '3dpcasl': 'asl'}

checked_filetypes = ['ge_data', 'dicom']

class CheckData():
    def __init__(self):
        if __name__ == '__main__':
            self.ParseOptions()
        self.imgtypes = IMGTYPES
        self.error = False
        self.summary = None
#        self.skeys = self.GetSortedSeries()

    def ParseOptions(self): 
        usage = "Usage: check_data <path-to-data>\nEnter --help for more info."
        optparser = OptionParser(usage)
        optparser.add_option( "-v", "--verbose", action="store_true", \
                dest="verbose",default=False, help='Print stuff to screen.')
        optparser.add_option( "", "--rescan", action="store_true", \
                dest="rescan",default=False, \
                help='Rescan all dicom directories.')
        optparser.add_option( "", "--rewrite-yaml", action="store_true", \
                dest="rewrite_yaml",default=False, help='Rewrite yaml files.')
        optparser.add_option( "", "--fast", action="store_true",  \
                dest="fast",default=False, help='Fast check by making sure ' + \
                'each directory contains the correct number of files.')
        optparser.add_option( "-o","--output-file",action="store", \
                    dest="outfile", type="string",default='info.txt',\
                    help='Output file where summary should be stored. ' + \
                         'Enter "crt" to write to the screen.')
        optparser.add_option( "","--info_only",action="store_true", \
                    dest="info_only", default=False,\
                    help='Write summary. (requires -o option). Do not ' + \
                         'reread every file.')
        opts, args = optparser.parse_args()

        if len(args) != 1:
            print usage + '\n'
            sys.exit(1)
        else:
            self.topdir = os.path.abspath(args[0])

        self.rescan = opts.rescan
        self.verbose = opts.verbose
        self.rewrite_yaml = opts.rewrite_yaml
        if self.rewrite_yaml:
            self.rescan = True
        self.outfile = opts.outfile
        self.info_only = opts.info_only
        self.fast = opts.fast

    def CountDicomFiles(self, dname):
        nfiles = 0
        for fname in fnames:
            if fname.endswith('.bz2') and fname[-8:-4].isdigit():
                nfiles += 1
            elif fname.endswith('.gz') and fname[-6:-2].isdigit():
                nfiles += 1
            elif fname[-4:].isdigit():
                nfiles += 1

    def ClassifyFiles(self):
        procnames = []
        unknowns = []
        biopac_files = []
        for dirpath, dnames, fnames in os.walk(self.topdir):
            if dirpath in procnames:
                continue
            try:
                isd = IsDicom(dirpath)
                if isd.isdir:
                    procnames.append(dirpath)
                elif isd.istar:
                    procnames.append(dirpath)
                else:
                    for fname in fnames:
                        fullpath = '%s/%s' % (dirpath, fname)
                        if isIfile(fullpath):
                            procnames.append(dirpath)
                            break
                        elif file_type(fullpath) == 'biopac':
                            biopac_files.append(fullpath)
                        else:
#                            print 'Unknown image %s: ' % fullpath
                            unknowns.append(dirpath)
            except:
#                print except_msg()
                unknowns.append(dirpath)
        procnames.sort()
        return procnames, unknowns, biopac_files

    def Process(self):
        image_files, unknowns, biopac_files = self.ClassifyFiles()
        if len(image_files) == 0:
            sys.stderr.write('No files to process.\n')
            sys.exit(1)
        self.info = {'unrecognized':unknowns}
        self.text_header = ''
        self.summary = ''
        for fullpath in image_files:
            H = self.GetHeader(fullpath)
            if H is None:
#                self.info[fullpath] = None
                self.info['unrecognized'].append(fullpath)
            else:
#               Store summary info.
                self.info[fullpath] = self.GetInfo(H, fullpath)

                if H.hdr['filetype'] == 'dicom'  and len(self.text_header) == 0:
                    text = self.TextHeader(H.hdr)
                else:
                    text = ''
                text += self.TextEntryInfo(fullpath, H.hdr)
                self.summary += text
                if self.verbose:
                    sys.stdout.write(text)

                if self.rewrite_yaml:
#                   Rewrite the yaml file.
                    self.WriteYaml(fullpath, H)
        for fullpath in biopac_files:
            bd = BiopacData(fullpath)
            text = bd.DumpSummary(fd=None)
            text = '\n%s\n%s' % (fullpath, text)
            self.summary += text
            if self.verbose:
                sys.stdout.write(text)
        self.WriteSummary(fullpath)
 
    def GetHeader(self, fullname):
        if self.verbose:
            print 'Checking %s' % fullname
        try:
            if self.rescan:
                H = Header(fullname, ignore_yaml=True, scan=True)
            else:
                H = Header(fullname, ignore_yaml=False, scan=False)
        except (KeyError, RuntimeError), errmsg:
                sys.stderr.write('\n%s\nError reading %s\n' % \
                                                (errmsg, fullname))
#                print except_msg()
                return None
        if H.hdr is None:
            sys.stderr.write('Not an image file: %s\n' % fullname)
            return None
        if H.hdr['filetype'] == 'dicom':
            if H.hdr['native_header'].get('DicomInfo', None) is None:
#               No scan info,  rescan file
                H = Header(fullname, ignore_yaml=True, scan=True)
                scanned = True
        return H

    def GetInfo(self, H, name):
        info = {}
        info['plane'] = H.hdr['plane']
        info['mdim'] = H.hdr['mdim']
        info['tdim'] = H.hdr['tdim']
        info['zdim'] = H.hdr['zdim']
        info['data_filetype'] = H.hdr['filetype']
        if H.hdr['filetype'] == 'dicom' or 'ge_ifile':
            info['acqtime'] = H.hdr['subhdr']['SeriesTime']
            info['series'] = H.hdr['subhdr']['SeriesNumber']
            info['psdname'] = \
                 H.hdr['subhdr']['PulseSequenceName']
            if isinstance(H.hdr['subhdr'].get('SeriesTime',None), int) or \
               isinstance(H.hdr['subhdr'].get('SeriesTime',None), float):
                info['acquisition_time'] = datetime.fromtimestamp(\
                float(H.hdr['subhdr']['SeriesTime'])).strftime('%d%b%Y_%X')
            elif isinstance(H.hdr['subhdr'].get('SeriesTime',None), str):
                info['acquisition_time'] = H.hdr['subhdr']['SeriesTime']
            else:
                info['acquisition_time'] = 'N/A'
        return info

    def WriteYaml(self, path, H):
        if os.path.isdir(path):
            dname = path
        else:
            dname = os.path.dirname(path)
        yaml_prefix = '%s/%s' % (dname, dname.split('/')[-1])
        if self.verbose:
            print 'Writing yaml header to %s' % yaml_prefix
            sys.stdout.flush()
        write_yaml(yaml_prefix, H.hdr, write_pickle=True)

#        H.write_hdr_to_yaml(yaml_prefix)

    def WriteSummary(self, path=None):
        if self.outfile is None:
            return
        elif self.outfile == 'crt':
            sys.stdout.write(self.summary)
        else:
            if path is None:
                dname = os.path.dirname(self.outfile)
            elif os.path.isdir(path):
                dname = os.path.dirname(path)
            else:
                dname = os.path.dirname(self.outfile)
            outfile = '%s/%s' % (dname, os.path.basename(self.outfile))
            if self.verbose:
                print 'Writing summary to %s' % outfile
            try:
                f = open(outfile, 'w')
                f.write(self.summary)
                f.close()
            except IOError:
                sys.stderr.write('Could not write summary to %s' % outfile)
                sys.exit(1)

    def FastCheck(self):
        print 'Fast check not currently supported.'
   #     dnames = self.info.keys()
   #     dnames.sort()
   #     if len(dnames) > 0:
   #         print '\nChecking %s' % os.path.dirname(dnames[0])
   #     for dname in dnames:
   #         if 'localizer' in dname:
   #             continue
   #         bname = os.path.basename(dname)
   #         nfiles = self.info[dname]['nfiles']
   #         zdim = self.info[dname]['zdim']
   #         tdim = self.info[dname]['tdim']
   #         mdim = self.info[dname]['mdim']
   #         if tdim > 1:
   #             plural = 's'
   #         else:
   #             plural = ''
   #         if mdim > 1:
   #             mplural = 's'
   #         else:
   #             mplural = ''
   #         if nfiles == zdim*tdim*mdim:
   #             print '%s: %d slices and %d frame%s and %s image type%s correctly uploaded' % \
   #                                 (bname, zdim, tdim, plural, mdim, mplural)
   #         elif nfiles < zdim*tdim*mdim:
   #             print '*** %s: Missing files. Expected: %d, Found: %d ***\n' % \
   #                                                 (bname, zdim*tdim, nfiles)
   #             self.error = True
   #         elif nfiles > zdim*tdim*mdim:
   #             print '*** %s: Extra files. Expected: %d, Found: %d ***\n' % \
   #                                                 (bname, zdim*tdim, nfiles)
   #             self.error = True


  #  def GetSortedSeries(self):
  #      self.keys = self.info.keys()
  #      self.keys.sort()
  #      ser_to_key = {}
  #      for key in self.info.keys():
  #          series = self.info[key]['series']
  #          if series > 0:
  #              if ser_to_key.has_key(series):
  #                  ser_to_key[series].append(key)
  #              else:
  #                  ser_to_key[series] = [key]
  #      series = ser_to_key.keys()
  #      series.sort()
  #      skeys = []
  #      for serno in series:
  #          skeys += ser_to_key[serno]
  #      return skeys

    def Error(self, path):
        print 'plane: ',hdr['plane'], self.info[path]['plane']
        print 'tdim: ',hdr['tdim'], self.info[path]['tdim']
        print 'data_filetype: ',hdr['filetype'], self.info[path]['data_filetype']
        print 'acqtime: ', hdr['subhdr']['SeriesTime'], self.info[path]['acqtime']
        print 'acqtime: ', type(hdr['subhdr']['SeriesTime']), type(self.info[path]['acqtime'])
        errstr = '\n*** CheckData: Inconsistent data in %s ***\n' % path
        sys.stderr.write(errstr)
        self.error = True 

    def TextHeader(self, hdr):
        sd = hdr['subhdr']['StudyDate']
        return \
        'Protocol: %s\n' % hdr['subhdr']['ProtocolName'] + \
        'Study description: %s\n' % hdr['subhdr']['StudyDescription'] + \
        'Study date: %s/%s/%s\n' % (sd[4:6],sd[6:8],sd[:4]) + \
        'Patient ID: %s\n' % hdr['subhdr']['PatientId'] + \
        'Patient sex: %s\n' % hdr['subhdr']['PatientSex'] + \
        'Patient weight: %s\n' % hdr['subhdr']['PatientWeight'] + \
        'Patient age: %s\n' % hdr['subhdr']['PatientAge']

    def TextEntryInfo(self, path, hdr):
        psdname = self.info[path]['psdname'].strip()
        return \
            '\nPath: %s\n' % path.strip() + \
            'Image type: %s\n' % self.imgtypes.get(psdname, psdname) + \
            'Series Description: %s\n' % hdr['subhdr']['SeriesDescription'] + \
            'Acquisition time: %s\n' % self.info[path]['acquisition_time'] + \
            'Orientation: %s\n' % hdr['orientation'] + \
            'Image plane: %s\n' % hdr['plane'] + \
            'Image dimensions: %dx%d\n' % (hdr['xdim'], hdr['ydim']) + \
            'Number of slices: %d\n' % hdr['zdim'] + \
            'Number of frames: %d\n' % self.info[path]['tdim'] + \
            'Number of image types: %d\n' % hdr['mdim']

def check_data():
    try:
        cd = CheckData()
        cd.Process()
    except (RuntimeError, IOError, OSError), errmsg:
        sys.stderr.write('%s\n%s\n' % (errmsg, except_msg()))
        sys.stderr.write('Error')
        sys.exit(1)
    if cd.error:
        sys.stderr.write('Error')
        sys.exit(1)
    else:
        sys.stderr.write('OK')
        sys.exit(0)

if __name__ == '__main__':
    check_data()
