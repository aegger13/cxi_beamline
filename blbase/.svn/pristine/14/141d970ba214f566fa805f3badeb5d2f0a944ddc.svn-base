#!/usr/bin/python
# This module provides support
# for generic devices
# 
# Author:         Daniel Flath (SLAC)
# Created:        Apr 25, 2013
# Modifications:
#   Apr 25, 2011 DF
#       first version

import numpy as n
import sys
from blutil import estr
from blutil.pypslog import logprint
from motorPresets import PresetGroup 

class Device(object):
  """
    Base class for beamline devices.

    Add some documentation!
  """

  def __init__(self,objName=None,pvBase=None,presetsfile=None):
     self.objName = objName
     self.pvBase = pvBase
     self._presetsFile=presetsfile

     # fill this out in base classes like "self.motors={"motor1name": motor1object, "motor2name": motor2object, ...}
     self.motors = dict()

  def status(self):
    str = "** %s Status **\n\t%10s\t%10s\t%10s\n" % (self.objName, "Motor","User","Dial")
    keys = self.motors.keys()
    keys.sort()
    for key in keys:
       m = self.motors[key]
       str += "\t%10s\t%+10.4f\t%+10.4f\n" % (key,m.wm(),m.wm_dial())
       pass
    return str

  def detailed_status(self, toPrint=True):
    str = "** %s Detailed Status **\n" % (self.objName)
    keys = self.motors.keys()
    keys.sort()
    formatTitle = "%15s %20s  %18s  %4s  %10s  %10s  %10s  %10s  %10s  %10s  %7s  %7s  %7s  %7s  %5s  %5s  %7s\n"
    formatEntry = "%15s %20s  %18s  %4s  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %7.1f  %7.1f  %7.1f  %7.1f  %5.1f  %5.1f  %7.1f\n"
    str += formatTitle % ("Name", "EPICS Name", "PV Name", "EGU", "User", "User LL", "User HL", "Dial", "Dial LL", "Dial HL", "Vmin", "Vmin", "Vmax", "Vmax", "Accel", "Decel", "% Run")
    str += formatTitle % ("", "", "", "", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(Rev/s)", "(EGU/s)", "(Rev/s)", "(EGU/s)", "(s)", "(s)", "Current")
    for key in keys:
       m = self.motors[key]
       str += formatEntry % (self.objName+"."+key,m.get_par_silent("description"), m.pvname, m.get_par_silent("units"), m.wm(), m.get_par_silent("low_limit"), m.get_par_silent("high_limit"), m.wm_dial(), m.get_par_silent("dial_low_limit"), m.get_par_silent("dial_high_limit"), m.get_par_silent("s_base_speed"), m.get_par_silent("base_speed"), m.get_par_silent("s_speed"), m.get_par_silent("slew_speed"), m.get_par_silent("acceleration"), m.get_par_silent("back_accel"), float(m.get_par_silent("run_current",":")))
    if (toPrint):
      print str
    else:
      return str
       
  def __repr__(self):
    return self.status()

  def _loadPresets(self, reload=False):
    if self._presetsFile is None:
      print "ERROR: {0} has no preset file.".format(self.objName)
      return False
    if hasattr(self, "_presetGroup") and not reload:
      return True
    self._presetGroup = PresetGroup()
    for motor in self.motors.values():
      self._presetGroup.add(motor)
    return self._presetGroup.load(self._presetsFile)

  def presetMove(self, presetName, confirm=True):
    didLoad = self._loadPresets()
    if didLoad:
      print "Moving to preset location {0}.".format(presetName)
      self.presetPrint()
      if confirm:
        print "\nPerform this move? [N/y] ",
        r = raw_input()
        if r.lower() != 'y':
            return
        pass
      print "OK! Performing Moves"
      self._presetGroup.group_move(presetName)

  def presetPrint(self, presetName):
    didLoad = self._loadPresets()
    if didLoad:
      self._presetGroup.showPreset(presetName)

  def presetList(self):
    didLoad = self._loadPresets()
    if didLoad:
      print "Available Presets:"
      self._presetGroup.listPresets()

  def presetGenerate(self, name='current_pos'):
    """ Generate a preset position list """
    mnames = self.motors.keys()
    mnames.sort()
    p = "%s = {" % (name)
    i=0
    for mn in mnames:
      if i: p+=", "
      m = self.motors[mn]
      p += "'%s':%f" % (mn,m.wm())
      i+=1
      pass
    p += "}"
    print "Below is a preset string for the current position of the '%s' motors.  Please remove any motors which you do not want to move when activating the preset!\n\n%s" % (self.objName, p) 
    pass

