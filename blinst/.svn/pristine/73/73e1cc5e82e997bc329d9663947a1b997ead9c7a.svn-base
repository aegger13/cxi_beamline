#!/usr/bin/python
# This module provides support for
# PIM (profile intensity monitor) devices

from blbase.stateioc import stateiocDevice
from blutil import estr
from time import sleep
import psp.Pv as Pv

class PIM:
  """ Class to control the PIM """
  def __init__(self, PV, screen_motor=None, zoom_lens_motor=None,
               lens_focus_motor=None, led=None, det=None, zoomPV=None,
               desc="PIM", checkMECXRTBelens=None):
    if PV == "":
      self.pim = None
    else:
      self.pim = stateiocDevice(PV)

    self.y = screen_motor
    self.zoom  = zoom_lens_motor
    self.focus = lens_focus_motor
    self.__led = led
    self.__desc = desc
    self.__det = det
    self.__zoomPV = zoomPV

    # Hutch specific routines that I don't know what to do with yet
    self._checkMECXRTBelens = checkMECXRTBelens=None # Used in .sin() for MEC
    self._viewerlauncher=None                        # Used in .viewer() in MEC

  def screen_in(self):
    self.pim.move("YAG")

  def diode_in(self):
    light = self.__getlight()
    if light and light > 1:
      print "Note: the LED light is not off, use .lightoff() to switch it off"
    self.pim.move("DIODE")

  def all_out(self):
    self.pim.move("OUT")

  def set_screen_in(self, pos):
    self.pim.setStatePos("YAG", pos)

  def set_diode_in(self, pos):
    self.pim.setStatePos("DIODE", pos)

  def set_all_out(self, pos):
    self.pim.setStatePos("OUT", pos)

  def lightoff(self):
    if self.__led:
      Pv.put(self.__led, 0)
    else:
      print "No LED in this PIM object"

  def lighton(self, level=100):
    if self.__led:
      Pv.put(self.__led, level)
    else:
      print "No LED in this PIM object"

  def __getlight(self):
    if self.__led:
      return Pv.get(self.__led)
    else:
      print "No LED in this PIM object"

  def zoomlvl(self,level=None):
    """
    Set or get zoom level

    Usage:
    zoomlvl()  --> Get zoom level
    zoomlvl(4) --> Set zoom level to 4
    """
    if not self.__zoomPV:
      print "Must have zoom level PV"
      return
    if not level:
      return Pv.get(self.__zoomPV + ':CUR_ZOOM')
    elif 1 <= level <= 12:
      print "Zooming to level", level
      Pv.put(self.__zoomPV + ':DES_ZOOM', level)
    else:
      return "Argument must be between 1 and 12"

  def zoomlvl_calibrate(self, lowLim=0, highLim=100):
    """ Self calibration for navitar zoom level """
    if not self.zoom:
      print "No zoom motor in PIM object"
      return
    print 'Finding lower limit...' 
    self.zoom.move(lowLim + 2)
    while self.zoom.ismoving():
      pass
    (status,msg) = self.zoom.check_limit_switches()
    while status is not 'low': 
      self.zoom.mvr(-1)
      while self.zoom.ismoving(): 
        pass
      (status,msg) = self.zoom.check_limit_switches()
    max_out = Pv.get(self.zoom.pvname + '.RMP')
    Pv.put(self.__zoomPV + ':MAX_OUT', max_out)
    Pv.put(self.zoom.pvname + ':SET_ZERO.PROC', 1)
    print '...Done.'
    sleep(2)
    print 'Finding upper limit...'
    self.zoom.move(highLim - 2)
    sleep(1)
    while self.zoom.ismoving():
      pass
    (status,msg) = self.zoom.check_limit_switches()
    while status is not 'high': 
      self.zoom.mvr(1)
      while self.zoom.ismoving(): 
        pass
      (status,msg) = self.zoom.check_limit_switches()
    max_in = Pv.get(self.zoom.pvname + '.RMP')
    Pv.put(self.__zoomPV + ':MAX_IN', max_in)
    print '...Done.'
    print 'Finished calibrating'

  def sin(self):
    if self._checkMECXRTBelens is not None:
      XRTBlenPosition = Pv.get("MEC:HXM:MMS:02.RBV")
      if XRTBlenPosition < -10.0:
        print "XRT Belens could be in, are you sure for yag3.sin()? Y/[N]"
        token = raw_input()
        if token == 'Y':
          self.screen_in()
        else:
          print "yag3.sin() aborted."
          return
      else:
        self.screen_in()
    else:
      self.screen_in()

  def viewer(self):
    ''' launches the gui viewer of the YAG screen '''
    if self._viewerlauncher==None : print('No gui file defined for this yag screen')
    else : os.system(self._viewerlauncher)

  def __repr__(self):
    return self.status()

  def status(self):
    str = estr("%s " % self.__desc,color="black",type="bold")
    state = self.pim.state()
    if state == "YAG":
      str += "screen is %s\n" % estr("IN",type="normal")
    elif state == "DIODE":
      str += "diode is %s\n" % estr("IN",type="normal")
    elif state == "OUT":
      str += "all elements are %s\n" % estr("OUT",color="green",type="normal")
    else:
      str += "%s\n" % estr("UNKOWN position",type="normal")
    if self.zoom:
      str += " zoom %.1f%%\n" % self.zoom.wm()
    if self.focus:
      str += " focus %.1f%%\n" % self.focus.wm()
    if self.__led:
      str += " light level %s%%\n" % self.__getlight()
    if self.__det:
      str += " %s" % self.__det.status()
    return str

