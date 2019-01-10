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
import time
from datetime import datetime
import parallel
import serial
from signal import SIGUSR1, SIGABRT, signal
from subprocess import Popen, PIPE
from optparse import OptionParser
import mmap
import fcntl

from numpy import zeros, short, ushort, byte, ubyte, fromstring, arange, sin, \
                  array
from scipy.io import savemat
from wimage_lib import except_msg
import constants as c

# From GE documentation on the serila port
# A packet of 12 bytes is sent every 4msec whose format consists of:
#unsigned short sequence_number;
#signed short ECG2_data;
#signed short ECG3_data;
#signed short Resp_data;
#signed short PPG_data;
#unsigned short Checksum;
#NOTE: The Checksum is calculated using unsigned byte values of all the
#data.

BAUDRATE = 115200
DATAWIDTH = 8
PARITY = None
STOP_BITS = 1
FLOW_CONTROL = None
PACKET_LGTH = 12
PROC_PACKET_LGTH = 8
SYNC_DELAY = .0045 # interval between packets in seconds.

SERPORT = '/dev/ttyS0'
PARPORT = '/dev/parport1'
PORT_BUFLEN = 4095
PACKETS_PER_BUFFER = int(4095/12)
READ_LGTH = 12*PACKETS_PER_BUFFER # Number of bytes per serial port read.
#READ_LGTH = 12*PACKETS_PER_BUFFER # Number of bytes per serial port read.

DATA_LGTH = 4
DATA_LGTH_BYTES = 2*DATA_LGTH # data stored as shorts
PROC_BUFLEN = PACKETS_PER_BUFFER*DATA_LGTH # Number of processed shorts/read
PROC_BUFLEN_BYTES = 2*PROC_BUFLEN # Number of processed bytes/read

LEN_TIME_TAGS = 24
NUM_IOBUF_PER_OUTBUF = 1
OUT_BUFLEN = NUM_IOBUF_PER_OUTBUF*PROC_BUFLEN  # Length of each output buffer.
OUT_BUFLEN_BYTES = NUM_IOBUF_PER_OUTBUF*PROC_BUFLEN_BYTES + LEN_TIME_TAGS
OUT_BUFLEN_PTS = OUT_BUFLEN/DATA_LGTH

SAMPLE_INTERVAL = .004 # Sampling time in seconds.
BUFFER_FILLTIME = NUM_IOBUF_PER_OUTBUF*PACKETS_PER_BUFFER*SAMPLE_INTERVAL

TIMEOUT_SEC = 120.

MMAP_FILE = '/tmp/read_physio_mmap'
LOCAL_DIR='/local'
LOGFILE_RP = '%s/read_physio' % LOCAL_DIR
LOGFILE_PP = '%s/proc_physio' % LOCAL_DIR
LOGFILE_PP_WRITE = '%s/read_physio_io' % LOCAL_DIR
SCANNER_INFO_FILE = '%s/.scanner_info.txt' % LOCAL_DIR
STATUS_FILE = '%s/.get_physio_status.txt' % LOCAL_DIR
CARDIAC_RESP_BACKUP='/study/scanner/CardiacResp'

# If no sync signal received over parallel port for this time, acquisition
# will be terminated.
ENDOFSCAN_TIMEOUT = 3*PACKETS_PER_BUFFER*SAMPLE_INTERVAL + .10

NODATA_TIMEOUT = ENDOFSCAN_TIMEOUT + 2*BUFFER_FILLTIME

RESYNC_INTERVAL = .5*PACKETS_PER_BUFFER*SAMPLE_INTERVAL
CHECK_SYNC_TIMEOUT = .12 # Maximum time spent checking to see if scan still running.
PROC_READ_TIMEOUT = max(8*BUFFER_FILLTIME, 1.5*ENDOFSCAN_TIMEOUT)
IOCODES = ['init', 'gogo', 'stop', 'hold', 'wait', 'done', 'exit']
IOCODES_ACK = map(lambda x: '%sack' % x, IOCODES)
IOCODE_TRANSITIONS = { \
                    'init':'wait', \
                    'wait':'gogo', \
                    'gogo':'stop', \
                    'stop':'hold', \
                    'hold':'done', \
                    'done':'init', \
                    '':    'init'}


def move_old(pp, fnames=None):
#   Move files written to local output directory to the study drive.
    try:
        if fnames is None:
            fnames = map(lambda x: '%s/%s' % \
                                (LOCAL_DIR, x), os.listdir(LOCAL_DIR))
        newnames = []
        for fname in fnames:
            pp.LogMessage('fname: %s' % fname)
            if fname.endswith('.mat'):
#                fullname = '%s/%s' % (LOCAL_DIR, fname)
                cmd = 'mv %s %s' % (fname, CARDIAC_RESP_BACKUP)
                f = Popen(cmd, shell=True, stderr=PIPE, executable='/bin/bash')
                errors = f.communicate()
                errs = f.wait()
                if errs:
                    raise RuntimeError('\nCommand: %s\n%s\n%s' % \
                                                 (cmd, errors, except_msg()))
                pp.LogMessage('Moved %s to %s' % \
                                        (fname, CARDIAC_RESP_BACKUP))
                newnames.append('%s/%s' % \
                                (CARDIAC_RESP_BACKUP, os.path.basename(fname)))
    except:
        raise RuntimeError('Error while moving .mat file to %s\n%s' % \
                                        (CARDIAC_RESP_BACKUP, except_msg()))
    return newnames

def rewrite_raw(prefix, raw_outfile, queue):
    """
    Task that rewrites the raw output file.
    """
    try:
#       Create the process object.
        pp = ProcessPhysio(prefix=prefix)
        pp.LogMessage('%s:' % datetime.today())
#       Rewrite the raw data as .mat file.
        outfile = pp.RewriteRaw(raw_outfile)
        outfile = os.path.realpath(outfile)
        pp.LogMessage('Output  file: %s\n' % outfile)
        if outfile is not None and outfile.startswith(LOCAL_DIR):
            pp.LogMessage('Moving output  file: %s, localdir: %s\n' % (outfile, LOCAL_DIR))
            new_names = move_old(pp, fnames=[outfile])
            pp.UpdateStatus(pp.serno, new_names[0])
        else:
            pp.UpdateStatus(pp.serno, outfile)
            queue.put([outfile, pp.serno, pp.errlog])
            queue.close()
            queue.join_thread()
    except KeyboardInterrupt: 
#       Always save the data.
        pass
    except RuntimeError, errmsg:
            pp.LogMessage('%s: Error while moving .mat file to %s\n%s\n' % \
                        (datetime.today(), CARDIAC_RESP_BACKUP, except_msg()))
    except:
            pp.LogMessage('%s: Error while moving .mat file to %s\n%s\n' % \
                        (datetime.today(), CARDIAC_RESP_BACKUP, except_msg()))

class IOCode():
    def __init__(self, iocode):
        self.code = iocode

class ReadPhysio():

    def __init__(self, fd, opts, ioc):
        self.soft_trigger = opts.soft_trigger
        self.verbose = opts.verbose
        self.debug = opts.debug
        self.pipe = opts.pipe
        self.ioc = ioc
        self.iocode = 'init'
        self.last_iocode = ''
        self.last_info = ''
        os.umask(0)
        logfile = '%s_%s.log' % \
                        (LOGFILE_RP, datetime.today().strftime('%Y%b'))
        if os.path.exists(logfile):
            self.fer = open(logfile, 'a+')
        else:
            self.fer = open(logfile, 'w')
        self.LogMessage('\nInitialize ReadPhysio at %s:\n' % (datetime.today()))
        os.umask(002)
        x = []
        for code in IOCODES:
            x.append((code, 0))
        self.sent_iocodes = dict(x)

#       Setup the serial port.
        self.sport = serial.Serial(port=SERPORT, baudrate=BAUDRATE, timeout=1)
        self.sport.flushInput()

#       Setup the parallel port.
        self.pport = parallel.Parallel(PARPORT)
        self.pport.PPSETMODE('compatible')

        self.checked_data = zeros(PROC_BUFLEN, short)

        self.fd = fd
        self.fd.flush()
        self.nullpacket = zeros(DATA_LGTH, short)

#       Set up double buffer.
        self.buffer = zeros([2,OUT_BUFLEN], short)
        self.time_tags = zeros(3, float)
        self.tmp_time = zeros(1, float)
        self.zero_times = self.time_tags.tostring()

#       Make stdin a non-blocking device
        fn = sys.stdin.fileno()
        fl = fcntl.fcntl(fn, fcntl.F_GETFL)
        fcntl.fcntl(fn, fcntl.F_SETFL, fl | os.O_NONBLOCK)

#       Make stderr a non-blocking device
        if not sys.stderr.isatty():
            fn = sys.stderr.fileno()
            fl = fcntl.fcntl(fn, fcntl.F_GETFL)
            fcntl.fcntl(fn, fcntl.F_SETFL, fl | os.O_NONBLOCK)

#       Initialize stuff that gets re-initialized for each run.
        self.ReInit()

    def ReInit(self):
        self.trigger_time = time.time()
        self.WriteIoCode('init')
        self.SendIoCode('init')
        self.bufnum = 0
        self.nwrote = 0

    def ReadIoCode(self):
#       Read iocode from shared memory
        self.ioc.seek(0)
        iocode = self.ioc.read(4)
        if self.debug and iocode != self.iocode:
            self.LogMessage('ReadPhysio::ReadIoCode: %s' % self.iocode)
        self.iocode = iocode

    def WriteIoCode(self, iocode, tag=''):
        """
        Write iocode to memory file (i.e, shared memory) and to stderr.
        """
        if iocode in IOCODES:
            self.ioc.seek(0)
            self.ioc.write(iocode)
            if self.debug and iocode != self.iocode:
                self.LogMessage('ReadPhysio::WriteIoCode: %s __%s__' % \
                                                        (tag, iocode))
            self.iocode = iocode

    def IoCodeComm(self):
#        if sys.stdin.isatty():
#            return
        value = self.ReadStdin()
        if len(value) > 0: 
            print 100, 'ReadPhysio: __%s__' % value
            iocode = self.ParseStdin(value)
            if iocode is not None and self.debug:
                self.LogMessage('IoCodeComm::iocode: %s' % iocode)
            if iocode is not None:
                self.WriteIoCode(iocode)
#                self.SendIoCode('%sack' % iocode)
                if self.debug and sys.stdout.isatty():
                    self.LogMessage('IoCodeComm::value: %s' % value)

    def SendIoCode(self, iocode):
        sys.stderr.write(iocode)
        sys.stderr.flush()
        if not iocode.endswith('ack'):
            self.sent_iocodes[iocode] += 1
        if self.debug:
            self.LogMessage('SendIoCode: Sent %s' % iocode)
        self.LogMessage('SendIoCode: Sent %s' % iocode)

    def ReadStdin(self, block=False):
        value = ''
        while True:
            try: 
                value = sys.stdin.read().strip()
                break
            except IOError: 
                if block == True:
                    continue
                else:
                    value = ""
                    break
        return value

    def ParseStdin(self, value):
#       Look for acks sent from physio.
        acks, value = self.FindCodeInString(list(IOCODES_ACK), value)
        for ack in acks.keys():
            if self.sent_iocodes.has_key(ack[:4]):
                self.sent_iocodes[ack[:4]] = 0
            else:
                self.LogMessage( \
                'iocode %s acknowledged but no record of it being sent.' % ack)

#       Look for iocodes sent from physio (i.e., 'wait' or 'stop')
        codes, value = self.FindCodeInString(list(IOCODES), value)
        keys = codes.keys()
        if len(keys) > 1:
            nmax = -1
            for key in keys:
                if codes[key] > nmax:
                    nmax = codes[key]
                    keymax = key
            code = codes[keymax]
        elif len(keys) == 1:
            code = keys[0]
        else:
            code = None
#        self.LogMessage('ParseStdin::output code: %s' % code )
        return code
        

    def FindCodeInString(self, code_list, value):
        fnd = {}
        test = map(lambda x: x in value, code_list)
        n = 0
        while True in test:
            code = code_list[test.index(True)]
            fnd[code] = n
#           Remove code from input string.
            value = ''.join(value.split(code))
            test.remove(True)
            n += 1
        return fnd, value

    def ReadFullPackets(self):
        """
        Empty buffer by reading full packets and discarding.
        """
        n = self.sport.inWaiting()
        full_packets = int(n/PACKET_LGTH)
        if full_packets > 0:
            self.sport.read(full_packets*PACKET_LGTH)

    
    def Sync(self, resync=False):
        """
        Sync input buffer to data stream to ensure that first byte in 
        the buffer is the first byte in a packet.
        """
        n = 0
        if resync:
            self.ReadFullPackets()
        else:
            self.sport.flushInput()
        while True:
            cdata = self.sport.read(PACKET_LGTH)
            if len(cdata) != PACKET_LGTH:
                self.Wait(SYNC_DELAY)
                continue
            bytes = fromstring(cdata[:10], ubyte)
            csum = bytes.sum()
            data = fromstring(cdata[:12], short)
            if csum == data[5]:
                self.last_seqnum = fromstring(cdata[:2], ushort)
                break
            else:
                self.sport.flushInput()
                self.Wait(SYNC_DELAY)
            n += 1

    def ResyncTTL(self, timeout=CHECK_SYNC_TIMEOUT):
        """
        Check for TTL pulse with a short timeout interval that ensures no
        loss of data.
        """
        time0 = time.time()
        time1 = time0
        if self.soft_trigger:
            self.trigger_time = time.time()
        last_ttl = self.pport.getInPaperOut()
        while time1-time0 < timeout:
            ttl = self.pport.getInPaperOut()
            time1 = time.time()
            if ttl != last_ttl:
                self.trigger_time = time1
                if self.debug:
                    self.LogMessage('Re-synced at %6.1f sec' % \
                                                (time1-self.time_tags[0]))
                break
            self.Wait(.001)

    def GetNullTTL(self, mincount=10):
        ttls = []
        time0 = time.time()
#        self.fer.write("GetNullTTL\n")
        ttl = None
        while len(ttls) < mincount and ttl != None:
            ttl = self.pport.getInPaperOut()
            ttls.append()
        if sys.stdout.isatty():
            print ttls
        return ttl

    def WaitForTTL(self, timeout=60.):
        time0 = time.time()
        time00 = time0
        time1 = time0
        last_ttl = self.pport.getInPaperOut()
#       last_ttl = self.GetNullTTL()
#        print 111,last_ttl
        while time1-time0 < timeout:
            ttl = self.pport.getInPaperOut()
#            print 222,ttl
            if self.soft_trigger and (time1 - time0) > 1.:
                ttl = not ttl
                self.LogMessage('Soft triggered at %s, ttl: %s, last_ttl: %s' %\
                            (self.GetTime(self.trigger_time), ttl, last_ttl))
            if ttl is not None and ttl != last_ttl and (time1 - time0) > .1:
                self.Sync(resync=True)
                self.trigger_time = time.time()
#               Initialize output buffers and signal parent to go.
                self.buffer[:,:] = 0
                self.time_tags[0] = self.trigger_time
                self.LogMessage('Got TTL at %s, ttl: %s, last_ttl: %s' % \
                            (self.GetTime(self.trigger_time), ttl, last_ttl))
                self.GetInfo()
                return True
            if (time1 - time00) > RESYNC_INTERVAL:
                self.Sync(resync=True)
                time1 = time.time()
                time00 = time1
            else:
                time1 = time.time() # Don't count resync in timeout counter.
        return False

    def Read(self):
        read_lgth = READ_LGTH
        cdata = self.sport.read(READ_LGTH)
        if len(cdata) != read_lgth:
            self.LogMessage( \
            'Tried to read %d bytes from serial port, got %d bytes.' % \
                                                    (read_lgth, len(cdata)))
        j = 0
        seqnum0 = self.last_seqnum
        for ptr in xrange(0,read_lgth, PACKET_LGTH):
            bytes = fromstring(cdata[ptr:ptr+PACKET_LGTH-2], ubyte)
            local_chksum = bytes.sum()
            chksum = fromstring(cdata[ptr+PACKET_LGTH-2:ptr+PACKET_LGTH], ushort)  
            if local_chksum == chksum:
                seqnum = fromstring(cdata[ptr:ptr+2], ushort)  
                if seqnum > self.last_seqnum + 1:
                    if self.verbose:
                        self.LogMessage('*** Padding %d times (%d %d) ***' % \
                           (seqnum-self.last_seqnum-1, self.last_seqnum, seqnum))
                    for i in xrange(seqnum-self.last_seqnum-1):
                        self.checked_data[j:j+DATA_LGTH] = self.nullpacket
                        j += DATA_LGTH
                data = fromstring(cdata[ptr+2:ptr+PACKET_LGTH-2], short)
                self.checked_data[j:j+DATA_LGTH] = data
                j += DATA_LGTH
                self.last_seqnum = seqnum
            else:
                self.LogMessage( \
                'Lost synchronization with physio data, reacquiring ...')
                self.Sync()
        return self.checked_data[:j], j

    def DoubleBuffer(self):
        """
        Double buffer the output of the read method.
        """
        time_now = time.time()
        self.time_tags[1] = time_now
        if (time_now - self.trigger_time) > ENDOFSCAN_TIMEOUT:
#           Acquisition timed out, terminate acquistion.
            self.LogMessage('Trigger acq timed out @ %6.1f sec. ' % \
                (time_now - self.trigger_time) + \
                'Assuming end of scan ...' % (time_now - self.time_tags[0]))
            hold = True
        elif self.iocode == 'stop':
            hold = True
        else:
            hold = False
        for ip in xrange(0, OUT_BUFLEN, PROC_BUFLEN):
#           Check to see if scan is still running.  Timeout in 60 ms.
            self.ResyncTTL()
    
#           Read another serial port buffer.
            data, lgth = self.Read()
            self.buffer[self.bufnum, ip:ip+lgth] = data
            if hold:
#               Initialize unwritten part of buffer and write it out now.
                self.buffer[self.bufnum,ip+lgth:] = 0
                break
        self.time_tags[2] = time.time()
        self.fd.write(self.buffer[self.bufnum,:].tostring() + \
                                            self.time_tags.tostring())
        self.fd.flush()
        if hold:
            self.LogMessage('Buffer flushed at %s' % self.GetTime())
            self.WriteIoCode('hold')
        self.bufnum ^= 1
        self.nwrote += OUT_BUFLEN

    def GetInfo(self):
#       Make sure scanner info has been updated since sync signal received.
        f = open('%s' % SCANNER_INFO_FILE, 'r')
        info = f.read().strip()
        f.close()
        exam, patid, psdname, serno, outdir = info.split('*')
        if info != self.last_info:
            self.LogMessage('\n\tStudy Info:\n' + \
                              '\tExam: %s\n' % exam + \
                              '\tSubject ID: %s\n' % patid + \
                              '\tPulseSequence: %s\n' % psdname + \
                              '\tSeriesNumber: %s\n' % serno + \
                              '\tOutput Directory: %s' % outdir)
        return exam, patid, psdname, serno, outdir
            
    def CleanUp(self):
#       Close the pipe and exit
        self._del_()

    def _del_(self):
        self.LogMessage( \
        'Child process wrote %d words. Closing pipe and exiting.' % self.nwrote)
        if  not self.fer.closed and not self.fer.isatty():
            self.fer.close()
            try: os.chmod(self.fer.name, 0777)
            except: pass
        if not self.fd.closed:
            self.fd.close()
        self.sport.close()
#        self.pport.close()
        sys.exit(0)

    def GetTime(self, posix_time=None):
        if posix_time is None:
            posix_time = time.time()
        dtime = datetime.fromtimestamp(posix_time)
        date_fmt = dtime.strftime('%Y%b%d@%H:%M:%S') + \
                    ':%03d' % int(1000*(posix_time-int(posix_time)))
        return date_fmt

    def LogMessage(self, msg, flush=False):
        if self.fer is not None and not self.fer.closed:
            self.fer.write(msg + '\n')
            if flush or self.verbose:
                self.fer.flush()
        if self.verbose and sys.stdout.isatty():
            sys.stdout.write(msg + '\n')
            sys.stdout.flush()

    def Wait(self, delay):
        """
        Wait for delay seconds (really wait that long).
        """
        time0 = time.time()
        dt = 0
        while dt < delay:
            time.sleep(delay - dt)
            dt = time.time() - time0
        
    def MainLoop(self):
        time0 = time.time()
        last_iocode = ''
        self.Sync()
        while True:
            if self.iocode != last_iocode:
                self.LogMessage('MainLoop::iocode: %s, time: %s' % \
                                (self.iocode, self.GetTime()))
                if self.iocode != IOCODE_TRANSITIONS[last_iocode]:
#                   Skipped a code. send the missing one(s).
                    iocode =  IOCODE_TRANSITIONS[last_iocode]
                    self.LogMessage('MainLoop::iocode forced to: %s' % iocode)
                    self.SendIoCode(iocode)
                last_iocode = self.iocode
                self.SendIoCode(self.iocode)
            if self.iocode == 'init':
                self.Sync(resync=True)
            elif self.iocode == 'wait':
                self.trigger_time = time.time()
                for i in xrange(5):
                    go = self.WaitForTTL()
                    if go: break
                    else: self.LogMessage('TTL timeout at %s' % self.GetTime())
                self.WriteIoCode('gogo')
                self.SendIoCode('gogo')
            elif self.iocode == 'gogo' or self.iocode == 'stop':
                self.DoubleBuffer()
            elif self.iocode == 'hold':
#               Wait for read process.
                self.ReadIoCode()
            elif self.iocode == 'done':
#               Make sure it has been written to stderr.
                self.SendIoCode('done')
                self.Wait(.1)
                self.fer.flush()
                self.ReInit()
#               Tell GUI that we're ready for another run.
            elif self.iocode == 'exit':
                self.CleanUp()
                break
            self.IoCodeComm()
            self.Wait(.005)
 
class ProcessPhysio():

    def __init__(self, fd=None, child_pid=None, prefix=None, \
                                            opts=None, ioc=None): 
#       Get the file descriptor for the pipe to the child process and make
#       it non-blocking.
        if fd is not None:
            self.fd = fd
            self.fd.flush()
            fn = self.fd.fileno()
            fl = fcntl.fcntl(fn, fcntl.F_GETFL)
            fcntl.fcntl(fn, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.child_pid = child_pid
        self.ioc = ioc
        self.f = None
        self.raw_outfile = None
        self.nread = 0
        self.rewrote = False
        self.subproc = None
        self.prefix = prefix
        self.serno = -1
        self.errlog = ''

        if opts is None:
            self.verbose = False
            self.debug = False
            self.soft_trigger = False
            self.pipe = None
            self.test_pattern = False
        else:
            self.verbose = opts.verbose
            self.debug = opts.debug
            self.soft_trigger = opts.soft_trigger
            self.pipe = opts.pipe
            self.test_pattern = opts.test_pattern

        os.umask(002)

        self.nbuf = 0
        self.last_info = ''

        if fd is None:
#           This is the rewrite process.
            logfile = '%s_%s.log' % \
                        (LOGFILE_PP_WRITE, datetime.today().strftime('%Y%b'))
            if os.path.exists(logfile):
                self.fep = open(logfile, 'a+')
            else:
                self.fep = open(logfile, 'w')
            return

#       Open log file.
        os.umask(0)
        logfile = '%s_%s.log' % \
                        (LOGFILE_PP, datetime.today().strftime('%Y%b'))
        if os.path.exists(logfile):
            self.fep = open(logfile, 'a+')
        else:
            self.fep = open(logfile, 'w')
        self.fep.write('\n%s:\n' % (datetime.today()))

        self.iocode = 'init'

        self.UpdateStatus(-1, 'None')
        tmp = zeros(3, float)
        self.zero_times = tmp.tostring()

    def OpenRawFile(self):
#       Open raw output file.
        if self.f is None:
            prefix = '/local/physio_tmp_%s' % \
                                    datetime.today().strftime('%Y%b%d_%H_%M')
            self.raw_outfile = self.GetSuffix(prefix)
            self.raw_outfile += '.raw'
            self.f = open(self.raw_outfile, 'w')
            self.f.write('ECG2\tECG3\tRespiration\tPPG\n')

    def UpdateStatus(self, serno, fname):
        self.fstat = open(STATUS_FILE, 'w')
        self.fstat.seek(0)
        self.fstat.write('%s*%s' % (serno, fname))
        self.fstat.close()
        if self.verbose:
            self.LogMessage('ProcPhysio::output file: %s*%s' % (serno, fname))

    def LogMessage(self, msg, flush=False):
        if self.fep is None:
            self.errlog += '%s\n' % msg
        else:
            self.fep.write(msg + '\n')
            if flush or self.verbose:
                self.fep.flush()
        if self.verbose and sys.stdout.isatty():
            try: 
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
            except IOError: pass

    def ReadIoCode(self):
        self.ioc.seek(0)
        iocode = self.ioc.read(4)
        if self.debug and iocode != self.iocode:
            self.LogMessage('ProcPhysio::ReadIoCode: __%s__' % self.iocode)
        elif len(iocode) != 4 and self.debug:
            self.LogMessage('ProcPhysio::ReadIoCode: invalid iocode: __%s__' % \
                                                                        iocode)
        if iocode in IOCODES:
            self.iocode = iocode
        return 

    def FlushPipe(self):
        try: cdata = self.fd.read()
        except: cdata = ''
        return len(cdata)

    def Wait(self, delay):
        """
        Wait for delay seconds (really wait that long).
        """
        time0 = time.time()
        dt = 0
        while dt < delay:
            time.sleep(delay - dt)
            dt = time.time() - time0

    def FlushBuffer(self):
        """
        Ensure all data has been read from ReadPhysio.
        """
        nread = 1
        while self.f is not None and nread > 0:
            self.Wait(.1) # Wait for I/O to complete
            nread = self.ReadBuffer()
            self.nread += nread
#            self.Wait(.1) # Wait for I/O to complete
            self.LogMessage('Buffer flushed at %s, nread: %d' % \
                                        (self.GetTime(), nread))

    def ReadBuffer(self):

#       Read data from pipe.
        try: cdata = self.fd.read(OUT_BUFLEN_BYTES)
        except: cdata = ''

        nread = len(cdata)
        if nread == 0:
            return 0
        self.nread += nread
        if nread < OUT_BUFLEN_BYTES:
            self.fep.write('*** buffer size: %d, nread: %d *** \n' % \
                                        (OUT_BUFLEN_BYTES, nread))
        self.nbuf += 1
        self.rewrote = False
        self.nread += nread

        if self.test_pattern:
            # Generate sinusoidal respiration and pulse-ox signals.
            data_out = self.TestPattern(nread)
        else:
            data_out = cdata[:nread]

#       Write buffer to disk.
        self.f.write(data_out)

        if self.pipe is None:
            if  sys.stdout.isatty():
                sys.stdout.write('.')
                sys.stdout.flush()
        else:
            try:
#               Write data to pipe to GUI.
                sys.stdout.write(data_out[:-LEN_TIME_TAGS])
                sys.stdout.flush()

            except IOError,errmsg:
#               Log errors and continue
                msg = 'Non-fatal error, continuing data collection.\n%s\n%s' % \
                                                     (errmsg, except_msg())
                self.LogMessage(msg)
            except (OSError, IOError), errmsg:
                msg = '\nNon-fatal error, continuing data collection.\n%s' % \
                                                    except_msg()
                self.LogMessage(msg)
        return nread

    def TestPattern(self, nread):
        npack = float(nread/PROC_PACKET_LGTH)
        time_now = time.time() - self.test_time0
#        self.LogMessage('Time: %f: ' % time_now)
        times = SAMPLE_INTERVAL*arange(npack) + time_now
        if self.verbose:
            self.LogMessage('time0: %6.3f, time1: %6.3f' % \
                                                (times[0], times[-1]))
        phs = 2.*c.pi*times
        y = zeros([npack,4],short)
        y[:,2] = (1000.*sin(.125*phs)).astype(short)
        y[:,3] = (1000.*sin(phs)).astype(short)
        y[:,0] = 0 #(1000.*sin(.25*phs)).astype(short)
        y[:,1] = 0 #(1000.*sin(.5*phs)).astype(short)
        return y.reshape([npack*4]).tostring()

    def WriteIoCode(self, iocode=None):
        if iocode == None:
            iocode = self.iocode
        if iocode in IOCODES:
            self.ioc.seek(0)
            self.ioc.write(iocode)
            if self.debug and iocode != self.iocode:
                self.LogMessage('ProcPhysio::WriteIoCode: __%s__' % iocode)
            self.iocode = iocode

    def GetInfo(self):
#       Make sure scanner info has been updated since sync signal received.
        f = open('%s' % SCANNER_INFO_FILE, 'r')
        info = f.read().strip()
        f.close()
        exam, patid, psdname, serno, outdir = info.split('*')
        return exam, patid, psdname, serno, outdir

    def CreatePrefix(self, start_posix):
#        self.LogMessage('CreatePrefix, self.prefix: %s' % self.prefix)
        if self.prefix != 'auto' and self.prefix != None:
            return self.prefix
        exam, patid, psdname, self.serno, outdir = self.GetInfo()

        if not outdir.startswith('/') or 'None' in outdir:
            outdir = '/local'
        else:
            outdir += '/cardiac'
#        self.LogMessage('outdir: %s\n' % outdir)

#        self.LogMessage('CreatePrefix, outdir: %s' % outdir)
        if not os.path.exists(outdir):
            try:
                os.makedirs(outdir)
            except:
                self.LogMessage('Could not create directory: %s' % outdir)

        if patid == 'None':
            base = 'physio_%s' % datetime.fromtimestamp(start_posix).\
                                               strftime('%Y%b%d_%H:%M')
        else:
            base = 'physio_%s_s%s' % (patid, self.serno)
#        self.LogMessage('CreatePrefix, base: %s' % base)
        prefix = '%s/%s' % (outdir, base)
#        self.LogMessage('prefix: %s' % prefix)
#        self.LogMessage('CreatePrefix, prefix: %s' % prefix)
        prefix = self.GetSuffix(prefix)
#        self.LogMessage('CreatePrefix, prefix: %s' % prefix, flush=True)

        return prefix


    def GetSuffix(self, prefix):
        """
        Append alphabetic to filename to create unique name.
        """
        tmp = prefix
        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        i = 0
        while os.path.exists('%s.mat' % prefix) or os.path.exists('%s/%s.mat' %\
                            (CARDIAC_RESP_BACKUP, os.path.basename(prefix))):
            prefix = '%s%s' % (tmp, alphabet[i])
            i += 1
        return prefix

    def SplitDataTime(self, nbufs, alldata):
        """
        Split time info (3 floats at the end of each buffer) from the data
        and return in separate arrays.
        """
#        self.fep.write('nbufs: %d, len(alldata): %d\n' % (nbufs, len(alldata)))
        data = zeros([nbufs*OUT_BUFLEN_PTS, DATA_LGTH], short)
        times = zeros([nbufs*OUT_BUFLEN_PTS], float)
        for ib in xrange(nbufs):
            i0 = ib*OUT_BUFLEN_PTS
            i1 = i0 + OUT_BUFLEN_PTS
            j0 = ib*OUT_BUFLEN_BYTES
            j1 = j0 + OUT_BUFLEN_BYTES - LEN_TIME_TAGS
            if j1 > len(alldata):
                k = (len(alldata) - j0)/DATA_LGTH_BYTES
                i1 = i0 + DATA_LGTH*k
                j1 = j0 + DATA_LGTH_BYTES*k
                ctimes = zeros(3, float).tostring()
            else:
                ctimes = alldata[j1:j1+LEN_TIME_TAGS]
            data[i0:i1] = fromstring(alldata[j0: j1], short). \
                            reshape([OUT_BUFLEN_PTS, DATA_LGTH])
            times[i0:i1], start_posix, start_fmt = self.GetTimeTags(ctimes)
        return data, times, start_posix, start_fmt
 
    def RewriteRaw(self, raw_outfile):
        """
        Read raw output file, format the data, and rewrite it to the 
        study drive.
        """
        if not os.path.exists(raw_outfile):
#           Must be calling this for second time on an exception
            self.raw_outfile = None
            return None
        outdir = os.path.dirname(raw_outfile)
        if not os.path.exists(outdir):
            try:
                os.makedirs(outdir)
            except:
                raise RuntimeError( 'Could not create %s' % outdir)

#       Read raw data file.
        f = open(raw_outfile, 'r')
        names = f.readline().strip()
        alldata = f.read()
        f.close()

        nbufs = len(alldata)/OUT_BUFLEN_BYTES
        if nbufs < 1:
            raise RuntimeError('No buffer collected, no data to rewrite')
        data, times, start_posix, start_fmt = \
                                            self.SplitDataTime(nbufs, alldata)

#       Create unique name from info stored by dashboard running on scanner.
        outfile = self.CreatePrefix(start_posix)
#        self.LogMessage('final outfile: %s\n' % outfile)

        try:
            f = open(outfile + '.mat', 'w')
        except:
#           Could not open first try, write to /local.
            outfile = '/local/%s' % os.path.basename(outfile)
            f = open(outfile + '.mat', 'w')
        else:
            f.close()

#       Rewrite to matlab format
        mat = {'names': names, \
               'data':data, \
               'times':times, \
               'start_time_posix':start_posix, \
               'start_time':start_fmt}
        savemat(outfile, mat, oned_as='column', do_compression=True)

        self.LogMessage('Data written to %s' % outfile)
        self.LogMessage('raw data file: %s' % raw_outfile)


        p = Popen('/bin/rm %s'%raw_outfile, shell=True, executable='/bin/bash')
        errs = p.wait()

        return os.path.realpath(outfile + '.mat')
 
    def RewriteData(self):
        """
        Rewrite data to matlab file.
        """
#        self.LogMessage('Rewriting data, self.rewrote: %s.' % self.rewrote)

        if self.rewrote or self.f is None:
            self.rewrote = True
            return
        self.rewrote = True

        if not self.f.closed:
            self.f.close()
            self.f = None

        try: 
            from multiprocessing import Process, Queue
#           Create a second process to rewrite to /study.
            self.queue = Queue()
            self.subproc = Process(target=rewrite_raw, \
                            args=(self.prefix, self.raw_outfile, self.queue))
            self.subproc.start()
        except ImportError:
#           This version of python must not have the multiprocessing module.
            self.LogMessage( \
            'Error importing multiprocessing. Rewriting data in main thread.')
            print 900
            self.matfile = self.RewriteRaw(self.raw_outfile)
            if self.matfile is None:
                return
            self.subproc = None
            self.FinishRewrite(main_thread=True)
        except:
            self.LogMessage(except_msg())

    def CheckRewrite(self):
        if self.subproc is not None and not self.subproc.is_alive():
            self.subproc.join()
            self.FinishRewrite()

    def ReadQueue(self, wait=False, timeout=10):
        """
        Read messages from rewrite process from queue.
        """
        try: 
            info = self.queue.get(wait)
            if info is None:
                self.LogMessage('rewrite_raw: no file written.')
            else:
                outfile, self.serno,  log_msg = info
                self.LogMessage(log_msg)
        except Empty:
            if wait:
                self.LogMessage( \
                        'Timeout while waiting for rewrite_raw to terminate')
            else:
                self.LogMessage( \
                        'rewrite_raw did not terminate normally.')

    def FinishRewrite(self, mainthread=False):
        if self.subproc is not None and self.subproc.is_alive():
            if self.subproc.exitcode is None:
#               Rewrite process terminated, check the queue.
                self.ReadQueue(wait=False)
                self.subproc.terminate()
            else:
#               Read queue with a 10 second timeout.
                self.subproc.join()
                self.ReadQueue(wait=False, timeout=10)
            self.subproc.terminate()
            self.subproc = None

#           Update status file.
            if outfile is not None:
                self.UpdateStatus(self.serno, outfile)
                self.rewrote = True
        elif mainthread:
#           Update status file.
            self.UpdateStatus(self.serno, outfile)
            self.rewrote = True

    def GetTime(self, posix_time=None):
        if posix_time is None:
            posix_time = time.time()
        if not isinstance(posix_time, float):
            raise RuntimeError('Invalid format for posix_time')
        dtime = datetime.fromtimestamp(posix_time)
        date_fmt = dtime.strftime('%Y%b%d@%H:%M:%S') + \
                    ':%03d' % int(1000*(posix_time-int(posix_time)))
        return date_fmt

    def GetTimeTags(self, sdata):
        times = fromstring(sdata, float)
        t0 = times[1] - times[0]
        t1 = times[2] - times[0]
        dt = (times[2] - times[1])/PACKETS_PER_BUFFER
        date_fmt = self.GetTime(times[0])
        if self.verbose:
            self.fep.write(\
            'Packet start: %8.4f, Packet end: %8.4f, Sampling interval: %8.6f\n' % \
                                                                (t0, t1, dt))
        return (dt*arange(OUT_BUFLEN_PTS).astype(float) + t0), \
                                                    times[0], date_fmt

    def MainLoop(self):
        """
        Main processing loop.
        """
        time0 = time.time()
        self.test_time0 = time0
        last_iocode = ''
        initializing = False
        while self.iocode != 'exit':
            self.ReadIoCode()
            if self.iocode != last_iocode:
#                if self.debug:
                self.LogMessage('MainLoop::iocode: %s, time: %s' % \
                                         (self.iocode, self.GetTime()))
                last_iocode = self.iocode
            if self.iocode == 'init':
#               Open raw file for next acquisition.
                self.rewrote = False
                self.rewrote = 0
                nleft = self.FlushPipe()
                if not initializing:
                    self.LogMessage('Intializing at %s' % \
                                                self.GetTime())
                    initializing = True
                if nleft > 0:
                    self.LogMessage( \
                    'Found %d bytes in pipe at initialization. at %s' %\
                                            (nleft, self.GetTime()))
                self.time00 = time.time()
            elif self.iocode == 'wait':
                self.nread = 0
                initializing = False
                self.OpenRawFile()
                self.GetInfo()
                self.time00 = time.time()
            elif self.iocode in ('gogo', 'stop'):
                initializing = False
                if self.f is None:
#                   Output file has already been closed. This acq is complete.
                    nread = 0
                else:
                    nread = self.ReadBuffer()
                time_now = time.time()
                if nread > 0:
#                   Reset the timeout timer.
                    self.time00 = time_now
                elif (time_now - self.time00) > NODATA_TIMEOUT:
#                       No data, let the timout-timer run
                        self.WriteIoCode('stop')
                if self.iocode == 'hold':
#                   No data and read process flushed its buffer. We're done.
                    self.FlushBuffer()
                    self.RewriteData()
                    self.WriteIoCode('done')
            elif self.iocode == 'hold':
#               All the data have been read, rewrite if not already rewritten.
                self.FlushBuffer()
                self.RewriteData()
                self.WriteIoCode('done')
                self.time00 = time.time()
            elif self.iocode == 'done' and (time.time() - self.time00) > .5:
                self.WriteIoCode('init')
            elif self.iocode == 'done':
                pass
            elif self.iocode == 'exit':
                self.LogMessage( \
                'ProcessPhysio exiting after loop timeout.')
                self.LogMessage( \
                'Elapsed time since last valid data: %5.3f sec' % \
                                                (time.time()-time0))
                self.CleanUp()
            else:
                self.LogMessage('*** Error: unprocessed state: %s'%self.iocode)

#           Check for completion of output file I/O every pass.
            if self.rewrote == True:
                self.CheckRewrite()
            self.Wait(.005)
        self.LogMessage('ProcessPhysio:: Exiting ...')

    def __del__(self):
        try:
            self.CleanUp()
        except:
            self.LogMessage(except_msg() + '\n')

    def CleanUp(self):
#       Finish writing all data.
        if self.subproc is not None:
#           Wait for rewrite process to complete.
            self.subproc.join()
            self.FinishRewrite()
        self.LogMessage('ProcessPhysio read a total of %d bytes' % \
                                                        self.nread)
        if self.f is not None and not self.f.closed:
            self.f.close()
        if self.child_pid is not None:
            os.kill(self.child_pid, SIGABRT)
        if self.fep is not None and not self.fep.isatty() :
            if not self.fep.closed:
                self.fep.close()
            try: os.chmod(self.fep.name, 0777)
            except: pass
        os._exit(0)


def parse_options():
    usage = '\tUsage: get_physio <output_file>\n' + \
            '\tset <output_file> to "auto" to form name from subject ID and series number\n' + \
            '\tget_physio --help for more usage info.\n'
    optparser = OptionParser(usage)
    optparser.add_option( "-v", "--verbose", action="store_true", \
            dest="verbose",default=False, \
            help='Print stuff to screen.')
    optparser.add_option( "", "--debug", action="store_true", \
                          dest="debug",default=False, help='Debug mode.')
#    optparser.add_option( "", "--dabout", action="store_true", \
#                          dest="dabout",default=False, \
#                          help='Using dabout for trigger. Assume low-to-high transition')
    optparser.add_option( "", "--test-pattern", action="store_true", \
            dest="test_pattern",default=False, \
            help='Simulate data for testing purposes.')
    optparser.add_option( "", "--pipe", action="store_true", \
            dest="pipe",default=None, \
            help='stdout is connected to a pipe. Write all output to stdout.')
    optparser.add_option( "", "--soft-trigger", action="store_true", \
            dest="soft_trigger",default=False, \
            help='Do not wait for trigger signal from scanner.')
#    optparser.add_option( "", "--prefix", action="store", \
#            dest="prefix",default=None, type=str, \
#            help='Name of destination file. Will be constructed automatically.+\
#                  from exam number etc if no prefix is supplied')
    opts, args = optparser.parse_args()

    if len(args) != 1:
        sys.stderr.write(usage)
        sys.exit()

    prefix = args[0]

    return prefix, opts
    

def read_physio():
#   Parse the command line
    prefix, opts = parse_options()

#   Setup the memory map for comm. between the two processes.
    mmapfile = '%s_%s' % (MMAP_FILE, os.getenv('USER'))
    if not os.path.exists(mmapfile):
        f = open(mmapfile, 'w')
        f.write('    ')
        f.close()
    fmmap = os.open(mmapfile, os.O_RDWR)
    os.write(fmmap,'    ')
    ioc = mmap.mmap(fmmap, 4)
    ioc.seek(0)
    ioc.write('init')
#   Create a pipe for communication between the two processes
    fr, fw = os.pipe()
#   Fork to create a high-priority, fast task to read the I/O ports and
#   another low-priority task to write to disk.
    child_pid = os.fork()

    if child_pid:
#       Parent process, close the write pipe.
        os.close(fw)
        try:
            fdr = os.fdopen(fr, 'r', OUT_BUFLEN_BYTES)
            os.nice(10) # The child gets priority
            pp = None
            pp = ProcessPhysio(fdr, child_pid, prefix, opts, ioc)
            pp.MainLoop() # Main processing loop.
            os.waitpid(child_pid, 0) # Make sure child process exited.
            fdr.close()
        except(IOError, OSError), errmsg:
            msg = '\n%s\n%s\n' % (errmsg, except_msg())
            os.kill(child_pid, SIGABRT) # Abort the child process
            sys.stderr.write(msg)
            sys.stderr.flush()
            if pp is not None:
                pp.fep.write(msg)
        except KeyboardInterrupt:
            pp.CleanUp()
#           Abort the child process
            os.kill(child_pid, SIGABRT) 
#           Make sure child process exits.
            os.waitpid(child_pid, os.WNOHANG) 
        except (SystemExit):
            os.kill(child_pid, SIGABRT) 
            os.waitpid(child_pid, os.WNOHANG) 
        except:
            if pp is None:
                sys.stderr.write('\n%s\n' % except_msg())
            else:
                pp.fep.write('\n%s\n' % except_msg())
                os.kill(child_pid, SIGABRT) 
                os.waitpid(child_pid, os.WNOHANG) 
    else:
#       Child process. (The one that grabs the data)
        os.close(fr)
        try:
            fdw = os.fdopen(fw, 'w', OUT_BUFLEN_BYTES)
            rp = ReadPhysio(fdw, opts, ioc)
        except:
            sys.stderr.write('\n%s\n' % except_msg())
            rp = None
            sys.exit()
        try:
            rp.MainLoop()
            rp.LogMessage('ReadPhysio:: Exiting ...')
        except (KeyboardInterrupt, SystemExit):
            if rp is not None:
                if not fdw.closed:
                    fdw.flush()
                    fdw.close()
                if sys.stderr.isatty():
                    sys.stderr.write('\nKeyboard Interrupt\n')
                    print except_msg()
                    sys.stderr.flush()
                rp.CleanUp()
            os._exit(0)
        except:
            msg = '\n%s\n' % except_msg()
            rp.LogMessage(msg)
            if sys.stderr.isatty():
                sys.stderr.write(msg)
            rp.CleanUp()
            os._exit(0)

if __name__ == '__main__':
    read_physio()
