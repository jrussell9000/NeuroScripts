#!/usr/bin/env python

import sys
import os
from optparse import OptionParser
from subprocess import Popen, PIPE
from stat import S_IRWXU, S_IRWXG, S_IRWXO
from datetime import datetime
from xml.etree.ElementTree import ElementTree

from file_io import Wimage
from wbl_util import GetTmpSpace, except_msg

AQUALPATH='/apps/noarch/Aqual2/'
#QATOPDIR='/study/QA/MR750_QA'
#QATOPDIR = '/Volumes/home/mri/pub_html'
QATOPDIR = '/home/mri/pub_html'

class RunQa():

    def __init__(self):
        self.GetOptions()

    def GetOptions(self):
        usage = 'qa_all epi_filename t1_filename\n' + \
                'Enter --help for more info.'
        optparser = OptionParser(usage)
        optparser.add_option( "-v", "--verbose", action="store_true", \
                    dest="verbose", help='Print stuff to screen.')
        optparser.add_option( "", "--data-dir", action="store", \
                    dest="data_dir", default=None, \
                    help='Directory containing the data.')
        optparser.add_option( "", "--epi-only", action="store_true", \
                    dest="epi_only", help='Only compute EPI metrics.')
        optparser.add_option( "", "--t1-only", action="store_true", \
                    dest="t1_only", help='Only compute structural metrics.')
        optparser.add_option( "", "--prefix", action="store",  \
                dest="prefix",default=None, type=str, \
                help="Output Directory. Defaults to same path as EPI.")
        opts, args = optparser.parse_args()

        self.data_dir = opts.data_dir
        if len(args) < 1 or len(args) > 2 and self.data_dir is None:
            print usage + '\n'
            sys.exit(1)

        self.epi_only = opts.epi_only
        self.t1_only = opts.t1_only
        self.verbose = opts.verbose
        self.date = datetime.today().strftime('%Y%b%d')
        if opts.prefix is None:
            self.prefix = '%s/qa_%s' % (QATOPDIR, self.date)
        else:
            self.prefix = opts.prefix


        if self.data_dir is not None:
            self.FindData()
        else:
            if len(args) == 1:
                if self.epi_only:
                    self.epifile = os.path.abspath(args[0])
                    self.t1file = None
                elif self.t1_only:
                    self.epifile = None
                    self.t1file = os.path.abspath(args[0])
                else:
                    print usage + '\n'
                    sys.exit()
            else:
                self.epifile = os.path.abspath(args[0])
                self.t1file = os.path.abspath(args[1])

#       Create directory on /tmp
        self.tmp = GetTmpSpace(500)
        self.tmpdir = self.tmp()
        if self.t1file is not None:
            self.ADNI_jpeg = '%s/%s_aqual2.jpeg' % \
                (self.prefix, os.path.basename(self.t1file).replace('.nii',''))
        self.UW_snr = '%s/uwqa_snr.png' % self.prefix
        self.UW_plots = '%s/uwqa_plots.png' % self.prefix

#       Create output directory.
        if os.path.exists(self.prefix):
            cmd = '/bin/rm -r %s' % self.prefix
            output = self.ExecCmd(cmd)
            print output
        os.mkdir(self.prefix)

    def FindData(self):
        """
        Search for EPIs (s*_epi) and T1's  (s*_bravo). This entry is used
        when the program is spawned by upload_data.
        """
        fnames = os.listdir('%s/dicoms' % self.data_dir)
        self.epifile = None
        self.t1file = None
        for fname in fnames:
            if 'epi' in fname:
                self.epifile = '%s/dicoms/%s' % (self.data_dir, fname)
            elif 'bravo' in fname:
                self.t1file = '%s/dicoms/%s' % (self.data_dir, fname)
        if self.epifile is None and self.t1file is None:
            raise RuntimeError('Could not find T1 or EPI data')
        elif  self.epifile is None:
            self.t1_only = True
            self.epi_only = False
        elif  self.t1file is None:
            self.t1_only = False
            self.epi_only = True


    def AdniQa(self):
        """
        Run the ADNI Q/A analyis.
        """
        if  os.path.isdir(self.t1file):
#           Must be a dicom directory.
            tmpfile = '%s/tmp' % self.tmpdir
            cmd = 'convert_file %s %s nii' % (self.t1file, tmpfile)
            output = self.ExecCmd(cmd, ignore_errors=True)
            tmpfile += '.nii'
        else:
            tmpfile = self.t1file

        mfile = '%s/qa_tmp.m' % self.tmpdir
        f = open(mfile, 'w')
        os.chmod(mfile, S_IRWXU | S_IRWXG | S_IRWXO)
        f.write("addpath '%s'\n" % AQUALPATH)
        cmd = "[status, results, phan] = adni_qa('%s', %s, '%s')\n" % (tmpfile, 0, self.prefix)
        f.write(cmd)
        f.write('exit\n')
        f.close()
        cmd = 'cd %s && matlab -nodesktop -nosplash -r %s' % (self.tmpdir, os.path.basename(mfile[:-2]))
        output = self.ExecCmd(cmd, ignore_errors=True)
        print 'ADNI Q/A results written to %s' % self.prefix

    def FbirnQA(self):
        """
        Run the standard FBIRN Q/Q
        """
#       Make sure it's a nifti.
        base = os.path.basename(self.epifile)

#       Create the xcede file.
        self.xcdfile = '%s.xml' % base
        if os.path.exists(self.xcdfile):
            os.remove(self.xcdfile)
#        cmd = 'analyze2bxh --xcede %s %s' % (epinifti, self.xcdfile)
        cmd = 'dicom2bxh --search-for-others --ignore-errors --xcede2 %s/%s.0001 %s ' % (self.epifile, os.path.basename(self.epifile), self.xcdfile)
        output = self.ExecCmd(cmd, ignore_errors=True)
#        print output

#       Do the QA.
        tmpout = '%s/fbirn_qa' % self.tmpdir
        cmd = 'fmriqa_phantomqa.pl %s %s' % (self.xcdfile, tmpout)
        output = self.ExecCmd(cmd, ignore_errors=True)
        print output
        cmd = 'cp %s/* %s' % (tmpout, self.prefix)
        output = self.ExecCmd(cmd)
        print 'FBIRN QA results written to %s' % self.prefix

    def UwQA(self):
        """
        Execute UW Q/A that fits Legendre polynomials.
        """
        if self.epifile is None:
            return
        cmd = 'scanner_qa --legendre-order=5 --skip-frames=4 --prefix=%s/uwqa --write-images %s' % (self.prefix, self.epifile)
        output = self.ExecCmd(cmd, ignore_errors=True)
        print output

    def EditHtml(self):
        """
        Add links to UW and ADNI data in page written by fbirn Q/A procedure.
        """
        f = open('%s/index.html' % self.prefix)
        html_in = f.readlines()
        f.close()

        self.htmlout_file = '%s/qa_%s.html' % (self.prefix, self.date)
        f = open(self.htmlout_file, 'w')
        head_found = False
        title_found = False
        html_out = []
        for line in html_in:
            if 'title' in line and not head_found:
                f.write('<title>QA results %s</title>\n' % self.date)
                head_found = True
            elif '<h1>' in line and not title_found:
#               Insert new stuff here.
                self.WriteNewHtml(f)
                f.write('<h1>FBIRN Q/A results for %s</h1>\n' % self.date)
            else:
                f.write(line)
        f.close()

#       Add a link to the top-level page.
        self.UpdateHtmlIndex()

    def WriteNewHtml(self, f):
        if os.path.exists(self.UW_snr):
            f.write('<h1>UW SFNR and stability results %s</h1>\n' % self.date)
            f.write('<p><img src="%s" /></p>\n\n' % \
                                            os.path.basename(self.UW_snr))
            f.write('<p><img src="%s" /></p>\n\n' % \
                                            os.path.basename(self.UW_plots))
        if os.path.exists(self.ADNI_jpeg):
            f.write('<h1>ADNI Gradient linearity results, %s</h1>\n' % self.date)
            f.write('<p><img src="%s" /></p>\n\n' % self.ADNI_jpeg)

    def UpdateHtmlIndex(self):
        """
        Add a link to new page in top-level page.
        """
        index_html = '%s/index.html' % QATOPDIR
        f = open(index_html, 'r')
        lines = f.readlines()
        f.close()
        base = os.path.basename(self.htmlout_file)
        dname = os.path.dirname(self.htmlout_file).split('/')[-1]
        ref_path = './%s/%s' % (dname, base)

#       Insert link to new data.
        tree = ElementTree()
        tree.parse(self.xcdfile)
        for el in tree.getiterator():
            if 'scandate' in el.attrib.get('name',''):
                scandate = el.text
            elif 'scantime' in el.attrib.get('name',''):
                scantime = el.text
        linkname = '%s at %s' % (scandate, scantime)

#       Rewrite the disk file.
        lines_out = []
        for line in lines:
            if 'Put New Results Here' in line:
                newline = '<li>Data acquired on <a href=%s>%s</a></li>\n' % (ref_path, linkname)
                lines_out.append(newline)
            lines_out.append(line)

        f = open(index_html, 'w')
        f.writelines(lines_out)
        f.close()

    def ExecCmd(self, cmd, ignore_errors=False):
        print cmd
        f = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        output, errs = f.communicate()
#        print 'output: ',output
        if errs: 
            print output
            if not ignore_errors:
                raise RuntimeError(\
                'Error executing commands:\n\t%s\n\tError: %s' % (cmd, errs))
            else:
                sys.stderr.write('%s\n' % errs)
        return output
    
    def CleanUp(self):
        self.tmp.Clean()
#        cmd = '/bin/rm -r %s' % self.tmpdir
#        print cmd
#        print 'Skipping cleanup.'
#        self.ExecCmd(cmd)

def run_all_qa():
    try:
        rq = RunQa()
        if not rq.epi_only:
            rq.AdniQa()
        if not rq.t1_only:
            rq.FbirnQA()
            rq.UwQA()
        rq.EditHtml()
        rq.CleanUp()
        sys.exit(0)
    except (IOError, RuntimeError), errstr:
        sys.stderr.write('%s\n%s\n' % (errstr, except_msg()))
        rq.CleanUp()
        sys.exit(1)


if __name__ == '__main__':
    run_all_qa()
