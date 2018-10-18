#!/usr/bin/env python

import sys
import string
import os
try:
    from numpy.oldnumeric import *
except:
    from Numeric import *

MAX_GRAD = 2.4 # Maximum gradent strength

"""
Program: format_history

Purpose: Format history file from the GE simulator into a spreadsheet.

By: John Ollinger

"""

if(len(sys.argv) < 2):
    print "Usage: format_history history_file "
#    print "       -ssp: Include ssp codes."
    sys.exit(1)

iarg = 0
lcv = 0
lcssp = 1
for arg in sys.argv:
    if arg == "-v": 
        lcverbose = 1
#    if arg == "-ssp": 
#        lcssp = 1
    else:
        if arg[0] == "-":
            print "\n*** Could not parse this option: %s *** \n\n" % (arg)
            sys.exit(1)
    iarg = iarg + 1

input_file = sys.argv[1]
f = open(input_file,"r")
lines = f.readlines()
f.close

# Loop through each line in the file.
maxseq = 0
npulse = 0
npulses = []
boards = []
waveform_memory = 0
for line in lines:
    if string.find(line,"Board") >= 0:
        board = line[8:-1]
        boards.append(board)
    if string.find(line,"Sequence") >= 0:
        strt = string.find(line,"(")
        if strt > 0:
            end = string.find(line,")")
            seq = string.atoi(line[strt+1:end])
        elif string.find(line,":") == 10:
            seq = string.atoi(line[11:])
        else:
            seq = 1
        if seq > maxseq:
            maxseq = seq
        npulses.append(npulse/3)
        npulse = 0
    if line != "\n":
        npulse = npulse + 1


start_times = zeros(4000,Int)
np_total = 0
print "Sequence\tBoard\tPulse\tType\tAmp\tStart\tEnd\tDur\tPer\tAmpl\tArea\tAbs_Area\tNsinc_Cycles\tAlpha"
for seq in range(maxseq):
    np = 0
    Board = []
    Pulse = []
    Type = []
    Amp = []
    Start = []
    End = []
    Dur = []
    Per = []
    Ampl = []
    Area = []
    Abs_Area = []
    SSP_codes = []
    nsinc = []
    alpha = []
    inseq = 0
    line_number = 1
    linetype = -1
    if lines[0] == "\n":
        filetype = "plotpulse"
    else:
        filetype = "ipgsim"
    for line in lines:
#       Get the sequence of the current line.
        line_number = line_number + 1
        if  string.find(line,"Board") >= 0 or string.find(line,"Sequence") >= 0 or string.find(line,"Pulse:") >= 0 or string.find(line,"Area:") or string.find(line,"Instr:") >= 0:
            parse_line = 1
        else:
            parse_line = 0
        if string.find(line,"Board") == 1:
            board = string.strip(line[8:-1])
        if string.find(line,"Sequence") > 0 and parse_line:
            strt = string.find(line,"(")
            if strt >= 0:
                end = string.find(line,")")
                fseq = string.atoi(line[strt+1:end])
            else:
                strt = string.find(line,":")
                fseq = string.atoi(line[strt+1:])
            if seq+1 == fseq: 
               inseq = 1
            else:
               inseq = 0 
        if inseq:
#           Save this line in output. 
            line = string.replace(line,": ",":")
            fields = string.split(line)
            keywordm1 = ""
            for field in fields:

                subfields = string.split(field,":")
#                print 111,subfields
                keyword = string.strip(subfields[0]) 
#                print line,'keyword: ',keyword
                if keyword == 'Amp' and linetype == 1:
                    keyword = 'Ampl' # Plotpulse uses same keyword twice.
###                if len(subfields) == 1:
###                    print "...%s..." % keyword
###                else:
###                    print "...%s...%s..." % (keyword,subfields[1])
                if keyword == 'Pulse':
#                    print 222,subfields,fields
                    linetype = 0
                    Pulse.append(fields[1])
                    Board.append(board)
                    np = np + 1
                    opcodes = ""
                    SSP_codes.append("")
                    nsinc.append("")
                    alpha.append("")
                elif keyword == 'Instr':
                    linetype = 1
                elif keyword == 'Type':
                    type = subfields[1]
                    Type.append(type)
###                    print "...%s...%s..." % (board,type)
                    if type == 'Reserve' or type == "External":
#                       No amplitude for this type of pulse.
                        Amp.append("") 
                    elif type == 'Bits':
                        Amp.append("") 
                        Ampl.append("") 
                        if filetype == "plotpulse":
                            Per.append("")
                    elif board == 'SSP' and type == 'Const':
                        Amp.append("") 
                        Ampl.append("") 
                elif keyword == 'Amp':
                    value = "%7.3f" % (MAX_GRAD*string.atof(subfields[1])/32768.)
                    if keywordm1 == 'Start':
                        start_amp = value
                    elif keywordm1 == 'End':
                        value = "%s %s" % (start_amp,value)
                        Amp.append(value)
                    else:
                        if linetype == 0:
                            Amp.append(value)
                        else:
                            Ampl.append(value)
                elif keyword == 'Start':
                    if len(subfields) == 2:
                        value = "%7.3f" % (string.atof(subfields[1])/1000.)
                        start_times[np-1] = string.atoi(subfields[1])
                        Start.append(value)
                elif keyword == 'End':
                    if len(subfields) == 2:
                        value = "%7.3f" % (string.atof(subfields[1])/1000.)
                        End.append(value)
                elif keyword == 'Dur':
                    value = "%7.3f" % (string.atof(subfields[1])/1000.)
                    Dur.append(value)
                elif keyword == 'Per':
                    Per.append(subfields[1])
                elif keyword == 'Ampl':
                    value = "%7.5f" % (MAX_GRAD*string.atof(subfields[1])/32768.)
                    Ampl.append(value)
                elif keyword == 'Area':
                    linetype = 2
                    if keywordm1 == 'Abs':
                        Abs_Area.append(subfields[1])
                    else:
                        Area.append(subfields[1])
                elif keyword == 'Cycl':
                    if keywordm1 == 'Nsinc':
                        nsinc[np-1] = subfields[1]
                elif keyword == 'Alpha':
                    alpha[np-1] = subfields[1]
                keywordm1 = keyword
            if len(fields) > 0:
                keyword = string.strip(fields[0]) 
#                print keyword
                if (keyword == 'Waveform' or keyword == 'WaveM:') and board == 'SSP':
                    waveform_memory = 1
                    if len(fields) > 4:
                        if string.strip(fields[4]) == '#':
                            for arg in fields[5:]:
                                opcodes = opcodes + "%s " % string.strip(arg)
                            opcodes = opcodes + "\t"
                        else:
                            opcodes = ""
                    else:
                        opcodes = ""
                elif waveform_memory and len(fields) > 4:
#                   Save SSP operations.
                    if string.strip(fields[3]) == '#':
                        for arg in fields[4:]:
                            opcodes = opcodes + "%s " % string.strip(arg)
                        opcodes = opcodes + "\t"
            if waveform_memory and len(fields) < 2:
#                    print "saving codes",opcodes
#                    print 111,np,len(SSP_codes),len(Pulse)
                    SSP_codes[np-1] = string.strip(opcodes)
                    opcodes = ""
                    waveform_memory = 0

        if len(Amp) != len(Pulse):
            print "Error: Keyword not present at line #%d, line = %s" % (line_number,line)
            sys.exit(1)
#   Now sort by starting time and write to output.
#    print len(Board)
#    print len(Pulse)
#    print len(Type)
#    print len(Amp)
#    print len(Start)
#    print len(End)
#    print len(Dur)
#    print len(Per)
#    print len(SSP_codes)
    np_total = np_total + np
    idx = argsort(start_times[:np])
    for i in range(np):
        if Board[idx[i]] == 'SSP':
            if lcssp:
                print "%d\t%s\t%s\t%s\t%s\t%11.3f\t%11.3f\t%11.3f\t%s\t%s" % (seq+1,Board[idx[i]],Pulse[idx[i]],Type[idx[i]],Amp[idx[i]],float(Start[idx[i]]),float(End[idx[i]]),float(Dur[idx[i]]),Per[idx[i]],SSP_codes[idx[i]])
#            else:
#                print "%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (seq+1,Board[idx[i]],Pulse[idx[i]],Type[idx[i]],Amp[idx[i]],Start[idx[i]],End[idx[i]],Dur[idx[i]],Per[idx[i]])
        else:
            print "%d\t%s\t%s\t%s\t%s\t%11.3f\t%11.3f\t%11.3f\t%s\t%s\t%s\t%s\t%s\t%s" % (seq+1,Board[idx[i]],Pulse[idx[i]],Type[idx[i]],Amp[idx[i]],float(Start[idx[i]]),float(End[idx[i]]),float(Dur[idx[i]]),Per[idx[i]],Ampl[idx[i]],Area[idx[i]],Abs_Area[idx[i]],nsinc[idx[i]],alpha[idx[i]])

print "Total number of pulses: %d" % np_total
