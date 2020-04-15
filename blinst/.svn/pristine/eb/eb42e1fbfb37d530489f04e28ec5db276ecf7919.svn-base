from blutil import estr
from blbase.motorutil import tweak2D
from blbase.stateioc import stateiocDevice
import psp.Pv as Pv
from time import time,sleep
from beamline import *
from blutil import estr


class RefLaser:
  def __init__(self, motors, mirrorPV, mirror, x=None, y=None, rx=None, ry=None, air_x=None, air_y=None, vac_x=None, vac_y=None, motors_in_way=None, flipper=None, glaswindow=None, bewindow=None):
    self.m=mirror
    if air_x is not None: self.air_x=air_x
    if air_y is not None: self.air_y=air_y
    if vac_x is not None: self.vac_x=vac_x
    if vac_y is not None: self.vac_y=vac_y
    if rx is not None: self.rx=rx
    if ry is not None: self.ry=ry
    if x is not None: self.x=x
    if y is not None: self.y=y
    self._motors = motors
    self._flip = flipper
    self._glaswindow = glaswindow
    self._bewindow = bewindow
    if self._flip is not None:
      setattr(self, self._flip._name, self._flip)
    self._inout = stateiocDevice(mirrorPV)
    if motors_in_way is None:
      self._motors_in_way = []
    else:
      self._motors_in_way = motors_in_way
    self._motors_in_way_name = [ mot_tup[0] for mot_tup in self._motors_in_way ]
    self._outpresetname = 'reflaser_beamline_position'

  def moveinBeamlineOut(self):
    self.movein()
    self.outPosGroup = self._motors.set_presets(self._motors_in_way_name, self._outpresetname)
    for motname,pos in self._motors_in_way:
      self._motors.__dict__[motname].mv(pos)
      sleep(.1)
    if self._glaswindow is not None:
      self._glaswindow.close()
    self.unblock()   

  def moveoutBeamlineIn(self):
    self.moveout()
    print "Loading preset of previously saved \"beamline-in\" position..."
    self.outPosGroup.group_move(self._outpresetname)
    if self._glaswindow is not None and self._bewindow is not None:
      if self._glaswindow.openok():
        self._bewindow.close()
      else: print "Cannot open the glass window; no permission"
    self.block()

  def set_inpos(self,pos):
    self._inout.setStatePos("IN", pos)
     
  def set_outpos(self,pos):
    self._inout.setStatePos("OUT", pos)
     
  def movein(self):
    self._inout.move_in()

  def moveout(self):
    self._inout.move_out()

  def wait(self):
    self._inout.wait()

  def isin(self):
    return self._inout.is_in()

  def isout(self):
    return self._inout.is_out()

  def status(self):
    pos = self.m.wm()
    if self.isin():
      pos_str =  estr("IN",color="red",type="normal")
    elif self.isout():
      pos_str =  estr("OUT",color="green",type="normal")
    else:
      pos_str = estr("UNKOWN",color="red")
    str = "Ref laser position is : %s (stage at %.3f mm)" % (pos_str,pos)
    if hasattr(self, 'x') or hasattr(self, 'y') or hasattr(self, 'rx') or hasattr(self, 'ry'):
      str+='\npico motors positions: \n'
      if hasattr(self, 'x'): str+='x = %+.4f\n' % self.x.wm()
      if hasattr(self, 'y'): str+='y = %+.4f\n' % self.y.wm()
      if hasattr(self, 'rx'): str+='rx = %+.4f\n' % self.rx.wm()
      if hasattr(self, 'ry'): str+='ry = %+.4f\n' % self.ry.wm()
    return str

  def block(self):
    if self._flip is not None: self._flip.flip_in()

  def unblock(self):
    if self._flip is not None: self._flip.flip_out()

  def tweakair(self):
    if hasattr(self, 'air_x') and hasattr(self, 'air_y'):
      tweak2D(self.air_x,self.air_y,mothstep=0.001,motvstep=0.001,dirh=-1,dirv=-1)

  def tweakvac(self):
    if hasattr(self, 'vac_x') and hasattr(self, 'vac_y'):
      tweak2D(self.vac_x,self.vac_y,mothstep=0.001,motvstep=0.001,dirh=-1,dirv=-1)

  def edm(self):
    try:
      self.m.expert_screen()
    except:
      print "Problem with motor_expert_screen script!"

  def __repr__(self):
    return self.status()
