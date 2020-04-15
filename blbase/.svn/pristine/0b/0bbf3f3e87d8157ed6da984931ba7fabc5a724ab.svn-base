import psp.Pv as Pv
import time
from numpy import *
from time import time, sleep
from blbase.motorutil import tweak, tweak2D

class Questar(object):
  def __init__(self,motor_x,motor_y,motor_focus,camera,name):
    self._name   = name
    self.mx = motor_x
    self.my = motor_y
    self.mfocus = motor_focus
    self.cam = camera
    
  def focus(self,step=0.1):
    '''changes the focus of the questar.
       1d tweak: use left right arrow for motion, up-down to change stepsize'''
    self.mfocus.tweak(step)
 
  def tweak(self):
    '''tweaks the left-right and up-down position of the questar. 
       2d tweak: use arrow for motion. +- changes stepsize. CTRL-C to quit''' 
    
    tweak2D(self.mx,self.my,dirh=1,dirv=1) 

  def grab(self,show=False):
    '''grabs an image of the questar camera and returns it as a numpy array.'''
    tmpdata=self.cam.grab(show)
    return tmpdata

  def viewer(self):
    ''' launcher the viewer of the questar camera'''
    self.cam.viewer()
  
