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
from socket import gethostname

ID = "$Id: traffic_report.py 184 2009-09-01 16:36:46Z jmo $"[1:-1]

LOADS_INFO = '/scratch/tmp/tmp_loads.txt'
SERVERS = ['poblano', 'ancho', 'chilaca', 'mirasol', \
           'mulato', 'pasilla', 'punjab']

def current_is_best(hostname, bestload):
    if sys.argv[-1].strip() == '-v':
        print '\tCurrent server (%s) with a load factor of %4.2f is the best choice.' % (hostname, bestload)

def traffic_report():

    hostname = gethostname().split('.')[0]

    if hostname not in SERVERS:
        return

    f = open(LOADS_INFO, 'r')
    lines = f.readlines()
    f.close()

    loads = {}
    tags = []
    for line in lines:
        words = line.split()
        if len(words) < 2:
            continue
        if words[0].endswith(':') and len(words) == 4:
            loads[words[0][:-1]] = float(words[1])
            tags.append('%f_%s' % \
                    (int(round(float(words[1]))), words[0][:-1]))

#   Sort by time first, then hostname.
    tags.sort()
    if len(tags) == 0:
        current_is_best(hostname, bestload)
        return
    besthost = tags[0].split('_')[1]
    bestload = int(round(float(tags[0].split('_')[0])))

    current_load = int(round(float(loads.get(hostname, bestload))))
    sys.stdout.write('\n')
    if current_load > bestload+1:
#       Make a suggestion.
        print '\nCurrent load on %s: %f\nBetter Choices:' % \
                                    (hostname, loads[hostname])
        for tag in tags:
            server = tag.split('_')[1]
            pad = max(10 - len(server), 0)*' '
            if loads[server] < current_load:
                print '\t%s:%s load = %4.2f' % (server, pad, loads[server])
    else:
        current_is_best(hostname, bestload)
    sys.stdout.write('\n')

if __name__ == '__main__':
    traffic_report()

