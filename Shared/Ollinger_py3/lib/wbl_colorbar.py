#!/usr/bin/env python

ID = "$Id: wbl_colorbar.py 179 2009-08-21 18:13:58Z jmo $"[1:-1]

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


import os
import sys
import math

import wx
from numpy import sign, zeros, take, put, float, short, ubyte, array, arange, \
        integer, reshape, fliplr, flipud
from scipy.ndimage.interpolation import zoom

ID = "$Id: wbl_colorbar.py 179 2009-08-21 18:13:58Z jmo $"[1:-1]


GRAY = 1
COLOR42 = 2
SPECTRUM = 3
COLORBAR_WIDTH = 20
COLORWIN_WIDTH = 80
NATIVE_YDIM = 255

# Annotation formats.
text_cvt_fmt = {-4:'%1.7f',-3:'%1.6f',-2:'%1.5f',-1:'%1.4f', \
                 0:'%1.3f',1:'%1.3f',2:'%2.2f',3:'%3.1f', \
                 4:'%4.0f',5:'%5.0f',5:'%6.0f'}

def color42():

    """
    Function: color42()

    Purpose: Return palette for color32 color scale.
    """

    rgb = zeros([3,256],ubyte)

#   Red
    rgb[0,0:13] = 0
    rgb[0,3:26] = 102
    rgb[0,6:38] = 51
    rgb[0,51:64] = 85
    rgb[0,64:77] = 102
    rgb[0,77:89] = 119
    rgb[0,89:102] = 136
    rgb[0,102:115] = 51 #51
    rgb[0,128:140] = 85 #85
    rgb[0,140:153] = 68
    rgb[0,153:166] = 204
    rgb[0,166:178] = 238
    rgb[0,178:191] = 221
    rgb[0,217:229] = 204
    rgb[0,229:242] = 187
    rgb[0,242:256] = 255

#   Green
    rgb[1,0:13] = 0
    rgb[1,16:38] = 51
    rgb[1,51:64] = 85
    rgb[1,64:77] = 102
    rgb[1,77:89] = 119
    rgb[1,89:102] = 136
    rgb[1,102:115] = 102
    rgb[1,115:128] = 153
    rgb[1,128:140] = 204
    rgb[1,140:153] = 238
    rgb[1,153:166] = 255
    rgb[1,166:178] = 238
    rgb[1,178:191] = 221
    rgb[1,191:204] = 187
    rgb[1,204:217] = 136
    rgb[1,217:229] = 102
    rgb[1,229:242] = 68
    rgb[1,242:255] = 0
    rgb[1,255] = 0
#   Blue
    rgb[2,0:13] = 0
    rgb[2,13:26] = 85
    rgb[2,38:51] = 119
    rgb[2,51:64] = 136
    rgb[2,64:77] = 187
    rgb[2,77:89] = 204
    rgb[2,89:102] = 238
    rgb[2,102:115] = 51
    rgb[2,128:140] = 85
    rgb[2,140:153] = 68
    rgb[2,153:166] = 34
    rgb[2,166:178] = 102
    rgb[2,178:191] = 85
    rgb[2,191:204] = 68
    rgb[2,204:217] = 34
    rgb[2,217:229] = 17
    rgb[2,229:256] = 0

    return rgb

def afni_spectrum():

    """ Load AFNI spectrum color table from a dump of the table. """

    rgb = zeros([3,256],ubyte)

    rgb[0,:] = array((255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 254, 251, 248,  \
        245, 241, 238, 235, 231, 228, 225, 221, 218, 215, 211, 208,  \
        204, 201, 198, 194, 191, 187, 184, 180, 177, 173, 169, 166,  \
        162, 159, 155, 151, 147, 144, 140, 136, 132, 129, 125, 121,  \
        117, 113, 109, 105, 101, 97, 93, 88, 84, 80, 75, 71, 67, 62,  \
        57, 53, 48, 43, 38, 32, 27, 21, 14, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 18, 24, 30, 35)).astype(ubyte)
    rgb[1,:] = array((0, 0, 0, 0, 0, 17, 23, 29, 34, 40, 45, 50, 54,  \
        59, 64, 68, 73, 77, 81, 86, 90, 94, 98, 102, 106, 110, 114,  \
        118, 122, 126, 130, 134, 138, 141, 145, 149, 153, 156, 160,  \
        164, 167, 171, 174, 178, 181, 185, 188, 192, 195, 199, 202,  \
        206, 209, 213, 216, 219, 223, 226, 229, 233, 236, 239, 243,  \
        246, 249, 252, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 252, 249, 246, 243, 239, 236, 233, 229, 226, 223,  \
        219, 216, 213, 209, 206, 202, 199, 195, 192, 188, 185,  \
        181, 178, 174, 171, 167, 164, 160, 156, 153, 149, 145,  \
        141, 138, 134, 130, 126, 122, 118, 114, 110, 106, 102,  \
        98, 94, 90, 86, 81, 77, 73, 68, 64, 59, 54, 50, 45, 40,  \
        34, 29, 23, 17, 0, 0, 0, 0, 0)).astype(ubyte)

    rgb[2,:] = array((35, 30, 24, 18, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  \
        0, 0, 0, 0, 0, 0, 0, 0, 14, 21, 27, 32, 38, 43, 48, 53, 57,  \
        62, 67, 71, 75, 80, 84, 88, 93, 97, 101, 105, 109, 113,  \
        117, 121, 125, 129, 132, 136, 140, 144, 147, 151, 155,  \
        159, 162, 166, 169, 173, 177, 180, 184, 187, 191, 194,  \
        198, 201, 204, 208, 211, 215, 218, 221, 225, 228, 231,  \
        235, 238, 241, 245, 248, 251, 254, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,  \
        255, 255)).astype(ubyte)

    return rgb

class ColorBar(wx.Panel):
    def __init__(self, parent,palette, ID=-1,label="", pos=wx.DefaultPosition, \
                size=(20,255)):
        wx.Panel.__init__(self, parent, ID, pos, size, wx.NO_BORDER,label)
        self.fs = self.GetFont().GetPointSize()
#        self.SetBackgroundColour("darkslategray")
        self.SetBackgroundColour(wx.BLACK)
        self.SetForegroundColour("yellow")
        self.font = wx.Font(self.fs,wx.SWISS,wx.NORMAL,wx.NORMAL)
        self.SetMinSize(size)
        self.label=label
#        self.imgwin = parent.imgwin
        self.RefreshAll = parent.RefreshAll
        self.xdim = COLORBAR_WIDTH
        self.ydim = NATIVE_YDIM
        self.wxdim = size[0]
        self.wydim = size[1]
        self.colormin = 0.
        self.colormax = 1.

#       Get color scales.
        self.palette = palette
        self.rgb_c42 = color42()
        self.afni_spectrum = afni_spectrum()
        if palette == COLOR42:
            self.rgb = self.rgb_c42
        elif palette == SPECTRUM:
            self.rgb = self.afni_spectrum
        else:
            self.rgb = reshape((arange(256).astype(ubyte)). \
                    repeat(3),[256,3]).transpose()
        self.save_rgb = zeros([3,256],ubyte)
        self.save_rgb[:,:] = self.rgb[:,:]
        self.Palette = wx.Palette(self.rgb[0,:], self.rgb[1,:], self.rgb[2,:])
        self.hide = False
        self.gamma = 1
        self.gamma_corr = array(arange(256)).astype(ubyte)

#       Create an ndarray containing a color bar.
        self.rawimg = array(self.ydim-1-arange(self.ydim)). \
                    astype(integer).repeat(self.xdim).ravel()
        self.rawbar = self.MakeColors(self.rawimg)
        self.barimg = wx.ImageFromBuffer(self.xdim,self.ydim,self.rawbar)
        self.gamma = 1

#       Create black background.
        bkg_xdim = self.wxdim - self.xdim
        bkg_raw  = zeros([bkg_xdim*self.wydim], ubyte)
        bkg_img = self.MakeColors(bkg_raw)
        backimg = wx.ImageFromBuffer(bkg_xdim, self.wydim, bkg_img)
        self.bkg_bitmap = backimg.ConvertToBitmap()

#       Setup Threshold controls.
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lthresh = 0.
        self.uthresh = 1.
        self.ymin = 0
        self.ymax = 255
        self.y0 = 0
        self.y1 = 0
        self.ym1 = 0
        self.set_lower = True
        self.set_drag = False
        

#       Setup popup menu.
        self.gray_id = wx.NewId()
        self.c42_id = wx.NewId()
        self.spectrum_id = wx.NewId()
        self.flip_id = wx.NewId()
        self.hide_id = wx.NewId()
        self.reset_id = wx.NewId()
        self.alpha = wx.NewId()
        self.a0 = wx.NewId()
        self.a1 = wx.NewId()
        self.a2 = wx.NewId()
        self.a3 = wx.NewId()
        self.a4 = wx.NewId()
        self.a5 = wx.NewId()
        self.a6 = wx.NewId()
        self.a7 = wx.NewId()
        self.a8 = wx.NewId()
        self.a9 = wx.NewId()
        self.alpha_tab = {self.a0:0, self.a1:16, self.a2:32,  \
                self.a3:48, self.a4:64,self.a5:80, self.a6:96, \
                self.a7:112, self.a8:128, self.a9:196}

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_MENU,self.OnGray,id=self.gray_id)
        self.Bind(wx.EVT_MENU,self.OnColor42,id=self.c42_id)
        self.Bind(wx.EVT_MENU,self.OnSpectrum,id=self.spectrum_id)
        self.Bind(wx.EVT_MENU,self.OnFlip,id=self.flip_id)
        self.Bind(wx.EVT_MENU,self.OnHide,id=self.hide_id)
        self.Bind(wx.EVT_MENU,self.OnReset,id=self.reset_id)

        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a0)
        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a1)
        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a2)
        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a3)
        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a4)
        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a5)
        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a6)
        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a7)
        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a8)
        self.Bind(wx.EVT_MENU,self.OnAlpha,id=self.a9)

    def OnContextMenu(self, evt):
#       Popus menu for colorbar controls
        menu = wx.Menu()
        menu.Append(self.gray_id,'Gray scale')
        menu.Append(self.spectrum_id,'AFNI Spectrum')
        menu.Append(self.c42_id,'Discrete Colors')
        menu.Append(self.flip_id,'Flip Colors')
        if self.hide:
            menu.Append(self.hide_id,'Show')
        else:
            menu.Append(self.hide_id,'Hide')
        menu.Append(self.reset_id,'Reset')

#       Here is the alpha submenu.
        sm_alpha = wx.Menu()
        sm_alpha.Append(self.a0,'Alpha: 1')
        sm_alpha.Append(self.a1,'Alpha: 2')
        sm_alpha.Append(self.a2,'Alpha: 3')
        sm_alpha.Append(self.a3,'Alpha: 4')
        sm_alpha.Append(self.a4,'Alpha: 5')
        sm_alpha.Append(self.a5,'Alpha: 6')
        sm_alpha.Append(self.a6,'Alpha: 7')
        sm_alpha.Append(self.a7,'Alpha: 8')
        sm_alpha.Append(self.a8,'Alpha: 9')
        sm_alpha.Append(self.a9,'Alpha: 10')
        menu.AppendMenu(self.alpha,"Transparency",sm_alpha)

#       Pop it up.
        self.PopupMenu(menu)
        menu.Destroy()
#        evt.Skip()

    def OnPaint(self, evt):
        self.Redraw()

    def OnGray(self,evt):
        self.rgb = reshape((arange(256).astype(ubyte)). \
                    repeat(3),[256,3]).transpose()
        self.save_rgb[:,:] = self.rgb[:,:]
        self.Palette = wx.Palette(self.rgb[0,:], self.rgb[1,:], self.rgb[2,:])
        self.alpha = 255
        self.Redraw()
        self.Rebuild()
        self.RefreshAll()

    def OnColor42(self,evt):
        self.palette = COLOR42
        self.rgb = self.rgb_c42
        self.save_rgb[:,:] = self.rgb[:,:]
        self.Palette = wx.Palette(self.rgb[0,:], self.rgb[1,:], self.rgb[2,:])
        self.Rebuild()
        self.Redraw()
        self.RefreshAll()

    def OnSpectrum(self,evt):
        self.palette = SPECTRUM
        self.rgb = self.afni_spectrum
        self.save_rgb[:,:] = self.rgb[:,:]
        self.Palette = wx.Palette(self.rgb[0,:], self.rgb[1,:], self.rgb[2,:])
        self.Rebuild()
        self.Redraw()
        self.RefreshAll()

    def OnFlip(self,evt):
        x = reshape(self.rgb,[3,256])
        self.rgb = fliplr(x)
        self.save_rgb[:,:] = self.rgb[:,:]
        self.Palette = wx.Palette(self.rgb[0,:], self.rgb[1,:], self.rgb[2,:])
        self.Rebuild()
        self.Redraw()
        self.RefreshAll()

    def OnHide(self,evt):
        if self.hide:
            self.hide = False
        else:
            self.hide = True
        self.RefreshAll()

    def OnReset(self,evt):
        print 'Reset colorbar'
        self.lthresh = 0
        self.uthresh = 1
        self.gamma = 1
        self.gamma_corr = array(arange(256)).astype(ubyte)
        self.Rebuild()
        self.Redraw()
        self.RefreshAll()

    def OnLeftDown(self,evt):
        x0,self.y0 = evt.GetPosition()
        xmax,ymax = self.GetSize()
        y0 = ymax - self.y0
        self.drag = False
        if y0 < 0:
            y0 = 0
        if abs(self.uthresh*ymax - y0) < abs(self.lthresh*ymax - y0):
            self.set_lower = False
            print 'set upper'
        else:
            self.set_lower = True
            print 'set lower'
        self.Redraw()
        self.RefreshAll()

    def OnLeftUp(self,evt):
        xmax,ymax = self.GetSize()
        if self.drag:
#           Make sure this is a drag event to reduce false triggers.
            x1,y1 = evt.GetPosition()
            if self.set_lower:
                print 'lower',self.ymin,ymax,y1
                self.lthresh = float(ymax-y1)/float(ymax)
                if self.lthresh > self.uthresh:
                    self.lthresh = self.uthresh - .01
            else:            
                print 'upper',self.ymax,ymax,y1
                self.uthresh = float(ymax-y1)/float(ymax)
                if self.uthresh < self.lthresh:
                    self.uthresh = self.lthresh + .01
            self.drag = False
            self.y0 = 0
            self.lthresh = min(self.lthresh,1.)
            self.lthresh = max(self.lthresh,0.)
            self.uthresh = min(self.uthresh,1.)
            self.uthresh = max(self.uthresh,0.)
            print 'Thresholds: ',self.lthresh,self.uthresh
            self.rgb[:,:] = self.save_rgb[:,:]
            self.rgb[:,int(self.uthresh*self.wydim):] = 0
            self.rgb[:,:int(self.lthresh*self.wydim)] = 0
            self.Palette = wx.Palette(self.rgb[0,:], self.rgb[1,:], self.rgb[2,:])
            self.Rebuild()
            self.Redraw()
            self.RefreshAll()

    def OnMouseMotion(self,evt):
#       Get thresholds interactively.
        self.ym1 = self.y1
        x1,self.y1 = evt.GetPosition()
        if abs(self.y1 - self.y0) > 10:
            self.drag = True

    def OnAlpha(self,evt):
        self.alpha = self.alpha_tab[evt.GetId()]
        print 'OnAlpha: ',self.alpha
#        self.imgwin.RegenerateImage(self.imgwin.ulay)
#        self.RefreshImage()
        self.RefreshAll()

    def MakeColors(self, img):
        img = img.astype(integer).ravel()
        rawbar = zeros([len(img),3],ubyte)
        rawbar[:,0] = self.rgb[0,:].take(img)
        rawbar[:,1] = self.rgb[1,:].take(img)
        rawbar[:,2] = self.rgb[2,:].take(img)
#        self.rawbar.tostring()
        return rawbar

    def Rebuild(self):
        if self.palette == GRAY:
#           Only do gamma correction for gray-scales.
            self.rawbar = array(self.ydim-1-arange(self.ydim)).astype(ubyte)
            self.rawbar[int((1.-self.lthresh)*self.ydim):] = 0
            self.rawbar[:int((1.-self.uthresh)*self.ydim)] = 0
            self.rawbar = self.gamma_corr.take(self.rawbar)
            self.rawbar = (self.rawbar.repeat(self.xdim)).reshape([self.ydim,self.xdim])
            self.rawbar = self.rawbar.repeat(3).ravel()
        else:
            self.rawbar = self.MakeColors(self.rawimg)
        self.barimg = wx.ImageFromBuffer(self.xdim,self.ydim,self.rawbar.tostring())

    def DrawHashMarks(self,dc):
        N = int(self.wydim/25) + 1
        val = self.colormin
        delta = (self.colormax - self.colormin)/float(N-1)
        digits = int(math.log10(max(abs(self.colormin),abs(self.colormax))))
        fmt = text_cvt_fmt.get(digits,'%g')
        maxlgth = len(fmt%self.colormax)
        for i in range(N):
            y = self.wydim - i*25
            dc.SetFont(self.font)
            sval = (fmt % (self.colormin + float(i)*delta))
            sval = (maxlgth - len(sval))*' ' + sval
            dc.DrawText(sval,COLORBAR_WIDTH+5,y)

    def SetColorRange(self, min, max):
        self.colormin = min
        self.colormax = max

    def Redraw(self):
        if self.gamma_corr is not None:
            self.Rebuild()
        self.wxdim,self.wydim = self.GetSize()
        self.barimg.Rescale(COLORBAR_WIDTH,self.wydim)
        self.bitmap = self.barimg.ConvertToBitmap()
        dc = wx.ClientDC(self)
#        dc.SetBackground(wx.Brush("darkslategray"))
        dc.SetTextForeground("goldenrod")
        dc.Clear()
        pen = dc.GetPen()
        pen.SetColour('yellow')
        pen.SetWidth(1)
        dc.SetPen(pen)
        dc.DrawBitmap(self.bitmap,0,0,False)
        dc.DrawBitmap(self.bkg_bitmap,self.xdim,0,False)
        self.DrawHashMarks(dc)
        return dc


if __name__ == '__main__':
    sys.stdout.write('%s\n' % ID)
