#!/usr/bin/env python

ID = "$Id:"[1:-1]

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
import math
import time
from optparse import OptionParser

import wx
from numpy import zeros, float, ubyte, array, isnan, integer, empty, \
                  short, fromstring, arange, ones, where, abs

from wbl_util import SshPipe, except_msg, OpenRemote, SshExec
from subprocess import PIPE, Popen

UPDATE_INTERVAL = 60 # Duration of timer loop in ms.
DATA_RATE = 2000  # Data rate in bytes/sec
READ_LENGTH = 4*(int(DATA_RATE*UPDATE_INTERVAL/1000.)/4) 
PACKET_TIME=.004
PACKET_LGTH = 8
PACKET_WDS = PACKET_LGTH/2
#LINUX_HOST = 'mentha'
#LINUX_USER = 'mri'
PHYSIO_STATUS_FILE = '.get_physio_status.txt'
SCAN_INFO_FILE = '.scanner_info.txt'
CHANNEL_NAMES = ['ECG2','ECG3','Resp','PPG']
IOCODES = ['init', 'gogo', 'stop', 'hold', 'wait', 'done', 'exit']

site_specific = { \
    'waisman': { \
        'linux_host': 'mentha', \
        'linux_user': 'mri', \
        'linux_password': None, \
        'linux_dir':   '/local', \
        }, \
    'heri': { \
        'linux_host': '144.92.3.189', \
        'linux_user': 'mri', \
        'linux_password': 'iat@heri', \
        'linux_dir':    '__HOME__', \
        }
    }
SITE = 'waisman'


YDIM = 128
WXDIM = 1536
LABELDIM = 40
LABEL_WIDTH = 60

WINDOW_WIDTH_NOMINAL = 10 # width in seconds
HASH_WIDTH = YDIM
HASH_STEP = 50

SCANNER_FILE = '.scanner_info.txt'
ENDOFSCAN_TIMEOUT = 5

CHILD_STATUS_TEXT = {'init':'Click "Wait for TTL" after prescan.', \
                     'wait':'Waiting for TTL pulse.', \
                     'gogo':'Acquiring data.', \
                     'stop':'Flushing buffers and writing mat file.', \
                     'hold':'Flushing buffers and writing mat file.', \
                     'done':'Acquisition complete.', \
                     'exit':'Exiting.'}

GUI_STATUS_TEXT =   {'init':'Initializing.', \
                     'wait':'Waiting for TTL pulse.', \
                     'gogo':'Acquiring data.', \
                     'stop':'Acquiring data.', \
                     'hold':'Acquiring data.', \
                     'done':'Acquisition complete.', \
                     'exit':'Exiting.'}

IOCODES = ['init', 'gogo', 'stop', 'hold', 'wait', 'done']
IOCODES_ACK = map(lambda x: '%sack' % x, IOCODES)

#def exec_linux_cmd(args, verbose=False):
##    print "ssh %s@%s %s" % (LINUX_USER, LINUX_HOST, args)
#    cmd = "ssh %s@%s %s" %  (LINUX_USER, LINUX_HOST, args)
#    if verbose:
#        print cmd
#    f = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, executable='/bin/bash')
#    output, errmsg = f.communicate()
#    errs = f.wait()
#    if len(errmsg) > 0:
#        raise IOError('Error executing %s\n%s\n' % (cmd, errmsg))
#    return output

class StripChart(wx.Panel):

    def __init__(self, topframe, nchan=3, ID=-1, size=(1024, 384), pos=wx.DefaultPosition, label='', chan_names=CHANNEL_NAMES, verbose=False, debug=False):
        wx.Panel.__init__(self, topframe, ID, pos, size, wx.NO_BORDER,label)

        self.exam = ''
        self.patid = ''
        self.serno = ''
        self.psdname = ''
        self.run_start_time = time.time()

        self.verbose = verbose
        self.debug = debug
        self.SetBackgroundColour(wx.BLACK)
        self.frame_xdim = size[0]
        self.frame_ydim = size[1]

#       Axis and lettering.
        self.axis_width = LABEL_WIDTH

        self.xdim = self.frame_xdim - self.axis_width
        self.ydim = YDIM
        self.nchan = nchan
        self.chan_names = chan_names
        self.pos_xaxis = self.ydim*ones(self.nchan)

        self.fs = self.GetFont().GetPointSize()
        self.fs = 14
        self.font = wx.Font(self.fs,wx.SWISS,wx.NORMAL,wx.BOLD)
        self.label_fs = 12
        self.label_font = wx.Font(self.label_fs,wx.SWISS,wx.NORMAL,wx.BOLD)

        self.axis_color =  array([0, 255, 255]).astype(ubyte)
        self.frame_color = array([0, 255, 255]).astype(ubyte)
        self.sec_per_div = 1.
        self.rescale = True


        self.plot_data = zeros([self.xdim, self.nchan], integer)
        self.plot_scl = zeros([self.xdim, self.nchan], integer)
        self.scrap = zeros([1, self.nchan], integer)
        self.scrap_off = 0
        self.plotmin = zeros(self.nchan, float)
        self.plotmax = zeros(self.nchan, float)
        self.scl = ones(self.nchan, float)
        self.paused = False

        self.TimeStep(1.)
        self.SetupDecorations()
        self.time0 = time.time()
        self.scale_time = self.time0
        self.start = True
        self.last_serno = -1
        self.last_outfile = 'None'

        self.DrawFrame()

    def TimeStep(self, sec_per_div):
        self.sec_per_div = sec_per_div
        self.time_step = 2*int(float(sec_per_div)/(PACKET_TIME*HASH_STEP))
        if self.verbose:
            print 'Time step: %d pts' % self.time_step
        if self.time_step < 1.:
            self.time_step = 1.

    def SetupDecorations(self):

#       Set hash marks for every HASH_STEP pixels.
        nsteps = int(WXDIM/HASH_STEP) + 1
        xposs = (HASH_STEP*arange(nsteps) + self.axis_width).tolist()
        self.hash_marks = []
        for ch in xrange(self.nchan):
            ypos = ch*self.ydim + self.ydim/2
            for xpos in xposs:
                self.hash_marks.append(\
                        (xpos, ypos-HASH_WIDTH/2, xpos, ypos+HASH_WIDTH/2))

#       Now define the axes and frames.
        self.axes_list = []
        self.box_list = []
        for ch in xrange(self.nchan):
            self.axes_list.append( \
                    (self.axis_width, ch*self.ydim+self.pos_xaxis[ch], \
                     self.frame_xdim, ch*self.ydim+self.pos_xaxis[ch]))
            self.box_list.append((self.axis_width, (ch+1)*self.ydim, \
                                  self.frame_xdim, (ch+1)*self.ydim))
        self.axes_list.append((self.axis_width, 0, self.axis_width, self.nchan*self.ydim))
        self.box_list.append((0, self.nchan*self.ydim, \
                              self.axis_width, self.nchan*self.ydim))

    def Update(self, data_in):
#       Initialize.
        if self.paused:
            return
        if self.start:
            self.time0 = time.time()
            self.start = False

        nscrap = self.scrap.shape[0]
        n_in = data_in.shape[0]
        ntot = n_in + nscrap
        alldata = zeros([ntot, self.nchan], integer)
        alldata[:nscrap, :] = self.scrap
        alldata[nscrap:, :] = data_in
        n_new = ntot/self.time_step
        self.scrap = alldata[n_new*self.time_step+1:, :]
#        print 100,'nscrap: %d, n_in: %d, n_new: %d, ntot: %d' % (nscrap, n_in, n_new, ntot)

        if n_new == 0:
            return

        idx = (self.time_step*arange(n_new)).tolist()
        plot_new = zeros([n_new, self.nchan], integer)
        for ch in xrange(self.nchan):
            plot_new[:,ch] = alldata[:,ch].take(idx)

        self.plot_data[:-n_new,:] = self.plot_data[n_new:,:]
        self.plot_data[-n_new:,:] = plot_new[:n_new,:]

#       Find scale factor.
        if self.rescale:
            self.rescale = False
            self.Rescale()
        plot_scl = self.scl*(self.plot_data - self.plotmin)
        if plot_scl.max() > self.ydim or plot_scl.min() < 0:
            self.Rescale()
            plot_scl = self.scl*(self.plot_data - self.plotmin)

#       Plot it.
        x_coords = arange(self.xdim).astype(integer)
        y_coords = zeros([self.nchan, self.xdim], integer)
        for ch in xrange(self.nchan):
            y_coords[ch,:] = self.nchan*self.ydim - \
                        (plot_scl[:,ch] + ch*self.ydim).astype(integer)
        self.DrawFrame()
        self.DrawPlot(x_coords, y_coords)

    def Clear(self):
        self.plot_data[:,:] = 0

    def Rescale(self):
        self.plotmax = self.plot_data.max(axis=0)
        self.plotmin = self.plot_data.min(axis=0)
        self.scl = .95*float(self.ydim)/(self.plotmax - self.plotmin)
        self.scl = where(self.plotmax == self.plotmin, 1., self.scl)
        self.pos_xaxis = self.scl*self.plotmin
        self.pos_xaxis = where(self.pos_xaxis < -self.ydim, -self.ydim, self.pos_xaxis)
        self.pos_xaxis = where(self.pos_xaxis > 0, 0, self.pos_xaxis)
        self.SetupDecorations()

    def DrawFrame(self):
        dc = wx.ClientDC(self)
        dc.SetTextForeground("goldenrod")
        dc.Clear()
        pen = dc.GetPen()
        dc.SetPen(pen)

#       Draw the axes, boxes, and hash marks.
        pen.SetColour('green')
        pen.SetWidth(1)
        dc.DrawLineList(self.axes_list, pens=pen)
        pen.SetColour('green')
        pen.SetWidth(2)
        dc.DrawLineList(self.box_list, pens=pen)

        pen = wx.Pen('white', style=wx.USER_DASH, width=1)
        pen.SetDashes([1,1,0,0,1,1,0,0,1,1,0,0,1,1,0,0])
        pen.SetWidth(1)
        dc.DrawLineList(self.hash_marks, pens=pen)

#       Now for the annotations
        dc.SetPen(pen)
        pen.SetWidth(1)
        dc.SetFont(self.font)
        dc.SetTextForeground("cyan")
        line_hght = 20
        for ch in xrange(self.nchan):
            dc.DrawText(self.chan_names[self.nchan-ch-1], self.axis_width, ch*self.ydim)
        xpos = 0
        ypos = self.nchan*self.ydim
        dc.DrawText('%3.1f seconds per division' % self.sec_per_div, xpos, ypos)
#        sec = time.time() - self.time0
        sec = time.time() - self.run_start_time
        min = int(sec/60)
        sec -= min*60
        ypos += line_hght
        dc.DrawText('Elapsed time: %02d:%02d'%(min,sec), xpos, ypos)
        xpos = 200
        ypos = self.nchan*self.ydim
        dc.DrawText('Exam number: %s' % self.exam, xpos, ypos)
        ypos += line_hght
        dc.DrawText('Subject ID: %s' % self.patid, xpos, ypos)
        ypos += line_hght
        dc.DrawText('Series Number: %s' % self.serno, xpos, ypos)
        ypos += line_hght
        dc.DrawText('Pulse sequence: %s' % self.psdname, xpos, ypos)
        xpos += 300
        ypos = self.nchan*self.ydim
#        dc.DrawText('Series: %s' % self.last_serno, xpos, ypos)
#        ypos = self.nchan*self.ydim + line_hght
        dc.DrawText('File name: %s' % self.last_outfile, xpos, ypos)
#            self.exam, self.patid, self.psdname, self.serno = data.split('_')

        self.LabelAxes(dc)

    def LabelAxes(self, dc):
        pen = dc.GetPen()
        dc.SetPen(pen)
        dc.SetTextForeground("goldenrod")
        pen.SetWidth(2)
        dc.SetFont(self.label_font)
        fxdim, fydim = self.label_font.GetPixelSize()
        for ch in xrange(self.nchan):
            y0 = (self.nchan-ch)*self.ydim + self.pos_xaxis[ch]
            ymax = ch*self.ydim + self.scl[ch]*self.plotmax[ch]
            ymin = (ch+1)*self.ydim + self.scl[ch]*self.plotmin[ch]
#            dc.DrawText('0', self.axis_width-fxdim-5, y0-fydim)
            str = '%d' % self.plotmin[ch]
            dc.DrawText(str, self.axis_width-len(str)*fxdim-5, \
                                            (self.nchan-ch)*self.ydim-fydim)
            str = '%d' % self.plotmax[ch]
            dc.DrawText(str, self.axis_width-len(str)*fxdim-5, \
                                            (self.nchan-ch-1)*self.ydim)

    def DrawPlot(self, x_coords, y_coords):
#       Draw the graph.
        dc = wx.ClientDC(self)
        pen = wx.Pen('yellow', style=wx.SOLID, width=1)
        pen.SetWidth(1)
        lines = []
        for i in xrange(self.nchan):
            for j in xrange(len(x_coords)-1):
                lines.append(\
                (x_coords[j]+self.axis_width, y_coords[i][j], x_coords[j+1]+self.axis_width, y_coords[i][j+1]))
        pen.SetWidth(1)
        pen.SetColour('yellow')
        dc.DrawLineList(lines, pens=pen)

    def GetFilename(self):
#       Open file dialog box.
        wildcard = "*.dat | *.mat "
        dlg = wx.FileDialog(self,message="Choose File", \
                            defaultDir=os.getcwd(), \
                            defaultFile="", \
                            wildcard="*", \
                            style=wx.SAVE | wx.CHANGE_DIR)

        if dlg.ShowModal() == wx.ID_OK:
            self.dialog_fname = dlg.GetPaths()[0]
            dlg.Destroy()
        else:
            self.dialog_fname = None
            sys.stderr.write("Read dialog failed.\n")
            dlg.Destroy()
            return None

class PhysioTop(wx.Frame):

    def __init__(self):
        self.auto_trigger = False

    def Init(self, outfile=None, update_interval=UPDATE_INTERVAL, title='', \
             test_pattern=False, verbose=False, soft_trigger=False, \
             exam=None, series=None, id=None, debug=False): 


        self.SetupSite()
        self.verbose = verbose
        self.debug = debug
        if test_pattern:
            self.test_pattern = '--test-pattern --soft-trigger'
        elif soft_trigger:
            self.test_pattern = '--soft-trigger'
        else:
            self.test_pattern = ''
        if debug:
            self.test_pattern += ' --debug'
#        if dabout:
#            self.test_pattern += ' --dabout'
        self.channels = [2,3]
        self.nchan = len(self.channels)
        self.last_summary_string = ''
        self.tmp_time = zeros(1, float)
        self.child_iocode = ''
        self.last_child_iocode = ''
        x = []
        for code in IOCODES:
            x.append((code, 0))
        self.sent_iocodes = dict(x)
        self.tail = ''
        self.passctr = 0
        self.restart = 0


        self.button_hght = 100
        wxdim = WXDIM
        wydim = self.nchan*YDIM + LABELDIM
        wx.Frame.__init__(self, None, size=(wxdim, wydim+self.button_hght), \
                                                                title=title)
        
        self.update_interval = update_interval
        self.read_length = READ_LENGTH
        self.SetBackgroundColour("darkslategray")

#       Create strip chart object.
        self.chart = StripChart(self, nchan=self.nchan, size=(wxdim, wydim), chan_names=('Resp', 'PulseOx'), verbose=self.verbose, debug=self.debug)


        if outfile is not None:
            self.outfile = outfile
        else:
            self.outfile = ''
            if exam is not None:
                self.outfile += 'E%s_' % exam
            if series is not None:
                self.outfile += 'S%s_' % series
            if id is not None:
                self.outfile += 'ID%s_' % id
            if len(self.outfile) > 0:
                self.outfile = self.outfile[:-1]
        if self.outfile != 'auto' and len(self.outfile) == 0:
#           No output file specified and no study info.
            self.chart.GetFilename()
            self.outfile = self.chart.dialog_fname
            if self.outfile is None:
                raise RuntimeError('Invalid output file')
        if not self.outfile.startswith('/study'):
            self.outfile = '/local/%s' % os.path.basename(self.outfile)

#       Create status bar
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(3)

        self.WaitTTLButton()
        self.AutoTTLButton()
        self.StopButton()
        self.RestartButton()
        self.PauseButton()
        self.RescaleButton()
        self.HalfSecPerDiv()
        self.OneSecPerDiv()
        self.TwoSecPerDiv()
        self.FourSecPerDiv()
        self.ExitButton()

        self.CloseWindow()


        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnsizer.Add(self.go, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.auto, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.stop, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.restartb, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.pause, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.rescale, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.halfdiv, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.onediv, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.twodiv, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.fourdiv, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2 )
        btnsizer.Add(self.exit, 1, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, border=2)
        btnsizer.SetDimension(0, 0, wxdim, self.button_hght/2)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.chart,            1, wx.ALIGN_TOP | wx.ALL, border=2)
        sizer.Add(btnsizer) #, 1, wx.ALIGN_BOTTOM | wx.ALL, border=2)
        self.SetSizerAndFit(sizer)
        self.sizer = sizer

#       Create timer events to implement real-time loop.
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimerEvent, self.timer)
        status = self.timer.Start(self.update_interval, oneShot=True)
        self.scanfile = '%s/%s' % (os.getenv('HOME'), SCANNER_FILE)
        self.scanfile_mtime = 0
        self.remote_mtime = 0
        self.GetScanInfo()

        self.time0 = time.time()
        self.data_timer = time.time()
        self.iocodem1 = '    '
        self.child_iocodem1 = '    '
        self.error_msg = ''
        self.iocode = 'init'
        self.child_iocode = 'init'

        self.speed_buttons = {.5: self.halfdiv, \
                               1.: self.onediv, \
                               2.: self.twodiv, \
                               4.: self.fourdiv}
        self.time_stepm1 = -1

        self.KillGetPhysio()

        try:
            self.error_msg = 'Starting acquisition task on %s.' % self.linux_host
            self.StartGetPhysio()
        except OSError, errmsg:
            sys.stderr.write('\n%s\n%s\n' % (errmsg, except_msg()))
            self.Exit()
        except KeyboardInterrupt, errmsg:
            self.Exit()

    def GetRemoteHome(self, host, user, password):
#       Store data in home directory.        
        status, dname, errs = SshExec(host, user, password, 'echo ${HOME}')()
        if status:
            raise RuntimeError('Could not retrieve remote home directory')
        return dname

    def SetupSite(self):
#       Get site-specific information.
        self.linux_user = site_specific[SITE]['linux_user']
        self.linux_host = site_specific[SITE]['linux_host']
        self.linux_password = site_specific[SITE]['linux_password']
        self.linux_dir = site_specific[SITE]['linux_dir']
        self.scan_info_file = '%s/%s' % (self.linux_dir, SCAN_INFO_FILE)
        self.physio_status_file = '%s/%s' % (self.linux_dir, PHYSIO_STATUS_FILE)
        if self.linux_dir == '__HOME__':
#           Store data in home directory.
            self.linux_dir = self.GetRemoteHome(self.linux_host, \
                                    self.linux_user, self.linux_password)
    
    def GetScanInfo(self, force=False):
        st = os.stat(self.scanfile)
        if self.scanfile_mtime != st.st_mtime or force:
            self.scanfile_mtime = st.st_mtime
            f = OpenRemote(self.scan_info_file, 'r', self.linux_host, \
                                                        self.linux_user)
#            f = open(self.scanfile, 'r')
            data = f.read().strip()
            f.close()
            wds = data.split('*')
            if len(wds) == 5:
                self.exam, self.patid, self.psdname, self.serno, outdir = wds
            else:
                self.error_msg = 'Error reading scanner info: %s\n' % data
                sys.stderr.write(self.error_msg)
            self.psdname = self.psdname.split('/')[-1]
            self.chart.exam = self.exam
            self.chart.patid = self.patid
            self.chart.psdname = self.psdname
            self.chart.serno = self.serno
            self.new_scaninfo = True

    def UpdateStatus(self):
        self.statusbar.SetStatusText(CHILD_STATUS_TEXT[self.child_iocode], 0)
        self.statusbar.SetStatusText(GUI_STATUS_TEXT[self.iocode], 1)
        self.statusbar.SetStatusText(self.error_msg, 2)

    def StartGetPhysio(self):
        self.pipe = None
        options = self.test_pattern
        if self.verbose:
            options += ' -v '
        cmd = 'get_physio --pipe %s auto' % options
        if self.verbose:
            print cmd
        self.pipe = SshPipe(cmd, self.linux_host, self.linux_user, \
                                    read_noblock=True, readerr_noblock=True)
        if self.pipe is None:
            raise OSError('Unidentified error in SshPipe')

    def KillGetPhysio(self):
#        text = exec_linux_cmd("ps -aef | grep get_physio", verbose=False)
        cmd = "ps -aef | grep get_physio"
        status, text, errs = SshExec(self.linux_host, self.linux_user, \
                                                self.linux_password, cmd)()
        if status:
            raise RuntimeError('Error find pid')
        pids = ''
        for line in text.split('\n'):
            if 'get_physio' in line and 'grep' not in line:
                wds = line.split()
                pids = '%s %s' % (pids, line.split()[1])
        if len(pids) > 0:
            print 'Killing get_physio tasks on %s' % self.linux_host
#            exec_linux_cmd('kill -s SIGINT %s' % pids, verbose=False)
            cmd = 'kill -s SIGINT %s' % pids
            status, text, errs = SshExec(self.linux_host, self.linux_user, \
                                                self.linux_password, cmd)()
            if status:
                raise RuntimeError('Error killing get_physio tasks.')

    def RestartGetPhysio(self):
        self.error_msg = 'Wait while acquisition process is restarting ...'
        self.KillGetPhysio()
        self.StartGetPhysio()
        self.child_iocode = 'init'

    def CheckChildError(self, no_restart=False):
#       Check for error messages from get_physio
        err = self.pipe.ReadError()
        if 'Error' in err:
#           Exception occurred in get_physio.
            self.error_msg = 'Error occurred during acquistion. Restarting ...'
            print self.error_msg
            print err
            self.RestartGetPhysio()
        else:
            iocode = None
            i = 0
            while i < len(err)-4:
                if err[i:i+4] in IOCODES:
                    iocode = err[i:i+4]
                    i += 4
                else:
                    i += 1
            if iocode is not None:
                self.child_iocode = iocode
                if      iocode in ('hold', 'stop', 'done') and \
                   self.iocode in ('gogo', 'hold'):
                    self.SetStop()
                    self.iocode = iocode
                elif self.iocode in ('hold', 'stop', 'wait', 'init'):
                    self.iocode = iocode
                else:
                    print err
            
            return err

    def LogMessage(self, msg):
        sys.stdout.write('%s\n' % msg)
        sys.stdout.flush()

    def IoCodeComm(self):
        value = self.pipe.ReadError()
        if len(value) > 0:
#            print 'IoCodeComm: __%s__' % value
            iocode = self.ParseInput(value)
#            print 'IoCodeComm: __%s__' % iocode
            if iocode is not None and self.debug:
                self.LogMessage('IoCodeComm::iocode: %s' % iocode)
            if iocode is not None:
                self.child_iocode = iocode
#                self.SendIoCode('%sack' % iocode)
#                self.LogMessage('IoCodeComm::iocode: %s' % iocode)

    def SendIoCode(self, iocode):
        self.WriteChild(iocode)
        if not iocode.endswith('ack'):
            self.sent_iocodes[iocode] += 1
        if self.debug:
            self.LogMessage('SendIoCode: Sent %s' % iocode)


    def ParseInput(self, value):
#       Look for acks sent from get_physio.
        acks, value = self.FindCodeInString(list(IOCODES_ACK), value)
        for ack in acks.keys():
            if self.sent_iocodes.has_key(ack[:4]):
                self.sent_iocodes[ack[:4]] = 0
            else:
                self.LogMessage( \
                'iocode %s acknowledged but no record of it being sent.' % ack)
                self.error_msg = \
                'iocode %s acknowledged but no record of it being sent.' % ack
#       Look for iocodes sent from get_physio (i.e., 'wait' or 'stop')
        codes, value = self.FindCodeInString(list(IOCODES), value)
#        print 301, '__%s__'  % value, codes
        keys = codes.keys()
        if len(keys) > 1:
            nmax = -1
            for key in keys:
                if codes[key] > nmax:
                    nmax = codes[key]
                    keymax = key
            code = keymax
        elif len(keys) == 1:
            code = keys[0]
        else:
            code = None
        if self.debug:
            self.LogMessage('ParseInput::output code: %s' % code )
        return code


    def FindCodeInString(self, code_list, value):
        fnd = {}
        test = map(lambda x: x in value, code_list)
#        print 400, '__%s__' % value,test, code_list
#        n = 0
        while True in test:
            i = test.index(True)
            code = code_list[i]
#            print 410,test.index(True), test
            test[i] = False
            n = value.find(code)
            while n >= 0:
                fnd[code] = n
                value = value[:n] + value[n+len(code):]
                n = value.find(code)
#           Remove code from input string.
##            value = ''.join(value.split(code))
#            n += 1
        return fnd, value

    def WaitTTLButton(self):
#       Wait for sync pulse from scanner.
        self.go_id = wx.NewId()
#        self.go = wx.Button(self, self.go_id, "Wait For TTL", size=(100, 50), \
#                            pos=wx.DefaultPosition)
        self.go = wx.ToggleButton(self, self.go_id, "Wait For TTL", \
                            size=(100, 50), pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnWaitTTL, id=self.go_id)
        self.go.SetToolTipString('Click after prescan to enable triggering')

    def SetWaitTTLButton(self, value):
        self.go.SetValue(value)
    
    def AutoTTLButton(self):
#       Wait for sync pulse from scanner with auto retriggering.
        self.auto_id = wx.NewId()
        self.auto = wx.ToggleButton(self, self.auto_id, "Auto Trigger", \
                            size=(100, 50), pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnAutoWaitTTL, id=self.auto_id)
        self.go.SetToolTipString('Click after prescan. Will trigger automatically on every sync pulse after that.  If RF Unblank is used as a sync pulse, acquisitions will be triggered by prescan and reference scans.')

    def SetAutoWaitTTLButton(self, value):
        self.auto.SetValue(value)
    
    def StopButton(self):
#       Terminate data collection.
        self.stop_id = wx.NewId()
        self.stop = wx.ToggleButton(self, self.stop_id, "Stop", \
                            size=(100, 50), pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnStop, id=self.stop_id)
        self.go.SetToolTipString("If you can't figure this one out you're in dep trouble.")

    def SetStopButton(self, value):
        self.stop.SetValue(value)

    def RestartButton(self):
#       Terminate data collection.
        self.restart_id = wx.NewId()
        self.restartb = wx.ToggleButton(self, self.restart_id, "Restart", \
                                    size=(100, 50), pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnRestart, id=self.restart_id)
        self.restartb.SetToolTipString('Restart low-level acquisition processes.')

    def SetRestartButton(self, value):
        self.restartb.SetValue(value)

    def HalfSecPerDiv(self):
        self.halfdiv_id = wx.NewId()
        self.halfdiv = wx.ToggleButton(self, self.halfdiv_id, ".5 sec/div", \
                                size=(100, 50), pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnHalfDiv, id=self.halfdiv_id)

    def OneSecPerDiv(self):
        self.onediv_id = wx.NewId()
        self.onediv = wx.ToggleButton(self, self.onediv_id, "1 sec/div", \
                                size=(100, 50), pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnOneDiv, id=self.onediv_id)

    def TwoSecPerDiv(self):
        self.twodiv_id = wx.NewId()
        self.twodiv = wx.ToggleButton(self, self.twodiv_id, "2 sec/div", \
                                size=(100, 50), pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnTwoDiv, id=self.twodiv_id)

    def FourSecPerDiv(self):
        self.fourdiv_id = wx.NewId()
        self.fourdiv = wx.ToggleButton(self, self.fourdiv_id, "4 sec/div", \
                                size=(100, 50), pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnFourDiv, id=self.fourdiv_id)

    def PauseButton(self):
        self.pause_id = wx.NewId()
        self.pause = wx.ToggleButton(self, self.pause_id, "Pause", \
                            pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnPause, id=self.pause_id)
        self.go.SetToolTipString('Pause data display. Acquisition is unaffected.')

    def RescaleButton(self):
        self.rescale_id = wx.NewId()
        self.rescale = wx.ToggleButton(self, self.rescale_id, "Rescale", \
                            pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnRescale, id=self.rescale_id)

    def ExitButton(self):
        self.exit_id = wx.NewId()
        self.exit = wx.ToggleButton(self, self.exit_id, "Exit", \
                            pos=wx.DefaultPosition)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnExit, id=self.exit_id)
        self.exit.SetToolTipString("")

    def CloseWindow(self):
        self.close_id = wx.NewId()
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

    def OnCloseWindow(self, evt):
        self.Exit()

    def OnWaitTTL(self, evt):
        self.iocode = 'wait'
        self.SendIoCode('wait')
        self.chart.time0 = time.time()
        self.passctr = 0
        self.auto_trigger = False
        self.chart.Clear()
#        junk = self.pipe.Read() # Clear the input pipe.
        self.error_msg = 'Last Command: Manual wait for TTL pulse.'

    def OnAutoWaitTTL(self, evt):
        self.iocode = 'wait'
        self.SendIoCode('wait')
        self.chart.time0 = time.time()
        self.passctr = 0
        self.auto_trigger = True
        self.chart.Clear()
#        junk = self.pipe.Read() # Clear the input pipe.
        self.error_msg = 'Last Command: Auto wait for TTL pulse.'

    def OnStop(self, evt):
        self.SendIoCode('stop')
        self.error_msg = 'Last Command: Stop acquisition.'

    def OnRestart(self, evt):
        self.restart = 1

    def OnRescale(self, evt):
        self.chart.rescale = True
        self.rescale.SetValue(False)

    def OnHalfDiv(self, evt):
        self.chart.TimeStep(.5)

    def OnOneDiv(self, evt):
        self.chart.TimeStep(1.)

    def OnTwoDiv(self, evt):
        self.chart.TimeStep(2.)

    def OnFourDiv(self, evt):
        self.chart.TimeStep(4.)

    def SpeedPushButtons(self):
        for speed in self.speed_buttons.keys():
            if speed == self.chart.sec_per_div:
                self.speed_buttons[speed].SetValue(True)
            else:
                self.speed_buttons[speed].SetValue(False)
#                apply(self.speed_buttons[speed], (False))

    def OnPause(self, evt):
        if self.chart.paused:
            self.chart.paused = False
#            self.error_msg = self.pause_status
        else:
            self.chart.paused = True
#            self.pause_status = self.status_text
#            self.error_msg = 'Strip chart display paused.'

    def WriteChild(self, data, ignore_errors=False):
        try:
            self.pipe.Write(data)
            self.pipe.Flush()
        except (OSError, IOError), errmsg:
            if not ignore_errors:
                sys.stderr.write('\n%s\n' % except_msg())
                self.Exit()

    def OnTimerEvent(self,evt):
        """
        This gets executed at a regular frequence.
        """
        try:
            self.MainLoop()
        except (OSError, IOError), errmsg:
            sys.stderr.write('\n%s\n%s\n' % (errmsg, except_msg())) 
            self.Exit()
        except:
            sys.stderr.write('\n%s\n' % (except_msg())) 
            self.Exit()

    def LogIoCodes(self):
        if self.iocode != self.iocodem1 or \
           self.child_iocode != self.child_iocodem1:
            print 'iocodes: GUI_child = %s_%s' % \
                                    (self.iocode, self.child_iocode)
            self.iocodem1 = self.iocode
            self.child_iocodem1 = self.child_iocode

    def FlushInput(self):
        junk = self.pipe.Read()

    def MainLoop(self):

        start_time = time.time()

        if self.time_stepm1 != self.chart.sec_per_div:
            self.SpeedPushButtons()
            self.time_stepm1 = self.chart.sec_per_div

#       Update summary info.
        n_1sec = int(1000/UPDATE_INTERVAL)
        if self.passctr % 2*n_1sec == 0:
            if self.child_iocode in ('init', 'done', 'wait', 'hold'):
                self.GetRemoteStatus() # Check for output file name.
            self.GetScanInfo()
            self.UpdateStatus()

#       Check for I/O codes from child process.
        self.IoCodeComm()

        self.LogIoCodes()

        if self.restart == 1:
            self.SetRestartButton(True)
            self.restart += 1
        elif self.restart == 2:
            self.RestartGetPhysio()
            self.SetRestartButton(False)
            self.restart = 0
        if self.iocode == 'init':
            self.chart.run_start_time = time.time()
            self.chart.time0 = time.time()
            if self.auto_trigger:
                self.iocode = 'wait'
        elif self.iocode == 'wait':
            self.data_timer = time.time()
            self.FlushInput()
            if self.child_iocode == 'gogo':
                self.iocode = 'gogo'
                self.passctr = 0
                self.SetAutoWaitTTLButton(False)
                self.SetWaitTTLButton(False)
            else:
                if self.auto_trigger:
                    self.SetAutoWaitTTLButton(True)
                else:
                    self.SetWaitTTLButton(True)
            self.chart.Clear
        elif self.iocode == 'gogo':
#           Pipe is ready.  Read it and process.
            self.ProcessData()
            if self.child_iocode in ('stop', 'hold', 'done', 'init', 'wait'):
                self.iocode = 'done'
            if (time.time() - self.data_timer) > ENDOFSCAN_TIMEOUT:
#               Timed out.  Scan must have ended.
                self.SendIoCode('stop')
                self.tail = ''
        elif self.iocode in ['stop', 'hold']:
            self.SetStopButton(True)
        elif self.iocode == 'done':
            self.iocode = 'init'
            self.tail = ''
            self.SetStopButton(False)

        self.passctr += 1
        self.StartDelay(start_time)

    def StartDelay(self, start_time):
#       Calculate delay unti next update.
        comp_time = 1000*(time.time() - start_time)
        delay = UPDATE_INTERVAL - comp_time
        if delay <= 1.:
            delay = 1.
        self.timer.Start(delay, oneShot=True)

    def ProcessData(self):
        """
        Read data from pipe and process it.
        """
        newdata = self.pipe.Read(self.read_length)
        if len(newdata) > 0:
            self.data_timer = time.time()
            if self.chart.run_start_time < 0:
#               First data packet.
                self.chart.run_start_time = time.time() - \
                                    (PACKET_TIME*len(newdata)/PACKET_LGTH)
                self.chart.Clear()

#           Add leftovers from the last read.
            data = self.tail + newdata
            if self.debug:
                sys.stdout.write('\rdata length: %d' % len(data))

#           Format the input data.
            npacket = int(len(data)/PACKET_LGTH)
            packets = fromstring(data[:PACKET_LGTH*npacket], short).\
                                            reshape([npacket, PACKET_WDS])
            packets = packets[:,(2,3)]

#           Left overs for next pass.
            self.tail = data[npacket*PACKET_LGTH:]

            self.chart.Update(packets)
        return len(newdata)

    def GetRemoteStatus(self, force=False):
        f = OpenRemote(self.physio_status_file, 'r', self.linux_host, \
                                        self.linux_user, self.linux_password)
        summary_string = f.read()
        f.close()
        if (summary_string != self.last_summary_string) or force:
            fname = summary_string.split('*')[-1]
            if fname != 'None':
                print 'File written to %s' % fname
                if self.iocode == 'hold':
                    self.iocode = 'done'
            self.last_summary_string = summary_string
            self.chart.last_serno, self.chart.last_outfile = \
                                            summary_string.split('*')
#           Redraw axes.
            self.chart.DrawFrame()

    def OnExit(self, evt):
        self.Exit()

    def Exit(self):
        if self.pipe is not None:
            try:
                self.SendIoCode('exit', ignore_errors=True)
                time.sleep(.01)
            except: pass
        self.KillGetPhysio()
        self.Destroy()
        sys.exit()


class PhysioGui(wx.App):
    """
    Dummy object required by wx to create the application widget.
    """
    def OnInit(self):
#       Call the widget that does the work.
        self.frame = PhysioTop()
        self.Init = self.frame.Init
        self.Show = self.frame.Show
#        self.chart = self.frame.UpdateChart()
        return True

def parse_options():
    usage = '\tUsage: physio <output_file>\n' + \
            '\tget_physio --help for more usage info.\n'
    optparser = OptionParser(usage)
    optparser.add_option( "-v", "--verbose", action="store_true", \
            dest="verbose",default=False, \
            help='Print stuff to screen.')
    optparser.add_option( "", "--debug", action="store_true", \
            dest="debug",default=False, \
            help='Print debugging info to screen.')
#    optparser.add_option( "", "--dabout", action="store_true", \
#                          dest="dabout",default=False, \
#                          help='Using dabout for trigger. Assume low-to-high transition')
    optparser.add_option( "", "--test-pattern", action="store_true", \
            dest="test_pattern",default=False, \
            help='Simulate data for testing purposes.')
    optparser.add_option( "", "--soft-trigger", action="store_true", \
            dest="soft_trigger",default=False, \
            help='Trigger  from software rather than from TTL pulse.')
    optparser.add_option( "", "--exam", action="store", type="str", \
            dest="exam_number",default=None, \
            help='Exam number.')
    optparser.add_option( "", "--series", action="store", type="str", \
            dest="series_number",default=None, \
            help='Series number.')
    optparser.add_option( "", "--subject-id", action="store", type="str", \
            dest="subject_id",default=None, \
            help='Subject ID.')
    opts, args = optparser.parse_args()

    return args, opts


def physio():


    args, opts = parse_options()
    if len(args) == 1:
        outfile = args[0]
    else:
        outfile = None

    gui = PhysioGui(redirect=False)

#   Now initialize the window.
    try:
        gui.Init(outfile=outfile, title='Scanner Cardiac and Respiration data', test_pattern=opts.test_pattern, verbose=opts.verbose, soft_trigger=opts.soft_trigger,exam=opts.exam_number, series=opts.series_number, id=opts.subject_id, debug=opts.debug)

        gui.Show()
        gui.MainLoop()
    except:
        sys.stderr.write('\n%s\n' % except_msg())
        gui.Exit()

if __name__ == "__main__":
    physio()

