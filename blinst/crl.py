"""
Module for Be lens macros and safe operation.
"""

import time
import copy
from itertools import chain
import shutil
import numpy as np
import simplejson as json
from blbase import stateioc
from blbase.motorutil import tweak2D
from blbase.virtualmotor import VirtualMotor
from blutil import config
from blutil.belenses import calcDistanceForSize, calcBeamFWHM,\
                            calcLensSet, setLensSetsToFile
from blutil.calc import LensTransmission
import blutil.belenses

# Available lens radii
lensRadii2D = [50e-6,100e-6,200e-6,300e-6,500e-6,1000e-6,1500e-6]

class Crl(object):
  """
  Class for Be lens macros and safe operation.
  """
  def __init__(self, lensX, lensY, lensZ, yStatePV,
      CRLConfigFile=config.DEFAULT_LENS_SET,
      calibfile=None,
      zoffset=None, zdir=None, zrange=None,
      precisionLateral=0.05, E=None, attObj=None,
      lclsObj=None, monoObj=None,
      beamsizeUnfocused=500e-6):
    """
    lensX, lensY, lensZ: motors that move the position of the lens set
    yStatePV: ims motor states PV for preset y positions. This is used to
      check which lens set is closest to the beam.
    CRLConfigFile: file that defines which lenses are being used.
      see /reg/neh/operator/xppopr/xpppython_files/Be_lens_sets/current_set
    calibfile: json file that defines beam trajectory.
      contains dx, dy, x_ref, y_ref, z_ref
    zoffset: distance from sample to lens_z=0 in meters
    zdir: 1 or -1, represents beam direction wrt z direction.
    zrange: array or tuple of 2 values: minimum and maximum z pos in meters
    precisionLateral: tolerance on xy deviations from calibrated beam path
      before python prints a warning. Same units as x, y (currently mm)
    E: energy override for calculations. If E is defined, we'll use it,
      otherwise we'll try to use the mono first and the lcls second.
    attObj: lusiatt attenuator object for instrument-safe moves.
    lclsObj: object that gets PVs from lcls (for energy)
    monoObj: object that gets energy from monochromator
    beamsizeUnfocused: radial size of x-ray beam before focusing.
    """

    self._CRLConfigFile = CRLConfigFile
    try:
        self._readLensSet()
    except Exception as exc:
        print "\n\nWARNING: Could not load lens sets from File!"
        print exc
        print "Crl calculations may not behave as expected.\n"
    self._calibfile = calibfile
    self._zrange = zrange
    self._zdir = zdir
    self._zoffset = zoffset
    self._precisionLateral = precisionLateral
    self.beamsizeUnfocused = beamsizeUnfocused

    self.x = lensX
    self.y = lensY
    self.z = lensZ
    self._E = E
    self._attObj = attObj
    self._lclsObj = lclsObj
    self._monoObj = monoObj

    self.ypos = stateioc.stateiocDevice(yStatePV)
    self.zpos = VirtualMotor('crl_zpos', self._moveZ, self._whereZ,
                             self._waitall)
    self.beamSize = VirtualMotor('crl_beamsize', self._moveBeamsize,
                                 self._whereBeamsize,self._waitall)

    self.calc = blutil.belenses

  @property
  def E(self):
    """
    The energy used in calculations. user override > mono > lcls
    """
    if self._E is not None:
      self._which_E = "user override"
      return self._E
    if self._monoObj is not None:
      if self._monoObj._stateh1n.state() != "OUT":
        try:
          try:
            val = self._monoObj.getE()
          except:
            val = self._monoObj.getE1C()
          self._which_E = "mono"
          return val
        except:
          pass
    if self._lclsObj is not None:
      try:
        val = self._lclsObj.getXrayeV()/1000
        self._which_E = "lcls"
        return val
      except:
        pass
    self._which_E = "none"
    return None

  @E.setter
  def E(self, energy):
    """
    Override the mono/lcls energy for calculations.
    """
    self._E = energy

  def which_E(self):
    """
    Return a string indicating where the value of E is coming from.
    """
    if self.E is None:
      return "No source for E."
    return "E = {0:.3f}keV, from {1}".format(self.E, self._which_E)

  def get_calibration(self):
    """
    Load movement trajectory calibration from file.
    dx, dy: proportional change in x and y with respect to z
    x_ref, y_ref, z_ref: coordinates of a reference point along the beam
    """
    try:
      with open(self._calibfile, "r") as f:
        return json.load(f)
    except:
      return {}

  def set_calibration(self, dx=None, dy=None,
            x_ref=None, y_ref=None, z_ref=None):
    """
    Write movement trajectory calibration to file.
    dx, dy: proportional change in x and y with respect to z
    x_ref, y_ref, z_ref: coordinates of a reference point along the beam
    """
    calib = self.get_calibration()
    new_calib = dict(dx=dx, dy=dy, x_ref=x_ref, y_ref=y_ref, z_ref=z_ref)
    for name, value in new_calib.items():
      if value is not None:
        calib[name] = value
    txt = json.dumps(calib, sort_keys=True, indent="  ") + "\n"
    with open(self._calibfile, "w") as f:
      f.write(txt)
    return self.get_calibration()

  def set_reference_here(self):
    """
    Use current point as the saved reference point for calibrated moves.
    """
    xpos, ypos, zpos = self.x.wm(), self.y.wm(), self.z.wm()
    self.set_calibration(x_ref=xpos, y_ref=ypos, z_ref=zpos)
    return self.get_calibration()

  def set_calib_delta_here(self):
    """
    Use current point to set dx and dy for calibration with respect to current
    set reference point.
    """
    calib = self.get_calibration()
    x_here = self.x.wm()
    y_here = self.y.wm()
    z_here = self.z.wm()
    dx = (x_here - calib["x_ref"]) / (z_here - calib["z_ref"])
    dy = (y_here - calib["y_ref"]) / (z_here - calib["z_ref"])
    self.set_calibration(dx=dx, dy=dy)
    return self.get_calibration()

  def save_calib_backup(self):
    """
    Saves a backup file for the current calibration
    """
    shutil.copyfile(self._calibfile, self._calibfile +
                    time.strftime("_%Y-%m-%d_%Hh%Mm%Ss"))

  def _moveZ(self, pos, safe=True):
    """
    Moves z to pos and x and y to their calibrated offset positions. If safe
    is True, we call ._makeSafe().
    """
    if safe:
        is_safe = self._makeSafe()
    if not safe or is_safe:
      if self._calibfile is None:
        self.z.mv(pos)
      else:
        calib = self.get_calibration()
        dz = pos - calib["z_ref"]
        self.z.mv(pos)
        self.x.mv(calib["x_ref"] + calib["dx"] * dz)
        self.y.mv(calib["y_ref"] + calib["dy"] * dz)
    else:
      print "crl moveZ ABORTED!"

  def _whereZ(self):
    """
    Check if the lens is along the calibrated beam path.
    Return z's position.
    """
    if self._calibfile is not None:
      calib = self.get_calibration()
      x_off = self.x.wm() - calib["x_ref"]
      y_off = self.y.wm() - calib["y_ref"]
      z_off = self.z.wm() - calib["z_ref"]
      dx = calib["dx"]
      dy = calib["dy"]
      if abs(z_off * dx - x_off) > self._precisionLateral:
        print "WARNING: Lens x is outside the expected calibrated location!"
      if abs(z_off * dy - y_off) > self._precisionLateral:
        print "WARNING: Lens y is outside the expected calibrated location!"
    return self.z.wm()

  def _makeSafe(self):
    """
    Move the thickest attenuator in to prevent damage due to wayward focused
    x-rays. Return True if the attenuator was moved in.
    """
    if self._attObj is None:
      print "WARNING: Cannot do safe crl moveZ, no attenuator object provided."
      return False
    filt, thk = self._attObj.filters[0], 0
    for f in self._attObj.filters:
      t = f.d()
      if t > thk:
        filt, thk = f, t
    if not filt.isin():
      filt.movein()
      time.sleep(0.01)
      filt.wait()
    if filt.isin():
      print "REMINDER: Beam stop attenuator moved in!"
      safe = True
    else:
      print "WARNING: Beam stop attenuator did not move in!"
      safe = False
    return safe

  def _moveBeamsize(self, size, safe=True):
    """
    Change the beamsize at the sample location.
    """
    if None in (self._zoffset, self._zdir, self.beamsizeUnfocused):
      print "Cannot move beamsize. At least one of", \
            "zoffset, zdir, beamsizeUnfocused was not defined at init."
    else:
      dist = calcDistanceForSize(size, self._lensPacks[self._get_lensset()],
             self.E, fwhm_unfocused=self.beamsizeUnfocused)[0]
      self._moveZ((dist - self._zoffset) * self._zdir * 1000, safe=safe)

  def _whereBeamsize(self):
    """
    Return the beamsize at the sample location.
    """
    if None in (self._zoffset, self._zdir, self.beamsizeUnfocused):
      print "Cannot check beamsize. At least one of", \
            "zoffset, zdir, beamsizeUnfocused was not defined at init."
    else:
      lenspack = self._lensPacks[self._get_lensset()]
      dist_m = self.z.wm() / 1000 * self._zdir + self._zoffset
      return calcBeamFWHM(self.E, lenspack, distance=dist_m, material="Be",
                      density=None, fwhm_unfocused=self.beamsizeUnfocused)
  
  def _waitall(self):
    """
    Wait for all motors to be done moving.
    """
    for mot in [self.z,self.x,self.y]:
      mot.wait()
  
  def stop(self):
    """
    Stop all motors.
    """
    for mot in [self.z,self.x,self.y]:
      mot.stop()

  def _get_lensset(self):
    """
    Return the index of the lensset closest to the beam
    """
    states = self.ypos.statesAll()
    states.remove("OUT")
    states.sort()
    pos_d = self.ypos.statePosAll()
    here = self.y.wm()
    deltas = []
    for s in states:
      deltas.append(abs(pos_d[s] - here))
    index = np.argmin(deltas)
    p_len = len(self._lensPacks)
    if index >= p_len:
      return p_len - 1
    else:
      return index

  def align(self):
    """
    Tweak the x and y positions with the intention of aligning them with the
    beam.
    """
    tweak2D(self.x,self.y,-.02,.02,'Be_lens_x','Be_lens_y')

  def alignCalibrationForLensset(self, lenssetNo=None, dz=100, safe=True):
    """
    Macro for calibration. Steps:
    1. Make safe
    2. Save z pos
    3. Move z, x to previous reference position
    4. Move y to preset corresponding to lenssetNo,
        or don't move it if left as None
    5. call .align() to align x and y with beam
    6. save reference position
    7. move z by dz, call .align() to align x and y with beam
    8. save trajectory as dx and dy
    9. return to original z pos, but aligned with the beam
    """
    if safe:
      if not self._makeSafe():
        return
    z_orig = self.z.wm()
    if lenssetNo is None:
      print "Moving x and z to reference pos... (assume y is close)"
    else:
      if not isinstance(lenssetNo, int):
        print "lenssetNo must be an integer!"
        return
      print "Moving x and z to reference pos, y to epics preset"
      y_move = False
      for state in self.ypos.statesAll():
        if str(lenssetNo) in state:
          self.ypos.moveState(state)
          y_move = True
          break
      if not y_move:
        print "Invalid lenssetNo!"
        return
    calib = self.get_calibration()
    self.z.mv(calib["z_ref"])
    self.x.mv(calib["x_ref"])
    self._waitall()
    print "Please align lens with cursor keys!"
    print "(change step size with Shift-<cursors>, to quit press q)"
    self.align()
    self.set_reference_here()
    self.zpos.mvr(dz)
    self._waitall()
    print "Please align lens with cursor keys!"
    print "(change step size with Shift-<cursors>, to quit press q)"
    self.align()
    self.set_calib_delta_here()
    print "Calibration complete, returning to original z pos"
    self.zpos.mv(z_orig)
    self._waitall()
    print "Done!"
    
  def _setLensSetsToFile(self, lenssets=None):
    if lenssets is not None:
      self._lensPacks = lenssets
    filename = self._CRLConfigFile
    setLensSetsToFile(self._lensPacks, filename, debug=True)
    
  def _readLensSet(self, printOnly=False):
    filename = self._CRLConfigFile
    f=open(filename)
    sets = eval(f.read())
    print 'sets:',sets
    f.close()
    if not printOnly:
      self._lensPacks = sets

  def planSet(self, Energy, sizehor, sizever=None, exclude=[],
        maxTotNumberOfLenses=12, maxeach=5, focusBeforeSample=False):
    """
    Macro to help plan for what lens set to use.
    """
    if None in (self._zoffset, self._zrange, self.beamsizeUnfocused):
      print "Cannot planSet. At least one of zoffset, zrange," \
            "beamsizeUnfocused not defined in init."
      return

    focusBeforeSample = int(focusBeforeSample)
    if sizever is not None:
      sizecalc1 = np.max(sizehor,sizever)
    else:
      sizecalc1 = sizehor

    tlensradii = copy.copy(lensRadii2D)
    for rad in exclude:
      tlensradii.remove(rad)
    sets, effrads, sizes, foclens = calcLensSet(Energy, sizecalc1,
        self._zoffset, Nmax=maxTotNumberOfLenses, maxeach=5,
        lensRadii=lensRadii2D)
    dists = np.asarray(
        [calcDistanceForSize(sizecalc1, list(chain(*zip(set, tlensradii))),
         E=Energy, fwhm_unfocused=self.beamsizeUnfocused)[focusBeforeSample]
         for set in sets])
    goodsets = np.logical_and(
        dists > np.min(self._zoffset + np.asarray(self._zrange)),
        dists < np.max(self._zoffset + np.asarray(self._zrange)))
    sets = sets[goodsets]
    sizerangemin = np.asarray(
        [calcBeamFWHM(Energy, list(chain(*zip(set, tlensradii))),
         distance=self._zoffset-min(self._zrange),
         fwhm_unfocused=self.beamsizeUnfocused, printsummary=False)
         for set in sets])
    sizerangemax = np.asarray(
        [calcBeamFWHM(Energy, list(chain(*zip(set, tlensradii))),
         distance=self._zoffset-max(self._zrange),
         fwhm_unfocused=self.beamsizeUnfocused, printsummary=False)
         for set in sets])

    sizes = sizes[goodsets]
    effrads = effrads[goodsets]
    dists = dists[goodsets]
    foclens = foclens[goodsets]
    transms = np.asarray(
        [LensTransmission(ter, self.beamsizeUnfocused, E=Energy)
         for ter in effrads])
    Nlenses_s = np.sum(sets,1)

    resstring = ' N   f/m   Min/um   Max/um   T/%  Set  \n'
    zips = zip(sets, sizerangemin, sizerangemax, effrads, transms, Nlenses_s,
               foclens)
    t = '{:2d} {:5.2f} {:8.1f} {:8.1f} {:5.1f}  '
    for n, z in enumerate(zips):
      set, sizemin, sizemax, effrad, transm, Nlenses, foclen = z
      resstring += t.format(n, foclen, sizemin*1e6, sizemax*1e6, transm*100)
      resstring += ', '.join(['%d x %dum'%(setLensno, tlensradii[m]*1e6)
                              for m, setLensno in enumerate(set)
                              if setLensno > 0])
      resstring += '\n'
    print resstring

  def __repr__(self):
    return self.status()

  def status(self):
    xpos = self.x.wm()
    ypos = self.y.wm()
    zpos = self.z.wm()
    str  = "Lens positions: "
    str += "(X,Y,Z) at %.2f, %.2f, %.2f.\n" % (xpos, ypos, zpos)
    return str

  def printSet(self):
    str = "Lens configuration: (#lens, radius) "
    for ipack,pack in enumerate(self._lensPacks):
      str += "\n pack %d: " % ipack
      lp = np.array(pack).reshape(2,len(pack)/2)
      for lenstype in lp:
        str += "(%d, %d*1e-6)" % (int(lenstype[0]), int(lenstype[1]*1e6))
    return str

