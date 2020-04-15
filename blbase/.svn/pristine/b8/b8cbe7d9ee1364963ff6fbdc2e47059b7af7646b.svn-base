### Bob Nagler, May 01 2012

import psp.Pv as Pv
from blutil import notice
import time
from numpy import *
from time import time, sleep
class NanoMotor(object):
  def __init__(self,pvmove,pvread,name,pvspeed):
#    Motor.__init__(self,None,name,readbackpv=None,has_dial=False)
    self.name   = name
    self.pvmv = pvmove
    self.pvrd = pvread
    self.pvspeed=pvspeed

  def __call__(self,value):
    self.move(value)

  def __repr__(self):
    return self.status()

  def status(self):
    s  = "Pv motor %s\n" % self.name
    s += "  current position %.4g\n" % self.wm()
    return s

  def move_relative(self,howmuch):
    p = self.wm()
    return self.move(p+howmuch)

  def move_silent(self,value): return self.move(value)

  def mvr(self,howmuch): return self.move_relative(howmuch)

  def  move(self,value): return  Pv.put(self.pvmv,str(value))

  def  mv(self,value): return self.move(value)

  def  wm(self):
    mposstr=Pv.get(self.pvrd)
    mpos=double(mposstr)
    return mpos






  def update_move(self,value,show_previous=True):
    """ moves motor while displaying motor position, CTRL-C stops motor"""
    if (show_previous):
     print "initial position: " + str(self.wm())
    self.move(value)
    sleep(0.02)
    try:
      while(abs(self.wm()-value)>0.01):
        s="motor position: " + str(self.wm())
        notice(s)
        sleep(0.01)
    except KeyboardInterrupt:
      print "Ctrl-C pressed. trying to stopping motor"
      self.mv(self.wm())
      sleep(1)
    s="motor position: " + str(self.wm())
    notice(s)




  def umv(self,value):return self.update_move(value)

  def umvr(self,howmuch,show_previous=True):
    startpos=self.wm()
    endpos=startpos+howmuch
    return self.update_move(endpos,show_previous)

  def  wait(self): time.sleep(0.02)

  def speed(self,value=None):
    """returns the speed, or sets it.
       This is a temporary hack, particularly for the nanoc for the tychography
    """

    if value==None:
      v=Pv.get(self.pvspeed)
      return v

    else:
      Pv.put(self.pvspeed,str(value))
      
