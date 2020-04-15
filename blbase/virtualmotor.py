from time import sleep,time
from blutil.pypslog import logprint
from blutil import config
from blutil import notice
import psp.Pv as Pv
import datetime
import pprint
import simplejson
import shutil
from functools import partial
from pylab import ginput
import numpy as np
from blutil import keypress
import os
import sys
from blutil.threadtools import PycaThread
import motorPresets as mp

#
# MCB - User vs. Dial coordinates.
#
# For the most part, these should be identical.  If they aren't, there will
# usually be a pvoff PV defined, giving the offset between the two.
#
# However, there is some old XCS code that strictly deals with user coordinates
# and wants to pass in getUserHilim/getUserLowlim functions.  If these are
# defined, the coordinates might differ, but we have *no* idea how.  In this
# use case, we had better be using *only* user coordinates and not have any
# different dial coordinates.
#

class VirtualMotor(object):
  def __init__(self,name,move,wm,wait=None,set=None,stop=None,tolerance=None,direction=1,
               pvpos=None,pvoff=None,lowlim=None,hilim=None,
               getDialHilim=None, getDialLowlim=None, setDialHilim=None, setDialLowlim=None,
               getUserHilim=None, getUserLowlim=None,
               backlash_dist=0, unattended=False, set_speed=None, get_speed=None, motorsobj=None, egu="mm"):
    self.name   = name
    self._move_dial   = move
    self._wm     = wm
    self._wait   = wait
    self.tolerance = tolerance
    self._set     = set
    self._stop     = stop
    self.pvname = "virtual motor"
    self.pvpos = pvpos; # position pv
    self.pvoff = pvoff; # offset pv
    self.direction = direction/abs(direction) # 1 or -1
    self.low_dial_lim = lowlim
    self.high_dial_lim = hilim
    self.getDialHighlim = getDialHilim
    self.getDialLowlim = getDialLowlim
    self.setDialHighlim = setDialHilim
    self.setDialLowlim = setDialLowlim
    self.getUserHighlim = getUserHilim
    self.getUserLowlim = getUserLowlim
    self.move_silent = self.move
    self.backlash_dist = backlash_dist
    self._desired_value = None
    if motorsobj is not None:
      try:
        motorsobj.add(self)
      except:
        motorsobj.__setattr__(self.name,self)
    self._unattended = unattended
    if unattended:
      print "unattended motion, waiting function will be overwritten"
      self._wait = self._wait_for_movingflag 
    if not get_speed == None:
      self.get_speed = get_speed
    if not set_speed == None:
      self.set_speed = set_speed
    self.egu=egu
    if mp.ready():
      self.presets = mp.MotorPresets(self) 

  def get_highLimDial(self):
    if self.getDialHighlim is not None:
      return self.getDialHighlim()
    else:
      return self.high_dial_lim

  def get_lowLimDial(self):
    if self.getDialLowlim is not None:
      return self.getDialLowlim()
    else:
      return self.low_dial_lim

  def set_highLimDial(self, value):
    if self.setDialHighlim is not None:
      self.setDialHighlim(value)
    else:
      self.high_dial_lim = value

  def set_lowLimDial(self, value):
    if self.setDialLowlim is not None:
      self.setDialLowlim(value)
    else:
      self.low_dial_lim = value

  def get_hilim(self):
    if self.getUserHighlim is not None:
      return self.getUserHighlim()
    if (self.pvoff is None):
      offset=0
    else:
      offset=Pv.get(self.pvoff)
    lim = self.get_highLimDial()
    if lim is not None:
      lim = self.direction*self.get_highLimDial()+offset
    return lim

  def set_hilim(self, value):
    if (self.pvoff is None):
      offset=0
    else:
      offset=Pv.get(self.pvoff)
    lim = self.direction * (value - offset) 
    self.set_highLimDial(lim)

  def get_lowlim(self):
    if self.getUserLowlim is not None:
      return self.getUserLowlim()
    if (self.pvoff is None):
      offset=0
    else:
      offset=Pv.get(self.pvoff)
    lim = self.get_lowLimDial()
    if lim is not None:
      lim = self.direction*lim+offset
    return lim

  def set_lowlim(self, value):
    if (self.pvoff is None):
      offset=0
    else:
      offset=Pv.get(self.pvoff)
    lim = self.direction * (value - offset) 
    self.set_lowLimDial(lim)

  def set(self,value):
    if (self._set is not None):
      self._set(value)
    elif (self.pvoff is not None):
      offset = value - self.direction*self.wm_dial()
      Pv.put(self.pvoff,offset)
      sleep(0.1); # gives epics time to update offset pv
      self.wm()
    else:
      print "user position not defined for this motor"
      
  def stop(self):
    if (self._stop is not None):
      self._stop()
    else:
      print "stop method is not defined!!!"


  def wm(self, debug=0):
    if debug>0:
      print 'virt motor wm: '
    if (self.pvoff is None):
      offset=0
    else:
      offset=Pv.get(self.pvoff)
    if debug>0:
      print 'virtualmotor offset: ',offset
      print 'virtualmotor dir: ',self.direction
      print 'virtualmotor dial pos: ',self.wm_dial()
    user = self.direction*self.wm_dial()+offset
    if (self.pvpos is not None):
      Pv.put(self.pvpos,user)
    return user

  def wm_update(self):
    try:
      while True:
        s = "motor position: %s" % self.wm_string()
        notice(s)
        sleep(0.05)
    except KeyboardInterrupt:
        pass

  def move(self,value):
    if (self.pvoff is None):
      offset=0
    else:
      offset=Pv.get(self.pvoff)
    dial = (float(value)-offset)*self.direction
    if (self.backlash_dist>0) and (self.wm() > value):
      dial_backlash = (float(value)-offset-self.backlash_dist)*self.direction
      self.move_dial(dial_backlash)
    elif (self.backlash_dist<0) and (self.wm() < value):
      dial_backlash = (float(value)-offset-self.backlash_dist)*self.direction
      self.move_dial(dial_backlash)
    self._desired_value = value
    self.move_dial(dial)
    return value

  def wm_string(self):
    return self.wm()

  def wm_dial(self):
    pos = self._wm()
    return pos

  def move_dial(self,value):
    if (self.low_dial_lim is not None):
      check_low = (value>=self.low_dial_lim)
    else:
      check_low = True
    if (self.high_dial_lim is not None):
      check_high = (value<=self.high_dial_lim)
    else:
      check_high = True
    check = check_low and check_high
    if (not check):
      logprint("Asked to move %s (pv %s) to dial %f that is outside limits, aborting" % (self.name,self.pvname,value),print_screen=1)
    else:
      self._join_thread()
      if not self._unattended:
        self._move_dial(value)
        if self.pvpos is not None:
          self._movethread = PycaThread(target=self.__wait_and_update_user_PV)
          self._movethread.start()
        else:
          self.wm()
      else:
        self._movethread = PycaThread(target=self._move_dial_and_update_user_PV,args=(value,))
        self._movethread.start()

  def _join_thread(self):
    try:
      self._movethread.join()
    except AttributeError:
      pass

  def _move_dial_and_update_user_PV(self,value):
    self._ismoving = True
    self._move_dial(value)
    self.wm()
    self._ismoving=False

  def __wait_and_update_user_PV(self):
    #self.wait() can't use this since Pv isn't thread safe
    desired_value = self._desired_value
    nomove_num = 0
    nomove_max = 3
    nomove_tol = self.tolerance or 0.001
    pos_tol = self.tolerance or 0
    pos = self.wm()
    while (abs(pos-desired_value)>pos_tol and nomove_num<nomove_max):
      old_pos = pos
      sleep(0.25)
      pos = self.wm()
      if nomove_num>=nomove_max:
        break
      if (abs(old_pos-pos)<=nomove_tol):
        nomove_num+=1

#this function has no deadband to account for fluctuations of the readback 
#assumes that the motor has no user/dial offset (compares wm() w/ wm_dial())
  def _is_motor_moving(self):
    initial_pos = self.wm()
    sleep(0.1)
    check = (self.wm_dial()==initial_pos)
    if (check):
      self._desired_value = initial_pos
    return (not check)
  
  def _wait_for_movingflag(self):
    while self._ismoving:
      sleep(.0001)

  def wait(self):
    self._join_thread()
    if (self._wait is not None):
      self._wait()
    elif (self.tolerance is None):
      while( self._is_motor_moving() ):
        pass
    else:
      initial_pos = self.wm()
      if (self._desired_value is None):
        #if (self.name == "ccmE"):
            #print "ccmE wait: no desired value, check if moving....", self._is_motor_moving()
        while( self._is_motor_moving() ):
          pass
      else:
        t0 = time()
        #print "ccmE wait: delta pos:",self.wm()-self._desired_value," tolerance ",self.tolerance
        while (abs(self.wm()-self._desired_value)>self.tolerance):
          sleep(0.01)
          if ( ((time()-t0)>0.1) and  (not self._is_motor_moving) ):
            break
        #if (self.name == "ccmE"):
          #print "ccmE after wait: delta pos: ",self.wm() - self._desired_value, "delta time: ",time()-t0, " moving: ", self._is_motor_moving()
    pos = self.wm()
     
  def update_move_relative(self,howmuch,show_previous=True):
    pos = self.wm()
    self.update_move(pos+howmuch,show_previous)
    
  def umvr(self,howmuch,show_previous=True): self.update_move_relative(howmuch,show_previous)

  #def mv_ginput(self):
    #pos = ginput(1)[0][0]
    #print "...moving %s to %g" %(self.name,pos)
    #self.mv(pos)
  def mv_ginput(self,ElogQuestion=True):
    print "Select x-position in current plot by mouseclick\n"
    pos = ginput(1)[0][0]
    print "...moving %s to %g" %(self.name,pos)
    self.mv(pos)
    if ElogQuestion:
      if raw_input('Would you like to send this move to the logbook? (y/n)\n') is 'y':
        elogStr = "Moved %s to %g." %(self.name,pos)
        config.Elog.submit(elogStr)
              
  def mv_elog(self,value,ElogQuestion=True):
    oldpos = self.wm()
    print "...moving %s to %g" %(self.name,value)
    self.mv(value)
    if ElogQuestion:
      if raw_input('Would you like to send this move to the logbook? (y/n)\n') is 'y':
        elogStr = "Moved %s from %g by %g to %g." %(self.name,oldpos,value-oldpos,value)
        config.Elog.submit(elogStr)

  def mvr_elog(self,value,ElogQuestion=True):
    oldpos = self.wm()
    print "...moving %s to %g" %(self.name,value)
    self.mvr(value)
    newpos = self.wm()
    if ElogQuestion:
      if raw_input('Would you like to send this move to the logbook? (y/n)\n') is 'y':
        elogStr = "Moved %s from %g by %g to %g." %(self.name,oldpos,value,newpos)
        config.Elog.submit(elogStr)

  def update_move_dial(self,value,show_previous=True):
    if (show_previous):
      print "initial position: %s" % self.wm_dial()
    self.move_dial(value)
    sleep(0.1)
    while ( self._is_motor_moving() ):
      s = "motor position: %s" % self.wm_dial()
      notice(s)
      sleep(0.05)
    s = "motor position: %s" % self.wm_dial()
    notice(s)
    print ""

  def update_move(self,value,show_previous=True):
    if (show_previous):
      print "initial position: %s" % self.wm_string()
    self.move(value)
    sleep(0.1)
    while ( self._is_motor_moving() ):
      s = "motor position: %s" % self.wm_string()
      notice(s)
      sleep(0.05)
    s = "motor position: %s" % self.wm_string()
    notice(s)
    print ""

  umv = update_move

  def __call__(self,value=None):
    if value is None:
      return self.wm()
    else:
      self.move(value)

  def __str__(self):
    return "virtual motor %s" % self.name

  def __repr__(self):
    return self.status()

  def status(self):
    s  = "virtual motor %s\n" % self.name
    s += "  current position (user,dial): (%.4g,%.4g)\n" % (self.wm(),self.wm_dial())
    if (self.direction>0):
      dir = "not inverted"
    else:
      dir = "inverted"
    s += "  user vs dial direction: %s\n" % dir
    if (self.low_dial_lim is None):
      lowlim="None"
    else:
      lowlim="%.4g" % self.low_dial_lim
    if (self.high_dial_lim is None):
      highlim="None"
    else:
      highlim="%.4g" % self.high_dial_lim
    s += "  dial limits (low,high): (%s,%s)\n" % (lowlim,highlim)
    try:
      s += "  preset position       : %s" % (self.presets.state())
    except AttributeError:
      pass
    return s

  def within_limits(self, pos=None):
    hilim = self.get_hilim()
    lolim = self.get_lowlim()
    if pos is None:
      pos_ok = True
    else:
      pos_ok = (lolim < pos or lolim is None) and (pos < hilim or hilim is None)
    here = self.wm()
    here_ok = (lolim < here or lolim is None) and (pos < hilim or hilim is None)
    return pos_ok and here_ok

  def move_relative(self,howmuch):
    p = self.wm()
    if (howmuch == 0):
      return p
    else:
      return self.move(p+howmuch)

  def mvr(self,howmuch): self.move_relative(howmuch)

  def  mv(self,value):   self.move(value)

  def tweak(self,step=0.1):
    help = "q = exit; up = step*2; down = step/2, left = neg dir, right = pos dir\n"
    help = help + "g = go abs, s = set"
    print "tweaking virtual motor %s " % (self.name)
    print "current position %s" % (self.wm_string())
    step = float(step)
    oldstep = 0
    k=keypress.KeyPress()
    while (k.isq() is False):
      if (oldstep != step):
        print "stepsize: %g" % step
        sys.stdout.flush()
        oldstep = step
      k.waitkey()
      if ( k.isu() ):
        step = step*2.
      elif ( k.isd() ):
        step = step/2.
      elif ( k.isr() ):
        self.mvr(step)
        self.wait()
        print self.wm()
      elif ( k.isl() ):
        self.mvr(-step)
        self.wait()
        print self.wm()
      elif ( k.iskey("g") ):
        print "enter absolute position (char to abort go to)"
        sys.stdout.flush()
        v=sys.stdin.readline()
        try:
          v = float(v.strip())
          self.mv(v)
        except:
          print "value cannot be converted to float, exit go to mode ..."
          sys.stdout.flush()
      elif ( k.iskey("s") ):
        print "enter new set value (char to abort setting)"
        sys.stdout.flush()
        v=sys.stdin.readline()
        try:
          v = float(v[0:-1])
          self.set(v)
        except:
          print "value cannot be converted to float, exit go to mode ..."
          sys.stdout.flush()
      elif ( k.isq() ):
	self.stop()
        break
      else:
        print help
    print "final position: %s" % self.wm_string()

