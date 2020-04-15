import pyca
import psp.Pv as Pv
from blutil import estr
from blutil.calc import * 
from time import sleep

class DelayStage2time:

  def __init__(self,name,stage,user_pv=None,direction=1):
    self.name = name
    self.user_pv = user_pv
    self.stage = stage
    self.direction = direction
   
  def mv(self,t):
    """ Sets the stage delay 
        t is the desired laser delay (seconds)
    """
    mm=self.secondsToMM(t)
    self.stage.mv(0.5*mm)
    if self.user_pv:
      Pv.put(self.user_pv,t)
    return

  def set(self,t):
    mm = self.secondsToMM(t)
    self.stage.set(mm)
    if self.user_pv:
      Pv.put(self.user_pv,t)
    return
    
  def wm(self):
    mm = self.stage.wm()
    t = self.mmToSeconds(2*mm)
    return t

  def wait(self):
    self.stage.wait()
 
  def mmToSeconds(self,mm):
    t=self.direction*mm/u['mm']/c['c']
    return t

  def secondsToMM(self,t):
    mm=self.direction*t*c['c']*u['mm']
    return mm
  
  def get_hilim(self):
    if hasattr(self.stage,'get_hilim') and hasattr(self.stage,'get_lowlim'):
      if self.direction>0:
        return self.mmToSeconds(self.stage.get_hilim()*2.)
      elif self.direction<0:
        return self.mmToSeconds(self.stage.get_lowlim()*2.)
      return -self.mmToSeconds(self.stage.get_hilim()*2.)

  def get_lowlim(self):
    if hasattr(self.stage,'get_hilim') and hasattr(self.stage,'get_lowlim'):
      if self.direction>0:
        return self.mmToSeconds(self.stage.get_lowlim()*2.)
      elif self.direction<0:
        return self.mmToSeconds(self.stage.get_hilim()*2.)
      return -self.mmToSeconds(self.stage.get_lowlim()*2.)

class timeStageSeries_Compensate:

  def __init__(self,name,stage0,stage1,stage0direction=1,stage1direction=1):
    self.name = name
    self.stage0 = stage0
    self.stage1 = stage1
    self.stage0direction = stage0direction
    self.stage1direction = stage1direction
   
  def mv(self,t):
    self.stage0.mv(t)
    if (-t > self.stage1.get_lowlim()) and (-t < self.stage1.get_hilim()):
      self.stage1.mv(-t)
    else: 
      print "cannot move delaystage1 for the timetool, reached limit"
      print "stage0:",self.stage0.status()
      print "stage1:",self.stage1.status()
    return

  #def set(self,t):
    #mm = self.secondsToMM(t)
    #self.stage.set(mm)
    #if self.user_pv:
      #Pv.put(self.user_pv,t)
    #return
    
  def wm(self):
    return self.stage0.wm()

  def wait(self):
    self.stage0.wait()
    self.stage1.wait()

  def set(self,value):
    self.stage0.set(value)
    self.stage1.set(-value)


class timeStageSeries_Compensate_relative:

  def __init__(self,name,stage0,stage1,stage1lowlim,stage1highlim,stage0direction=1,stage1direction=1):
    self.name = name
    self.stage0 = stage0
    self.stage1 = stage1
    self.stage0direction = stage0direction
    self.stage1direction = stage1direction
    self.stage1lowlim = stage1lowlim
    self.stage1highlim = stage1highlim
   
  def mv(self,t):
    s0_0 = self.stage0.wm()
    s1_0 = self.stage1.wm()
    Dt = t - s0_0
    s1_1 = s1_0 - self.stage1direction*Dt
    self.stage0.mv(t)
    if (s1_1>self.stage1lowlim) & (s1_1<self.stage1highlim):
      self.stage1.mv(s1_1)
    else:
      print "Move of %s cannot be compensated by %s!" %(self.stage0.name,self.stage1.name)
    return

  #def set(self,t):
    #mm = self.secondsToMM(t)
    #self.stage.set(mm)
    #if self.user_pv:
      #Pv.put(self.user_pv,t)
    #return
    
  def wm(self):
    return self.stage0.wm()

  def wait(self):
    self.stage0.wait()
    self.stage1.wait()
 
