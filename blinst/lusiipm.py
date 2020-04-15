#!/usr/bin/python
# This module provides support for 
# IPM (intensity position monitor) devices

from blbase.stateioc import stateiocDevice
from blutil import estr, guessBeamline, config
from blutil.edm import edm_hutch_open
import subprocess

class IPM:
  """ Class to control the IPM """
  def __init__(self, ipmPV, det=None, ipimb=None,
               mot_diode_x=None, mot_diode_y=None, mot_target_y=None,
               desc="ipm", show_dets=False):
    self._ipmPV = ipmPV
    diodePV = ipmPV + ":DIODE"
    targetPV = ipmPV + ":TARGET"
    self.diode = stateiocDevice(diodePV)
    self.target = stateiocDevice(targetPV)
    self.__show_dets=show_dets
    self.__det=det
    self.__desc=desc

    self.ipimb = ipimb
    self.dx = mot_diode_x
    self.dy = mot_diode_y
    self.ty = mot_target_y

    self.amiDet = self.__det

  def diode_in(self):
    """Move diode to in position."""
    self.diode.move("IN")

  def diode_out(self):
    """Move diode to out position."""
    self.diode.move("OUT")

  def target_in(self, num):
    """Move target to in position 1, 2, 3, or 4."""
    self.target.move("TARGET{0}".format(num))

  def target_out(self):
    """Move target to in position."""
    self.target.move("OUT")

  def target_pos(self):
    """Show target set positions."""
    return self.target.posAll()

  def set_diodein(self, pos):
    """Change diode in position."""
    self.diode.setStatePos("IN", pos)

  def set_diodeout(self, pos):
    """Change diode out position."""
    self.diode.setStatePos("OUT", pos)

  def get_gain(self, num=-1):
    """
    Get ipimb gain.

    Parameters:
    num: integer channel number. Leave at -1 to get all channels.
    """
    return self.ipimb.getGain(num)

  def set_gain(self, gain, num=-1):
    """
    Set ipimb gain.

    Parameters:
    gain: string gain value, one of the following options:
         ["1pF", "4.7pF", "24pF", "120pF", "620pF",
          "3.3nF", "10nF", "5.7pF", "28.7pF", "144pF",
          "740pF", "3.92nF", "13.3nF", "0pF", "14nF"]
    you can also use "+1" to go to the next option on the list,
    or "-1" to go to the previous option.
    num: integer, which channel to set. Leave at -1 to set all.
    """
    return self.ipimb.setGain(gain, num)

  def config_gui(self):
    self.ipimb.config_gui()

  def edm_control(self):
    """
    Opens up the ipm gui.

    Checks for a file under device_states/ipm.edl and opens it appropriately.
    """
    self._gui("ipm", self.ipimb.basePV)

  def edm_median(self):
    """
    Opens up the ipm median gui.

    Checks for a file under device_states/posMon.edl and opens it appropriately.
    """
    self._gui("posMon", self._ipmPV + ":PY")

  def _gui(self, file, ipm_macro):
    try:
      hutch = guessBeamline()
      base, iocpv, evrpv = self._config_pvs()
      macros = {
                  "DEVICE"   : self._ipmPV,
                  "IPM"      : ipm_macro,
                  "TARGETM"  : self.ty.pvname,
                  "DIODEM"   : self.dy.pvname,
                  "CONFIG"   : "env -i /reg/neh/operator/xppopr/bin/ipmConfigEpics_basic {0} {1} {2}".format(base, iocpv, evrpv),
                  "LOCATION" : self._ipmPV.split(":")[1],
                  "DEV_NAME" : self.__desc.upper(),
               }
      edm_hutch_open("device_states/{}.edl".format(file), **macros)
    except Exception, exc:
      print "Error opening ipm gui:"
      print exc

  def _config_pvs(self):
    """
    Return pvs needed to launch config gui
    """
    base = self.ipimb.basePV
    iocpv = base[:-2] + "IOC"
    evrpv = self.ipimb._ipimb__evrPV
    ncolon = evrpv.count(":")
    while evrpv.count(":") == ncolon:
        evrpv = evrpv[:-1]
    return base, iocpv, evrpv

  def __repr__(self):
    return self.status()

  def status(self,show_dets=None):
    str = estr(self.__desc, color="black", type="bold")
    if self.dx and self.dy:
      str += ", diode @ (dx,dy) = ({0:.4f},{1:.4f})".format(self.dx.wm(),self.dy.wm())
    str += ", diode {0}".format(self.diode.state())
    if self.ty:
      str += ", target @ ty = {0:.4f}".format(self.ty.wm())
    str += ", target {0}\n".format(self.target.state())
    if show_dets is None:
      show_dets = self.__show_dets
    if self.__det and show_dets:
      str += " {0}".format(self.__det.status())
    return str

