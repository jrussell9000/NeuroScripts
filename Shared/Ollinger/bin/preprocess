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



import sys
import os
from os import F_OK, R_OK, W_OK
from optparse import OptionParser
from tempfile import mkdtemp
from file_io import Wimage, Header, ispfile, isIfile, \
                abspath_to_relpath, append_history_note, exec_cmd
from wisc_dicom import isdicom, IsDicom
from numpy import zeros
from datetime import datetime
from wbl_util import execCmd, except_msg, send_email, GetTmpSpace, ismounted
import pickle
import yaml
from yaml.scanner import ScannerError
import smtplib
from email.mime.text import MIMEText
import socket
from socket import gethostname
import time
import constants as c
import traceback
from stat import S_IRWXU, S_IRWXG
from bz2 import BZ2File
from temporal_snr import TemporalSnr

#EXAMS_FILE='/study/scanner/preprocessed_exams.txt'
DEFAULT_SKIP=5
ERROR=1
IGNORE=1
OK=0

UMASK_FILE=0113
UMASK_DIR=0002

ZIP_EXCLUDE = \
            '-not \( -name "*.txt" \) ' + \
            '-not  \( -name "*.yaml" \) ' + \
            '-not  \( -name "*.doc" \) ' + \
            '-not  \( -name "*.xls" \) ' + \
            '-not  \( -name "*.ppt" \) ' + \
            '-not  \( -name "*.bsh" \) ' + \
            '-not  \( -name "*.jpg" \) ' + \
            '-not  \( -name "*.png" \) ' + \
            '-not  \( -name "*.pro" \) ' + \
            '-not  \( -name "*.es" \) ' + \
            '-not  \( -name "*.ebs" \) ' + \
            '-not  \( -name "*.pdf" \) ' + \
            '-not  \( -name "*.py" \) ' + \
            '-not  \( -name "*.sta" \) ' + \
            '-not  \( -name "*.m" \) ' + \
            '-not  \( -name "*.exe" \) ' + \
            '-not  \( -name "*.spo" \) ' + \
            '-not  \( -name "*.sav" \) ' + \
            '-not  \( -name "*.1D" \) ' + \
            '-not  \( -name "*.xcl" \) ' + \
            '-not  \( -name "*.pl" \) '

decompress_cmds = {'.gz':'gunzip --to-stdout', '.bz2':'bunzip2 --stdout'}

IMGTYPES = {'efgre3d':'T1High',
            '3dir':'T1High',
            'bravo':'T1High',
            'fse-xl':'T2',
            'frfseopt':'T2',
            'cube':'T2',
            'cubet2':'T2',
            '2dfast':'fmap',
            'epibold':'epi',
            'fcmemp':'T1se',
            'fse':'T2',
            '3-plane':'localizer',
            'epi':'epi',
            'epirt':'epi',
            'epirt_20':'epi',
            'epirt_22':'epi',
            '*epfid2d1_64':'epi',
            'epi2':'dti',
            'dti':'dti',
            'asl':'asl',
            '3dpcasl': 'asl'}


def key_callback(option,opt_str,value,parser):
    """
    Used with optparser for multiple arguments of the same type.
    """
    if "--epi-key" in opt_str:
        parser.values.epi_keys.append(value)
    elif "--exclude" in opt_str:
        parser.values.exclude_paths.append(value)

#*********************************************************************************
def EmailResults(recipient, error_mesg, topdir, dumpfile, logfile, motcor_summary):
#*********************************************************************************
    """
    Email summary of results to user.
    """
    if recipient is None:
        return
    elif 'noname' in recipient:
        return

    sender = 'preprocess'

    if 'Abnormal' in error_mesg > 0:
        subject = 'Problem while preprocessing %s' % topdir
    else:
        subject = 'Preprocessing complete for %s' % topdir
    mssg = error_mesg

    if logfile is not None and isinstance(logfile, str):
        f = open(logfile, 'r')
        lines = f.readlines()
        f.close()
        logged_errors = ''
        for i in xrange(len(lines)):
            if 'rror' in lines[i]:
                mssg += ''.join(lines[i-1:])
                break
    mssg += motcor_summary

    if dumpfile is not None:
        f = open(dumpfile,'r')
        mssg += '\nSummary of processing:\n'
        mssg += f.read()
        f.close()

    send_email(recipient, subject, mssg, sender)


#***********************
def hms_to_secs(hms_in):
#***********************

#   Converts time in the string format of hh:mm:ss to seconds since midnight.
    hms = hms_in.split(':')
    return float(hms[2]) + 60.*(float(hms[1]) + 60.*float(hms[0]))

class EmptyOptions():
    def __init__(self):
        self.debug_tmp = False
        self.outdir = None
        self.align_fmaps = False
        self.no_align_fmaps = False
        self.skull_strip = False
        self.keep_epi_raw = False
        self.keep_epi_mot = False
        self.fake_opts = True
        self.epi_keys = {}
        self.exclude_paths = []
        self.clean_epi = False

class DataInfo(object):

    def __init__(self,topdir, redo=False, verbose=False, dry_run=False, \
                 skip=None, scratch='/scratch', no_email=False, \
                 template_file=None):

#       Get the version of the software.
        try:
            f = open(c.FMRI_TOOLS_VERSION_FILE,'r')
            self.version = f.read().strip()
            f.close()
        except IOError:
            self.version = '0.0.0'
        self.scratch = scratch
        self.user_scratch_dir = "%s/%s-preprocess" % (
            self.scratch, os.getenv('USER'))
        self.no_email = no_email
        self.prog = os.path.basename(sys.argv[0])[:-3].strip()
        self.verstring = "\n%s: version %s\n\n" % (self.prog, self.version)
        if self.prog == 'preprocess':
            print self.verstring
        self.anatref_entry = None
        self.ntype = {}
        self.tmplt = None
        self.template_file = template_file

        self.info = {}
        self.fmaps = {}
        self.pfiles = []
        self.epirt_paths = []
        self.refdats = {}
        self.epi_series = []
        self.pfiles_recon = []
        self.topdir = os.path.abspath(topdir)
        self.logdir = None
        self.verbose = verbose
        self.anatomical = None
#        self.anat_ref = None
        self.n_epi = 1
        self.epi_info = {}
        self.found_data = False
        self.visited_dirs = set()
        self.errors = False

#       Get options.
        if not hasattr(self, 'opts'):
            self.opts = EmptyOptions()
        else:
            self.opts.fake_opts = False

#       Create temporary directory.
        if self.opts.debug_tmp:
            self.tmpdir = '/tmp/debug_tmp'
            self.MakeDir(self.tmpdir)
        else:
            self.tmp = GetTmpSpace(1000)
            self.tmpdir = self.tmp()

#       Fix stupid matplotlib dependency.
        os.unsetenv('MPLCONFIGDIR')
        matplot_tmpdir = '%s/.matplotlib' % self.tmpdir
        os.putenv('MPLCONFIGDIR', matplot_tmpdir)
        if hasattr(self, 'MakeDir'):
            self.MakeDir(matplot_tmpdir)

#       Check paths to be excluded.
        self.exclude_paths = []
        for path in self.opts.exclude_paths:
            apath = os.path.abspath(path)
            if os.path.exists(apath):
                self.exclude_paths.append(os.path.abspath(path))
            else:
                sys.stderr.write('\n*** Nonexistent path specified in --exclude argument.\n***Invalid path: %s\n***Aborting ...\n' % apath)
                self.term_mesg = '\nAbnormal termination.\n'
                self.CleanUp()
        self._ProcessTemplate(self.topdir)

#       Check for keywords defining which epis to reconstruct.
        self.epi_keys = {}
        for keyword in self.opts.epi_keys:
            wds = keyword.split(':')
            self.epi_keys[wds[0]] = wds[1]

#       Table mapping image types to entries in the master info table.
        self.entry_map = {'epi':[], 'anat':[], 'fmap':[], 'dti':[], \
                          'first_epi':[], 'asl':[]}
        self.imgtype = IMGTYPES
        self.GetInfoMethods = {\
                    'T1High': self._AnatInfo, \
                    'T2': self._AnatInfo, \
                    'fse': self._AnatInfo, \
                    'T1se': self._AnatInfo, \
                    'fmap': self._FmapInfo, \
                    'dti': self._DtiInfo, \
                    'epi': self._EpiInfo, \
                    'asl': self._AslInfo}
        self.anat_types = ['T1High', 'T2', 'T1se', 'fse']
        self.suffix = {\
                    'brik':'+orig.BRIK', \
                    'nii':'.nii', \
                    'n+1':'.nii', \
                    'ni1':'.hdr', \
                    'ana':'.hdr'}
        self.infile_suffix = {\
                    'brik':'+orig', \
                    'nii':'.nii', \
                    'n+1':'nii'}


    def FindStuffToDo(self):
        """
        Walk through directories and categorize the data. This method builds
        the "info" attribute - a dictionary that characterizes each data
        series and defines the options and input/output file-names for each
        stage of processing.
        """

        while self.topdir.endswith('/'):
            self.topdir = self.topdir[:-1]
        if hasattr(self, 'LogProcess'):
            self.LogProcess()

#       Look for data to process.
        self.WalkPath(self.topdir)
        if os.path.islink('%s/anatomicals' % self.topdir):
#           os.walk won't follow links, so do this one manually.
            if not os.path.exists('%s/dicoms' % self.topdir):
#               Don't do a duplicate search.
                pathname = os.readlink('%s/anatomicals' % self.topdir)
                self.WalkPath(pathname)

#       Pair-up fieldmaps with EPI's
        self._SetFmapInfo()

#       Pair fieldmaps with strucural images.
        self._SetAnatTgts()

#       Assocate a ref.dat file with each EPI.
        self._GetRefdat()

        self._MakeEpiScratchDir()

#       Order the EPIs so the names are correct.
        self._GetEpiOrder()

#       Associate each EPI with an anatomical, determine if it was
#       acquired before or after the epi
        self._SetBaseEpi()

        self.motcor_summary = self.SummarizeMotionTargets()
        f = open('%s/motion_corr.txt' % self.logdir, 'w')
        f.write(self.motcor_summary)
        f.close()
        if self.verbose:
            print self.motcor_summary


    def MakeDir(self, dirname):
        """ Create directory or exit on error. """
        if os.path.exists(dirname):
            return
        try:
            os.umask(UMASK_DIR)
            os.makedirs(dirname)
        except OSError:
            self.errors = True
            errstr = '\nCould not create directory: %s ... ' % dirname
            self.LogErrors(errstr)
            raise OSError(errstr)
        os.umask(UMASK_FILE)


    def Gunzip(self, pathname):
        cmd = "gunzip -rfq %s" % pathname
        try:
            execCmd(cmd)
        except RuntimeError:
            self.errors = True
            errstr = "%s\nCould not unzip data files in %s" % (cmd, pathname) +\
                     "\nChange permissions and rerun the script."
            raise RuntimeError(errstr)

    def Gzip(self, pathname):
        cmd = 'find %s -type f %s' % (pathname, ZIP_EXCLUDE)
        try:
            print 'Gzip starting time: %s' % time.strftime('%H:%M:%S')
            execCmd(cmd)
            print 'Gzip ending time: %s' % time.strftime('%H:%M:%S')
        except RuntimeError:
            self.errors = True
            print 'Gzip ending time: %s' % time.strftime('%H:%M:%S')
            errstr = "Could not gzip data files in %s" % pathname + \
                     "Change permissions and compress by hand."
#           Don't call this a fatal error.
            sys.stderr.write('%s\n' % errstr)
            raise RuntimeError(errstr)

    def CheckCompression(self, filename):
        if filename.endswith('.gz'):
            fname = filename[:-3]
            compression = '.gz'
        elif filename.endswith('.bz2'):
            fname = filename[:-4]
            compression = '.bz2'
        else:
            fname = filename
            compression = None
        return (fname, compression)


    def WalkPath(self, pathname):
        "Check subdirectories of topdir for data we can process."""
        pfile_basenames = []
        self.n_t1low = 1
        self.n_t1high = 1
        followed_links = {}
        for root, dnames, fnames in os.walk(pathname, topdown=True):
            bname = os.path.basename(root)
            if bname == 'anatomicals' and 'dicoms' in dnames:
#               Don't check twice.
                continue
            # Ensure we never parse the same directory twice
            idx = 0
            for dname in dnames:
                full_dname = '%s/%s' % (root, dname)
                if os.path.islink(full_dname):
#                   Edit directories so links will be followed (once).
                    linked_path = os.readlink(full_dname)
                    if not followed_links.has_key(linked_path):
                        followed_links[linked_path] = True
                        dnames[idx] = linked_path
                idx += 1
            real_root = os.path.realpath(root)
            if real_root in self.visited_dirs:
                continue
            self.visited_dirs.add(real_root)

            self.current_entry = real_root
            if self.current_entry.endswith('.yaml'):
                self.current_entry = os.path.dirname(self.current_entry)
            if real_root.startswith(pathname + '/orig') or \
                                os.path.basename(real_root) == 'cardiac':
                continue
            if self.verbose:
                sys.stdout.write('Checking %s ...\n' % real_root)
                sys.stdout.flush()
            if IsDicom(real_root)():
                fnames = [real_root]
                isdicom = True
            else:
                isdicom = False
            if len(fnames) > 1:
                dirname, filename = self._yaml_filename(real_root)
#                                            os.path.dirname(fnames[0]))
                fullpath = '%s/%s' % (dirname, filename)
                if os.path.exists(fullpath):
                    fnames = [filename] + fnames
            for fname in fnames:
                if fname.startswith('raw'):
#                   Ignore yaml files in p-file directories
                    fnames.remove(fname)
                elif fname.endswith('.yaml'):
#                   Move yaml file to the beginning of the list.
                    fnames.remove(fname)
                    fnames = [fname] + fnames
            for name in fnames:
                fname, compression = self.CheckCompression(name)
                if isdicom:
                    fullpath = name
                else:
                    fullpath = os.path.abspath('%s/%s' % (real_root,name))

#               Check if file is in an excluded directory.
                exclude = False
                for expath in self.exclude_paths:
                    if fullpath.startswith(expath):
                        exclude = True
                        sys.stdout.write('*** Excluding data: %s\n' % \
                                                                fullpath)
                        break
                if exclude:
                    break

                if not os.path.isdir(fullpath) and os.path.exists(fullpath) and\
                   not os.path.basename(fullpath) in pfile_basenames or isdicom:
#                   Interrogate header of file specified by fullpath.
                    info = self._GetImageInfo(fullpath)
                    if info != None:
                        if info['type'] == 'refdat':
                            continue
                        elif info['type'] == 'break':
                            break
                        info['compression'] = compression
                        info['pfile_decomp'] = '%s/%s' % (real_root, fname)
                        self.found_data = True
                        if info['type'] == 'localizer':
                            break
                        elif info['data_filetype'] == 'ge_data':
                            self.info[fullpath] = info
                            pfile_basenames.append(os.path.basename(fullpath))
                        elif os.path.isdir(real_root):
                            self.info[real_root] = info
                        else:
                            self.info[os.path.dirname(real_root)] = info
                        if info['data_filetype'] == 'dicom' or \
                           info['data_filetype'] == 'ge_ifile':
#                           Only look at one header per series or run.
                            break

#       Prune duplicate p-files.
        pfiles = {}
        for fname in self.pfiles:
#           Non-unique entries will be overwritten.
            pfiles[os.path.basename(fname)] = fname
        self.pfiles = pfiles.values()

    def _FindTemplateFile(self, topdir):
        """
        Fill in a heirarcy of template files.  The default template file is
        first loaded. Then entries are overwritten by entries in the study-level
        template (in the directory containing each subject-level directories).
        Finally, entries in the subject-level template are loaded.
        """
        if topdir.endswith('..'):
            topdir = '/'.join(topdir.split('/')[:-2])
        fnames = os.listdir(topdir)
        for fname in fnames:
            filename = '%s/%s' % (topdir, fname)
            if filename.endswith('.yaml') and not os.path.isdir(filename) and \
                                                    os.path.exists(filename):
                f = open(filename, 'r')
                magic_code = f.read(22)
                f.close()
                if '#!fmri_file_template' in magic_code:
                    return filename
        return None

    def _LoadTemplate(self,fname):
        """
        Read a single template file and return the resulting dict object.
        """
        f = open(fname, 'r')
        lines = f.readlines()
        data = ''
        for line in lines:
            if not line.startswith('---'):
                data += line
        data = data.replace('\t','    ')
        if '\t' in data:
            errstr = \
            'Illegal tabs encountered in template file. Use spaces instead.'
            raise ScannerError(errstr)
            proc.LogErrors(errstr)
        tmplt = yaml.load(data)
        f.close()
        return tmplt

    def _GetTemplate(self):
        """
        Load the hierarchy of templates.
        """
#       First read default template.
        tmplt = self._LoadTemplate(c.preproc_template_default)
        tmplt['proc'] = self.topdir
        self.template_type = 'default'

        self.templates = []
        if self.template_file is not None:
            tmplt.update(self._LoadTemplate(self.template_file))
            self.template_type = 'command-line'
            self.templates.append(os.path.abspath(self.template_file))
            found_template = True
        else:
#           Find a study specific template file.
            study_template_file = self._FindTemplateFile('%s/..' % self.topdir)
            if study_template_file is not None:
#               Merge study template into default, study template has precedence.
                if self.verbose:
                    print "Using study template at " + study_template_file
                tmplt.update(self._LoadTemplate(study_template_file))
                self.template_type = 'study-specific'
                self.templates.append(os.path.abspath(study_template_file))
                found_template = True
            else:
                found_template = False
#           Now look for a subject-specific template file.
            subject_template_file = self._FindTemplateFile('%s' % self.topdir)
            if subject_template_file is not None:
#               Merge subject template, subject template has precedence.
                if self.verbose:
                    print "Using subject-specific template at %s" % \
                                                        subject_template_file
                tmplt.update(self._LoadTemplate(subject_template_file))
                self.template_type = 'study-specific'
                self.templates.append(os.path.abspath(subject_template_file))
                found_template = True

        if not found_template:
            raise RuntimeError('Could not find template file.')

        if tmplt.get('subject','same') == 'same':
#           Default subdirectory is same as data directory.
            tmplt['subject'] = self.topdir.split('/')[-1]
        else:
            if not isinstance(tmplt['subject'],str):
                errstr = 'preprocess: Invalid subject number. Be sure to ' + \
                         'enclose the subject number item with double quotes.'
                raise RuntimeError(errstr)

#       Keys that apply to all EPIs.
        self.fsl_flip = tmplt.get('fsl_flip', False)
        if self.fsl_flip:
            self.flip_opts = '-LT'
        else:
            self.flip_opts = ''

#       Replace strings with python types.
        for key in tmplt.keys():
            if tmplt[key] == 'None':
                tmplt[key] = None
            elif key == 'True':
                tmplt[key] = True
            elif key == 'False':
                tmplt[key] = False
        return tmplt

    def _ProcessTemplate(self,topdir):
        """
        Process the data in the templates and set attributes accordingly.
        """
        self.dicomdir = "%s/anatomicals" % self.topdir
        self.rawdir = "%s/raw" % topdir
        self.rawdirs = {}
        tmplt = self._GetTemplate()
        if self.opts.outdir is not None:
#           Override template output directory.
            tmplt['top_outdir'] = self.opts.outdir
        self.tmplt = tmplt
        if len(tmplt['top_outdir']) == 0:
            tmplt['top_outdir'] = os.path.realpath(self.topdir)
            raise RuntimeError('Template file must specify an output directory.')
        tmplt['top_outdir'] = os.path.realpath(tmplt['top_outdir'])
        if '/home' in tmplt['top_outdir'][:7]:
            raise RuntimeError('Image data cannot be stored in the /home partition. Change the "top_outdir" entry in the template file: %s.' % (' '.join(self.templates)))
#            tmplt['subject'] = 'orig'
        self.procdir = os.path.abspath("%s/%s" % \
                            (tmplt['top_outdir'],tmplt['subject']))
        target = os.path.abspath('%s/../..' % tmplt['top_outdir'])
        if not ismounted(target):
            raise RuntimeError('Could not access partition at %s' % target)

        self.anatdir = "%s/anat" % self.procdir
        self.fmapdir = "%s/%s" % (self.procdir,tmplt['fmap']['outdir'])
        self.dtidir = "%s/%s" % (self.procdir,tmplt['dti']['outdir'])
        self.logdir = "%s/%s" % (self.procdir,tmplt['logdir'])
        self.skip = tmplt.get('skip', DEFAULT_SKIP)
        self.acq_tr = tmplt.get('acq_tr',None)
        self.episetup_dir = "%s/%s" % (self.procdir,tmplt['first_epi'])
        self.fsl_cmpblty = tmplt.get('fsl_compatibility',False)
        self.epi_file_format = self.tmplt['epi_file_format']
        self.censor_thresh = tmplt.get('censor_threshold', 2.)
        self.censor_interleave = tmplt.get('censor_interleave', True)
#        self.server_userid = self.tmplt.get('server_userid','default')

#       Overide flags for aligning EPIs and skull-stripping with command-
#       line options.
        if self.opts.align_fmaps:
            self.align_fmaps = True
        else:
            self.align_fmaps = self.tmplt.get('epi_align', False)

        if self.opts.no_align_fmaps:
            self.no_align_fmaps = True
        else:
            self.no_align_fmaps = self.tmplt.get('no_epi_align', False)

        if self.opts.skull_strip:
            self.skull_strip = True
        else:
            self.skull_strip = self.tmplt.get('skull_strip', False)

#       Create log file now so it can be used immediately.
        if not os.path.exists(self.logdir):
            if self.verbose:
                print 'mkdir %s' % self.logdir
            if not self.opts.fake_opts:
                self.MakeDir(self.logdir)

        self._ProcessTemplateEpiInfo()

    def _CheckForEmbeddedBlanks(string):
        if ' ' in string[1:-1]:
#           Embedded blank in filename. Missing comma?
            errstr = 'preprocess: Embedded blank in file name. Be sure '+\
            'that each file in the list is delimited by a comma.\n'
            raise RuntimeError(errstr)
#

    def _ProcessTemplateEpiInfo(self):
#       Extract EPI groups and setup data structures used for sorting.
        self.epidirs = []
        epi_info = {}
        keys = self.tmplt.keys()
#       Move epidir_dflt key to the end.
        keys.remove('epidir_dflt')
        keys = keys + ['epidir_dflt']
        nepi_keys = 0
        acq_orders = []
        for key in self.tmplt.keys():
            item = self.tmplt[key]
            if key == 'epidir_dflt':
#               Make sure this is always ordered last.
                self.tmplt[key]['acq_order'] = 1000
                if nepi_keys > 0:
#                   Don't process if there are explicitly definied epis.
                    continue
#           For each group of epis, create a list containing an index to the
#           next name to be used and the orientation.
            if isinstance(item, dict):
                if not item.get('type','') == 'epi':
                    continue
                nepi_keys += 1
                epidir = '%s/%s' % (self.procdir, item['outdir'])
                if epidir not in self.epidirs:
                    self.epidirs.append(epidir)
                plane = item.get('plane','any')
                acq_order = item.get('acq_order',0)
#                if epi_info.has_key(acq_order) and key != 'epidir_dflt':
                if acq_order in acq_orders:
                    if key != 'epidir_dflt':
                        raise RuntimeError(self.template_type + \
                                ' template has non-unique values of acq_order')
                elif epi_info.has_key(acq_order):
#                   Overwrite lower-priority template file.
                    del epi_info[acq_order]
                acq_orders.append(acq_order)
                epi_info[acq_order] = {'tmplt_key':key, \
                                       'plane':plane, \
                                       'subdir':[], \
                                       'names':[]}
                for name in  item['names']:
                    epi_info[acq_order]['names'].append(\
                                            '%s/%s' % (epidir, name))
                    epi_info[acq_order]['subdir'].append(item['outdir'])
                epi_tmpdir = '%s/%s' % (self.tmpdir, item['outdir'])
                if epi_tmpdir not in self.epidirs:
                    self.epidirs.append(epi_tmpdir)

#       Delete duplicate names, sort, and create final list.
        epi_acqs = epi_info.keys()
        epi_acqs.sort()
        self.epinames = {}
        for acq in epi_acqs:
            if len(epi_acqs) > 1 and \
                epi_info[acq]['tmplt_key'] == 'epidir_dflt':
#               Delete epi group in default template if others were supplied.
                continue
            plane = epi_info[acq]['plane']
            if not self.epinames.has_key(plane):
                self.epinames[plane] = \
                            {'n_epi':0, 'names':[], 'anat_ref':[],'subdir':[]}
            self.epinames[plane]['names'] += epi_info[acq]['names']
            self.epinames[plane]['subdir'] += epi_info[acq]['subdir']

    def _yaml_filename(self, path):
        """
        Synthesize yaml header filename from directory name.
        """
        fullpath = os.path.abspath(path)
        if not os.path.isdir(fullpath):
            dirname = os.path.dirname(fullpath)
        else:
            dirname = path
        if dirname.endswith('/'):
            dirname = dirname[:-1]
        fname = dirname.split('/')[-1] + '.yaml'
        return dirname, fname

    def _FmapInfo(self, info, path):
        if not os.path.isdir(path):
            pathdir = os.path.dirname(path)
        else:
            pathdir = path
        fnames = os.listdir(pathdir)
#        if len(fnames) < 8*self.hdr['zdim']:
        err = False
        if self.hdr['native_header'].has_key('EchoTimes'):
            if self.hdr['native_header']['EchoTimes'] < 2:
                err = True
        else:
            if len(fnames) < 8*self.hdr['zdim']:
                err = True
        if err:
            errstr = "\n*** Fieldmap data are incomplete: %s ***\n\n" % path
            self.LogErrors(errstr)
            return ERROR

        info['outdir'] = '%s/%s' % (self.procdir, self.tmplt['fmap']['outdir'])
        info['imgfile'] = '%s/fmap_%s' % (info['outdir'],info['plane'].strip())
        info['imgfile_r'] = '%s_r' % info['imgfile']
        info['magfile'] = '%s_mag' % info['imgfile']
        info['magfile_r'] = '%s_mag_r' % info['imgfile']
        info['filetype'] = 'nii'
        info['echo_spacing'] = self.tmplt['fmap']['echo_spacing']
        info['correct_fmap_phase'] = self.tmplt['correct_fmap_phase']
        info['matfile'] = '%s_matfile.aff12.1D' % info['imgfile']
        info['matfile_unitary'] = '%s_matfile_unitary.aff12.1D' % info['imgfile']
        self.fmaps[pathdir] = info['imgfile']
        self.entry_map['fmap'].append(self.current_entry)
        return OK

    def _AnatInfo(self, info, path):
        """ Get T1 and T2 weighted structural image info."""
        if info['data_filetype'] == 'ge_data':
            return ERROR
        outdir = '%s/%s' % (self.procdir, self.tmplt['anat']['outdir'])
        info['InversionTime'] = self.hdr['native_header']['InversionTime']

        if info['psdname'] == 'efgre3d' or info['psdname'] == 'bravo':
#           Structural scans are 3d inversion-recovery.
            if self.hdr['native_header']['InversionTime'] < 1.:
#           Only inversion recovery used for anatomy.  Must be calibration.
                return None
            elif self.hdr['zsize'] > 1.25:
#               Only one slab acquired. Assume thick slices.
                name = 'T1Low_%d' % self.n_t1low
                self.n_t1low += 1
            else:
                if self.n_t1high == 0:
                    name = 'T1High'
                else:
                    name = 'T1High_%d' % self.n_t1high
                self.n_t1high += 1
        else:
            psdname = info['psdname']
            name = self.imgtype.get(psdname, info['psdname'])
            if self.ntype.has_key(psdname):
                self.ntype[psdname] += 1
                name = '%s_%0d' % (name, self.ntype[psdname])
            else:
                self.ntype[psdname] = 1
        info['norm_src'] = False
        info['outdir'] = outdir
        info['filetype'] = self.tmplt['anat']['format']
        info['imgfile'] = '%s/%s' % (info['outdir'], name)

        self.entry_map['anat'].append(self.current_entry)
        return OK

    def _DtiInfo(self, info, path):
        info['outdir'] = '%s/%s' %(self.procdir, self.tmplt['dti']['outdir'])
        info['filetype'] = self.tmplt['dti']['format']
        info['pepolar'] = self.tmplt['dti']['pepolar']
        info['imgfile'] = '%s/s%s_dti_%0ddir' % \
                            (info['outdir'],info['series'], info['tdim']-1)
        self.entry_map['dti'].append(self.current_entry)
        return OK

    def _AslInfo(self, info, path):
        info['outdir'] = '%s/%s' %(self.procdir, self.tmplt['asl']['outdir'])
        info['filetype'] = self.tmplt['asl']['format']
        info['imgfile'] = '%s/s%s_asl' % (info['outdir'],info['series'])
        self.entry_map['asl'].append(self.current_entry)

    def _NoInfo(self, info, path):
        if info['type'] is None:
            return
        else:
            errstr = 'Invalid "type" specified.\ninfo: %s\n\n' % info['type']
            self.LogErrors(errstr)
            raise RuntimeError(errstr)
        return OK

    def _EpiInfo(self, info, path):
        """
        Create list of epis in pfile format (epi_series) and of
        epis in dicom format (epirt_paths)
        """

        epi_vals = {'tdim':self.hdr['tdim'], 'plane':self.hdr['plane'], \
                    'SeriesNumber':self.hdr['subhdr']['SeriesNumber']}
        for key in self.epi_keys.keys():
            if self.epi_keys[key] != str(epi_vals[key]):
#               Return None, which will cause these data to be ignored.
                return None

#       Early versions of the EPIC software saved p-files for the setup epis.
#       Don't process these (or any epi with fewer than eight useable frames).
        if self.hdr['tdim'] < (8 + self.skip):
            return None

        info['slice_order'] = self.shdr.get('SliceOrder', 'altplus')
        if self.shdr['EffEchoSpacing'] is not None:
            info['echo_spacing'] = self.shdr['EffEchoSpacing']/1000.
        else:
            info['echo_spacing'] = 0.
        if info['data_filetype'] == 'dicom':
#           Entry is name of dirctory for dicom images.
            if not os.path.isdir(path):
                entry = os.path.dirname(path)
            else:
                entry = path
        else:
#           Otherwise it is the name of a directory containing p-files.
            entry = path

        if info['data_filetype'] == 'ge_data' and info['type'] is not None:
#           Found a pfile. Add it to the list.
            if entry not in self.pfiles and info['tdim'] > 2:
                self.pfiles.append(entry)
                self.entry_map['epi'].append(entry)
            if info['series']  not in self.epi_series:
                self.epi_series.append(info['series'])
        elif info['data_filetype'] == 'dicom' and \
                info['psdname'] == 'epibold':
#           This is the initial EPI done during setup.
            info['outdir'] = self.episetup_dir
            info['type'] = 'first_epi'
            self.entry_map['first_epi'].append(entry)
            info['imgfile'] = '%s/first_epi_%d' % \
                        (self.episetup_dir, len(self.entry_map['first_epi']))
        elif ('epirt' in info['psdname'] or info['psdname'] == 'epi' or \
              info['psdname'] == '*epfid2d1_64')  and info['tdim'] > 2:
#           This is an epi reconstructed on the scanner.
            self.epi_series.append(info['series'])
            self.entry_map['epi'].append(entry)
            if not os.path.isdir(path):
                tmp_path = os.path.dirname(path)
            else:
                tmp_path = path
            self.epirt_paths.append(tmp_path)

        if self.fsl_flip:
            info['filetype'] = 'brik'
        else:
            info['filetype'] = self.tmplt['epi_file_format']

        info['TR'] = self.hdr['tsize']
        if self.tmplt['acq_tr'] is None:
            info['acq_tr'] = float(info['TR'])
        else:
            info['acq_tr'] = float(self.tmplt['acq_tr'])
        return OK

    def _GetImageInfo(self,path):
        """
        Read the header from the raw data specified by "path" and use this
        information combined with the template information to generate the
        "info" dict object.  This object defines the options and paths for
        each operation.
        """
        hd = Header(path, scan=True)
        hdr = hd.hdr
        self.hdr = hdr
        if hdr is None:
#           Either a ref.dat file or it isn't an imaging file.
            if 'ref' in path and 'dat' in path:
                self.refdats[os.path.realpath(path)] = True
                info = {'type':'refdat'}
                return info
            else:
                return None
        elif hdr['filetype'] == 'dicom' and not path.endswith('.yaml'):
#           Write a yaml file to the raw data directory if possible.
            dirname, outfile = self._yaml_filename(path)
            yaml_name = '%s/%s' % (dirname, outfile)
            if not os.path.exists(yaml_name):
#               Create yaml file using dirname,
#               e.g., ../anatomicals/S2_EFGRE3D/s2_efgre3d.yaml
                try:
                    hd.write_hdr_to_yaml('%s/%s' % (dirname,outfile))
                except IOError:
#                   This is a nonessential function, so ignore exceptions
#                   such as access violations.
                    pass
        elif hdr['filetype'] == 'dicom' or hdr['filetype'] == 'ge_ifile':
            if not os.path.isdir(path):
                path = os.path.dirname(path)
        shdr = hdr['subhdr']
        nhdr = hdr['native_header']
        self.shdr = shdr
        if 'dti' in shdr.get('PulseSequenceName','').lower() \
        or 'dti' in nhdr.get('PulseSequenceFile',''):
            psdname = 'dti'
        else:
            psdname = os.path.basename((shdr.get('PulseSequenceName','').strip()).lower())
        info = {'psdname':psdname, \
             'acqtime':shdr['AcqTime'], \
             'series':int(shdr['SeriesNumber']), \
             'plane':hdr['plane'].strip(), \
             'type':self.imgtype.get(psdname,None), \
             'plane':hdr['plane'], \
             'acqtime':shdr['SeriesTime'], \
#             'fmapdir':None, \
             'refdat':None, \
             'imgfile':None, \
             'base':None, \
             'tdim':int(hdr['tdim']), \
             'echo_spacing':None, \
             'filetype':'brik', \
             'suffix':self.suffix.get(hdr['filetype'], 'brik'), \
             'data_filetype':hdr['filetype']}
        if info['type'] == 'localizer':
#           Don't process the localizer.
            return info
        if isinstance(info['acqtime'], int):
            info['acquisition_time'] = time.ctime(info['acqtime'])
        if nhdr.get('ImageFormat',('unknown'))[0] == 'DERIVED' and info['type'] == 'epi':
#           Sometimes screenshots are defined as epis.
            info['type'] = None

#       Call the method appropriate to the type of scan in this series.
        stat = apply( self.GetInfoMethods.get(info['type'], self._NoInfo), \
                                                            [info, path])
        if stat:
            info = {'type':'break'}
            return info
        info['suffix'] = self.suffix.get(info['filetype'], 'brik')
        return info

    def StripSuffix(self, fname):
        outfile = fname.replace('.nii', '')
        outfile = outfile.replace('.BRIK','')
        outfile = outfile.replace('.HEAD','')
        return outfile.replace('+orig','')

    def _SetFmapInfo(self):
        """
        Pair up each epi with a fieldmap.
        """
        for epi in self.pfiles + self.epirt_paths:
            self.info[epi]['fmapname'] = None
            self.info[epi]['fmap_entry'] = None
            for entry in self.entry_map['fmap']:
                fmap_name = self.info[entry]['imgfile'] + self.info[entry]['suffix']
                if self.info[entry]['plane'] == self.info[epi]['plane']:
#                   Use the fieldmap acquired at the same plane.
                    self.info[epi]['fmapname'] = fmap_name
                    self.info[epi]['fmap_entry'] = entry
                    break
            else:
#                for fmap in self.fmaps.keys():
                for entry in self.entry_map['fmap']:
#                   No fmap at same orientation, look for fmaps in other planes.
#                   There won't be more than one, so it isn't much of a choice.
                    fmap_name = self.info[entry]['imgfile'] + \
                                                    self.info[entry]['suffix']
                    if self.info[entry]['plane'] == 'sagittal':
                        self.info[epi]['fmapname'] = fmap_name
                        self.info[epi]['fmap_entry'] = entry
                        break
                    elif self.info[entry]['plane'] == 'axial':
                        self.info[epi]['fmapname'] = fmap_name
                        self.info[epi]['fmap_entry'] = entry
                        break
                    elif self.info[entry]['plane'] == 'coronal':
                        self.info[epi]['fmapname'] = fmap_name
                        self.info[epi]['fmap_entry'] = entry
                        break
                    elif self.info[entry]['plane'] == 'oblique':
                        self.info[epi]['fmapname'] = fmap_name
                        self.info[epi]['fmap_entry'] = entry
                        self.info[epi]['plane'] = 'oblique'
                        break

    def _FindNearestAnat(self, acqtime):
        """
        Find the hi-res structural image that was acquired nearest to "acqtime"
        """
        tdiff_min = 1e6
        for anat in self.entry_map['anat']:
            if self.info[anat]['type'] == 'T1High' and \
                            self.info[anat]['InversionTime'] > 0.:
                tdiff = abs(acqtime - self.info[anat]['acqtime'])
                if tdiff < tdiff_min:
                    tdiff_min = tdiff
                    anat_min = anat
        return anat_min

    def _SetAnatTgts(self):
        """
        Create structures defining acquisition time for fieldmaps and
        anatomicals. First find the fieldmap (or hi-res structural if no
        fieldmap was collected) nearest (on average) to the epis.  Then
        define this series as the one that should be in register with the epis.
        """
        anat_candidates = {}
        fmap_candidates = {}
        for entry in self.entry_map['anat']:
            if self.info[entry]['type'] == 'T1High':
                anat_candidates[entry] = self.info[entry]['acqtime']

#       Find the valid anatomical acquired nearest to fieldmap.
        tdiff_min = 1e6
        if len(self.entry_map['fmap']) > 0:
            for entry in self.entry_map['fmap']:
                anat_tgt = self. _FindNearestAnat(self.info[entry]['acqtime'])
                self.info[entry]['anat_ref'] = anat_tgt
        else:
#           No fieldmaps were collected. Find the structural nearest the
#           beginning of the EPIs.
            if len(self.entry_map['anat']) == 1:
                anat_tgt = self.entry_map['anat'][0]
            else:
                epi_start = []
                tmin = 1e6
                for anat in self.entry_map['anat']:
                    if self.info[anat]['type'] != 'T1High':
                        continue
                    tsum1 = 0; tsum2 = 0;
                    for epi in self.entry_map['epi']:
#                       Difference from start of structural and first epi
                        tsum1 += abs(self.info[anat]['acqtime'] - \
                                                        self.info[epi]['acqtime'])
#                       Difference from start of structural and last epi
                        tsum2 += abs(self.info[anat]['acqtime'] - \
                                (self.info[epi]['acqtime'] +\
                                 self.info[epi]['TR']*self.info[epi]['tdim']))
                    if tsum1 < tmin or tsum2 < tmin:
                        tmin = min(tsum1, tsum2)
                        anat_tgt = anat

#       Resolve anatomical names and links.
        self._SetAnatNames(anat_tgt)

#       Set appropriate attributes in the entry for each EPI.
        for epi in self.entry_map['epi']:
            if  len(self.entry_map['fmap']) > 0 and not self.no_fmapcorr:
                fmap_entry = self.info[epi]['fmap_entry']
                anat_ref = self.info[fmap_entry]['anat_ref']
                self.info[epi]['anat_tgt'] = fmap_entry
                self.info[epi]['anat_matfile'] = self.info[fmap_entry]['matfile']
                if self.align_fmaps or (not self.no_align_fmaps and \
                            self._SetCatMotionFmapMats(fmap_entry, anat_ref)):
#                   Concatenate motion-correction matrices with tranform from
#                   fieldmap to structural.  Use the registered fieldmap.
                    self.info[epi]['catmats'] = True
                    fmap_info = self.info[self.info[epi]['fmap_entry']]
                    self.info[epi]['fmapname'] = \
                            fmap_info['imgfile_r'] + fmap_info['suffix']
                else:
#                   Assume fieldmap is in register with the structural.
                    self.info[epi]['catmats'] = False
            else:
                self.info[epi]['anat_tgt'] = anat_tgt
                self.info[epi]['anat_matfile'] = None
                self.info[epi]['catmats'] = False
            self.info[epi]['anat_link'] = self.info[anat_tgt]['imgfile'] + \
                                           self.info[anat_tgt]['suffix']

    def _SetAnatNames(self, anat_tgt):
        """
        Resolve anatomical names and links.
        anat_tgt: entry corresponding to the anatomical that is the source
        image for spatial normalization.
        """
#       Define links to structural image in each output directory.
        for entry in self.entry_map['epi'] + self.entry_map['fmap'] + \
                        self.entry_map['dti'] + self.entry_map['asl']:
            self.info[entry]['anat_link'] = anat_tgt

#       Name the normalization source image T1High. Number the rest.
        anat_entries = self.entry_map['anat'][:]
        anat_entries.remove(anat_tgt)
        n_t1high = 1
        for entry in anat_entries:
            if self.info[entry]['type'] == 'T1High':
#               High res T1-weighted, not normalization target. Rename it.
                fname = 'T1High_%d' % n_t1high
                fullname = '%s/%s' % (self.info[entry]['outdir'], fname)
                self.info[entry]['imgfile'] = fullname
                self.info[entry]['imgfile_skstrip'] = '%s_skstrip' % fullname
                self.info[entry]['matfile'] = '%s_matfile.aff12.1D' % fullname
                self.info[anat_tgt]['norm_src'] = False
                n_t1high += 1
        fname = 'T1High'
        fullname = '%s/%s' % (self.info[anat_tgt]['outdir'], fname)
        self.info[anat_tgt]['imgfile'] = fullname
        self.info[anat_tgt]['imgfile_skstrip'] = '%s_skstrip' % fullname
        self.info[anat_tgt]['matfile'] = '%s_matfile.aff12.1D' % fullname
        self.info[anat_tgt]['norm_src'] = True

        self.anatomical = '%s%s' %  (self.info[anat_tgt]['imgfile'], \
                                             self.info[anat_tgt]['suffix'])
#       The target for motin correction is the source for spatial normalization.
        self.norm_src = anat_tgt

    def _SetCatMotionFmapMats(self, fmap, anat):
        """
        Determine whether to (1) motion-correct to frame nearest T1High and
        assume that T1High and the fieldmap are in register or (2) catenate
        transformations to the base epi with a transformation from the base
        epi to T1High.
        """
        if abs(self.info[fmap]['series'] - self.info[anat]['series']) == 1:
#           Adjacent series, use them.
            return False
        elif abs(self.info[fmap]['acqtime'] - self.info[anat]['acqtime']) < 180:
            return False
        else:
            sernos = []
            min_series = min(self.info[fmap]['series'], self.info[anat]['series'])
            max_series = max(self.info[fmap]['series'], self.info[anat]['series'])
            gap_series = range(min_series+1, max_series, 1)
            for entry in self.info.keys():
                if self.info[entry]['type'] != 'null':
                    sernos.append(self.info[entry]['series'])
            for series in gap_series:
                if series in sernos:
#                   Fieldmap is separated from structural by one "full" series,
#                   where a full series is any series that was worth processing
#                   by this progroam, i.e, not a HOS,  an asset cal scan, a
#                   b1 cal scan or any other very sort calibration scan.
                    return True
            return False

    def _SetBaseEpi(self):
        """
        Define the series and frame for the target epi for motion correction.
        This is done by first creating a dictionary indexed by the time-delay
        between the epis and the target (two entries per epi: one for the
        first frame; one for the last.).  Then sort the keys to find the
        minimum time and use this entry to define the base epi and whether the
        beginning or ending frame should be used.
        """
        tinfo = {}
        for entry in self.entry_map['epi']:
            info = self.info[entry]
            if self.info[entry]['fmap_entry'] is None:
                tgt = info['anat_tgt']
            else:
                tgt = info['fmap_entry']
            tgt_time = self.info[tgt]['acqtime']

            plane = info['plane']
            if not tinfo.has_key(plane):
                tinfo[plane] = {}
            tdiff = abs(info['acqtime'] - tgt_time)
            tinfo[plane][tdiff] = (entry, 'start')
            tdiff = abs(info['acqtime'] + info['TR']*info['tdim']/1000 - tgt_time)
            tinfo[plane][tdiff] = (entry, 'end')

        bases = {}
        for plane in tinfo.keys():
            tdiffs = tinfo[plane].keys()
            tdiffs.sort()
            bases[plane] = tinfo[plane][tdiffs[0]]

        for epi in self.entry_map['epi']:
            plane = self.info[epi]['plane']
            base_entry, base = bases[plane]
            self.info[epi]['base_entry'] = base_entry
            self.info[epi]['base'] = base
            self.info[epi]['basefile'] = '%s'%(self.info[base_entry]['imgfile'])

    def GetBase(self, fname, suffix):
        """
        Strip of leading directory names to make a pretty path for display.
        """
        wds = fname.split('/')
        suff = suffix.replace('.BRIK','')
        suff = suff.replace('.HEAD','')
        if len(wds) > 1:
            return '.../%s' % '/'.join(wds[-2:]) + suff
        else:
            return fname + suff

    def SummarizeMotionTargets(self):
        """
        Create a text string summarizing how the motion correction was done.
        """
        text = '\nSummary of motion-correction: \n'
        for epi in self.entry_map['epi']:
            info = self.info[epi]
            text += self.GetBase(epi, '')
            base = self.GetBase(info['base_entry'], '')
            text += ' ->3dvolreg-> %s[%s]' % (base, info['base'])
            if info['fmap_entry'] is not None:
                fmap = info['fmap_entry']
                text += ' ->assume-registered-> %s' % self.GetBase(fmap, '')
                anat =  self.info[fmap]['anat_ref']
                if info['catmats']:
                    text += ' ->3dAllineate-> %s' % \
                                            self.GetBase(anat, '')
                else:
                    text += ' ->assume-registered-> %s' % self.GetBase(anat, '')
            else:
                anat =  info['anat_tgt']
                text += ' ->assume-registered-> %s' % self.GetBase(anat, '')
            text += '\nEPIs should be in register with %s\n' % \
                                            self.GetBase(self.anatomical, '')
        return text

    def _GetRefdat(self):
        """
        Find the correct ref.dat file for each p-file.
        """
        for rfile in self.refdats.keys():
#           Get times for ref.dat files with a time-stamp.
            words = rfile.replace('.','_').split('_')
            if len(words) == 6 and words[-2].count(':') == 20:
#               This file was time-stamped by the sequence. Get the
#               date and time. file name format:
#               ref_Sep_9_2007_11:28:32.dat
                rtime[rfile] = hms_to_secs(words[-2])
        for pfile in self.pfiles:
            min_difftime = 1.e20
            self.info[pfile]['refdat'] = None
            for rfile in self.refdats.keys():
                if rfile[:3] == 'ref' and 'dat' in rfile:
#                   This is a reference data file. First see if the orientation is
#                   appended. If the file has neither a time-stamp nor a plane and
#                   there is more than one ref.dat, the epi reconstruction will
#                   be aborted.
                    rinfo = {}
                    ref_file = None
                    if 'sag' in rfile and self.info[pfile]['plane'] == 'sagittal':
#                        self.info[pfile]['refdat'] = rfile
                        ref_file = rfile
                        break
                    elif 'cor' in rfile and self.info[pfile]['plane'] == 'coronal':
#                        self.info[pfile]['refdat'] = rfile
                        ref_file = rfile
                        break
                    elif 'axial' in rfile and self.info[pfile]['plane'] == 'axial':
#                        self.info[pfile]['refdat'] = rfile
                        ref_file = rfile
                        break
                    elif len(self.refdats.keys()) == 1:
#                       Use the only one if that is all there is.
                        ref_file = rfile
                    epi_time = hms_to_secs(self.info[pfile]['acqtime'].split()[-2])
                    if epi_time - rtime[rfile] < min_difftime and \
                                                rftime[rfile] > epi_time:
#                       Use the reference file that acquired nearest to the EPI
#                       but before it.
                        min_difftime = epi_time - rtime[rfile]
#                        self.info[pfile]['refdat'] = rfile
                        ref_file = rfile
                    if ref_file:
#                       Found a candidate.
                        if not self.info[pfile]['refdat']:
#                           Haven't found one yet, use it.
                            self.info[pfile]['refdat'] = ref_file
                        else:
#                           Found two. Choose one in the same directory.
                            oldpath = os.path.dirname(self.info[pfile]['refdat'])
                            newpath = os.path.dirname(ref_file)
                            pfile_path = os.path.dirname(pfile)
                            if oldpath == newpath:
#                               Same path, use the old one.
                                self.info[pfile]['refdat'] = ref_file
                            elif newpath == pfile_path:
                                self.info[pfile]['refdat'] = ref_file
#                           else Do nothing, use existing choice.
                elif not os.path.exists(rfile):
                    self.info[pfile]['refdat'] = None
                elif os.stat(rfile).st_size > 0:
#                   This path is taken if no info is encoded in the file name.
#                   Don't use empty ref.dat files.
                    self.info[pfile]['refdat'] = rfile

    def _MakeEpiScratchDir(self):
        self.MakeDir(self.user_scratch_dir)
        prefix = "%s-" % (int(time.time()))
        self.epi_scratch_space = mkdtemp(
            dir=self.user_scratch_dir, prefix=prefix)
        os.chmod(self.epi_scratch_space, S_IRWXU | S_IRWXG)


    def _GetEpiOrder(self):
        """
        Order the epis and assign names defined in the template files.
        """
        self.epi_series.sort()
        for series in self.epi_series:
            self.GetEpiAcqTimes(series)
            self.AssignEpiNames()

    def GetEpiAcqTimes(self, series):
        """
        Fill structure for sorting acquisition times.
        """
#       Find minimum and maximum start times for each acquistion in series.
        self.epi_times = {}
        for entry in self.entry_map['epi']:
#        Loop through each file in this series.
         if self.info[entry]['series'] == series and \
                                     self.info[entry]['tdim'] > 2:
#            Relate each entry to its time of acquisition.
             self.epi_times[self.info[entry]['acqtime']] = entry

    def AssignEpiNames(self):
        """
        Assign names to each epi file based on information in the template.
        """
#       Sort each run in the series by its acquisition time.
        epi_sort = self.epi_times.keys()
        epi_sort.sort()
#       Rewrite pfiles as an ordered list of p-files to be reconstructed.
        for idx in xrange(len(epi_sort)):
            entry = self.epi_times[epi_sort[idx]]
            info = self.info[entry]
            if info['data_filetype'] == 'ge_data':
                self.pfiles_recon.append(entry)
            info['run'] = '%0d' % (self.n_epi)
            self.n_epi = self.n_epi + 1
            plane = info['plane']
            if not self.epinames.has_key(plane):
                plane = 'any'
            n_epi = self.epinames[plane]['n_epi']
            if n_epi > len(self.epinames[plane]['names'])-1:
                if self.epinames.has_key('any') and \
                                    n_epi < len(self.epinames['any']):
                    plane = 'any'
                    n_epi = self.epinames[plane]['n_epi']
                else:
                    self.DumpInfo()
                    errstr = 'Not enough EPI names in template file'
                    raise RuntimeError(errstr)
#                    epiname = self.epinames[plane]['names'][n_epi]

            filebase = os.path.basename(self.epinames[plane]['names'][n_epi])
            epi_mf_outdir = os.path.dirname(\
                                self.epinames[plane]['names'][n_epi])

            epi_base = self.epinames[plane]['subdir'][n_epi]
            tmp_outdir = '%s/%s' % (self.tmpdir, epi_base)
#           Get output directory for raw epis.
            if self.no_motcorr:
                epi_r_outdir = epi_mf_outdir
            elif self.keep_epi_raw:
                epi_r_outdir = self.epi_scratch_space
            else:
                epi_r_outdir = tmp_outdir

#           Get output directory for motion-corrected epis.
            if self.keep_epi_mot:
                epi_m_outdir = self.epi_scratch_space
            else:
                epi_m_outdir = tmp_outdir
            info['outdir'] = epi_mf_outdir
            if n_epi < len(self.epinames[plane]['names']):
                epiname = self.epinames[plane]['names'][n_epi]
                info['imgfile'] = '%s/%s' % (epi_r_outdir, filebase)
            else:
                info['imgfile'] = '%s/s%0d_epi_run%0d' % \
                                    (epi_r_outdir, n_epi, idx+1)
            self.epinames[plane]['n_epi'] += 1

            info['mot_file'] = '%s/%s_mtn.txt' % (epi_mf_outdir, filebase)
            info['censor_prefix'] = '%s/%s' % (epi_mf_outdir, filebase)
            info['imgfile_t'] = '%s/%s_t' % (epi_m_outdir, filebase)
            if self.no_motcorr:
                info['imgfile_m'] = None
                info['imgfile_mf'] = None
                info['imgfile_final'] = info['imgfile']
            else:
                info['imgfile_m'] = '%s/%s_m' % (epi_m_outdir, filebase)
                if self.no_fmapcorr or info['fmap_entry'] is None:
                    info['imgfile_m'] = '%s/%s_m' % (epi_mf_outdir, filebase)
                    info['imgfile_mf'] = None
                    info['imgfile_final'] = info['imgfile_m']
                else:
                    info['imgfile_m'] = '%s/%s_m' % (epi_m_outdir, filebase)
                    info['imgfile_mf'] = '%s/%s_mf' % (epi_mf_outdir, filebase)
                    info['imgfile_final'] = info['imgfile_mf']
            info['skip'] = self.skip
            info['motion_ref_frame'] = self.tmplt['motion_ref_frame']

            info['motion_interp'] = self.tmplt['epi_motion_interp']
            if not info['motion_interp'].startswith('-'):
                info['motion_interp'] = '-%s' % info['motion_interp']

            info['filetype'] = self.tmplt['epi_file_format']
            info['valid'] = True
            self.info[entry] = info

            if not self.no_motcorr:
                epi_base = os.path.basename(info['imgfile_m'])
                info['matfile_m'] = '%s/%s.aff12.1D' % (info['outdir'], epi_base)
                info['matfile_mcat'] = '%s/%scat.aff12.1D' % (info['outdir'], epi_base)

    def DumpInfo(self):
        """ Dump the info object to a yaml file. """
        if self.logdir is None:
            return
        self.dumpfile = '%s/preprocess_info.yaml' % (self.logdir)
        try:
            f = open(self.dumpfile,'w')
            f.write(yaml.dump(self.info,default_flow_style=False, indent=4))
            f.close()
        except IOError:
            self.errors = True
            errstr =  'Error accessing %s' % self.dumpfile
            raise IOError(errstr)
            self.LogErrors(errstr)

    def UnDumpInfo(self):
        """ Load the info dictionary from a yaml file. """
        filename = '%s/preprocess_info.yaml' % self.logdir
        f = open(filename,'r')
        self.info = yaml.load(f.read())
        f.close()

class ProcData(DataInfo):
    """
    Methods in this object perform the actions defined by the ProcData object.
    """
    def __init__(self, opts):
        self.dumpfile = None
        self.error_log = ''
        self.f_log = None
        self.f_crash = None
        self.f_bash = None
        self.opts = opts
        self.keep_epi_raw = opts.keep_epi_raw
        self.keep_epi_mot = opts.keep_epi_mot
        self.anatref_entry = None
        self.template_type = 'default'
        self.slicetime_corr = not opts.no_slicetime
        self.no_motcorr = opts.no_motcorr
        self.no_fmapcorr = opts.no_fmapcorr
        self.term_mesg = 'No problems detected'
        self.template_file = opts.template_file
        self.server = socket.gethostname().split('.')[0]
        self.starttime = datetime.today().strftime('%d%b%Y_%H:%M')

    def Initialize(self, topdir, redo=False, verbose=False, dry_run=False, \
                    skip=None, scratch='/scratch', no_email=False, \
                    template_file=None):

#       Create default file object for early crashes.
        self.logfile = sys.stderr
        self.motcor_summary = ''

#       Set default permission to 0775
        os.umask(UMASK_FILE)

#       Initialize data structures.
        DataInfo.__init__(self, topdir, redo, verbose, skip, dry_run, scratch, \
                          no_email, template_file)

#       Walk through data directories and categorize files.
        self.FindStuffToDo()

        if skip is None:
            self.skip = self.tmplt['skip']
        self.redo = redo
        self.verbose = verbose
        self.dry_run = dry_run
        self.verbose = verbose
        self.no_email = no_email

#       Create output directories.
        self.CreateDirs()


        self.DumpInfo()

#       Open the logfiles.
        self.logfile = '%s/preprocess_%s.log' % (self.logdir, self.starttime)
        self.f_log = open(self.logfile,'w')
        self.f_log.write(self.verstring)
        self.f_log.write('%s\n'%' '.join(sys.argv))
        self.f_log.write('# Date: %s\n\n' % \
                        datetime.today().strftime('%a %b %d, %Y; %X'))
        self.f_log.write('Server: %s\n' % self.server)
        self.f_log.write(self.motcor_summary)
        self.f_log.flush()

        self.f_crash = open('%s/preprocess_failed.log' % self.logdir,'w')
        self.f_crash.seek(0,2)
        self.f_crash.write('Last written on %s\n\n' % \
                        datetime.today().strftime('%a %b %d, %Y; %X'))

        self.f_bash = open('%s/preprocess_%s.bsh' % (self.logdir, self.starttime),'w')
        self.f_bash.seek(0,2)
        self.f_bash.write('#!/bin/bash\n\n')
        self.f_bash.write('# Written on %s\n\n' % \
                        datetime.today().strftime('%a %b %d, %Y; %X'))

#        self.epi_prefixes = {}

    def CleanEpi(self):
        """
        Ensure all epi files are recomputed by verifying that all output
        prefixes either don't exist or are deleted.
        """
        for entry in self.info.keys():
            info = self.info[entry]
            if info['psdname'] == 'epi':
                for tag in ('imgfile', 'imgfile_m', 'imgfile_mf', 'imgfile_t'):
                    if info.has_key(tag) and info[tag] is not None and \
                                                    os.path.exists(info[tag]):
                        print 'Deleting %s*' % (info[tag], info['suffix'])
                        cmd = '/bin/rm %s%s*' % (info[tag], info['suffix'])
                        self.ExecCmd(cmd)
                        if '.BRIK' in info['suffix']:
                            cmd = '/bin/rm %s%s*' % (info[tag], \
                                  info['suffix'].replace('.BRIK','.HEAD'))
                            self.ExecCmd(cmd)

    def CreateDirs(self):
        """
        Create output directories if they don't already exist.
        """
#       First, create a list of directories.
        dnames = []
        tags = ['', '_m', '_mf']
        for entry in self.info.keys():
            if self.info[entry]['type'] == 'epi':
                for tag in tags:
                    fname = self.info[entry].get('imgfile%s' % tag, None)
                    if fname is not None:
                        dnames.append(os.path.dirname(fname))
            else:
                if self.info[entry].get('outdir',None) is not None:
                    dnames.append(self.info[entry]['outdir'])

#       Create them if they don't already exist.
        for dname in dnames:
            if  not os.path.exists(dname):
                self.MakeDir(dname)
                if self.verbose:
                    print 'mkdir %s' % dname

    def ExecCmd(self, cmd, halt_on_error=True):
        """
        Execute a bash command.  This method is obsolete now.  At one time
        it called a library function that worked around a deadlock bug in
        popen2
        """
        self.f_bash.write("%s\n"%cmd)
        self.f_bash.flush()
        if not self.dry_run:
            try:
                execCmd(cmd, self.f_log, self.f_crash, self.verbose)
                self.f_log.flush()
            except RuntimeError, errstr:
                if halt_on_error:
                    raise RuntimeError(errstr)
                else:
                    self.LogErrors('%s' % errstr)
                    return True
        else:
            return False

    def ConvertAnat(self):
        """
        Convert anatomical images from dicom or i-files to briks or niftis.
        """
        if self.verbose:
            print 'Convert T1 and T2 images...'
        for entry in self.info:
            info = self.info[entry]
            if  self.info[entry]['imgfile'] is None:
                continue
            if self.info[entry]['type'] in self.anat_types:
                key = self.info[entry]['type']
                imgfile = self.info[entry]['imgfile']
                cmd = 'convert_file %s %s %s %s' % (self.flip_opts, entry, \
                            imgfile, self.info[entry]['filetype'])
                checkfile = '%s%s' % (imgfile, self.info[entry]['suffix'])
                self.CheckExec(cmd, [checkfile])
                if self.info[entry]['norm_src'] and self.skull_strip:
                    cmd = "3dSkullStrip -input %s -prefix %s" % \
                          (checkfile, self.info[entry]['imgfile_skstrip'])
                    checkfile = '%s+orig.BRIK' % \
                                     (self.info[entry]['imgfile_skstrip'])
                    self.CheckExec(cmd, [checkfile])
#
    def AlignFieldmaps(self):
        """
        Register the magnitude image from the fieldmap data to the
        hi-res structural. Save the matrices for later use in motion
        correction.
        """
        for entry in self.entry_map['fmap']:
            info = self.info[entry]

#           Register the magnitude image at the shortest TR to the T1-IR
#           structural image.
            target = self.info[self.norm_src]['imgfile'] + \
                                        self.info[self.norm_src]['suffix']
            source = info['magfile'] + info['suffix']
            matfile = info['matfile']
            fmt = '3dAllineate -prefix NULL -1Dmatrix_save %s -base %s ' + \
                  '-source %s -cost mi -warp shift_rotate'
            cmd = fmt % (info['matfile'], target, source)
            self.CheckExec(cmd, [info['matfile']])

#           Convert to unitary matrix (remove scaling component.)
            cmd = 'cat_matvec -ONELINE %s -P > %s' % \
                                    (info['matfile'], info['matfile_unitary'])
            self.CheckExec(cmd, [info['matfile_unitary']])

#           Rotate the magnitude image to the new grid.
            fmt = '3dAllineate -prefix %s -interp cubic -1Dmatrix_apply %s %s'
            cmd = fmt % (info['magfile_r']+info['suffix'], \
                  info['matfile_unitary'], info['magfile'] + info['suffix'])
            self.CheckExec(cmd, [info['magfile_r']+info['suffix']])

#           Rotate the fieldmap to the new grid.
            fmt = '3dAllineate -prefix %s -interp cubic -1Dmatrix_apply %s %s'
            cmd = fmt % (info['imgfile_r']+info['suffix'], \
                  info['matfile_unitary'], info['imgfile'] + info['suffix'])
            self.CheckExec(cmd, [info['imgfile_r']+info['suffix']])

    def ProcessDTI(self):
        """
        Convert anatomical images to briks.
        """
        for entry in self.info:
            if self.info[entry]['type'] == 'dti':
                if self.verbose:
                    print 'Processing DTI data in %s' % os.path.basename(entry)
#                dtiname = '%s/s%s_dti' % \
#                        (self.info[entry]['outdir'],self.info[entry]['series'])
                cmd = 'convert_file %s %s %s' % (entry, \
                       self.info[entry]['imgfile'], self.info[entry]['filetype'])
                fname = '%s%s' % \
                        (self.info[entry]['imgfile'], self.info[entry]['suffix'])
                self.CheckExec(cmd, [fname])

    def ProcessAsl(self):
        """
        Convert ASL images to nifti.
        """
        for entry in self.info:
            if self.info[entry]['type'] == 'asl':
                if self.verbose:
                    print 'Processing ASL data in %s' % os.path.basename(entry)
                cmd = 'convert_file %s %s %s' % (entry, \
                       self.info[entry]['imgfile'], self.info[entry]['filetype'])
                fname = '%s%s' % \
                        (self.info[entry]['imgfile'], self.info[entry]['suffix'])
                self.CheckExec(cmd, [fname])

    def MakeFieldmaps(self):
        """
        Create the fieldmap(s) and the corresponding  magnitude images.
        """
        if self.verbose:
            print 'Compute fieldmaps.'
        for entry in self.info:
            if self.info[entry]['type'] == 'fmap':
                if self.info[entry]['imgfile'] == None:
#                   Fieldmap data not found.
                    return
#               Make a magnitude image for use in checking registration.
                cmd = 'convert_file -f0 -m0 %s %s nii' % \
                            (entry, self.info[entry]['magfile'])
                self.CheckExec(cmd, [self.info[entry]['magfile'] + '.nii'])

#       Make fieldmap. Use separate loop in case make_fmap aborts.
        for entry in self.info:
            if self.info[entry]['type'] == 'fmap':
                fmapname = self.info[entry]['imgfile']
                if not os.path.exists('%s.nii' % fmapname) or self.redo:
#                   Couldn't find or existing fmap, compute a new one.
                    if self.verbose:
                        extra_args = '-v'
                    else:
                        extra_args = ''
                    if self.info[entry]['correct_fmap_phase'] == 'force':
                        extra_args += ' --force-slicecorr'
                    elif self.info[entry]['correct_fmap_phase'] == 'omit':
                        extra_args += ' --omit-slicecorr'
                    cmd = 'make_fmap %s %s %s' % (extra_args, entry, fmapname)
#                    error = self.ExecCmd(cmd, halt_on_error=False)
                    if self.no_fmapcorr:
                        halt_on_error = False
                    else:
                        halt_on_error = True
                    error = self.CheckExec(cmd, ['%s.nii' % fmapname], \
                                                halt_on_error=halt_on_error)
                    if error:
                        self.info[entry]['valid'] = False
                        del self.fmaps[entry]

    def LinkAnat(self):
        """Create link to structural image if it doesn't already exist."""

        if self.anatomical is None:
            return
        for entry in self.info.keys():
            info = self.info[entry]
            if info.has_key('anat_link'):
                self.LinkFiles(info['outdir'], self.anatomical)

    def LinkFiles(self, srcdir, target):
        """
        Create links to BRIK, HEAD, and .nii files.
        """
        if '+orig' in target:
            tgt_prefix = target.replace('.BRIK','')
            tgt_prefix = tgt_prefix.replace('.HEAD','')
            linkfiles = ['%s.HEAD'%tgt_prefix, '%s.BRIK' %tgt_prefix]
        else:
            linkfiles = [target]
        for linkfile in linkfiles:
            linkname = '%s/%s' % (srcdir, os.path.basename(linkfile))
            rel_linkdir = abspath_to_relpath(os.path.dirname(target), srcdir)
            rel_linkfile = '%s/%s' % (rel_linkdir, os.path.basename(linkfile))
            if not os.path.exists(linkname) and not os.path.islink(linkname):
                cmd = 'cd %s && ln -s %s %s' % (srcdir, rel_linkfile, linkname)
                self.ExecCmd(cmd)

    def ExtractFirstEpi(self):
        """
        Extract the initial EPIs stored in dicom format.
        """
        for entry in self.info:
            if self.info[entry]['type'] == 'first_epi':
                epiname = self.info[entry]['imgfile']
                cmd = 'convert_file %s -f0 %s %s %s' % \
                   (self.flip_opts, entry,epiname, self.info[entry]['filetype'])
                fname = '%s%s' %  (epiname, self.info[entry]['suffix'])
                self.CheckExec(cmd, [fname])
                self.info[entry]['imgfile'] = fname

    def ReconEpis(self):
        """
        Reconstruct the EPIs from p-files.
        """
        run = zeros(100)
        if self.verbose:
            print 'Reconstruct EPIs'
        for pfile in self.pfiles_recon:
            if self.info[pfile]['refdat'] is None:
#               Find the ref.dat file later.
                continue
            if self.info[pfile]['compression'] is not None:
#               Data are compressed, copy to tmp.
                compression = self.info[pfile]['compression']

                pfile_decomp = '%s/%s' %  (self.tmpdir, \
                            os.path.basename(self.info[pfile]['pfile_decomp']))
                if os.path.exists(pfile_decomp):
                    errstr = 'Attempting to overwrite existing p-file (%s)' % pfile_decomp + \
                    ' in ReconEpis'

                cmd = '%s %s > %s' % \
                            (decompress_cmds[compression], pfile, pfile_decomp)
                self.ExecCmd(cmd)
            else:
#               Create a link on /tmp to the pfile so the link to ref.dat will also
#               be on /tmp, (which is always writeable.)
                pfile_decomp = '%s/%s' % (self.tmpdir, os.path.basename(pfile))
                if not os.path.exists(pfile_decomp):
                    os.symlink(pfile, pfile_decomp)
            refname, refcmpress = self.CheckCompression( \
                                                self.info[pfile]['refdat'])
            if refcmpress is not None:
                refdat_decomp = '%s/%s' % (self.tmpdir, os.path.basename(refname))
                cmd = '%s %s > %s' % \
                            (decompress_cmds[refcmpress], \
                             self.info[pfile]['refdat'], refdat_decomp)
                self.ExecCmd(cmd)
            else:
                refdat_decomp = self.info[pfile]['refdat']
            if refdat_decomp is not None:
                if refdat_decomp != 'ref.dat':
#                   Create link bearing the file name epirecon_ex expects.
                    refdat_link = '%s/ref.dat' % self.tmpdir
                    if not os.path.exists(refdat_link):
                        if self.verbose:
                            print 'ln -s %s %s' %  (refdat_decomp, refdat_link)
                        if os.path.islink(refdat_link):
#                           ref.dat is a broken symbolic link.
                            if self.verbose:
                                print 'rm %s' % ref_file
                            os.remove(refdat_link)
                        try:
                            os.symlink(refdat_decomp, refdat_link)
                        except OSError:
                            self.errors = True
                            pfile_link = '%s/%s' % (self.tmpdir, os.path.basename(pfile_decomp))
                            os.symlink(pfile_decomp, pfile_link)
                            os.symlink(refdat_decomp, '%s/ref.dat' % self.tmpdir)

                series = int(self.info[pfile]['series'])
                run[series] = run[series] + 1
                epiname = self.info[pfile]['imgfile']
                cmd = 'epirecon_ex -F -f %s -NAME %s -fmt brik -skip %d' % \
                                            (pfile_decomp, epiname, self.skip)
                fname = '%s+orig.BRIK' %  epiname
                self.CheckExec(cmd, [fname])
#                self.epi_prefixes[pfile] = self.info[pfile]['imgfile']
            else:
                errstr = '*******************************************\n' + \
                         'No ref.dat file exists for %s\n' % pfile + \
                         '*******************************************\n'
                self.error_log = self.error_log + errstr
                self.f_crash.write(errstr)

    def PruneEpiEntries(self):
        """
        Eliminate entries in epi recon table that have already been
        reconstructed. I don't remember why this is here but I know that at
        one time it was important.
        """
        pruned = {}
        basefiles = []
        baseentries = {}
        for entry in self.entry_map['epi']:
            if baseentries.has_key(self.info[entry]['basefile']):
                baseentries[self.info[entry]['basefile']].append(entry)
            else:
                baseentries[self.info[entry]['basefile']] = [entry]
        for entry in self.entry_map['epi']:
            targets = []
            if self.no_motcorr:
                target = self.info[entry]['imgfile']
            elif self.info[entry]['fmapname'] is None or self.no_fmapcorr:
                target = self.info[entry]['imgfile_m']
            else:
                target = self.info[entry]['imgfile_mf']
            targets.append(target + self.info[entry]['suffix'])
            targets.append('%s%s' % (self.info[entry]['censor_prefix'], '_censor.1D'))
            pruned[entry] = [True, baseentries[self.info[entry]['basefile']]]
            for target in targets:
                pruned[entry] = \
                            [False, baseentries[self.info[entry]['basefile']]]
        for key in pruned.keys():
            if not pruned[key][0]:
                for entry in  pruned[key][1]:
                    pruned[entry][0] = False
        tmp = new_map = []
        for entry in self.entry_map['epi']:
            if pruned[entry][0]:
                if self.verbose:
                    print 'Skipping %s: Already reconstructed.' % targets[0]
                if entry in self.pfiles_recon:
                    self.pfiles_recon.remove(entry)
            else:
                new_map.append(entry)
        self.entry_map['epi'] = new_map

    def ConvertRtEpis(self):
        """
        Convert epis reconstructed on the scanner.
        """
        if self.verbose:
            print 'Convert EPIs to brik'
        for entry in self.entry_map['epi']:
            if ('epirt' in self.info[entry]['psdname'] or \
                self.info[entry]['psdname'] == 'epi' or \
                self.info[entry]['psdname'] == '*epfid2d1_64') and \
                self.info[entry]['data_filetype'] == 'dicom':
                series = self.info[entry]['series']
                if self.info[entry]['skip'] > 0:
                    skip = '--skip=%s' % self.info[entry]['skip']
                else:
                    skip = ''
                cmd = 'convert_file %s %s %s brik' % \
                                (skip, entry, self.info[entry]['imgfile'])
                checkname = '%s+orig.BRIK' % (self.info[entry]['imgfile'])
                self.CheckExec(cmd, [checkname])

    def SliceTimeCorrect(self, info, epifile):
        if info['acq_tr'] != info['TR'] and  self.slicetime_corr:
#           This is a bunched EPI, do the special slice-time correction.
            tshift_file = '%s/%s_tshift' % \
                (self.tmpdir, os.path.basename(epifile).replace('+orig',''))

            cmd = '3dTshift -tpattern %s -TR %fms -prefix %s %s' % \
            (info['slice_order'], info['acq_tr'], info['imgfile_t'], epifile)
            self.CheckExec(cmd, ['%s+orig' % tshift_file])
            tshift_str = ''
            tshift_file = '%s+orig' % info['imgfile_t']
            cmd = '3drefit -TR %fms %s' % \
                            (info['TR'],tshift_file)
            self.ExecCmd(cmd)
            tshift_str = ''
        elif self.slicetime_corr:
#       Time-shift the EPIs. 3dTshift aborts if tdim < 8.
            if self.skip == 0:
                skip = 4
            else:
                skip = self.skip
            cmd = '3dTshift -TR %fms -tpattern %s -prefix %s -ignore %d %s' % \
                  (info['acq_tr'], info['slice_order'], info['imgfile_t'], \
                                                                skip, epifile)
            checknames = ['%s+orig.BRIK'%info['imgfile_t'],\
                         '%s+orig.HEAD'%info['imgfile_t']]
            self.CheckExec(cmd, checknames)
        else:
            cmd = '3dcopy %s %s+orig' % (epifile, info['imgfile_t'])
            self.CheckExec(cmd, [info['imgfile_t']+'+orig'])
        return


    def CorrectMotion(self):
        """
        Correct for motion and call SliceTimeCorrect.
        """
        if self.verbose:
            print "Correct for motion"
        for entry in self.entry_map['epi']:
            info = self.info[entry]

            if os.path.exists(info['imgfile_m'] + info['suffix']):
                return
#           Always use brik for 3dDeconvolve.
            suffix = '+orig'
            epifile = '%s%s' % (info['imgfile'], suffix)
            prefix = info['imgfile_m']
            base_entry = info['base_entry']
            if info['base'] == 'start':
#               Use the first frame specified in template file.  Defaults
#               to zero.
                base = info['motion_ref_frame']
            else:
#               Use the last frame.
                base = self.info[base_entry]['tdim'] - info['skip']-1
                base =  ('%d' % base).replace(' ','')

#           Correct for slice-timing.
            self.SliceTimeCorrect(info, epifile)

            plane = info['plane']
            anat_tgt = info['anat_tgt']
#            anat_entry = self.anat_entry[plane]

            if info['catmats']:
#               Include additonal transformation in motion correction such
#               that final image is in register with the fieldmap, which has
#               been registered to the structural image that will be used for
#               spatial normalization.
                self.MotcorCatenate(info, base, anat_tgt)
            else:
#               Assume fieldmap is in register with the structural.
                self.Motcor(info, base)

            if info.get('fmapname', None) is None:
#               No fieldmap correction.
                if self.fsl_flip:
#                   Flip the way fslview likes it.
                    self.FSLFlip(info['imgfile_m'], info['imgfile_final'])
                elif info['suffix'] == '.nii':
#                   Copy motion-corrected images from /tmp to output directory
                    outfile = info['imgfile_final'] + info['suffix']
                    cmd = '3dcopy %s+orig %s' % (info['imgfile_m'], outfile)
                    self.CheckExec(cmd, [outfile], force=True)
                    cmd = '/bin/rm %s+orig*' % info['imgfile_m']
                    self.CheckExec(cmd, [], force=True)

    def MotcorCatenate(self, info, base, anat_tgt):
        """
        Compute motion-correction transformation matrices, catenate with
        transform from fieldmap to structural, then inteprolate the data to
        the final grid.
        """
#       First compute the transformation matrices due to epi-to-epi motion.
        fmt = '3dvolreg -prefix NULL -1Dmatrix_save %s -twopass ' + \
                            '-verbose -base %s+orig[%s] -dfile %s %s+orig'
        cmd = fmt % (info['matfile_m'], info['basefile'], base, \
                                        info['mot_file'], info['imgfile_t'])
        self.CheckExec(cmd, [info['matfile_m']])

#       Catenate with transformation from epi base image to the anatomical.
        cmd = 'cat_matvec  -ONELINE %s -P  %s -P > %s' % \
                          (self.info[anat_tgt]['matfile'], info['matfile_m'], \
                                                        info['matfile_mcat'])
        self.CheckExec(cmd, [info['matfile_mcat']])

#       Interpolate the data to the new grid.
        fmt = '3dAllineate -prefix %s -interp cubic -1Dmatrix_apply %s ' + \
                                 '-warp shift_rotate -base %s+orig[%s] %s+orig'
        cmd = fmt % (info['imgfile_m'], info['matfile_mcat'], info['basefile'], \
                                                        base, info['imgfile_t'])
        self.CheckExec(cmd, ['%s+orig.BRIK'%info['imgfile_m'], \
                             '%s+orig.HEAD'%info['imgfile_m']])

    def Motcor(self, info, base):
        """
        Motion correct using 3dvolreg.  No slice-time correction.
        """
        fmt = '3dvolreg -prefix %s -twopass  %s -verbose -base %s+orig[%s] ' + \
                                                        '-dfile %s %s+orig'
        cmd = fmt % (info['imgfile_m'], info['motion_interp'], \
                     info['basefile'], base, info['mot_file'], info['imgfile_t'])

        self.CheckExec(cmd, ['%s+orig.BRIK' % info['imgfile_m'], \
                             '%s+orig.HEAD' % info['imgfile_m']])


    def JumpCensor(self):
        """
        Call the jump_censor program to characterize the degree of motion.
        """
        if self.verbose:
            print 'Computing censor files.'
        for entry in self.entry_map['epi']:
            if self.censor_interleave:
                input_file = '%s+orig' % self.info[entry]['imgfile']
                interleave = '--interleave'
            else:
                interleave = ''
                if os.path.exists(self.info[entry]['mot_file']):
                    input_file = self.info[entry]['mot_file']
                else:
                    input_file = '%s+orig' % self.info[entry]['imgfile']
            cmd = \
            "jump_censor -v --prefix=%s %s --store-plot --threshold=%f %s" % \
                                        (self.info[entry]['censor_prefix'],
                                         interleave,
                                         self.censor_thresh,
                                         input_file)
            try:
                self.CheckExec(cmd, ['%s_censor.1D' %
                                    self.info[entry]['censor_prefix']],
                                    force=False)
            except:
                print 'Error computing censor files.'

    def CheckExec(self, cmd, checknames, force=False, halt_on_error=True):
        """
        Check if output file exists, then execute commmand.
        If there is more than one output file, the command will be
        executed if at least one is missing.
        """
        gone = False
        names = []
        for name in checknames:
            if '+orig' in name:
                if name.endswith('+orig'):
                    names.append('%s.HEAD' % name)
                    names.append('%s.BRIK' % name)
                elif name.endswith('HEAD'):
                    names.append(name)
                    newname = name[:-4] + 'BRIK'
                    if newname not in checknames:
                        names.append(newname)
                elif name.endswith('BRIK'):
                    newname = name[:-4] + 'HEAD'
                    if newname not in checknames:
                        names.append(newname)
                    names.append(name)
            else:
                names.append(name)
        for name in names:
            if not os.path.exists(name) and not os.path.exists('%s.gz'%name):
                gone = True
            elif self.redo or force or gone:
                os.remove(name)
                gone = True
        if self.redo or gone:
            self.ExecCmd(cmd,  halt_on_error=halt_on_error)
            if '+orig.' in names[0]:
                name = names[0].replace('.BRIK','')
                name = name.replace('.HEAD','')
                append_history_note(name, cmd)

    def FieldmapCorrection(self):
        if self.verbose:
            print "Fieldmap correction"
        for entry in self.entry_map['epi']:
            info = self.info[entry]
            if info['type'] == 'epi' and info['fmapname'] is not None:
                infile = '%s+orig' % (info['imgfile_m'])
                cmd = 'fieldmap_correction -m --tag=f -t%s %s %s %s %s' % \
                      (info['filetype'], info['fmapname'], info['echo_spacing'],\
                       info['outdir'], '%s+orig' % info['imgfile_m'])
                self.CheckExec(cmd, [info['imgfile_mf'] + info['suffix']])

                if self.fsl_flip:
                    self.FSLFlip(info['imgfile_mf'], info['imgfile_mf'])

#           Create links from outut directory to files on /scratch
            for tgt in (info['imgfile'], info['imgfile_m']):
                if '/scratch' in tgt:
                    self.LinkFiles(self.info[entry]['outdir'], \
                                   tgt + self.info[entry]['suffix'])

    def ComputeSNR(self):
        """
        Compute the temporal SNR for each epi, save in a nifti file, and
        store a summmary in a png file.
        """
        for epi in self.entry_map['epi']:
            epifile = self.info[epi]['imgfile_final'] + self.info[epi]['suffix']
            prefix = self.info[epi]['imgfile_final'] + '_snr'
            if not os.path.exists('%s_snr.png' % prefix):
                if self.verbose:
                    print 'TemporalSnr(epifile=%s, prefix=%s)' % \
                                                (epifile, prefix)
                try:
                    TemporalSnr(epifile=epifile, prefix=prefix)()
                except:
                    print("Error computing temporal SNR")

    def FSLFlip(self, infile, prefix):
        """
        Flip axes to orientation fslview expects.
        """
        cmd = '3dresample -orient LPI -prefix %s.nii -inset %s+orig' % \
                                                    (prefix, infile)
        self.CheckExec(cmd, ['%s.nii' % prefix])
        fname = '%s+orig.BRIK' % infile
        if os.path.exists(fname):
            os.remove(fname)
        fname = '%s+orig.HEAD' % infile
        if os.path.exists(fname):
            os.remove(fname)

    def Chown(self):
        """
        Change ownership to group read read/write.
        """
        cmd = 'chmod -R 0775 %s' % self.procdir
        self.ExecCmd(cmd)

    def LogErrors(self, errstr):
        self.error_log = self.error_log + errstr
        if self.opts.verbose:
            sys.stderr.write('%s\n' % errstr)
        if  self.f_crash is not None:
            self.f_crash.write('\n%s\n' % errstr)
        if  self.f_log is not None:
            self.f_log.write('\n%s\n' % errstr)
            self.f_log.flush()

    def LogProcess(self):
        """
        Store some useful information in the log file.
        """
        time = datetime.today().strftime('%a %Y%b%d %X')
#       Get user name.
        f = os.popen("whoami","r")
        user = f.read().strip()
        f.close()

        entry = '%s\t%s\t%s\t%s\n' % (time, self.topdir, user, self.version)

        if ismounted(c.exams_file):
#           Append info to the exams file.
            try:
                f = open(c.exams_file,'a+')
                f.seek(0, 2)
                f.write(entry)
                f.close()
            except:
#               Not a huge problem if this doesn't work.
                pass

    def CleanUp(self):
        """
        Delete temporary files, close log files and email results.
        """
        if (not self.keep_epi_raw or not self.keep_epi_mot) \
                                 and not self.opts.debug_tmp:
            self.tmp.Clean()
        overall_msg = self.SummaryErrorMessage()
        if self.tmplt and not self.no_email:
            EmailResults(self.tmplt['email'], overall_msg, \
                self.topdir, self.dumpfile, self.logfile, self.motcor_summary)

#       Write the error message to the log file.
        if self.f_log is None:
#           Log file not opened yet, do it now.
            if self.logdir is not None:
                logfile = '%s/preprocess.log' % self.logdir
                f_log = open(logfile,'w')
                f_log.write('\n%s\n' % overall_msg)
                f_log.close()
        else:
            self.f_log.write('\n%s\n' % overall_msg)
        sys.exit()

    def SummaryErrorMessage(self, error_log=None):
        """
        Create summary message for email.
        """
        if error_log is None:
            error_log = self.error_log
#        server = socket.gethostname().split('.')[0]
        mssg = '\nPreprocessing script complete for data in %s\n\nServer: %s\n'\
                                                 % (self.topdir, self.server)
#       Log time.
        ms = time.time()
        ms = int(1000*(ms - int(ms)))
        mssg += '\nTime: %s:%03d\n' % \
                        (datetime.today().strftime('%a %b %d, %Y; %X'), ms)
        if len(error_log) > 0:
            mssg += 'Command: %s\n\nSummary:\n' % (' '.join(sys.argv))
            lines = error_log.split('\n')
            for line in lines:
                if line.startswith('Description:'):
                    mssg += line[12:]
            mssg += '\n\nDetails:' + error_log
        else:
            mssg += '\nNo problems detected (this does NOT imply that everything was computed.).\n\n'
        return mssg

def parse_cmdline():

    proc = None
    usage = "preprocess path  Enter --help for a list of options." + \
            "Default action is to process everything."
    optparser = OptionParser(usage)

    optparser.add_option( "-v", "--verbose", action="store_true", \
                dest="verbose",default=False, \
                help='Print stuff to screen.')
    optparser.add_option( "", "--no-email", action="store_true", \
                dest="no_email",default=False, \
                help="Don't send any emails.")
    optparser.add_option( "-R", "--recompute", action="store_true", \
                dest="redo",default=False, help='Recompute all files.')
    optparser.add_option("", "--exclude", action="callback", \
                callback=key_callback, dest="exclude_paths", type="string", \
                default=[], help=\
        'A path that is to be excluded from the analysis.  Both ' + \
        'relative and absolute paths can be entered. If EXCLUDE_PATH is ' +\
        'a directory, all files in the directory and in its subdirectories '+\
        'will be excluded.')
    optparser.add_option("", "--epi-key", action="callback", \
                callback=key_callback, dest="epi_keys", type="string", \
                default=[], help=\
        'Keyword and value that must be present in the p-file header if it' + \
        'is to be processed.  For example, suppose epis were collected with '+\
        'for two paradigms during the same session.  If one contained 198 ' + \
        'frames and the other 210, specfying the keyword tdim:198 would '+\
        'cause the program to only process EPI runs containing 198 frames' + \
        'Valid keywords are "tdim" (number of frames), "SeriesNumber", '+\
        'and/or "plane" (axial, sagittal, or coronal). Multiple keywords' + \
        'can be entered (e.g., "--epi_key=tdim:198 --epi-key=plane:sagittal")')
    optparser.add_option( "", "--hog-disk", action="store_true", \
                dest="hog",default=False, \
                help='Save all intermediate files. Same as --keep-epi-all.')
    optparser.add_option( "", "--keep-epi-raw", action="store_true", \
                dest="keep_epi_raw",default=False, \
                help='Keep uncorrected EPI images. They will be stored ' + \
                'in a shadow directory on /scratch, e.g., if output ' + \
                'directory is /study/mystudy/processed/subj001, images ' + \
                'will be stored in /scratch/mystudy/processed/subj001')
    optparser.add_option( "", "--keep-epi-mot", action="store_true", \
                dest="keep_epi_mot",default=False, \
                help='Keep motion-corrected (but not yet fieldmap-' +\
                'corrected EPI images. They will be stored ' + \
                'in a shadow directory on /scratch, e.g., if output ' + \
                'directory is /study/mystudy/processed/subj001, images ' + \
                'will be stored in /scratch/mystudy/processed/subj001')
    optparser.add_option( "", "--keep-epi-all", action="store_true", \
                dest="keep_epi_all",default=False, \
                help='Keep all EPI images, including intermediate images ' + \
                'Intermediate EPIs will be stored ' + \
                'in a shadow directory on /scratch, e.g., if output ' + \
                'directory is /study/mystudy/processed/subj001, images ' + \
                'will be stored in /scratch/mystudy/processed/subj001')
    optparser.add_option( "", "--base-firstepi", action="store_true", \
                dest="base_firstepi", default=False, help=\
        'Align EPI runs to reference EPI image instead of first or last '+\
        'timeseries image.' )
    optparser.add_option( "", "--dry_run", action="store_true", \
                dest="dry_run",default=False, help= \
        "Analyze data and create output yaml file but done't compute anything.")
    optparser.add_option( "", "--debug-tmp", action="store_true",  \
                dest="debug_tmp",default=None, help=\
              "Write tmp files to /tmp/debug_tmp. For debugging purposes only.")
    optparser.add_option( "", "--skull-strip", action="store_true", \
                dest="skull_strip",default=False, \
                help='Skull strip the anatomical reference image.')
    optparser.add_option( "", "--align-fmaps", action="store_true", \
                dest="align_fmaps",default=False, \
                help='Always register fieldmaps with the structural image' + \
                     'image used for spatial normalization.  Otherwise, ' + \
                     'Only register the fieldmaps if they were not acquired ' + \
                     'right after the structural (give or take a shim series.)')
    optparser.add_option( "", "--no-align-fmaps", action="store_true", \
                dest="no_align_fmaps",default=False, \
                help='Never register fieldmaps with the structural image')
    optparser.add_option( "-s", "--skip", action="store", dest="skip", \
                type="int",default=None,\
                help="Number of frames to skip at  the beginning of each run.")
    optparser.add_option( "", "--template", action="store", \
                dest="template_file", type="str",default=None,\
                help="The one and only template file to be used.")
    optparser.add_option( "", "--scratch", action="store", dest="scratch", \
                type="str",default='/scratch',\
                help="Name of scratch partition. Destination for " + \
                     "intermediate time-series data.")
    optparser.add_option( "-o", "--output_dir", action="store", dest="outdir", \
                type="string",default=None,\
                help="Directory where output data are written.  " + \
                     "This overides the value in the template file.")
    optparser.add_option( "", "--followon-script", action="store", \
                dest="followon_script", type="string",default=None,\
                help="Script to be run after preprocess complets." + \
                "It will be called with the output path as the only argument.")

    optparser.add_option( "", "--clean-epi", action="store_true", \
                dest="clean_epi",default=False, \
                help='Remove all epi images.')
    optparser.add_option( "", "--no-slicetime", action="store_true", \
                dest="no_slicetime",default=False, \
                help='Skip slice-timing correction.')
    optparser.add_option( "", "--no-motcor", action="store_true", \
                dest="no_motcorr",default=False, \
                help='Do not do motion and fieldmap correction.')
    optparser.add_option( "", "--no-fmapcor", action="store_true", \
                dest="no_fmapcorr",default=False, \
                help='Skip fieldmpap correction even if a fieldmap exists.')

    opts, args = optparser.parse_args()

    error_log = ""
    if len(args) != 1:
        print "\npreprocess version %s" % version
        errstr = "Expecting 1 argument:\nEnter 'preprocess --help' for usage."
        f = open(c.FMRI_TOOLS_VERSION_FILE,'r')
        version = f.read().strip()
        f.close()
        error_log = error_log + errstr
        raise RuntimeError(errstr)

    # Name the directories.
    topdir = os.path.abspath(args[0])
    print 'Processing %s' % topdir
    if not os.path.exists(topdir):
        errstr = 'preprocess: Cannot access data: %s\n' % topdir
        error_log = error_log + errstr
        sys.stderr.write(errstr)
#        proc.LogErrors(errstr)
        raise IOError(errstr)

    return topdir, opts, error_log

def clean_epi(topdir, opts):
    if opts.outdir:
        yaml_file = '%s/log/preprocess_info.yaml' % opts.outdir
    else:
        dc = DataInfo(topdir, template_file=None)
        yaml_file = '%s/log/preprocess_info.yaml' % dc.procdir
    f = open(yaml_file, 'r')
    info = yaml.load(f.read())
    f.close()
    for key in info.keys():
        if info[key]['type'] == 'epi':
            images = ('imgfile', 'imgfile_t', 'imgfile_m', 'imgfile_mf')
            for image in images:
                prefix = info[key].get(image, None)
                if prefix is None:
                    continue
                fname = '%s%s' % (prefix, info[key]['suffix'])
                if os.path.exists(fname):
                    print 'Deleting %s' % fname
                    os.remove(fname)
                if os.path.exists(fname + '.gz'):
                    print 'Deleting %s' % fname
                    os.remove(fname)
                if info[key]['filetype'] == 'brik':
                    fname = fname.replace('BRIK','HEAD')
                    if os.path.exists(fname):
                        print 'Deleting %s' % fname
                        os.remove(fname)
                    if os.path.exists(fname + '.gz'):
                        print 'Deleting %s' % fname
                        os.remove(fname)

def main(user_email):

    topdir, opts, error_log = parse_cmdline()

    if opts.clean_epi:
#       Delete all epi image files created by last run of preprocess.
        clean_epi(topdir, opts)

  #  # Store the path so we can tell what was done today.
  #  if ismounted(os.path.dirname(c.exams_file)):
  #      f = open(c.exams_file,'r')
# #       f.seek(0,2)
  #      lines = f.readlines()
  #      f.close()
  #      outpaths = []
  #      outlines = []
  #      for line in lines:
  #          words = line.strip().split()
  #          if words[-1] not in outpaths:
  #              outpaths.append(words[-1])
  #              outlines.append(line)
  #      if topdir not in outpaths:
  #          timestamp = datetime.today().strftime('%a %b %d, %Y; %X')
  #          outlines.append('%s; %s\n' % (timestamp,topdir))
  #          f = open(c.exams_file,'w')
  #          f.writelines(outlines)
  #          f.close()

##   Set flag to compute the item.
    if opts.keep_epi_all or opts.hog:
        opts.keep_epi_raw = True
        opts.keep_epi_mot = True

    try:
#       Create processing object.
        proc = ProcData(opts)
        proc.error_log = error_log
    except RuntimeError, errmsg:
        proc.errors = True
        proc.term_mesg = '\nAbnormal termination.\n'
        errstr = 'preprocess: Error during initialization.\n%s\n' % errmsg
        sys.stderr.write(errstr)
        error_log = error_log + errstr
        sys.exit(1)

    try:
#       Initialize data strucures by scanning all subdirectories.
        proc.Initialize(topdir, opts.redo, opts.verbose, \
                opts.dry_run, opts.skip, opts.scratch, opts.no_email, \
                opts.template_file)

        if opts.clean_epi:
#           Ensure that all epis and ancillary files are recomputed.
            proc.CleanEpi()
            sys.exit(1)

        if proc.template_type == 'default':
            sys.stderr.write('No template found.  Exiting\n')
            proc.term_mesg = '\nAbnormal termination.\n'
            sys.exit(1)


        if opts.dry_run:
#           Test run. info structure was computed, so exit.
            proc.DumpInfo()
            sys.stdout.write(\
            '\nFinished initialization. Information used to guide ' + \
            'preprocessing was\nwritten to %s\n' % proc.dumpfile)
            sys.exit()

        proc.ConvertAnat()
        proc.ProcessDTI()
        proc.ProcessAsl()
        if not opts.no_fmapcorr:
            proc.MakeFieldmaps()
            proc.AlignFieldmaps()
        proc.PruneEpiEntries()
        proc.ExtractFirstEpi()
        proc.ReconEpis()
        proc.ConvertRtEpis()
        if not opts.no_motcorr:
            proc.CorrectMotion()
            proc.JumpCensor()
            if not opts.no_fmapcorr:
                proc.FieldmapCorrection()
                proc.ComputeSNR()
#       Create links to structural images.
        proc.LinkAnat()
        proc.CleanUp()
    except RuntimeError, errmsg:
        proc.errors = True
        proc.term_mesg = '\nAbnormal termination.\n'
        errstr = except_msg()
        proc.LogErrors(errstr)
        proc.CleanUp()
        sys.exit()
    except ScannerError, err:
        proc.errors = True
        proc.term_mesg = '\nAbnormal termination.\n'
        errstr = except_msg('--- Error in template file. ---')
        proc.LogErrors(errstr)
        proc.CleanUp()
#       Fatal error, exit
        sys.exit(1)
    except SystemExit:
        pass
#        proc.term_mesg = '\nAbnormal termination.\n'
    except KeyboardInterrupt:
        proc.term_mesg = '\nTerminated by ctrl-c\n'
        sys.exit()
    except:
        proc.errors = True
        proc.term_mesg = '\nAbnormal termination.\n'
        errstr = except_msg(__name__)
        proc.LogErrors(errstr)
        proc.CleanUp()

#   Change permissions.
    try:
        uid = os.getuid()
        if hasattr(proc, 'procdir'):
            for root,dummy,files in os.walk(proc.procdir):
                for fname in files:
                    fullname = '%s/%s' % (root, fname)
                    if os.path.exists(fullname):
                        st = os.stat(fullname)
                        if st.st_uid == uid:
#                           File ownership OK, add user and group write access.
                            os.chmod(fullname, S_IRWXU | S_IRWXG )
    except RuntimeError, err:
#       This is a nonfatal error.
        proc.errors = True
        proc.term_mesg = '\nAbnormal termination.\n'
        proc.LogErrors("Warning: Could not change ownership of output files.  This does not affect results.")


#   Dump status information in the info dictionary to disk and compress
#   the raw data.
    try:
        proc.DumpInfo()
    except IOError, errstr:
        proc.errors = True
        proc.term_mesg = '\nAbnormal termination.\n'
        errstr = except_msg(errstr)
        proc.LogErrors(errstr)
        proc.CleanUp()

#   Tell them its done.
    if proc.tmplt is not None:
        overall_msg = proc.SummaryErrorMessage()
        if not proc.no_email:
            EmailResults(proc.tmplt['email'], overall_msg, \
                    proc.topdir, proc.dumpfile, proc.logfile, proc.motcor_summary)

        if proc.errors and not proc.no_email:
#           Mail me the errors.
            EmailResults('ollinger@wisc.edu', overall_msg, \
                    proc.topdir, proc.dumpfile, proc.logfile, proc.motcor_summary)
        else:
            if proc is None:
                print 'Abnormal termination.'
            else:
                print proc.term_mesg
            if opts.followon_script is not None:
                cmd = '%s %s' % (opts.followon_script, proc.procdir)
                print cmd
                exec_cmd(cmd)

if __name__ == '__main__':
    try:
        user_email = None
        main(user_email)
    except RuntimeError, errmsg:
        sys.stderr.write('\nError occured in preprocess.\n%s\n\n' % errmsg)
        EmailResults(user_email, errmsg, sys.argv, None, '/dev/null', '')
        sys.exit(1)
