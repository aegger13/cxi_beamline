import matplotlib
if not hasattr(matplotlib,'backends'):
    matplotlib.use("TkAgg")
import pylab as p
from numpy import array,isfinite
from peakanalysis import PeakAnalysis
import blutil


class Plot2D:
  def __init__(self,i,x=None,y=None,daq=None,dets=None):
    self.__id = i
    self.daq=daq
    self.dets=dets
    p.ion(); # interactive on
    self.enable=True
    self.fig = p.figure(i)
    self.fig.canvas.set_window_title('%spython online plot' % blutil.guessBeamline())
    self.plot=self.fig.add_subplot(1,1,1); # make one plot
    specs = ['ko-','rs-','gd-','b^-','mv-','c>-','y<-']
    specdescs = ['black circles','red squares','green diamonds','blue triangles up','magenta triangles down','cyan triangles right','yellow triangles left (last linespec series, next will be black again)']
    specNO = self.fig.get_label()
    if not specNO:
      specNO=0
    specNO = int(specNO)
    if specNO==7:
      specNO=0
    thisspec = specs[specNO]
    print 'Data is plotted as %s.' % specdescs[specNO]
    self.fig.set_label(specNO+1)

    if (x is not None):
      self.line,=self.plot.plot(x,y,thisspec)
    else:
      self.line,=self.plot.plot([0, 1],[0,1],thisspec)
    p.draw()

  def win_title(self,title):
    self.fig.canvas.set_window_title(title)

  def set_xlabel(self,xlabel):
    p.figure(self.__id)
    p.xlabel(xlabel)

  def set_ylabel(self,ylabel):
    p.figure(self.__id)
    p.ylabel(ylabel)

  def set_title(self,title):
    p.figure(self.__id)
    p.title(title)

  def get_linelist(self):
    ah = self.fig.get_axes()[0]
    dstr = ''
    n = 0
    for lh in ah.lines:
      n+=1
      dstr += "  %d : " % n
      str = lh.markers[lh.get_marker()]
      marker = str.split('_draw_')[-1].replace('_',' ')
      color = self.get_colorname(lh.get_color())
      dstr += "%s %s\n" % (color,marker)
    print dstr

  def getMostRecentData(self):
    ah = self.fig.get_axes()[0]
    return ah.lines[-1].get_data()

  def remove_line(self,lineno):
    self.fig.get_axes()[0].lines[lineno-1].remove()
    p.draw()

  def get_colorname(self,colorletter):
    colors = dict(b='blue',g='green',r='red',c='cyan',m='magenta',y='yellow',k='black',w='white')
    colorstring = colors[colorletter]
    return colorstring

  def setdata(self,x,y):
    if (not self.enable):
      return
    p.figure(self.__id)
    x=array(x)[isfinite(x)]
    y=array(y)[isfinite(x)]
#    print y
#    idx = isfinite(y)
#    x = x[idx]
#    y = y[idx]
    self.line.set_data(x,y)
    try:
        self.plot.set_ylim(y[isfinite(y)].min(),y[isfinite(y)].max())
    except ValueError:
        print "Error updating ylim! We have no data or invalid data!"
    try:
        self.plot.set_xlim(x[isfinite(x)].min(),x[isfinite(x)].max())
    except ValueError:
        print "Error updating xlim! We have no data or invalid data!"
    try :
      (CEN,FWHM,PEAK) = PeakAnalysis(x,y)
    except:
      CEN=FWHM=PEAK=1e1000/1e1000
    title = "CEN %.5e, FWHM %.5e, PEAK %.5e" % (CEN,FWHM,PEAK)
    self.set_title(title)
    p.draw()
    p.pause(0.01)

  def get_data_from_daq(self):
    while True:
        x = self.daq._Daq__x
        y = self.daq._Daq__y[self.dets[0]]
        if (not self.enable):
            return
        p.figure(self.__id)
        x=array(x)
        y=array(y)
        if x==array([]):
          x = array([0,1])
        if y==array([]):
          y = array([0,1])
          yield x,y

  def update_plot(self,data):
    x,y = data
    self.line.set_data(x,y)
    #self.plot.set_ylim(y[isfinite(y)].min(),y[isfinite(y)].max())
    #self.plot.set_xlim(x[isfinite(x)].min(),x[isfinite(x)].max())
    try :
      (CEN,FWHM,PEAK) = PeakAnalysis(x,y)
    except:
      CEN=FWHM=PEAK=1e1000/1e1000
    title = "CEN %.5e, FWHM %.5e, PEAK %.5e" % (CEN,FWHM,PEAK)
    self.set_title(title)

  def set_updating(self):
      self.ani = animation.FuncAnimation(self.fig, self.update_plot, self.get_data_from_daq, interval=100)

  def __call__(self,x,y):
    self.setdata(x,y)

