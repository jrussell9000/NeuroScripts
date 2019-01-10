#!/usr/bin/env python

"""
Module: plotlib

Purpose: Add a layer above matplotlib to create plot objects.

By: John Ollinger

Date: July, 2008

"""

import os
import sys
import itertools
import numpy as np
from numpy import zeros, int, arange, sin, allclose, array, polyfit, ubyte, \
                  histogram, where, nonzero
from numpy.random import rand
import scipy.stats

try:
    from scipy.interpolate import interp1d
except:
#   Don't crash now, this module might not be used.
    pass

from wbl_util import except_msg
#try:
##   Use the antigrain backend if it is available. 
#    backend = 'MacOSX'  # works under osx
##    backend = 'pdf'   #  works  under osx
##    backend = 'Agg'   #  works  under osx
##    backend = 'GTK'   #  works  under osx
##    backend = 'GTKAgg'   #  works  under osx
##    backend = 'TkAgg'   #  works  under osx
##    backend = 'CocoaAgg'   #  works  under osx
##    backend = 'WX'   #  works  under osx
##    backend = 'WXAgg'   #  works  under osx
##    backend = 'QtAgg'   #  works  under osx
#    import matplotlib
#    matplotlib.use(backend)
#    orint 'Loaded %s backend' % backend
#except:
#    print except_msg()
#    print '***  Could not load %s backend *** ' % backend

def import_matplotlib(visible=True):
    """
    Work around the inconvenient fact that the backend must be selected before
    anything is imported. If a visible GUI such a MacOSX is seleted, the screen
    will flash even if the show() method isn't called. 

    This function should be called from the __init__ method in each class. If
    nothing will be displayed, set visible=False.
    """
    import matplotlib
    if visible:
        if 'darwin' in sys.platform:
            matplotlib.use('MacOSX')
        else:
            for backend in ['QtAgg', 'WX', 'GTKAgg', 'TkAgg', 'Agg', 'pdf']:
                try:
                    matplotlib.use(backend)
                    break
                except NameError:
                    print 'Could not find backend: %s' % backend
    else:
            matplotlib.use('Agg')

    global figure, errorbar, figtext, table, annotate, imshow, colormaps, \
                                                            colorbar, axes
    global cm, SubplotParams, ListedColormap, FontProperties, Bbox, Line2D
    global plot, xlabel, ylabel, show, subplot, title, axis, savefig, \
                      bar, xticks, setp, fill, legend, axvspan, suptitle, \
                      title, close

    from matplotlib.pyplot import figure, errorbar, figtext, table, annotate, \
                                imshow, colormaps, colorbar, axes
    from matplotlib import cm
    from matplotlib.figure import SubplotParams
    from matplotlib.colors import ListedColormap
    from matplotlib.font_manager import FontProperties
    from matplotlib.transforms import Bbox
    from matplotlib.lines import Line2D
    from pylab import plot, xlabel, ylabel, show, subplot, title, axis, savefig, \
                      bar, xticks, setp, fill, legend, axvspan, suptitle, \
                      title, close

COLOR42 = [(0.1875, 0.0000, 0.1875), (0.2891, 0.0000, 0.2578), (0.3945, 0.0000, 0.3281), (0.3984, 0.0000, 0.3320), (0.1992, 0.1992, 0.3320), (0.1992, 0.1992, 0.3906), (0.1992, 0.1992, 0.4570), (0.1992, 0.1992, 0.4648), (0.3320, 0.3320, 0.5273), (0.3984, 0.3984, 0.7266), (0.4648, 0.4648, 0.7930), (0.5273, 0.5273, 0.9258), (0.1992, 0.3984, 0.1992), (0.1992, 0.5938, 0.1992), (0.3320, 0.7930, 0.3320), (0.2656, 0.9258, 0.2656), (0.7930, 0.9922, 0.1328), (0.9258, 0.9258, 0.3984), (0.8594, 0.8594, 0.3320), (0.8594, 0.7266, 0.2656), (0.8594, 0.5273, 0.1328), (0.7930, 0.3984, 0.0664), (0.7266, 0.2656, 0.0000), (0.9922, 0.0000, 0.0000)]

markers = {'square': 's', \
           'circle': 'o', \
           'triangle_up': '^', \
           'triangle_right': '>', \
           'triangle_down': 'v', \
           'triangle_left': '<', \
           'diamond': 'd', \
           'pentagram': 'p', \
           'star': '*', \
           'hexagon': 'H', \
           'plus': '+', \
           'cross': 'x', \
           'none': ' '}

marker_names = [ \
           'square', \
           'circle', \
           'triangle_up', \
           'triangle_right', \
           'triangle_down', \
           'triangle_left', \
           'diamond', \
           'pentagram', \
           'star', \
           'hexagon', \
           'plus', \
           'cross', \
           'none']

colors = { \
           'blue':'b', \
           'green':'g', \
           'red':'r', \
           'cyan':'c', \
           'magenta':'m', \
           'yellow':'y', \
           'black':'k', \
           'white':'w', \
           'DarkCoolBrown': '#534741', \
           'DarkMagentaRed': '#9e0039', \
           'DarkWarmBrown': '#603913', \
           'DarkerGreen': '#005826', \
           'DarkerYellowOrange': '#7d4900', \
           'PureMagentaRed': '#ee145b', \
           'PureRedOrange': '#f26522', \
           'PureViolet': '#662d91', \
           'PureVioletMagenta': '#92278f', \
            }

color_keys = [ \
           'black', \
           'red', \
           'cyan', \
           'magenta', \
           'blue', \
           'green', \
           'yellow', \
           'white', \
           'DarkCoolBrown', \
           'DarkMagentaRed', \
           'DarkWarmBrown', \
           'DarkerGreen', \
           'DarkerYellowOrange', \
           'PureMagentaRed', \
           'PureRedOrange', \
           'PureViolet', \
           'PureVioletMagenta' \
            ]

color_list = map(lambda x: colors[x], color_keys)

legend_locations = { \
            'best':0, \
            'upper_right':1, \
            'upper_left':2, \
            'lower_left':3, \
            'lower_right':4, \
            'right':5, \
            'center_left':6, \
            'center_right':7, \
            'lower_center':8, \
            'upper_center':9, \
            'center':10}


class SimpleBarChart():

    """
    Create a simple vertical bar chart.
    
    Arguments:
        categories: A list of strings to be used as category labels.
        values: A list or numpy array of counts, one value per category.
        Nmax: Maximum number of categories.
    """
    def __init__(self, categories, values, Nmax=500, xaxis_label=None, \
                 yaxis_label=None, suptitle=None, visible=True):
#        Nmax = 15
        import_matplotlib(visible)
        if len(categories) < Nmax:
            N = len(categories)
        else:
            N = Nmax

        ind = arange(N)
        width = .8
        p1 = bar(ind, values[:N], width, color='y', bottom=.5 )
        if xlabel:
            xlabel(xaxis_label)
        if ylabel:
            ylabel(yaxis_label)
        if title:
            title(title_in)
        locs, labels = xticks(ind + width, categories[:N])
        setp(labels, 'rotation', 'vertical')
        show()

class PlotState():
    def __init__(self):
        self.min_yval =  1.e20
        self.max_yval = -1.e20
        self.min_xval =  1.e20
        self.max_xval = -1.e20
        self.nplotted = 0
        self.lgnd = None
        self.subplot = []
        self.plots = []
        self.legstrs = []
#        self.data = {}


class ScatterPlot():

    def __init__(self, nrow, ncol, \
                       suptitle=None, \
                       fill_color='0.80', \
                       fill_alpha=.9, \
                       width=8, \
                       height=10, \
                       colors='krbgmcy', \
                       footnote=None, \
                       visible=True):
        """
        nrow and ncol are the numbers of rows and columns of subplots.
        colors is a tuple containing  colors drawn from 'krbgmcy'
        footnote is a list of strings (length one or two) that will be 
        printed at the bottom of the figure.  A table can be made by 
        adding end-of-lines appropriately.
        """
        import_matplotlib(visible)
        self.nrow = nrow
        self.ncol = ncol
        self.nplot = self.nrow*self.ncol
        self.fill_color = fill_color
        self.fill_alpha = fill_alpha
        self.suptitle = suptitle
        self.row = 1
        self.col = 1
        self.lgnd = None
#       Cycle through all colors
        self.colors = itertools.cycle(colors)
        self.markers = itertools.cycle('sod*+^xvHp><')
        self.s = []
        self.ns = 0
        self.plotno = 0
        self.data = []
        self.footnote = footnote
        self.bottom = .1

#       Create new figure
        self.fg = figure(figsize=(width, height), facecolor='w')
        self.Footnote()

    def Footnote(self):
        footnote = self.footnote
        if footnote is not None:
            ncol = len(footnote)
            nline = max(len(footnote[0].split('\n'))  + 1, \
                       len(footnote[-1].split('\n')) + 1)
            self.bottom = .25+nline*.009 - (self.nrow-1)*.06
            self.fg.subplotpars.update(bottom=self.bottom)
            if ncol == 1:
                figtext(.02, .02, footnote[0], figure=self.fg, color='k')
            elif ncol == 2:
                figtext(.02, .02, footnote[0], figure=self.fg, color='k')
                figtext(.5, .02, footnote[1], figure=self.fg, color='k')

    def Close(self):
        close(self.fg)

    def AddPlot(self, x_coords, y_coords, \
                x_label=None, \
                y_label=None, \
                xmin = None, \
                xmax = None, \
                ymin = None, \
                ymax = None, \
                overplot=False, \
                markerin='auto', \
                markersize=4, \
                color=None, \
                linewidth=2, \
                markeronly=False, \
                marker_edgecolor=None, \
                marker_facecolor=None, \
                lineonly=False, \
                xgrid_lines=False, \
                ygrid_lines=False, \
                subtitle=None, \
                nsubplot=None, \
                column_gap=.2, \
                row_gap=.2, \
                left_margin=.125, \
                right_margin=.9, \
                top_margin=.9, \
                bottom_margin=.1, \
                legstr=None, \
                ):   
        """
        column_gap, left, right, bottom, hspace are a fraction of total width.
        """

#       Save data for all lines plotted.
        if legstr is None:
            ylab = y_label
        else:
            ylab = legstr
        self.data.append(('pts', x_label, ylab, x_coords, y_coords))

        if markerin == 'auto':
            marker = self.markers.next()
        else:
            marker = markers[markerin]

#       Get the color
        if color is None:
            self.color = self.colors.next()
        elif colors.has_key(color):
            self.color = colors[color]
        else:
            print 'Available colors: ', colors.keys()
            raise RuntimeError('Unknown color.')

        if marker_edgecolor is None:
            if marker_facecolor is None:
                _marker_edgecolor = self.color
            else:
                _marker_edgecolor = marker_facecolor
        else:
            _marker_edgecolor = marker_edgecolor

        if marker_facecolor is None:
            _marker_facecolor = self.color
        else:
            _marker_facecolor = marker_facecolor
        

#       Set the line width. Erase the line by making it zero width.
        if markeronly:
            linewidth = False

        if lineonly:
            marker=markers['none']
        
#       Designate plot position and plot.
        if not overplot or self.ns == 0:
            sp = subplot(self.nrow, self.ncol, self.ns+1)
            self.s.append(PlotState())
            self.s[self.ns].subplot = sp
            self.ns += 1

#        self.fg.subplotpars.wspace = column_gap
#        self.fg.subplotpars.hspace = row_gap
#        self.fg.subplotpars.top = top_margin
#        self.fg.subplotpars.bottom = bottom_margin
#        self.fg.subplotpars.left = left_margin
#        self.fg.subplotpars.right = right_margin
        self.fg.subplotpars.update(left_margin, self.bottom, \
                                   right_margin, top_margin, \
                                   column_gap, row_gap)

#       Get index to current subplot.
        if nsubplot is None:
            ns = self.ns-1
        else:
            ns = nsubplot

#       Write grid lines
        self.SetGridLines(self.s[ns].subplot, xgrid_lines, ygrid_lines)

        self.plotno += 1
        if legstr is None:
            legstr = 'plot_%d' % self.plotno
        p = plot(x_coords, y_coords,  \
             marker=marker, \
             c=self.color, \
             markeredgecolor=_marker_edgecolor, \
             markerfacecolor=_marker_facecolor, \
             markersize=markersize, \
             label=legstr, \
             linewidth=linewidth)
        self.s[ns].plots.append(p[0])
        self.s[ns].legstrs.append(legstr)

#       Save the plot.
#        self.s[ns].plots[legstr] = p

#       Add title above all plots.
        if self.suptitle is not None:
            suptitle(self.suptitle, fontsize=14)

#       Add title to this subplot
        if subtitle is not None:
            title(subtitle)

#       Add axis labels.
        if x_label is not None:
            xlabel(x_label, fontsize='large')
        if y_label is not None:
            ylabel(y_label, fontsize='large')

#       Compute axis limits.
        max_xval = x_coords.max()
        max_yval = y_coords.max()
        min_xval = x_coords.min()
        min_yval = y_coords.min()
        if max_yval > 0:
            max_yval *= 1.1
        else:
            max_yval = 0.
        if min_yval < 0:
            min_yval *= 1.1
        else:
            min_yval = 0.
        if ymin is None:
            self.s[ns].min_yval = min(min_yval, self.s[ns].min_yval)
        else:
            self.s[ns].min_yval = ymin
        if ymax is None:
            self.s[ns].max_yval = max(max_yval, self.s[ns].max_yval)
        else:
            self.s[ns].max_yval = ymax

        if xmin is None:
            self.s[ns].min_xval = min(min_xval, self.s[ns].min_xval)
        else:
            self.s[ns].min_xval = xmin
        if xmax is None:
            self.s[ns].max_xval = max(max_xval, self.s[ns].max_xval)
        else:
            self.s[ns].max_xval = xmax

#       Draw a line at y=0.
        delta = (self.s[ns].max_yval - self.s[ns].min_yval)/500.
        line = fill([self.s[ns].min_xval, self.s[ns].max_xval, \
                     self.s[ns].max_xval, self.s[ns].min_xval], \
                    [-delta, -delta, delta, delta], facecolor=colors['black'])

#       Set the upper and lower limits of the axes.
        self.axis = axis([self.s[ns].min_xval, self.s[ns].max_xval, \
              self.s[ns].min_yval, self.s[ns].max_yval], fontsize='large')

#  #     Save the data.
   #     self.s[ns].data[self.s[ns].nplotted] = {\
   #                                 'xlabel':x_label, \
   #                                 'x_coords': x_coords,
   #                                 'ylabel':y_label, \
   #                                 'y_coords': y_coords}
        self.s[ns].nplotted += 1
        if not overplot:
            ns = len(self.s)
            self.row = (ns % self.nrow) + 1
            self.col = ns/self.nrow + 1

    def SetGridLines(self, sp, xgrid, ygrid):
        if xgrid or ygrid:
            sp.grid(True)
        if xgrid:
            ticklines = sp.get_xticklines()
            if ygrid:
                ticklines.extend( sp.get_yticklines() )
            gridlines = sp.get_xgridlines()
            ticklabels = sp.get_xticklabels()
            if ygrid:
                ticklabels.extend(sp.get_xticklabels())
        elif ygrid:
            ticklines = sp.get_yticklines()
            gridlines = sp.get_ygridlines()
            ticklabels = sp.get_yticklabels()
        else:
            return

        for line in ticklines:
            line.set_linewidth(3)

        for line in gridlines:
            line.set_linestyle('-')

        for label in ticklabels:
            label.set_color('k')
            label.set_fontsize('medium')

    def ErrorBars(self, x, y, \
                  xerr=None, \
                  yerr=None, \
                  fmt='-', \
                  capsize=3, \
                  linewidth=1, \
                  barsabove=True, \
                  lolims=False, \
                  uplims=False, \
                  xlolims=False, \
                  xuplims=False, \
                  ):
        """
        x and y are the plotted data points.
        xerr and yerr are either scalars, Nx1 or 2xN vectors.
        """

        self.data.append(('err', x, y, xerr, yerr))
        errorbar(x, y, yerr=yerr, xerr=xerr, fmt=fmt, ecolor=self.color, \
             elinewidth=linewidth, capsize=capsize, barsabove=barsabove, \
             lolims=lolims, uplims=uplims, xlolims=xlolims, xuplims=xuplims, \
             linewidth=0)
        axis(self.axis, fontsize='large')

    def SortPlotData(self):
        """
        Sort data into a single dictionary.  Each entry contains all of the
        data for a single line.
        """
        if len(self.data) == 0:
            return None, 0
        plotdata = {}
        np = 0
        errorbars = []
        npt_max = 0
        for line in self.data:
            if line[0] == 'pts':
                plotdata[np] = {'xlabel': line[1], \
                                'ylabel':line[2], \
                                'x':line[3], \
                                'y':line[4], \
                                'xerrs':None, \
                                'yerrs':None}
                if len(plotdata[np]['y']) > npt_max:
                    npt_max = len(plotdata[np]['y'])
                np += 1
            else: # error bar data. Must be processed last, so save for now.
                errorbars.append(line)
        plotdata['npts'] = npt_max

#       Now attach the errorbars.
        for ebar in errorbars:
            xerr = ebar[1]
            yerr = ebar[2]
            for ip in xrange(np):
                if allclose(xerr, plotdata[ip]['x']) and \
                                   allclose(yerr, plotdata[ip]['y']):
                    plotdata[ip]['xerrs'] = ebar[3]
                    plotdata[ip]['yerrs'] = ebar[4]

#       Check to see if all data are plotted against the same x coordinate.
        x0 =  plotdata[0]['x']
        for ip in xrange(1,np):
            if not allclose(plotdata[ip]['x'], x0):
                plotdata['samex'] = False
                break
        else:
            plotdata['samex'] = True
        return plotdata, np

    def WriteData(self, filename):
        plotdata, np = self.SortPlotData()
        if np == 0:
            return
        f = open(filename, 'w')

        f.write('%s' % plotdata[0]['xlabel'])
        if plotdata[0]['xerrs'] is not None:
            f.write('\t%s_xerr' % (plotdata[0]['xlabel']))
        f.write('\t%s' % plotdata[0]['ylabel'])
        if plotdata[0]['yerrs'] is not None:
            f.write('\t%s_yerr' % (plotdata[0]['ylabel']))
        for ip in xrange(1,np):
            if not plotdata['samex']:
                f.write('\t%s' % plotdata[ip]['xlabel'])
                if plotdata[0]['xerrs'] is not None:
                    f.write('\t%s_xerr' % (plotdata[0]['xlabel']))
            f.write('\t%s' % plotdata[ip]['ylabel'])
            if plotdata[0]['yerrs'] is not None:
                f.write('\t%s_yerr' % (plotdata[0]['ylabel']))
        f.write('\n')
        for ix in xrange(plotdata['npts']):
            f.write('%g' % plotdata[0]['x'][ix])
            if plotdata[0]['xerrs'] is not None:
                f.write('\t%g' % (plotdata[0]['xerrs'][ix]))
            f.write('\t%g' % plotdata[0]['y'][ix])
            if plotdata[0]['yerrs'] is not None:
                f.write('\t%g' % (plotdata[0]['yerrs'][ix]))
            for ip in xrange(1,np):
                if not plotdata['samex']:
                    f.write('\t%g' % plotdata[ip]['x'][ix])
                    if plotdata[ip]['xerrs'] is not None:
                        f.write('\t%g' % (plotdata[ip]['xerrs'][ix]))
                f.write('\t%g' % plotdata[ip]['y'][ix])
                if plotdata[0]['yerrs'] is not None:
                    f.write('\t%g' % (plotdata[ip]['yerrs'][ix]))
            f.write('\n')
        print 'Data written to %s' % filename
        f.close()
   
    def AddFill(self, nsubplot=None):
#       Get index to current subplot.
        if nsubplot is None:
            ns = self.ns-1
        else:
            ns = nsubplot
        xmin, xmax, ymin, ymax = axis()
        axvspan(xmin, xmax, facecolor=self.fill_color, alpha=self.fill_alpha)

    def AddLegend(self, loc='best', subplot='all', \
                  fontsize='medium', ncol=1, fill=False):
        """
        sublplot takes on values of 'all', 'first', or 'last'. It controls 
        whether legends are created for the first, last, or all subplots.
        """
#       Get index to current subplot.

        if subplot == 'first':
            ns = [0]
        elif subplot == 'last':
            ns = [self.ns-1]
        else:
            ns = range(self.ns)
        for n in ns:
            self.s[n].lgnd = legend(self.s[n].plots, self.s[n].legstrs, \
                          loc=legend_locations[loc], \
                          ncol=ncol, \
                          prop=FontProperties(size=fontsize), \
                          )
            frame = self.s[n].lgnd.get_frame()
#            frame.set_facecolor(self.fill_color)

            frame = self.s[n].lgnd.get_frame()
            if fill:
                frame.set_facecolor(self.fill_color)
                frame.set_alpha(self.fill_alpha)

    def AddTable(self, row_labels, data, loc='bottom'):

        col_labels = ('Parameter', 'Values')
        text = ''
        for row in xrange(len(row_labels)):
            text += '%s: %s\n' % (row_labels[row], data[row])
        text = text[:-1]
        figtext(.60, .01, text, figure=self.fg, alpha=.8, color='g')
        self.fg.subplotpars.update(bottom=.5)

    def WritePlot(self, filename, filetype='png'):
        """
        filetype takes on values of png, eps, svg, ps, and pdf
        """
        fname = filename.replace('.png','')
        fname = fname.replace('.eps','')
        fname = fname.replace('.svg','')
        fname = fname.replace('.pdf','')
        savefig('%s.%s' % (fname, filetype))

    def Show(self):
        show()
        
builtin_cmaps = ('hot', 'gray', 'spectral', 'hsv', 'flag')
class PlotImage():

    def __init__(self, interp='bilinear', colormap='gray', alpha=1., \
                 width=4, height=4, facecolor='w', column_gap=.2, \
                row_gap=.2, left_margin=.125, right_margin=.95, \
                top_margin=.95, bottom_margin=.1, visible=True):
        """
        Set visible = True if images are to be displayed to the screen. Otherwise
        set it False. (If set incorrectly, the screen will flash during batch
        processing.
        """
        import_matplotlib(visible=visible)
#       Interpolation choices: e.g., bilinear, nearest, bicubic
#       colormaps: hot, gray, spectral
        self.alpha = alpha
        self.width = width
        self.height = height

        self.left_margin = left_margin
        self.bottom_margin = bottom_margin
        self.right_margin = right_margin
        self.top_margin = top_margin
        self.column_gap = column_gap
        self.row_gap = row_gap

#       Creat figure to contain everything.
        self.fig = figure(figsize=(width, height), facecolor=facecolor)
        self.fig.subplotpars.update(self.left_margin,  self.bottom_margin, \
                                    self.right_margin, self.top_margin, \
                                    self.column_gap,   self.row_gap)
        self.interp = interp
        if colormap in builtin_cmaps:
            self.colormap = colormap
        elif colormap == 'color42':
            from color42 import colors42
            self.colormap = self.MakeColorMap(colors42, 'color42')


    def Draw(self, image, subtitle=None, gridlines=None, linewidth=1):
        self.ydim, self.xdim = image.shape
        self.data = image
        self.ax = self.fig.add_subplot(111)
        self.ax.update_params()
        self.img = self.ax.imshow(image, interpolation=self.interp, \
                            cmap=self.colormap, aspect='equal', \
                            origin='lower', figure=self.fig) 
        for gline in gridlines:
            line2d = Line2D(gline[0], gline[1], linewidth=linewidth, color='g')
            self.ax.add_line(line2d)
#       Add title to this subplot
        if subtitle is not None:
            title(subtitle)

    def GetSlice(self, image, axis, frm, slice_in, xyzsize=None):
        if xyzsize is None:
            xyzsize = (1., 1., 1.)

        if float(slice_in) !=  float(int(slice_in)):
#           Slice specified as a fraction of the maximum.
            slc = int(slice_in*(image.shape[axis[0]+1] - 1))
            
        if axis[1]:
#           Flip the slice axis.
            nslice = image.shape[axis[0]+1]
            slc = nslice - slc - 1

        if axis[0] == 0:
            img = image[frm, slc, :, :]
            xysize = (xyzsize[1], xyzsize[0])
        elif axis[0] == 1:
            img = image[frm, :, slc, :]
            xysize = (xyzsize[2], xyzsize[0])
        elif axis[0] == 2:
            img = image[frm, :, :, slc]
            xysize = (xyzsize[2], xyzsize[1])
        else:
            raise RuntimeError('Invalid axis: %d' % axis)

        if axis[4]:
#           Transpose.
            img = img.T

        img = self.ResampleAxis(img, xysize)

        if axis[2]:
#           Flip left to right
            img = np.fliplr(img)
        if axis[3]:
#           Flip top to bottome
            img = np.flipud(img)
        return img

    def ResampleAxis(self, img, xysize):
        """
        Resample one axis to create square voxels.
        """
        ydim, xdim = img.shape
        if xysize[0] < xysize[1]:
#           Resample the y axis.
            new_ydim = int(ydim*xysize[1]/xysize[0] + .4999)
            new_img = zeros((new_ydim, xdim), float)
            new_yvals = (float(ydim) - 1.)*arange(new_ydim)/float(new_ydim)
            for x in xrange(xdim):
                finterp = interp1d(range(ydim), img[:, x])
                new_img[:, x] = finterp(new_yvals)
        elif xysize[0] > xysize[1]:
#           Resample the x axis.
            new_xdim = int(xdim*xysize[0]/xysize[1] + .4999)
            new_img = zeros((ydim, new_xdim), float)
            new_xvals = (float(xdim) - 1.)*arange(new_xdim)/float(new_xdim)
            for y in xrange(ydim):
                finterp = interp1d(range(xdim), img[y, :])
                new_img[y, :] = finterp(new_xvals)
        else:
            new_img = img
        return new_img


    def DrawReslice(self, nrow, ncol, image, image_plane, slice_plane, \
                    xyzsize=None, scaling='local', xlabels=None, ylabels=None, \
                    x_label=None, y_label=None, fig_title=None, middle96=None):
        """
        image is a 3D volume.

        slice_plane is a list of tuples (plane, slice, [frame]) were slice is the 
        slice number starting at zero and plane is 'axial', 'sagittal', or 
        'coronal'. If "slice" is less than one, it is multiplied by the number of
        slices. For example, to display a midsagittal slice, use 
        slice_plane = ("sagittal", .5).  Frame is optional and is the frame 
        number starting at zero.

        image_plane is the plane of the input image.

        xyzsize is a tuple of voxel sizes (xsize, ysize, zsize)

        scaling takes on values of "local" and "global" and "column"

        """
#       Encode actions: (slice_axis, flip_slice, fliplr, flipud, transpose)
        axes_defs = {\
        'RAI':{'axial':(0,0,1,1,0), 'sagittal':(2,1,0,0,0), 'coronal':(1,0,1,0,0)}, \
        'ASL':{'axial':(1,1,0,1,1), 'sagittal':(0,0,0,1,0), 'coronal':(2,0,0,1,1)}, \
        'RSA':{'axial':(1,1,1,1,0), 'sagittal':(2,1,0,1,1), 'coronal':(0,0,1,1,0)}, \
        'RAS':{'axial':(0,1,1,1,0), 'sagittal':(2,0,0,0,0), 'coronal':(1,0,0,0,0)}, \
        'ASR':{'axial':(1,0,0,1,1), 'sagittal':(0,1,0,1,0), 'coronal':(2,1,0,1,1)}, \
        'RSP':{'axial':(1,0,1,1,0), 'sagittal':(2,0,0,1,1), 'coronal':(0,1,1,1,0)}}

        if image.ndim == 3:
            zdim, ydim, xdim = image.shape
            tdim = 1
        elif image.ndim == 4:
            tdim, zdim, ydim, xdim = image.shape
        shp = (tdim, zdim, ydim, xdim)

        images = []
        for entry in slice_plane:
#           Loop through each 2D image
            plane, slc  = entry[:2]
            if len(entry) == 3:
                frm = entry[2]
            else:
                frm = 0
            axis_def = axes_defs[image_plane][plane]
            img = self.GetSlice(image.reshape(shp), axis_def, frm, slc, xyzsize)
            images.append(img)
        images = self.PadImages(images)
        self.DrawMany(images, nrow, ncol, xlabels, ylabels, x_label, y_label, \
                     scaling=scaling, fig_title=fig_title, middle96=middle96)

    def PadImages(self, images):
        xdim_max = 0; ydim_max = 0;
        for img in images:
            ydim, xdim = img.shape
            xdim_max = max(xdim_max, xdim)
            ydim_max = max(ydim_max, ydim)

        imgout = []
        for img in images:
            ydim, xdim = img.shape
            xpad = (xdim_max - xdim)/2
            ypad = (ydim_max - ydim)/2
            jmg = zeros((ydim_max, xdim_max), img.dtype)
            jmg[ypad:ypad+ydim, xpad:xpad+xdim] = img
            imgout.append(jmg)
        return imgout

    def Middle96(self, image):
        """
        middle96: Clip image values at the 2% and 98% levels.
        """
        image_flat = image.ravel()
        nonzero_vals = image_flat[np.nonzero(image_flat)]
        minval = scipy.stats.scoreatpercentile(nonzero_vals, 2)
        maxval = scipy.stats.scoreatpercentile(nonzero_vals, 98)
        out = image
        out = where(image < minval, minval, out)
        out = where(image > maxval, maxval, out)
        return out, minval, maxval

    def ScaleImage(self, image, scaling, ncol, nrow, middle96=False):
        """
        Scale output image either locally (each pane to its own maximum), 
        globally (to a single global max and min) or by by column (each 
        column of panes has its own max and min

        middle96: Clip image values at the 2% and 98% levels.
        """

        imgout = zeros(image.shape, ubyte)
        ydim, xdim = image.shape
        ydim_pane = ydim/nrow
        xdim_pane = xdim/ncol
        
        self.offsets = []
        self.scale_factors = []
        if scaling == 'global':
            if middle96:
                img, minval, maxval = self.Middle96(image)
            else:
                img = image
            offset = img.min()
            scl = 255./(maxval - offset)
            imgout = scl*(img - img.min())
            self.offsets.append(offset)
            self.scale_factors.append(scl)
        elif scaling == 'local':
            for i in xrange(ncol):
                for j in xrange(nrow):
                    i0 = i*xdim_pane
                    j0 = j*ydim_pane
                    img = image[j0:j0+ydim_pane, i0:i0+xdim_pane]
                    if middle96:
                        img, minval, maxval = self.Middle96(img)
                    offset = img.min()
                    scl = 255./(img.max() - offset)
                    imgout[j0:j0+ydim_pane, i0:i0+xdim_pane] = scl*(img - offset)
                    self.offsets.append(offset)
                    self.scale_factors.append(scl)
        elif scaling == 'column':
            for i in xrange(ncol):
                i0 = i*xdim_pane
                img = image[:, i0:i0+xdim_pane]
                if middle96:
                    img, minval, maxval = self.Middle96(img)
                offset = img.min()
                scl = 255./(img.max() - offset)
                imgout[:, i0:i0+xdim_pane] = scl*(img - offset)
                self.offsets.append(offset)
                self.scale_factors.append(scl)
        else:
            raise RuntimeError('Invalid value for scaling: %s' % scaling)
        return imgout

    def DrawMany(self, images, nrow, ncol, xlabels=None, ylabels=None, \
                x_label=None, y_label=None, scaling='local', fig_title=None, \
                middle96 = None):
        """
        scaling takes on values of "local" and "global" and "column"
        """
#       Compute the numbers of rows and columns.
        ydim_pane, xdim_pane = images[0].shape
        nimg = len(images)
        if nimg <= ncol:
            ncol = nimg
            nrow = 1
        else:
            xrow = float(nimg)/float(ncol)
            nrow = int(nimg)/int(ncol)
            if xrow > float(nrow):
                nrow += 1

#       Paint the images into individual panes of final image.
        lw = 1
        xdim = (xdim_pane+lw)*ncol + lw
        ydim = (ydim_pane+lw)*nrow + lw
        i0 = lw
        j0 = (ydim_pane + lw)*(nrow-1) + lw
        image = zeros((ydim, xdim), float)
        lines = []
        for img in images:
            image[j0:j0+ydim_pane, i0:i0+xdim_pane] = img
            if i0 >= (xdim_pane + lw)*(ncol-1):
                i0 = lw
                j0 -= (ydim_pane + lw)
            else:
                i0 += (xdim_pane + lw)

#       Scale the images into unsigned bytes.
        image = self.ScaleImage(image, scaling, ncol, nrow, middle96=middle96)

#       Draw the grid lines.
        i0 = 0
        for i in xrange(nrow+1):
#           Vertical lines
            lines.append((((i0, i0), (0, ydim))))
            i0 += (xdim_pane + lw)
        j0 = 0
        for j in xrange(ncol+1):
#           Horizontal lines
            lines.append(((0, ydim), (j0, j0)))
            j0 += (ydim_pane + lw)
        self.Draw(image, gridlines=lines, linewidth=2)

#       Now label the axes.
        if xlabels is not None:
            nlabs = len(xlabels)
            delta = image.shape[1]/nlabs
            tickpos = delta*arange(nlabs) + delta/2
            self.ax.set_xticks(tickpos)
            xlabs = self.ax.set_xticklabels(xlabels, size='x-large')
        else:
            self.ax.set_yticks([0])
            ylabs = self.ax.set_yticklabels([''])

        if ylabels is not None:
            nlabs = len(ylabels)
            delta = float(image.shape[0])/(nlabs+1.)
            tickpos = delta*arange(nlabs) + delta/2.
            tickpos = tickpos.tolist()
            tickpos.reverse()
            tickpos = array(tickpos)
            self.ax.set_yticks(tickpos)
            ylabs = self.ax.set_yticklabels(ylabels, \
                    size='x-large', rotation='vertical')
        else:
            self.ax.set_yticks([0])
            ylabs = self.ax.set_yticklabels([''])

        if fig_title is not None:
            suptitle(fig_title, y=.9, fontsize=14)
        if x_label is not None:
            self.ax.set_xlabel(x_label, size='x-large')
        if y_label is not None:
            self.ax.set_ylabel(y_label, size='x-large')
            
             
    def Footnote(self, footnotes):
        """
        Create a footnote at the bottom of the figure.
        text is a list of text strings.
        """
        xbl = .05 # bottom left in inches
        ybl = .05  # bottom left in inches
        lsp = .20 # Line spacing in inches.
        x = xbl/self.width
        y = (ybl + len(footnotes)*lsp)/self.height
        delta = lsp/self.height
        for footnote in footnotes:
            self.fig.text(x, y, footnote, size='large')
            y -= delta

    def LabelXAxis(self, labels, title=None, center=True, rotation='horz'):
        nlab = len(labels)
        self.ax.set_xticks(arange(nlab) + self.width/nlab)
        xlabs = self.ax.set_xticklabels(labels)
        if rotation == 'vertical':
            for xlab in xlabs:
                xlab.set_rotation('vertical')
        if title is not None:
            self.ax.set_xlabel(title)

    def LabelYAxis(self, labels, title=None, center=True, rotation='horz'):
        nlab = len(labels)
        self.ax.set_yticks(arange(nlab) + self.width/nlab)
        ylabs = self.ax.set_yticklabels(labels)
        if rotation == 'vertical':
            for ylab in ylabs:
                ylab.set_rotation('vertical')
        if title is not None:
            self.ax.set_ylabel(title)

    def SetXGrid(self):
        for x in xrange(1,self.xdim):
            self.ax.axvline(x-.5, linestyle='--', color='k')

    def SetYGrid(self):
        for y in xrange(1,self.ydim):
            self.ax.axhline(y-.5, linestyle='--', color='k')

    def ColorBar(self, shrink=.75, minval=0, maxval=255, tickvals=None, \
                                                tick_fmt='%1.2g', label=None):
        """
        minvalue is the minimum value in the image.
        maxvalue is the maximum value in the image.
        tickvals are the values of ticks in the same units as the image.
        """
#        tickvals[-1] = 90
        scl = 255./(maxval - minval)
        abs_tick_locs = map(lambda x: scl*(x-minval), tickvals)
        self.cbar = colorbar(self.img, ax=self.ax, shrink=shrink, \
                             ticks=abs_tick_locs)
        if tickvals is not None:
            tick_labels = map(lambda x: tick_fmt % x, tickvals)
            self.cbar.ax.set_yticklabels(tick_labels)

#       Add the label.
        if label is not None:
            self.cbar.set_label(label, size='x-large')

    def MakeColorMap(self, colors, name):
        return ListedColormap(colors, name, colors.shape[0])

    def WriteImage(self, filename, filetype='png'):
        """
        filetype takes on values of png, eps, svg, ps, and pdf
        """
        fname = filename.replace('.png','')
        fname = fname.replace('.eps','')
        fname = fname.replace('.svg','')
        fname = fname.replace('.pdf','')
        savefig('%s.%s' % (fname, filetype))

    def Show(self):
        show()

class PlotCovariance(PlotImage):
    
    def __init__(self, image, labels=None, Title=None, grid=False, \
                 width=4, height=4, colormap='color42', visible=True):
        PlotImage.__init__(self, interp='nearest', \
                 colormap=colormap, left_margin=.25, right_margin=.95, \
                 width=width, height=height, visible=visible)
        self.Draw(image, subtitle=Title)
        self.ColorBar(shrink=.65)
        if labels is not None:
            self.LabelXAxis(labels, rotation='vertical')
            self.LabelYAxis(labels, rotation='horizontal')
        if grid:
            self.SetXGrid()
            self.SetYGrid()

    def Show(self):
        show()

class PlotCorrelation(ScatterPlot):

    def __init__(self, xdata, ydata, nsample=None, height=4, width=6, \
                 xlabel='x-data', ylabel='y-data',title=None, xmin=None, \
                 xmax=None, visible=True):
        import_matplotlib(visible)
        from scipy.stats import pearsonr, bayes_mvs
        self.xdata, self.ydata = xdata, ydata
        self.nsample = nsample
        self.height = height
        self.width = width
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title
        if xmin is None:
            self.xmin = self.xdata.min()
        else:
            self.xmin = xmin
        if xmax is None:
            self.xmax = self.xdata.max()
        else:
            self.xmax = xmax
        ymin = self.ydata.min()
        ymax = self.ydata.max()
        self.xymin = min(self.xmin, ymin)
        self.xymax = max(self.xmax, ymax)

        if self.nsample is None:
            self.xdata_plot, self.ydata_plot = xdata, ydata
        else:
            self.xdata_plot, self.ydata_plot = self.SampleData(xdata, ydata)

#       Compute regression line.
        rleg = self.RegressionLine()

#       Compute statistics.
        pleg = self.Stats()

        ScatterPlot.__init__(self, 1, 1,  width=self.width, \
                            height=self.height, suptitle=self.title)
        self.Plot((rleg, pleg))

    def SampleData(self, xdata, ydata):
        nvox = xdata.shape[0]
        samp = (nvox*rand(self.nsample)).astype(int)
        xd = xdata.take(samp)
        yd = ydata.take(samp)
        return xd, yd

    def Stats(self):
        self.rval, self.pval = pearsonr(self.xdata, self.ydata)
        stat_label = 'r: %1.3f, p<%1.4g, n=%d' % \
                                    (self.rval, self.pval, self.xdata.shape[0])

        return stat_label

    def Plot(self, legend):
        self.AddPlot(self.xdata_plot, self.ydata_plot,  \
                x_label=self.xlabel, \
                y_label=self.ylabel, \
                xmin=self.xmin, \
                xmax=self.xmax, \
                ymin=self.xymin, \
                ymax=self.xymax, \
                markerin='circle', \
                color='PureViolet', \
                overplot=False, \
                markersize=3, \
                xgrid_lines = False, \
                ygrid_lines = False, \
                lineonly=False,  \
                markeronly=True, \
                marker_edgecolor=None, \
                legstr=legend[0])
        self.AddPlot(self.xreg, self.yreg,  \
                x_label=self.xlabel, \
                y_label=self.ylabel, \
                xmin=self.xmin, \
                xmax=self.xmax, \
                ymin=self.xymin, \
                ymax=self.xymax, \
                color='black', \
                overplot=True, \
                markersize=4, \
                xgrid_lines = False, \
                ygrid_lines = False, \
                lineonly=True,  \
                legstr = legend[1], \
                markeronly=False)
        self.AddLegend(fontsize='medium', subplot='all')

    def RegressionLine(self, N=2):
        m,b = polyfit(self.xdata, self.ydata, 1)
        xmin = self.xdata.min()
        xmax = self.xdata.max()
        self.xreg = xmin + (xmax - xmin)*arange(N)
        self.yreg = m*self.xreg + b

        fit_label = 'y = %1.4fx + %1.4f' % (m, b)

        residuals = self.ydata - m*self.xdata - b
        cmean, csd, cvar = bayes_mvs(residuals, alpha=.99)
        dmedian, (dsd_lower, dsd_upper) = cmean
        self.conf_xvals = array((xmin, xmax)).astype(float)
        self.conf_lower = array((m*xmin + b + dmedian + dsd_lower, \
                          m*xmax + b + dmedian + dsd_lower)).astype(float)
        self.conf_upper = array((m*xmin + b + dmedian + dsd_upper, \
                          m*xmax + b + dmedian + dsd_upper)).astype(float)
        return fit_label
