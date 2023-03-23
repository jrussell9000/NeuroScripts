#!/usr/bin/env python

# Parts of this code was published in "Python Cookbook" by O'Reilly. It
# was downloaded from:
#       http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52296
# Slight modifications were required.


# Written by John Ollinger
#
# University of Wisconsin, 8/16/09

# Copyright (c) 2006-2007, John Ollinger, University of Wisconsin
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#    * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ** This software was designed to be used only for research purposes. **
# ** Clinical uses are not recommended, and have never been evaluated. **
# ** This software comes with no warranties of any kind whatsoever,    **
# ** and may not be useful for anything.  Use it at your own risk!     **
# ** If these terms are not acceptable, you aren't allowed to use the code.**

from distutils import sysconfig
import sys
import os
from stat import S_IRWXU, S_IRWXG, S_IRWXO
import traceback
import time
# import dummy_thread as thread
import socket
from email.mime.text import MIMEText
from subprocess import Popen, PIPE
# import fcntl
# from binascii import hexlify
import constants as c
# from queue import Empty
import Crypto

try:
    import paramiko
    from paramiko import ChannelException, SSHException, AuthenticationException, BadHostKeyException
except:
    pass

ID = "$Id: wbl_util.py 583 2011-07-08 18:47:42Z jmo $"[1:-1]

cvt_mode = {'r': os.O_RDONLY,
            'w': (os.O_CREAT | os.O_WRONLY),
            'a': os.O_APPEND}

str_to_bool = {'False': False, 'True': True}

email_server = 'mulato'
FIGARO_TMP = '/ESE/scratch/tmp'

# Define the location of the known-hosts table based on machine architercture.
host_type = sysconfig.get_config_vars('MACHDEP')[0]
if host_type == 'darwin':
    KNOWN_HOSTS = '/etc/ssh_known_hosts'
else:
    KNOWN_HOSTS = '/etc/ssh/ssh_known_hosts'


def except_msg(name=None, msg=None):
    """Create nicely formatted error message for exceptions."""
    exc = sys.exc_info()
    if exc[0] is None:
        return ''
    trc_back = traceback.extract_tb(exc[2])
    type = '%s' % exc[0]
    type = type.split('.')[-1][:-2]

    errstr = '\n' + 80 * '*' + '\n'
    if name:
        errstr = errstr + "Error encountered in: %s\n" % name
    else:
        errstr = errstr + "Error:" + str(exc[0]) + '\n'
    if msg:
        errstr += '%s\n' % msg
    errstr = errstr + \
        'Type: %s\n' % type + \
        'Description: *** %s ***\n' % exc[1] + \
        'Filename: %s%s\n' % (3 * " ", trc_back[0][0]) + \
        'Traceback:\n'

    for entry in trc_back:
        spaces = max(20 - len(entry[2]), 0)
        # names = entry[0].split('/')[-1]
        if len(entry[0]) < 52:
            fname = entry[0]
        else:
            fname = entry[0][-49:]
            fname = '...' + fname[fname.find('/'):]
        spaces1 = max(52 - len(fname), 0) * ' '
        errstr = errstr + '    %s:%s%s:%sline %d\n' % \
            (fname, spaces1, entry[2], spaces * " ", entry[1])
    errstr = errstr + \
        80 * '*' + '\n\n'
    return errstr


def execCmd(cmd, f_log=None, f_crash=None, verbose=False):
    """
    Function to execute a command and log results.  Only used by
    preprocess.
    """
    if verbose:
        sys.stdout.write('%s\n' % cmd)
    output = ''
    try:
        f = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        output, errout = f.communicate()
        errs = f.wait()
    except:
        raise OSError("bash command:\n%s\n%s\n" % (cmd, output))
        f_crash.write(cmd + '\n')
        f_crash.write(output + '\n')
        f_crash.write(errout + '\n')
    if errs:
        raise OSError(
            "Error executing command:\n%s\n%s\n%s" % (cmd, output, errout))

    if f_log is not None:
        f_log.write(cmd + '\n')
        f_log.write(output + '\n')
    if verbose:
        sys.stdout.write(output + '\n')


class Translate:
    """
    Translate characters supplied by the "frm" string to characters
    supplied by the "to" string.
    """
    allchars = str.maketrans('', '')

    def __init__(self, frm='', to='', delete='', keep=None):
        if len(to) == 1:
            to = to * len(frm)
        self.trans = str.maketrans(frm, to)
        if keep is None:
            self.delete = delete
        else:
            self.delete = self.allchars.translate(self.allchars,
                                                  keep.translate(self.allchars, delete))

    def __call__(self, s):
        return s.translate(self.trans, self.delete)


class Timer():
    """
    Object used to time execution of code.
    """

    def __init__(self):
        self.StartTimer()

    def StartTimer(self):
        self.start = time.time()

    def Elapsed(self):
        """
        Returns elapsed time in seconds.
        """
        return float(time.time() - self.start)

    def ReadTimer(self, min=0):
        """
        Compute elapsed time and return as a text string formatted as
        minutes:seconds:msec
        """
        end_time = time.time()
        elapsed_time = end_time - self.start
        if elapsed_time < 0:
            elapsed_time = 24 * 3600 + elapsed_time
        hrs = int(elapsed_time / 3600)
        mins = int((elapsed_time - hrs * 3600) / 60)
        secs = int((elapsed_time - hrs * 3600 - mins * 60))
        ms = 1000 * (elapsed_time - hrs * 3600 - mins * 60 - secs)
        if secs >= min:
            text = '%d:%02d:%03d' % (mins, secs, ms)
        else:
            text = ""
        return text


def ssh_connect(hostname, username, password=None, timeout=5):
    """
    Creates a paramiko SSHClient object and connects to <username>@<hostname>.
    The connect process times out after <timeout> seconds. An IOError
    exception is raised if the TCP connect fails.
    """
    try:
        client = paramiko.SSHClient()
        if os.path.exists(KNOWN_HOSTS):
            client.load_system_host_keys(KNOWN_HOSTS)
        else:
            client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        Crypto.Random.atfork()
        key_files = []
        auto_upload = '%s/.ssh/auto_upload' % os.getenv('HOME')
        if os.path.exists(auto_upload):
            key_files.append(auto_upload)
        id_rsa = '%s/.ssh/id_rsa' % os.getenv('HOME')
        if os.path.exists(id_rsa):
            key_files.append(id_rsa)
        id_dsa = '%s/.ssh/id_dsa' % os.getenv('HOME')
        if os.path.exists(id_dsa):
            key_files.append(id_dsa)
        if len(key_files) == 0:
            key_files = None
        client.connect(hostname, username=username, password=password,
                       key_filename=key_files, timeout=timeout)
    except (AuthenticationException, SSHException, socket.error,
            BadHostKeyException) as errmsg:
        raise IOError('Error opening ssh client to %s@%s\n%s\n%s\n' %
                      (username, hostname, errmsg, except_msg()))
    return client


class OpenRemote():
    def __init__(self, filename, mode, hostname, username, passwd=None):
        """
        Emulate a python file object for remote files., i.e.,
        opens <filename> with specified mode on the node
        <username>@<hostname>. <mode> takes on the usual values, "r", "w" etc.
        Host-key authentication is attempted if a password is not supplied.
        """
        try:
            self.client = ssh_connect(hostname, username, passwd)
            self.sftp = self.client.open_sftp()
        except AuthenticationException:
            raise IOError(
                'Authentication error: Could not open ssh client to %s@%s:%s\n' %
                (username, hostname, filename))
        try:
            self.fd = self.sftp.open(filename, mode)
        except (IOError, NameError, ChannelException, SSHException) as errmsg:
            raise IOError(
                'Authentication error: Could not open channel to %s@%s:%s\n%s\n' %
                (username, hostname, filename, errmsg))

    def write(self, data):
        return self.fd.write(data)

    def writelines(self, sequence):
        return self.fd.writelines()

    def seek(self, offset, whence=0):
        return self.fd.seek(offset, whence)

    def read(self):
        return self.fd.read()

    def readline(self, Nmax=None):
        return self.fd.readline(Nmax)

    def readlines(self, Nmax=None):
        return self.fd.readlines(Nmax)

    def flush(self):
        return self.fd.flush()

    def close(self):
        if self.fd:
            self.fd.close()
        return self.client.close()

    def tell(self):
        return self.fd.tell()


def ssh_validate(hostname, username, passwd):
    """
    Open a remote connection. Return True if successful.
    """
    # output = ""
    try:
        client = ssh_connect(hostname, username, passwd)
        client.close()
        return True
    except:
        return False


def ssh_exists(filename, hostname, username, passwd=None):
    """
    Return True if <username>@<hostname>:<filename> exists.
    """
    # x = ssh_stat(filename, hostname, username,
    #              passwd), filename, hostname, username, passwd
    if ssh_stat(filename, hostname, username, passwd) is None:
        return False
    else:
        return True


def ssh_stat(filename, hostname, username, passwd=None):
    """
    Return the python os.stat object for <username>@<hostname>:<filename>.
    """
    try:
        client = ssh_connect(hostname, username, passwd)
        sftp = client.open_sftp()
        status = sftp.stat(filename)
        sftp.close()
        client.close()
        return status
    except:
        return None


def scp(local_file, remote_file, hostname, username, passwd):
    """
    Emulate scp command by copying <local_file> to
    <username>@<hostname>:<remote_file>
    """
    client = ssh_connect(hostname, username, passwd)
    sftp = client.open_sftp()
    sftp.put(local_file, remote_file)
    sftp.close()
    client.close()


class SshExec():
    """
    Execute a remote command using ssh. Simplifies the interface to
    paramiko.SshClient a bit. Unlike ssh, it provides password authentication
    and it supports non-blocking reads from the child process's stdout and
    stderr streams.
    Note: Make sure the SshExec object isn't garbage-collected before the
    remote task completes!
    """

    def __init__(self, hostname, username, passwd=None, cmd=None, timeout=None):
        self.cmd = cmd
        self.timeout = timeout
        try:
            self.client = ssh_connect(hostname, username, passwd)
        except (SSHException, AuthenticationException) as errmsg:
            errmsg = 'Error connecting to %s@%s\n%s\n%s\n' % \
                (username, hostname, errmsg, except_msg())
            raise IOError(errmsg)

    def __call__(self, cmd=None, block=True):
        if cmd is not None:
            self.cmd = cmd
        if self.cmd is None:
            raise IOError('No command specified')
        else:
            return self.Exec(self.cmd, block=block)

    def Exec(self, cmd, block=True):
        """
        Execute <cmd> on the remote host.  Block until completion
        if <block> = True
        """
        self.cmd = cmd
        try:
            self.fin, self.fout, self.ferr = self.client.exec_command(cmd)
        except SSHException as errmsg:
            raise IOError('Error executing command: %s\n%s' %
                          (errmsg, except_msg()))
        errors = ''
        if block:
            output = self.fout.read()
            errors = self.ferr.read()
            self.fout = None
            self.fin = None
            self.ferr = None
#            self.close()
        else:
            #           Make channel non-blocking. The ChannelFile object used for I/O with
            #           SSHClient cannot be made nonblocking, so emulate Python file objects
            #           using low-level paramiko commands.
            self.ch = self.fin.channel
            self.ch.setblocking(0)
            if self.timeout is not None:
                self.ch.settimeout(self.timeout)
            output = None
            errors = None
        return output, errors

    def read(self, maxlength=100000):
        """
        Read up to <maxlength> bytes from the subprocesses stdout stream.
        """
        if self.ch.recv_ready():
            return self.ch.recv(maxlength)
        else:
            return ''

    def readerr(self, maxlength=100000):
        """
        Read up to <maxlength> bytes from the subprocesses stderr stream.
        """
        if self.ch.recv_stderr_ready():
            return self.ch.recv_stderr(maxlength)
        else:
            return ''

    def write(self, data):
        """
        Write <data> bytes to the subprocesses stdin stream.
        """
        if self.ch.exit_status_ready():
            raise IOError('Remote process has completed: %s' % self.cmd)
        else:
            if self.ch.send_ready():
                self.ch.sendall(data)

    def writeerr(self, data):
        if self.ch.exit_status_ready():
            raise IOError('Remote process has completed: %s' % self.cmd)
        else:
            if self.ch.send_ready():
                self.ch.sendall_stderr(data)

    def flush(self):
        """
        Flush the local processes input buffer.
        """
        if self.fin.channel.exit_status_ready():
            raise IOError('Remote process has completed: %s' % self.cmd)
        else:
            self.fin.flush()

    def close(self):
        self.client.close()

    def Running(self):
        """
        Return True if the remote process is running.  Assumes nonblockng mode.
        """
        return (True, False)[self.ch.exit_status_ready()]

    def ExitOK(self):
        """
        Return True if the remote process exited without errors.
        """
        if self.ch.exit_status_ready():
            return((True, False)[self.ch.recv_exit_status()])
        else:
            return(None)


def check_freedisk(path):
    """
    Check for amount of free disk space in megabytes on the partition
    containing "path".
    """
    if path and os.path.exists(path):
        st = os.statvfs(path)
#       Round block size down to 8k to mimic the df command.
        return((.85 * float(st.f_bfree) * (st.f_frsize / 1000) * 1000.) / 1.e6)
    else:
        return 0.


def chg_perm(path):
    """
    Change permissions and catch all errors. Errors are noncritical,
    so let them go without barfing on the screen.
    """
    try:
        os.chmod(path, S_IRWXU | S_IRWXG | S_IRWXO)
    except OSError:
        #        Noncritical error, let it go.
        pass


class GetTmpSpace():
    """
    Create a temporary directory named
    <tmpdir>/tmp_<pid>_<year><month><day>_<hour>:<minute>:<second>:<msec>
    where <pid> is the calling process's pid and tmpdir is selected from a
    list of potential paths.  The first is keyword <tmpdir>, then the primary
    and secondary tmp paths specified in constants.py, then /tmp, them the cwd.
    In each case, there must be at least <size> megabytes available.
    """

    def __init__(self, size, user_tmp=None):
        if user_tmp is not None:
            utmp = user_tmp
            if not os.access(user_tmp, os.W_OK):
                try:
                    os.makedirs(user_tmp)
                except:
                    utmp = None
        else:
            utmp = None
        self.tmpdir = self._SelectPath(size, utmp)

    def __call__(self):
        return self.tmpdir

    def _SelectPath(self, max_required, user_tmp=None):
        """
        Find place to write temporary files.
        max_required: Maximum amount of space required in MB.
        """
        candidate_paths = [c.primary_tmp_dir, c.secondary_tmp_dir,
                           '/tmp', os.getcwd()]
        if user_tmp is not None:
            if not os.path.exists(user_tmp):
                puser = os.path.dirname(user_tmp)
            else:
                puser = user_tmp
            candidate_paths = [puser] + candidate_paths
        tried = "Checked these paths for sufficient space:"
        for path in candidate_paths:
            if check_freedisk(path) > max_required and os.access(path, os.W_OK):
                if user_tmp is not None and path == user_tmp:
                    tmpdir = user_tmp
                else:
                    tmpdir = '%s/%s' % (path, self._TmpDirTag(path))
                self._CreateSubdir(tmpdir)
                if tmpdir:
                    break
        else:
            sys.stderr.write("get_tmp_space: Insufficient space available. ' + \
            asked for %d, found %d \n" % (max_required, check_freedisk(tmpdir)))
            sys.stderr.write(tried)
            tmpdir = None
        self.tmpdir = tmpdir
        return tmpdir

    def _TmpDirTag(self, tmpdir):
        ms = time.time()
        ms = int(1000 * (ms - int(ms)))
        return '%s_%d_%s:%03d' % (os.environ['LOGNAME'], os.getpid(),
                                  time.strftime('%y%b%d_%H:%M:%S'), ms)

    def _CreateSubdir(self, tmpdir):
        try:
            #           Create directory with time and user stamp.
            if tmpdir is not None:
                os.makedirs(tmpdir)
                chg_perm(tmpdir)
            return tmpdir
        except:
            return None

    def Clean(self):
        """
        Delete temporary directory and its contents.
        """
        if self.tmpdir is not None and os.path.exists(self.tmpdir):
            cmd = 'chmod -R 0777 %s && /bin/rm -rf %s' % \
                (self.tmpdir, self.tmpdir)
            f = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            output, errs = f.communicate()
            if errs:
                raise IOError(
                    'Error deleting tmp space:\n\t%s\n\tError: %s' % (cmd, errs))


def send_email(recipient, subject, message, sender=None):

    sendmail_location = "/usr/sbin/sendmail"  # may vary by system?

    # Create a text/plain message
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    p = Popen(
        "%s -t" % sendmail_location,
        shell=True,
        stdin=PIPE
    )
    p.communicate(msg.as_string())
    if p.returncode != 0:
        return True
    else:
        return False
        return False


def get_library_name(prefix):
    """
    Construct a name for fileio dyamic libraries from the architecture, processor, and python version.
    """
    import platform
    from distutils import sysconfig

    pyversion = ''.join(platform.python_version().split('.')[:2])

    deployment_tgt = sysconfig.get_config_vars(
        'MACOSX_DEPLOYMENT_TARGET')[0].replace('.', '')
    machdep = sysconfig.get_config_vars('MACHDEP')[0]
    if 'linux' in machdep:
        name = '%s_linux_%s_%s' % (prefix, platform.processor(), pyversion)
    elif 'darwin' in machdep:
        name = '%s_macosx_%s_%s_%s' % (prefix, deployment_tgt,
                                       platform.processor(), pyversion)
    else:
        name = '%s_unknown' % prefix
    return name


def ismounted(partition, hostname=None, username=None, password=None, timeout=2):
    """
    Start a remote or local task to run stat on the partition in question.  If the
    command completes before the timeout the partition is assumed to be mounted.
    """
    cmd = 'df -h %s' % partition
    if hostname is None or username is None:
        local = True
        f = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        s = f.stdout
        #       Make nonblocking
        # fn = s.fileno()
        # fl = fcntl.fcntl(fn, fcntl.F_GETFL)
    else:
        #       Remote host.
        local = False
        s = SshExec(hostname, username, password)
        s.Exec(cmd, block=False)
    time0 = time.time()
    time1 = time0
    while (time1 - time0) < timeout:
        if local:
            status = f.poll()
            if status is None:
                status = True
        else:
            status = s.Running()
        if not status:
            # out = s.read().strip()
            return True
        time.sleep(.1)
        time1 = time.time()
    s.close()
    return False


if __name__ == '__main__':
    sys.stdout.write('%s\n' % ID)
