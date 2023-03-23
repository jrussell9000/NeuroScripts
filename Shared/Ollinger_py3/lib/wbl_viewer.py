#!/usr/bin/env python

ID = "$Id: wbl_viewer.py 216 2009-11-18 01:43:09Z jmo $"[1:-1]

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
import wx
from wx.py.buffer import Buffer
import math

from numpy import zeros, float, arange, where, fliplr, integer, ubyte, \
            ndarray, array, empty, isnan, ones, fromstring
from scipy.ndimage.interpolation import zoom

from wbl_colorbar import ColorBar, COLOR42, GRAY, SPECTRUM, COLORWIN_WIDTH
from wbl_text_dialog import TextDialog
from file_io import Wimage


GLOBAL_SCALE = 1
LOCAL_SCALE = 2
FIXED_SCALE = 3
PERFUSION_SCALE = 4
    
AXIAL = 1
SAGITTAL = 2
CORONAL = 4

NEAREST_NEIGHBOR = 0
LINEAR = 1
CUBIC_SPLINE = 2

DEFAULT_WIDTH = 256.
MAX_WIDTH = 1024
STATUS_HGHT = 50

colorscales = {'gray':GRAY, 'spectrum':SPECTRUM, 'color42':COLOR42}
interp_cvt = {'nearest_neighbor':NEAREST_NEIGHBOR, 'linear':LINEAR, \
              'cubic':CUBIC_SPLINE}

#class WblImagePanel(wx.Panel):

def get_save_filename(parent, topdir=None, filter=None):
#   Open file dialog box.
    if filter is None:
        filter = "AFNI (*.HEAD) | *.HEAD | Analyze files (*.hdr)" + \
                         "| *.hdr | Nifti files (*.nii) | *.nii"
    if topdir is None:
        topdir = os.getcwd()
    dlg = wx.FileDialog(parent, message="Choose File", \
                        defaultDir=os.getcwd(), \
                        defaultFile="", \
                        wildcard='%s*.png' % filter, \
                        style=wx.FD_SAVE | wx.CHANGE_DIR)

    if dlg.ShowModal() == wx.ID_OK:
        filename = dlg.GetPaths()[0]
        dlg.Destroy()
        return(filename)
    else:
        sys.stderr.write("Read dialog failed.\n")
        dlg.Destroy()
        return None


class Viewer(wx.Panel):

    def __init__(self, topframe, image=None, statusbar=None, ID=-1, label="", \
        left_is_left=True, interp=LINEAR, \
        pos=wx.DefaultPosition, size=(DEFAULT_WIDTH, DEFAULT_WIDTH)):

        wx.Panel.__init__(self,topframe, ID, pos, size, wx.NO_BORDER,label)
        self.image = image
        self.topframe = topframe
        self.annotations = {}
        self.fs = self.GetFont().GetPointSize()
        self.fs = 14
        self.font = wx.Font(self.fs,wx.SWISS,wx.NORMAL,wx.BOLD)
        self.SetBackgroundColour(wx.BLACK)
        self.statusbar = statusbar
        self.SetMinSize(size)
        self.win_xdim = size[0]
        self.win_ydim = size[1]
#       Image stuff.
        self.left_is_left = left_is_left
        self.fixed_min = 0
        self.fixed_max = 10000
        self.interp = interp
        self.scale_type = LOCAL_SCALE
        self.scale_offset = 0.
        self.scale_factor = 1.
        self.drag_y0 = 0

#       Bind main image window popup.
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
#        self.Bind(wx.EVT_MENU,self.OnXProf,id=self.x_prof_id)
#        self.Bind(wx.EVT_MENU,self.OnYProf,id=self.y_prof_id)
#        self.Bind(wx.EVT_MENU,self.OnTProf,id=self.t_prof_id)
#        self.Bind(wx.EVT_MENU,self.OnSqReg,id=self.sqreg_id)
#        self.Bind(wx.EVT_MENU,self.OnOverplot,id=self.overplot_id)
#        self.Bind(wx.EVT_MENU,self.OnSaveProf,id=self.saveprof_id)
#        self.Bind(wx.EVT_MENU,self.OnSelectAxial,id=self.axl_id)
#        self.Bind(wx.EVT_MENU,self.OnSelectSagittal,id=self.sag_id)
#        self.Bind(wx.EVT_MENU,self.OnSelectCoronal,id=self.cor_id)

#       Profile options submenu IDs.
#        self.profopt_id = wx.NewId()
#        self.profopt_lines_id = wx.NewId()
#        self.profopt_pts_id = wx.NewId()
#        self.profopt_lpts_id = wx.NewId()
#        self.profopt_size_id = wx.NewId()
#        self.profopt_which_id = wx.NewId()
#       Bind profile options submenu
#        self.Bind(wx.EVT_MENU,self.OnProfLines,id=self.profopt_lines_id)
#        self.Bind(wx.EVT_MENU,self.OnProfPoints,id=self.profopt_pts_id)
#        self.Bind(wx.EVT_MENU,self.OnProfLinesPoints,id=self.profopt_lpts_id)
#        self.Bind(wx.EVT_MENU,self.OnProfSize,id=self.profopt_size_id)
#        self.Bind(wx.EVT_MENU,self.OnProfWhich,id=self.profopt_which_id)

        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)

#       Submenu IDs
        self.imgopt_id = wx.NewId()
        self.img_sclopt_id = wx.NewId()
        self.img_interp_id = wx.NewId()

#       Image options submenu ID
        self.imgopt_globscl_id = wx.NewId()
        self.imgopt_locscl_id = wx.NewId()
        self.imgopt_fixscl_id = wx.NewId()
        self.imgopt_perfscl_id = wx.NewId()
        self.imgopt_leftisleft_id = wx.NewId()

        self.Bind(wx.EVT_MENU,self.OnGlobalScale,id=self.imgopt_globscl_id)
        self.Bind(wx.EVT_MENU,self.OnLocalScale,id=self.imgopt_locscl_id)
        self.Bind(wx.EVT_MENU,self.OnFixedScale,id=self.imgopt_fixscl_id)
        self.Bind(wx.EVT_MENU,self.OnLeftIsWhat,id=self.imgopt_leftisleft_id)

#       Interpolation methods
        self.img_uinterp_id = wx.NewId()
        self.img_ointerp_id = wx.NewId()
        self.imgopt_uintrp_nn_id = wx.NewId()
        self.imgopt_uintrp_li_id = wx.NewId()
        self.imgopt_uintrp_cu_id = wx.NewId()
        self.imgopt_ointrp_nn_id = wx.NewId()
        self.imgopt_ointrp_li_id = wx.NewId()
        self.imgopt_ointrp_cu_id = wx.NewId()
        self.Bind(wx.EVT_MENU,self.InterpNN,id=self.imgopt_uintrp_nn_id)
        self.Bind(wx.EVT_MENU,self.InterpLinear,id=self.imgopt_uintrp_li_id)
        self.Bind(wx.EVT_MENU,self.InterpCubic,id=self.imgopt_uintrp_cu_id)

#       Image options submenu IDs.
        self.profopt_id = wx.NewId()

        self.profopt_pts_id = wx.NewId()
        self.profopt_lpts_id = wx.NewId()
        self.profopt_size_id = wx.NewId()
        self.profopt_which_id = wx.NewId()

        self.copy_id = wx.NewId()
        self.png_id = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnCopy, id=self.copy_id)
        self.Bind(wx.EVT_MENU, self.OnPng, id=self.png_id)

#       Initialize status bar.
        if self.statusbar:
            self.UpdateStatusBarStatus()

    def OnPaint(self, evt):
        self.RefreshAll()

    def OnContextMenu(self,evt):
#       Create options popup menu
        menu = wx.Menu()

 #       sm_imgopt = wx.Menu()

#       Image scaling options sub-submenu.
        ssm_imgopt_scale = wx.Menu()
        ssm_imgopt_scale.Append(self.imgopt_globscl_id,'Global')
        ssm_imgopt_scale.Append(self.imgopt_locscl_id,'Local')
        ssm_imgopt_scale.Append(self.imgopt_fixscl_id,'Fixed')
#        ssm_imgopt_scale.Append(self.imgopt_perfscl_id,'Perfusion Scaling')

        ssm_imgopt_interp = wx.Menu()
        ssm_imgopt_interp.Append(self.imgopt_uintrp_nn_id,'Nearest Neighbor')
        ssm_imgopt_interp.Append(self.imgopt_uintrp_li_id,'Linear')
        ssm_imgopt_interp.Append(self.imgopt_uintrp_cu_id,'Cubic Spline')

#       Stack up the menus
#        sm_imgopt.AppendMenu(self.img_sclopt_id,"Scaling Options",ssm_imgopt_scale)
#        sm_imgopt.AppendMenu(self.img_uinterp_id,"Interpolation",ssm_imgopt_interp)
        if self.left_is_left:
            menu.Append(self.imgopt_leftisleft_id,'Left is Right')
        else:
            menu.Append(self.imgopt_leftisleft_id,'Left is Left')
#        menu.AppendMenu(self.imgopt_id,"Image Options",sm_imgopt)
        menu.AppendMenu(self.img_sclopt_id,"Scaling Options",ssm_imgopt_scale)
        menu.AppendMenu(self.img_uinterp_id,"Interpolation",ssm_imgopt_interp)
        menu.Append(self.copy_id,"Copy")
        menu.Append(self.png_id,"Save PNG")

        self.PopupMenu(menu)
        menu.Destroy()
        evt.Skip()
        self.RefreshAll()

    def OnPng(self, evt):
        if hasattr(self.topframe, 'ScreenDump'):
            self.topframe.ScreenDump()

    def OnCopy(self, evt):
        if hasattr(self.topframe, 'CopyToClipboard'):
            self.topframe.CopyToClipboard()

    def OnLeftDown(self, evt):
        xwin, ywin = evt.GetPosition()
        self.drag_y0 = ywin
        scl = float(self.xdim)/float(self.win_xdim)
        if self.left_is_left:
            xval = int(round(scl*(self.win_xdim - xwin - 1)))
        else:
            xval = int(round(scl*xwin))
        yval = int(round(scl*ywin))
        value = float(self.image[yval, xval])
        status_txt = '(%d,%d): %f' % (xval, yval, value)
        self.statusbar.SetStatusText(status_txt,0)

    def OnLeftUp(self, evt):
        pass
#        print 'In OnLeftUp'
#        self.RefreshAll()

    def OnMouseMotion(self,evt):
        if evt.LeftIsDown():
            xpos,ypos = evt.GetPosition()
#           Left button depressed, drag event.
            if evt.LeftIsDown() and abs(ypos - self.drag_y0) > 10:
#               Changing value of gamma.
                dgamma = .05*float(ypos-self.drag_y0)/float(self.win_ydim)
                self.topframe.colorbar.gamma =  self.topframe.colorbar.gamma + dgamma
                if self.topframe.colorbar.gamma < .05:
                    self.topframe.colorbar.gamma = .05
                scl = 255./(255.**self.topframe.colorbar.gamma)
                self.topframe.colorbar.gamma_corr = (scl*array(arange(256). \
                        astype(float))**self.topframe.colorbar.gamma).astype(ubyte)
                self.topframe.colorbar.Redraw()
                self.RefreshAll()

    def OnGlobalScale(self,evt):
        self.scale_type = GLOBAL_SCALE
        self.RefreshAll()

    def OnLocalScale(self,evt):
        self.scale_type = LOCAL_SCALE
        self.RefreshAll()

    def OnFixedScale(self,evt):
        dlg = TextDialog(self, -1, \
                        'Enter max and min values', \
                        ['Min:', 'Max:'], \
                        ['%f'%self.image.min(), '%f'%self.image.max()])
        dlg.CenterOnScreen()
        value = dlg.ShowModal()
        if value == wx.ID_OK:
            test = dlg.values[0] + dlg.values[1]
            test = test.replace('.','0').replace('-','0')
            if test.isdigit():
                self.scale_type = FIXED_SCALE
                self.fixed_min = float(dlg.values[0])
                self.fixed_max = float(dlg.values[1])
                self.topframe.colorbar.colormin = self.fixed_min
                self.topframe.colorbar.colormax = self.fixed_max
                self.RefreshAll()

    def OnLeftIsWhat(self,evt):
        if self.left_is_left:
            self.left_is_left = False
        else:
            self.left_is_left = True
        self.RefreshAll()
        self.UpdateStatusBarStatus()


    def InterpNN(self,evt):
        self.interp = NEAREST_NEIGHBOR
#        self.Reinitialize(self.ulay,self.ulay.hdr,Rcrt=self.Rcrt)
        self.RefreshAll()

    def InterpLinear(self,evt):
        self.interp = LINEAR
#        self.ulay.Reinitialize(self.ulay,self.ulay.hdr,Rcrt=self.Rcrt)
        self.RefreshAll()

    def InterpCubic(self,evt):
        self.interp = CUBIC_SPLINE
#        self.ulay.Reinitialize(self.olay,self.olay.hdr,self.ulay.hdr,Rcrt=self.Rcrt)
        self.RefreshAll()


    def RefreshAll(self, image=None):
        if image is not None:
            self.image = image
        self.RegenerateImage(self.image)
        if self.topframe.colorbar:
            self.topframe.colorbar.Redraw()
        self.RefreshImage()

    def RegenerateImage(self, image):
        if not isinstance(image, ndarray):
            raise RuntimeError('Invalid image.')
#       Recompute bitmap from ndarray. Usually in response to slider, resize events eg.
        self.ydim, self.xdim = image.shape
        self.win_ydim, self.win_xdim = self.GetSize()
        zoom1 = float(self.win_xdim)/float(self.xdim)
        zoom2 = float(self.win_ydim)/float(self.ydim)
        if zoom1 < zoom2:
            self.zoom_factor = zoom1
        else:
            self.zoom_factor = zoom2
        if image is not None:
            img = zoom(image, self.zoom_factor,order=self.interp)
#       Find the appropriate min and max
        if self.scale_type == GLOBAL_SCALE:
            min = img.min()
            max = img.max()
        elif self.scale_type == FIXED_SCALE:
            min = self.fixed_min
            max = self.fixed_max
            img = where(img < min, min, img)
            img = where(img > max, max, img)
#        else:
        min = img.min()
        max = img.max()
        min = (min - self.scale_offset)*self.scale_factor
        max = (max - self.scale_offset)*self.scale_factor
        img = where(img > max, max, img)
        img = where(img < min, min, img)
#       Flip to requested orientation
        if self.left_is_left:
            img = fliplr(img)
        if (max-min) == 0 or isnan(min) or isnan(max):
            img = zeros(img.shape,integer).ravel()
        else:
            img = ((img-min)*255./(max - min)).astype(integer).ravel()
        img = self.topframe.colorbar.gamma_corr.take(img)

#       Display with current color map.
        rgb_palette = self.topframe.colorbar.rgb
        rgb = zeros([len(img),3],ubyte)
        rgb[:,0] = rgb_palette[0,:].take(img)
        rgb[:,1] = rgb_palette[1,:].take(img)
        rgb[:,2] = rgb_palette[2,:].take(img)

        xdim = int(self.zoom_factor*self.xdim)
        ydim = int(self.zoom_factor*self.ydim)
        wximg = wx.ImageFromBuffer(xdim, ydim, rgb.tostring())
#        alpha = empty(image.zxdim*image.zydim,ubyte)
#        alpha[:] = image.colorbar.alpha
#        image.img.SetAlphaData(alpha)
        alpha = empty(xdim*ydim, ubyte)
        alpha[:] = 255
        wximg.SetAlphaData(alpha)
        self.bitmap = wximg.ConvertToBitmap()

    def RefreshImage(self):
#       Update the display and colorbars.
        dc = wx.ClientDC(self)
#        dc.SetBackgroundMode(wx.SOLID)
        dc.SetTextForeground("goldenrod")
        dc.Clear()
#        dc.FloodFill(0, 0, wx.BLACK)
        pen = dc.GetPen()
        pen.SetColour('yellow')
        pen.SetWidth(1)
        dc.SetPen(pen)
        dc.DrawBitmap(self.bitmap, 0, 0, False)
#        self.topframe.parent.palette = self.bitmap.GetPalette()
        if self.annotations.has_key('text'):
#            xpos = self.annotations['xpos']
#            ypos = self.annotations['ypos']
            text = self.annotations['text']
            xpos = self.annotations.get('xpos', None)
            if not xpos:
                xpos = 5
            ypos = self.annotations.get('ypos', None)
            if not ypos:
                ypos = self.win_ydim - 20
            dc.SetFont(self.font)
            dc.DrawText(text, xpos, ypos)
 
    def OnResize(self):
        print 'In OnResize'
        self.RefreshAll()

    def UpdateStatusBarStatus(self):
        scale_string = ['Gscl','Lscl','Fscl']
        if self.left_is_left:
            status_txt = "LisL"
        else:
            status_txt = "LisR"
        interp_string = ['NN','Li','Cu']
        interp_str = interp_string[self.interp]
        scale_type = self.scale_type
        status_txt = "%s, %s, %s" % (status_txt, \
                scale_string[scale_type-1],interp_str)
        self.statusbar.SetStatusText(status_txt,1)

class ViewPanel(wx.Panel):

    def __init__(self, parent, nrow, ncol, ID=-1, pos=(0,0), label='', colorscale=GRAY, left_is_left=True, interp=LINEAR):
#       Create the widgets and bind them to event callbacks.
        self.parent = parent
        self.top_png_dir = None
        self.RefreshAll = parent.RefreshAll
        size = parent.GetSize()
        wx.Panel.__init__(self, parent,ID,pos,size,wx.NO_BORDER,label)
        self.imgwin = []
        for z in xrange(self.parent.zdim):
            self.imgwin.append(Viewer(self, self.parent.image[z,...], \
                self.parent.statusbar, left_is_left=left_is_left, interp=interp))
        self.colorbar = ColorBar(self, colorscale, size=(self.parent.xcolordim, \
                            self.parent.ycolordim), pos=(self.parent.img_xdim, 0))
        self.colorbar.gamma_corr = array(arange(256)).astype(ubyte)
#        self.imgwin.SetSizeHints(xmin,ymin,5*xmin,5*ymin,xmin/4,ymin/4)

#       Arrange the windows with the box sizer.
        topsizer = wx.BoxSizer(wx.HORIZONTAL)
        imgsizer = wx.BoxSizer(wx.VERTICAL)
        sizers = []
        z = 0
        for row in xrange(nrow):
            rowsizer = wx.BoxSizer(wx.HORIZONTAL)
            for col in xrange(ncol):
                rowsizer.Add(self.imgwin[z], 1., border=parent.borderwidth, \
                         flag=wx.ALIGN_LEFT | wx.SHAPED | wx.EXPAND | wx.ALL)
                z += 1
            imgsizer.Add(rowsizer, 1., wx.ALIGN_BOTTOM | wx.SHAPED | wx.EXPAND)
        topsizer.Add(imgsizer, 1.,  wx.ALIGN_LEFT | wx.SHAPED | wx.EXPAND) 
        topsizer.Add(self.colorbar, 0.,  wx.ALIGN_LEFT | wx.SHAPED | wx.EXPAND) 
        topsizer.Fit(self.colorbar)
        self.SetSizerAndFit(topsizer)
        self.parent.imgwin = self.imgwin
        self.parent.colorbar = self.colorbar
        self.SetBackgroundColour("darkslategray")

    def GetScreenBitmap(self):
        self.RefreshAll()
        viewer_dc = wx.ClientDC(self)
        width, height = self.GetClientSizeTuple()
        dcm = wx.MemoryDC()

        dcm.SetPalette(self.colorbar.Palette)
        self.screen_bitmap = wx.EmptyBitmap(width, height, wx.BITMAP_TYPE_PNG)
        dcm.SelectObject(self.screen_bitmap)
        dcm.Blit(0, 0, width, height, viewer_dc, 0, 0)
        dcm.SelectObject(wx.NullBitmap)
        self.screen_image = self.screen_bitmap.ConvertToImage()
        size = self.screen_image.GetSize()

#       Stupid Blit method only puts the data in the alpha channel. Fix it.
        alpha = self.screen_image.GetAlphaData()
        N = len(alpha)
        newdata = zeros([N,3], ubyte)
        alphab = fromstring(alpha, ubyte)
        newdata[: ,0] = alphab
        newdata[: ,1] = alphab
        newdata[: ,2] = alphab
        self.screen_image.SetData(newdata.ravel().tostring())
        self.screen_bitmap = self.screen_image.ConvertToBitmap(8)

    def ScreenDump(self, filename=None):
        if filename is None:
            filename = get_save_filename(self, filter='png', topdir=self.top_png_dir) 
        self.top_png_dir = os.path.dirname(filename)
        self.GetScreenBitmap()
        self.screen_bitmap.SaveFile(filename, wx.BITMAP_TYPE_PNG)

    def CopyToClipboard(self):
        clip = wx.TheClipboard
        if not clip.IsSupported:
            raise RuntimeError('Clipboard is not supported on this machine.')
        self.GetScreenBitmap()
        status = clip.Open()
        bitmap = wx.BitmapDataObject(self.screen_bitmap)
        status = clip.SetData(bitmap)
        clip.Flush()
        clip.Close()



class WblImageDisplay(wx.Frame):
    
    def __init__(self):
        self.colormin = 0.
        self.colormax = 10.
        self.annotations = {}
        self.copy_to_clipboard = False

    def CopyToClipboard(self):
        if self.copy_to_clipboard:
            self.CopyToClipboard()

    def Init(self, image, ncol=None, title='', colors='gray', left_is_left=True,\
             interp='linear', pane_size=DEFAULT_WIDTH):

        interp1 = interp_cvt.get(interp, None)
        if interp1 is None:
            raise RuntimeError('Invalid value of interp: %s' % interp)
        colorscale = colorscales[colors] 
        self.borderwidth = 1
        if image.ndim == 3:
            self.zdim, self.ydim, self.xdim = image.shape
        else:
            self.ydim, self.xdim = image.shape
            self.zdim = 1
        self.image = image.reshape([self.zdim, self.ydim, self.xdim])
        if isinstance(pane_size, tuple):
            zoom_factor = pane_size[1]/self.ydim
        else:
            zoom_factor = pane_size/self.ydim
        self.img_xdim = self.xdim*zoom_factor
        self.img_ydim = self.ydim*zoom_factor
        self.colorbar = None
        if not ncol:
            ncol = int(MAX_WIDTH/self.img_xdim)
            if ncol > self.zdim:
                ncol = int(self.zdim)
        nrow = int(self.zdim/ncol)
        if nrow*ncol < self.zdim:
            nrow += 1
        self.xcolordim = COLORWIN_WIDTH
        self.ycolordim = nrow*self.img_ydim
        self.wxdim = ncol*self.img_xdim + self.xcolordim + (ncol-1)*self.borderwidth
        self.wydim = nrow*self.img_ydim + STATUS_HGHT + (nrow-1)*self.borderwidth

        wx.Frame.__init__(self, None, size=(self.wxdim, self.wydim), title=title)
#        self.SetBackgroundColour("darkslategray")
        self.zoom_factor = 1
        self.image_loaded = False
#       Setup status bar and event bar.
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(2)
        self.statusbar.SetStatusWidths([-2,-1])

#       Create the viewer window
        self.view_panel = ViewPanel(self, nrow, ncol, colorscale=colorscale, \
                            left_is_left=left_is_left, interp=interp1)

        self.CopyToClipboard = self.view_panel.CopyToClipboard
        self.copy_to_clipboard = True

    def ScreenDump(self, filename):
        self.view_panel.ScreenDump(filename)

    def OnPaint(self, evt):
        self.RefreshAll()

    def SetColorRange(self, min, max):
        self.colormin = min
        self.colormax = max
        self.colorbar.SetColorRange(min, max)

    def RefreshAll(self, palette=None, new_image=None, new_annotations=None):
        if new_annotations is not None:
            self.annotations = new_annotations
        self.colorbar.imgmin = self.colormin
        self.colorbar.imgmin = self.colormax
        for z in xrange(self.zdim):
#            print 'Refreshing pane %d' % z
            self.imgwin[z].annotations = self.annotations.get(z, {})
            self.imgwin[z].RefreshAll(image=new_image)

    def LoadFile(self, filename):
        if filename is not None:
            w = Wimage(filename)
            if w.hdr is None:
                raise RuntimeError('Could not read %s' % filename)
            self.hdr = w.hdr
            if self.hdr['tdim'] == 1 and self.hdr['mdim'] == 1:
                self.image = w.readfile()
            else:
                raise RuntimeError(\
                '%d-dimensional images are not supported.' % self.hdr['ndim'])
        else:
            self.image = None
#        self.imgwin.RefreshAll()

    def Annotate(self, annotations):
        """
        annotations is a dictionary containing entries xpos, ypos, and text
        where xpos and ypos are relative to the upper left corner of the 
        image pane and text is the text to be written. Entries are indexed
        by the z dimension of the displayed images.
        """
        self.annotations = annotations
       

class WblViewer(wx.App):
    """
    Dummy object required by wx to create the application widget.
    """
    def OnInit(self):
#       Call the widget that does the work.
        self.frame = WblImageDisplay()
        self.InitViewer = self.frame.Init
        self.SetColorRange = self.frame.SetColorRange
        self.Show = self.frame.Show
        self.ScreenDump = self.frame.ScreenDump
        self.Annotate = self.frame.Annotate
        self.RefreshAll = self.frame.RefreshAll
        self.CopyToClipboard = self.frame.CopyToClipboard
        return True

def wbl_image_display():
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = None
    dims = 256
    image = zeros([2, dims, dims], float)
    for i in xrange(dims):
        image[0,i,:] = i*arange(dims)
    for z in xrange(1,2):
        image[z,:,:] = image[0,:,:]
    app = WblViewer(redirect=False)
    app.InitViewer(image, title='test', colors='color42')
    app.SetColorRange(0., 1.)
    app.Show()
#    app.ScreenDump('test.png')
    app.MainLoop()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--version':
            sys.stdout.write('%s\n' % ID)
            sys.exit()
    else:
        wbl_image_display()
