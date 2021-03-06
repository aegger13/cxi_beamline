#!/usr/bin/python
# This module provides support for PV based monitors
# 
# Author:         Marco Cammarata (SLAC)
# Created:        Aug 5, 2010
# Modifications:
#   Aug 5, 2010 MC
#       first version

import pyami
import numpy
from numpy import nan,array,sqrt,isfinite
from blutil.pypslog import logprint
from time import sleep
import thread

detector_ids = {
  'CsPad':      (0x14000a00,'Image'),
  'CsPad2x2_0': (0x14000d00,'Image'),
  'CsPad2x2_1': (0x14000d01,'Image'),
  'YagMono':    (0x0f010401,'Image'),
  'Yag2':       (0x12010401,'Image'),
  'Yag2Single': (0x12010401,'SingleImage'),
  'Yag3':       (0x13010401,'Image'),
  'Opal0':      (0x16000300,'Image'),
  'Opal1':      (0x16000301,'Image'),
  'Opal1Single':(0x16000301,'SingleImage'),
  'Opal2':      (0x16000302,'Image'),
  'Acquiris':   (0x15000200,'Waveform'), #
  #'Imp':        (0x16001c00,'Waveform'),  
}

class PYAMIdetector:
  """A simple class to handle PV based detectors"""
  def __init__(self,ami_name,mne_name,channel=-1):
    self.aminame = ami_name
    self.name   = mne_name
    self.scale  = 1
    self.pyamiE = None
    self.type = "Scalar"
    self.channel = channel
    self.__filter_string = None
    for detId in detector_ids:      
      if (ami_name == detId):
        self.type = detector_ids[detId][1]
        self.aminame = detector_ids[detId][0]
        if (self.type == "Image") or (self.type == "SingleImage"):
          self.channel=0

  def create_ami(self,type):
    try:
      if type == "Scalar":
        if self.__filter_string is None:
          self.pyamiE  = pyami.Entry(self.aminame, "Scalar")
        else:
          self.pyamiE  = pyami.Entry(self.aminame, "Scalar", self.__filter_string)
      elif type == "SingleImage":
        self.pyamiE  = pyami.Entry(det_id=self.aminame, channel=self.channel, op='single')
      else:
        self.pyamiE  = pyami.Entry(self.aminame, self.channel)
    except RuntimeError:
      s = "detector %s cannot be found" % self.name
      logprint(s,print_screen=True)
      self.pyamiE = None

  def connect(self,filter_string=None,forceconnect=0,type=None):
    if type is None:
      type = self.type
    if (forceconnect > 0):
      self.pyamiE = None
    if (self.pyamiE is not None):
      if filter_string == self.__filter_string:
        #print "PYAMI: entry already exists for %s" %self.aminame
        #print "PYAMI: creating new entry for %s REMOVE THIS" % self.name
        #self.create_ami(type)
        return
      else:
        self.__filter_string = filter_string
        print "PYAMI: recreating entry for %s (filter changed)" % self.name
        self.create_ami(type)
    else:
      print "PYAMI: creating initial entry for %s" % self.name
      self.create_ami(type)

  def get(self):
    self.connect(self.__filter_string)
    if (self.type == "Scalar"):
      return self.getScalar()
    elif (self.type == "Image") or (self.type == "SingleImage"):
      return self.getImage()
    else:
      print 'detector type unsupported'

  def getScalar(self):
    if (self.pyamiE is None):
      x={}
      x["entries"]=0
      x["mean"] = numpy.nan
      x["rms"] = numpy.nan
      x["err"] = numpy.nan
    else:
      try:
        x = self.pyamiE.get()
        x["mean"]=self.scale*x["mean"]
        x["err"] = x["rms"]/sqrt(x["entries"])
      except RuntimeError:
        x={}
        x["entries"]=0
        x["mean"] = numpy.nan
        x["rms"] = numpy.nan
        x["err"] = numpy.nan
    return x

  def getImage(self):
    x={}
    x["entries"]=0
    if (self.pyamiE is not None):
      try:
        #self.pyamiE.clear()
        #x=self.pyamiE.get()
        #ntries=0
        #while (x["entries"]==0 and ntries < 110):
        #  #sleep(0.01)
        #  x=self.pyamiE.get()
        #  print 'have ', x["entries"], ' images'
        #  ntries = ntries+1
        x=self.pyamiE.get()
      except RuntimeError:
        print 'runtimeError getting',self.nam
    #if (config.DEBUG>1):
    #  print 'got ', x["entries"],' images, return now' 
    return x

  def getImageTest(self, nImages=1):
    x={}
    x["entries"]=0
    self.connect(self.__filter_string)
    if (self.pyamiE is not None):
      try:
        #self.pyamiE.clear()
        #x=self.pyamiE.get()
        #ntries=0
        #while (x["entries"]==0 and ntries < 110):
        #  #sleep(0.01)
        #  x=self.pyamiE.get()
        #  print 'have ', x["entries"], ' images'
        #  ntries = ntries+1
        x=self.pyamiE.get()
        ngets=1
        print 'start: ',x['time']
        tstamp=0
        for i in range(0,nImages):
          while (tstamp == x['time']):
            x=self.pyamiE.get()
            ngets=ngets+1
          if (tstamp==0):
            tstart=x['time']
          tstamp=x['time']
      except RuntimeError:
        print 'runtimeError getting',self.nam
    #if (config.DEBUG>1):
    #  print 'got ', x["entries"],' images-return now' 
    print 'end: ',x['time'],' total gets: ',ngets
    if (nImages >1):
      print ' got images effectively at ',nImages/(x['time']-tstart),' Hz'
    return x

  def getImagePush(self, nImages=1):
    x={}
    x["entries"]=0
    times = []
    self.connect(self.__filter_string)
    if (self.pyamiE is not None):
      self.pyamiE.pstart()
      try:
        for i in range(0,nImages):          
          x=self.pyamiE.pget()
          if (i==0): tstart=x['time']
          times.append(x['time'])
        if (nImages >1):
          print ' got images effectively at ',(nImages-1)/(x['time']-tstart),' Hz'
      except RuntimeError:
        print 'runtimeError getting',self.name
      self.pyamiE.pstop()
    times.sort()
    print 'times: ',times
    return x

  def getmean(self,int_time=None):
    self.connect(self.__filter_string)
    if (self.type == "Scalar"):
      return self.getmeanScalar()
    else:
      print 'detector type unsupported'

  def getmeanScalar(self,int_time=None):
    if (self.pyamiE is None):
      return numpy.nan
    else:
      if (int_time is not None):
        self.clear()
        sleep(int_time)
      x = self.get()
      return self.scale*x["mean"]

  def clear(self):
    self.pyamiE.clear()
      
class IPIMBDetector:
  """A simple class to handle Pv based detectors"""
  def __init__(self,aminame,namebase="detector",kind="NotKnown",timeout=15):
    self.aminame=aminame
    self.__kind = kind
    if (namebase == ""):
      namebase = pvname
    self.ch0  = PYAMIdetector( aminame + ":CH0" ,namebase+".ch0" )
    self.ch1  = PYAMIdetector( aminame + ":CH1" ,namebase+".ch1" )
    self.ch2  = PYAMIdetector( aminame + ":CH2" ,namebase+".ch2" )
    self.ch3  = PYAMIdetector( aminame + ":CH3" ,namebase+".ch3" )
    self.sum  = PYAMIdetector( aminame + ":SUM" ,namebase+".sum")
    self.xpos = PYAMIdetector( aminame + ":XPOS",namebase+".xpos")
    self.ypos = PYAMIdetector( aminame + ":YPOS",namebase+".ypos")

  def __repr__(self):
    return self.status()

  def status(self):
    str=""
    if (self.__kind=="ipm"):
      str  = " %10s %6s %6s %10s %10s %10s %10s\n" % ("sum", "xpos","ypos","ch0(up)","ch1(north)","ch2(down)","ch3(south)")
      str += "  %+10.3e %+6.3f %+6.3f " % ( self.sum.getmean(0.3),self.xpos.getmean(0.3),self.ypos.getmean(0.3) )
      str += "%10.3e %10.3e %10.3e %10.3e\n" % ( self.ch0.getmean(0.3),self.ch1.getmean(0.3),self.ch2.getmean(0.3),self.ch3.getmean(0.3) )
    if (self.__kind=="pim"):
      str  = " %10s %10s %10s %10s\n" % ("ch0(up)","ch1(north)","ch2(down)","ch3(south)")
      str += "%10.3e %10.3e %10.3e %10.3e\n" % ( self.ch0.getmean(0.3),self.ch1.getmean(0.3),self.ch2.getmean(0.3),self.ch3.getmean(0.3) )
    return str

#this should be rewritten: not necesarily do we run with all channels (or more than 1-2).
class ADCDetector:
  """A simple class to handle Pv based detectors"""
  def __init__(self,aminame,namebase="detector",kind="NotKnown",timeout=15):
    self.__kind = kind
    if (namebase == ""):
      namebase = pvname
    if self.__kind == 'slowAdc': 
      self.ch0  = PYAMIdetector( aminame + ":Ch00" ,namebase+".ch0" )
      self.ch1  = PYAMIdetector( aminame + ":Ch01" ,namebase+".ch1" )
      self.ch2  = PYAMIdetector( aminame + ":Ch02" ,namebase+".ch2" )
    elif self.__kind == 'Acromag': 
      self.ch0  = PYAMIdetector( aminame + ":CH0" ,namebase+".ch0" )
      self.ch1  = PYAMIdetector( aminame + ":CH1" ,namebase+".ch1" )
      self.ch2  = PYAMIdetector( aminame + ":CH2" ,namebase+".ch2" )
      self.ch3  = PYAMIdetector( aminame + ":CH3" ,namebase+".ch3" )
      self.ch4  = PYAMIdetector( aminame + ":CH4" ,namebase+".ch4" )
      self.ch5  = PYAMIdetector( aminame + ":CH5" ,namebase+".ch5" )
      self.ch6  = PYAMIdetector( aminame + ":CH6" ,namebase+".ch6" )
      self.ch7  = PYAMIdetector( aminame + ":CH7" ,namebase+".ch7" )
      self.ch8  = PYAMIdetector( aminame + ":CH8" ,namebase+".ch8" )
      self.ch9  = PYAMIdetector( aminame + ":CH9" ,namebase+".ch9" )
      self.ch10  = PYAMIdetector( aminame + ":CH10" ,namebase+".ch10" )
      self.ch11  = PYAMIdetector( aminame + ":CH11" ,namebase+".ch11" )
      self.ch12  = PYAMIdetector( aminame + ":CH12" ,namebase+".ch12" )
      self.ch13  = PYAMIdetector( aminame + ":CH13" ,namebase+".ch13" )
      self.ch14  = PYAMIdetector( aminame + ":CH14" ,namebase+".ch14" )
      self.ch15  = PYAMIdetector( aminame + ":CH15" ,namebase+".ch15" )


  def __repr__(self):
    return self.status()

  def status(self):
    str=""
    if (self.__kind=="slowAdc"):
#      str  = " %10s %10s %10s %10s %10s\n" % ("ch0", "ch1","ch2","ch3","ch4")
#      str += " %10.3e %10.3e %10.3e %10.3e %10.3e\n" % ( self.ch0.getmean(0.3),self.ch1.getmean(0.3),self.ch2.getmean(0.3),self.ch3.getmean(0.3),self.ch4.getmean(0.3) )
      str  = " %10s %10s %10s %10s %10s\n" % ("ch0", "ch1","ch2")
      str += " %10.3e %10.3e %10.3e %10.3e %10.3e\n" % ( self.ch0.getmean(0.3),self.ch1.getmean(0.3),self.ch2.getmean(0.3)  )
    return str


class EncoderDetector:
  """A simple class to handle Pv based detectors"""
  def __init__(self,aminame,namebase="detector",kind="enc",timeout=15):
    self.__kind = kind
    if (namebase == ""):
      namebase = pvname
    self.ch0  = PYAMIdetector( aminame + ":CH0" ,namebase+".ch0" )
    self.ch1  = PYAMIdetector( aminame + ":CH1" ,namebase+".ch1" )
    self.ch2  = PYAMIdetector( aminame + ":CH2" ,namebase+".ch2" )
    self.ch3  = PYAMIdetector( aminame + ":CH3" ,namebase+".ch3" )

  def __repr__(self):
    return self.status()

  def status(self):
    str=""
    if (self.__kind=="enc"):
      str  = " %10s %10s %10s %10s %10s\n" % ("ch0", "ch1","ch2","ch3")
      str += " %10.3e %10.3e %10.3e %10.3e %10.3e\n" % ( self.ch0.getmean(0.3),self.ch1.getmean(0.3),self.ch2.getmean(0.3),self.ch3.getmean(0.3))
    return str

class Wave8Detector:
  """A simple class to handle Pv based detectors"""
  def __init__(self,aminame,namebase="detector",kind="snd",timeout=15):
    self.__kind = kind
    if (namebase == ""):
      namebase = pvname
    self.ch0  = PYAMIdetector( aminame + ":PEAK_A:CH00" ,namebase+".ch0" )
    self.ch1  = PYAMIdetector( aminame + ":PEAK_A:CH01" ,namebase+".ch1" )
    self.ch2  = PYAMIdetector( aminame + ":PEAK_A:CH02" ,namebase+".ch2" )
    self.ch3  = PYAMIdetector( aminame + ":PEAK_A:CH03" ,namebase+".ch3" )
    self.ch4  = PYAMIdetector( aminame + ":PEAK_A:CH04" ,namebase+".ch4" )
    self.ch5  = PYAMIdetector( aminame + ":PEAK_A:CH05" ,namebase+".ch5" )
    self.ch6  = PYAMIdetector( aminame + ":PEAK_A:CH06" ,namebase+".ch6" )
    self.ch7  = PYAMIdetector( aminame + ":PEAK_A:CH07" ,namebase+".ch7" )
    self.ch8  = PYAMIdetector( aminame + ":PEAK_A:CH08" ,namebase+".ch8" )
    self.ch9  = PYAMIdetector( aminame + ":PEAK_A:CH09" ,namebase+".ch9" )
    self.ch10 = PYAMIdetector( aminame + ":PEAK_A:CH10" ,namebase+".ch10" )
    self.ch11 = PYAMIdetector( aminame + ":PEAK_A:CH11" ,namebase+".ch11" )
    self.ch12 = PYAMIdetector( aminame + ":PEAK_A:CH12" ,namebase+".ch12" )
    self.ch13 = PYAMIdetector( aminame + ":PEAK_A:CH13" ,namebase+".ch13" )
    self.ch14 = PYAMIdetector( aminame + ":PEAK_A:CH14" ,namebase+".ch14" )
    self.ch15 = PYAMIdetector( aminame + ":PEAK_A:CH15" ,namebase+".ch15" )
    if self.__kind == 'snd':
      self.dd  = PYAMIdetector( aminame + ":PEAK_A:CH08" ,namebase+".dd" ) 
      self.dcc  = PYAMIdetector( aminame + ":PEAK_A:CH09" ,namebase+".dcc" )
      self.dci  = PYAMIdetector( aminame + ":PEAK_A:CH10" ,namebase+".dci" )
      self.dco  = PYAMIdetector( aminame + ":PEAK_A:CH11" ,namebase+".dco" )
      self.di  = PYAMIdetector( aminame + ":PEAK_A:CH12" ,namebase+".di" )
      self.do  = PYAMIdetector( aminame + ":PEAK_A:CH13" ,namebase+".do" )
      self.t4  = PYAMIdetector( aminame + ":PEAK_A:CH14" ,namebase+".t1" )
      self.t1  = PYAMIdetector( aminame + ":PEAK_A:CH15" ,namebase+".t4" )
    if self.__kind == 'bmmon':
      self.sum  = PYAMIdetector( aminame + ":SUM"  ,namebase+".sum" )
      self.xpos = PYAMIdetector( aminame + ":XPOS" ,namebase+".xpos" )
      self.ypos = PYAMIdetector( aminame + ":yPOS" ,namebase+".ypos" )

  def __repr__(self):
    return self.status()

  def status(self):
    str=""
    if (self.__kind.find("snd")>=0):
      str="status printout not yet defined."
    return str
